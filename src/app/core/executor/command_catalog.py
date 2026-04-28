from app.shared.enums import AssetType


COMMAND_CATALOG = {
    AssetType.LINUX.value: {
        "system_resources": ["uptime", "free -m", "df -h"],
        "network_health": ["ip addr", "ip route", "ss -tulpn"],
        "process_health": ["ps aux", "top -b -n 1"],
    },
    AssetType.HUAWEI.value: {
        "interface_status": ["display interface brief"],
        "routing_table": ["display ip routing-table"],
        "neighbor_status": ["display lldp neighbor brief"],
    },
}


def get_commands_for_task(asset_type: AssetType, task_type: str) -> list[str]:
    return COMMAND_CATALOG[asset_type.value][task_type]
