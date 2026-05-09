from __future__ import annotations

from typing import Any

from app.core.tool.contracts import ToolCall, ToolContext, ToolError, ToolEvent, ToolResult
from app.core.tool.events import ToolEventPublisher
from app.core.tool.executor import ToolExecutionTimeoutError, ToolExecutor
from app.core.tool.policy import ToolPolicy
from app.core.tool.registry import ToolRegistry
from app.core.tool.validator import ToolArgumentValidator, ToolValidationError


class ToolRuntime:
    def __init__(
        self,
        *,
        registry: ToolRegistry,
        policy: ToolPolicy | None = None,
        validator: ToolArgumentValidator | None = None,
        executor: ToolExecutor | None = None,
        events: ToolEventPublisher | None = None,
    ) -> None:
        self._registry = registry
        self._policy = policy or ToolPolicy()
        self._validator = validator or ToolArgumentValidator()
        self._executor = executor or ToolExecutor()
        self._events = events or ToolEventPublisher()

    def run_tool_call(self, *, call: ToolCall, context: ToolContext) -> ToolResult:
        registered = self._registry.get(call.name)
        if registered is None:
            return ToolResult(ok=False, error=ToolError(code="not_found", message=f"tool not found: {call.name}"))

        policy = self._policy.evaluate(call.name, context)
        if policy.decision == "deny":
            return ToolResult(ok=False, error=ToolError(code="forbidden", message=policy.reason or "tool denied"))
        if policy.decision == "confirm":
            return ToolResult(ok=False, error=ToolError(code="forbidden", message=policy.reason or "tool requires confirmation"))

        self._events.publish(ToolEvent(type="tool_started", tool_name=call.name, tool_call_id=call.id))

        try:
            validated_arguments = self._validator.validate(registered.definition, call.arguments)
            output = self._executor.execute(
                handler=registered.handler,
                arguments=validated_arguments,
                context=context,
                timeout_seconds=registered.definition.timeout_seconds,
            )
        except ToolValidationError as exc:
            self._events.publish(
                ToolEvent(type="tool_failed", tool_name=call.name, tool_call_id=call.id, detail=str(exc))
            )
            return ToolResult(ok=False, error=ToolError(code="invalid_arguments", message=str(exc)))
        except ToolExecutionTimeoutError as exc:
            self._events.publish(
                ToolEvent(type="tool_failed", tool_name=call.name, tool_call_id=call.id, detail=str(exc))
            )
            return ToolResult(ok=False, error=ToolError(code="timeout", message=str(exc)))
        except Exception as exc:
            self._events.publish(
                ToolEvent(type="tool_failed", tool_name=call.name, tool_call_id=call.id, detail=str(exc))
            )
            return ToolResult(ok=False, error=ToolError(code="execution_error", message=str(exc)))

        self._events.publish(ToolEvent(type="tool_succeeded", tool_name=call.name, tool_call_id=call.id))
        return ToolResult(ok=True, output=output)

    def list_events(self) -> list[ToolEvent]:
        return self._events.list_events()

    def list_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
                "source": tool.source,
            }
            for tool in self._registry.list_definitions()
        ]
