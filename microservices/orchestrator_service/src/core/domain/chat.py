"""
Chat Domain Models.
Contains AdminConversation, AdminMessage, CustomerConversation, CustomerMessage.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, Text, func
from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship

from microservices.orchestrator_service.src.models.mission import OrchestratorSQLModel

from .common import CaseInsensitiveEnum, FlexibleEnum, JSONText, utc_now

if TYPE_CHECKING:
    from .user import User


class MessageRole(CaseInsensitiveEnum):
    """
    Message Role Enum.
    """

    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"


class AdminConversation(OrchestratorSQLModel, table=True):
    __tablename__ = "admin_conversations"
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(max_length=500)
    user_id: int = Field(foreign_key="users.id", index=True)
    conversation_type: str = Field(default="general", max_length=50)
    # Link to mission created from this conversation
    linked_mission_id: int | None = Field(default=None, index=True)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )

    # Relationships
    user: User = Relationship(
        sa_relationship=relationship("User", back_populates="admin_conversations")
    )
    messages: list[AdminMessage] = Relationship(
        sa_relationship=relationship("AdminMessage", back_populates="conversation")
    )


class AdminMessage(OrchestratorSQLModel, table=True):
    __tablename__ = "admin_messages"
    id: int | None = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="admin_conversations.id", index=True)
    role: MessageRole = Field(sa_column=Column(FlexibleEnum(MessageRole)))
    content: str = Field(sa_column=Column(Text))
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )

    # Relationships
    conversation: AdminConversation = Relationship(
        sa_relationship=relationship("AdminConversation", back_populates="messages")
    )


class CustomerConversation(OrchestratorSQLModel, table=True):
    """
    Standard Customer Conversation.
    """

    __tablename__ = "customer_conversations"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(max_length=500)
    user_id: int = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )

    user: User = Relationship(
        sa_relationship=relationship("User", back_populates="customer_conversations")
    )
    messages: list[CustomerMessage] = Relationship(
        sa_relationship=relationship("CustomerMessage", back_populates="conversation")
    )


class CustomerMessage(OrchestratorSQLModel, table=True):
    """
    Standard Customer Message with policy flags.
    """

    __tablename__ = "customer_messages"

    id: int | None = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="customer_conversations.id", index=True)
    role: MessageRole = Field(sa_column=Column(FlexibleEnum(MessageRole)))
    content: str = Field(sa_column=Column(Text))
    policy_flags: dict[str, str] | None = Field(
        default=None,
        sa_column=Column(JSONText),
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )

    conversation: CustomerConversation = Relationship(
        sa_relationship=relationship("CustomerConversation", back_populates="messages")
    )
