TEMPLATES = {
    "server": {
        "system_resources": ["uptime", "free -m", "df -h"],
        "network_health": ["ip addr", "ss -tulpn"],
    },
    "cisco": {
        "interface_status": ["show interface status"],
        "routing_table": ["show ip route"],
        "neighbor_status": ["show cdp neighbors"],
    },
    "huawei": {
        "interface_status": ["display interface brief"],
        "routing_table": ["display ip routing-table"],
        "neighbor_status": ["display lldp neighbor brief"],
    },
    "juniper": {
        "interface_status": ["show interfaces terse"],
        "routing_table": ["show route"],
        "neighbor_status": ["show lldp neighbors"],
    },
}
