import hashlib
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import (
    ConflictError,
    ForbiddenError,
    GatewayError,
    InvalidInputError,
    NotFoundError,
)
from app.models import (
    Collection,
    CollectionEntry,
    CollectionStatus,
    Community,
    EntryStatus,
    Member,
    Payment,
    PaymentChannel,
    PaymentStatus,
    User,
    WebhookEvent,
)
from app.schemas.payments import ManualMarkIn
from app.services import audit, ledger
from app.services.monnify import MonnifyError, monnify_service


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_payment_by_reference(db: Session, payment_reference: str) -> Payment:
    payment = (
        db.query(Payment)
        .filter(Payment.payment_reference == payment_reference)
        .first()
    )
    if payment is None:
        raise NotFoundError("Payment not found")
    return payment


# ── Checkout initiation ───────────────────────────────────────────────────────

async def _initiate_checkout(
    db: Session,
    *,
    collection: Collection,
    entry: CollectionEntry,
    customer_name: str,
    customer_email: str,
    redirect_url: str,
    payer_email: Optional[str] = None,
) -> Payment:
    if collection.status != CollectionStatus.ACTIVE:
        raise InvalidInputError("Collection is not active")
    if entry.status != EntryStatus.PENDING:
        raise InvalidInputError("No pending amount due")

    # Reuse an in-flight checkout instead of stacking duplicates.
    existing = (
        db.query(Payment)
        .filter(
            Payment.entry_id == entry.id,
            Payment.status == PaymentStatus.PENDING,
            Payment.channel == PaymentChannel.CHECKOUT,
        )
        .first()
    )
    if existing and existing.checkout_url:
        return existing

    payment = Payment(
        collection_id=collection.id,
        entry_id=entry.id,
        member_id=entry.member_id,
        amount=entry.amount_due,
        channel=PaymentChannel.CHECKOUT,
        payment_reference=f"acafund-{collection.id}-{entry.id}-{uuid4().hex[:8]}",
        status=PaymentStatus.PENDING,
        payer_email=payer_email,
    )
    db.add(payment)
    db.flush()

    try:
        result = await monnify_service.init_transaction(
            amount=entry.amount_due,
            customer_name=customer_name,
            customer_email=customer_email,
            payment_reference=payment.payment_reference,
            description=f"Payment for {collection.title}",
            redirect_url=redirect_url,
        )
    except MonnifyError as e:
        db.rollback()
        raise GatewayError(f"Payment gateway error: {e.message}")

    payment.checkout_url = result["checkoutUrl"]
    payment.monnify_transaction_reference = result.get("transactionReference")
    db.commit()
    db.refresh(payment)
    return payment


async def member_pay(
    db: Session, user: User, collection: Collection, redirect_url: str
) -> Payment:
    member = (
        db.query(Member)
        .filter(
            Member.community_id == collection.community_id,
            Member.user_id == user.id,
        )
        .first()
    )
    if member is None:
        raise ForbiddenError("Not a community member")
    entry = (
        db.query(CollectionEntry)
        .filter(
            CollectionEntry.collection_id == collection.id,
            CollectionEntry.member_id == member.id,
        )
        .first()
    )
    if entry is None:
        raise ForbiddenError("Not enrolled in this collection")
    return await _initiate_checkout(
        db,
        collection=collection,
        entry=entry,
        customer_name=user.full_name,
        customer_email=user.email,
        redirect_url=redirect_url,
    )


async def guest_pay(
    db: Session,
    collection: Collection,
    entry_id: int,
    redirect_url: str,
    payer_email: Optional[str],
) -> Payment:
    entry = db.get(CollectionEntry, entry_id)
    if entry is None or entry.collection_id != collection.id:
        raise NotFoundError("Entry not found in this collection")
    member = db.get(Member, entry.member_id)
    email = payer_email or member.email or f"guest-{entry.id}@acafund.app"
    return await _initiate_checkout(
        db,
        collection=collection,
        entry=entry,
        customer_name=member.display_name,
        customer_email=email,
        redirect_url=redirect_url,
        payer_email=payer_email,
    )


# ── Reconciliation ────────────────────────────────────────────────────────────

