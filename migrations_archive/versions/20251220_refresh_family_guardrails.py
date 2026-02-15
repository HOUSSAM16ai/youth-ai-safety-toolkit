"""Add refresh token family and replay guardrails

Revision ID: 20251220_refresh_family
Revises: 0b5107e8283d
Create Date: 2025-12-20 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251220_refresh_family"
down_revision = "0b5107e8283d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("refresh_tokens") as batch:
        batch.add_column(sa.Column("family_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("replaced_by_token_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("created_ip", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("user_agent", sa.String(length=255), nullable=True))
        batch.create_index("ix_refresh_tokens_family_id", ["family_id"], unique=False)
        batch.create_index(
            "ix_refresh_tokens_replaced_by_token_id", ["replaced_by_token_id"], unique=False
        )

    op.execute("UPDATE refresh_tokens SET family_id = token_id WHERE family_id IS NULL")


def downgrade() -> None:
    with op.batch_alter_table("refresh_tokens") as batch:
        batch.drop_index("ix_refresh_tokens_replaced_by_token_id")
        batch.drop_index("ix_refresh_tokens_family_id")
        batch.drop_column("user_agent")
        batch.drop_column("created_ip")
        batch.drop_column("replaced_by_token_id")
        batch.drop_column("family_id")
