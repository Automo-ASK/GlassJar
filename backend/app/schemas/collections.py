from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import CollectionStatus, EntryStatus
from app.schemas.common import Money, ORMModel

CustomFieldType = Literal["text", "number", "phone", "email", "select", "checkbox"]


class CustomFieldDef(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=120)
    type: CustomFieldType
    required: bool = False
    options: Optional[list[str]] = None

    @model_validator(mode="after")
    def select_needs_options(self):
        if self.type == "select" and not self.options:
            raise ValueError("select fields must define at least one option")
        return self


class CollectionCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    amount_per_member: Decimal = Field(gt=0)
    target_amount: Optional[Decimal] = Field(default=None, ge=0)
    deadline: Optional[datetime] = None
    budget_allocation: Optional[dict[str, float]] = None
    custom_fields: Optional[list[CustomFieldDef]] = None

    @field_validator("deadline")
    @classmethod
    def deadline_not_in_past(cls, v):
        if v is not None and v.date() < datetime.now(timezone.utc).date():
            raise ValueError("deadline cannot be in the past")
        return v

    @field_validator("budget_allocation")
    @classmethod
    def allocation_sums_to_100(cls, v):
        if v is not None and abs(sum(v.values()) - 100.0) > 0.01:
            raise ValueError("budget_allocation percentages must sum to 100")
        return v

    @field_validator("custom_fields")
    @classmethod
    def field_keys_unique(cls, v):
        if v is not None:
            keys = [f.key for f in v]
            if len(keys) != len(set(keys)):
                raise ValueError("custom_fields keys must be unique")
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
    custom_fields: Optional[list[CustomFieldDef]] = None
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


class FormResponseOut(BaseModel):
    payment_id: int
    entry_id: Optional[int] = None
    display_name: str
    amount: Money
    paid_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    values: dict


class CollectionResponsesOut(BaseModel):
    custom_fields: list[CustomFieldDef]
    responses: list[FormResponseOut]
