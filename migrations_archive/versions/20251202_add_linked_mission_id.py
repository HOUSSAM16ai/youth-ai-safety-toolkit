"""Add linked_mission_id to admin_conversations

Revision ID: 20251202_linked_mission
Revises: 351109e83078
Create Date: 2025-12-02

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '20251202_linked_mission'
down_revision = '351109e83078'  # Reference the merge head (unified history)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add linked_mission_id column to admin_conversations table."""
    # Check if column exists before adding
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('admin_conversations')]

    if 'linked_mission_id' not in columns:
        op.add_column(
            'admin_conversations',
            sa.Column('linked_mission_id', sa.Integer(), nullable=True)
        )
        op.create_index(
            'ix_admin_conversations_linked_mission_id',
            'admin_conversations',
            ['linked_mission_id'],
            unique=False
        )


def downgrade() -> None:
    """Remove linked_mission_id column from admin_conversations table."""
    op.drop_index(
        'ix_admin_conversations_linked_mission_id',
        table_name='admin_conversations'
    )
    op.drop_column('admin_conversations', 'linked_mission_id')
