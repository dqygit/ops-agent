from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import (
    MCPConnectionTestResponse,
    MCPServerCreate,
    MCPServerEnableRequest,
    MCPServerUpdate,
    MCPServerView,
    MCPToolUpdate,
)
from app.services.mcp_service import McpService

router = APIRouter()


def get_mcp_service() -> McpService:
    return McpService()


def redacted_server_view(service: McpService, server: Any) -> MCPServerView:
    return MCPServerView(**service.store.redacted_server(server))


def find_server_by_tool_id(service: McpService, tool_id: str) -> Any | None:
    for server in service.list_servers():
        if any(tool.id == tool_id for tool in server.tools):
            return server
    return None


@router.get("/api/mcp/servers")
def list_mcp_servers(service: McpService = Depends(get_mcp_service)) -> list[MCPServerView]:
    return [redacted_server_view(service, server) for server in service.list_servers()]


@router.post("/api/mcp/servers", status_code=201)
def create_mcp_server(
    payload: MCPServerCreate,
    service: McpService = Depends(get_mcp_service),
) -> MCPServerView:
    server = service.store.create_server(**payload.model_dump())
    return redacted_server_view(service, server)


@router.put("/api/mcp/servers/{server_id}")
def update_mcp_server(
    server_id: str,
    payload: MCPServerUpdate,
    service: McpService = Depends(get_mcp_service),
) -> MCPServerView:
    server = service.store.update_server(server_id, **payload.model_dump(exclude_unset=True))
    if server is None:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return redacted_server_view(service, server)


@router.delete("/api/mcp/servers/{server_id}")
def delete_mcp_server(
    server_id: str,
    service: McpService = Depends(get_mcp_service),
) -> dict[str, bool]:
    if not service.store.delete_server(server_id):
        raise HTTPException(status_code=404, detail="MCP server not found")
    return {"success": True}


@router.post("/api/mcp/servers/{server_id}/enabled")
def set_mcp_server_enabled(
    server_id: str,
    payload: MCPServerEnableRequest,
    service: McpService = Depends(get_mcp_service),
) -> MCPServerView:
    try:
        server = service.store.set_server_enabled(server_id, payload.enabled)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if server is None:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return redacted_server_view(service, server)


@router.post("/api/mcp/servers/{server_id}/refresh")
def refresh_mcp_server(
    server_id: str,
    service: McpService = Depends(get_mcp_service),
) -> MCPServerView:
    server = service.refresh_server(server_id)
    if server is None:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return redacted_server_view(service, server)


@router.post("/api/mcp/servers/{server_id}/test")
def test_mcp_server(
    server_id: str,
    service: McpService = Depends(get_mcp_service),
) -> MCPConnectionTestResponse:
    server = service.refresh_server(server_id)
    if server is None:
        raise HTTPException(status_code=404, detail="MCP server not found")

    server_view = redacted_server_view(service, server)
    if server.last_refresh_succeeded:
        return MCPConnectionTestResponse(
            success=True,
            message="Connection succeeded",
            server=server_view,
        )
    return MCPConnectionTestResponse(
        success=False,
        message=server.last_error or "Connection failed",
        server=server_view,
    )


@router.patch("/api/mcp/tools/{tool_id}")
def update_mcp_tool(
    tool_id: str,
    payload: MCPToolUpdate,
    service: McpService = Depends(get_mcp_service),
) -> MCPServerView:
    tool = service.store.update_tool(tool_id, **payload.model_dump(exclude_unset=True))
    if tool is None:
        raise HTTPException(status_code=404, detail="MCP tool not found")

    server = find_server_by_tool_id(service, tool_id)
    if server is None:
        raise HTTPException(status_code=404, detail="MCP tool not found")
    return redacted_server_view(service, server)
