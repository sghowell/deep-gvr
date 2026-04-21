from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .cli import SkillSessionSummary, run_session_command, resume_session_command
from .contracts import ReleasePreflightReport
from .orchestrator import CommandExecutor
from .prompt_profiles import DEFAULT_PROMPT_PROFILE
from .release_surface import collect_codex_preflight


class CodexSshDevboxPreflightError(RuntimeError):
    def __init__(self, report: ReleasePreflightReport) -> None:
        failing_checks = ", ".join(check.name for check in report.checks if check.status.value != "ready")
        message = "Codex SSH/devbox execution is blocked by preflight checks."
        if failing_checks:
            message = f"{message} Failing checks: {failing_checks}."
        super().__init__(message)
        self.report = report


@dataclass(slots=True)
class CodexSshDevboxExecutionResult:
    preflight: ReleasePreflightReport
    session: SkillSessionSummary

    def to_dict(self) -> dict[str, object]:
        return {
            "preflight": self.preflight.to_dict(),
            "session": self.session.to_dict(),
        }


def ensure_codex_ssh_devbox_ready(
    *,
    config_path: Path | None = None,
    codex_skills_dir: Path | None = None,
    hermes_skills_dir: Path | None = None,
    hermes_config_path: Path | None = None,
) -> ReleasePreflightReport:
    report = collect_codex_preflight(
        config_path=config_path,
        codex_skills_dir=codex_skills_dir,
        hermes_skills_dir=hermes_skills_dir,
        hermes_config_path=hermes_config_path,
        ssh_devbox=True,
    )
    if not report.operator_ready:
        raise CodexSshDevboxPreflightError(report)
    return report


def run_codex_ssh_devbox_session(
    problem: str,
    *,
    config_path: str | Path | None = None,
    codex_skills_dir: Path | None = None,
    hermes_skills_dir: Path | None = None,
    hermes_config_path: Path | None = None,
    prompt_root: str | Path = "prompts",
    prompt_profile: str = DEFAULT_PROMPT_PROFILE,
    routing_probe_mode: str = "auto",
    toolsets: list[str] | None = None,
    skills: list[str] | None = None,
    command_timeout_seconds: int = 120,
    session_id: str | None = None,
    executor: CommandExecutor | None = None,
) -> CodexSshDevboxExecutionResult:
    report = ensure_codex_ssh_devbox_ready(
        config_path=Path(config_path).expanduser() if config_path is not None else None,
        codex_skills_dir=codex_skills_dir,
        hermes_skills_dir=hermes_skills_dir,
        hermes_config_path=hermes_config_path,
    )
    summary = run_session_command(
        problem,
        config_path=config_path,
        prompt_root=prompt_root,
        prompt_profile=prompt_profile,
        routing_probe_mode=routing_probe_mode,
        toolsets=toolsets,
        skills=skills,
        command_timeout_seconds=command_timeout_seconds,
        session_id=session_id,
        executor=executor,
    )
    return CodexSshDevboxExecutionResult(preflight=report, session=summary)


def resume_codex_ssh_devbox_session(
    session_id: str,
    *,
    config_path: str | Path | None = None,
    codex_skills_dir: Path | None = None,
    hermes_skills_dir: Path | None = None,
    hermes_config_path: Path | None = None,
    prompt_root: str | Path = "prompts",
    prompt_profile: str = DEFAULT_PROMPT_PROFILE,
    routing_probe_mode: str = "auto",
    toolsets: list[str] | None = None,
    skills: list[str] | None = None,
    command_timeout_seconds: int = 120,
    executor: CommandExecutor | None = None,
) -> CodexSshDevboxExecutionResult:
    report = ensure_codex_ssh_devbox_ready(
        config_path=Path(config_path).expanduser() if config_path is not None else None,
        codex_skills_dir=codex_skills_dir,
        hermes_skills_dir=hermes_skills_dir,
        hermes_config_path=hermes_config_path,
    )
    summary = resume_session_command(
        session_id,
        config_path=config_path,
        prompt_root=prompt_root,
        prompt_profile=prompt_profile,
        routing_probe_mode=routing_probe_mode,
        toolsets=toolsets,
        skills=skills,
        command_timeout_seconds=command_timeout_seconds,
        executor=executor,
    )
    return CodexSshDevboxExecutionResult(preflight=report, session=summary)


def codex_ssh_devbox_blocked_result(error: CodexSshDevboxPreflightError) -> dict[str, object]:
    return {
        "preflight": error.report.to_dict(),
        "session": None,
        "error": str(error),
    }
