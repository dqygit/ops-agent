"""命令审批策略模块。

基于配置文件判断命令是否需要用户审批。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ApprovalRule:
    """审批规则。"""
    pattern: str  # 正则表达式模式
    action: Literal["allow", "deny", "ask"]  # allow=自动通过, deny=拒绝, ask=需要审批
    description: str = ""


@dataclass
class ApprovalPolicy:
    """审批策略配置。"""
    mode: Literal["strict", "permissive"] = "strict"  # strict=默认需审批, permissive=默认允许
    rules: list[ApprovalRule] | None = field(default_factory=list)


class ApprovalChecker:
    """命令审批检查器。"""
    
    def __init__(self, policy: ApprovalPolicy):
        self._policy = policy
    
    def check_command(self, command: str) -> tuple[Literal["allow", "deny", "ask"], str]:
        """检查命令是否需要审批。
        
        Returns:
            (action, reason) - action 为 allow/deny/ask, reason 为原因说明
        """
        command = command.strip()
        
        # 按顺序匹配规则
        rules = self._policy.rules or []
        for rule in rules:
            try:
                if re.search(rule.pattern, command, re.IGNORECASE):
                    reason = rule.description or f"匹配规则: {rule.pattern}"
                    return rule.action, reason
            except re.error:
                continue
        
        # 没有匹配规则，使用默认策略
        if self._policy.mode == "permissive":
            return "allow", "默认策略：允许执行"
        else:
            return "ask", "默认策略：需要审批"


def create_default_policy() -> ApprovalPolicy:
    """创建默认审批策略。"""
    return ApprovalPolicy(
        mode="strict",
        rules=[
            # 安全的只读命令 - 自动允许
            ApprovalRule(pattern=r"^(ls|pwd|whoami|echo|cat|head|tail|grep|find|which|type)\b", action="allow", description="安全的只读命令"),
            ApprovalRule(pattern=r"^(ps|top|df|du|free|uptime|date|hostname)\b", action="allow", description="系统信息查询命令"),
            
            # 危险命令 - 拒绝
            ApprovalRule(pattern=r"^(rm\s+-rf\s+/|mkfs|dd\s+if=.*of=/dev/)", action="deny", description="危险的系统破坏命令"),
            ApprovalRule(pattern=r":(){ :|:& };:", action="deny", description="Fork 炸弹"),
            
            # 需要审批的命令
            ApprovalRule(pattern=r"^(rm|mv|cp|chmod|chown|kill|pkill|systemctl|service)\b", action="ask", description="可能影响系统的命令"),
            ApprovalRule(pattern=r"^(apt|yum|dnf|pacman|brew)\s+(install|remove|update|upgrade)", action="ask", description="软件包管理命令"),
            ApprovalRule(pattern=r"^(docker|kubectl|helm)\b", action="ask", description="容器编排命令"),
        ]
    )
