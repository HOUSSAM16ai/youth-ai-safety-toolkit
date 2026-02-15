import uvicorn
from fastapi import FastAPI

from app.config import DEFAULT_GATEWAY_CONFIG
from app.gateway import APIGateway

app = FastAPI(title="CogniForge API Gateway", version="1.0.0")

# Initialize the Gateway
gateway = APIGateway(config=DEFAULT_GATEWAY_CONFIG)

# Mount the Gateway Router
# Note: The gateway router should handle routing logic based on config
app.include_router(gateway.router)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "api-gateway"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
