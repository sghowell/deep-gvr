from __future__ import annotations

import json
from typing import Any

DEFAULT_PROMPT_PROFILE = "compact"
PROMPT_PROFILES = ("compact", "full")


def normalize_prompt_profile(profile: str) -> str:
    normalized = profile.strip().lower()
    if normalized not in PROMPT_PROFILES:
        raise ValueError(
            f"Unsupported prompt profile {profile!r}. Expected one of: {', '.join(PROMPT_PROFILES)}."
        )
    return normalized


def dump_prompt_json(payload: Any, *, profile: str) -> str:
    normalized = normalize_prompt_profile(profile)
    if normalized == "compact":
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    return json.dumps(payload, indent=2)


def build_live_role_query(
    *,
    role: str,
    prompt_text: str,
    payload: dict[str, Any],
    response_contract: dict[str, Any],
    route_notes: list[str],
    route_temperature: float | None,
    prompt_profile: str,
) -> str:
    profile = normalize_prompt_profile(prompt_profile)
    route_lines = [f"role={role}"]
    if route_notes:
        route_lines.extend(route_notes)
    if route_temperature is not None:
        route_lines.append("Temperature fallback is recorded only; Hermes CLI cannot enforce it.")

    if profile == "full":
        return (
            "# deep-gvr live benchmark\n\n"
            f"Role: {role}\n\n"
            "Follow the role prompt below exactly when producing your answer.\n\n"
            f"{prompt_text}\n\n"
            "Return ONLY one JSON object. Do not wrap it in markdown fences. Do not add commentary.\n\n"
            "JSON contract:\n"
            f"{dump_prompt_json(response_contract, profile=profile)}\n\n"
            "Routing context:\n"
            f"{chr(10).join(route_lines)}\n\n"
            "Request payload:\n"
            f"{dump_prompt_json(payload, profile=profile)}\n"
        )

    budget_lines = _live_response_budget_lines(role)
    return "\n".join(
        [
            "# deep-gvr",
            f"Role: {role}",
            "Use the prompt. Return one JSON object that matches the contract.",
            prompt_text,
            "Response budget:",
            *budget_lines,
            "JSON contract:",
            dump_prompt_json(response_contract, profile=profile),
            "Route:",
            "; ".join(route_lines),
            "Payload:",
            dump_prompt_json(payload, profile=profile),
            "",
        ]
    )


def build_formal_query(
    *,
    prompt_text: str,
    payload: dict[str, Any],
    transport_lines: list[str],
    prompt_profile: str,
) -> str:
    profile = normalize_prompt_profile(prompt_profile)
    response_contract = {
        "results": [
            {
                "claim": "string",
                "backend": "aristotle",
                "proof_status": "requested|proved|disproved|timeout|error|unavailable",
                "details": "string",
                "lean_code": "string",
                "proof_time_seconds": "number | null",
            }
        ]
    }

    if profile == "full":
        return (
            "# deep-gvr tier3 formal verification\n\n"
            "Follow the formal-verification prompt below exactly when producing your answer.\n\n"
            f"{prompt_text}\n\n"
            "Return ONLY one JSON object. Do not wrap it in markdown fences. Do not add commentary.\n\n"
            "JSON contract:\n"
            f"{dump_prompt_json(response_contract, profile=profile)}\n\n"
            "Transport context:\n"
            f"{chr(10).join(transport_lines)}\n\n"
            "Request payload:\n"
            f"{dump_prompt_json(payload, profile=profile)}\n"
        )

    return "\n".join(
        [
            "# deep-gvr tier3 formal verification",
            "Use Aristotle when available and return exactly one JSON object that matches the contract.",
            prompt_text,
            "Response budget:",
            "- Return one result object per claim.",
            "- Keep `details` concrete and brief.",
            "- Preserve Lean code only when a tool actually produced it.",
            "JSON contract:",
            dump_prompt_json(response_contract, profile=profile),
            "Transport context:",
            *transport_lines,
            "Request payload:",
            dump_prompt_json(payload, profile=profile),
            "",
        ]
    )


def _live_response_budget_lines(role: str) -> list[str]:
    if role in {"generator", "reviser"}:
        return [
            "- Be concise.",
            "- Prefer one sentence per string field.",
            "- Keep lists to at most three items unless required.",
        ]
    if role == "verifier":
        return [
            "- Keep checks short and concrete.",
            "- List only the flaws or caveats needed for the verdict.",
            "- Request Tier 2 or Tier 3 only when necessary.",
        ]
    return [
        "- Keep the response concise and contract-compliant.",
    ]
