from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import (
    ConflictError,
    ForbiddenError,
    GatewayError,
    InvalidInputError,
    NotFoundError,
)
from app.core.money import to_money
from app.models import (
    Collection,
    CollectionEntry,
    CollectionStatus,
    EntryStatus,
    Member,
    Payment,
    PaymentChannel,
    PaymentStatus,
    User,
    WebhookEvent,
)
from app.schemas.payments import ManualMarkIn
from app.services import audit, expenses as expenses_service, ledger
from app.services.flutterwave import FlutterwaveError, flutterwave_service


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


def submit_payment_form(
    db: Session, payment: Payment, collection: Collection, values: dict
) -> Payment:
    """Validate and store a guest's answers to the collection's custom form,
    submitted after checkout and before the confirmation screen."""
    field_defs = collection.custom_fields or []
    for field in field_defs:
        key = field["key"]
        value = values.get(key)
        if field.get("required") and (value is None or value == ""):
            raise InvalidInputError(f"'{field['label']}' is required")
        if value is None or value == "":
            continue
        if field["type"] == "select" and value not in (field.get("options") or []):
            raise InvalidInputError(f"'{field['label']}' has an invalid selection")
        if field["type"] == "checkbox" and not isinstance(value, bool):
            raise InvalidInputError(f"'{field['label']}' must be true or false")
        if field["type"] == "number":
            try:
                float(value)
            except (TypeError, ValueError):
                raise InvalidInputError(f"'{field['label']}' must be a number")

    payment.form_responses = values
    payment.form_submitted_at = _now()
    db.commit()
    db.refresh(payment)
    return payment


# ── Checkout initiation ───────────────────────────────────────────────────────
#
# Collection is via a Flutterwave dynamic virtual account: the payer transfers
# directly to a one-time account/bank number instead of being redirected to a
# hosted checkout page. `charge.completed` webhook confirms it, keyed by our
# payment_reference. No BVN, no card fields collected by us.

async def _create_virtual_account_payment(
    db: Session,
    *,
    collection: Collection,
    amount: Decimal,
    reference: str,
    customer_email: str,
    customer_name: str,
    payer_email: Optional[str],
    entry: Optional[CollectionEntry] = None,
) -> Payment:
    payment = Payment(
        collection_id=collection.id,
        entry_id=entry.id if entry else None,
        member_id=entry.member_id if entry else None,
        amount=amount,
        channel=PaymentChannel.CHECKOUT,
        payment_reference=reference,
        status=PaymentStatus.PENDING,
        payer_email=payer_email,
    )
    db.add(payment)
    db.flush()

    try:
        customer = await flutterwave_service.create_customer(customer_email, customer_name)
        account = await flutterwave_service.create_virtual_account(
            reference=payment.payment_reference,
            amount=amount,
            customer_id=customer["id"],
            narration=f"{collection.title} - {customer_name}",
        )
    except FlutterwaveError as e:
        db.rollback()
        raise GatewayError(f"Payment gateway error: {e.message}")

    payment.flw_customer_id = customer["id"]
    payment.flw_virtual_account_id = account.get("id")
    payment.va_account_number = account.get("account_number")
    payment.va_bank_name = account.get("account_bank_name")
    va_amount = account.get("amount")
    payment.va_amount = Decimal(str(va_amount)) if va_amount is not None else amount
    expiry_iso = account.get("account_expiration_datetime")
    if expiry_iso:
        try:
            payment.va_expires_at = datetime.fromisoformat(expiry_iso.replace("Z", "+00:00"))
        except ValueError:
            pass
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
    if collection.status != CollectionStatus.ACTIVE:
        raise InvalidInputError("Collection is not active")
    if entry.status != EntryStatus.PENDING:
        raise InvalidInputError("No pending amount due")

    existing = (
        db.query(Payment)
        .filter(
            Payment.entry_id == entry.id,
            Payment.status == PaymentStatus.PENDING,
            Payment.channel == PaymentChannel.CHECKOUT,
        )
        .first()
    )
    if existing and existing.va_account_number:
        return existing

    return await _create_virtual_account_payment(
        db,
        collection=collection,
        amount=entry.amount_due,
        reference=f"GlassJar-{collection.id}-{entry.id}-{uuid4().hex[:8]}",
        customer_email=user.email,
        customer_name=user.full_name,
        payer_email=user.email,
        entry=entry,
    )


async def public_pay(
    db: Session,
    collection: Collection,
    redirect_url: str,
    payer_email: Optional[str],
) -> Payment:
    """Anyone-with-the-link checkout: no roster match, no CollectionEntry.
    Amount is fixed at the collection's per-payer amount."""
    if collection.status != CollectionStatus.ACTIVE:
        raise InvalidInputError("Collection is not active")

    email = payer_email or f"guest-{uuid4().hex[:8]}@GlassJar.app"
    return await _create_virtual_account_payment(
        db,
        collection=collection,
        amount=collection.amount_per_member,
        reference=f"GlassJar-{collection.id}-guest-{uuid4().hex[:8]}",
        customer_email=email,
        customer_name="Guest",
        payer_email=payer_email,
    )


def total_collected(db: Session, collection_id: int) -> Decimal:
    total = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.collection_id == collection_id, Payment.status == PaymentStatus.PAID)
        .scalar()
    )
    return to_money(total)


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

    if locked.entry_id is not None:
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


async def sync_payment(db: Session, payment: Payment) -> str:
    """Re-check a payment's status.

    Flutterwave's virtual-account flow doesn't expose a "verify this
    reference against the gateway right now" endpoint the way Monnify did —
    confirmation is webhook-driven only (`charge.completed`). This is a
    best-effort no-op that just re-reads our own record; it exists so the
    frontend's "sync" retry button still has something to call, but it can't
    manufacture a confirmation the webhook hasn't delivered yet.
    """
    if payment.status == PaymentStatus.PAID:
        return "already_paid"
    return "not_paid"


async def handle_webhook(db: Session, payload: dict, raw_body: bytes) -> str:
    """Process one Flutterwave webhook delivery exactly once.

    The WebhookEvent row and whatever state change it causes land in a
    single transaction; a concurrent duplicate delivery loses on the unique
    event key and rolls back cleanly.
    """
    event_type = payload.get("type", "")
    data = payload.get("data", {}) or {}
    event_key = (
        data.get("id") or payload.get("webhook_id") or f"unkeyed-{uuid4().hex}"
    )

    if db.query(WebhookEvent).filter(WebhookEvent.event_key == event_key).first():
        return "duplicate"

    event = WebhookEvent(provider="flutterwave", event_key=event_key, payload=payload)
    db.add(event)

    if event_type == "charge.completed":
        outcome = _process_charge_completed(db, data)
    elif event_type in ("transfer.disburse", "transfer.reversal"):
        outcome = expenses_service.process_transfer_webhook(db, data)
    else:
        outcome = "ignored"

    event.outcome = outcome
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return "duplicate"
    return outcome


def _process_charge_completed(db: Session, data: dict) -> str:
    reference = data.get("reference")
    if not reference:
        return "ignored"
    payment = (
        db.query(Payment).filter(Payment.payment_reference == reference).first()
    )
    if payment is None:
        return "ignored"
    if payment.status == PaymentStatus.PAID:
        return "already_paid"

    status = str(data.get("status", "")).lower()
    if status not in ("succeeded", "success"):
        return "not_paid"

    amount_paid = Decimal(str(data.get("amount", 0)))
    if amount_paid < payment.amount:
        return "underpaid"

    _apply_paid(db, payment.id, data)
    return "ok"


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
