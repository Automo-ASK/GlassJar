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
)
from app.schemas.collections import (
    CollectionCreateIn,
    CollectionDashboardOut,
    CollectionDetailOut,
    CollectionOut,
    EntryOut,
)
from app.schemas.reports import ActiveCollectionSummaryOut
from app.services import audit

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

    rows = (
        db.query(
            CollectionEntry.collection_id,
            CollectionEntry.status,
            func.count(CollectionEntry.id),
            func.coalesce(func.sum(CollectionEntry.amount_due), 0),
        )
        .filter(CollectionEntry.collection_id.in_([c.id for c in active]))
        .group_by(CollectionEntry.collection_id, CollectionEntry.status)
        .all()
    )
    rollups: dict[int, dict[EntryStatus, tuple[int, Decimal]]] = defaultdict(dict)
    for collection_id, status, n, total in rows:
        rollups[collection_id][status] = (n, to_money(total))

    summaries = []
    for collection in active:
        agg = rollups.get(collection.id, {})
        paid_n, paid_sum = agg.get(EntryStatus.PAID, (0, ZERO))
        pending_n, _ = agg.get(EntryStatus.PENDING, (0, ZERO))
        summaries.append(
            ActiveCollectionSummaryOut(
                id=collection.id,
                title=collection.title,
                target_amount=collection.target_amount,
                amount_collected=paid_sum,
                paid_count=paid_n,
                pending_count=pending_n,
            )
        )
    return summaries


def dashboard(db: Session, collection: Collection) -> CollectionDashboardOut:
    agg = entry_rollup(db, collection.id)
    paid_n, collected = agg.get(EntryStatus.PAID, (0, ZERO))
    pending_n, outstanding = agg.get(EntryStatus.PENDING, (0, ZERO))
    waived_n, _ = agg.get(EntryStatus.WAIVED, (0, ZERO))

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
