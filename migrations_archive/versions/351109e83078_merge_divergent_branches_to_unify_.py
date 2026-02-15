"""Merge divergent branches to unify migration history

Revision ID: 351109e83078
Revises: 20251111_drop_cosmic_security, 23c1d9e5dc65
Create Date: 2025-11-14 17:54:54.018430

"""

# revision identifiers, used by Alembic.
revision = "351109e83078"
down_revision = ("20251111_drop_cosmic_security", "23c1d9e5dc65")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
