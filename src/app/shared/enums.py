from enum import Enum


class AssetType(str, Enum):
    LINUX = "linux"
    HUAWEI = "huawei"


class TaskStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ModelProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI_COMPATIBLE = "openai_compatible"


class TerminalEventType(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    CONTEXT_ATTACHED = "context_attached"
    OUTPUT = "terminal_output"


class TaskType(str, Enum):
    INTERFACE_STATUS = "interface_status"
    ROUTING_TABLE = "routing_table"
    NEIGHBOR_STATUS = "neighbor_status"
    SYSTEM_RESOURCES = "system_resources"
    NETWORK_HEALTH = "network_health"
