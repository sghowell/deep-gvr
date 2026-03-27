from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from .contracts import DeepGvrConfig, ProbeStatus, SessionCheckpoint
from .evaluation import CommandExecutor, HermesPromptRoleRunner, LiveEvalConfig, benchmark_routing_probe
from .formal import AristotleFormalVerifier, FormalVerifier
from .json_schema import validate
from .tier1 import SessionStore, Tier1LoopRunner, Tier1RunResult

_DEFAULT_CONFIG_PATH = Path("~/.hermes/deep-gvr/config.yaml")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _isoformat(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def default_config_path() -> Path:
    return _DEFAULT_CONFIG_PATH.expanduser()


def default_config_payload() -> dict[str, Any]:
    return DeepGvrConfig().to_dict()


def resolve_config_path(path: str | Path | None = None) -> Path:
    if path is None:
        return default_config_path()
    return Path(path).expanduser()


def write_default_config(path: str | Path | None = None, *, force: bool = False) -> Path:
    config_path = resolve_config_path(path)
    if config_path.exists() and not force:
        return config_path

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.safe_dump(default_config_payload(), sort_keys=False),
        encoding="utf-8",
    )
    return config_path


def load_runtime_config(path: str | Path | None = None) -> DeepGvrConfig:
    config_path = resolve_config_path(path)
    if not config_path.exists():
        write_default_config(config_path)

    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    schema = json.loads((_repo_root() / "schemas" / "config.schema.json").read_text(encoding="utf-8"))
    validate(payload, schema)
    return DeepGvrConfig.from_dict(payload)


def load_domain_context(
    config: DeepGvrConfig,
    *,
    domain_override: str | None = None,
) -> tuple[str, list[str]]:
    domain = domain_override or config.domain.default
    files: list[Path] = []
    if config.domain.context_file:
        files.append(Path(config.domain.context_file).expanduser())
    else:
        domain_files = {
            "qec": _repo_root() / "domain" / "qec_context.md",
            "fbqc": _repo_root() / "domain" / "fbqc_context.md",
        }
        if domain in domain_files:
            files.append(domain_files[domain])
        if domain == "qec":
            files.append(_repo_root() / "domain" / "known_results.md")

    notes: list[str] = []
    for path in files:
        if not path.exists():
            raise FileNotFoundError(f"Configured domain context file {path} does not exist.")
        notes.extend(_markdown_notes(path.read_text(encoding="utf-8")))
    return domain, notes


def _markdown_notes(text: str) -> list[str]:
    notes: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith(("- ", "* ")):
            notes.append(stripped[2:].strip())
        else:
            notes.append(stripped)
    return notes


def _split_csv_flags(values: list[str]) -> list[str]:
    items: list[str] = []
    for value in values:
        items.extend(part.strip() for part in value.split(",") if part.strip())
    return items


def _resolve_routing_probe(mode: str):
    if mode == "auto":
        return None
    return benchmark_routing_probe(ProbeStatus(mode))


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
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return dict(asdict(self))


def run_session_command(
    problem: str,
    *,
    config_path: str | Path | None = None,
    domain: str | None = None,
    prompt_root: str | Path = "prompts",
    routing_probe_mode: str = "auto",
    toolsets: list[str] | None = None,
    skills: list[str] | None = None,
    command_timeout_seconds: int = 120,
    session_id: str | None = None,
    executor: CommandExecutor | None = None,
    formal_verifier: FormalVerifier | None = None,
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
        routing_probe_mode=routing_probe_mode,
        toolsets=toolsets or [],
        skills=skills or [],
        command_timeout_seconds=command_timeout_seconds,
        executor=executor,
        formal_verifier=formal_verifier,
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
    routing_probe_mode: str = "auto",
    toolsets: list[str] | None = None,
    skills: list[str] | None = None,
    command_timeout_seconds: int = 120,
    executor: CommandExecutor | None = None,
    formal_verifier: FormalVerifier | None = None,
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
        routing_probe_mode=routing_probe_mode,
        toolsets=toolsets or [],
        skills=skills or [],
        command_timeout_seconds=command_timeout_seconds,
        executor=executor,
        formal_verifier=formal_verifier,
        resume_session_id=session_id,
    )


