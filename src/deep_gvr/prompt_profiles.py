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

    if role == "verifier":
        return _build_compact_verifier_query(
            prompt_text=prompt_text,
            payload=payload,
            route_lines=route_lines,
        )

    return _build_compact_generic_query(
        role=role,
        prompt_text=prompt_text,
        payload=payload,
        response_contract=response_contract,
        route_lines=route_lines,
        profile=profile,
    )


def _build_compact_generic_query(
    *,
    role: str,
    prompt_text: str,
    payload: dict[str, Any],
    response_contract: dict[str, Any],
    route_lines: list[str],
    profile: str,
) -> str:
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


def _build_compact_verifier_query(
    *,
    prompt_text: str,
    payload: dict[str, Any],
    route_lines: list[str],
) -> str:
    return "\n".join(
        [
            "# deep-gvr",
            "Role: verifier",
            "Audit the candidate only. Return one JSON object.",
            prompt_text,
            "Response budget:",
            "- Keep each check detail to one short sentence.",
            "- List only the flaws or caveats needed for the verdict.",
            "- Request Tier 2 or Tier 3 only when the candidate truly requires it.",
            "Tier 2 spec keys:",
            (
                '- If simulation_requested is true, use '
                '{"simulator":"stim","task":{"code":"surface_code","task_type":"rotated_memory_z",'
                '"distance":[...],"rounds_per_distance":"d|2d|<int>","noise_model":"depolarizing",'
                '"error_rates":[...],"decoder":"pymatching","shots_per_point":...},'
                '"resources":{"timeout_seconds":...,"max_parallel":...}}.'
            ),
            "Tier 2 normalization:",
            "- Use the canonical noise model string `depolarizing`, not `uniform_depolarizing` or `iid_depolarizing`.",
            "- Keep `shots_per_point` at or below 100000 and `max_parallel` at or below 4.",
            "Tier discipline:",
            "- Do not request Tier 2 or Tier 3 just to polish a verdict that Tier 1 already settles.",
            "- If the candidate predicts threshold behavior, logical-error ordering across named distances, or a specific logical-error level at a named physical error rate/decoder/noise model and no simulation_results are attached, request Tier 2 by default.",
            "- Keep known-false literature-grounded contradictions at Tier 1 unless simulation is needed for the core contradiction itself.",
            "Tier 3 trigger:",
            "- If the main claim is a short formal theorem, request tier3 even when Tier 1 already suggests it is correct.",
            "JSON shape:",
            (
                '{"verdict":"VERIFIED|FLAWS_FOUND|CANNOT_VERIFY",'
                '"tier1":{"checks":[{"check":"...","status":"pass|fail|uncertain","detail":"..."}],'
                '"overall":"VERIFIED|FLAWS_FOUND|CANNOT_VERIFY","flaws":["..."],"caveats":["..."]},'
                '"tier2":{"simulation_requested":false,"reason":"...","simulation_spec":null},'
                '"tier3":[],'
                '"flaws":["..."],"caveats":["..."],"cannot_verify_reason":null}'
            ),
            "Route:",
            "; ".join(route_lines),
            "Payload:",
            *_compact_verifier_payload_lines(payload),
            "",
        ]
    )


def _compact_verifier_payload_lines(payload: dict[str, Any]) -> list[str]:
    candidate = payload.get("candidate", {})
    lines = [
        f"session_id={payload.get('session_id', '')}",
        f"iteration={payload.get('iteration', '')}",
        "candidate:",
        f"- hypothesis: {candidate.get('hypothesis', '')}",
        f"- approach: {candidate.get('approach', '')}",
        *_candidate_list_lines("technical_details", candidate.get("technical_details", [])),
        *_candidate_list_lines("expected_results", candidate.get("expected_results", [])),
        *_candidate_list_lines("assumptions", candidate.get("assumptions", [])),
        *_candidate_list_lines("limitations", candidate.get("limitations", [])),
        *_candidate_list_lines("references", candidate.get("references", [])),
    ]
    simulation_results = payload.get("simulation_results")
    if simulation_results is None:
        lines.append("simulation_results: none")
    else:
        lines.append(f"simulation_results: {dump_prompt_json(simulation_results, profile='compact')}")
    formal_results = payload.get("formal_results")
    if not formal_results:
        lines.append("formal_results: none")
    else:
        lines.append(f"formal_results: {dump_prompt_json(formal_results, profile='compact')}")
    return lines


def _candidate_list_lines(label: str, values: Any) -> list[str]:
    items = list(values or [])
    if not items:
        return [f"- {label}: none"]
    lines = [f"- {label}:"]
    lines.extend(f"  - {item}" for item in items)
    return lines


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
