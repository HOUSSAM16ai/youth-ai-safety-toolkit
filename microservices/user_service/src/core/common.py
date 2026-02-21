"""
Common domain utilities and base classes.
Adapted for User Service Microservice.
"""

from __future__ import annotations

import enum
import json
from datetime import UTC, datetime

from sqlalchemy import Text, TypeDecorator
from sqlalchemy.engine.interfaces import Dialect


def utc_now() -> datetime:
    """
    Get current time in UTC.

    Returns:
        datetime: Current UTC datetime
    """
    return datetime.now(UTC)


class CaseInsensitiveEnum(enum.StrEnum):
    """
    Case-Insensitive Enum.
    Allows matching 'user' and 'USER' from database.
    """

    @classmethod
    def _missing_(cls, value: object) -> object:
        if isinstance(value, str):
            upper_value = value.upper()
            if upper_value in cls.__members__:
                return cls[upper_value]
            for member in cls:
                if member.value == value.lower():
                    return member
        return None


class FlexibleEnum(TypeDecorator):
    """
    Flexible Enum Type Decorator for SQLAlchemy.
    Stores as TEXT, handles case-insensitivity on retrieval.
    """

    impl = Text
    cache_ok = True

    def __init__(self, enum_type: type[enum.Enum], *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._enum_type = enum_type

    def process_bind_param(self, value: object, dialect: Dialect) -> object:
        if value is None:
            return None
        if isinstance(value, self._enum_type):
            return value.value
        if isinstance(value, str):
            try:
                return self._enum_type(value).value
            except ValueError:
                return value.lower()
        return value

    def process_result_value(self, value: object, dialect: Dialect) -> object:
        if value is None:
            return None
        if isinstance(value, self._enum_type):
            return value
        try:
            return self._enum_type(value)
        except Exception:
            resolved = self._enum_type._missing_(value)
            return resolved or value


class JSONText(TypeDecorator):
    """
    SQLAlchemy TypeDecorator that serializes JSON to Text for storage
    and deserializes Text to JSON on retrieval.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: object, dialect: Dialect) -> object:
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value: object, dialect: Dialect) -> object:
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