def _apply_paid(db: Session, payment_id: int, verification: dict) -> bool:
    """Transition a payment to PAID under a row lock. Returns False when it was
    already reconciled. Stages changes only — the caller commits."""
    locked = (
        db.query(Payment).filter(Payment.id == payment_id).with_for_update().one()
    )
    if locked.status == PaymentStatus.PAID:
        return False

    locked.status = PaymentStatus.PAID
    locked.raw_verification_payload = verification
    locked.paid_at = _now()

    entry = db.get(CollectionEntry, locked.entry_id)
    entry.status = EntryStatus.PAID
    entry.paid_at = _now()

    collection = db.get(Collection, locked.collection_id)
    ledger.record_credit(
        db,
        community_id=collection.community_id,
        amount=locked.amount,
        reference_type="payment",
        reference_id=locked.id,
        description=f"Payment {locked.payment_reference}",
    )
    return True


async def _verify_with_gateway(payment: Payment) -> tuple[bool, dict]:
    verification = await monnify_service.verify_transaction(payment.payment_reference)
    status_str = verification.get("paymentStatus", "")
    amount_paid = Decimal(str(verification.get("amountPaid", 0)))
    ok = status_str in ("PAID", "OVERPAID") and amount_paid >= payment.amount
    return ok, verification


async def sync_payment(db: Session, payment: Payment) -> str:
    """Verify a payment against Monnify and reconcile if it settled."""
    if payment.status == PaymentStatus.PAID:
        return "already_paid"
    try:
        ok, verification = await _verify_with_gateway(payment)
    except MonnifyError as e:
        raise GatewayError(f"Monnify error: {e.message}")
    if not ok:
        return "not_paid"
    _apply_paid(db, payment.id, verification)
    db.commit()
    return "reconciled"


async def handle_webhook(db: Session, payload: dict, raw_body: bytes) -> str:
    """Process one Monnify webhook delivery exactly once.

    The WebhookEvent row, the payment transition, and the ledger credit all
    land in a single transaction; a concurrent duplicate delivery loses on the
    unique event key and rolls back cleanly.
    """
    event_data = payload.get("eventData", payload)
    tx_ref = event_data.get("transactionReference") or payload.get(
        "transactionReference"
    )
    event_key = tx_ref or hashlib.sha256(raw_body).hexdigest()

    if db.query(WebhookEvent).filter(WebhookEvent.event_key == event_key).first():
        return "duplicate"

    event = WebhookEvent(event_key=event_key, payload=payload)
    db.add(event)

    outcome = await _process_webhook_payload(db, payload, event_data, event)
    event.outcome = outcome
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return "duplicate"
    return outcome


async def _process_webhook_payload(
    db: Session, payload: dict, event_data: dict, event: WebhookEvent
) -> str:
    payment_reference = event_data.get("paymentReference") or payload.get(
        "paymentReference"
    )
    if payment_reference:
        payment = (
            db.query(Payment)
            .filter(Payment.payment_reference == payment_reference)
            .first()
        )
        if payment:
            if payment.status == PaymentStatus.PAID:
                return "already_paid"
            try:
                ok, verification = await _verify_with_gateway(payment)
            except MonnifyError:
                return "verification_failed"
            if not ok:
                return "not_paid"
            _apply_paid(db, payment.id, verification)
            return "ok"

    # No matching Payment row — check for reserved-account direct transfer.
    product = event_data.get("product", payload.get("product", {})) or {}
    account_reference = product.get("reference", "")
    amount_paid = Decimal(
        str(event_data.get("amountPaid") or payload.get("amountPaid") or 0)
    )

    if account_reference.startswith("acafund-comm-") and amount_paid > 0:
        community = (
            db.query(Community)
            .filter(Community.reserved_account_reference == account_reference)
            .first()
        )
        if community:
            db.flush()  # assign event.id for the ledger reference
            ledger.record_credit(
                db,
                community_id=community.id,
                amount=amount_paid,
                reference_type="reserved_account_transfer",
                reference_id=event.id,
                description=f"Direct transfer via reserved account ({account_reference})",
                raw_payload=payload,
            )
            return "reserved_account_credit_recorded"

    return "ignored"


# ── Manual actions ────────────────────────────────────────────────────────────

