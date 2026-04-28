from app.core.executor.safety_guard import ensure_command_allowed


def execute_plan(plan, connector) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for step in plan:
        ensure_command_allowed(step.command)
        output = connector.run_command(step.command)
        rows.append(
            {
                "command": step.command,
                "output": output,
                "error": "",
                "status": "completed",
            }
        )
    return rows
