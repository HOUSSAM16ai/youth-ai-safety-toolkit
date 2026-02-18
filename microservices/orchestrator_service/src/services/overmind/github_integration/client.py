"""
GitHub Client Manager.
Handles authentication and connection to GitHub API using PyGithub.
Ensures blocking calls are executed in a thread executor.
"""

import asyncio
import os
import subprocess
from collections.abc import Callable
from typing import TypeVar

from app.core.di import get_logger
from microservices.orchestrator_service.src.services.overmind.github_integration.models import (
    RepoInfo,
)

logger = get_logger(__name__)

# Try to import PyGithub
try:
    from github import Github, GithubException, Repository

    PYGITHUB_AVAILABLE = True
except ImportError:
    PYGITHUB_AVAILABLE = False
    Github = object  # type: ignore
    Repository = object  # type: ignore
    GithubException = Exception
    logger.warning("PyGithub not installed. GitHub integration will be disabled.")


T = TypeVar("T")


class GitHubClient:
    """
    Wrapper around PyGithub client to handle authentication and
    provide thread-safe execution for blocking calls.
    """

    def __init__(
        self,
        token: str | None = None,
        repo_owner: str | None = None,
        repo_name: str | None = None,
    ) -> None:
        self.token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.github_client: Github | None = None
        self.repo_object: Repository | None = None
        self.authenticated = False

        if not self.repo_owner:
            self.repo_owner = self._detect_repo_owner_sync()
        if not self.repo_name:
            self.repo_name = self._detect_repo_name_sync()

        self.repo_full_name = (
            f"{self.repo_owner}/{self.repo_name}" if self.repo_owner and self.repo_name else None
        )

        # Initialize immediately if token exists
        if PYGITHUB_AVAILABLE and self.token:
            try:
                self.github_client = Github(self.token)
                self.authenticated = True
                if self.repo_full_name:
                    # We don't fetch the repo object here to avoid blocking init
                    # It will be fetched on first access or explicitly
                    pass
            except Exception as e:
                logger.error(f"Failed to initialize PyGithub client: {e}")

    async def initialize(self) -> None:
        """Async initialization to fetch repo object safely."""
        if self.authenticated and self.repo_full_name and self.github_client:
            try:
                self.repo_object = await self.run_async(
                    self.github_client.get_repo, self.repo_full_name
                )
                logger.info(f"GitHub integration initialized: {self.repo_full_name}")
            except Exception as e:
                logger.error(f"Failed to fetch repo object: {e}")

    async def run_async(self, func: Callable[..., T], *args: object, **kwargs: object) -> T:
        """
        Executes a blocking function in the default executor.
        Use this for ALL PyGithub calls.
        """
        loop = asyncio.get_running_loop()
        # functools.partial is needed if kwargs are used, but for simplicity
        # in this specific wrapper, we might need to handle it.
        # run_in_executor doesn't support kwargs directly.
        import functools

        call = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, call)

    def _detect_repo_owner_sync(self) -> str | None:
        """Detect repo owner from git remote (Synchronous)."""
        try:
            result = subprocess.run(
                ["git", "remote", "-v"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "github.com" in line and "origin" in line:
                        parts = line.split("github.com")[1].split("/")
                        if len(parts) >= 2:
                            return parts[0].strip(":").strip()
        except Exception as e:
            logger.debug(f"Could not detect repo owner: {e}")
        return None

    def _detect_repo_name_sync(self) -> str | None:
        """Detect repo name from git remote (Synchronous)."""
        try:
            result = subprocess.run(
                ["git", "remote", "-v"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "github.com" in line and "origin" in line:
                        parts = line.split("/")
                        if len(parts) >= 2:
                            return parts[-1].split()[0].replace(".git", "")
        except Exception as e:
            logger.debug(f"Could not detect repo name: {e}")
        return None

    async def get_repo_info(self) -> RepoInfo:
        if not self.repo_object:
            return RepoInfo(
                owner=self.repo_owner or "unknown",
                name=self.repo_name or "unknown",
                error="Repository not initialized",
            )

        try:
            # PyGithub objects access attributes lazily which might trigger requests
            # So we should wrap attribute access if it's not cached?
            # Actually, standard attributes are usually loaded.
            # But let's wrap the whole construction just in case.

            def _build_info():
                return RepoInfo(
                    owner=self.repo_object.owner.login,
                    name=self.repo_object.name,
                    full_name=self.repo_object.full_name,
                    description=self.repo_object.description,
                    stars=self.repo_object.stargazers_count,
                    forks=self.repo_object.forks_count,
                    open_issues=self.repo_object.open_issues_count,
                    default_branch=self.repo_object.default_branch,
                    private=self.repo_object.private,
                    created_at=self.repo_object.created_at.isoformat(),
                    updated_at=self.repo_object.updated_at.isoformat(),
                    url=self.repo_object.html_url,
                )

            return await self.run_async(_build_info)

        except Exception as e:
            logger.error(f"Error getting repo info: {e}")
            return RepoInfo(
                owner=self.repo_owner or "unknown", name=self.repo_name or "unknown", error=str(e)
            )
