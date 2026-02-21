"""
User Domain Models.
Contains User, Role, Permission, and Auth Tokens.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship, SQLModel

from app.core.domain.common import CaseInsensitiveEnum, FlexibleEnum, utc_now
from app.security.passwords import pwd_context

if TYPE_CHECKING:
    from app.core.domain.audit import AuditLog
    from app.core.domain.chat import AdminConversation, CustomerConversation
    from app.core.domain.mission import Mission


class UserStatus(CaseInsensitiveEnum):
    """User Lifecycle Status."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    DISABLED = "disabled"


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: int | None = Field(default=None, primary_key=True)
    external_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), unique=True, nullable=True),
    )
    full_name: str = Field(max_length=150)
    email: str = Field(max_length=150, unique=True, index=True)
    password_hash: str | None = Field(default=None, max_length=256)
    is_admin: bool = Field(default=False)
    is_active: bool = Field(default=True)
    status: UserStatus = Field(
        sa_column=Column(FlexibleEnum(UserStatus), default=UserStatus.ACTIVE),
        default=UserStatus.ACTIVE,
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    )

    # Relationships
    admin_conversations: list[AdminConversation] = Relationship(
        sa_relationship=relationship("AdminConversation", back_populates="user")
    )
    customer_conversations: list[CustomerConversation] = Relationship(
        sa_relationship=relationship("CustomerConversation", back_populates="user")
    )
    missions: list[Mission] = Relationship(
        sa_relationship=relationship("Mission", back_populates="initiator")
    )
    roles: list[Role] = Relationship(
        back_populates="users",
        link_model="UserRole",  # type: ignore[arg-type]
        sa_relationship=relationship(
            "app.core.domain.user.Role", secondary="user_roles", back_populates="users"
        ),
    )
    refresh_tokens: list[RefreshToken] = Relationship(
        sa_relationship=relationship("RefreshToken", back_populates="user"),
    )
    password_reset_tokens: list[PasswordResetToken] = Relationship(
        sa_relationship=relationship("PasswordResetToken", back_populates="user"),
    )
    audit_logs: list[AuditLog] = Relationship(
        sa_relationship=relationship("AuditLog", back_populates="actor"),
    )

    def set_password(self, password: str) -> None:
        self.password_hash = pwd_context.hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return pwd_context.verify(password, self.password_hash)

    def verify_password(self, password: str) -> bool:
        return self.check_password(password)

    def __repr__(self):
        return f"<User id={self.id} email={self.email}>"


class Role(SQLModel, table=True):
    __tablename__ = "roles"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, sa_column=Column(String(100), unique=True))
    description: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    )

    users: list[User] = Relationship(
        back_populates="roles",
        link_model="UserRole",  # type: ignore[arg-type]
        sa_relationship=relationship(
            "app.core.domain.user.User", secondary="user_roles", back_populates="roles"
        ),
    )
    permissions: list[Permission] = Relationship(
        back_populates="roles",
        link_model="RolePermission",  # type: ignore[arg-type]
        sa_relationship=relationship(
            "app.core.domain.user.Permission",
            secondary="role_permissions",
            back_populates="roles",
        ),
    )


class Permission(SQLModel, table=True):
    __tablename__ = "permissions"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, sa_column=Column(String(100), unique=True))
    description: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    )

    roles: list[Role] = Relationship(
        back_populates="permissions",
        link_model="RolePermission",  # type: ignore[arg-type]
        sa_relationship=relationship(
            "app.core.domain.user.Role",
            secondary="role_permissions",
            back_populates="permissions",
        ),
    )


class UserRole(SQLModel, table=True):
    __tablename__ = "user_roles"

    user_id: int = Field(foreign_key="users.id", primary_key=True, index=True)
    role_id: int = Field(foreign_key="roles.id", primary_key=True, index=True)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )


class RolePermission(SQLModel, table=True):
    __tablename__ = "role_permissions"

    role_id: int = Field(foreign_key="roles.id", primary_key=True, index=True)
    permission_id: int = Field(foreign_key="permissions.id", primary_key=True, index=True)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )


from app.core.domain.audit import AuditLog as _AuditLog

_ = _AuditLog


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"

    id: int | None = Field(default=None, primary_key=True)
    token_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), unique=True, nullable=False),
    )
    family_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), index=True, nullable=False),
    )
    user_id: int = Field(foreign_key="users.id", index=True)
    hashed_token: str = Field(max_length=255)
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), index=True))
    revoked_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    replaced_by_token_id: str | None = Field(
        default=None, sa_column=Column(String(36), nullable=True, index=True)
    )
    created_ip: str | None = Field(default=None, max_length=64)
    user_agent: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )

    user: User = Relationship(
        sa_relationship=relationship("app.core.domain.user.User", back_populates="refresh_tokens")
    )

    def revoke(self, *, revoked_at: datetime | None = None, replaced_by: str | None = None) -> None:
        self.revoked_at = revoked_at or utc_now()
        self.replaced_by_token_id = replaced_by

    def is_active(self, *, now: datetime | None = None) -> bool:
        current_time = now or utc_now()
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=UTC)

        expiry = self.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=UTC)

        return self.revoked_at is None and current_time < expiry


class PasswordResetToken(SQLModel, table=True):
    __tablename__ = "password_resets"

    id: int | None = Field(default=None, primary_key=True)
    token_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), unique=True, nullable=False),
    )
    hashed_token: str = Field(max_length=255, sa_column=Column(String(255), unique=True))
    user_id: int = Field(foreign_key="users.id", index=True)
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), index=True))
    redeemed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    requested_ip: str | None = Field(default=None, max_length=64)
    user_agent: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )

    user: User = Relationship(
        sa_relationship=relationship(
            "app.core.domain.user.User", back_populates="password_reset_tokens"
        )
    )

    def is_active(self, *, now: datetime | None = None) -> bool:
        moment = now or utc_now()
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=UTC)
        expiry = self.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=UTC)
        if self.redeemed_at and self.redeemed_at.tzinfo is None:
            self.redeemed_at = self.redeemed_at.replace(tzinfo=UTC)
        return self.redeemed_at is None and moment < expiry

    def mark_redeemed(self, *, redeemed_at: datetime | None = None) -> None:
        self.redeemed_at = redeemed_at or utc_now()
