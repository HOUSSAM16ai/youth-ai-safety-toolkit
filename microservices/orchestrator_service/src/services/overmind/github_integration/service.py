"""
GitHub Integration Service Facade.
Aggregates domain-specific managers and exposes a clean, unified API.
Adheres to strictly typed async operations.
"""

from app.core.di import get_logger
from microservices.orchestrator_service.src.services.overmind.github_integration.client import (
    GitHubClient,
)
from microservices.orchestrator_service.src.services.overmind.github_integration.domain.branches import (
    BranchManager,
)
from microservices.orchestrator_service.src.services.overmind.github_integration.domain.commits import (
    CommitManager,
)
from microservices.orchestrator_service.src.services.overmind.github_integration.domain.files import (
    FileManager,
)
from microservices.orchestrator_service.src.services.overmind.github_integration.domain.issues import (
    IssueManager,
)
from microservices.orchestrator_service.src.services.overmind.github_integration.domain.pr import (
    PRManager,
)
from microservices.orchestrator_service.src.services.overmind.github_integration.models import (
    GitHubBranch,
    GitHubCommit,
    GitHubFileContent,
    GitHubIssue,
    GitHubPR,
    RepoInfo,
)

logger = get_logger(__name__)


class GitHubService:
    """
    Unified Facade for GitHub Operations.
    Delegates to specialized domain managers.
    Ensures thread-safety for underlying blocking PyGithub calls.
    """

    def __init__(
        self,
        token: str | None = None,
        repo_owner: str | None = None,
        repo_name: str | None = None,
    ) -> None:
        self.client = GitHubClient(token, repo_owner, repo_name)

        # Domain Managers
        self._branches = BranchManager(self.client)
        self._commits = CommitManager(self.client)
        self._prs = PRManager(self.client)
        self._issues = IssueManager(self.client)
        self._files = FileManager(self.client)

    async def initialize(self) -> None:
        """Async initialization required to fetch repo metadata safely."""
        await self.client.initialize()

    def is_authenticated(self) -> bool:
        return self.client.authenticated

    async def get_repo_info(self) -> RepoInfo:
        return await self.client.get_repo_info()

    # =========================================================================
    # DELEGATED METHODS
    # =========================================================================

    async def list_branches(self) -> list[GitHubBranch]:
        return await self._branches.list_branches()

    async def create_branch(self, branch_name: str, from_branch: str = "main") -> dict[str, object]:
        return await self._branches.create_branch(branch_name, from_branch)

    async def delete_branch(self, branch_name: str) -> dict[str, object]:
        return await self._branches.delete_branch(branch_name)

    async def list_commits(self, branch: str = "main", limit: int = 10) -> list[GitHubCommit]:
        return await self._commits.list_commits(branch, limit)

    async def get_commit(self, sha: str) -> GitHubCommit | dict[str, str]:
        return await self._commits.get_commit(sha)

    async def list_pull_requests(self, state: str = "open") -> list[GitHubPR]:
        return await self._prs.list_pull_requests(state)

    async def create_pull_request(
        self, title: str, body: str, head: str, base: str = "main"
    ) -> dict[str, object]:
        return await self._prs.create_pull_request(title, body, head, base)

    async def merge_pull_request(
        self, pr_number: int, merge_method: str = "merge"
    ) -> dict[str, object]:
        return await self._prs.merge_pull_request(pr_number, merge_method)

    async def list_issues(
        self, state: str = "open", labels: list[str] | None = None
    ) -> list[GitHubIssue]:
        return await self._issues.list_issues(state, labels)

    async def create_issue(
        self, title: str, body: str, labels: list[str] | None = None
    ) -> dict[str, object]:
        return await self._issues.create_issue(title, body, labels)

    async def close_issue(self, issue_number: int) -> dict[str, object]:
        return await self._issues.close_issue(issue_number)

    async def get_file_content(
        self, file_path: str, branch: str = "main"
    ) -> GitHubFileContent | dict[str, object]:
        return await self._files.get_file_content(file_path, branch)

    async def update_file(
        self, file_path: str, content: str, message: str, branch: str = "main"
    ) -> dict[str, object]:
        return await self._files.update_file(file_path, content, message, branch)
