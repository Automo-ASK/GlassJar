from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import CollectionStatus, EntryStatus, db_enum


class Collection(Base):
    __tablename__ = "collections"
    __table_args__ = (
        CheckConstraint("amount_per_member >= 0", name="ck_collections_amount_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    community_id: Mapped[int] = mapped_column(ForeignKey("communities.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    amount_per_member: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    target_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    budget_allocation: Mapped[Optional[dict]] = mapped_column(JSON)
    status: Mapped[CollectionStatus] = mapped_column(
        db_enum(CollectionStatus), default=CollectionStatus.ACTIVE
    )
    share_token: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    entries: Mapped[list["CollectionEntry"]] = relationship(
        back_populates="collection", cascade="all, delete-orphan"
    )


class CollectionEntry(Base):
    """One roster member's slot in one collection: what they owe and whether
    they've paid. Manual actions (mark paid, waive) record who did it and why."""

    __tablename__ = "collection_entries"
    __table_args__ = (
        UniqueConstraint("collection_id", "member_id", name="uq_entry_collection_member"),
        CheckConstraint("amount_due >= 0", name="ck_entries_amount_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("collections.id"), index=True
    )
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), index=True)
    amount_due: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[EntryStatus] = mapped_column(
        db_enum(EntryStatus), default=EntryStatus.PENDING
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    note: Mapped[Optional[str]] = mapped_column(Text)
    marked_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))

    collection: Mapped[Collection] = relationship(back_populates="entries")
    member: Mapped["Member"] = relationship()  # noqa: F821
