from app.core.di import get_logger
from microservices.orchestrator_service.src.services.overmind.github_integration.client import (
    GitHubClient,
)
from microservices.orchestrator_service.src.services.overmind.github_integration.models import (
    GitHubCommit,
)

logger = get_logger(__name__)


class CommitManager:
    def __init__(self, client: GitHubClient):
        self.client = client

    async def list_commits(self, branch: str = "main", limit: int = 10) -> list[GitHubCommit]:
        if not self.client.repo_object:
            return []

        try:

            def _fetch():
                commits = []
                for commit in self.client.repo_object.get_commits(sha=branch)[:limit]:
                    commits.append(
                        GitHubCommit(
                            sha=commit.sha[:7],
                            message=commit.commit.message,
                            author=commit.commit.author.name,
                            date=commit.commit.author.date.isoformat(),
                            url=commit.html_url,
                        )
                    )
                return commits

            result = await self.client.run_async(_fetch)
            logger.info(f"Listed {len(result)} commits from '{branch}'")
            return result

        except Exception as e:
            logger.error(f"Error listing commits: {e}")
            return []

    async def get_commit(self, sha: str) -> GitHubCommit | dict[str, str]:
        if not self.client.repo_object:
            return {"error": "Repository not initialized"}

        try:

            def _fetch():
                commit = self.client.repo_object.get_commit(sha)
                return GitHubCommit(
                    sha=commit.sha,
                    message=commit.commit.message,
                    author=commit.commit.author.name,
                    date=commit.commit.author.date.isoformat(),
                    files_changed=len(commit.files),
                    additions=commit.stats.additions,
                    deletions=commit.stats.deletions,
                    url=commit.html_url,
                )

            return await self.client.run_async(_fetch)

        except Exception as e:
            logger.error(f"Error getting commit {sha}: {e}")
            return {"error": str(e)}
