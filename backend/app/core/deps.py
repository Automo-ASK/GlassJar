from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models import Collection, Expense, Member, MemberRole, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

_credentials_exc = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    user_id = decode_access_token(token)
    if user_id is None:
        raise _credentials_exc
    user = db.get(User, user_id)
    if user is None:
        raise _credentials_exc
    return user


def _membership_or_403(db: Session, community_id: int, user_id: int) -> Member:
    membership = (
        db.query(Member)
        .filter(Member.community_id == community_id, Member.user_id == user_id)
        .first()
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a community member"
        )
    return membership


def get_membership(
    community_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Member:
    return _membership_or_403(db, community_id, current_user.id)


def require_community_role(allowed_roles: list[MemberRole]):
    def dependency(membership: Member = Depends(get_membership)) -> Member:
        assert_role(membership, allowed_roles)
        return membership

    return dependency


def assert_role(membership: Member, allowed_roles: list[MemberRole]) -> None:
    if membership.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


def get_collection_context(
    collection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> tuple[Collection, Member]:
    """Resolve a collection-scoped route to (collection, caller's membership)."""
    collection = db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    membership = _membership_or_403(db, collection.community_id, current_user.id)
    return collection, membership


def get_expense_context(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> tuple[Expense, Member]:
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    membership = _membership_or_403(db, expense.community_id, current_user.id)
    return expense, membership
