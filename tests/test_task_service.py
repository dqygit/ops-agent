from app.core.executor.command_executor import execute_plan
from app.shared.schemas import PlanStep


class FakeConnector:
    def __init__(self):
        self.commands = []

    def run_command(self, command: str) -> str:
        self.commands.append(command)
        return f"ok:{command}"


def test_execute_plan_returns_structured_step_results():
    connector = FakeConnector()
    plan = [
        PlanStep(title="one", command="uptime", reason="r1", risk_level="low"),
        PlanStep(title="two", command="display interface brief", reason="r2", risk_level="low"),
    ]

    rows = execute_plan(plan, connector)

    assert rows == [
        {"command": "uptime", "output": "ok:uptime", "error": "", "status": "completed"},
        {"command": "display interface brief", "output": "ok:display interface brief", "error": "", "status": "completed"},
    ]
    assert connector.commands == ["uptime", "display interface brief"]
