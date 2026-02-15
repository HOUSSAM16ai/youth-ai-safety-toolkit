from uuid import UUID, uuid4

from sqlmodel import JSON, Field, SQLModel

# Import shared models so Alembic detects them for this service
from app.domain.models.outbox import MissionOutbox  # noqa: F401


class Plan(SQLModel, table=True):
    """
    نموذج الخطة لقاعدة البيانات.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    goal: str = Field(index=True)
    steps: list[str] = Field(default_factory=list, sa_type=JSON)
