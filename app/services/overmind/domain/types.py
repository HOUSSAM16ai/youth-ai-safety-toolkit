"""
Overmind Domain Types.
Strict type definitions for mission context, readiness checks, and internal structures.
Adheres to the "No Any" policy.
"""

from typing import Literal, NotRequired, TypedDict

# Recursive JSON Type for strict typing of arbitrary JSON structures
# Using 'type' keyword for Python 3.12+ compliance (UP040)
type JsonValue = dict[str, JsonValue] | list[JsonValue] | str | int | float | bool | None

# Mission Context is a JSON object
type MissionContext = dict[str, JsonValue]


class ProviderReadinessDetails(TypedDict):
    """Details returned by provider readiness checks."""

    status: Literal["ready", "degraded", "failed"]
    reason: NotRequired[str]
    details: NotRequired[str]


class EgressCheckDetails(TypedDict):
    """Details returned by egress connectivity checks."""

    status: Literal["OK", "PARTIAL", "NO_EGRESS"]
    success_count: int
    failed_probes: list[str]


class MissionReadinessStatus(TypedDict):
    """Overall mission readiness status."""

    ready: bool
    mode: NotRequired[Literal["ready", "degraded", "failed"]]
    error: NotRequired[str]
    details: NotRequired[str]
