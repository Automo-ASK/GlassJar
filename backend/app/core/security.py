from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
import jwt

from app.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


def create_access_token(subject: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return jwt.encode(
        {"sub": str(subject), "exp": expire, "jti": uuid4().hex},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def decode_token(token: str) -> dict | None:
    """Return the decoded payload (sub, exp, jti) or None if invalid/expired.

    Revocation is checked at the dependency layer, where a DB session is
    available — see app.core.deps.get_token_payload.
    """
    try:
        return jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
    except jwt.PyJWTError:
        return None
