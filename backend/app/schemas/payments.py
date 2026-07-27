from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from app.models.enums import PaymentChannel, PaymentStatus
from app.schemas.common import Money, ORMModel


class PayInitIn(BaseModel):
    redirect_url: str


class PayInitOut(BaseModel):
    checkout_url: str
    payment_reference: str


class PaymentOut(ORMModel):
    id: int
    collection_id: int
    entry_id: int
    member_id: int
    amount: Money
    channel: PaymentChannel
    payment_reference: str
    monnify_transaction_reference: Optional[str] = None
    status: PaymentStatus
    checkout_url: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: datetime


class ManualMarkIn(BaseModel):
    channel: PaymentChannel
    note: Optional[str] = None

    @field_validator("channel")
    @classmethod
    def must_be_manual(cls, v: PaymentChannel) -> PaymentChannel:
        if v == PaymentChannel.CHECKOUT:
            raise ValueError("manual marks must use manual_cash or manual_transfer")
        return v


class NoteIn(BaseModel):
    note: Optional[str] = None
