from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.connectors.device_profiles import DeviceProfile


@dataclass(frozen=True, slots=True)
class NetworkCliAnalysis:
    prompt: str | None
    pager_detected: bool
    confirm_detected: bool
    matched_error: str | None
    mode: str | None


def analyze_transcript(output: str, profile: DeviceProfile) -> NetworkCliAnalysis:
    prompt = _last_match(output, profile.prompt_patterns)
    matched_error = _first_match(output, profile.error_patterns)
    return NetworkCliAnalysis(
        prompt=prompt,
        pager_detected=_has_match(output, profile.pager_patterns),
        confirm_detected=_has_match(output, profile.confirm_patterns),
        matched_error=matched_error,
        mode=detect_mode(prompt),
    )


def strip_pager_markers(output: str, profile: DeviceProfile) -> str:
    cleaned = output
    for pattern in profile.pager_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return cleaned


def detect_mode(prompt: str | None) -> str | None:
    if not prompt:
        return None
    lowered = prompt.lower().strip()
    if "config" in lowered or lowered.startswith("["):
        return "config"
    if lowered.endswith(">"):
        return "exec"
    if lowered.endswith("#"):
        return "privileged"
    return "unknown"


def _has_match(text: str, patterns: tuple[str, ...]) -> bool:
    return _first_match(text, patterns) is not None


def _first_match(text: str, patterns: tuple[str, ...]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(0)
    return None


def _last_match(text: str, patterns: tuple[str, ...]) -> str | None:
    last_match: re.Match[str] | None = None
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            if last_match is None or match.start() >= last_match.start():
                last_match = match
    return last_match.group(0).strip() if last_match is not None else None
