from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum, StrEnum

from sqlalchemy import JSON, Column, DateTime, String, func
from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship, SQLModel


def utc_now():
    return datetime.utcnow()


class CaseInsensitiveEnum(StrEnum):
    """Case insensitive enum mixin."""

    @classmethod
    def _missing_(cls, value):
        for member in cls:
            if member.value.lower() == value.lower():
                return member
        return None


class FlexibleEnum(Enum):
    pass


class UserStatus(CaseInsensitiveEnum):
    """User Lifecycle Status."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    DISABLED = "disabled"


class MicroUserRole(SQLModel, table=True):
    __tablename__ = "user_roles"
    __table_args__ = {"extend_existing": True}
    user_id: int = Field(foreign_key="users.id", primary_key=True)
    role_id: int = Field(foreign_key="roles.id", primary_key=True)


class MicroRole(SQLModel, table=True):
    __tablename__ = "roles"
    __table_args__ = {"extend_existing": True}
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: str | None = None

    users: list[MicroUser] = Relationship(
        sa_relationship=relationship("MicroUser", secondary="user_roles", back_populates="roles")
    )
    permissions: list[MicroPermission] = Relationship(
        sa_relationship=relationship(
            "MicroPermission", secondary="role_permissions", back_populates="roles"
        )
    )


class MicroPermission(SQLModel, table=True):
    __tablename__ = "permissions"
    __table_args__ = {"extend_existing": True}
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: str | None = None

    roles: list[MicroRole] = Relationship(
        sa_relationship=relationship(
            "MicroRole", secondary="role_permissions", back_populates="permissions"
        )
    )


class MicroRolePermission(SQLModel, table=True):
    __tablename__ = "role_permissions"
    __table_args__ = {"extend_existing": True}
    role_id: int = Field(foreign_key="roles.id", primary_key=True)
    permission_id: int = Field(foreign_key="permissions.id", primary_key=True)


class MicroRefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"
    __table_args__ = {"extend_existing": True}

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

    user: MicroUser = Relationship(
        sa_relationship=relationship("MicroUser", back_populates="refresh_tokens")
    )

    def revoke(self, *, revoked_at: datetime | None = None, replaced_by: str | None = None) -> None:
        self.revoked_at = revoked_at or utc_now()
        self.replaced_by_token_id = replaced_by

    def is_active(self, *, now: datetime | None = None) -> bool:
        current_time = now or utc_now()
        return self.revoked_at is None and current_time < self.expires_at


class MicroPasswordResetToken(SQLModel, table=True):
    __tablename__ = "password_resets"
    __table_args__ = {"extend_existing": True}

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

    user: MicroUser = Relationship(
        sa_relationship=relationship("MicroUser", back_populates="password_reset_tokens")
    )

    def is_active(self, *, now: datetime | None = None) -> bool:
        moment = now or utc_now()
        return self.redeemed_at is None and moment < self.expires_at

    def mark_redeemed(self, *, redeemed_at: datetime | None = None) -> None:
        self.redeemed_at = redeemed_at or utc_now()


class MicroAuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    actor_user_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    action: str = Field(max_length=150, index=True)
    target_type: str = Field(max_length=100)
    target_id: str | None = Field(default=None, max_length=150)
    details: dict[str, object] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON, nullable=False, default=dict),
    )
    ip: str | None = Field(default=None, max_length=64)
    user_agent: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True),
    )

    actor: MicroUser | None = Relationship(
        sa_relationship=relationship("MicroUser", back_populates="audit_logs"),
    )


class MicroUser(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str | None = Field(default=None, alias="hashed_password")

    full_name: str | None = None
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    is_admin: bool = Field(default=False)

    status: UserStatus = Field(default=UserStatus.ACTIVE)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    roles: list[MicroRole] = Relationship(
        sa_relationship=relationship("MicroRole", secondary="user_roles", back_populates="users")
    )

    refresh_tokens: list[MicroRefreshToken] = Relationship(
        sa_relationship=relationship("MicroRefreshToken", back_populates="user")
    )

    password_reset_tokens: list[MicroPasswordResetToken] = Relationship(
        sa_relationship=relationship("MicroPasswordResetToken", back_populates="user")
    )

    audit_logs: list[MicroAuditLog] = Relationship(
        sa_relationship=relationship("MicroAuditLog", back_populates="actor")
    )

    def set_password(self, password: str) -> None:
        pass

    def check_password(self, password: str) -> bool:
        return True

    @property
    def hashed_password(self):
        return self.password_hash

    @hashed_password.setter
    def hashed_password(self, value):
        self.password_hash = value


# Aliases for compatibility with existing imports
User = MicroUser
Role = MicroRole
UserRole = MicroUserRole
Permission = MicroPermission
RolePermission = MicroRolePermission
RefreshToken = MicroRefreshToken
PasswordResetToken = MicroPasswordResetToken
AuditLog = MicroAuditLog
