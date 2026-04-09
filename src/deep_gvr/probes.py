from __future__ import annotations

import importlib.util
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .contracts import CapabilityProbeResult, DeepGvrConfig, ProbeStatus
from .formal import inspect_aristotle_transport, inspect_mathcode_transport, inspect_opengauss_transport


def probe_model_routing(runtime_evidence: dict[str, Any] | None = None) -> CapabilityProbeResult:
    hermes_available = shutil.which("hermes") is not None
    evidence = dict(runtime_evidence or {})
    route_pairs = evidence.get("route_pairs")
    distinct_routes_verified = bool(evidence.get("distinct_routes_verified"))

    if hermes_available and distinct_routes_verified:
        return CapabilityProbeResult(
            name="per_subagent_model_routing",
            status=ProbeStatus.READY,
            summary="Per-subagent model routing was verified from observed delegated runtime behavior.",
            preferred_outcome="Route generator and verifier to distinct providers or models.",
            fallback="If runtime behavior regresses, revert to prompt separation plus temperature decorrelation.",
            details={
                "hermes_available": hermes_available,
                "distinct_routes_verified": distinct_routes_verified,
                "route_pairs": route_pairs,
                "evidence_source": evidence.get("evidence_source", "runtime"),
            },
        )

    return CapabilityProbeResult(
        name="per_subagent_model_routing",
        status=ProbeStatus.FALLBACK,
        summary="Per-subagent model routing is not yet proven from runtime evidence; use the documented fallback until delegated behavior is confirmed.",
        preferred_outcome="Route generator and verifier to distinct providers or models.",
        fallback="Use prompt separation plus temperature decorrelation and record the limitation.",
        details={
            "hermes_available": hermes_available,
            "distinct_routes_verified": distinct_routes_verified,
            "route_pairs": route_pairs,
            "evidence_source": evidence.get("evidence_source", "none"),
        },
    )


def probe_mcp_inheritance(runtime_evidence: dict[str, Any] | None = None) -> CapabilityProbeResult:
    hermes_available = shutil.which("hermes") is not None
    evidence = dict(runtime_evidence or {})
    delegated_mcp_verified = bool(evidence.get("delegated_mcp_verified"))

    if hermes_available and delegated_mcp_verified:
        status = ProbeStatus.READY
        summary = "Delegated verifier MCP access was verified from observed runtime behavior."
    else:
        status = ProbeStatus.FALLBACK
        summary = (
            "Subagent MCP inheritance is not yet proven from runtime evidence; use the implemented orchestrator-mediated formal "
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
            "delegated_mcp_verified": delegated_mcp_verified,
            "evidence_source": evidence.get("evidence_source", "none"),
            "mcp_details": evidence.get("mcp_details"),
        },
    )


def probe_aristotle_transport() -> CapabilityProbeResult:
    transport = inspect_aristotle_transport()
    if not transport.hermes_available:
        status = ProbeStatus.BLOCKED
        summary = "Hermes CLI is not available, so Aristotle transport cannot be dispatched from the orchestrator."
    elif transport.ready:
        status = ProbeStatus.READY
        summary = (
            "Hermes CLI, Aristotle credentials, and an Aristotle MCP server are configured for orchestrator-mediated "
            "formal verification."
        )
    else:
        status = ProbeStatus.FALLBACK
        summary = (
            "Aristotle transport is not fully configured; use the structured unavailable fallback until Hermes MCP is ready."
        )

    return CapabilityProbeResult(
        name="aristotle_transport",
        status=status,
        summary=summary,
        preferred_outcome="Allow the orchestrator to dispatch Tier 3 proof attempts through configured Hermes MCP tools.",
        fallback="Persist the formal request and return structured unavailable results until Hermes MCP transport is configured.",
        details={
            "hermes_available": transport.hermes_available,
            "aristotle_key_present": transport.aristotle_key_present,
            "hermes_config_path": transport.hermes_config_path,
            "hermes_config_exists": transport.hermes_config_exists,
            "mcp_server_name": transport.mcp_server_name,
            "mcp_server_configured": transport.mcp_server_configured,
            "configured_mcp_servers": transport.configured_mcp_servers,
        },
    )


