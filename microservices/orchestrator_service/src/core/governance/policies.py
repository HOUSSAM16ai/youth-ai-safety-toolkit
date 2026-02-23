"""
Mission Outcome Policy.
-----------------------
Implements the Decision Kernel for determining Mission Status.
Replaces ad-hoc logic in OvermindOrchestrator.
"""

import logging

from pydantic import Field

# Updated to use microservice model
from microservices.orchestrator_service.src.models.mission import MissionStatus
from app.core.governance.contracts import GovernanceModel
from app.core.governance.decision import DecisionRecord, Policy
from app.core.governance.errors import FailureClass

logger = logging.getLogger(__name__)


class MissionContext(GovernanceModel):
    """
    Context required to decide a Mission's outcome.
    """

    mission_id: int
    execution_status: str | None = None  # From OperatorAgent (failed, partial_failure, etc)
    tool_results: list[dict] = Field(default_factory=list)  # Raw tool outputs
    has_empty_search: bool = False


class MissionOutcome(GovernanceModel):
    """
    The decision result.
    """

    final_status: str  # MissionStatus string
    notes: str


class MissionOutcomePolicy(Policy[MissionContext, MissionOutcome]):
    """
    The Single Source of Truth for Mission Success/Failure.
    """

    @property
    def name(self) -> str:
        return "MissionOutcomePolicy_v1"

    def evaluate(self, context: MissionContext) -> DecisionRecord[MissionOutcome]:
        """
        Decide the mission status based on evidence.
        """
        decision_id = f"mission_{context.mission_id}_outcome"

        # 1. Explicit Operator Failure
        if context.execution_status == "failed":
            return DecisionRecord(
                decision_id=decision_id,
                policy_name=self.name,
                status="COMPLETED",
                failure_class=FailureClass.BUSINESS_REJECTED,
                result=MissionOutcome(
                    final_status=MissionStatus.FAILED, notes="Operator reported total failure."
                ),
                reasoning="OperatorAgent explicitly signaled 'failed' status.",
            )

        # 2. Explicit Operator Partial Failure
        if context.execution_status == "partial_failure":
            return DecisionRecord(
                decision_id=decision_id,
                policy_name=self.name,
                status="COMPLETED",
                result=MissionOutcome(
                    final_status=MissionStatus.PARTIAL_SUCCESS,
                    notes="Operator reported partial failures.",
                ),
                reasoning="OperatorAgent explicitly signaled 'partial_failure' status.",
            )

        # 3. Empty Search Results (Degraded Experience)
        if context.has_empty_search:
            return DecisionRecord(
                decision_id=decision_id,
                policy_name=self.name,
                status="COMPLETED",
                result=MissionOutcome(
                    final_status=MissionStatus.PARTIAL_SUCCESS,
                    notes="Search tools returned empty results.",
                ),
                reasoning="Critical search step yielded no data (Empty Result).",
            )

        # 4. Default Success
        return DecisionRecord(
            decision_id=decision_id,
            policy_name=self.name,
            status="COMPLETED",
            result=MissionOutcome(
                final_status=MissionStatus.SUCCESS, notes="Mission completed successfully."
            ),
            reasoning="No failure signals detected.",
        )
