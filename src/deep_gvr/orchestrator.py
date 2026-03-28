from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from .prompt_profiles import DEFAULT_PROMPT_PROFILE


@dataclass(slots=True)
class CommandExecutionResult:
    returncode: int
    stdout: str
    stderr: str


class CommandExecutor(Protocol):
    def __call__(self, command: list[str], cwd: Path) -> CommandExecutionResult:
        ...


@dataclass(slots=True)
class DelegatedOrchestratorConfig:
    hermes_binary: str = "hermes"
    prompt_profile: str = DEFAULT_PROMPT_PROFILE
    command_timeout_seconds: int = 120
    toolsets: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    provider: str = "default"
    model: str = ""


@dataclass(slots=True)
class OrchestratorTranscript:
    command: str
    session_id: str
    config_path: str
    prompt_root: str
    prompt_profile: str
    routing_probe: str
    skills: list[str]
    hermes_command: list[str]
    query: str
    response: str
    question: str | None = None
    domain_override: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "session_id": self.session_id,
            "config_path": self.config_path,
            "prompt_root": self.prompt_root,
            "prompt_profile": self.prompt_profile,
            "routing_probe": self.routing_probe,
            "skills": list(self.skills),
            "hermes_command": list(self.hermes_command),
            "query": self.query,
            "response": self.response,
            "question": self.question,
            "domain_override": self.domain_override,
        }


class HermesDelegatedOrchestratorRunner:
    def __init__(
        self,
        config: DelegatedOrchestratorConfig,
        *,
        cwd: Path | None = None,
        executor: CommandExecutor | None = None,
    ) -> None:
        self.config = config
        self.cwd = cwd or Path.cwd()
        self.executor = executor
        self.transcripts: list[OrchestratorTranscript] = []

    def run(
        self,
        *,
        question: str,
        session_id: str,
        config_path: Path,
        prompt_root: Path,
        routing_probe_mode: str,
        domain_override: str | None = None,
    ) -> dict[str, Any]:
        return self._invoke(
            command="run",
            session_id=session_id,
            config_path=config_path,
            prompt_root=prompt_root,
            routing_probe_mode=routing_probe_mode,
            question=question,
            domain_override=domain_override,
        )

    def resume(
        self,
        *,
        session_id: str,
        config_path: Path,
        prompt_root: Path,
        routing_probe_mode: str,
    ) -> dict[str, Any]:
        return self._invoke(
            command="resume",
            session_id=session_id,
            config_path=config_path,
            prompt_root=prompt_root,
            routing_probe_mode=routing_probe_mode,
        )

    def _invoke(
        self,
        *,
        command: str,
        session_id: str,
        config_path: Path,
        prompt_root: Path,
        routing_probe_mode: str,
        question: str | None = None,
        domain_override: str | None = None,
    ) -> dict[str, Any]:
        effective_skills = _merge_skills(self.config.skills)
        if self.executor is None:
            _ensure_skill_installed("deep-gvr")
        query = _build_orchestrator_query(
            command=command,
            session_id=session_id,
            config_path=config_path,
            prompt_root=prompt_root,
            prompt_profile=self.config.prompt_profile,
            routing_probe_mode=routing_probe_mode,
            question=question,
            domain_override=domain_override,
        )
        hermes_command = [self.config.hermes_binary, "chat", "-Q", "-q", query]
        if self.config.provider not in {"", "default", "auto"}:
            hermes_command.extend(["--provider", self.config.provider])
        if self.config.model not in {"", "configured-by-hermes", "provider-default"}:
            hermes_command.extend(["--model", self.config.model])
        if self.config.toolsets:
            hermes_command.extend(["--toolsets", ",".join(self.config.toolsets)])
        hermes_command.extend(["--skills", ",".join(effective_skills)])

        if self.executor is not None:
            result = self.executor(hermes_command, self.cwd)
        else:
            result = _default_executor(
                hermes_command,
                self.cwd,
                self.config.command_timeout_seconds,
            )

        response_text = result.stdout if result.returncode == 0 else f"{result.stdout}\n{result.stderr}".strip()
        self.transcripts.append(
            OrchestratorTranscript(
                command=command,
                session_id=session_id,
                config_path=str(config_path),
                prompt_root=str(prompt_root),
                prompt_profile=self.config.prompt_profile,
                routing_probe=routing_probe_mode,
                skills=effective_skills,
                hermes_command=list(hermes_command),
                query=query,
                response=response_text,
                question=question,
                domain_override=domain_override,
            )
        )
        if result.returncode != 0:
            raise RuntimeError(
                "Hermes delegated orchestrator failed "
                f"with exit code {result.returncode}: {result.stderr.strip() or result.stdout.strip()}"
            )
        return _extract_json_object(result.stdout)


