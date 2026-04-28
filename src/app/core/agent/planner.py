from app.core.agent.classifier import classify_task
from app.core.executor.command_catalog import get_commands_for_task
from app.shared.enums import AssetType
from app.shared.schemas import PlanStep, TerminalContextAttachment


TITLE_MAP = {
    "interface_status": "Check interface status",
    "routing_table": "Check routing table",
    "neighbor_status": "Check neighbor status",
    "system_resources": "Check system resources",
    "network_health": "Check network health",
}


def build_plan(
    asset_type: AssetType,
    user_input: str,
    terminal_context: TerminalContextAttachment | None = None,
    recent_messages: list[dict] | None = None,
) -> list[PlanStep]:
    task_type = classify_task(user_input)
    context_note = terminal_context.selection_label if terminal_context else "no terminal context attached"
    return [
        PlanStep(
            title=TITLE_MAP[task_type],
            command=command,
            reason=f"Selected from the readonly catalog with {context_note}",
            risk_level="low",
        )
        for command in get_commands_for_task(asset_type, task_type)
    ]
