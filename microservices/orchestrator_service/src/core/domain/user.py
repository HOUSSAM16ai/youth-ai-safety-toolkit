"""
User Domain Models.
Contains User (Simplified for Orchestrator).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship

from microservices.orchestrator_service.src.models.mission import OrchestratorSQLModel

from .common import CaseInsensitiveEnum, FlexibleEnum, utc_now

if TYPE_CHECKING:
    # Forward references as strings are sufficient for SQLModel/SQLAlchemy
    # when models are in the same registry/metadata.
    from .chat import AdminConversation, CustomerConversation
    from .mission import Mission


class UserStatus(CaseInsensitiveEnum):
    """User Lifecycle Status."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    DISABLED = "disabled"


class User(OrchestratorSQLModel, table=True):
    __tablename__ = "users"
    id: int | None = Field(default=None, primary_key=True)
    external_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), unique=True, nullable=True),
    )
    full_name: str = Field(max_length=150)
    email: str = Field(max_length=150, unique=True, index=True)
    # password_hash removed to avoid dependency on passlib
    # password_hash: str | None = Field(default=None, max_length=256)
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

    # Relationships (Simplified)
    admin_conversations: list[AdminConversation] = Relationship(
        sa_relationship=relationship("AdminConversation", back_populates="user")
    )
    customer_conversations: list[CustomerConversation] = Relationship(
        sa_relationship=relationship("CustomerConversation", back_populates="user")
    )
    missions: list[Mission] = Relationship(
        sa_relationship=relationship("Mission", back_populates="initiator")
    )

    # Removed: roles, refresh_tokens, password_reset_tokens, audit_logs

    def __repr__(self):
        return f"<User id={self.id} email={self.email}>"
