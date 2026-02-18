from __future__ import annotations

import logging

from microservices.orchestrator_service.src.services.overmind.graph.nodes import (
    AgentMessage,
    AgentNode,
)

logger = logging.getLogger(__name__)


class DecentralizedGraphOrchestrator:
    """
    Manages the lifecycle and connectivity of the Multi-Agent Graph.
    Pillar 3: Decentralized Multi-Agent Graph Architecture.
    """

    def __init__(self):
        self.nodes: dict[str, AgentNode] = {}

    def register_node(self, node: AgentNode) -> None:
        """Adds a node to the graph."""
        self.nodes[node.agent_id] = node
        logger.info(f"Registered Agent Node: {node.agent_id} ({node.role})")

    def create_link(self, source_id: str, target_id: str) -> None:
        """Establishes a connection between two agents."""
        if source_id in self.nodes and target_id in self.nodes:
            self.nodes[source_id].connect(target_id)
            logger.info(f"Linked {source_id} -> {target_id}")

    async def dispatch(
        self, target_id: str, message_content: dict[str, object], sender_id: str = "system"
    ) -> None:
        """Sends a message to a specific node."""
        if target_id in self.nodes:
            msg = AgentMessage(sender_id=sender_id, target_id=target_id, content=message_content)
            await self.nodes[target_id].receive(msg)
        else:
            logger.warning(f"Dispatch failed: Target {target_id} not found.")


_orchestrator: DecentralizedGraphOrchestrator | None = None
