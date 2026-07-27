from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import RevokedToken, User
from app.schemas.auth import LoginIn, RegisterIn


def register(db: Session, data: RegisterIn) -> tuple[User, str]:
    email = data.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise ConflictError("Email already registered")

    user = User(
        email=email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name.strip(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, create_access_token(user.id)


def login(db: Session, data: LoginIn) -> tuple[User, str]:
    user = db.query(User).filter(User.email == data.email.lower()).first()
    if user is None or not verify_password(data.password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")
    return user, create_access_token(user.id)


def logout(db: Session, payload: dict) -> None:
    """Revoke the presented token immediately rather than waiting for expiry."""
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    db.add(RevokedToken(jti=payload["jti"], expires_at=expires_at))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # already revoked — logout is idempotent
