from app.core.agent.planner import build_plan
from app.shared.enums import AssetType
from app.shared.schemas import TerminalContextAttachment


def test_build_plan_uses_huawei_catalog_and_explicit_terminal_context():
    plan = build_plan(
        asset_type=AssetType.HUAWEI,
        user_input="检查接口状态",
        terminal_context=TerminalContextAttachment(
            terminal_session_id=7,
            selection_label="selected interface output",
            selected_text="GigabitEthernet0/0/1 down",
        ),
    )

    assert len(plan) == 1
    assert plan[0].command == "display interface brief"
    assert "selected interface output" in plan[0].reason
