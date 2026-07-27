import secrets
from typing import Optional

from sqlalchemy.orm import Session

from app.core.errors import (
    ConflictError,
    GatewayError,
    InvalidInputError,
    NotFoundError,
)
from app.models import (
    CollectionEntry,
    Community,
    Member,
    MemberRole,
    User,
)
from app.schemas.communities import (
    CommunityCreateIn,
    CommunityOut,
    JoinIn,
    MemberAddIn,
    ReservedAccountOut,
)
from app.services import audit
from app.services.monnify import MonnifyError, monnify_service


def _generate_invite_code(db: Session) -> str:
    while True:
        code = secrets.token_urlsafe(6)[:8].lower()
        if not db.query(Community).filter(Community.invite_code == code).first():
            return code


def to_community_out(community: Community) -> CommunityOut:
    reserved = None
    if community.reserved_account_number:
        reserved = ReservedAccountOut(
            bank_name=community.reserved_bank_name or "",
            account_number=community.reserved_account_number,
            account_name=community.reserved_account_name or "",
            status=community.reserved_account_status or "pending",
        )
    return CommunityOut(
        id=community.id,
        name=community.name,
        description=community.description,
        invite_code=community.invite_code,
        created_by=community.created_by,
        reserved_account=reserved,
    )


def get_community(db: Session, community_id: int) -> Community:
    community = db.get(Community, community_id)
    if community is None:
        raise NotFoundError("Community not found")
    return community


def create_community(db: Session, user: User, data: CommunityCreateIn) -> Community:
    community = Community(
        name=data.name.strip(),
        description=data.description,
        invite_code=_generate_invite_code(db),
        created_by=user.id,
    )
    db.add(community)
    db.flush()

    creator = Member(
        community_id=community.id,
        user_id=user.id,
        display_name=user.full_name,
        email=user.email,
        role=MemberRole.ADMIN,
        added_by=user.id,
    )
    db.add(creator)
    db.commit()
    db.refresh(community)
    return community


def lookup_by_invite(db: Session, invite_code: str) -> tuple[Community, list[Member]]:
    community = (
        db.query(Community).filter(Community.invite_code == invite_code.lower()).first()
    )
    if community is None:
        raise NotFoundError("Invalid invite code")
    unclaimed = (
        db.query(Member)
        .filter(Member.community_id == community.id, Member.user_id.is_(None))
        .order_by(Member.display_name)
        .all()
    )
    return community, unclaimed


def join_community(db: Session, user: User, data: JoinIn) -> Member:
    community, _ = lookup_by_invite(db, data.invite_code)

    existing = (
        db.query(Member)
        .filter(Member.community_id == community.id, Member.user_id == user.id)
        .first()
    )
    if existing:
        raise ConflictError("Already a member of this community")

    member: Optional[Member] = None
    if data.claim_member_id is not None:
        member = db.get(Member, data.claim_member_id)
        if member is None or member.community_id != community.id:
            raise NotFoundError("Roster entry not found in this community")
        if member.user_id is not None:
            raise ConflictError("That roster entry is already claimed")
    else:
        # Auto-claim a roster entry the rep created with this user's email.
        member = (
            db.query(Member)
            .filter(
                Member.community_id == community.id,
                Member.user_id.is_(None),
                Member.email == user.email,
            )
            .first()
        )

    if member is not None:
        member.user_id = user.id
        if not member.email:
            member.email = user.email
        action = "member_claimed"
    else:
        member = Member(
            community_id=community.id,
            user_id=user.id,
            display_name=user.full_name,
            email=user.email,
            role=MemberRole.MEMBER,
        )
        db.add(member)
        action = "member_joined"

    db.flush()
    audit.log(
        db,
        community_id=community.id,
        actor_user_id=user.id,
        action=action,
        entity_type="member",
        entity_id=member.id,
    )
    db.commit()
    db.refresh(member)
    return member


def list_members(db: Session, community_id: int) -> list[Member]:
    return (
        db.query(Member)
        .filter(Member.community_id == community_id)
        .order_by(Member.display_name)
        .all()
    )


def add_member(db: Session, actor: Member, data: MemberAddIn) -> Member:
    member = Member(
        community_id=actor.community_id,
        display_name=data.display_name.strip(),
        email=data.email.lower() if data.email else None,
        phone=data.phone,
        added_by=actor.user_id,
    )
    db.add(member)
    db.flush()
    audit.log(
        db,
        community_id=actor.community_id,
        actor_user_id=actor.user_id,
        action="member_added",
        entity_type="member",
        entity_id=member.id,
    )
    db.commit()
    db.refresh(member)
    return member


