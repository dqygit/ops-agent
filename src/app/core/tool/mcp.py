from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from app.core.loop.loop_events import LoopEvent
from app.core.loop.loop_state import LoopState
from app.core.loop.message_manager import MessageManager
from app.core.tool.handler import ToolDisplayMetadata
from app.core.tool.schema import LLMToolDefinition
from app.services.mcp_config_store import MCPServerConfig, MCPToolConfig
from app.services.mcp_service import McpService


class McpToolHandler:
    def __init__(
        self,
        *,
        service: McpService,
        server: MCPServerConfig,
        tool: MCPToolConfig,
    ) -> None:
        self._service = service
        self._server = server
        self._tool = tool

    @property
    def definition(self) -> LLMToolDefinition:
        return LLMToolDefinition(
            name=self._tool.exposed_name,
            description=self._tool.description or f"MCP tool {self._tool.original_name}",
            input_schema=self._tool.input_schema or {"type": "object", "properties": {}},
        )

    def needs_approval(self, args: dict[str, Any]) -> tuple[str, str]:
        _ = args
        if self._tool.approval_policy == "allow":
            return "allow", "MCP tool policy allows execution."
        if self._tool.approval_policy == "deny":
            return "deny", "MCP tool policy denies execution."
        return "ask", "MCP tool requires operator approval."

    def display_metadata(self, args: dict[str, Any]) -> ToolDisplayMetadata:
        _ = args
        return ToolDisplayMetadata(
            description=self._tool.description or f"MCP tool {self._tool.original_name}",
            display_text=f"Call MCP tool {self._tool.exposed_name}",
            extra={
                "kind": "mcp",
                "originalName": self._tool.original_name,
                "serverId": self._server.id,
            },
        )

    def execute(
        self,
        *,
        state: LoopState,
        step_id: str,
        args: dict[str, Any],
        manager: MessageManager | None = None,
    ) -> Iterator[LoopEvent]:
        _ = state, step_id
        result = self._service.call_tool(self._server, self._tool, args)
        output = self._service.normalize_output(result)
        if manager:
            yield from manager.update(tool_output=output)
        return result.ok, output
