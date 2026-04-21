from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from .contracts import CandidateSolution, OrchestratorBackend, VerificationReport
from .domain_context import load_domain_context
from .prompt_profiles import DEFAULT_PROMPT_PROFILE, build_live_role_query, normalize_prompt_profile
from .routing import EffectiveModelRoute, build_native_role_routing_plan, resolve_routing_probe
from .runtime_config import load_runtime_config
from .tier1 import GenerationRequest, RevisionRequest, Tier1LoopRunner, VerificationRequest


@dataclass(slots=True)
class CommandExecutionResult:
    returncode: int
    stdout: str
    stderr: str


class CommandExecutor(Protocol):
    def __call__(self, command: list[str], cwd: Path) -> CommandExecutionResult:
        ...


class OrchestratorBackendUnavailableError(RuntimeError):
    def __init__(self, message: str, *, final_verdict: str = "CANNOT_VERIFY") -> None:
        super().__init__(message)
        self.final_verdict = final_verdict


@dataclass(slots=True)
class OrchestratorBackendConfig:
    backend: OrchestratorBackend = OrchestratorBackend.HERMES
    hermes_binary: str = "hermes"
    codex_binary: str = "codex"
    prompt_profile: str = DEFAULT_PROMPT_PROFILE
    command_timeout_seconds: int = 120
    toolsets: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    provider: str = "default"
    model: str = ""
    role_routes: dict[str, Any] = field(default_factory=dict)
    writable_roots: list[str] = field(default_factory=list)


@dataclass(slots=True)
class OrchestratorTranscript:
    backend: str
    command: str
    session_id: str
    config_path: str
    prompt_root: str
    prompt_profile: str
    routing_probe: str
    role_routes: dict[str, Any]
    skills: list[str]
    backend_command: list[str]
    query: str
    response: str
    capability_evidence: dict[str, Any] = field(default_factory=dict)
    question: str | None = None
    domain_override: str | None = None
    role: str | None = None
    selected_route: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "backend": self.backend,
            "command": self.command,
            "session_id": self.session_id,
            "config_path": self.config_path,
            "prompt_root": self.prompt_root,
            "prompt_profile": self.prompt_profile,
            "routing_probe": self.routing_probe,
            "role_routes": dict(self.role_routes),
            "skills": list(self.skills),
            "backend_command": list(self.backend_command),
            "query": self.query,
            "response": self.response,
            "capability_evidence": dict(self.capability_evidence),
            "question": self.question,
            "domain_override": self.domain_override,
        }
        if self.role is not None:
            payload["role"] = self.role
        if self.selected_route is not None:
            payload["selected_route"] = dict(self.selected_route)
        if self.backend == OrchestratorBackend.HERMES.value:
            payload["hermes_command"] = list(self.backend_command)
        return payload


