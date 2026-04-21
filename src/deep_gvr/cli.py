from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .contracts import (
    BranchStatus,
    BranchStrategy,
    CapabilityProbeResult,
    DeepGvrConfig,
    HypothesisBranch,
    ProbeStatus,
    SessionCheckpoint,
)
from .domain_context import load_domain_context
from .orchestrator import CommandExecutor, OrchestratorBackendConfig, build_orchestrator_runner
from .probes import probe_model_routing
from .prompt_profiles import DEFAULT_PROMPT_PROFILE, PROMPT_PROFILES
from .routing import build_routing_plan
from .runtime_config import (
    default_config_path,
    default_config_payload,
    load_runtime_config,
    resolve_config_path,
    write_default_config,
)
from .runtime_paths import runtime_home_description
from .tier1 import SessionStore


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _isoformat(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _split_csv_flags(values: list[str]) -> list[str]:
    items: list[str] = []
    for value in values:
        items.extend(part.strip() for part in value.split(",") if part.strip())
    return items
@dataclass(slots=True)
class SkillSessionSummary:
    command: str
    session_id: str
    status: str
    final_verdict: str
    result_summary: str
    problem: str
    domain: str
    iterations: int
    config_path: str
    config_created: bool
    evidence_log: str
    checkpoint_file: str
    artifacts_dir: str
    artifacts: list[str]
    capability_evidence: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return dict(asdict(self))


def run_session_command(
    problem: str,
    *,
    config_path: str | Path | None = None,
    domain: str | None = None,
    prompt_root: str | Path = "prompts",
    prompt_profile: str = DEFAULT_PROMPT_PROFILE,
    routing_probe_mode: str = "auto",
    toolsets: list[str] | None = None,
    skills: list[str] | None = None,
    command_timeout_seconds: int = 120,
    session_id: str | None = None,
    executor: CommandExecutor | None = None,
) -> SkillSessionSummary:
    resolved_config_path = resolve_config_path(config_path)
    config_created = not resolved_config_path.exists()
    config = load_runtime_config(resolved_config_path)
    selected_domain, literature_context = load_domain_context(config, domain_override=domain)
    return _execute_command(
        command="run",
        config=config,
        config_path=resolved_config_path,
        config_created=config_created,
        prompt_root=prompt_root,
        prompt_profile=prompt_profile,
        routing_probe_mode=routing_probe_mode,
        toolsets=toolsets or [],
        skills=skills or [],
        command_timeout_seconds=command_timeout_seconds,
        executor=executor,
        run_problem=problem,
        run_domain=selected_domain,
        run_literature_context=literature_context,
        run_session_id=session_id or f"session_{uuid4().hex[:8]}",
    )


def resume_session_command(
    session_id: str,
    *,
    config_path: str | Path | None = None,
    prompt_root: str | Path = "prompts",
    prompt_profile: str = DEFAULT_PROMPT_PROFILE,
    routing_probe_mode: str = "auto",
    toolsets: list[str] | None = None,
    skills: list[str] | None = None,
    command_timeout_seconds: int = 120,
    executor: CommandExecutor | None = None,
) -> SkillSessionSummary:
    resolved_config_path = resolve_config_path(config_path)
    config_created = not resolved_config_path.exists()
    config = load_runtime_config(resolved_config_path)
    return _execute_command(
        command="resume",
        config=config,
        config_path=resolved_config_path,
        config_created=config_created,
        prompt_root=prompt_root,
        prompt_profile=prompt_profile,
        routing_probe_mode=routing_probe_mode,
        toolsets=toolsets or [],
        skills=skills or [],
        command_timeout_seconds=command_timeout_seconds,
        executor=executor,
        resume_session_id=session_id,
    )


def _execute_command(
    *,
    command: str,
    config: DeepGvrConfig,
    config_path: Path,
    config_created: bool,
    prompt_root: str | Path,
    prompt_profile: str,
    routing_probe_mode: str,
    toolsets: list[str],
    skills: list[str],
    command_timeout_seconds: int,
    executor: CommandExecutor | None,
    run_problem: str | None = None,
    run_domain: str | None = None,
    run_literature_context: list[str] | None = None,
    run_session_id: str | None = None,
    resume_session_id: str | None = None,
) -> SkillSessionSummary:
    session_store = SessionStore(
        config.evidence.directory,
        persist_to_memory=config.evidence.persist_to_memory,
    )
    session_id = run_session_id if command == "run" else resume_session_id
    prompt_root_path = _resolve_prompt_root(prompt_root)
    routing_probe = _resolve_routing_probe(config, routing_probe_mode)
    routing_plan = build_routing_plan(config, routing_probe=routing_probe)
    role_routes = _role_routes_payload(routing_plan)
    orchestrator = build_orchestrator_runner(
        OrchestratorBackendConfig(
            backend=config.runtime.orchestrator_backend,
            prompt_profile=prompt_profile,
            command_timeout_seconds=command_timeout_seconds,
            toolsets=list(toolsets),
            skills=list(skills),
            provider=config.models.orchestrator.provider,
            model=config.models.orchestrator.model,
            role_routes=role_routes,
            writable_roots=_backend_writable_roots(
                config=config,
                config_path=config_path,
                prompt_root=prompt_root_path,
            ),
        ),
        cwd=_repo_root(),
        executor=executor,
    )
    try:
        if command == "run":
            if run_problem is None or run_domain is None or run_literature_context is None:
                raise ValueError("Run command requires a problem, domain, and literature context.")
            summary_payload = orchestrator.run(
                question=run_problem,
                session_id=run_session_id,
                config_path=config_path,
                prompt_root=prompt_root_path,
                routing_probe_mode=routing_probe_mode,
                domain_override=run_domain,
                role_routes=role_routes,
            )
        elif command == "resume":
            if resume_session_id is None:
                raise ValueError("Resume command requires a session_id.")
            summary_payload = orchestrator.resume(
                session_id=resume_session_id,
                config_path=config_path,
                prompt_root=prompt_root_path,
                routing_probe_mode=routing_probe_mode,
                role_routes=role_routes,
            )
        else:
            raise ValueError(f"Unsupported command {command!r}.")
    except Exception as exc:
        if session_id is None:
            raise
        failure_verdict = str(getattr(exc, "final_verdict", "PENDING"))
        checkpoint = _record_session_artifacts(
            session_store=session_store,
            session_id=session_id,
            command=command,
            transcripts=orchestrator.transcripts,
            error=f"{type(exc).__name__}: {exc}",
            failure_verdict=failure_verdict,
        )
        return _summary_from_failure(
            command=command,
            config_path=config_path,
            config_created=config_created,
            session_store=session_store,
            session_id=session_id,
            checkpoint=checkpoint,
            fallback_problem=run_problem or "",
            fallback_domain=run_domain or config.domain.default,
            error=f"{type(exc).__name__}: {exc}",
            capability_evidence=_merge_capability_evidence(orchestrator.transcripts),
        )

    checkpoint = _record_session_artifacts(
        session_store=session_store,
        session_id=str(summary_payload.get("session_id") or session_id),
        command=command,
        transcripts=orchestrator.transcripts,
    )
    return _summary_from_payload(
        payload=summary_payload,
        command=command,
        config_path=config_path,
        config_created=config_created,
        checkpoint=checkpoint,
        session_store=session_store,
        fallback_problem=run_problem or "",
        fallback_domain=run_domain or config.domain.default,
    )


def _resolve_prompt_root(path: str | Path) -> Path:
    prompt_root = Path(path)
    if prompt_root.is_absolute():
        return prompt_root
    return _repo_root() / prompt_root


def _backend_writable_roots(
    *,
    config: DeepGvrConfig,
    config_path: Path,
    prompt_root: Path,
) -> list[str]:
    roots: list[Path] = [
        _repo_root(),
        config_path.parent,
        Path(config.evidence.directory).expanduser(),
    ]
    if prompt_root.is_absolute():
        roots.append(prompt_root)
    if config.domain.context_file:
        roots.append(Path(config.domain.context_file).expanduser().parent)
    if config.verification.tier3.enabled:
        if config.verification.tier3.backend == "mathcode":
            roots.append(Path(config.verification.tier3.mathcode.root).expanduser())
            roots.append(Path(config.verification.tier3.mathcode.run_script).expanduser().parent)
        if config.verification.tier3.backend == "opengauss":
            roots.append(Path(os.getenv("GAUSS_HOME", "~/.gauss")).expanduser())
            roots.append(Path("~/dev/OpenGauss").expanduser())
    unique_roots: list[str] = []
    for root in roots:
        normalized = str(root.resolve())
        if normalized not in unique_roots:
            unique_roots.append(normalized)
    return unique_roots


def _resolve_routing_probe(config: DeepGvrConfig, mode: str) -> CapabilityProbeResult:
    normalized = mode.strip().lower()
    if normalized == "auto":
        return probe_model_routing()
    if normalized == "ready":
        return CapabilityProbeResult(
            name="per_subagent_model_routing",
            status=ProbeStatus.READY,
            summary="Routing probe forced to ready by CLI flag for delegated runtime planning.",
            preferred_outcome="Route generator and verifier to distinct providers or models.",
            fallback="If runtime behavior disagrees, revert to prompt separation plus temperature decorrelation.",
            details={"forced_by": "routing_probe_mode", "mode": normalized},
        )
    if normalized == "fallback":
        return CapabilityProbeResult(
            name="per_subagent_model_routing",
            status=ProbeStatus.FALLBACK,
            summary="Routing probe forced to fallback by CLI flag for delegated runtime planning.",
            preferred_outcome="Route generator and verifier to distinct providers or models.",
            fallback="Use prompt separation plus temperature decorrelation and record the limitation.",
            details={"forced_by": "routing_probe_mode", "mode": normalized},
        )
    raise ValueError(f"Unsupported routing probe mode {mode!r}.")


def _route_payload(route: Any) -> dict[str, Any]:
    return {
        "provider": route.provider,
        "model": route.model,
        "routing_mode": route.routing_mode.value,
        "temperature": route.temperature,
        "notes": list(route.notes),
        "fallback_routes": [
            {
                "provider": fallback.provider,
                "model": fallback.model,
                "routing_mode": fallback.routing_mode.value,
                "temperature": fallback.temperature,
                "notes": list(fallback.notes),
            }
            for fallback in route.fallback_routes
        ],
    }


def _role_routes_payload(plan: Any) -> dict[str, Any]:
    return {
        "strategy": plan.strategy.value,
        "probe": plan.probe.to_dict(),
        "limitations": list(plan.limitations),
        "orchestrator": _route_payload(plan.orchestrator),
        "generator": _route_payload(plan.generator),
        "verifier": _route_payload(plan.verifier),
        "reviser": _route_payload(plan.reviser),
    }


def _merge_capability_evidence(transcripts: list[Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for item in transcripts:
        capability_evidence = getattr(item, "capability_evidence", None)
        if isinstance(capability_evidence, dict):
            merged.update(capability_evidence)
    return merged


def _record_session_artifacts(
    *,
    session_store: SessionStore,
    session_id: str,
    command: str,
    transcripts: list[Any],
    checkpoint: SessionCheckpoint | None = None,
    error: str | None = None,
    failure_verdict: str = "PENDING",
) -> SessionCheckpoint:
    current_checkpoint = checkpoint
    if current_checkpoint is None:
        checkpoint_path = session_store.session_paths(session_id).checkpoint_file
        if checkpoint_path.exists():
            current_checkpoint = session_store.load_checkpoint(session_id)

    new_artifacts: list[str] = []
    if transcripts:
        stamp = _utc_now().strftime("%Y%m%dT%H%M%SZ")
        new_artifacts.append(
            session_store.write_artifact_json(
                session_id,
                f"{stamp}_{command}_orchestrator_transcript.json",
                {
                    "command": command,
                    "generated_at": _isoformat(_utc_now()),
                    "calls": [item.to_dict() for item in transcripts],
                },
            )
        )
        capability_evidence = _merge_capability_evidence(transcripts)
        if capability_evidence:
            new_artifacts.append(
                session_store.write_artifact_json(
                    session_id,
                    f"{stamp}_{command}_capability_evidence.json",
                    {
                        "command": command,
                        "generated_at": _isoformat(_utc_now()),
                        "capability_evidence": capability_evidence,
                    },
                )
            )
    if error is not None:
        stamp = _utc_now().strftime("%Y%m%dT%H%M%SZ")
        new_artifacts.append(
            session_store.write_artifact_json(
                session_id,
                f"{stamp}_{command}_error.json",
                {
                    "command": command,
                    "generated_at": _isoformat(_utc_now()),
                    "error": error,
                },
            )
        )

    if current_checkpoint is None:
        session_paths = session_store.session_paths(session_id)
        fallback_checkpoint = SessionCheckpoint(
            session_id=session_id,
            problem="",
            domain="",
            started=_isoformat(_utc_now()),
            last_updated=_isoformat(_utc_now()),
            status="failed" if error is not None else "in_progress",
            current_iteration=0,
            max_iterations=0,
            next_phase="generate",
            active_branch_id="branch_1",
            branches=[
                HypothesisBranch(
                    branch_id="branch_1",
                    strategy=BranchStrategy.PRIMARY,
                    status=BranchStatus.FAILED if error is not None else BranchStatus.ACTIVE,
                    rationale="Primary research path derived directly from the original problem.",
                    created_iteration=0,
                    activated_iteration=0,
                    closed_iteration=0 if error is not None else None,
                )
            ],
            literature_context=[],
            candidate=None,
            verification_report=None,
            verdict_history=[],
            result_summary=(
                "Command failed before a checkpoint summary was available."
                if error is not None
                else "Delegated orchestrator returned before a local checkpoint was available."
            ),
            final_verdict=failure_verdict if error is not None else "PENDING",
            evidence_file=str(session_paths.evidence_log),
            artifacts_dir=str(session_paths.artifacts_dir),
            memory_summary_file=str(session_paths.memory_summary_file),
            parallax_manifest_file=str(session_paths.parallax_manifest_file),
            artifacts=[
                str((session_paths.session_dir.parent / artifact).resolve())
                for artifact in new_artifacts
            ],
        )
        session_store.save_checkpoint(fallback_checkpoint)
        return fallback_checkpoint

    for artifact in new_artifacts:
        if artifact not in current_checkpoint.artifacts:
            current_checkpoint.artifacts.append(artifact)
    if new_artifacts:
        session_store.save_checkpoint(current_checkpoint)
    return current_checkpoint


def _summary_from_failure(
    *,
    command: str,
    config_path: Path,
    config_created: bool,
    session_store: SessionStore,
    session_id: str,
    checkpoint: SessionCheckpoint,
    fallback_problem: str,
    fallback_domain: str,
    error: str,
    capability_evidence: dict[str, Any] | None = None,
) -> SkillSessionSummary:
    session_paths = session_store.session_paths(session_id)
    artifacts = checkpoint.artifacts
    return SkillSessionSummary(
        command=command,
        session_id=session_id,
        status=checkpoint.status,
        final_verdict=checkpoint.final_verdict,
        result_summary=checkpoint.result_summary or "Command failed.",
        problem=checkpoint.problem or fallback_problem,
        domain=checkpoint.domain or fallback_domain,
        iterations=len(checkpoint.verdict_history),
        config_path=str(config_path),
        config_created=config_created,
        evidence_log=str(session_paths.evidence_log),
        checkpoint_file=str(session_paths.checkpoint_file),
        artifacts_dir=str(session_paths.artifacts_dir),
        artifacts=[
            str((session_paths.session_dir.parent / artifact).resolve()) if not Path(artifact).is_absolute() else str(Path(artifact))
            for artifact in artifacts
        ],
        capability_evidence=capability_evidence,
        error=error,
    )


def _summary_from_result(
    *,
    command: str,
    config_path: Path,
    config_created: bool,
    result: Tier1RunResult,
    checkpoint: SessionCheckpoint,
) -> SkillSessionSummary:
    session_root = result.session_paths.session_dir.parent
    artifacts = [
        str((session_root / artifact).resolve()) if not Path(artifact).is_absolute() else str(Path(artifact))
        for artifact in checkpoint.artifacts
    ]
    return SkillSessionSummary(
        command=command,
        session_id=result.session_id,
        status=checkpoint.status,
        final_verdict=checkpoint.final_verdict,
        result_summary=checkpoint.result_summary,
        problem=checkpoint.problem,
        domain=checkpoint.domain,
        iterations=len(checkpoint.verdict_history),
        config_path=str(config_path),
        config_created=config_created,
        evidence_log=str(result.session_paths.evidence_log),
        checkpoint_file=str(result.session_paths.checkpoint_file),
        artifacts_dir=str(result.session_paths.artifacts_dir),
        artifacts=artifacts,
        capability_evidence=None,
    )


def _summary_from_payload(
    *,
    payload: dict[str, Any],
    command: str,
    config_path: Path,
    config_created: bool,
    checkpoint: SessionCheckpoint,
    session_store: SessionStore,
    fallback_problem: str,
    fallback_domain: str,
) -> SkillSessionSummary:
    session_id = str(payload.get("session_id") or checkpoint.session_id)
    session_paths = session_store.session_paths(session_id)
    artifact_values = [str(item) for item in payload.get("artifacts", [])]
    for artifact in checkpoint.artifacts:
        resolved = (
            str((session_paths.session_dir.parent / artifact).resolve())
            if not Path(artifact).is_absolute()
            else str(Path(artifact))
        )
        if resolved not in artifact_values:
            artifact_values.append(resolved)
    return SkillSessionSummary(
        command=command,
        session_id=session_id,
        status=str(payload.get("status") or checkpoint.status),
        final_verdict=str(payload.get("final_verdict") or checkpoint.final_verdict),
        result_summary=str(payload.get("result_summary") or checkpoint.result_summary),
        problem=str(payload.get("problem") or checkpoint.problem or fallback_problem),
        domain=str(payload.get("domain") or checkpoint.domain or fallback_domain),
        iterations=int(payload.get("iterations", len(checkpoint.verdict_history))),
        config_path=str(payload.get("config_path") or config_path),
        config_created=bool(payload.get("config_created", config_created)),
        evidence_log=str(payload.get("evidence_log") or session_paths.evidence_log),
        checkpoint_file=str(payload.get("checkpoint_file") or session_paths.checkpoint_file),
        artifacts_dir=str(payload.get("artifacts_dir") or session_paths.artifacts_dir),
        artifacts=artifact_values,
        capability_evidence=dict(payload.get("capability_evidence", {})) if isinstance(payload.get("capability_evidence"), dict) else None,
        error=str(payload["error"]) if payload.get("error") is not None else None,
    )


def _render_summary(summary: SkillSessionSummary) -> str:
    lines = [
        f"Command: {summary.command}",
        f"Session: {summary.session_id}",
        f"Status: {summary.status}",
        f"Verdict: {summary.final_verdict}",
        f"Domain: {summary.domain}",
        f"Iterations: {summary.iterations}",
        f"Summary: {summary.result_summary}",
        f"Config: {summary.config_path}",
        f"Evidence: {summary.evidence_log}",
        f"Checkpoint: {summary.checkpoint_file}",
        f"Artifacts: {summary.artifacts_dir}",
    ]
    if summary.config_created:
        lines.insert(7, "Config created: true")
    if summary.error:
        lines.append(f"Error: {summary.error}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run or resume deep-gvr research sessions.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-config", help="Create the default deep-gvr config file.")
    init_parser.add_argument(
        "--config",
        default="",
        help=f"Target config path. Default: {runtime_home_description()}/config.yaml",
    )
    init_parser.add_argument("--force", action="store_true", help="Overwrite an existing config file.")
    init_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")

    common_parent = argparse.ArgumentParser(add_help=False)
    common_parent.add_argument(
        "--config",
        default="",
        help=f"Config path. Default: {runtime_home_description()}/config.yaml",
    )
    common_parent.add_argument("--prompt-root", default="prompts", help="Prompt directory.")
    common_parent.add_argument(
        "--prompt-profile",
        choices=list(PROMPT_PROFILES),
        default=DEFAULT_PROMPT_PROFILE,
        help="Prompt scaffolding profile for live Hermes calls.",
    )
    common_parent.add_argument(
        "--routing-probe",
        choices=["auto", "ready", "fallback"],
        default="auto",
        help="Routing probe override for the session.",
    )
    common_parent.add_argument(
        "--command-timeout-seconds",
        type=int,
        default=120,
        help="Base Hermes command timeout for live role calls. The verifier may use a higher repo-local floor.",
    )
    common_parent.add_argument(
        "--toolsets",
        action="append",
        default=[],
        help="Comma-separated Hermes toolsets. Repeat to add more values.",
    )
    common_parent.add_argument(
        "--skills",
        action="append",
        default=[],
        help="Comma-separated Hermes skills. Repeat to add more values.",
    )
    common_parent.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")

    run_parser = subparsers.add_parser("run", parents=[common_parent], help="Start a new deep-gvr session.")
    run_parser.add_argument("question", help="Research question to run through the harness.")
    run_parser.add_argument("--domain", default="", help="Optional domain override.")
    run_parser.add_argument("--session-id", default="", help="Optional stable session ID.")

    resume_parser = subparsers.add_parser("resume", parents=[common_parent], help="Resume an existing session.")
    resume_parser.add_argument("session_id", help="Session ID to resume.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init-config":
        existed = resolve_config_path(args.config or None).exists()
        path = write_default_config(args.config or None, force=args.force)
        payload = {
            "config_path": str(path),
            "created": args.force or not existed,
        }
        print(json.dumps(payload, indent=2) if args.json else str(path))
        return 0

    kwargs = {
        "config_path": args.config or None,
        "prompt_root": args.prompt_root,
        "prompt_profile": args.prompt_profile,
        "routing_probe_mode": args.routing_probe,
        "toolsets": _split_csv_flags(args.toolsets),
        "skills": _split_csv_flags(args.skills),
        "command_timeout_seconds": args.command_timeout_seconds,
    }
    if args.command == "run":
        summary = run_session_command(
            args.question,
            domain=args.domain or None,
            session_id=args.session_id or None,
            **kwargs,
        )
    else:
        summary = resume_session_command(args.session_id, **kwargs)

    print(json.dumps(summary.to_dict(), indent=2) if args.json else _render_summary(summary))
    return 0 if summary.error is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
