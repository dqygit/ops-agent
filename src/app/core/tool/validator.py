from __future__ import annotations

from typing import Any

from app.core.tool.contracts import ToolDefinition


class ToolValidationError(ValueError):
    pass


class ToolArgumentValidator:
    def validate(self, definition: ToolDefinition, arguments: dict[str, Any]) -> dict[str, Any]:
        schema = definition.input_schema or {}
        if schema.get("type") == "object" and not isinstance(arguments, dict):
            raise ToolValidationError("tool arguments must be an object")

        required = schema.get("required")
        if isinstance(required, list):
            missing = [key for key in required if key not in arguments]
            if missing:
                raise ToolValidationError(f"missing required arguments: {', '.join(missing)}")

        properties = schema.get("properties")
        if isinstance(properties, dict):
            additional = schema.get("additionalProperties", True)
            if additional is False:
                unknown = [key for key in arguments if key not in properties]
                if unknown:
                    raise ToolValidationError(f"unknown arguments: {', '.join(unknown)}")

        return arguments
