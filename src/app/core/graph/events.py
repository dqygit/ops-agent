from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid


def new_event(state: dict[str, Any], *, kind: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    sequence = int(state.get("sequence", 0)) + 1
    state["sequence"] = sequence
    event = {
        "id": f"evt-{uuid.uuid4().hex[:12]}",
        "kind": kind,
        "runtimeId": state.get("runtime_id", ""),
        "sequence": sequence,
        "ts": datetime.now(UTC).isoformat(),
    }
    event.update(payload)
    return event


def push_event(state: dict[str, Any], *, kind: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    event = new_event(state, kind=kind, payload=payload)
    events = list(state.get("events") or [])
    events.append(event)
    state["events"] = events
    return event
