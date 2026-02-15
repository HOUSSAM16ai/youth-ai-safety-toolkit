"""Add password reset tokens with auditing context

Revision ID: 20260105_password_reset_tokens
Revises: 20251220_refresh_family, 20260101_add_rbac_ums
Create Date: 2026-01-05 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260105_password_reset_tokens"
down_revision = ("20251220_refresh_family", "20260101_add_rbac_ums")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """إنشاء جدول رموز إعادة تعيين كلمات المرور مع الفهارس اللازمة."""

    op.create_table(
        "password_resets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token_id", sa.String(length=36), nullable=False, unique=True),
        sa.Column("hashed_token", sa.String(length=255), nullable=False, unique=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_password_resets_user_id", "password_resets", ["user_id"], unique=False)
    op.create_index("ix_password_resets_expires_at", "password_resets", ["expires_at"], unique=False)
    op.create_index("ix_password_resets_redeemed_at", "password_resets", ["redeemed_at"], unique=False)


def downgrade() -> None:
    """حذف جدول رموز إعادة التعيين والفهارس المرتبطة."""

    op.drop_index("ix_password_resets_redeemed_at", table_name="password_resets")
    op.drop_index("ix_password_resets_expires_at", table_name="password_resets")
    op.drop_index("ix_password_resets_user_id", table_name="password_resets")
    op.drop_table("password_resets")
