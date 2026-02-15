import httpx
from fastapi import HTTPException, Request, Response, status
import logging

logger = logging.getLogger("api_gateway")

class GatewayProxy:
    """
    Reverse proxy handler for the API Gateway.
    """

    def __init__(self):
        # We will use a single client for connection pooling
        self.client = httpx.AsyncClient(timeout=60.0)

    async def close(self):
        await self.client.aclose()

    async def forward(self, request: Request, target_url: str, path: str) -> Response:
        """
        Forward the incoming request to the target service.

        Args:
            request: The original FastAPI Request.
            target_url: The base URL of the target service (e.g., http://planning-agent:8000).
            path: The path to append to the target URL.

        Returns:
            The response from the target service.
        """
        url = f"{target_url}/{path}"

        # Prepare headers
        headers = dict(request.headers)
        # Remove headers that will be set by the new request
        headers.pop("host", None)
        headers.pop("content-length", None)

        try:
            # Read body
            body = await request.body()

            response = await self.client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=body,
                params=request.query_params,
            )

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type"),
            )

        except httpx.RequestError as exc:
            logger.error(f"Proxy error to {url}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error communicating with upstream service: {str(exc)}"
            )
        except Exception as exc:
            logger.error(f"Unexpected error proxying to {url}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal Gateway Error"
            )
