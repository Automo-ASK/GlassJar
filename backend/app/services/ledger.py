from decimal import Decimal
from typing import Optional

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.money import to_money
from app.models import LedgerEntry, LedgerEntryType


def record_credit(
    db: Session,
    *,
    community_id: int,
    amount: Decimal,
    reference_type: str,
    reference_id: int,
    description: str = "",
    raw_payload: Optional[dict] = None,
) -> LedgerEntry:
    """Stage a credit. No commit here — the calling service commits so the
    ledger entry is atomic with the state change that caused it."""
    entry = LedgerEntry(
        community_id=community_id,
        type=LedgerEntryType.CREDIT,
        amount=to_money(amount),
        reference_type=reference_type,
        reference_id=reference_id,
        description=description,
        raw_payload=raw_payload,
    )
    db.add(entry)
    return entry


def record_debit(
    db: Session,
    *,
    community_id: int,
    amount: Decimal,
    reference_type: str,
    reference_id: int,
    description: str = "",
) -> LedgerEntry:
    entry = LedgerEntry(
        community_id=community_id,
        type=LedgerEntryType.DEBIT,
        amount=to_money(amount),
        reference_type=reference_type,
        reference_id=reference_id,
        description=description,
    )
    db.add(entry)
    return entry


def get_balance(db: Session, community_id: int) -> Decimal:
    signed = func.coalesce(
        func.sum(
            case(
                (LedgerEntry.type == LedgerEntryType.CREDIT, LedgerEntry.amount),
                else_=-LedgerEntry.amount,
            )
        ),
        0,
    )
    value = (
        db.query(signed).filter(LedgerEntry.community_id == community_id).scalar()
    )
    return to_money(value or 0)


def list_entries(
    db: Session, community_id: int, skip: int = 0, limit: int = 20
) -> tuple[list[LedgerEntry], int]:
    query = db.query(LedgerEntry).filter(LedgerEntry.community_id == community_id)
    total = query.count()
    entries = (
        query.order_by(LedgerEntry.created_at.desc(), LedgerEntry.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return entries, total
