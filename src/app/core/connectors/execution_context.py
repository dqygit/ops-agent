from typing import Any

from app.core.connectors.device_profiles import NETWORK_CLI_PROFILE, DeviceProfile


def build_asset_summary(asset: Any) -> str:
    return (
        f"asset={getattr(asset, 'name', '')}, type={getattr(asset, 'asset_type', '')}, "
        f"host={getattr(asset, 'host', '')}, user={getattr(asset, 'username', '')}"
    )


def infer_os_type(shell_type: str, *, execution_profile: str = "posix-shell") -> str:
    if execution_profile == NETWORK_CLI_PROFILE:
        if shell_type == "serial":
            return "serial-console"
        return "network-device"
    if shell_type in {"powershell", "cmd"}:
        return "Windows"
    if shell_type == "posix":
        return "Darwin/Linux"
    return "unknown"


def build_device_context(execution_profile: str, device_profile: DeviceProfile | None) -> str:
    if execution_profile != NETWORK_CLI_PROFILE or device_profile is None:
        return ""

    base_rules = [
        "You are operating a network device CLI, not a Linux shell.",
        "Do not use Linux commands.",
        f"Use the current device vendor syntax: {device_profile.vendor}.",
        "Prefer read-only inspection commands before changes.",
        "Treat prompts, pagination, configuration modes, and confirmations as protocol state.",
        "Never save configuration unless the user explicitly approves a save action.",
        "If command output contains an error pattern or an unexpected confirmation prompt, stop and explain.",
    ]
    if device_profile.vendor == "generic":
        base_rules.append(
            "This is a generic network device profile. First use '?' to inspect available commands, then choose vendor-specific read-only commands from that output before entering configuration mode."
        )
    else:
        base_rules.append(
            f"Read-only prefixes: {', '.join(device_profile.read_prefixes)}. Save commands requiring separate approval: {', '.join(device_profile.save_commands)}."
        )
    return "\n".join(base_rules)
