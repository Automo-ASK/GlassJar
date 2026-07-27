import secrets
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.core.money import to_money
from app.models import (
    Collection,
    CollectionEntry,
    CollectionStatus,
    EntryStatus,
    Member,
    Payment,
    PaymentStatus,
)
from app.schemas.collections import (
    CollectionCreateIn,
    CollectionDashboardOut,
    CollectionDetailOut,
    CollectionOut,
    EntryOut,
    FormResponseOut,
)
from app.schemas.reports import ActiveCollectionSummaryOut
from app.services import audit
from app.services import payments as payments_service

ZERO = Decimal("0.00")


def _generate_share_token(db: Session) -> str:
    while True:
        token = secrets.token_urlsafe(12)
        if not db.query(Collection).filter(Collection.share_token == token).first():
            return token


def get_collection(db: Session, collection_id: int) -> Collection:
    collection = db.get(Collection, collection_id)
    if collection is None:
        raise NotFoundError("Collection not found")
    return collection


def get_collection_by_share_token(db: Session, share_token: str) -> Collection:
    collection = (
        db.query(Collection).filter(Collection.share_token == share_token).first()
    )
    if collection is None:
        raise NotFoundError("Collection not found")
    return collection


def create_collection(
    db: Session, actor: Member, data: CollectionCreateIn
) -> Collection:
    roster = db.query(Member).filter(Member.community_id == actor.community_id).all()
    amount = to_money(data.amount_per_member)
    target = (
        to_money(data.target_amount)
        if data.target_amount is not None
        else to_money(amount * len(roster))
    )

    collection = Collection(
        community_id=actor.community_id,
        title=data.title.strip(),
        description=data.description,
        amount_per_member=amount,
        target_amount=target,
        deadline=data.deadline,
        budget_allocation=data.budget_allocation,
        custom_fields=(
            [f.model_dump() for f in data.custom_fields] if data.custom_fields else None
        ),
        status=CollectionStatus.ACTIVE,
        share_token=_generate_share_token(db),
        created_by=actor.user_id,
    )
    db.add(collection)
    db.flush()

    db.add_all(
        CollectionEntry(collection_id=collection.id, member_id=m.id, amount_due=amount)
        for m in roster
    )
    db.commit()
    db.refresh(collection)
    return collection


def list_collections(db: Session, community_id: int) -> list[Collection]:
    return (
        db.query(Collection)
        .filter(Collection.community_id == community_id)
        .order_by(Collection.created_at.desc())
        .all()
    )


def _entry_rows(db: Session, collection_id: int) -> list[tuple[CollectionEntry, str]]:
    return (
        db.query(CollectionEntry, Member.display_name)
        .join(Member, CollectionEntry.member_id == Member.id)
        .filter(CollectionEntry.collection_id == collection_id)
        .order_by(Member.display_name)
        .all()
    )


def entry_out(entry: CollectionEntry, display_name: str) -> EntryOut:
    return EntryOut(
        id=entry.id,
        collection_id=entry.collection_id,
        member_id=entry.member_id,
        display_name=display_name,
        amount_due=entry.amount_due,
        status=entry.status,
        paid_at=entry.paid_at,
        note=entry.note,
    )


def detail_out(db: Session, collection: Collection) -> CollectionDetailOut:
    base = CollectionOut.model_validate(collection)
    entries = [entry_out(e, name) for e, name in _entry_rows(db, collection.id)]
    return CollectionDetailOut(**base.model_dump(), entries=entries)


def entry_rollup(
    db: Session, collection_id: int
) -> dict[EntryStatus, tuple[int, Decimal]]:
    """Per-status (count, amount) for one collection, aggregated in SQL.

    One indexed GROUP BY regardless of roster size — dashboards must never
    pull whole entry lists into Python just to count them.
    """
    rows = (
        db.query(
            CollectionEntry.status,
            func.count(CollectionEntry.id),
            func.coalesce(func.sum(CollectionEntry.amount_due), 0),
        )
        .filter(CollectionEntry.collection_id == collection_id)
        .group_by(CollectionEntry.status)
        .all()
    )
    return {status: (n, to_money(total)) for status, n, total in rows}


