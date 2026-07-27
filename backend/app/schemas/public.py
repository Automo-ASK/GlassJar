from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from app.models.enums import CollectionStatus, EntryStatus, PaymentStatus
from app.schemas.common import Money, ORMModel


class PublicEntryOut(ORMModel):
    id: int
    display_name: str
    status: EntryStatus


class PublicCollectionOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    community_name: str
    amount_per_member: Money
    deadline: Optional[datetime] = None
    status: CollectionStatus
    entries: list[PublicEntryOut]


class GuestPayIn(BaseModel):
    redirect_url: str
    payer_email: Optional[EmailStr] = None


class PublicPaymentOut(BaseModel):
    payment_reference: str
    status: PaymentStatus
    amount: Money
    paid_at: Optional[datetime] = None
