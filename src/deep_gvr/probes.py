from __future__ import annotations

import os
import shutil
from dataclasses import asdict

from .contracts import CapabilityProbeResult, ProbeStatus


def probe_model_routing() -> CapabilityProbeResult:
    hermes_available = shutil.which("hermes") is not None
    override_hint = os.getenv("DEEP_GVR_HERMES_MODEL_ROUTING", "").strip().lower()

    if hermes_available and override_hint == "supported":
        return CapabilityProbeResult(
            name="per_subagent_model_routing",
            status=ProbeStatus.READY,
            summary="Hermes is present and the environment declares support for per-subagent model routing.",
            preferred_outcome="Route generator and verifier to distinct providers or models.",
            fallback="If runtime behavior disagrees, revert to prompt and temperature decorrelation.",
            details={"hermes_available": hermes_available, "override_hint": override_hint},
        )

    return CapabilityProbeResult(
        name="per_subagent_model_routing",
        status=ProbeStatus.FALLBACK,
        summary="Per-subagent model routing is not verified in this environment; use the documented fallback until a probe confirms support.",
        preferred_outcome="Route generator and verifier to distinct providers or models.",
        fallback="Use prompt separation plus temperature decorrelation and record the limitation.",
        details={"hermes_available": hermes_available, "override_hint": override_hint},
    )


def probe_mcp_inheritance() -> CapabilityProbeResult:
    hermes_available = shutil.which("hermes") is not None
    aristotle_key = bool(os.getenv("ARISTOTLE_API_KEY"))
    inheritance_hint = os.getenv("DEEP_GVR_SUBAGENT_MCP", "").strip().lower()

    if hermes_available and aristotle_key and inheritance_hint == "supported":
        status = ProbeStatus.READY
        summary = "Hermes and Aristotle credentials are present, and MCP inheritance is explicitly marked supported."
    else:
        status = ProbeStatus.FALLBACK
        summary = (
            "Subagent MCP inheritance is not verified; use the implemented orchestrator-mediated formal "
            "verification fallback."
        )

    return CapabilityProbeResult(
        name="subagent_mcp_inheritance",
        status=status,
        summary=summary,
        preferred_outcome="Allow the verifier subagent to call Aristotle MCP directly.",
        fallback="Have the orchestrator mediate formal verification requests and return results to verification.",
        details={
            "hermes_available": hermes_available,
            "aristotle_key_present": aristotle_key,
            "inheritance_hint": inheritance_hint,
        },
    )


def probe_checkpoint_resume() -> CapabilityProbeResult:
    return CapabilityProbeResult(
        name="session_checkpoint_resume",
        status=ProbeStatus.READY,
        summary="Checkpoint/resume is implemented with a checkpoint artifact plus append-only evidence records.",
        preferred_outcome="Persist loop state, verdict history, and artifact references so resume can continue from the last complete step.",
        fallback="Resume from the last complete checkpoint and re-run any incomplete verification step.",
        details={
            "checkpoint_file": "sessions/<session_id>/checkpoint.json",
            "evidence_log": "sessions/<session_id>.jsonl",
        },
    )


def probe_backend_dispatch() -> CapabilityProbeResult:
    local_ready = shutil.which("python3") is not None
    modal_ready = shutil.which("modal") is not None
    ssh_ready = shutil.which("ssh") is not None

    status = ProbeStatus.READY if local_ready else ProbeStatus.BLOCKED
    summary = "Local backend is available; Modal and SSH remain environment-dependent." if local_ready else "No Python runtime found for local adapter execution."

    return CapabilityProbeResult(
        name="backend_dispatch",
        status=status,
        summary=summary,
        preferred_outcome="Expose the same adapter CLI for local, Modal, and SSH backends.",
        fallback="Mark unavailable backends explicitly and continue with local-only development.",
        details={
            "local_ready": local_ready,
            "modal_ready": modal_ready,
            "ssh_ready": ssh_ready,
        },
    )


def run_capability_probes() -> list[CapabilityProbeResult]:
    return [
        probe_model_routing(),
        probe_mcp_inheritance(),
        probe_checkpoint_resume(),
        probe_backend_dispatch(),
    ]


def probes_as_dict() -> list[dict[str, object]]:
    return [asdict(result) for result in run_capability_probes()]