class OrchestratorRunner(Protocol):
    transcripts: list[OrchestratorTranscript]

    def run(
        self,
        *,
        question: str,
        session_id: str,
        config_path: Path,
        prompt_root: Path,
        routing_probe_mode: str,
        domain_override: str | None = None,
        role_routes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ...

    def resume(
        self,
        *,
        session_id: str,
        config_path: Path,
        prompt_root: Path,
        routing_probe_mode: str,
        role_routes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ...


class HermesDelegatedOrchestratorRunner:
    def __init__(
        self,
        config: OrchestratorBackendConfig,
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
        role_routes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._invoke(
            command="run",
            session_id=session_id,
            config_path=config_path,
            prompt_root=prompt_root,
            routing_probe_mode=routing_probe_mode,
            question=question,
            domain_override=domain_override,
            role_routes=role_routes,
        )

    def resume(
        self,
        *,
        session_id: str,
        config_path: Path,
        prompt_root: Path,
        routing_probe_mode: str,
        role_routes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._invoke(
            command="resume",
            session_id=session_id,
            config_path=config_path,
            prompt_root=prompt_root,
            routing_probe_mode=routing_probe_mode,
            role_routes=role_routes,
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
        role_routes: dict[str, Any] | None = None,
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
            role_routes=role_routes or self.config.role_routes,
            workspace_root=self.cwd,
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
        transcript = OrchestratorTranscript(
            backend=OrchestratorBackend.HERMES.value,
            command=command,
            session_id=session_id,
            config_path=str(config_path),
            prompt_root=str(prompt_root),
            prompt_profile=self.config.prompt_profile,
            routing_probe=routing_probe_mode,
            role_routes=dict(role_routes or self.config.role_routes),
            skills=effective_skills,
            backend_command=list(hermes_command),
            query=query,
            response=response_text,
            question=question,
            domain_override=domain_override,
        )
        self.transcripts.append(transcript)
        if result.returncode != 0:
            raise RuntimeError(
                "Hermes delegated orchestrator failed "
                f"with exit code {result.returncode}: {result.stderr.strip() or result.stdout.strip()}"
            )
        payload = _extract_json_object(result.stdout)
        capability_evidence = payload.get("capability_evidence")
        if isinstance(capability_evidence, dict):
            transcript.capability_evidence = dict(capability_evidence)
        return payload


class CodexLocalOrchestratorRunner:
    def __init__(
        self,
        config: OrchestratorBackendConfig,
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
        role_routes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._invoke(
            command="run",
            session_id=session_id,
            config_path=config_path,
            prompt_root=prompt_root,
            routing_probe_mode=routing_probe_mode,
            question=question,
            domain_override=domain_override,
            role_routes=role_routes,
        )

    def resume(
        self,
        *,
        session_id: str,
        config_path: Path,
        prompt_root: Path,
        routing_probe_mode: str,
        role_routes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._invoke(
            command="resume",
            session_id=session_id,
            config_path=config_path,
            prompt_root=prompt_root,
            routing_probe_mode=routing_probe_mode,
            role_routes=role_routes,
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
        role_routes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.executor is None:
            _ensure_binary_available(self.config.codex_binary, backend_name="Codex-local orchestrator")
        runtime_config = load_runtime_config(config_path)
        routing_probe = resolve_routing_probe(routing_probe_mode)
        routing_plan = build_native_role_routing_plan(runtime_config, routing_probe=routing_probe)
        loop_runner = Tier1LoopRunner(
            runtime_config,
            routing_probe=routing_probe,
            routing_plan=routing_plan,
        )

        if command == "run":
            if question is None:
                raise ValueError("Codex-local run requires a research question.")
            selected_domain, literature_context = load_domain_context(runtime_config, domain_override=domain_override)
            result = loop_runner.run(
                problem=question,
                domain=selected_domain,
                literature_context=literature_context,
                session_id=session_id,
                generator=lambda request: self._run_codex_generator(
                    command=command,
                    request=request,
                    config_path=config_path,
                    prompt_root=prompt_root,
                    routing_probe_mode=routing_probe_mode,
                    role_routes=role_routes,
                ),
                verifier=lambda request: self._run_codex_verifier(
                    command=command,
                    request=request,
                    config_path=config_path,
                    prompt_root=prompt_root,
                    routing_probe_mode=routing_probe_mode,
                    role_routes=role_routes,
                ),
                reviser=lambda request: self._run_codex_reviser(
                    command=command,
                    request=request,
                    config_path=config_path,
                    prompt_root=prompt_root,
                    routing_probe_mode=routing_probe_mode,
                    role_routes=role_routes,
                ),
            )
        elif command == "resume":
            result = loop_runner.resume(
                session_id,
                generator=lambda request: self._run_codex_generator(
                    command=command,
                    request=request,
                    config_path=config_path,
                    prompt_root=prompt_root,
                    routing_probe_mode=routing_probe_mode,
                    role_routes=role_routes,
                ),
                verifier=lambda request: self._run_codex_verifier(
                    command=command,
                    request=request,
                    config_path=config_path,
                    prompt_root=prompt_root,
                    routing_probe_mode=routing_probe_mode,
                    role_routes=role_routes,
                ),
                reviser=lambda request: self._run_codex_reviser(
                    command=command,
                    request=request,
                    config_path=config_path,
                    prompt_root=prompt_root,
                    routing_probe_mode=routing_probe_mode,
                    role_routes=role_routes,
                ),
            )
        else:
            raise ValueError(f"Unsupported command {command!r}.")

        return _tier1_result_payload(
            command=command,
            config_path=config_path,
            result=result,
        )

    def _run_codex_generator(
        self,
        *,
        command: str,
        request: GenerationRequest,
        config_path: Path,
        prompt_root: Path,
        routing_probe_mode: str,
        role_routes: dict[str, Any] | None,
    ) -> CandidateSolution:
        payload = {
            "session_id": request.session_id,
            "problem": request.problem,
            "domain": request.domain,
            "literature_context": list(request.literature_context),
            "prior_verdicts": [item.to_dict() for item in request.prior_verdicts],
            "branch_id": request.branch_id,
            "branch_strategy": request.branch_strategy.value,
            "branch_parent_id": request.branch_parent_id,
            "branch_rationale": request.branch_rationale,
            "trigger_flaws": list(request.trigger_flaws),
        }
        result = self._execute_codex_role(
            command=command,
            role="generator",
            route=request.route,
            config_path=config_path,
            prompt_root=prompt_root,
            routing_probe_mode=routing_probe_mode,
            role_routes=role_routes,
            payload=payload,
            response_contract=_candidate_response_contract(),
            response_schema=_candidate_response_schema(),
            session_id=request.session_id,
            question=request.problem,
        )
        return CandidateSolution.from_dict(result)

    def _run_codex_verifier(
        self,
        *,
        command: str,
        request: VerificationRequest,
        config_path: Path,
        prompt_root: Path,
        routing_probe_mode: str,
        role_routes: dict[str, Any] | None,
    ) -> VerificationReport:
        payload = {
            "session_id": request.session_id,
            "iteration": request.iteration,
            "candidate": request.candidate.to_dict(),
            "analysis_results": request.analysis_results.to_dict() if request.analysis_results is not None else None,
            "formal_results": [item.to_dict() for item in request.formal_results or []],
        }
        result = self._execute_codex_role(
            command=command,
            role="verifier",
            route=request.route,
            config_path=config_path,
            prompt_root=prompt_root,
            routing_probe_mode=routing_probe_mode,
            role_routes=role_routes,
            payload=payload,
            response_contract=_verification_response_contract(),
            response_schema=_verification_response_schema(),
            session_id=request.session_id,
        )
        return VerificationReport.from_dict(result)

    def _run_codex_reviser(
        self,
        *,
        command: str,
        request: RevisionRequest,
        config_path: Path,
        prompt_root: Path,
        routing_probe_mode: str,
        role_routes: dict[str, Any] | None,
    ) -> CandidateSolution:
        payload = {
            "session_id": request.session_id,
            "iteration": request.iteration,
            "candidate": request.candidate.to_dict(),
            "verification_report": request.verification_report.to_dict(),
            "branch_id": request.branch_id,
            "branch_strategy": request.branch_strategy.value,
            "branch_parent_id": request.branch_parent_id,
            "branch_rationale": request.branch_rationale,
        }
        result = self._execute_codex_role(
            command=command,
            role="reviser",
            route=request.route,
            config_path=config_path,
            prompt_root=prompt_root,
            routing_probe_mode=routing_probe_mode,
            role_routes=role_routes,
            payload=payload,
            response_contract=_candidate_response_contract(),
            response_schema=_candidate_response_schema(),
            session_id=request.session_id,
        )
        return CandidateSolution.from_dict(result)

    def _execute_codex_role(
        self,
        *,
        command: str,
        role: str,
        route: EffectiveModelRoute,
        config_path: Path,
        prompt_root: Path,
        routing_probe_mode: str,
        role_routes: dict[str, Any] | None,
        payload: dict[str, Any],
        response_contract: dict[str, Any],
        response_schema: dict[str, Any],
        session_id: str,
        question: str | None = None,
    ) -> dict[str, Any]:
        effective_route = _codex_effective_route(route)
        query = build_live_role_query(
            role=role,
            prompt_text=_runtime_role_prompt(prompt_root, role, self.config.prompt_profile),
            payload=payload,
            response_contract=response_contract,
            route_notes=_codex_route_notes(effective_route),
            route_temperature=effective_route.temperature,
            prompt_profile=self.config.prompt_profile,
        )
        codex_command, response_text = self._run_codex_command(
            query=query,
            response_schema=response_schema,
            route=effective_route,
        )
        transcript = OrchestratorTranscript(
            backend=OrchestratorBackend.CODEX_LOCAL.value,
            command=command,
            session_id=session_id,
            config_path=str(config_path),
            prompt_root=str(prompt_root),
            prompt_profile=self.config.prompt_profile,
            routing_probe=routing_probe_mode,
            role_routes=dict(role_routes or self.config.role_routes),
            skills=[],
            backend_command=list(codex_command),
            query=query,
            response=response_text,
            question=question,
            role=role,
            selected_route=_effective_route_payload(effective_route),
        )
        self.transcripts.append(transcript)
        try:
            return _extract_json_object(response_text)
        except ValueError as exc:
            raise OrchestratorBackendUnavailableError(
                f"Codex-local {role} role did not return a valid JSON payload: {exc}"
            ) from exc

    def _run_codex_command(
        self,
        *,
        query: str,
        response_schema: dict[str, Any],
        route: EffectiveModelRoute,
    ) -> tuple[list[str], str]:
        with tempfile.TemporaryDirectory(prefix="deep-gvr-codex-role-") as tmpdir:
            temp_root = Path(tmpdir)
            response_schema_path = temp_root / "role_response.schema.json"
            output_path = temp_root / "role_response.json"
            response_schema_path.write_text(json.dumps(response_schema, indent=2), encoding="utf-8")
            codex_command = [
                self.config.codex_binary,
                "exec",
                "--cd",
                str(temp_root),
                "--sandbox",
                "workspace-write",
                "--color",
                "never",
                "--skip-git-repo-check",
                "--json",
                "--output-schema",
                str(response_schema_path),
                "--output-last-message",
                str(output_path),
            ]
            if route.provider not in {"", "default", "auto"}:
                codex_command.extend(["-c", f'model_provider="{route.provider}"'])
            if route.model not in {"", "configured-by-codex", "provider-default"}:
                codex_command.extend(["--model", route.model])
            codex_command.append(query)

            if self.executor is not None:
                result = self.executor(codex_command, temp_root)
            else:
                result = _default_executor(
                    codex_command,
                    temp_root,
                    self.config.command_timeout_seconds,
                    backend_name="Codex-local orchestrator",
                )

            response_text = output_path.read_text(encoding="utf-8").strip() if output_path.exists() else ""
            if not response_text:
                response_text = result.stdout if result.returncode == 0 else f"{result.stdout}\n{result.stderr}".strip()
            if result.returncode != 0:
                raise OrchestratorBackendUnavailableError(
                    "Codex-local orchestrator failed "
                    f"with exit code {result.returncode}: {result.stderr.strip() or result.stdout.strip()}"
                )
            return codex_command, response_text


def build_orchestrator_runner(
    config: OrchestratorBackendConfig,
    *,
    cwd: Path | None = None,
    executor: CommandExecutor | None = None,
) -> OrchestratorRunner:
    if config.backend is OrchestratorBackend.HERMES:
        return HermesDelegatedOrchestratorRunner(config, cwd=cwd, executor=executor)
    if config.backend is OrchestratorBackend.CODEX_LOCAL:
        return CodexLocalOrchestratorRunner(config, cwd=cwd, executor=executor)
    raise ValueError(f"Unsupported orchestrator backend {config.backend!r}.")


def _runtime_role_prompt(prompt_root: Path, role: str, prompt_profile: str) -> str:
    base_prompt = _load_role_prompt(prompt_root, role=role, prompt_profile=prompt_profile)
    runtime_constraints = (
        "\n\n## Runtime Constraints\n"
        "- This is a runtime role execution, not a repository development task.\n"
        "- Do not edit repository source files, tests, docs, plans, or release assets.\n"
        "- Do not call `uv run deep-gvr run` or `uv run deep-gvr resume`.\n"
        "- Do not run Tier 2 adapters or Tier 3 proof backends directly from this role call.\n"
        "- Return only the requested JSON object and no extra prose.\n"
    )
    return base_prompt + runtime_constraints


def _load_role_prompt(prompt_root: Path, *, role: str, prompt_profile: str) -> str:
    normalized_profile = normalize_prompt_profile(prompt_profile)
    prompt_name = f"{role}.md"
    if role == "verifier" and normalized_profile == "compact":
        prompt_name = "verifier_compact.md"
    prompt_path = prompt_root / prompt_name
    if not prompt_path.exists():
        raise OrchestratorBackendUnavailableError(f"Missing role prompt at {prompt_path}.")
    return prompt_path.read_text(encoding="utf-8").strip()


def _candidate_response_contract() -> dict[str, Any]:
    return {
        "hypothesis": "string",
        "approach": "string",
        "technical_details": ["string"],
        "expected_results": ["string"],
        "assumptions": ["string"],
        "limitations": ["string"],
        "references": ["string"],
        "revision_notes": ["string"],
    }


def _candidate_response_schema() -> dict[str, Any]:
    string_list = {"type": "array", "items": {"type": "string"}}
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "hypothesis": {"type": "string"},
            "approach": {"type": "string"},
            "technical_details": string_list,
            "expected_results": string_list,
            "assumptions": string_list,
            "limitations": string_list,
            "references": string_list,
            "revision_notes": string_list,
        },
        "required": [
            "hypothesis",
            "approach",
            "technical_details",
            "expected_results",
            "assumptions",
            "limitations",
            "references",
            "revision_notes",
        ],
    }


def _verification_response_contract() -> dict[str, Any]:
    return {
        "verdict": "VERIFIED | FLAWS_FOUND | CANNOT_VERIFY",
        "tier1": {
            "checks": [{"check": "string", "status": "pass|fail|uncertain", "detail": "string"}],
            "overall": "VERIFIED | FLAWS_FOUND | CANNOT_VERIFY",
            "flaws": ["string"],
            "caveats": ["string"],
        },
        "tier2": {
            "analysis_requested": "boolean",
            "reason": "string",
            "analysis_spec": "object | null",
            "results": "object | null",
            "interpretation": "string | null",
        },
        "tier3": [
            {
                "claim": "string",
                "backend": "string",
                "proof_status": "requested|pending|proved|disproved|timeout|error|unavailable",
                "details": "string",
                "lean_code": "string",
                "proof_time_seconds": "number | null",
            }
        ],
        "flaws": ["string"],
        "caveats": ["string"],
        "cannot_verify_reason": "string | null",
    }


def _verification_response_schema() -> dict[str, Any]:
    check_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "check": {"type": "string"},
            "status": {"type": "string", "enum": ["pass", "fail", "uncertain"]},
            "detail": {"type": "string"},
        },
        "required": ["check", "status", "detail"],
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "verdict": {"type": "string", "enum": ["VERIFIED", "FLAWS_FOUND", "CANNOT_VERIFY"]},
            "tier1": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "checks": {"type": "array", "items": check_schema},
                    "overall": {"type": "string", "enum": ["VERIFIED", "FLAWS_FOUND", "CANNOT_VERIFY"]},
                    "flaws": {"type": "array", "items": {"type": "string"}},
                    "caveats": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["checks", "overall", "flaws", "caveats"],
            },
            "tier2": {
                "anyOf": [
                    {"type": "null"},
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "analysis_requested": {"type": "boolean"},
                            "reason": {"type": "string"},
                            "analysis_spec": {"type": ["object", "null"]},
                            "results": {"type": ["object", "null"]},
                            "interpretation": {"type": ["string", "null"]},
                        },
                        "required": ["analysis_requested", "reason"],
                    },
                ]
            },
            "tier3": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "claim": {"type": "string"},
                        "backend": {"type": "string"},
                        "proof_status": {
                            "type": "string",
                            "enum": ["requested", "pending", "proved", "disproved", "timeout", "error", "unavailable"],
                        },
                        "details": {"type": "string"},
                        "lean_code": {"type": "string"},
                        "proof_time_seconds": {"type": ["number", "null"]},
                    },
                    "required": ["claim", "backend", "proof_status", "details", "lean_code", "proof_time_seconds"],
                },
            },
            "flaws": {"type": "array", "items": {"type": "string"}},
            "caveats": {"type": "array", "items": {"type": "string"}},
            "cannot_verify_reason": {"type": ["string", "null"]},
        },
        "required": ["verdict", "tier1", "tier2", "tier3", "flaws", "caveats", "cannot_verify_reason"],
    }