def _merge_skills(skills: list[str]) -> list[str]:
    merged: list[str] = []
    for item in ["deep-gvr", *skills]:
        normalized = item.strip()
        if normalized and normalized not in merged:
            merged.append(normalized)
    return merged


def _ensure_skill_installed(skill_name: str) -> None:
    hermes_home = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes"))
    skill_path = hermes_home / "skills" / skill_name / "SKILL.md"
    if skill_path.exists():
        return
    raise RuntimeError(
        f"Hermes skill {skill_name!r} is not installed under {skill_path.parent}. "
        "Run scripts/install.sh before using the delegated orchestrator runtime."
    )


def _build_orchestrator_query(
    *,
    command: str,
    session_id: str,
    config_path: Path,
    prompt_root: Path,
    prompt_profile: str,
    routing_probe_mode: str,
    question: str | None = None,
    domain_override: str | None = None,
) -> str:
    request_payload = {
        "command": command,
        "session_id": session_id,
        "question": question,
        "domain_override": domain_override,
        "config_path": str(config_path),
        "prompt_root": str(prompt_root),
        "prompt_profile": prompt_profile,
        "routing_probe": routing_probe_mode,
        "workspace_root": str(Path.cwd()),
    }
    response_contract = {
        "command": "run | resume",
        "session_id": "string",
        "status": "string",
        "final_verdict": "PENDING | VERIFIED | FLAWS_FOUND | CANNOT_VERIFY",
        "result_summary": "string",
        "problem": "string",
        "domain": "string",
        "iterations": "number",
        "config_path": "string",
        "config_created": "boolean",
        "evidence_log": "string",
        "checkpoint_file": "string",
        "artifacts_dir": "string",
        "artifacts": ["string"],
        "error": "string | null",
    }
    return (
        "You are running the preloaded deep-gvr Hermes skill as the supported delegated orchestrator runtime.\n"
        "Use the skill instructions in full and treat the payload below as a /deep-gvr invocation.\n\n"
        f"Runtime request:\n{json.dumps(request_payload, indent=2)}\n\n"
        "Requirements:\n"
        "- Execute Generator, Verifier, Reviser, and any Simulator work through Hermes delegated role execution.\n"
        "- Do not call `uv run deep-gvr run` or `uv run deep-gvr resume`.\n"
        "- Use the supplied config path and write session evidence/checkpoint artifacts under the configured evidence directory.\n"
        "- Keep the verifier isolated from the original problem framing as described by the skill and architecture docs.\n"
        "- Return only one JSON object matching the response contract below.\n"
        "- If the run cannot complete, still return the JSON summary and populate the `error` field.\n\n"
        f"Response contract:\n{json.dumps(response_contract, indent=2)}"
    )


def _default_executor(
    command: list[str],
    cwd: Path,
    timeout_seconds: int | None,
) -> CommandExecutionResult:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
        return CommandExecutionResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
    except subprocess.TimeoutExpired:
        timeout_text = timeout_seconds if timeout_seconds is not None else "the configured"
        return CommandExecutionResult(
            returncode=124,
            stdout="",
            stderr=f"Hermes delegated orchestrator timed out after {timeout_text} seconds.",
        )


def _extract_json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise ValueError(f"Could not parse a JSON object from Hermes output: {text[:200]!r}")