def mark_paid_manual(
    db: Session,
    actor: Member,
    collection: Collection,
    entry: CollectionEntry,
    data: ManualMarkIn,
) -> Payment:
    if entry.status != EntryStatus.PENDING:
        raise ConflictError("Entry is not pending")

    payment = Payment(
        collection_id=collection.id,
        entry_id=entry.id,
        member_id=entry.member_id,
        amount=entry.amount_due,
        channel=data.channel,
        payment_reference=f"manual-{uuid4().hex[:12]}",
        status=PaymentStatus.PAID,
        recorded_by=actor.user_id,
        paid_at=_now(),
    )
    db.add(payment)
    db.flush()

    entry.status = EntryStatus.PAID
    entry.paid_at = payment.paid_at
    entry.note = data.note
    entry.marked_by = actor.user_id

    ledger.record_credit(
        db,
        community_id=collection.community_id,
        amount=payment.amount,
        reference_type="payment",
        reference_id=payment.id,
        description=f"Manual {data.channel.value} payment {payment.payment_reference}",
    )
    audit.log(
        db,
        community_id=collection.community_id,
        actor_user_id=actor.user_id,
        action="entry_marked_paid",
        entity_type="collection_entry",
        entity_id=entry.id,
        data={"channel": data.channel.value, "note": data.note},
    )
    db.commit()
    db.refresh(payment)
    return payment


def waive_entry(
    db: Session,
    actor: Member,
    collection: Collection,
    entry: CollectionEntry,
    note: Optional[str],
) -> CollectionEntry:
    if entry.status != EntryStatus.PENDING:
        raise ConflictError("Only pending entries can be waived")
    entry.status = EntryStatus.WAIVED
    entry.note = note
    entry.marked_by = actor.user_id
    audit.log(
        db,
        community_id=collection.community_id,
        actor_user_id=actor.user_id,
        action="entry_waived",
        entity_type="collection_entry",
        entity_id=entry.id,
        data={"note": note},
    )
    db.commit()
    db.refresh(entry)
    return entry


def revert_entry(
    db: Session,
    actor: Member,
    collection: Collection,
    entry: CollectionEntry,
    note: Optional[str],
) -> CollectionEntry:
    """Undo a manual mark or a waive. Manual payments are reversed with a
    balancing debit — ledger history is append-only, never rewritten."""
    if entry.status == EntryStatus.WAIVED:
        entry.status = EntryStatus.PENDING
        entry.note = note
        entry.marked_by = actor.user_id
        action = "waive_reverted"
    elif entry.status == EntryStatus.PAID:
        payment = (
            db.query(Payment)
            .filter(
                Payment.entry_id == entry.id, Payment.status == PaymentStatus.PAID
            )
            .order_by(Payment.id.desc())
            .first()
        )
        if payment is None or payment.channel == PaymentChannel.CHECKOUT:
            raise ConflictError("Verified gateway payments cannot be reverted")
        payment.status = PaymentStatus.REVERSED
        ledger.record_debit(
            db,
            community_id=collection.community_id,
            amount=payment.amount,
            reference_type="manual_reversal",
            reference_id=payment.id,
            description=f"Reversal of manual payment {payment.payment_reference}",
        )
        entry.status = EntryStatus.PENDING
        entry.paid_at = None
        entry.note = note
        entry.marked_by = actor.user_id
        action = "manual_payment_reverted"
    else:
        raise ConflictError("Nothing to revert on this entry")

    audit.log(
        db,
        community_id=collection.community_id,
        actor_user_id=actor.user_id,
        action=action,
        entity_type="collection_entry",
        entity_id=entry.id,
        data={"note": note},
    )
    db.commit()
    db.refresh(entry)
    return entry


# ── Lookups ───────────────────────────────────────────────────────────────────

def get_my_entry(
    db: Session, user: User, collection: Collection
) -> tuple[CollectionEntry, str]:
    member = (
        db.query(Member)
        .filter(
            Member.community_id == collection.community_id,
            Member.user_id == user.id,
        )
        .first()
    )
    if member is None:
        raise ForbiddenError("Not a community member")
    entry = (
        db.query(CollectionEntry)
        .filter(
            CollectionEntry.collection_id == collection.id,
            CollectionEntry.member_id == member.id,
        )
        .first()
    )
    if entry is None:
        raise NotFoundError("Not enrolled in this collection")
    return entry, member.display_name
