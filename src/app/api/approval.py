"""审批权限配置 API。"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.approval import ApprovalContext
from app.services.approval_service import get_approval_service


router = APIRouter()


class ApprovalPermissionsView(BaseModel):
    """审批权限视图。"""

    allow: list[str]
    deny: list[str]


class ApprovalPolicyView(BaseModel):
    """审批策略视图。"""

    permissions: ApprovalPermissionsView


class ApprovalContextView(BaseModel):
    asset_type: str = ""
    shell_type: str = ""
    profile: str = "posix-shell"
    vendor: str | None = None


class ApprovalCheckRequest(BaseModel):
    command: str
    context: ApprovalContextView | None = None


@router.get("/api/approval/policy")
def get_approval_policy() -> ApprovalPolicyView:
    """获取当前审批权限配置。"""
    service = get_approval_service()
    policy_dict = service.get_policy_dict()
    return ApprovalPolicyView(**policy_dict)


@router.put("/api/approval/policy")
def update_approval_policy(policy: ApprovalPolicyView) -> dict[str, str]:
    """更新审批权限配置。"""
    service = get_approval_service()
    service.update_policy_from_dict(policy.model_dump())
    return {"message": "审批权限已更新"}


@router.post("/api/approval/check")
def check_command(request: ApprovalCheckRequest) -> dict[str, str]:
    """检查命令是否需要审批。"""
    command = request.command
    if not command:
        raise HTTPException(status_code=400, detail="command 参数必填")

    service = get_approval_service()
    action, reason = service.check_command(
        command,
        context=None if request.context is None else ApprovalContext(**request.context.model_dump()),
    )
    return {"action": action, "reason": reason, "command": command}
