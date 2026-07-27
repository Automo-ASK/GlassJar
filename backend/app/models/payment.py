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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import PaymentChannel, PaymentStatus, db_enum


class Payment(Base):
    """A money-in attempt against a collection entry.

    Monnify checkouts and manual marks (cash / off-platform transfer) both
    create a Payment so every credit in the ledger traces back to one row.
    """

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_payments_amount_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id"), index=True)
    entry_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("collection_entries.id"), index=True
    )
    member_id: Mapped[Optional[int]] = mapped_column(ForeignKey("members.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    channel: Mapped[PaymentChannel] = mapped_column(
        db_enum(PaymentChannel), default=PaymentChannel.CHECKOUT
    )
    payment_reference: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    monnify_transaction_reference: Mapped[Optional[str]] = mapped_column(String(128))
    status: Mapped[PaymentStatus] = mapped_column(
        db_enum(PaymentStatus), default=PaymentStatus.PENDING
    )
    checkout_url: Mapped[Optional[str]] = mapped_column(Text)
    payer_email: Mapped[Optional[str]] = mapped_column(String(255))
    raw_verification_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    form_responses: Mapped[Optional[dict]] = mapped_column(JSON)
    form_submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    recorded_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    entry: Mapped[Optional["CollectionEntry"]] = relationship()  # noqa: F821


class WebhookEvent(Base):
    """Dedupe log of gateway webhook deliveries. `event_key` is unique, so a
    redelivered event is acknowledged without being processed twice."""

    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), default="monnify")
    event_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSON)
    outcome: Mapped[str] = mapped_column(String(64), default="received")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
