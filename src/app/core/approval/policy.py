"""命令审批策略模块。

基于 permissions.allow / permissions.deny 判断命令是否需要用户审批。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ApprovalPermissions:
    """自动允许或拒绝执行的命令前缀。"""

    allow: list[str] = field(default_factory=list)
    deny: list[str] = field(default_factory=list)


@dataclass
class ApprovalPolicy:
    """审批策略配置。"""

    permissions: ApprovalPermissions = field(default_factory=ApprovalPermissions)


class ApprovalChecker:
    """命令审批检查器。"""

    def __init__(self, policy: ApprovalPolicy):
        self._policy = policy

    def check_command(self, command: str) -> tuple[str, str]:
        """检查命令是否需要审批。"""
        command = command.strip()
        for prefix in self._policy.permissions.deny:
            if _matches_command_prefix(prefix, command):
                return "deny", f"匹配拒绝前缀: {prefix}"
        for prefix in self._policy.permissions.allow:
            if _matches_command_prefix(prefix, command):
                return "allow", f"匹配允许前缀: {prefix}"
        return "ask", "默认策略：需要审批"


def _matches_command_prefix(prefix: str, command: str) -> bool:
    prefix = prefix.strip()
    if not prefix:
        return False
    if prefix == "*":
        return True

    return command == prefix or command.startswith(f"{prefix} ")


def create_default_policy() -> ApprovalPolicy:
    """创建默认审批策略。"""
    return ApprovalPolicy(permissions=ApprovalPermissions())
