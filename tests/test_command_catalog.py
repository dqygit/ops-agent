from app.core.executor.command_catalog import get_commands_for_task
from app.shared.enums import AssetType


def test_command_catalog_returns_huawei_interface_command():
    commands = get_commands_for_task(AssetType.HUAWEI, "interface_status")

    assert commands == ["display interface brief"]