def probe_mathcode_transport(runtime_config: DeepGvrConfig | None = None) -> CapabilityProbeResult:
    config = runtime_config or DeepGvrConfig()
    transport = inspect_mathcode_transport(
        mathcode_root=config.verification.tier3.mathcode.root,
        run_script=config.verification.tier3.mathcode.run_script,
    )
    if transport.ready:
        status = ProbeStatus.READY
        summary = "MathCode local CLI, AUTOLEAN, and lean-workspace are configured for local Tier 3 formal verification."
    else:
        status = ProbeStatus.FALLBACK
        summary = "MathCode local formal transport is not fully configured; use another supported Tier 3 backend until the local checkout is ready."

    return CapabilityProbeResult(
        name="mathcode_transport",
        status=status,
        summary=summary,
        preferred_outcome="Allow the orchestrator to dispatch Tier 3 proof attempts through the local MathCode CLI.",
        fallback="Configure the local MathCode checkout and keep Tier 3 on another supported backend until it is ready.",
        details={
            "mathcode_root": transport.mathcode_root,
            "mathcode_root_exists": transport.mathcode_root_exists,
            "run_script": transport.run_script,
            "run_script_exists": transport.run_script_exists,
            "run_script_executable": transport.run_script_executable,
            "autolean_exists": transport.autolean_exists,
            "lean_workspace_exists": transport.lean_workspace_exists,
        },
    )


