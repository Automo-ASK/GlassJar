from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.enums import ExpenseStatus
from app.schemas.common import Money
from app.schemas.communities import ReservedAccountOut
from app.schemas.expenses import LedgerEntryOut


class TransparencyExpenseOut(BaseModel):
    title: str
    amount: Money
    category: str
    status: ExpenseStatus
    payout_reference: Optional[str] = None
    paid_out_at: Optional[datetime] = None


class TransparencyReportOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    target_amount: Optional[Money] = None
    amount_collected: Money
    paid_count: int
    pending_count: int
    waived_count: int
    budget_allocation: Optional[dict[str, float]] = None
    expenses: list[TransparencyExpenseOut]
    reserved_account: Optional[ReservedAccountOut] = None


class ActiveCollectionSummaryOut(BaseModel):
    id: int
    title: str
    target_amount: Optional[Money] = None
    amount_collected: Money
    paid_count: int
    pending_count: int


class CommunityDashboardOut(BaseModel):
    treasury_balance: Money
    active_collections: list[ActiveCollectionSummaryOut]
    pending_expenses_count: int
    recent_ledger: list[LedgerEntryOut]
