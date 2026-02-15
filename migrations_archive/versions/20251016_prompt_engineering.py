"""add prompt engineering tables

Revision ID: 20251016_prompt_engineering
Revises: 20251011_admin_chat
Create Date: 2025-10-16 17:30:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "20251016_prompt_engineering"
down_revision = "20251011_admin_chat"
branch_labels = None
depends_on = None


def JSONB_col():
    return sa.Text().with_variant(JSONB, "postgresql")


def upgrade():
    # Create prompt_templates table
    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("template_content", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("few_shot_examples", JSONB_col(), nullable=True),
        sa.Column("rag_config", JSONB_col(), nullable=True),
        sa.Column("variables", JSONB_col(), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_rate", sa.Float(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for prompt_templates
    op.create_index(
        "ix_prompt_template_category_active", "prompt_templates", ["category", "is_active"]
    )
    op.create_index("ix_prompt_template_usage", "prompt_templates", ["usage_count"])
    op.create_index(op.f("ix_prompt_templates_category"), "prompt_templates", ["category"])
    op.create_index(
        op.f("ix_prompt_templates_created_by_id"), "prompt_templates", ["created_by_id"]
    )
    op.create_index(op.f("ix_prompt_templates_name"), "prompt_templates", ["name"])

    # Create generated_prompts table
    op.create_table(
        "generated_prompts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_description", sa.Text(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=True),
        sa.Column("generated_prompt", sa.Text(), nullable=False),
        sa.Column("context_snippets", JSONB_col(), nullable=True),
        sa.Column("generation_metadata", JSONB_col(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("feedback_text", sa.Text(), nullable=True),
        sa.Column("conversation_id", sa.Integer(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["admin_conversations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["prompt_templates.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for generated_prompts
    op.create_index("ix_generated_prompt_created", "generated_prompts", ["created_at"])
    op.create_index(
        "ix_generated_prompt_template_rating", "generated_prompts", ["template_id", "rating"]
    )
    op.create_index(
        op.f("ix_generated_prompts_content_hash"), "generated_prompts", ["content_hash"]
    )
    op.create_index(
        op.f("ix_generated_prompts_conversation_id"), "generated_prompts", ["conversation_id"]
    )
    op.create_index(
        op.f("ix_generated_prompts_created_by_id"), "generated_prompts", ["created_by_id"]
    )
    op.create_index(op.f("ix_generated_prompts_template_id"), "generated_prompts", ["template_id"])


def downgrade():
    # Drop generated_prompts table and indexes
    op.drop_index(op.f("ix_generated_prompts_template_id"), table_name="generated_prompts")
    op.drop_index(op.f("ix_generated_prompts_created_by_id"), table_name="generated_prompts")
    op.drop_index(op.f("ix_generated_prompts_conversation_id"), table_name="generated_prompts")
    op.drop_index(op.f("ix_generated_prompts_content_hash"), table_name="generated_prompts")
    op.drop_index("ix_generated_prompt_template_rating", table_name="generated_prompts")
    op.drop_index("ix_generated_prompt_created", table_name="generated_prompts")
    op.drop_table("generated_prompts")

    # Drop prompt_templates table and indexes
    op.drop_index(op.f("ix_prompt_templates_name"), table_name="prompt_templates")
    op.drop_index(op.f("ix_prompt_templates_created_by_id"), table_name="prompt_templates")
    op.drop_index(op.f("ix_prompt_templates_category"), table_name="prompt_templates")
    op.drop_index("ix_prompt_template_usage", table_name="prompt_templates")
    op.drop_index("ix_prompt_template_category_active", table_name="prompt_templates")
    op.drop_table("prompt_templates")
