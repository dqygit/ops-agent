from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.core.tool.contracts import ToolContext

PolicyDecision = Literal["allow", "deny", "confirm"]


@dataclass(frozen=True)
class PolicyResult:
    decision: PolicyDecision
    reason: str = ""


@dataclass
class ToolPolicy:
    default_decision: PolicyDecision = "allow"
    allow_tools: set[str] = field(default_factory=set)
    deny_tools: set[str] = field(default_factory=set)
    confirm_tools: set[str] = field(default_factory=set)

    def evaluate(self, tool_name: str, context: ToolContext) -> PolicyResult:
        _ = context
        if tool_name in self.deny_tools:
            return PolicyResult(decision="deny", reason="tool denied by policy")
        if tool_name in self.confirm_tools:
            return PolicyResult(decision="confirm", reason="tool requires confirmation")
        if self.allow_tools:
            if tool_name in self.allow_tools:
                return PolicyResult(decision="allow")
            return PolicyResult(decision="deny", reason="tool not in allow list")
        return PolicyResult(decision=self.default_decision)
