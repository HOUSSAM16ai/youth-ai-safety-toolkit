"""Purify database: Remove old education and admin tables, and task_dependencies

Revision ID: 20250103_purify_db
Revises: c670e137ea84
Create Date: 2025-01-03 00:00:00

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250103_purify_db"
down_revision = "c670e137ea84"
branch_labels = None
depends_on = None


def upgrade():
    """
    Remove all old tables that are not related to the Overmind system:
    - Old education tables: subjects, lessons, exercises, submissions
    - Old admin chat tables: admin_conversations, admin_messages
    - Helper table: task_dependencies (no longer needed, using depends_on_json instead)
    """
    # Drop admin chat tables first (child before parent)
    with op.batch_alter_table("admin_messages", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_admin_messages_conversation_id"))
    op.drop_table("admin_messages")

    with op.batch_alter_table("admin_conversations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_admin_conversations_user_id"))
    op.drop_table("admin_conversations")

    # Drop old education tables (children before parents)
    with op.batch_alter_table("submissions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_submissions_user_id"))
        batch_op.drop_index(batch_op.f("ix_submissions_exercise_id"))
    op.drop_table("submissions")

    with op.batch_alter_table("exercises", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_exercises_lesson_id"))
    op.drop_table("exercises")

    with op.batch_alter_table("lessons", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_lessons_subject_id"))
    op.drop_table("lessons")

    with op.batch_alter_table("subjects", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_subjects_name"))
    op.drop_table("subjects")

    # Drop task_dependencies helper table (no longer needed)
    op.drop_table("task_dependencies")


def downgrade():
    """
    Recreate the removed tables for rollback purposes.
    Note: This will recreate empty tables without data.
    """
    # Recreate task_dependencies
    op.create_table(
        "task_dependencies",
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("depends_on_task_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["depends_on_task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_id", "depends_on_task_id"),
    )

    # Recreate subjects
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("subjects", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_subjects_name"), ["name"], unique=True)

    # Recreate lessons
    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=250), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("subject_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("lessons", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_lessons_subject_id"), ["subject_id"], unique=False)

    # Recreate exercises
    op.create_table(
        "exercises",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("correct_answer_data", sa.JSON(), nullable=True),
        sa.Column("lesson_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("exercises", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_exercises_lesson_id"), ["lesson_id"], unique=False)

    # Recreate submissions
    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_answer_data", sa.JSON(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("exercise_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("submissions", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_submissions_exercise_id"), ["exercise_id"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_submissions_user_id"), ["user_id"], unique=False)

    # Recreate admin_conversations
    op.create_table(
        "admin_conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("conversation_type", sa.String(length=50), nullable=False),
        sa.Column("deep_index_summary", sa.Text(), nullable=True),
        sa.Column("context_snapshot", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("admin_conversations", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_admin_conversations_user_id"), ["user_id"], unique=False
        )

    # Recreate admin_messages
    op.create_table(
        "admin_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("model_used", sa.String(length=100), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["admin_conversations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("admin_messages", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_admin_messages_conversation_id"), ["conversation_id"], unique=False
        )
