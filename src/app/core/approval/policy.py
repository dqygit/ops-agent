"""命令审批策略模块。

基于 permissions.allow / permissions.deny 判断命令是否需要用户审批。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.connectors.device_profiles import NETWORK_CLI_PROFILE, matches_command_prefix, select_device_profile


@dataclass
class ApprovalPermissions:
    """自动允许或拒绝执行的命令前缀。"""

    allow: list[str] = field(default_factory=list)
    deny: list[str] = field(default_factory=list)


@dataclass
class ApprovalPolicy:
    """审批策略配置。"""

    permissions: ApprovalPermissions = field(default_factory=ApprovalPermissions)


@dataclass(frozen=True, slots=True)
class ApprovalContext:
    asset_type: str = ""
    shell_type: str = ""
    profile: str = "posix-shell"
    vendor: str | None = None


class ApprovalChecker:
    """命令审批检查器。"""

    def __init__(self, policy: ApprovalPolicy):
        self._policy = policy

    def check_command(self, command: str, context: ApprovalContext | None = None) -> tuple[str, str]:
        """检查命令是否需要审批。"""
        command = command.strip()
        for prefix in self._policy.permissions.deny:
            if _matches_command_prefix(prefix, command):
                return "deny", f"匹配拒绝前缀: {prefix}"

        effective_context = context or ApprovalContext()
        if effective_context.profile == NETWORK_CLI_PROFILE:
            level = _classify_network_command(command, effective_context)
            for prefix in self._policy.permissions.allow:
                if _matches_command_prefix(prefix, command) and level == 0:
                    return "allow", f"匹配允许前缀: {prefix}"
            if level == 0:
                return "ask", "网络设备只读命令，按默认审批策略处理"
            if level == 1:
                return "ask", "网络设备模式切换命令需要审批"
            if level == 2:
                return "ask", "网络设备配置变更命令必须审批"
            if level == 3:
                return "ask", "网络设备保存配置命令必须单独审批"
            return "ask", "网络设备高危命令必须审批"

        for prefix in self._policy.permissions.allow:
            if _matches_command_prefix(prefix, command):
                return "allow", f"匹配允许前缀: {prefix}"
        return "ask", "默认策略：需要审批"


def _matches_command_prefix(prefix: str, command: str) -> bool:
    return matches_command_prefix(prefix, command)


def create_default_policy() -> ApprovalPolicy:
    """创建默认审批策略。"""
    return ApprovalPolicy(permissions=ApprovalPermissions())


def _classify_network_command(command: str, context: ApprovalContext) -> int:
    normalized = command.strip().lower()
    if not normalized:
        return 4

    profile = select_device_profile(context.asset_type, context.shell_type)
    level0_prefixes = profile.read_prefixes if profile is not None else ("show", "display", "ping", "traceroute", "tracert", "?")
    level1_prefixes = profile.config_entry + profile.config_exit if profile is not None else ("configure terminal", "conf t", "system-view", "configure", "end", "return")
    level3_prefixes = profile.save_commands if profile is not None else ("write memory", "copy running-config startup-config", "save", "commit")
    level4_prefixes = ("reload", "reset", "delete", "erase", "shutdown", "format")
    level2_prefixes = ("interface", "vlan", "ip route", "acl", "undo", "no ")

    if _matches_any(level4_prefixes, normalized):
        return 4
    if _matches_any(level3_prefixes, normalized):
        return 3
    if _matches_any(level2_prefixes, normalized):
        return 2
    if _matches_any(level1_prefixes, normalized):
        return 1
    if _matches_any(level0_prefixes, normalized):
        return 0
    return 2


def _matches_any(prefixes: tuple[str, ...], command: str) -> bool:
    return any(_matches_command_prefix(prefix, command) for prefix in prefixes)
