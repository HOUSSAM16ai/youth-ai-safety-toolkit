"""
Mission Domain Models.
Contains Mission, MissionPlan, Task, MissionEvent, and related Enums.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship, SQLModel

from .common import CaseInsensitiveEnum, FlexibleEnum, JSONText, utc_now

if TYPE_CHECKING:
    from .user import User


class MissionStatus(CaseInsensitiveEnum):
    """Mission Status Enum."""

    PENDING = "pending"
    PLANNING = "planning"
    PLANNED = "planned"
    RUNNING = "running"
    ADAPTING = "adapting"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    CANCELED = "canceled"


class PlanStatus(CaseInsensitiveEnum):
    DRAFT = "draft"
    VALID = "valid"
    INVALID = "invalid"
    SELECTED = "selected"
    ABANDONED = "abandoned"


class TaskStatus(CaseInsensitiveEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"
    SKIPPED = "skipped"


class MissionEventType(CaseInsensitiveEnum):
    CREATED = "mission_created"
    STATUS_CHANGE = "status_change"
    ARCHITECTURE_CLASSIFIED = "architecture_classified"
    PLAN_SELECTED = "plan_selected"
    EXECUTION_STARTED = "execution_started"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    REPLAN_TRIGGERED = "replan_triggered"
    REPLAN_APPLIED = "replan_applied"
    RISK_SUMMARY = "risk_summary"
    MISSION_COMPLETED = "mission_completed"
    MISSION_FAILED = "mission_failed"
    FINALIZED = "mission_finalized"


class Mission(SQLModel, table=True):
    __tablename__ = "missions"
    id: int | None = Field(default=None, primary_key=True)
    objective: str = Field(sa_column=Column(Text))
    status: MissionStatus = Field(
        default=MissionStatus.PENDING,
        sa_column=Column(FlexibleEnum(MissionStatus)),
    )
    initiator_id: int = Field(foreign_key="users.id", index=True)
    active_plan_id: int | None = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("mission_plans.id", use_alter=True)),
    )

    # Idempotency
    idempotency_key: str | None = Field(default=None, unique=True, index=True, max_length=128)

    locked: bool = Field(default=False)
    result_summary: str | None = Field(default=None, sa_column=Column(Text))
    total_cost_usd: float | None = Field(default=None)
    adaptive_cycles: int = Field(default=0)

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    )

    # Relationships
    initiator: User = Relationship(sa_relationship=relationship("User", back_populates="missions"))
    tasks: list[Task] = Relationship(
        sa_relationship=relationship(
            "Task",
            back_populates="mission",
            foreign_keys=lambda: [Task.mission_id],
        )
    )
    mission_plans: list[MissionPlan] = Relationship(
        sa_relationship=relationship(
            "MissionPlan", back_populates="mission", foreign_keys="[MissionPlan.mission_id]"
        )
    )
    events: list[MissionEvent] = Relationship(
        sa_relationship=relationship("MissionEvent", back_populates="mission")
    )


class MissionPlan(SQLModel, table=True):
    __tablename__ = "mission_plans"
    id: int | None = Field(default=None, primary_key=True)
    mission_id: int = Field(foreign_key="missions.id", index=True)
    version: int = Field(default=1)
    planner_name: str = Field(max_length=100)
    status: PlanStatus = Field(
        default=PlanStatus.DRAFT,
        sa_column=Column(FlexibleEnum(PlanStatus)),
    )
    score: float = Field(default=0.0)
    rationale: str | None = Field(sa_column=Column(Text))
    raw_json: object | None = Field(sa_column=Column(JSONText))
    stats_json: object | None = Field(sa_column=Column(JSONText))
    warnings_json: object | None = Field(sa_column=Column(JSONText))
    content_hash: str | None = Field(max_length=64)

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )

    # Relationships
    mission: Mission = Relationship(
        sa_relationship=relationship(
            "Mission", back_populates="mission_plans", foreign_keys="[MissionPlan.mission_id]"
        )
    )
    tasks: list[Task] = Relationship(sa_relationship=relationship("Task", back_populates="plan"))


class Task(SQLModel, table=True):
    __tablename__ = "tasks"
    id: int | None = Field(default=None, primary_key=True)
    mission_id: int = Field(foreign_key="missions.id", index=True)
    plan_id: int | None = Field(default=None, foreign_key="mission_plans.id", index=True)
    task_key: str = Field(max_length=50)
    description: str | None = Field(sa_column=Column(Text))
    tool_name: str | None = Field(max_length=100)
    tool_args_json: object | None = Field(default=None, sa_column=Column(JSONText))
    status: TaskStatus = Field(
        default=TaskStatus.PENDING,
        sa_column=Column(FlexibleEnum(TaskStatus)),
    )
    attempt_count: int = Field(default=0)
    max_attempts: int = Field(default=3)
    priority: int = Field(default=0)
    risk_level: str | None = Field(max_length=50)
    criticality: str | None = Field(max_length=50)
    depends_on_json: object | None = Field(default=None, sa_column=Column(JSONText))
    result_text: str | None = Field(sa_column=Column(Text))
    result_meta_json: object | None = Field(default=None, sa_column=Column(JSONText))
    error_text: str | None = Field(sa_column=Column(Text))

    started_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))
    finished_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))
    next_retry_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))
    duration_ms: int | None = Field(default=0)

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    )

    # Relationships
    mission: Mission = Relationship(
        sa_relationship=relationship(
            "Mission", back_populates="tasks", foreign_keys=lambda: [Task.mission_id]
        )
    )
    plan: MissionPlan = Relationship(
        sa_relationship=relationship(
            "MissionPlan", back_populates="tasks", foreign_keys=lambda: [Task.plan_id]
        )
    )


class MissionEvent(SQLModel, table=True):
    __tablename__ = "mission_events"
    id: int | None = Field(default=None, primary_key=True)
    mission_id: int = Field(foreign_key="missions.id", index=True)
    event_type: MissionEventType = Field(sa_column=Column(FlexibleEnum(MissionEventType)))
    payload_json: object | None = Field(default=None, sa_column=Column(JSONText))

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )

    # Relationships
    mission: Mission = Relationship(
        sa_relationship=relationship("Mission", back_populates="events")
    )


class MissionOutbox(SQLModel, table=True):
    """
    Transactional Outbox for Mission Events.
    Ensures that events are published to the Event Bus (Redis) reliably.
    """

    __tablename__ = "mission_outbox"
    id: int | None = Field(default=None, primary_key=True)
    mission_id: int = Field(index=True)
    event_type: str = Field(index=True)
    payload_json: object | None = Field(default=None, sa_column=Column(JSONText))
    status: str = Field(default="pending", index=True)  # pending, published, failed

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    published_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))


# Helpers
def log_mission_event(
    mission: Mission, event_type: MissionEventType, payload: dict, session=None
) -> None:
    """
    Log a mission event to the database.
    """
    evt = MissionEvent(mission_id=mission.id, event_type=event_type, payload_json=payload)
    if session:
        session.add(evt)


def update_mission_status(
    mission: Mission, status: MissionStatus, note: str | None = None, session=None
) -> None:
    """
    Update mission status.
    """
    mission.status = status
    mission.updated_at = utc_now()
