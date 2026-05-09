def needs_approval(risk_level: str) -> bool:
    normalized = (risk_level or "low").strip().lower()
    return normalized in {"medium", "high"}



def plan_requires_replan(
    *,
    proposed_command: str,
    locked_command: str,
    proposed_working_directory: str | None = None,
    locked_working_directory: str | None = None,
    proposed_risk_level: str | None = None,
    locked_risk_level: str | None = None,
) -> bool:
    if proposed_command.strip() != locked_command.strip():
        return True
    if (proposed_working_directory or "").strip() != (locked_working_directory or "").strip():
        return True
    if (proposed_risk_level or "").strip().lower() != (locked_risk_level or "").strip().lower():
        return True
    return False
