"""Agent Loop 策略与基础常量。"""

from __future__ import annotations

MAX_STEP_RETRIES = 3

RISK_LEVEL_LOW = "low"
RISK_LEVEL_MEDIUM = "medium"
RISK_LEVEL_HIGH = "high"
RISK_LEVEL_CRITICAL = "critical"

APPROVAL_REQUIRED_LEVELS = {RISK_LEVEL_MEDIUM, RISK_LEVEL_HIGH, RISK_LEVEL_CRITICAL}


def needs_approval(risk_level: str) -> bool:
    return risk_level in APPROVAL_REQUIRED_LEVELS
