def classify_task(user_input: str) -> str:
    text = user_input.lower()
    if "接口" in text or "interface" in text:
        return "interface_status"
    if "路由" in text or "route" in text:
        return "routing_table"
    if "邻居" in text or "lldp" in text:
        return "neighbor_status"
    if "cpu" in text or "内存" in text or "disk" in text:
        return "system_resources"
    return "network_health"
