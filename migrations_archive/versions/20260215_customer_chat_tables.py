"""Add customer chat conversation tables

Revision ID: 20260215_customer_chat_tables
Revises: 20260105_password_reset_tokens
Create Date: 2026-02-15 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260215_customer_chat_tables"
down_revision = "20260105_password_reset_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """إنشاء جداول محادثات العملاء القياسيين."""

    op.create_table(
        "customer_conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_customer_conversations_user_id",
        "customer_conversations",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "customer_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("customer_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("policy_flags", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_customer_messages_conversation_id",
        "customer_messages",
        ["conversation_id"],
        unique=False,
    )


def downgrade() -> None:
    """حذف جداول محادثات العملاء القياسيين."""

    op.drop_index("ix_customer_messages_conversation_id", table_name="customer_messages")
    op.drop_table("customer_messages")
    op.drop_index("ix_customer_conversations_user_id", table_name="customer_conversations")
    op.drop_table("customer_conversations")
