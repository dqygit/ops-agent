import re

from sqlmodel import Session

from app.db.models import AutoApprovalRule
from app.db.repositories import create_audit_log, create_auto_approval_match, create_auto_approval_rule, delete_auto_approval_rule, list_auto_approval_rules_by_session_id, update_auto_approval_rule

RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
READONLY_PREFIXES = (
    "ls",
    "cat",
    "df",
    "du",
    "free",
    "top",
    "ps",
    "netstat",
    "ss",
    "uptime",
    "uname",
    "journalctl",
    "show ",
    "display ",
)
DANGEROUS_TOKENS = ("rm ", "mv ", "chmod ", "chown ", "kill", "reboot", "shutdown", "systemctl restart")
SHELL_OPERATORS = (";", "&&", "||", "|", ">", "<", "`", "$(")


def tags_to_text(tags: list[str]) -> str:
    return ",".join(tags)


def tags_from_text(tags: str) -> list[str]:
    return [tag for tag in tags.split(",") if tag]


class AutoApprovalService:
    def create_rule(self, session: Session, session_id: int, payload) -> AutoApprovalRule:
        data = payload.model_dump(exclude={"asset_tags"})
        rule = create_auto_approval_rule(session, session_id=session_id, **data, asset_tags=tags_to_text(payload.asset_tags))
        create_audit_log(session, action="auto_approval_rule.created", entity_type="auto_approval_rule", entity_id=rule.id, session_id=session_id)
        return rule

    def list_rules(self, session: Session, session_id: int) -> list[AutoApprovalRule]:
        return list_auto_approval_rules_by_session_id(session, session_id)

    def update_rule(self, session: Session, rule_id: int, payload) -> AutoApprovalRule | None:
        updates = payload.model_dump(exclude_unset=True, exclude={"asset_tags"})
        if payload.asset_tags is not None:
            updates["asset_tags"] = tags_to_text(payload.asset_tags)
        rule = update_auto_approval_rule(session, rule_id, **updates)
        if rule is not None:
            create_audit_log(session, action="auto_approval_rule.updated", entity_type="auto_approval_rule", entity_id=rule.id, session_id=rule.session_id)
        return rule

    def delete_rule(self, session: Session, rule_id: int) -> bool:
        deleted = delete_auto_approval_rule(session, rule_id)
        if deleted:
            create_audit_log(session, action="auto_approval_rule.deleted", entity_type="auto_approval_rule", entity_id=rule_id)
        return deleted

    def match_rule(
        self,
        session: Session,
        session_id: int,
        *,
        asset_type: str,
        asset_tags: list[str],
        command: str,
        risk_level: str,
        estimated_duration_seconds: int | None = None,
    ) -> tuple[AutoApprovalRule | None, str]:
        normalized_command = command.strip().lower()
        if RISK_ORDER.get(risk_level, 3) >= RISK_ORDER["high"]:
            return None, "high risk commands require manual approval"
        for rule in list_auto_approval_rules_by_session_id(session, session_id):
            if not rule.enabled:
                continue
            reason = self._match_single(
                rule,
                asset_type=asset_type,
                asset_tags=asset_tags,
                command=normalized_command,
                risk_level=risk_level,
                estimated_duration_seconds=estimated_duration_seconds,
            )
            if reason:
                return rule, reason
        return None, "no matching rule"

    def record_match(self, session: Session, *, rule: AutoApprovalRule, approval_id: int, task_id: int, step_id: int | None, reason: str) -> None:
        create_auto_approval_match(session, rule_id=rule.id or 0, approval_id=approval_id, task_id=task_id, step_id=step_id, reason=reason)
        create_audit_log(session, action="auto_approval.matched", entity_type="auto_approval_rule", entity_id=rule.id, session_id=rule.session_id, task_id=task_id, details=reason)

    def _match_single(
        self,
        rule: AutoApprovalRule,
        *,
        asset_type: str,
        asset_tags: list[str],
        command: str,
        risk_level: str,
        estimated_duration_seconds: int | None = None,
    ) -> str:
        if RISK_ORDER.get(risk_level, 3) > RISK_ORDER.get(rule.max_risk_level, 0):
            return ""
        if estimated_duration_seconds is not None and estimated_duration_seconds > rule.max_duration_seconds:
            return ""
        if rule.asset_type and rule.asset_type != asset_type:
            return ""
        required_tags = set(tags_from_text(rule.asset_tags))
        if required_tags and not required_tags.issubset(set(asset_tags)):
            return ""
        if rule.readonly_only and not self._is_readonly(command):
            return ""
        if rule.command_name and not command.startswith(rule.command_name.lower()):
            return ""
        if rule.command_pattern and re.search(rule.command_pattern, command) is None:
            return ""
        return f"matched rule {rule.name}"

    def _is_readonly(self, command: str) -> bool:
        if any(operator in command for operator in SHELL_OPERATORS):
            return False
        if any(token in command for token in DANGEROUS_TOKENS):
            return False
        return any(command == prefix.strip() or command.startswith(prefix) for prefix in READONLY_PREFIXES)
