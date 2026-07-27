from typing import Optional

from pydantic import BaseModel, EmailStr, Field, computed_field

from app.models.enums import MemberRole
from app.schemas.common import ORMModel


class CommunityCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None


class ReservedAccountOut(BaseModel):
    bank_name: str
    account_number: str
    account_name: str
    status: str


class CommunityOut(ORMModel):
    id: int
    name: str
    description: Optional[str] = None
    invite_code: str
    created_by: int
    reserved_account: Optional[ReservedAccountOut] = None


class ReservedAccountSetupIn(BaseModel):
    bvn: str = Field(min_length=11, max_length=11, pattern=r"^\d{11}$")


class JoinIn(BaseModel):
    invite_code: str
    claim_member_id: Optional[int] = None


class UnclaimedMemberOut(ORMModel):
    id: int
    display_name: str


class CommunityLookupOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    unclaimed_members: list[UnclaimedMemberOut]


class MemberAddIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=32)


class MemberBulkAddIn(BaseModel):
    members: list[MemberAddIn] = Field(min_length=1, max_length=500)


class MemberOut(ORMModel):
    id: int
    community_id: int
    user_id: Optional[int] = None
    display_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: MemberRole

    @computed_field
    @property
    def is_claimed(self) -> bool:
        return self.user_id is not None


class RoleChangeIn(BaseModel):
    role: MemberRole
