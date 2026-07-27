from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.enums import CollectionStatus, EntryStatus
from app.schemas.common import Money, ORMModel


class CollectionCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    amount_per_member: Decimal = Field(gt=0)
    target_amount: Optional[Decimal] = Field(default=None, ge=0)
    deadline: Optional[datetime] = None
    budget_allocation: Optional[dict[str, float]] = None

    @field_validator("budget_allocation")
    @classmethod
    def allocation_sums_to_100(cls, v):
        if v is not None and abs(sum(v.values()) - 100.0) > 0.01:
            raise ValueError("budget_allocation percentages must sum to 100")
        return v


class CollectionOut(ORMModel):
    id: int
    community_id: int
    title: str
    description: Optional[str] = None
    amount_per_member: Money
    target_amount: Optional[Money] = None
    deadline: Optional[datetime] = None
    budget_allocation: Optional[dict[str, float]] = None
    status: CollectionStatus
    share_token: str
    created_by: int
    created_at: datetime


class EntryOut(ORMModel):
    id: int
    collection_id: int
    member_id: int
    display_name: str
    amount_due: Money
    status: EntryStatus
    paid_at: Optional[datetime] = None
    note: Optional[str] = None


class CollectionDetailOut(CollectionOut):
    entries: list[EntryOut]


class CollectionDashboardOut(BaseModel):
    total_members: int
    paid_count: int
    pending_count: int
    waived_count: int
    amount_collected: Money
    amount_outstanding: Money
    percent_target_reached: float
