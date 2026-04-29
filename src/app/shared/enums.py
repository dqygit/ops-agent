from enum import Enum


class AssetType(str, Enum):
    LINUX = "linux"
    LOCAL_TERMINAL = "local_terminal"
    NETWORK = "network"
    CISCO = "cisco"
    HUAWEI = "huawei"
    JUNIPER = "juniper"
    H3C = "h3c"


class TaskStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"
    SKIPPED = "skipped"


class ModelProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI_COMPATIBLE = "openai_compatible"


class TerminalEventType(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    CONTEXT_ATTACHED = "context_attached"
    OUTPUT = "terminal_output"
    COMMAND_STARTED = "command_started"
    COMMAND_FINISHED = "command_finished"


class ApprovalDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"


class CommandExecutionStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    INTERFACE_STATUS = "interface_status"
    ROUTING_TABLE = "routing_table"
    NEIGHBOR_STATUS = "neighbor_status"
    SYSTEM_RESOURCES = "system_resources"
    NETWORK_HEALTH = "network_health"
