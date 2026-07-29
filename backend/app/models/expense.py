from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import ExpenseStatus, db_enum


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_expenses_amount_positive"),
        # Dashboards count pending expenses per community on every load.
        Index("ix_expenses_community_status", "community_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    community_id: Mapped[int] = mapped_column(ForeignKey("communities.id"))
    collection_id: Mapped[Optional[int]] = mapped_column(ForeignKey("collections.id"))
    title: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    category: Mapped[str] = mapped_column(String(64))
    receipt_url: Mapped[Optional[str]] = mapped_column(Text)
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[ExpenseStatus] = mapped_column(
        db_enum(ExpenseStatus), default=ExpenseStatus.PENDING
    )
    approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    decision_note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    destination_bank_name: Mapped[Optional[str]] = mapped_column(String(128))
    destination_bank_code: Mapped[Optional[str]] = mapped_column(String(16))
    destination_account_number: Mapped[Optional[str]] = mapped_column(String(32))
    destination_account_name: Mapped[Optional[str]] = mapped_column(String(255))
    payout_reference: Mapped[Optional[str]] = mapped_column(String(128))
    flw_transfer_id: Mapped[Optional[str]] = mapped_column(String(64))
    payout_error: Mapped[Optional[str]] = mapped_column(Text)
    raw_payout_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    manual_payout: Mapped[bool] = mapped_column(Boolean, default=False)
    paid_out_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    paid_out_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