def _codex_effective_route(route: EffectiveModelRoute) -> EffectiveModelRoute:
    model = route.model
    notes = list(route.notes)
    if route.provider == "default" and model == "configured-by-hermes":
        model = "configured-by-codex"
        notes.append("Resolved the default backend model to the active Codex default.")
    return EffectiveModelRoute(
        provider=route.provider,
        model=model,
        routing_mode=route.routing_mode,
        temperature=route.temperature,
        notes=notes,
        fallback_routes=list(route.fallback_routes),
    )


def _codex_route_notes(route: EffectiveModelRoute) -> list[str]:
    return [
        f"provider={route.provider}",
        f"model={route.model}",
        *list(route.notes),
    ]


def _effective_route_payload(route: EffectiveModelRoute) -> dict[str, Any]:
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


def _tier1_result_payload(
    *,
    command: str,
    config_path: Path,
    result: Any,
) -> dict[str, Any]:
    checkpoint = result.checkpoint
    session_root = result.session_paths.session_dir.parent
    artifacts = [
        str((session_root / artifact).resolve()) if not Path(artifact).is_absolute() else str(Path(artifact))
        for artifact in checkpoint.artifacts
    ]
    return {
        "command": command,
        "session_id": result.session_id,
        "status": checkpoint.status,
        "final_verdict": checkpoint.final_verdict,
        "result_summary": checkpoint.result_summary,
        "problem": checkpoint.problem,
        "domain": checkpoint.domain,
        "iterations": len(checkpoint.verdict_history),
        "config_path": str(config_path),
        "config_created": False,
        "evidence_log": str(result.session_paths.evidence_log),
        "checkpoint_file": str(result.session_paths.checkpoint_file),
        "artifacts_dir": str(result.session_paths.artifacts_dir),
        "artifacts": artifacts,
        "capability_evidence": {},
        "error": None,
    }


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