def active_collection_summaries(
    db: Session, community_id: int
) -> list[ActiveCollectionSummaryOut]:
    """Summaries for every active collection in two queries total (not 2×N)."""
    active = (
        db.query(Collection)
        .filter(
            Collection.community_id == community_id,
            Collection.status == CollectionStatus.ACTIVE,
        )
        .order_by(Collection.created_at.desc())
        .all()
    )
    if not active:
        return []

    collection_ids = [c.id for c in active]

    rows = (
        db.query(
            CollectionEntry.collection_id,
            CollectionEntry.status,
            func.count(CollectionEntry.id),
        )
        .filter(CollectionEntry.collection_id.in_(collection_ids))
        .group_by(CollectionEntry.collection_id, CollectionEntry.status)
        .all()
    )
    counts: dict[int, dict[EntryStatus, int]] = defaultdict(dict)
    for collection_id, status, n in rows:
        counts[collection_id][status] = n

    # Amount collected is sourced from Payment directly (not the entry
    # rollup) since payments no longer have to trace back to a roster entry.
    collected_rows = (
        db.query(Payment.collection_id, func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.collection_id.in_(collection_ids),
            Payment.status == PaymentStatus.PAID,
        )
        .group_by(Payment.collection_id)
        .all()
    )
    collected_by_id = {cid: to_money(total) for cid, total in collected_rows}

    summaries = []
    for collection in active:
        paid_n = counts.get(collection.id, {}).get(EntryStatus.PAID, 0)
        pending_n = counts.get(collection.id, {}).get(EntryStatus.PENDING, 0)
        summaries.append(
            ActiveCollectionSummaryOut(
                id=collection.id,
                title=collection.title,
                target_amount=collection.target_amount,
                amount_collected=collected_by_id.get(collection.id, ZERO),
                paid_count=paid_n,
                pending_count=pending_n,
            )
        )
    return summaries


def dashboard(db: Session, collection: Collection) -> CollectionDashboardOut:
    agg = entry_rollup(db, collection.id)
    paid_n, _ = agg.get(EntryStatus.PAID, (0, ZERO))
    pending_n, outstanding = agg.get(EntryStatus.PENDING, (0, ZERO))
    waived_n, _ = agg.get(EntryStatus.WAIVED, (0, ZERO))
    collected = payments_service.total_collected(db, collection.id)

    percent = 0.0
    if collection.target_amount and collection.target_amount > 0:
        percent = round(float(collected / collection.target_amount * 100), 1)

    return CollectionDashboardOut(
        total_members=paid_n + pending_n + waived_n,
        paid_count=paid_n,
        pending_count=pending_n,
        waived_count=waived_n,
        amount_collected=collected,
        amount_outstanding=outstanding,
        percent_target_reached=percent,
    )


def list_anonymous_payments(db: Session, collection: Collection) -> list[FormResponseOut]:
    """Every paid-and-verified payment on this collection that isn't tied to
    a roster entry (the public share link no longer matches a name) —
    surfaced alongside the roster in the admin's member list, with whatever
    the payer filled in on the post-payment form (if any)."""
    rows = (
        db.query(Payment)
        .filter(
            Payment.collection_id == collection.id,
            Payment.entry_id.is_(None),
            Payment.status == PaymentStatus.PAID,
        )
        .order_by(Payment.paid_at)
        .all()
    )
    return [
        FormResponseOut(
            payment_id=payment.id,
            entry_id=None,
            display_name="Guest",
            amount=payment.amount,
            paid_at=payment.paid_at,
            submitted_at=payment.form_submitted_at,
            values=payment.form_responses or {},
        )
        for payment in rows
    ]


def close_collection(db: Session, actor: Member, collection: Collection) -> Collection:
    if collection.status == CollectionStatus.CLOSED:
        raise ConflictError("Collection is already closed")
    collection.status = CollectionStatus.CLOSED
    audit.log(
        db,
        community_id=collection.community_id,
        actor_user_id=actor.user_id,
        action="collection_closed",
        entity_type="collection",
        entity_id=collection.id,
    )
    db.commit()
    db.refresh(collection)
    return collection


def sync_entries(db: Session, actor: Member, collection: Collection) -> int:
    """Enroll roster members added after the collection was created."""
    enrolled_ids = {
        member_id
        for (member_id,) in db.query(CollectionEntry.member_id).filter(
            CollectionEntry.collection_id == collection.id
        )
    }
    missing = (
        db.query(Member)
        .filter(
            Member.community_id == collection.community_id,
            Member.id.notin_(enrolled_ids) if enrolled_ids else True,
        )
        .all()
    )
    if not missing:
        return 0
    db.add_all(
        CollectionEntry(
            collection_id=collection.id,
            member_id=m.id,
            amount_due=collection.amount_per_member,
        )
        for m in missing
    )
    audit.log(
        db,
        community_id=collection.community_id,
        actor_user_id=actor.user_id,
        action="entries_synced",
        entity_type="collection",
        entity_id=collection.id,
        data={"added": len(missing)},
    )
    db.commit()
    return len(missing)
