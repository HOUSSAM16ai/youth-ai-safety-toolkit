from app.core.di import get_logger
from microservices.orchestrator_service.src.services.overmind.github_integration.client import (
    GitHubClient,
)
from microservices.orchestrator_service.src.services.overmind.github_integration.models import (
    GitHubBranch,
)

logger = get_logger(__name__)


class BranchManager:
    def __init__(self, client: GitHubClient):
        self.client = client

    async def list_branches(self) -> list[GitHubBranch]:
        if not self.client.repo_object:
            return []

        try:

            def _fetch():
                branches = []
                for branch in self.client.repo_object.get_branches():
                    branches.append(
                        GitHubBranch(
                            name=branch.name,
                            sha=branch.commit.sha,
                            protected=branch.protected,
                        )
                    )
                return branches

            result = await self.client.run_async(_fetch)
            logger.info(f"Listed {len(result)} branches")
            return result

        except Exception as e:
            logger.error(f"Error listing branches: {e}")
            return []

    async def create_branch(self, branch_name: str, from_branch: str = "main") -> dict[str, object]:
        if not self.client.repo_object:
            return {"success": False, "error": "Repository not initialized"}

        try:

            def _create():
                source_branch = self.client.repo_object.get_branch(from_branch)
                source_sha = source_branch.commit.sha
                ref = f"refs/heads/{branch_name}"
                self.client.repo_object.create_git_ref(ref, source_sha)
                return source_sha

            sha = await self.client.run_async(_create)
            logger.info(f"Created branch '{branch_name}' from '{from_branch}'")
            return {
                "success": True,
                "branch": branch_name,
                "sha": sha,
                "from": from_branch,
            }

        except Exception as e:
            logger.error(f"Error creating branch: {e}")
            return {"success": False, "error": str(e)}

    async def delete_branch(self, branch_name: str) -> dict[str, object]:
        if not self.client.repo_object:
            return {"success": False, "error": "Repository not initialized"}

        try:
            if branch_name == self.client.repo_object.default_branch:
                return {
                    "success": False,
                    "error": f"Cannot delete default branch '{branch_name}'",
                }

            def _delete():
                ref = self.client.repo_object.get_git_ref(f"heads/{branch_name}")
                ref.delete()

            await self.client.run_async(_delete)
            logger.warning(f"Deleted branch '{branch_name}'")
            return {"success": True, "branch": branch_name}

        except Exception as e:
            logger.error(f"Error deleting branch: {e}")
            return {"success": False, "error": str(e)}
