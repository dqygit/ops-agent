from __future__ import annotations

import json
from collections.abc import Iterator

from app.core.llm.base import LLMCompletionRequest, SupportsCompletion
from app.shared.schemas import ModelConfig


FINAL_JSON_MARKER = "<FINAL_JSON>"


def stream_prose_until_marker(
    *,
    provider: SupportsCompletion,
    config: ModelConfig,
    request: LLMCompletionRequest,
    marker: str = FINAL_JSON_MARKER,
) -> Iterator[str]:
    """Yield natural-language prose deltas before the marker is seen.

    Once the marker is encountered, the marker itself is swallowed and the
    rest of the stream (typically a JSON payload) is yielded as raw deltas
    so callers can accumulate it for final parsing.
    """

    visible_buffer = ""
    marker_seen = False
    for chunk in provider.stream_complete(config=config, request=request):
        if not chunk.delta:
            continue
        if marker_seen:
            yield chunk.delta
            continue
        visible_buffer += chunk.delta
        marker_index = visible_buffer.find(marker)
        if marker_index >= 0:
            prose = visible_buffer[:marker_index]
            if prose:
                yield prose
            visible_buffer = visible_buffer[marker_index + len(marker):]
            marker_seen = True
            if visible_buffer:
                yield visible_buffer
                visible_buffer = ""
            continue
        safe_length = max(0, len(visible_buffer) - len(marker))
        if safe_length > 0:
            prose = visible_buffer[:safe_length]
            if prose:
                yield prose
            visible_buffer = visible_buffer[safe_length:]
    if not marker_seen and visible_buffer:
        yield visible_buffer


def safe_load_json(text: str) -> dict:
    """Parse a JSON dictionary from raw LLM output, tolerating surrounding noise."""
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(text[start : end + 1])
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}
