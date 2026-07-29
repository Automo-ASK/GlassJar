from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from app.models.enums import PaymentChannel, PaymentStatus
from app.schemas.common import Money, ORMModel


class PayInitIn(BaseModel):
    redirect_url: str


class PayInitOut(BaseModel):
    payment_reference: str
    # Transfer-to-this-account instructions — replaces the old hosted
    # checkout redirect. checkout_url stays for schema compatibility but is
    # unused under the Flutterwave virtual-account rail.
    checkout_url: Optional[str] = None
    va_account_number: Optional[str] = None
    va_bank_name: Optional[str] = None
    va_expires_at: Optional[datetime] = None
    # The exact amount to transfer — may differ from the collection amount
    # due to gateway fees; sending anything else can get bounced by the bank.
    va_amount: Optional[Money] = None


class PaymentOut(ORMModel):
    id: int
    collection_id: int
    entry_id: Optional[int] = None
    member_id: Optional[int] = None
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
