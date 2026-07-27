from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_membership, require_community_role
from app.database import get_db
from app.models import Member, MemberRole, User
from app.schemas.communities import (
    CommunityCreateIn,
    CommunityLookupOut,
    CommunityOut,
    JoinIn,
    MemberAddIn,
    MemberBulkAddIn,
    MemberOut,
    ReservedAccountOut,
    RoleChangeIn,
    UnclaimedMemberOut,
)
from app.services import communities as communities_service

router = APIRouter(prefix="/communities", tags=["communities"])

ADMIN_ONLY = [MemberRole.ADMIN]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CommunityOut)
async def create_community(
    body: CommunityCreateIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    community = await communities_service.create_community(db, current_user, body)
    return communities_service.to_community_out(community)


@router.get("/lookup", response_model=CommunityLookupOut)
def lookup(
    invite_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    community, unclaimed = communities_service.lookup_by_invite(db, invite_code)
    return CommunityLookupOut(
        id=community.id,
        name=community.name,
        description=community.description,
        unclaimed_members=[UnclaimedMemberOut.model_validate(m) for m in unclaimed],
    )


@router.post("/join", response_model=MemberOut)
def join(
    body: JoinIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return communities_service.join_community(db, current_user, body)


@router.get("/{community_id}", response_model=CommunityOut)
def get_community(
    community_id: int,
    membership: Member = Depends(get_membership),
    db: Session = Depends(get_db),
):
    community = communities_service.get_community(db, community_id)
    return communities_service.to_community_out(community)


@router.get(
    "/{community_id}/reserved-account", response_model=ReservedAccountOut | None
)
def get_reserved_account(
    community_id: int,
    membership: Member = Depends(get_membership),
    db: Session = Depends(get_db),
):
    community = communities_service.get_community(db, community_id)
    return communities_service.to_community_out(community).reserved_account


@router.post(
    "/{community_id}/reserved-account",
    status_code=status.HTTP_201_CREATED,
    response_model=ReservedAccountOut,
)
async def setup_reserved_account(
    community_id: int,
    membership: Member = Depends(require_community_role(ADMIN_ONLY)),
    db: Session = Depends(get_db),
):
    community = communities_service.get_community(db, community_id)
    community = await communities_service.setup_reserved_account(
        db, membership, community
    )
    return communities_service.to_community_out(community).reserved_account


@router.get("/{community_id}/members", response_model=list[MemberOut])
def list_members(
    community_id: int,
    membership: Member = Depends(get_membership),
    db: Session = Depends(get_db),
):
    return communities_service.list_members(db, community_id)


@router.post(
    "/{community_id}/members",
    status_code=status.HTTP_201_CREATED,
    response_model=MemberOut,
)
def add_member(
    community_id: int,
    body: MemberAddIn,
    membership: Member = Depends(require_community_role(ADMIN_ONLY)),
    db: Session = Depends(get_db),
):
    return communities_service.add_member(db, membership, body)


@router.post(
    "/{community_id}/members/bulk",
    status_code=status.HTTP_201_CREATED,
    response_model=list[MemberOut],
)
def add_members_bulk(
    community_id: int,
    body: MemberBulkAddIn,
    membership: Member = Depends(require_community_role(ADMIN_ONLY)),
    db: Session = Depends(get_db),
):
    return communities_service.add_members_bulk(db, membership, body.members)


@router.patch("/{community_id}/members/{member_id}/role", response_model=MemberOut)
def change_member_role(
    community_id: int,
    member_id: int,
    body: RoleChangeIn,
    membership: Member = Depends(require_community_role(ADMIN_ONLY)),
    db: Session = Depends(get_db),
):
    return communities_service.change_role(db, membership, member_id, body.role)


@router.delete(
    "/{community_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_member(
    community_id: int,
    member_id: int,
    membership: Member = Depends(require_community_role(ADMIN_ONLY)),
    db: Session = Depends(get_db),
):
    communities_service.remove_member(db, membership, member_id)
