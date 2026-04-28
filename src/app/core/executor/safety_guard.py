DENY_PREFIXES = (
    "rm ",
    "mv ",
    "chmod ",
    "chown ",
    "sudo ",
    "systemctl restart",
    "systemctl stop",
    "systemctl start",
    "reboot",
    "shutdown",
    "system-view",
)

ALLOW_PREFIXES = (
    "uptime",
    "free ",
    "df ",
    "ip ",
    "ss ",
    "ps ",
    "top ",
    "display ",
)


def ensure_command_allowed(command: str) -> bool:
    normalized = command.strip().lower()
    if normalized.startswith(DENY_PREFIXES):
        raise ValueError(f"Blocked unsafe command: {command}")
    if normalized.startswith(ALLOW_PREFIXES):
        return True
    raise ValueError(f"Command is not in readonly allowlist: {command}")
