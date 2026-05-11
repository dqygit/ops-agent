"""审批策略配置 API。"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.approval_service import get_approval_service


router = APIRouter()


class ApprovalPolicyView(BaseModel):
    """审批策略视图。"""
    mode: str
    rules: list[dict[str, Any]]


class ApprovalRuleCreate(BaseModel):
    """创建审批规则请求。"""
    pattern: str
    action: str
    description: str = ""


class ApprovalModeUpdate(BaseModel):
    """更新审批模式请求。"""
    mode: str


@router.get("/api/approval/policy")
def get_approval_policy() -> ApprovalPolicyView:
    """获取当前审批策略配置。"""
    service = get_approval_service()
    policy_dict = service.get_policy_dict()
    return ApprovalPolicyView(**policy_dict)


@router.put("/api/approval/policy")
def update_approval_policy(policy: ApprovalPolicyView) -> dict[str, str]:
    """更新审批策略配置。"""
    service = get_approval_service()
    service.update_policy_from_dict(policy.model_dump())
    return {"message": "审批策略已更新"}


@router.post("/api/approval/rules")
def add_approval_rule(rule: ApprovalRuleCreate) -> dict[str, str]:
    """添加审批规则。"""
    if rule.action not in ["allow", "deny", "ask"]:
        raise HTTPException(status_code=400, detail="action 必须是 allow, deny 或 ask")
    
    service = get_approval_service()
    service.add_rule(rule.pattern, rule.action, rule.description)
    return {"message": "审批规则已添加"}


@router.delete("/api/approval/rules/{pattern}")
def delete_approval_rule(pattern: str) -> dict[str, str]:
    """删除审批规则。"""
    service = get_approval_service()
    if service.remove_rule(pattern):
        return {"message": "审批规则已删除"}
    raise HTTPException(status_code=404, detail="规则不存在")


@router.put("/api/approval/mode")
def update_approval_mode(update: ApprovalModeUpdate) -> dict[str, str]:
    """更新审批模式。"""
    if update.mode not in ["strict", "permissive"]:
        raise HTTPException(status_code=400, detail="mode 必须是 strict 或 permissive")
    
    service = get_approval_service()
    service.update_mode(update.mode)
    return {"message": "审批模式已更新"}


@router.post("/api/approval/check")
def check_command(request: dict[str, str]) -> dict[str, str]:
    """检查命令是否需要审批。"""
    command = request.get("command", "")
    if not command:
        raise HTTPException(status_code=400, detail="command 参数必填")
    
    service = get_approval_service()
    action, reason = service.check_command(command)
    return {"action": action, "reason": reason, "command": command}
