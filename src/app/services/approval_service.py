"""命令审批服务模块。

提供命令审批策略的管理和检查功能。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, cast

from app.core.approval import ApprovalChecker, ApprovalPolicy, ApprovalRule, create_default_policy
from app.shared.config import SETTINGS_PATH


class ApprovalService:
    """审批服务。"""
    
    def __init__(self, config_path: str | None = None):
        """初始化审批服务。
        
        Args:
            config_path: 配置文件路径，默认为 ./config/approval_policy.json
        """
        if config_path is None:
            config_path = str(SETTINGS_PATH)
        
        self._config_path = Path(config_path)
        self._policy = self._load_policy()
        self._checker = ApprovalChecker(self._policy)
    
    def _load_policy(self) -> ApprovalPolicy:
        """从配置文件加载策略。"""
        if not self._config_path.exists():
            # 创建默认配置
            policy = create_default_policy()
            self._save_policy(policy)
            return policy
        
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            approval_data = data.get("approval") if isinstance(data, dict) else None
            if not isinstance(approval_data, dict):
                approval_data = {}
            
            rules = [
                ApprovalRule(
                    pattern=rule["pattern"],
                    action=cast(Literal["allow", "deny", "ask"], rule["action"]),
                    description=rule.get("description", "")
                )
                for rule in approval_data.get("rules", [])
            ]
            
            return ApprovalPolicy(
                mode=cast(Literal["strict", "permissive"], approval_data.get("mode", "strict")),
                rules=rules
            )
        except Exception:
            # 加载失败，返回默认策略
            return create_default_policy()
    
    def _save_policy(self, policy: ApprovalPolicy | None = None) -> None:
        """保存策略到配置文件。"""
        if policy is None:
            policy = self._policy
        
        # 确保目录存在
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        
        rules = policy.rules or []
        existing_data: dict[str, Any] = {}
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    existing_data = loaded
            except Exception:
                existing_data = {}

        existing_data["approval"] = {
            "mode": policy.mode,
            "rules": [
                {
                    "pattern": rule.pattern,
                    "action": rule.action,
                    "description": rule.description
                }
                for rule in rules
            ]
        }
        
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
    
    def check_command(self, command: str) -> tuple[str, str]:
        """检查命令是否需要审批。
        
        Returns:
            (action, reason) - action 为 allow/deny/ask
        """
        return self._checker.check_command(command)
    
    def get_policy_dict(self) -> dict[str, Any]:
        """获取策略配置字典。"""
        rules = self._policy.rules or []
        return {
            "mode": self._policy.mode,
            "rules": [
                {
                    "pattern": rule.pattern,
                    "action": rule.action,
                    "description": rule.description
                }
                for rule in rules
            ]
        }
    
    def update_policy_from_dict(self, data: dict[str, Any]) -> None:
        """从字典更新策略配置。"""
        rules = [
            ApprovalRule(
                pattern=rule["pattern"],
                action=cast(Literal["allow", "deny", "ask"], rule["action"]),
                description=rule.get("description", "")
            )
            for rule in data.get("rules", [])
        ]
        
        self._policy = ApprovalPolicy(
            mode=cast(Literal["strict", "permissive"], data.get("mode", "strict")),
            rules=rules
        )
        self._checker = ApprovalChecker(self._policy)
        self._save_policy()
    
    def add_rule(self, pattern: str, action: str, description: str = "") -> None:
        """添加审批规则。"""
        rule = ApprovalRule(
            pattern=pattern,
            action=cast(Literal["allow", "deny", "ask"], action),
            description=description
        )
        if self._policy.rules is None:
            self._policy.rules = []
        self._policy.rules.append(rule)
        self._save_policy()
    
    def remove_rule(self, pattern: str) -> bool:
        """删除审批规则。
        
        Returns:
            是否成功删除
        """
        if self._policy.rules is None:
            return False
        
        original_len = len(self._policy.rules)
        self._policy.rules = [r for r in self._policy.rules if r.pattern != pattern]
        
        if len(self._policy.rules) < original_len:
            self._save_policy()
            return True
        return False
    
    def update_mode(self, mode: str) -> None:
        """更新审批模式。"""
        self._policy.mode = cast(Literal["strict", "permissive"], mode)
        self._checker = ApprovalChecker(self._policy)
        self._save_policy()


# 全局单例
_approval_service: ApprovalService | None = None


def get_approval_service() -> ApprovalService:
    """获取全局审批服务实例。"""
    global _approval_service
    if _approval_service is None:
        _approval_service = ApprovalService()
    return _approval_service