def add_members_bulk(
    db: Session, actor: Member, items: list[MemberAddIn]
) -> list[Member]:
    members = [
        Member(
            community_id=actor.community_id,
            display_name=item.display_name.strip(),
            email=item.email.lower() if item.email else None,
            phone=item.phone,
            added_by=actor.user_id,
        )
        for item in items
    ]
    db.add_all(members)
    db.flush()
    audit.log(
        db,
        community_id=actor.community_id,
        actor_user_id=actor.user_id,
        action="members_bulk_added",
        entity_type="member",
        data={"count": len(members)},
    )
    db.commit()
    for m in members:
        db.refresh(m)
    return members


def _get_member_in_community(db: Session, community_id: int, member_id: int) -> Member:
    member = db.get(Member, member_id)
    if member is None or member.community_id != community_id:
        raise NotFoundError("Member not found")
    return member


def _other_admin_exists(db: Session, community_id: int, member_id: int) -> bool:
    return (
        db.query(Member)
        .filter(
            Member.community_id == community_id,
            Member.role == MemberRole.ADMIN,
            Member.id != member_id,
        )
        .first()
        is not None
    )


def change_role(
    db: Session, actor: Member, member_id: int, new_role: MemberRole
) -> Member:
    target = _get_member_in_community(db, actor.community_id, member_id)
    if target.id == actor.id:
        raise InvalidInputError("You cannot change your own role")
    if new_role != MemberRole.MEMBER and target.user_id is None:
        raise InvalidInputError(
            "Only claimed members (with an account) can hold governance roles"
        )
    if target.role == MemberRole.ADMIN and new_role != MemberRole.ADMIN:
        if not _other_admin_exists(db, actor.community_id, target.id):
            raise InvalidInputError("Community must keep at least one admin")

    previous = target.role
    target.role = new_role
    audit.log(
        db,
        community_id=actor.community_id,
        actor_user_id=actor.user_id,
        action="role_changed",
        entity_type="member",
        entity_id=target.id,
        data={"from": previous.value, "to": new_role.value},
    )
    db.commit()
    db.refresh(target)
    return target


def remove_member(db: Session, actor: Member, member_id: int) -> None:
    target = _get_member_in_community(db, actor.community_id, member_id)
    if target.id == actor.id:
        raise InvalidInputError("You cannot remove yourself")
    has_entries = (
        db.query(CollectionEntry)
        .filter(CollectionEntry.member_id == target.id)
        .first()
        is not None
    )
    if has_entries:
        raise ConflictError(
            "Member has collection history and cannot be removed; waive their entries instead"
        )
    if target.role == MemberRole.ADMIN and not _other_admin_exists(
        db, actor.community_id, target.id
    ):
        raise InvalidInputError("Community must keep at least one admin")

    audit.log(
        db,
        community_id=actor.community_id,
        actor_user_id=actor.user_id,
        action="member_removed",
        entity_type="member",
        entity_id=target.id,
        data={"display_name": target.display_name},
    )
    db.delete(target)
    db.commit()


def list_user_communities(db: Session, user: User) -> list[Community]:
    return (
        db.query(Community)
        .join(Member, Member.community_id == Community.id)
        .filter(Member.user_id == user.id)
        .order_by(Community.created_at.desc())
        .all()
    )


async def setup_reserved_account(
    db: Session, actor: Member, community: Community, bvn: str, admin_name: str
) -> Community:
    if community.reserved_account_status == "active":
        raise ConflictError("Reserved account is already set up")

    try:
        result = await monnify_service.create_reserved_account(
            community_id=community.id,
            community_name=community.name,
            admin_name=admin_name,
            bvn=bvn,
        )
    except MonnifyError as e:
        community.reserved_account_status = "failed"
        db.commit()
        raise GatewayError(f"Reserved account setup failed: {e.message}")

    community.reserved_account_reference = result["account_reference"]
    community.reserved_account_number = result["account_number"]
    community.reserved_bank_name = result["bank_name"]
    community.reserved_account_name = result["account_name"]
    community.reserved_account_status = result["status"]
    audit.log(
        db,
        community_id=community.id,
        actor_user_id=actor.user_id,
        action="reserved_account_created",
        entity_type="community",
        entity_id=community.id,
    )
    db.commit()
    db.refresh(community)
    return community
