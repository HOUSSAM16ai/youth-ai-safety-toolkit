from app.core.di import get_logger
from microservices.orchestrator_service.src.services.overmind.github_integration.client import (
    GitHubClient,
)
from microservices.orchestrator_service.src.services.overmind.github_integration.models import (
    GitHubIssue,
)

logger = get_logger(__name__)


class IssueManager:
    def __init__(self, client: GitHubClient):
        self.client = client

    async def list_issues(
        self,
        state: str = "open",
        labels: list[str] | None = None,
    ) -> list[GitHubIssue]:
        if not self.client.repo_object:
            return []

        try:

            def _fetch():
                issues = []
                # PyGithub lazy list iteration
                for issue in self.client.repo_object.get_issues(state=state, labels=labels or []):
                    if issue.pull_request:
                        continue
                    issues.append(
                        GitHubIssue(
                            number=issue.number,
                            title=issue.title,
                            state=issue.state,
                            author=issue.user.login,
                            labels=[label.name for label in issue.labels],
                            created_at=issue.created_at.isoformat(),
                            url=issue.html_url,
                        )
                    )
                return issues

            result = await self.client.run_async(_fetch)
            logger.info(f"Listed {len(result)} issues ({state})")
            return result

        except Exception as e:
            logger.error(f"Error listing issues: {e}")
            return []

    async def create_issue(
        self,
        title: str,
        body: str,
        labels: list[str] | None = None,
    ) -> dict[str, object]:
        if not self.client.repo_object:
            return {"success": False, "error": "Repository not initialized"}

        try:

            def _create():
                return self.client.repo_object.create_issue(
                    title=title,
                    body=body,
                    labels=labels or [],
                )

            issue = await self.client.run_async(_create)
            logger.info(f"Created issue #{issue.number}: {title}")
            return {
                "success": True,
                "number": issue.number,
                "title": issue.title,
                "url": issue.html_url,
            }

        except Exception as e:
            logger.error(f"Error creating issue: {e}")
            return {"success": False, "error": str(e)}

    async def close_issue(self, issue_number: int) -> dict[str, object]:
        if not self.client.repo_object:
            return {"success": False, "error": "Repository not initialized"}

        try:

            def _close():
                issue = self.client.repo_object.get_issue(issue_number)
                issue.edit(state="closed")
                return issue

            await self.client.run_async(_close)
            logger.info(f"Closed issue #{issue_number}")
            return {"success": True, "number": issue_number}

        except Exception as e:
            logger.error(f"Error closing issue #{issue_number}: {e}")
            return {"success": False, "error": str(e)}
