"""命令审批服务模块。

提供命令审批权限的管理和检查功能。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.approval import ApprovalChecker, ApprovalContext, ApprovalPermissions, ApprovalPolicy, create_default_policy
from app.shared.config import SETTINGS_PATH


class ApprovalService:
    """审批服务。"""

    def __init__(self, config_path: str | None = None):
        if config_path is None:
            config_path = str(SETTINGS_PATH)

        self._config_path = Path(config_path)
        self._policy = self._load_policy()
        self._checker = ApprovalChecker(self._policy)

    def _load_policy(self) -> ApprovalPolicy:
        """从配置文件加载策略。"""
        if not self._config_path.exists():
            policy = create_default_policy()
            self._save_policy(policy)
            return policy

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            permissions_data = data.get("permissions") if isinstance(data, dict) else None
            if isinstance(permissions_data, dict):
                allow = [item.strip() for item in permissions_data.get("allow", []) if isinstance(item, str) and item.strip()]
                deny = [item.strip() for item in permissions_data.get("deny", []) if isinstance(item, str) and item.strip()]
                return ApprovalPolicy(permissions=ApprovalPermissions(allow=allow, deny=deny))

            approval_data = data.get("approval") if isinstance(data, dict) else None
            if isinstance(approval_data, dict):
                policy = create_default_policy()
                self._save_policy(policy)
                return policy
        except Exception:
            return create_default_policy()

        policy = create_default_policy()
        self._save_policy(policy)
        return policy

    def _save_policy(self, policy: ApprovalPolicy | None = None) -> None:
        """保存策略到配置文件。"""
        if policy is None:
            policy = self._policy

        self._config_path.parent.mkdir(parents=True, exist_ok=True)

        existing_data: dict[str, Any] = {}
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    existing_data = loaded
            except Exception:
                existing_data = {}

        existing_data.pop("approval", None)
        existing_data["permissions"] = {"allow": policy.permissions.allow, "deny": policy.permissions.deny}

        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)

    def check_command(self, command: str, context: ApprovalContext | None = None) -> tuple[str, str]:
        """检查命令是否需要审批。"""
        return self._checker.check_command(command, context)

    def add_allow_prefix(self, prefix: str) -> bool:
        """添加允许执行的命令前缀。"""
        prefix = prefix.strip()
        if not prefix or prefix in self._policy.permissions.allow:
            return False
        self._policy.permissions.allow.append(prefix)
        self._checker = ApprovalChecker(self._policy)
        self._save_policy()
        return True

    def get_policy_dict(self) -> dict[str, Any]:
        """获取策略配置字典。"""
        return {"permissions": {"allow": self._policy.permissions.allow, "deny": self._policy.permissions.deny}}

    def update_policy_from_dict(self, data: dict[str, Any]) -> None:
        """从字典更新策略配置。"""
        permissions_data = data.get("permissions") if isinstance(data, dict) else None
        allow = permissions_data.get("allow", []) if isinstance(permissions_data, dict) else []
        deny = permissions_data.get("deny", []) if isinstance(permissions_data, dict) else []
        self._policy = ApprovalPolicy(
            permissions=ApprovalPermissions(
                allow=[item.strip() for item in allow if isinstance(item, str) and item.strip()],
                deny=[item.strip() for item in deny if isinstance(item, str) and item.strip()],
            )
        )
        self._checker = ApprovalChecker(self._policy)
        self._save_policy()


_approval_service: ApprovalService | None = None


def get_approval_service() -> ApprovalService:
    """获取全局审批服务实例。"""
    global _approval_service
    if _approval_service is None:
        _approval_service = ApprovalService()
    return _approval_service
