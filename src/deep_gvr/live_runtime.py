from __future__ import annotations

from typing import Sequence

_DEFAULT_ROLE_TOOLSETS = ("clarify",)
_VERIFIER_TIMEOUT_FLOOR_SECONDS = 150
_VERIFIER_EVIDENCE_TIMEOUT_FLOOR_SECONDS = 180


def resolve_live_role_toolsets(role: str, explicit_toolsets: Sequence[str] | None = None) -> list[str]:
    if explicit_toolsets:
        return [item for item in explicit_toolsets if item]
    if role in {"generator", "verifier", "reviser"}:
        return list(_DEFAULT_ROLE_TOOLSETS)
    return []


def resolve_live_role_timeout_seconds(
    role: str,
    base_timeout_seconds: int,
    *,
    has_simulation_results: bool = False,
    has_formal_results: bool = False,
) -> int:
    if role == "verifier":
        if has_simulation_results or has_formal_results:
            return max(base_timeout_seconds, _VERIFIER_EVIDENCE_TIMEOUT_FLOOR_SECONDS)
        return max(base_timeout_seconds, _VERIFIER_TIMEOUT_FLOOR_SECONDS)
    return base_timeout_seconds
