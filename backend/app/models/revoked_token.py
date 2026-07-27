from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RevokedToken(Base):
    """JWTs killed before their natural expiry (e.g. via /auth/logout).

    `expires_at` mirrors the token's own exp claim so a cleanup job can prune
    rows once the token would have expired anyway.
    """

    __tablename__ = "revoked_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