def _ensure_binary_available(binary: str, *, backend_name: str) -> None:
    if shutil.which(binary) is not None:
        return
    raise OrchestratorBackendUnavailableError(
        f"{backend_name} requires {binary!r} to be available on PATH."
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
    role_routes: dict[str, Any] | None = None,
    workspace_root: Path | None = None,
) -> str:
    request_payload = _orchestrator_request_payload(
        command=command,
        session_id=session_id,
        config_path=config_path,
        prompt_root=prompt_root,
        prompt_profile=prompt_profile,
        routing_probe_mode=routing_probe_mode,
        question=question,
        domain_override=domain_override,
        role_routes=role_routes,
        workspace_root=workspace_root,
    )
    response_contract = _orchestrator_response_contract()
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
        "- Include `capability_evidence` whenever the delegated runtime can observe actual role-level routing or delegated MCP behavior.\n"
        "- Treat `role_routes` as requested routing intent, not proof of capability closure.\n"
        "- Only mark `per_subagent_model_routing.distinct_routes_verified=true` when the delegated run can confirm generator and verifier actually executed on distinct routes.\n"
        "- Only mark `subagent_mcp_inheritance.delegated_mcp_verified=true` when the verifier itself exercised delegated Aristotle MCP access directly.\n"
        "- If a capability is not actually observed, omit it or return the verified flag as false instead of inferring success from config or probe overrides.\n"
        "- If the run cannot complete, still return the JSON summary and populate the `error` field.\n\n"
        f"Response contract:\n{json.dumps(response_contract, indent=2)}"
    )


