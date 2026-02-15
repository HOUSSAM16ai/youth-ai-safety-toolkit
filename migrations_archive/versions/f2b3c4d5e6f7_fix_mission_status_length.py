"""fix mission status length

Revision ID: f2b3c4d5e6f7
Revises: e1a2b3c4d5e6
Create Date: 2026-03-01 13:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'f2b3c4d5e6f7'
down_revision = 'e1a2b3c4d5e6'
branch_labels = None
depends_on = None

def upgrade():
    # 1. missions.status
    # Enum name was 'missionstatus'
    op.execute("ALTER TABLE missions DROP CONSTRAINT IF EXISTS missionstatus")
    op.execute("ALTER TABLE missions DROP CONSTRAINT IF EXISTS ck_missions_status")
    op.execute("ALTER TABLE missions ALTER COLUMN status TYPE TEXT")

    # 2. mission_plans.status
    # Enum name was 'planstatus'
    op.execute("ALTER TABLE mission_plans DROP CONSTRAINT IF EXISTS planstatus")
    op.execute("ALTER TABLE mission_plans DROP CONSTRAINT IF EXISTS ck_mission_plans_status")
    op.execute("ALTER TABLE mission_plans ALTER COLUMN status TYPE TEXT")

    # 3. tasks.task_type
    # Enum name was 'tasktype'
    op.execute("ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasktype")
    op.execute("ALTER TABLE tasks DROP CONSTRAINT IF EXISTS ck_tasks_task_type")
    op.execute("ALTER TABLE tasks ALTER COLUMN task_type TYPE TEXT")

    # 4. tasks.status
    # Enum name was 'taskstatus'
    op.execute("ALTER TABLE tasks DROP CONSTRAINT IF EXISTS taskstatus")
    op.execute("ALTER TABLE tasks DROP CONSTRAINT IF EXISTS ck_tasks_status")
    op.execute("ALTER TABLE tasks ALTER COLUMN status TYPE TEXT")

    # 5. mission_events.event_type
    # Enum name was 'missioneventtype'
    op.execute("ALTER TABLE mission_events DROP CONSTRAINT IF EXISTS missioneventtype")
    op.execute("ALTER TABLE mission_events DROP CONSTRAINT IF EXISTS ck_mission_events_event_type")
    op.execute("ALTER TABLE mission_events ALTER COLUMN event_type TYPE TEXT")


def downgrade():
    pass