def probe_opengauss_transport(
    *,
    opengauss_root: str | Path | None = None,
    gauss_binary: str | Path = "gauss",
    gauss_config_path: str | Path | None = None,
) -> CapabilityProbeResult:
    transport = inspect_opengauss_transport(
        opengauss_root=opengauss_root,
        gauss_binary=gauss_binary,
        gauss_config_path=gauss_config_path,
    )
    if transport.ready:
        status = ProbeStatus.READY
        summary = "Installed OpenGauss runtime and config are present for local interactive-proof diagnostics."
    else:
        status = ProbeStatus.BLOCKED
        summary = (
            "OpenGauss local runtime is not ready; use the dedicated diagnostics script to separate raw-checkout, "
            "installed-runtime, and upstream installer failures."
        )

    return CapabilityProbeResult(
        name="opengauss_transport",
        status=status,
        summary=summary,
        preferred_outcome="Have a working local gauss runtime and config available before enabling OpenGauss-backed Tier 3 work.",
        fallback="Use scripts/diagnose_opengauss.py and another supported Tier 3 backend until OpenGauss installability is restored.",
        details={
            "opengauss_root": transport.opengauss_root,
            "opengauss_root_exists": transport.opengauss_root_exists,
            "install_script": transport.install_script,
            "install_script_exists": transport.install_script_exists,
            "local_launcher": transport.local_launcher,
            "local_launcher_exists": transport.local_launcher_exists,
            "runner_venv": transport.runner_venv,
            "runner_venv_exists": transport.runner_venv_exists,
            "gauss_binary": transport.gauss_binary,
            "gauss_available": transport.gauss_available,
            "gauss_config_path": transport.gauss_config_path,
            "gauss_config_exists": transport.gauss_config_exists,
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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _package_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def probe_analysis_adapter_families() -> CapabilityProbeResult:
    family_packages = {
        "symbolic_math": ["sympy"],
        "optimization": ["scipy", "ortools"],
        "dynamics": ["scipy", "qutip"],
        "qec_decoder_benchmark": ["numpy", "stim", "pymatching"],
        "mbqc_graph_state": ["graphix"],
        "photonic_linear_optics": ["perceval"],
        "neutral_atom_control": ["pulser"],
        "topological_qec_design": ["tqec"],
        "zx_rewrite_verification": ["pyzx"],
    }
    family_readiness: dict[str, dict[str, object]] = {}
    ready_families = 0
    for family, packages in family_packages.items():
        package_state = {package: _package_available(package) for package in packages}
        family_ready = all(package_state.values())
        if family_ready:
            ready_families += 1
        family_readiness[family] = {
            "ready": family_ready,
            "packages": package_state,
        }
    status = ProbeStatus.READY if ready_families == len(family_packages) else ProbeStatus.FALLBACK
    summary = (
        "All OSS analysis adapter families have their local Python dependencies available."
        if status is ProbeStatus.READY
        else "One or more OSS analysis adapter families are configured structurally but missing local Python dependencies."
    )
    return CapabilityProbeResult(
        name="analysis_adapter_families",
        status=status,
        summary=summary,
        preferred_outcome="Expose the full OSS analysis portfolio through explicit local adapter readiness.",
        fallback="Install the missing OSS libraries or restrict runs to the ready adapter families.",
        details={
            "ready_family_count": ready_families,
            "total_family_count": len(family_packages),
            "families": family_readiness,
        },
    )


def probe_backend_dispatch(runtime_config: DeepGvrConfig | None = None) -> CapabilityProbeResult:
    config = runtime_config or DeepGvrConfig()
    modal_config = config.verification.tier2.modal
    ssh_config = config.verification.tier2.ssh

    local_ready = shutil.which("python3") is not None and all(
        _package_available(package_name) for package_name in ("numpy", "stim", "pymatching")
    )
    modal_binary = shutil.which(modal_config.cli_bin)
    modal_stub_path = Path(modal_config.stub_path).expanduser()
    if not modal_stub_path.is_absolute():
        modal_stub_path = _repo_root() / modal_stub_path
    modal_ready = modal_binary is not None and modal_stub_path.exists()

    ssh_binary = shutil.which("ssh")
    scp_binary = shutil.which("scp")
    ssh_key_path = Path(ssh_config.key_path).expanduser() if ssh_config.key_path else None
    ssh_key_exists = ssh_key_path.exists() if ssh_key_path is not None else True
    ssh_configured = bool(ssh_config.host and ssh_config.remote_workspace and ssh_config.python_bin)
    ssh_ready = ssh_binary is not None and scp_binary is not None and ssh_configured and ssh_key_exists

    status = ProbeStatus.READY if local_ready else ProbeStatus.BLOCKED
    summary = (
        "Backend dispatch is implemented for the QEC analysis path across local, Modal, and SSH execution; probe details record which backends are configured in this environment."
        if local_ready
        else "No usable local QEC analysis runtime was found for adapter execution."
    )

    return CapabilityProbeResult(
        name="backend_dispatch",
        status=status,
        summary=summary,
        preferred_outcome="Expose the same adapter CLI for local, Modal, and SSH backends.",
        fallback="Configure the missing backend prerequisites and rerun the readiness probe before using that backend.",
        details={
            "local_ready": local_ready,
            "local_dependencies": {
                "numpy": _package_available("numpy"),
                "stim": _package_available("stim"),
                "pymatching": _package_available("pymatching"),
            },
            "modal_ready": modal_ready,
            "modal_cli": modal_config.cli_bin,
            "modal_cli_available": modal_binary is not None,
            "modal_stub_path": str(modal_stub_path),
            "modal_stub_exists": modal_stub_path.exists(),
            "ssh_ready": ssh_ready,
            "ssh_binary_available": ssh_binary is not None,
            "scp_binary_available": scp_binary is not None,
            "ssh_host_configured": bool(ssh_config.host),
            "ssh_remote_workspace_configured": bool(ssh_config.remote_workspace),
            "ssh_python_bin": ssh_config.python_bin,
            "ssh_key_path": ssh_config.key_path,
            "ssh_key_exists": ssh_key_exists,
        },
    )


def run_capability_probes(
    capability_evidence: dict[str, Any] | None = None,
    runtime_config: DeepGvrConfig | None = None,
) -> list[CapabilityProbeResult]:
    evidence = dict(capability_evidence or {})
    return [
        probe_model_routing(evidence.get("per_subagent_model_routing")),
        probe_mcp_inheritance(evidence.get("subagent_mcp_inheritance")),
        probe_aristotle_transport(),
        probe_mathcode_transport(runtime_config),
        probe_opengauss_transport(),
        probe_checkpoint_resume(),
        probe_analysis_adapter_families(),
        probe_backend_dispatch(runtime_config),
    ]


def probes_as_dict() -> list[dict[str, object]]:
    return [asdict(result) for result in run_capability_probes()]
