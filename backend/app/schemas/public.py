from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from app.models.enums import CollectionStatus, PaymentStatus
from app.schemas.collections import CustomFieldDef
from app.schemas.common import Money


class PublicCollectionOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    community_name: str
    amount_per_member: Money
    target_amount: Optional[Money] = None
    amount_collected: Money
    deadline: Optional[datetime] = None
    status: CollectionStatus
    custom_fields: Optional[list[CustomFieldDef]] = None


class GuestPayIn(BaseModel):
    redirect_url: str
    payer_email: Optional[EmailStr] = None


class PublicPaymentOut(BaseModel):
    payment_reference: str
    status: PaymentStatus
    amount: Money
    paid_at: Optional[datetime] = None
    custom_fields: Optional[list[CustomFieldDef]] = None
    form_submitted: bool = False


class PaymentFormIn(BaseModel):
    values: dict[str, str | bool]
