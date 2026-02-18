from app.core.di import get_logger
from microservices.orchestrator_service.src.services.overmind.github_integration.client import (
    GitHubClient,
)
from microservices.orchestrator_service.src.services.overmind.github_integration.models import (
    GitHubPR,
)

logger = get_logger(__name__)


class PRManager:
    def __init__(self, client: GitHubClient):
        self.client = client

    async def list_pull_requests(self, state: str = "open") -> list[GitHubPR]:
        if not self.client.repo_object:
            return []

        try:

            def _fetch():
                prs = []
                for pr in self.client.repo_object.get_pulls(state=state):
                    prs.append(
                        GitHubPR(
                            number=pr.number,
                            title=pr.title,
                            state=pr.state,
                            author=pr.user.login,
                            head=pr.head.ref,
                            base=pr.base.ref,
                            created_at=pr.created_at.isoformat(),
                            url=pr.html_url,
                        )
                    )
                return prs

            result = await self.client.run_async(_fetch)
            logger.info(f"Listed {len(result)} pull requests ({state})")
            return result

        except Exception as e:
            logger.error(f"Error listing PRs: {e}")
            return []

    async def create_pull_request(
        self,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> dict[str, object]:
        if not self.client.repo_object:
            return {"success": False, "error": "Repository not initialized"}

        try:

            def _create():
                return self.client.repo_object.create_pull(
                    title=title,
                    body=body,
                    head=head,
                    base=base,
                )

            pr = await self.client.run_async(_create)
            logger.info(f"Created PR #{pr.number}: {title}")
            return {
                "success": True,
                "number": pr.number,
                "title": pr.title,
                "url": pr.html_url,
                "state": pr.state,
            }

        except Exception as e:
            logger.error(f"Error creating PR: {e}")
            return {"success": False, "error": str(e)}

    async def merge_pull_request(
        self,
        pr_number: int,
        merge_method: str = "merge",
    ) -> dict[str, object]:
        if not self.client.repo_object:
            return {"success": False, "error": "Repository not initialized"}

        try:

            def _merge():
                pr = self.client.repo_object.get_pull(pr_number)
                return pr.merge(merge_method=merge_method)

            result = await self.client.run_async(_merge)
            logger.info(f"Merged PR #{pr_number} using {merge_method}")
            return {
                "success": result.merged,
                "message": result.message,
                "sha": result.sha,
            }

        except Exception as e:
            logger.error(f"Error merging PR #{pr_number}: {e}")
            return {"success": False, "error": str(e)}
