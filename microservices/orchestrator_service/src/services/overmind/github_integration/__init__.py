"""
GitHub Integration Package.
Exposes the main service facade.
"""

from microservices.orchestrator_service.src.services.overmind.github_integration.service import (
    GitHubService,
)

__all__ = ["GitHubService"]
