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
    # Transfer-to-this-account instructions — the payer completes payment by
    # transferring directly, no hosted checkout redirect.
    va_account_number: Optional[str] = None
    va_bank_name: Optional[str] = None
    va_expires_at: Optional[datetime] = None
    # The exact amount to transfer — may differ from `amount` due to gateway
    # fees; sending anything else can get silently bounced by the bank.
    va_amount: Optional[Money] = None


class PaymentFormIn(BaseModel):
    values: dict[str, str | bool]
