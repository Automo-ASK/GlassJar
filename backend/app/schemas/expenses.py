from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import ExpenseStatus, LedgerEntryType
from app.schemas.common import Money, ORMModel


class ExpenseCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(gt=0)
    category: str = Field(min_length=1, max_length=64)
    collection_id: Optional[int] = None
    receipt_url: Optional[str] = None
    destination_bank_name: Optional[str] = None
    destination_account_number: Optional[str] = None
    destination_account_name: Optional[str] = None


class ExpenseOut(ORMModel):
    id: int
    community_id: int
    collection_id: Optional[int] = None
    title: str
    amount: Money
    category: str
    status: ExpenseStatus
    receipt_url: Optional[str] = None
    requested_by: int
    approved_by: Optional[int] = None
    decision_note: Optional[str] = None
    created_at: datetime
    decided_at: Optional[datetime] = None
    destination_bank_name: Optional[str] = None
    destination_account_number: Optional[str] = None
    destination_account_name: Optional[str] = None
    payout_reference: Optional[str] = None
    paid_out_at: Optional[datetime] = None
    paid_out_by: Optional[int] = None


class DecisionIn(BaseModel):
    note: Optional[str] = None


class MarkPaidOutIn(BaseModel):
    payout_reference: str = Field(min_length=1, max_length=128)


class LedgerEntryOut(ORMModel):
    id: int
    type: LedgerEntryType
    amount: Money
    reference_type: str
    reference_id: int
    description: Optional[str] = None
    created_at: datetime


class LedgerResponse(BaseModel):
    entries: list[LedgerEntryOut]
    balance: Money
    total: int
