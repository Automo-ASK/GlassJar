from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import LedgerEntryType, db_enum


class LedgerEntry(Base):
    """Append-only record of money in/out of a community treasury.

    The unique reference constraint means one source event (a payment, an
    expense payout, a webhook transfer) can post at most one credit and one
    debit — double-posting fails at the database, never silently.
    """

    __tablename__ = "ledger_entries"
    __table_args__ = (
        UniqueConstraint(
            "reference_type", "reference_id", "type", name="uq_ledger_reference"
        ),
        CheckConstraint("amount >= 0", name="ck_ledger_amount_positive"),
        # Serves both balance SUMs (community_id prefix) and the
        # recent-ledger listing without a sort step.
        Index("ix_ledger_community_created", "community_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    community_id: Mapped[int] = mapped_column(ForeignKey("communities.id"))
    type: Mapped[LedgerEntryType] = mapped_column(db_enum(LedgerEntryType))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    reference_type: Mapped[str] = mapped_column(String(64))
    reference_id: Mapped[int] = mapped_column(Integer)
    description: Mapped[Optional[str]] = mapped_column(Text, default="")
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
