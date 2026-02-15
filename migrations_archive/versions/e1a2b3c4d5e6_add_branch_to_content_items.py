"""add branch to content items

Revision ID: e1a2b3c4d5e6
Revises: dcc60af077c4
Create Date: 2026-03-01 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'e1a2b3c4d5e6'
down_revision = 'dcc60af077c4'
branch_labels = None
depends_on = None


def upgrade():
    # Add branch column to content_items
    op.add_column('content_items', sa.Column('branch', sa.String(length=100), nullable=True))

    # Create index on branch for faster filtering
    op.create_index(op.f('ix_content_items_branch'), 'content_items', ['branch'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_content_items_branch'), table_name='content_items')
    op.drop_column('content_items', 'branch')
