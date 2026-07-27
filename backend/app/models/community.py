from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import MemberRole, db_enum


class Community(Base):
    __tablename__ = "communities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    invite_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    reserved_account_reference: Mapped[Optional[str]] = mapped_column(String(64))
    reserved_account_number: Mapped[Optional[str]] = mapped_column(String(32))
    reserved_bank_name: Mapped[Optional[str]] = mapped_column(String(128))
    reserved_account_name: Mapped[Optional[str]] = mapped_column(String(255))
    reserved_account_status: Mapped[Optional[str]] = mapped_column(String(16))

    members: Mapped[list["Member"]] = relationship(
        back_populates="community", cascade="all, delete-orphan"
    )


class Member(Base):
    """A roster entry in a community.

    `user_id` is nullable: members added by name exist before (or without)
    ever creating an account. Claiming links a User to the row. Governance
    roles are only meaningful on claimed rows.
    """

    __tablename__ = "members"
    __table_args__ = (
        Index(
            "uq_members_community_user",
            "community_id",
            "user_id",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
            sqlite_where=text("user_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    community_id: Mapped[int] = mapped_column(
        ForeignKey("communities.id"), index=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(32))
    role: Mapped[MemberRole] = mapped_column(
        db_enum(MemberRole), default=MemberRole.MEMBER
    )
    added_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    community: Mapped[Community] = relationship(back_populates="members")
    user: Mapped[Optional["User"]] = relationship(  # noqa: F821
        back_populates="memberships", foreign_keys=[user_id]
    )
