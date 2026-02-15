"""add content items and solutions tables

Revision ID: dcc60af077c4
Revises: 20260215_customer_chat_tables
Create Date: 2026-01-16 02:25:00.800777

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'dcc60af077c4'
down_revision = '20260215_customer_chat_tables'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    # content_items table
    op.create_table(
        'content_items',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False), # exercise, lesson
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('level', sa.String(), nullable=True),
        sa.Column('subject', sa.String(), nullable=True),
        sa.Column('set_name', sa.String(), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('lang', sa.String(), nullable=True),
        sa.Column('md_content', sa.Text(), nullable=False),
        sa.Column('source_path', sa.String(), nullable=False),
        sa.Column('sha256', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # content_solutions table
    # Use generic JSON type which maps to JSON on Postgres and compatible type on SQLite
    op.create_table(
        'content_solutions',
        sa.Column('content_id', sa.String(), nullable=False),
        sa.Column('solution_md', sa.Text(), nullable=True),
        sa.Column('steps_json', sa.JSON(), nullable=True),
        sa.Column('final_answer', sa.String(), nullable=True),
        sa.Column('verified_by_human', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('sha256', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['content_id'], ['content_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('content_id')
    )

    # content_search table
    columns = [
        sa.Column('content_id', sa.String(), nullable=False),
        sa.Column('plain_text', sa.Text(), nullable=False),
    ]

    if is_postgres:
        columns.append(sa.Column('tsvector', postgresql.TSVECTOR(), nullable=True))
        columns.append(sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=True))
    else:
        # For SQLite, we might just skip these or add placeholders if needed,
        # but for now we skip them.
        pass

    op.create_table(
        'content_search',
        *columns,
        sa.ForeignKeyConstraint(['content_id'], ['content_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('content_id')
    )

    # Create indexes for search (Postgres only for TSVECTOR)
    if is_postgres:
        op.create_index('ix_content_search_tsvector', 'content_search', ['tsvector'], postgresql_using='gin')


def downgrade():
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    if is_postgres:
        op.drop_index('ix_content_search_tsvector', table_name='content_search', postgresql_using='gin')

    op.drop_table('content_search')
    op.drop_table('content_solutions')
    op.drop_table('content_items')