def _execute_command(
    *,
    command: str,
    config: DeepGvrConfig,
    config_path: Path,
    config_created: bool,
    prompt_root: str | Path,
    routing_probe_mode: str,
    toolsets: list[str],
    skills: list[str],
    command_timeout_seconds: int,
    executor: CommandExecutor | None,
    formal_verifier: FormalVerifier | None,
    run_problem: str | None = None,
    run_domain: str | None = None,
    run_literature_context: list[str] | None = None,
    run_session_id: str | None = None,
    resume_session_id: str | None = None,
) -> SkillSessionSummary:
    session_store = SessionStore(config.evidence.directory)
    runner = Tier1LoopRunner(
        config,
        session_store=session_store,
        routing_probe=_resolve_routing_probe(routing_probe_mode),
    )
    role_runner = HermesPromptRoleRunner(
        LiveEvalConfig(
            prompt_root=prompt_root,
            command_timeout_seconds=command_timeout_seconds,
            toolsets=list(toolsets),
            skills=list(skills),
        ),
        prompt_root=_resolve_prompt_root(prompt_root),
        executor=executor,
        cwd=_repo_root(),
    )

    verifier = formal_verifier or AristotleFormalVerifier()
    session_id = run_session_id if command == "run" else resume_session_id
    try:
        if command == "run":
            if run_problem is None or run_domain is None or run_literature_context is None:
                raise ValueError("Run command requires a problem, domain, and literature context.")
            result = runner.run(
                problem=run_problem,
                generator=role_runner.generator,
                verifier=role_runner.verifier,
                reviser=role_runner.reviser,
                simulator=None,
                formal_verifier=verifier,
                literature_context=run_literature_context,
                domain=run_domain,
                session_id=run_session_id,
            )
        elif command == "resume":
            if resume_session_id is None:
                raise ValueError("Resume command requires a session_id.")
            result = runner.resume(
                resume_session_id,
                generator=role_runner.generator,
                verifier=role_runner.verifier,
                reviser=role_runner.reviser,
                simulator=None,
                formal_verifier=verifier,
            )
        else:
            raise ValueError(f"Unsupported command {command!r}.")
    except Exception as exc:
        if session_id is None:
            raise
        checkpoint = _record_session_artifacts(
            session_store=session_store,
            session_id=session_id,
            command=command,
            transcripts=role_runner.transcripts,
            error=f"{type(exc).__name__}: {exc}",
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
        )

    checkpoint = _record_session_artifacts(
        session_store=session_store,
        session_id=result.session_id,
        command=command,
        transcripts=role_runner.transcripts,
        checkpoint=result.checkpoint,
    )
    return _summary_from_result(
        command=command,
        config_path=config_path,
        config_created=config_created,
        result=result,
        checkpoint=checkpoint,
    )


def _resolve_prompt_root(path: str | Path) -> Path:
    prompt_root = Path(path)
    if prompt_root.is_absolute():
        return prompt_root
    return _repo_root() / prompt_root


def _record_session_artifacts(
    *,
    session_store: SessionStore,
    session_id: str,
    command: str,
    transcripts: list[Any],
    checkpoint: SessionCheckpoint | None = None,
    error: str | None = None,
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
                f"{stamp}_{command}_role_transcripts.json",
                {
                    "command": command,
                    "generated_at": _isoformat(_utc_now()),
                    "calls": [item.to_dict() for item in transcripts],
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
        return SessionCheckpoint(
            session_id=session_id,
            problem="",
            domain="",
            started=_isoformat(_utc_now()),
            last_updated=_isoformat(_utc_now()),
            status="failed",
            current_iteration=0,
            max_iterations=0,
            next_phase="generate",
            literature_context=[],
            candidate=None,
            verification_report=None,
            verdict_history=[],
            result_summary="Command failed before a checkpoint summary was available.",
            final_verdict="PENDING",
            evidence_file=str(session_store.session_paths(session_id).evidence_log),
            artifacts_dir=str(session_store.session_paths(session_id).artifacts_dir),
            artifacts=[
                str((session_store.session_paths(session_id).session_dir.parent / artifact).resolve())
                for artifact in new_artifacts
            ],
        )

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
    init_parser.add_argument("--config", default="", help="Target config path. Default: ~/.hermes/deep-gvr/config.yaml")
    init_parser.add_argument("--force", action="store_true", help="Overwrite an existing config file.")
    init_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")

    common_parent = argparse.ArgumentParser(add_help=False)
    common_parent.add_argument("--config", default="", help="Config path. Default: ~/.hermes/deep-gvr/config.yaml")
    common_parent.add_argument("--prompt-root", default="prompts", help="Prompt directory.")
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
        help="Per-role Hermes command timeout.",
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
