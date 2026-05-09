from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
from typing import Any

from app.core.tool.contracts import ToolContext, ToolHandler


class ToolExecutionTimeoutError(TimeoutError):
    pass


@dataclass
class ToolExecutor:
    max_workers: int = 4

    def __post_init__(self) -> None:
        self._pool = ThreadPoolExecutor(max_workers=self.max_workers)

    def execute(self, *, handler: ToolHandler, arguments: dict[str, Any], context: ToolContext, timeout_seconds: int | None = None) -> Any:
        if timeout_seconds is None or timeout_seconds <= 0:
            return handler(arguments=arguments, context=context)

        future = self._pool.submit(handler, arguments=arguments, context=context)
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeout as exc:
            future.cancel()
            raise ToolExecutionTimeoutError(f"tool execution timed out after {timeout_seconds}s") from exc