def _orchestrator_request_payload(
    *,
    command: str,
    session_id: str,
    config_path: Path,
    prompt_root: Path,
    prompt_profile: str,
    routing_probe_mode: str,
    question: str | None = None,
    domain_override: str | None = None,
    role_routes: dict[str, Any] | None = None,
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    return {
        "command": command,
        "session_id": session_id,
        "question": question,
        "domain_override": domain_override,
        "config_path": str(config_path),
        "prompt_root": str(prompt_root),
        "prompt_profile": prompt_profile,
        "routing_probe": routing_probe_mode,
        "role_routes": role_routes or {},
        "workspace_root": str((workspace_root or Path.cwd()).resolve()),
    }


def _orchestrator_response_contract() -> dict[str, Any]:
    return {
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
        "capability_evidence": {
            "per_subagent_model_routing": {
                "distinct_routes_verified": "boolean",
                "route_pairs": {"generator": {"provider": "string", "model": "string"}, "verifier": {"provider": "string", "model": "string"}},
                "evidence_source": "string"
            },
            "subagent_mcp_inheritance": {
                "delegated_mcp_verified": "boolean",
                "mcp_details": {"tool": "string"},
                "evidence_source": "string"
            }
        },
        "error": "string | null",
    }


def _orchestrator_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "command": {"type": "string", "enum": ["run", "resume"]},
            "session_id": {"type": "string"},
            "status": {"type": "string"},
            "final_verdict": {
                "type": "string",
                "enum": ["PENDING", "VERIFIED", "FLAWS_FOUND", "CANNOT_VERIFY"],
            },
            "result_summary": {"type": "string"},
            "problem": {"type": "string"},
            "domain": {"type": "string"},
            "iterations": {"type": "number"},
            "config_path": {"type": "string"},
            "config_created": {"type": "boolean"},
            "evidence_log": {"type": "string"},
            "checkpoint_file": {"type": "string"},
            "artifacts_dir": {"type": "string"},
            "artifacts": {"type": "array", "items": {"type": "string"}},
            "capability_evidence": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "per_subagent_model_routing": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "distinct_routes_verified": {"type": "boolean"},
                            "route_pairs": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "generator": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "provider": {"type": "string"},
                                            "model": {"type": "string"},
                                        },
                                        "required": ["provider", "model"],
                                    },
                                    "verifier": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "provider": {"type": "string"},
                                            "model": {"type": "string"},
                                        },
                                        "required": ["provider", "model"],
                                    },
                                },
                                "required": ["generator", "verifier"],
                            },
                            "evidence_source": {"type": "string"},
                        },
                        "required": ["distinct_routes_verified", "route_pairs", "evidence_source"],
                    },
                    "subagent_mcp_inheritance": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "delegated_mcp_verified": {"type": "boolean"},
                            "mcp_details": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {"tool": {"type": "string"}},
                                "required": ["tool"],
                            },
                            "evidence_source": {"type": "string"},
                        },
                        "required": ["delegated_mcp_verified", "mcp_details", "evidence_source"],
                    },
                },
            },
            "error": {"type": ["string", "null"]},
        },
        "required": [
            "command",
            "session_id",
            "status",
            "final_verdict",
            "result_summary",
            "problem",
            "domain",
            "iterations",
            "config_path",
            "config_created",
            "evidence_log",
            "checkpoint_file",
            "artifacts_dir",
            "artifacts",
            "capability_evidence",
            "error",
        ],
    }


def _default_executor(
    command: list[str],
    cwd: Path,
    timeout_seconds: int | None,
    *,
    backend_name: str = "Hermes delegated orchestrator",
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
            stderr=f"{backend_name} timed out after {timeout_text} seconds.",
        )


def _normalized_writable_roots(configured_roots: list[str], cwd: Path) -> list[str]:
    roots: list[str] = []
    for candidate in [str(cwd), *configured_roots]:
        normalized = str(Path(candidate).expanduser().resolve())
        if normalized not in roots:
            roots.append(normalized)
    return roots


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
