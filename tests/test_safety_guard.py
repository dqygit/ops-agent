import pytest

from app.core.executor.safety_guard import ensure_command_allowed


def test_safety_guard_allows_readonly_linux_and_huawei_commands_only():
    assert ensure_command_allowed("uptime") is True
    assert ensure_command_allowed("display interface brief") is True

    with pytest.raises(ValueError):
        ensure_command_allowed("systemctl restart nginx")

    with pytest.raises(ValueError):
        ensure_command_allowed("system-view")
