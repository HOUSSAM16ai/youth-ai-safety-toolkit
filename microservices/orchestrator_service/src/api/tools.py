import asyncio
import inspect

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from microservices.orchestrator_service.src.services.overmind.graph.admin import ADMIN_TOOLS

router = APIRouter(prefix="/api/v1/tools", tags=["MCP Kagent Tools"])


class ToolInvokeRequest(BaseModel):
    args: dict


@router.post("/{tool_name}/invoke")
async def invoke_tool(tool_name: str, request: ToolInvokeRequest):
    for tool in ADMIN_TOOLS:
        if tool.name == tool_name:
            try:
                if asyncio.iscoroutinefunction(tool.invoke) or inspect.iscoroutinefunction(
                    tool.func
                ):
                    res = await tool.ainvoke(request.args)
                else:
                    res = tool.invoke(request.args)
                return res
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e)) from e
    raise HTTPException(status_code=404, detail="Tool not found")


@router.get("/{tool_name}/schema")
async def get_tool_schema(tool_name: str):
    for tool in ADMIN_TOOLS:
        if tool.name == tool_name:
            return (
                tool.args_schema.schema()
                if tool.args_schema
                else {"type": "object", "properties": {}}
            )
    raise HTTPException(status_code=404, detail="Tool not found")


@router.get("/{tool_name}/health")
async def tool_health(tool_name: str):
    for tool in ADMIN_TOOLS:
        if tool.name == tool_name:
            return {"status": "ok", "tool": tool.name}
    raise HTTPException(status_code=404, detail="Tool not found")
