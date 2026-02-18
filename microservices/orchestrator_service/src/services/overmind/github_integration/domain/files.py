from app.core.di import get_logger
from microservices.orchestrator_service.src.services.overmind.github_integration.client import (
    GitHubClient,
)
from microservices.orchestrator_service.src.services.overmind.github_integration.models import (
    GitHubFileContent,
)

logger = get_logger(__name__)


class FileManager:
    def __init__(self, client: GitHubClient):
        self.client = client

    async def get_file_content(
        self, file_path: str, branch: str = "main"
    ) -> GitHubFileContent | dict[str, object]:
        if not self.client.repo_object:
            return {"success": False, "error": "Repository not initialized"}

        try:

            def _fetch():
                file = self.client.repo_object.get_contents(file_path, ref=branch)
                import base64

                content = base64.b64decode(file.content).decode("utf-8")
                return GitHubFileContent(
                    path=file.path,
                    content=content,
                    sha=file.sha,
                    size=file.size,
                )

            return await self.client.run_async(_fetch)

        except Exception as e:
            logger.error(f"Error getting file {file_path}: {e}")
            return {"success": False, "error": str(e)}

    async def update_file(
        self,
        file_path: str,
        content: str,
        message: str,
        branch: str = "main",
    ) -> dict[str, object]:
        if not self.client.repo_object:
            return {"success": False, "error": "Repository not initialized"}

        try:

            def _update():
                # Get current file for SHA
                file = self.client.repo_object.get_contents(file_path, ref=branch)
                return self.client.repo_object.update_file(
                    path=file_path,
                    message=message,
                    content=content,
                    sha=file.sha,
                    branch=branch,
                )

            result = await self.client.run_async(_update)
            logger.info(f"Updated file {file_path} in branch {branch}")
            return {
                "success": True,
                "path": file_path,
                "commit_sha": result["commit"].sha,
            }

        except Exception as e:
            logger.error(f"Error updating file {file_path}: {e}")
            return {"success": False, "error": str(e)}
