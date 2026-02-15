"""Stub migration to fix broken dependency chain.

Revision ID: 20251111_drop_cosmic_security
Revises: 20251107_rename_metadata
Create Date: 2025-11-14 16:08:14.088745

"""

# revision identifiers, used by Alembic.
revision = "20251111_drop_cosmic_security"
down_revision = "20251107_rename_metadata"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
