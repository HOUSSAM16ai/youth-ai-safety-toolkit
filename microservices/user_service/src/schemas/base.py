"""
Core Schemas for User Service.
"""

from pydantic import BaseModel, ConfigDict

__all__ = ["RobustBaseModel"]


class RobustBaseModel(BaseModel):
    """
    Robust Base Model applying Postel's Law.
    """

    model_config = ConfigDict(
        extra="ignore",
        from_attributes=True,
        populate_by_name=True,
    )

    def to_dict(self, **kwargs: dict[str, str | int | bool]) -> dict[str, object]:
        return self.model_dump(**kwargs)
