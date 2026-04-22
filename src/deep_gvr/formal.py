from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Protocol

import yaml

from .contracts import FormalProofHandle, FormalProofLifecycle, MathCodeConfig, ProofStatus, Tier3ClaimResult, Tier3Config
from .prompt_profiles import DEFAULT_PROMPT_PROFILE, build_formal_query


@dataclass(slots=True)
class FormalVerificationRequest:
    session_id: str
    iteration: int
    claims: list[Tier3ClaimResult]
    backend: str
    timeout_seconds: int
    lifecycle_state: FormalProofLifecycle | None = None
    enable_lifecycle: bool = False


@dataclass(slots=True)
class AristotleTransportStatus:
    hermes_available: bool
    aristotle_key_present: bool
    hermes_config_path: str
    hermes_config_exists: bool
    mcp_server_name: str
    mcp_server_configured: bool
    configured_mcp_servers: list[str]

    @property
    def ready(self) -> bool:
        return self.hermes_available and self.aristotle_key_present and self.mcp_server_configured


@dataclass(slots=True)
class MathCodeTransportStatus:
    mathcode_root: str
    mathcode_root_exists: bool
    run_script: str
    run_script_exists: bool
    run_script_executable: bool
    autolean_exists: bool
    lean_workspace_exists: bool

    @property
    def ready(self) -> bool:
        return (
            self.mathcode_root_exists
            and self.run_script_exists
            and self.run_script_executable
            and self.autolean_exists
            and self.lean_workspace_exists
        )


@dataclass(slots=True)
class OpenGaussTransportStatus:
    opengauss_root: str
    opengauss_root_exists: bool
    install_script: str
    install_script_exists: bool
    local_launcher: str
    local_launcher_exists: bool
    runner_venv: str
    runner_venv_exists: bool
    gauss_binary: str
    gauss_available: bool
    gauss_config_path: str
    gauss_config_exists: bool

    @property
    def ready(self) -> bool:
        return self.gauss_available and self.gauss_config_exists


@dataclass(slots=True)
class CommandExecutionResult:
    returncode: int
    stdout: str
    stderr: str


class CommandExecutor(Protocol):
    def __call__(self, command: list[str], cwd: Path) -> CommandExecutionResult:
        ...


@dataclass(slots=True)
class FormalVerificationResultSet:
    results: list[Tier3ClaimResult]
    transport_artifact: dict[str, Any] | None = None
    lifecycle_state: FormalProofLifecycle | None = None
    pending: bool = False


class FormalVerifier(Protocol):
    def __call__(self, request: FormalVerificationRequest) -> FormalVerificationResultSet | list[Tier3ClaimResult]:
        ...


_ARISTOTLE_PROJECT_ID_RE = re.compile(r"Project created:\s*([0-9a-fA-F-]+)")
_ARISTOTLE_TARBALL_RE = re.compile(r"Project saved to\s+([^\s]+\.tar\.gz)")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _isoformat_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def default_hermes_config_path() -> Path:
    return Path("~/.hermes/config.yaml").expanduser()


def default_mathcode_root() -> Path:
    return Path("~/dev/mathcode").expanduser()


def default_mathcode_run_script() -> Path:
    return default_mathcode_root() / "run"


def default_opengauss_root() -> Path:
    return Path("~/dev/OpenGauss").expanduser()


def default_gauss_home() -> Path:
    return Path(os.getenv("GAUSS_HOME", "~/.gauss")).expanduser()


def default_gauss_config_path() -> Path:
    return default_gauss_home() / "config.yaml"


def load_hermes_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = default_hermes_config_path() if path is None else Path(path).expanduser()
    if not config_path.exists():
        return {}
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        return {}
    return payload


def inspect_aristotle_transport(
    *,
    hermes_binary: str = "hermes",
    hermes_config_path: str | Path | None = None,
    mcp_server_name: str = "aristotle",
) -> AristotleTransportStatus:
    config_path = default_hermes_config_path() if hermes_config_path is None else Path(hermes_config_path).expanduser()
    config = load_hermes_config(config_path)
    mcp_servers = config.get("mcp_servers")
    configured_servers = (
        sorted(str(name) for name in mcp_servers.keys()) if isinstance(mcp_servers, dict) else []
    )
    return AristotleTransportStatus(
        hermes_available=shutil.which(hermes_binary) is not None,
        aristotle_key_present=bool(os.getenv("ARISTOTLE_API_KEY")),
        hermes_config_path=str(config_path),
        hermes_config_exists=config_path.exists(),
        mcp_server_name=mcp_server_name,
        mcp_server_configured=isinstance(mcp_servers, dict) and mcp_server_name in mcp_servers,
        configured_mcp_servers=configured_servers,
    )


def _resolve_mathcode_root(path: str | Path | None) -> Path:
    if path is None:
        return default_mathcode_root()
    return Path(path).expanduser()


def _resolve_mathcode_run_script(path: str | Path | None, *, mathcode_root: Path) -> Path:
    if path is None:
        return default_mathcode_run_script()
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    if "/" in str(path):
        return mathcode_root / candidate
    located = shutil.which(str(path))
    if located:
        return Path(located)
    return mathcode_root / candidate


def inspect_mathcode_transport(
    *,
    mathcode_root: str | Path | None = None,
    run_script: str | Path | None = None,
) -> MathCodeTransportStatus:
    root_path = _resolve_mathcode_root(mathcode_root)
    run_path = _resolve_mathcode_run_script(run_script, mathcode_root=root_path)
    return MathCodeTransportStatus(
        mathcode_root=str(root_path),
        mathcode_root_exists=root_path.exists(),
        run_script=str(run_path),
        run_script_exists=run_path.exists(),
        run_script_executable=run_path.exists() and os.access(run_path, os.X_OK),
        autolean_exists=(root_path / "AUTOLEAN").exists(),
        lean_workspace_exists=(root_path / "lean-workspace").exists(),
    )


def _resolve_binary(binary: str | Path) -> tuple[str, bool]:
    candidate = Path(binary).expanduser()
    if candidate.is_absolute() or "/" in str(binary):
        return str(candidate), candidate.exists() and os.access(candidate, os.X_OK)
    located = shutil.which(str(binary))
    return located or str(binary), located is not None


def inspect_opengauss_transport(
    *,
    opengauss_root: str | Path | None = None,
    gauss_binary: str | Path = "gauss",
    gauss_config_path: str | Path | None = None,
) -> OpenGaussTransportStatus:
    root_path = default_opengauss_root() if opengauss_root is None else Path(opengauss_root).expanduser()
    install_script = root_path / "scripts" / "install.sh"
    local_launcher = root_path / "gauss"
    runner_venv = root_path / ".opengauss-installer-venv"
    resolved_binary, gauss_available = _resolve_binary(gauss_binary)
    config_path = default_gauss_config_path() if gauss_config_path is None else Path(gauss_config_path).expanduser()
    return OpenGaussTransportStatus(
        opengauss_root=str(root_path),
        opengauss_root_exists=root_path.exists(),
        install_script=str(install_script),
        install_script_exists=install_script.exists(),
        local_launcher=str(local_launcher),
        local_launcher_exists=local_launcher.exists(),
        runner_venv=str(runner_venv),
        runner_venv_exists=runner_venv.exists(),
        gauss_binary=resolved_binary,
        gauss_available=gauss_available,
        gauss_config_path=str(config_path),
        gauss_config_exists=config_path.exists(),
    )


class AristotleFormalVerifier:
    def __init__(
        self,
        executor: Callable[[FormalVerificationRequest], FormalVerificationResultSet | list[Tier3ClaimResult]] | None = None,
        *,
        command_executor: CommandExecutor | None = None,
        cli_command_executor: CommandExecutor | None = None,
        hermes_binary: str = "hermes",
        aristotle_binary: str = "aristotle",
        hermes_config_path: str | Path | None = None,
        prompt_root: str | Path = "prompts",
        cwd: str | Path | None = None,
        command_timeout_seconds: int | None = None,
        provider: str = "default",
        model: str = "",
        toolsets: list[str] | None = None,
        skills: list[str] | None = None,
        mcp_server_name: str = "aristotle",
        prompt_profile: str = DEFAULT_PROMPT_PROFILE,
        allow_cli_fallback: bool = True,
        prefer_lifecycle: bool = False,
    ) -> None:
        self.executor = executor
        self.command_executor = command_executor
        self.cli_command_executor = cli_command_executor
        self.hermes_binary = hermes_binary
        self.aristotle_binary = aristotle_binary
        self.hermes_config_path = hermes_config_path
        self.prompt_root = Path(prompt_root)
        self.cwd = Path(cwd) if cwd is not None else _repo_root()
        self.command_timeout_seconds = command_timeout_seconds
        self.provider = provider
        self.model = model
        self.toolsets = list(toolsets or [])
        self.skills = list(skills or [])
        self.mcp_server_name = mcp_server_name
        self.prompt_profile = prompt_profile
        self.allow_cli_fallback = allow_cli_fallback
        self.prefer_lifecycle = prefer_lifecycle

    def __call__(self, request: FormalVerificationRequest) -> FormalVerificationResultSet:
        if request.backend != "aristotle":
            return self._result_set(
                request,
                status=ProofStatus.ERROR,
                details=f"Unsupported formal backend {request.backend!r} for the Aristotle runner.",
                proof_time_seconds=0.0,
                artifact_status="unsupported_backend",
            )

        if self.executor is not None:
            try:
                outcome = self.executor(request)
                if isinstance(outcome, FormalVerificationResultSet):
                    return outcome
                return FormalVerificationResultSet(
                    results=list(outcome),
                    pending=any(item.proof_status is ProofStatus.PENDING for item in outcome),
                )
            except TimeoutError:
                return self._result_set(
                    request,
                    status=ProofStatus.TIMEOUT,
                    details=(
                        "Aristotle formal verification timed out before a proof result was available."
                    ),
                    proof_time_seconds=float(request.timeout_seconds),
                    artifact_status="timeout",
                )
            except Exception as exc:  # pragma: no cover - defensive runtime boundary
                return self._result_set(
                    request,
                    status=ProofStatus.ERROR,
                    details=f"Aristotle formal verification failed: {type(exc).__name__}: {exc}",
                    proof_time_seconds=0.0,
                    artifact_status="error",
                )

        transport = inspect_aristotle_transport(
            hermes_binary=self.hermes_binary,
            hermes_config_path=self.hermes_config_path,
            mcp_server_name=self.mcp_server_name,
        )
        if not transport.aristotle_key_present:
            return self._result_set(
                request,
                status=ProofStatus.UNAVAILABLE,
                details="ARISTOTLE_API_KEY is not configured; formal verification is unavailable in this environment.",
                proof_time_seconds=0.0,
                artifact_status="missing_api_key",
                transport=transport,
            )
        if self._should_use_lifecycle(request):
            return self._run_via_aristotle_cli_lifecycle(request)
        primary_result = self._run_via_hermes_mcp(request, transport)
        fallback_result = self._maybe_run_cli_fallback(request, primary_result)
        return fallback_result or primary_result

    def _should_use_lifecycle(self, request: FormalVerificationRequest) -> bool:
        if not self._cli_transport_available():
            return False
        return request.lifecycle_state is not None or (request.enable_lifecycle and self.prefer_lifecycle)

    def _cli_transport_available(self) -> bool:
        return self.cli_command_executor is not None or shutil.which(self.aristotle_binary) is not None

    def _cli_executor(self, request: FormalVerificationRequest) -> CommandExecutor:
        return self.cli_command_executor or (
            lambda current_command, current_cwd: _default_executor(
                current_command,
                current_cwd,
                self.command_timeout_seconds if self.command_timeout_seconds is not None else request.timeout_seconds,
                command_label="Aristotle CLI command",
            )
        )

    def _run_via_aristotle_cli_lifecycle(
        self,
        request: FormalVerificationRequest,
    ) -> FormalVerificationResultSet:
        executor = self._cli_executor(request)
        now = _isoformat_now()
        attempts: list[dict[str, Any]] = []
        if request.lifecycle_state is None:
            handles, submission_results = self._submit_cli_projects(request, executor, now, attempts)
        else:
            handles = [FormalProofHandle.from_dict(item.to_dict()) for item in request.lifecycle_state.handles]
            submission_results = {
                item.claim: Tier3ClaimResult(
                    claim=item.claim,
                    backend=item.backend,
                    proof_status=item.proof_status,
                    details=item.details,
                    lean_code="",
                    proof_time_seconds=None,
                )
                for item in handles
                if item.proof_status is not ProofStatus.PENDING
            }
        poll_results = self._poll_cli_projects(request, executor, handles, now, attempts)
        results_by_claim = {item.claim: item for item in submission_results.values()}
        results_by_claim.update({item.claim: item for item in poll_results})
        results = [results_by_claim.get(claim.claim, self._pending_result_from_claim(claim)) for claim in request.claims]
        lifecycle = FormalProofLifecycle(
            backend=request.backend,
            transport="aristotle_cli_lifecycle",
            proof_status=self._overall_lifecycle_status(results),
            handles=handles,
            last_transition=now,
            details=self._lifecycle_details(results),
        )
        status = "pending" if lifecycle.proof_status is ProofStatus.PENDING else "completed"
        if lifecycle.proof_status in {ProofStatus.ERROR, ProofStatus.TIMEOUT, ProofStatus.UNAVAILABLE}:
            status = "error"
        return FormalVerificationResultSet(
            results=results,
            transport_artifact={
                "transport": "aristotle_cli_lifecycle",
                "status": status,
                "backend": request.backend,
                "attempts": attempts,
            },
            lifecycle_state=lifecycle,
            pending=lifecycle.proof_status is ProofStatus.PENDING,
        )

    def _submit_cli_projects(
        self,
        request: FormalVerificationRequest,
        executor: CommandExecutor,
        now: str,
        attempts: list[dict[str, Any]],
    ) -> tuple[list[FormalProofHandle], dict[str, Tier3ClaimResult]]:
        handles: list[FormalProofHandle] = []
        submission_results: dict[str, Tier3ClaimResult] = {}
        for claim in request.claims:
            prompt = self._build_cli_prompt(claim)
            command = [self.aristotle_binary, "submit", prompt]
            command_result = executor(command, self.cwd)
            attempt: dict[str, Any] = {
                "phase": "submit",
                "claim": claim.claim,
                "command": list(command),
                "stdout": command_result.stdout,
                "stderr": command_result.stderr,
            }
            if command_result.returncode != 0:
                details = (
                    command_result.stderr.strip()
                    or command_result.stdout.strip()
                    or "Aristotle CLI project submission failed."
                )
                attempt["status"] = "error"
                submission_results[claim.claim] = Tier3ClaimResult(
                    claim=claim.claim,
                    backend=request.backend,
                    proof_status=ProofStatus.ERROR,
                    details=details,
                    lean_code="",
                    proof_time_seconds=0.0,
                )
                attempts.append(attempt)
                continue
            try:
                project_id = _parse_aristotle_cli_project_id(command_result.stdout)
            except Exception as exc:  # pragma: no cover - defensive runtime boundary
                attempt["status"] = "parse_error"
                submission_results[claim.claim] = Tier3ClaimResult(
                    claim=claim.claim,
                    backend=request.backend,
                    proof_status=ProofStatus.ERROR,
                    details=(
                        "Aristotle CLI submission returned an unreadable project id: "
                        f"{type(exc).__name__}: {exc}"
                    ),
                    lean_code="",
                    proof_time_seconds=0.0,
                )
                attempts.append(attempt)
                continue

            handles.append(
                FormalProofHandle(
                    claim=claim.claim,
                    backend=request.backend,
                    project_id=project_id,
                    transport="aristotle_cli_lifecycle",
                    proof_status=ProofStatus.PENDING,
                    submitted_at=now,
                    details=f"Submitted Aristotle project {project_id}.",
                )
            )
            attempt["status"] = "submitted"
            attempt["project_id"] = project_id
            attempts.append(attempt)
        return handles, submission_results

    def _poll_cli_projects(
        self,
        request: FormalVerificationRequest,
        executor: CommandExecutor,
        handles: list[FormalProofHandle],
        now: str,
        attempts: list[dict[str, Any]],
    ) -> list[Tier3ClaimResult]:
        results: list[Tier3ClaimResult] = []
        for handle in handles:
            if handle.proof_status is not ProofStatus.PENDING:
                results.append(
                    Tier3ClaimResult(
                        claim=handle.claim,
                        backend=handle.backend,
                        proof_status=handle.proof_status,
                        details=handle.details,
                        lean_code="",
                        proof_time_seconds=None,
                    )
                )
                continue
            with tempfile.TemporaryDirectory(prefix="deep-gvr-formal-result-") as tmpdir:
                destination = Path(tmpdir) / "result"
                command = [
                    self.aristotle_binary,
                    "result",
                    "--wait",
                    "--destination",
                    str(destination),
                    handle.project_id,
                ]
                command_result = executor(command, self.cwd)
                attempt: dict[str, Any] = {
                    "phase": "result",
                    "claim": handle.claim,
                    "project_id": handle.project_id,
                    "command": list(command),
                    "stdout": command_result.stdout,
                    "stderr": command_result.stderr,
                }
                handle.poll_count += 1
                handle.last_polled_at = now
                if command_result.returncode == 124 or "timed out" in command_result.stderr.lower():
                    handle.proof_status = ProofStatus.PENDING
                    handle.details = (
                        f"Aristotle project {handle.project_id} is still running; resume this session to continue polling."
                    )
                    attempt["status"] = "timeout"
                    results.append(
                        Tier3ClaimResult(
                            claim=handle.claim,
                            backend=handle.backend,
                            proof_status=ProofStatus.PENDING,
                            details=handle.details,
                            lean_code="",
                            proof_time_seconds=None,
                        )
                    )
                    attempts.append(attempt)
                    continue
                if command_result.returncode != 0:
                    handle.proof_status = ProofStatus.ERROR
                    handle.details = (
                        command_result.stderr.strip()
                        or command_result.stdout.strip()
                        or f"Aristotle result retrieval failed for project {handle.project_id}."
                    )
                    attempt["status"] = "error"
                    results.append(
                        Tier3ClaimResult(
                            claim=handle.claim,
                            backend=handle.backend,
                            proof_status=ProofStatus.ERROR,
                            details=handle.details,
                            lean_code="",
                            proof_time_seconds=0.0,
                        )
                    )
                    attempts.append(attempt)
                    continue

                try:
                    summary_text, lean_code = _extract_aristotle_result_artifacts(destination)
                except Exception as exc:  # pragma: no cover - defensive runtime boundary
                    handle.proof_status = ProofStatus.ERROR
                    handle.details = (
                        "Aristotle result retrieval returned an unreadable proof bundle: "
                        f"{type(exc).__name__}: {exc}"
                    )
                    attempt["status"] = "parse_error"
                    results.append(
                        Tier3ClaimResult(
                            claim=handle.claim,
                            backend=handle.backend,
                            proof_status=ProofStatus.ERROR,
                            details=handle.details,
                            lean_code="",
                            proof_time_seconds=0.0,
                        )
                    )
                    attempts.append(attempt)
                    continue

                handle.proof_status = ProofStatus.PROVED
                handle.details = (
                    f"Aristotle completed project {handle.project_id}. "
                    f"{summary_text.strip() or 'A completed proof bundle was downloaded.'}"
                )
                attempt["status"] = "completed"
                results.append(
                    Tier3ClaimResult(
                        claim=handle.claim,
                        backend=handle.backend,
                        proof_status=ProofStatus.PROVED,
                        details=handle.details,
                        lean_code=lean_code,
                        proof_time_seconds=None,
                    )
                )
                attempts.append(attempt)
        return results

    def _overall_lifecycle_status(self, results: list[Tier3ClaimResult]) -> ProofStatus:
        statuses = {item.proof_status for item in results}
        if not statuses:
            return ProofStatus.ERROR
        if ProofStatus.PENDING in statuses:
            return ProofStatus.PENDING
        if statuses <= {ProofStatus.PROVED}:
            return ProofStatus.PROVED
        if statuses <= {ProofStatus.DISPROVED}:
            return ProofStatus.DISPROVED
        if ProofStatus.ERROR in statuses:
            return ProofStatus.ERROR
        if ProofStatus.TIMEOUT in statuses:
            return ProofStatus.TIMEOUT
        if ProofStatus.UNAVAILABLE in statuses:
            return ProofStatus.UNAVAILABLE
        return ProofStatus.ERROR

    def _lifecycle_details(self, results: list[Tier3ClaimResult]) -> str:
        pending = sum(1 for item in results if item.proof_status is ProofStatus.PENDING)
        proved = sum(1 for item in results if item.proof_status is ProofStatus.PROVED)
        errored = sum(1 for item in results if item.proof_status is ProofStatus.ERROR)
        return f"pending={pending} proved={proved} error={errored}"

    def _pending_result_from_claim(self, claim: Tier3ClaimResult) -> Tier3ClaimResult:
        return Tier3ClaimResult(
            claim=claim.claim,
            backend=claim.backend,
            proof_status=ProofStatus.PENDING,
            details="Tier 3 proof submission is in progress.",
            lean_code="",
            proof_time_seconds=None,
        )

    def _resolve_prompt_path(self) -> Path:
        if self.prompt_root.is_absolute():
            return self.prompt_root
        return _repo_root() / self.prompt_root

    def _build_query(
        self,
        request: FormalVerificationRequest,
        *,
        prompt_text: str,
        transport: AristotleTransportStatus,
    ) -> str:
        payload = {
            "session_id": request.session_id,
            "iteration": request.iteration,
            "backend": request.backend,
            "timeout_seconds": request.timeout_seconds,
            "claims": [item.to_dict() for item in request.claims],
        }
        transport_lines = [
            f"- Required MCP server: {transport.mcp_server_name}",
            f"- Configured MCP servers: {', '.join(transport.configured_mcp_servers) or 'none'}",
            "- If Aristotle MCP tools are unavailable, return unavailable results instead of inventing proof success.",
        ]
        return build_formal_query(
            prompt_text=prompt_text,
            payload=payload,
            transport_lines=transport_lines,
            prompt_profile=self.prompt_profile,
        )

    def _normalize_results(
        self,
        request: FormalVerificationRequest,
        raw_results: list[object],
    ) -> list[Tier3ClaimResult]:
        parsed: dict[str, Tier3ClaimResult] = {}
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            payload = dict(item)
            payload["backend"] = request.backend
            model = Tier3ClaimResult.from_dict(payload)
            parsed[model.claim] = model

        results: list[Tier3ClaimResult] = []
        for claim in request.claims:
            if claim.claim in parsed:
                results.append(parsed[claim.claim])
                continue
            results.append(
                Tier3ClaimResult(
                    claim=claim.claim,
                    backend=request.backend,
                    proof_status=ProofStatus.ERROR,
                    details="Aristotle transport did not return a result for this claim.",
                    lean_code="",
                    proof_time_seconds=0.0,
                )
            )
        return results

    def _run_via_hermes_mcp(
        self,
        request: FormalVerificationRequest,
        transport: AristotleTransportStatus,
    ) -> FormalVerificationResultSet:
        if not transport.hermes_available and self.command_executor is None:
            return self._result_set(
                request,
                status=ProofStatus.UNAVAILABLE,
                details="Hermes CLI is not available, so Aristotle formal verification cannot be dispatched.",
                proof_time_seconds=0.0,
                artifact_status="missing_hermes",
                transport=transport,
            )
        if not transport.mcp_server_configured:
            return self._result_set(
                request,
                status=ProofStatus.UNAVAILABLE,
                details=(
                    f"Hermes config {transport.hermes_config_path} does not define mcp_servers.{transport.mcp_server_name}; "
                    "formal verification is unavailable until the Aristotle MCP server is configured."
                ),
                proof_time_seconds=0.0,
                artifact_status="missing_mcp_server",
                transport=transport,
            )

        prompt_path = self._resolve_prompt_path() / "formalizer.md"
        prompt_text = prompt_path.read_text(encoding="utf-8")
        query = self._build_query(request, prompt_text=prompt_text, transport=transport)
        command = [self.hermes_binary, "chat", "-Q", "-q", query]
        if self.provider not in {"", "default", "auto"}:
            command.extend(["--provider", self.provider])
        if self.model not in {"", "configured-by-hermes", "provider-default"}:
            command.extend(["--model", self.model])
        if self.toolsets:
            command.extend(["--toolsets", ",".join(self.toolsets)])
        if self.skills:
            command.extend(["--skills", ",".join(self.skills)])

        executor = self.command_executor or (
            lambda current_command, current_cwd: _default_executor(
                current_command,
                current_cwd,
                self.command_timeout_seconds if self.command_timeout_seconds is not None else request.timeout_seconds,
                command_label="Hermes command",
            )
        )
        command_result = executor(command, self.cwd)
        transport_artifact = {
            "transport": "hermes_mcp",
            "status": "completed",
            "backend": request.backend,
            "mcp_server_name": transport.mcp_server_name,
            "configured_mcp_servers": list(transport.configured_mcp_servers),
            "hermes_config_path": transport.hermes_config_path,
            "prompt_path": str(prompt_path),
            "command": list(command),
            "query": query,
            "response": command_result.stdout if command_result.returncode == 0 else f"{command_result.stdout}\n{command_result.stderr}".strip(),
        }

        if command_result.returncode != 0:
            if command_result.returncode == 124 or "timed out" in command_result.stderr.lower():
                transport_artifact["status"] = "timeout"
                return self._result_set(
                    request,
                    status=ProofStatus.TIMEOUT,
                    details=command_result.stderr.strip() or "Aristotle formal verification timed out.",
                    proof_time_seconds=float(request.timeout_seconds),
                    artifact_status="timeout",
                    transport=transport,
                    transport_artifact=transport_artifact,
                )
            transport_artifact["status"] = "error"
            return self._result_set(
                request,
                status=ProofStatus.ERROR,
                details=(
                    "Aristotle formal verification failed through Hermes CLI: "
                    f"{command_result.stderr.strip() or command_result.stdout.strip() or 'unknown error'}"
                ),
                proof_time_seconds=0.0,
                artifact_status="error",
                transport=transport,
                transport_artifact=transport_artifact,
            )

        try:
            payload = _extract_json_object(command_result.stdout)
            raw_results = payload.get("results", [])
            if not isinstance(raw_results, list):
                raise ValueError("Hermes formal transport did not return a 'results' array.")
            results = self._normalize_results(request, raw_results)
        except Exception as exc:  # pragma: no cover - defensive runtime boundary
            transport_artifact["status"] = "parse_error"
            return self._result_set(
                request,
                status=ProofStatus.ERROR,
                details=f"Aristotle formal verification returned an unreadable payload: {type(exc).__name__}: {exc}",
                proof_time_seconds=0.0,
                artifact_status="parse_error",
                transport=transport,
                transport_artifact=transport_artifact,
            )

        return FormalVerificationResultSet(results=results, transport_artifact=transport_artifact)

    def _maybe_run_cli_fallback(
        self,
        request: FormalVerificationRequest,
        primary_result: FormalVerificationResultSet,
    ) -> FormalVerificationResultSet | None:
        if not self.allow_cli_fallback:
            return None
        if not self._should_try_cli_fallback(primary_result):
            return None
        if shutil.which(self.aristotle_binary) is None and self.cli_command_executor is None:
            return None

        fallback_result = self._run_via_aristotle_cli(request, primary_result.transport_artifact)
        if any(item.proof_status in {ProofStatus.PROVED, ProofStatus.DISPROVED} for item in fallback_result.results):
            return fallback_result

        merged_artifact = dict(primary_result.transport_artifact or {})
        merged_artifact["cli_fallback"] = fallback_result.transport_artifact
        merged_results: list[Tier3ClaimResult] = []
        fallback_by_claim = {item.claim: item for item in fallback_result.results}
        for item in primary_result.results:
            fallback_item = fallback_by_claim.get(item.claim)
            details = item.details
            if fallback_item is not None:
                details = f"{details} CLI fallback also failed: {fallback_item.details}".strip()
            merged_results.append(
                Tier3ClaimResult(
                    claim=item.claim,
                    backend=item.backend,
                    proof_status=item.proof_status,
                    details=details,
                    lean_code=item.lean_code,
                    proof_time_seconds=item.proof_time_seconds,
                )
            )
        return FormalVerificationResultSet(results=merged_results, transport_artifact=merged_artifact)

    def _should_try_cli_fallback(self, result_set: FormalVerificationResultSet) -> bool:
        statuses = {item.proof_status for item in result_set.results}
        if statuses & {ProofStatus.PROVED, ProofStatus.DISPROVED}:
            return False
        artifact_status = (result_set.transport_artifact or {}).get("status")
        return artifact_status in {"missing_hermes", "missing_mcp_server", "error", "parse_error", "timeout"}

    def _run_via_aristotle_cli(
        self,
        request: FormalVerificationRequest,
        primary_transport_artifact: dict[str, Any] | None,
    ) -> FormalVerificationResultSet:
        executor = self.cli_command_executor or (
            lambda current_command, current_cwd: _default_executor(
                current_command,
                current_cwd,
                self.command_timeout_seconds if self.command_timeout_seconds is not None else request.timeout_seconds,
                command_label="Aristotle CLI command",
            )
        )
        attempts: list[dict[str, Any]] = []
        results: list[Tier3ClaimResult] = []
        overall_status = "completed"
        for claim in request.claims:
            prompt = self._build_cli_prompt(claim)
            command = [self.aristotle_binary, "submit", "--wait", prompt]
            command_result = executor(command, self.cwd)
            attempt: dict[str, Any] = {
                "claim": claim.claim,
                "command": list(command),
                "stdout": command_result.stdout,
                "stderr": command_result.stderr,
            }
            if command_result.returncode != 0:
                overall_status = "error"
                details = command_result.stderr.strip() or command_result.stdout.strip() or "Aristotle CLI returned a non-zero exit code."
                attempt["status"] = "error"
                results.append(
                    Tier3ClaimResult(
                        claim=claim.claim,
                        backend=request.backend,
                        proof_status=ProofStatus.ERROR,
                        details=details,
                        lean_code="",
                        proof_time_seconds=0.0,
                    )
                )
                attempts.append(attempt)
                continue
            try:
                project_id, tarball_path = _parse_aristotle_cli_submit_output(command_result.stdout)
                summary_text, lean_code = _extract_aristotle_bundle_artifacts(Path(tarball_path))
                attempt.update(
                    {
                        "status": "completed",
                        "project_id": project_id,
                        "tarball_path": tarball_path,
                    }
                )
                details = (
                    f"Direct Aristotle CLI fallback succeeded for project {project_id}. "
                    f"{summary_text.strip() or 'Aristotle returned a completed proof bundle.'}"
                )
                results.append(
                    Tier3ClaimResult(
                        claim=claim.claim,
                        backend=request.backend,
                        proof_status=ProofStatus.PROVED,
                        details=details,
                        lean_code=lean_code,
                        proof_time_seconds=None,
                    )
                )
            except Exception as exc:  # pragma: no cover - defensive runtime boundary
                overall_status = "error"
                attempt["status"] = "parse_error"
                results.append(
                    Tier3ClaimResult(
                        claim=claim.claim,
                        backend=request.backend,
                        proof_status=ProofStatus.ERROR,
                        details=f"Direct Aristotle CLI fallback returned an unreadable proof bundle: {type(exc).__name__}: {exc}",
                        lean_code="",
                        proof_time_seconds=0.0,
                    )
                )
            attempts.append(attempt)

        return FormalVerificationResultSet(
            results=results,
            transport_artifact={
                "transport": "aristotle_cli_direct",
                "status": overall_status,
                "backend": request.backend,
                "primary_transport": dict(primary_transport_artifact or {}),
                "attempts": attempts,
            },
        )

    def _build_cli_prompt(self, claim: Tier3ClaimResult) -> str:
        details = claim.details.strip() or "Formalize and prove the claim directly."
        return (
            "In Lean 4 with Mathlib, formalize and prove the following claim. "
            "Use a complete theorem with no sorrys. If the full semantic statement is awkward, prove the cleanest theorem that captures the mathematical core of the claim and explain that connection in comments. "
            f"Claim: {claim.claim} Context: {details}"
        )

    def _result_set(
        self,
        request: FormalVerificationRequest,
        *,
        status: ProofStatus,
        details: str,
        proof_time_seconds: float | None,
        artifact_status: str,
        transport: AristotleTransportStatus | None = None,
        transport_artifact: dict[str, Any] | None = None,
    ) -> FormalVerificationResultSet:
        artifact = dict(transport_artifact or {})
        artifact.setdefault("transport", "hermes_mcp" if transport is not None else "injected_executor")
        artifact.setdefault("status", artifact_status)
        artifact.setdefault("backend", request.backend)
        if transport is not None:
            artifact.setdefault("mcp_server_name", transport.mcp_server_name)
            artifact.setdefault("configured_mcp_servers", list(transport.configured_mcp_servers))
            artifact.setdefault("hermes_config_path", transport.hermes_config_path)
        return FormalVerificationResultSet(
            results=[
                Tier3ClaimResult(
                    claim=claim.claim,
                    backend=request.backend,
                    proof_status=status,
                    details=details,
                    lean_code=claim.lean_code,
                    proof_time_seconds=proof_time_seconds,
                )
                for claim in request.claims
            ],
            transport_artifact=artifact,
            pending=status is ProofStatus.PENDING,
        )


class MathCodeFormalVerifier:
    def __init__(
        self,
        executor: Callable[[FormalVerificationRequest], FormalVerificationResultSet | list[Tier3ClaimResult]] | None = None,
        *,
        command_executor: CommandExecutor | None = None,
        mathcode_root: str | Path | None = None,
        run_script: str | Path | None = None,
        prompt_root: str | Path = "prompts",
        cwd: str | Path | None = None,
        command_timeout_seconds: int | None = None,
        prompt_profile: str = DEFAULT_PROMPT_PROFILE,
    ) -> None:
        self.executor = executor
        self.command_executor = command_executor
        self.mathcode_root = mathcode_root
        self.run_script = run_script
        self.prompt_root = Path(prompt_root)
        self.cwd = Path(cwd) if cwd is not None else _repo_root()
        self.command_timeout_seconds = command_timeout_seconds
        self.prompt_profile = prompt_profile

    def __call__(self, request: FormalVerificationRequest) -> FormalVerificationResultSet:
        if request.backend != "mathcode":
            return self._result_set(
                request,
                status=ProofStatus.ERROR,
                details=f"Unsupported formal backend {request.backend!r} for the MathCode runner.",
                proof_time_seconds=0.0,
                artifact_status="unsupported_backend",
            )

        if self.executor is not None:
            try:
                outcome = self.executor(request)
                if isinstance(outcome, FormalVerificationResultSet):
                    return outcome
                return FormalVerificationResultSet(
                    results=list(outcome),
                    pending=any(item.proof_status is ProofStatus.PENDING for item in outcome),
                )
            except TimeoutError:
                return self._result_set(
                    request,
                    status=ProofStatus.TIMEOUT,
                    details="MathCode formal verification timed out before a proof result was available.",
                    proof_time_seconds=float(request.timeout_seconds),
                    artifact_status="timeout",
                )
            except Exception as exc:  # pragma: no cover - defensive runtime boundary
                return self._result_set(
                    request,
                    status=ProofStatus.ERROR,
                    details=f"MathCode formal verification failed: {type(exc).__name__}: {exc}",
                    proof_time_seconds=0.0,
                    artifact_status="error",
                )

        transport = inspect_mathcode_transport(
            mathcode_root=self.mathcode_root,
            run_script=self.run_script,
        )
        unavailable_details = self._transport_unavailable_details(transport)
        if unavailable_details is not None:
            return self._result_set(
                request,
                status=ProofStatus.UNAVAILABLE,
                details=unavailable_details,
                proof_time_seconds=0.0,
                artifact_status="unavailable",
                transport=transport,
            )

        prompt_path = self._resolve_prompt_path() / "formalizer.md"
        prompt_text = prompt_path.read_text(encoding="utf-8")
        query = self._build_query(request, prompt_text=prompt_text, transport=transport)
        command = [
            transport.run_script,
            "-p",
            "--output-format",
            "json",
            "--json-schema",
            json.dumps(self._output_schema(), separators=(",", ":")),
            query,
        ]
        before_formalizations = _snapshot_mathcode_formalizations(Path(transport.mathcode_root))
        executor = self.command_executor or (
            lambda current_command, current_cwd: _default_executor(
                current_command,
                current_cwd,
                self.command_timeout_seconds if self.command_timeout_seconds is not None else request.timeout_seconds,
                command_label="MathCode command",
            )
        )
        command_result = executor(command, Path(transport.mathcode_root))
        generated_file = _find_generated_mathcode_formalization(
            Path(transport.mathcode_root),
            previous_snapshot=before_formalizations,
        )
        transport_artifact: dict[str, Any] = {
            "transport": "mathcode_cli",
            "status": "completed",
            "backend": request.backend,
            "mathcode_root": transport.mathcode_root,
            "run_script": transport.run_script,
            "autolean_exists": transport.autolean_exists,
            "lean_workspace_exists": transport.lean_workspace_exists,
            "prompt_path": str(prompt_path),
            "command": list(command),
            "query": query,
            "response": command_result.stdout if command_result.returncode == 0 else f"{command_result.stdout}\n{command_result.stderr}".strip(),
        }
        if generated_file is not None:
            transport_artifact["generated_lean_file"] = generated_file

        if command_result.returncode != 0:
            if command_result.returncode == 124 or "timed out" in command_result.stderr.lower():
                transport_artifact["status"] = "timeout"
                return self._result_set(
                    request,
                    status=ProofStatus.TIMEOUT,
                    details=command_result.stderr.strip() or "MathCode formal verification timed out.",
                    proof_time_seconds=float(request.timeout_seconds),
                    artifact_status="timeout",
                    transport=transport,
                    transport_artifact=transport_artifact,
                )
            transport_artifact["status"] = "error"
            return self._result_set(
                request,
                status=ProofStatus.ERROR,
                details=(
                    "MathCode formal verification failed through the local CLI: "
                    f"{command_result.stderr.strip() or command_result.stdout.strip() or 'unknown error'}"
                ),
                proof_time_seconds=0.0,
                artifact_status="error",
                transport=transport,
                transport_artifact=transport_artifact,
            )

        try:
            payload = _extract_structured_payload(command_result.stdout)
            raw_results = payload.get("results", [])
            if not isinstance(raw_results, list):
                raise ValueError("MathCode formal transport did not return a 'results' array.")
            results = _normalize_formal_results(
                request,
                raw_results,
                missing_result_detail="MathCode transport did not return a result for this claim.",
            )
        except Exception as exc:  # pragma: no cover - defensive runtime boundary
            transport_artifact["status"] = "parse_error"
            return self._result_set(
                request,
                status=ProofStatus.ERROR,
                details=f"MathCode formal verification returned an unreadable payload: {type(exc).__name__}: {exc}",
                proof_time_seconds=0.0,
                artifact_status="parse_error",
                transport=transport,
                transport_artifact=transport_artifact,
            )

        return FormalVerificationResultSet(results=results, transport_artifact=transport_artifact)

    def _resolve_prompt_path(self) -> Path:
        if self.prompt_root.is_absolute():
            return self.prompt_root
        return _repo_root() / self.prompt_root

    def _build_query(
        self,
        request: FormalVerificationRequest,
        *,
        prompt_text: str,
        transport: MathCodeTransportStatus,
    ) -> str:
        payload = {
            "session_id": request.session_id,
            "iteration": request.iteration,
            "backend": request.backend,
            "timeout_seconds": request.timeout_seconds,
            "claims": [item.to_dict() for item in request.claims],
        }
        transport_lines = [
            "- Selected backend: MathCode local CLI",
            f"- MathCode root: {transport.mathcode_root}",
            f"- AUTOLEAN available: {'yes' if transport.autolean_exists else 'no'}",
            "- Return only structured JSON that matches the supplied JSON schema.",
            "- If MathCode cannot complete the proof attempt, return unavailable or error rather than inventing proof success.",
        ]
        return build_formal_query(
            prompt_text=prompt_text,
            payload=payload,
            transport_lines=transport_lines,
            prompt_profile=self.prompt_profile,
        )

    def _output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["results"],
            "additionalProperties": False,
            "properties": {
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["claim", "proof_status", "details", "lean_code"],
                        "additionalProperties": False,
                        "properties": {
                            "claim": {"type": "string"},
                            "proof_status": {
                                "type": "string",
                                "enum": [
                                    ProofStatus.REQUESTED.value,
                                    ProofStatus.PENDING.value,
                                    ProofStatus.PROVED.value,
                                    ProofStatus.DISPROVED.value,
                                    ProofStatus.TIMEOUT.value,
                                    ProofStatus.ERROR.value,
                                    ProofStatus.UNAVAILABLE.value,
                                ],
                            },
                            "details": {"type": "string"},
                            "lean_code": {"type": "string"},
                            "proof_time_seconds": {"type": ["number", "null"]},
                        },
                    },
                }
            },
        }

    def _transport_unavailable_details(self, transport: MathCodeTransportStatus) -> str | None:
        if not transport.mathcode_root_exists:
            return (
                f"MathCode root {transport.mathcode_root} does not exist; local MathCode formal verification is unavailable."
            )
        if not transport.run_script_exists:
            return (
                f"MathCode run script {transport.run_script} does not exist; local MathCode formal verification is unavailable."
            )
        if not transport.run_script_executable:
            return (
                f"MathCode run script {transport.run_script} is not executable; local MathCode formal verification is unavailable."
            )
        if not transport.autolean_exists:
            return (
                f"MathCode root {transport.mathcode_root} is missing AUTOLEAN/; local MathCode formal verification is unavailable."
            )
        if not transport.lean_workspace_exists:
            return (
                f"MathCode root {transport.mathcode_root} is missing lean-workspace/; local MathCode formal verification is unavailable."
            )
        return None

    def _result_set(
        self,
        request: FormalVerificationRequest,
        *,
        status: ProofStatus,
        details: str,
        proof_time_seconds: float | None,
        artifact_status: str,
        transport: MathCodeTransportStatus | None = None,
        transport_artifact: dict[str, Any] | None = None,
    ) -> FormalVerificationResultSet:
        artifact = dict(transport_artifact or {})
        artifact.setdefault("transport", "mathcode_cli" if transport is not None else "injected_executor")
        artifact.setdefault("status", artifact_status)
        artifact.setdefault("backend", request.backend)
        if transport is not None:
            artifact.setdefault("mathcode_root", transport.mathcode_root)
            artifact.setdefault("run_script", transport.run_script)
            artifact.setdefault("autolean_exists", transport.autolean_exists)
            artifact.setdefault("lean_workspace_exists", transport.lean_workspace_exists)
        return FormalVerificationResultSet(
            results=[
                Tier3ClaimResult(
                    claim=claim.claim,
                    backend=request.backend,
                    proof_status=status,
                    details=details,
                    lean_code=claim.lean_code,
                    proof_time_seconds=proof_time_seconds,
                )
                for claim in request.claims
            ],
            transport_artifact=artifact,
            pending=status is ProofStatus.PENDING,
        )


def build_formal_verifier(
    tier3_config: Tier3Config,
    *,
    executor: Callable[[FormalVerificationRequest], FormalVerificationResultSet | list[Tier3ClaimResult]] | None = None,
    command_executor: CommandExecutor | None = None,
    cli_command_executor: CommandExecutor | None = None,
    hermes_binary: str = "hermes",
    aristotle_binary: str = "aristotle",
    hermes_config_path: str | Path | None = None,
    prompt_root: str | Path = "prompts",
    cwd: str | Path | None = None,
    command_timeout_seconds: int | None = None,
    provider: str = "default",
    model: str = "",
    toolsets: list[str] | None = None,
    skills: list[str] | None = None,
    prompt_profile: str = DEFAULT_PROMPT_PROFILE,
) -> FormalVerifier:
    if tier3_config.backend == "aristotle":
        return AristotleFormalVerifier(
            executor=executor,
            command_executor=command_executor,
            cli_command_executor=cli_command_executor,
            hermes_binary=hermes_binary,
            aristotle_binary=aristotle_binary,
            hermes_config_path=hermes_config_path,
            prompt_root=prompt_root,
            cwd=cwd,
            command_timeout_seconds=command_timeout_seconds,
            provider=provider,
            model=model,
            toolsets=toolsets,
            skills=skills,
            prompt_profile=prompt_profile,
            prefer_lifecycle=True,
        )
    if tier3_config.backend == "mathcode":
        mathcode_config = tier3_config.mathcode if isinstance(tier3_config.mathcode, MathCodeConfig) else MathCodeConfig()
        return MathCodeFormalVerifier(
            executor=executor,
            command_executor=command_executor,
            mathcode_root=mathcode_config.root,
            run_script=mathcode_config.run_script,
            prompt_root=prompt_root,
            cwd=cwd,
            command_timeout_seconds=command_timeout_seconds,
            prompt_profile=prompt_profile,
        )
    raise ValueError(f"Unsupported formal backend {tier3_config.backend!r}.")


def _default_executor(
    command: list[str],
    cwd: Path,
    timeout_seconds: int | None = None,
    *,
    command_label: str = "Command",
) -> CommandExecutionResult:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        return CommandExecutionResult(returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr)
    except subprocess.TimeoutExpired:
        timeout_text = timeout_seconds if timeout_seconds is not None else "the configured"
        return CommandExecutionResult(
            returncode=124,
            stdout="",
            stderr=f"{command_label} timed out after {timeout_text} seconds.",
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


def _extract_structured_payload(text: str) -> dict[str, Any]:
    payload = _extract_json_object(text)
    structured_output = payload.get("structured_output")
    if isinstance(structured_output, dict):
        return structured_output
    return payload


def _normalize_formal_results(
    request: FormalVerificationRequest,
    raw_results: list[object],
    *,
    missing_result_detail: str,
) -> list[Tier3ClaimResult]:
    parsed: dict[str, Tier3ClaimResult] = {}
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        payload = dict(item)
        payload["backend"] = request.backend
        model = Tier3ClaimResult.from_dict(payload)
        parsed[model.claim] = model

    results: list[Tier3ClaimResult] = []
    for claim in request.claims:
        if claim.claim in parsed:
            results.append(parsed[claim.claim])
            continue
        results.append(
            Tier3ClaimResult(
                claim=claim.claim,
                backend=request.backend,
                proof_status=ProofStatus.ERROR,
                details=missing_result_detail,
                lean_code="",
                proof_time_seconds=0.0,
            )
        )
    return results


def _snapshot_mathcode_formalizations(mathcode_root: Path) -> dict[Path, tuple[int, int]]:
    formalizations_root = mathcode_root / "LeanFormalizations"
    if not formalizations_root.exists():
        return {}
    snapshot: dict[Path, tuple[int, int]] = {}
    for path in formalizations_root.rglob("*.lean"):
        if not path.is_file():
            continue
        stat = path.stat()
        snapshot[path] = (stat.st_mtime_ns, stat.st_size)
    return snapshot


def _find_generated_mathcode_formalization(
    mathcode_root: Path,
    *,
    previous_snapshot: dict[Path, tuple[int, int]] | None = None,
) -> dict[str, Any] | None:
    formalizations_root = mathcode_root / "LeanFormalizations"
    if not formalizations_root.exists():
        return None
    previous = previous_snapshot or {}
    candidates = [path for path in formalizations_root.rglob("*.lean") if path.is_file()]
    if not candidates:
        return None
    changed_candidates: list[tuple[Path, os.stat_result]] = []
    for path in candidates:
        stat = path.stat()
        previous_state = previous.get(path)
        current_state = (stat.st_mtime_ns, stat.st_size)
        if previous_state is None or previous_state != current_state:
            changed_candidates.append((path, stat))
    if not changed_candidates:
        return None
    latest, latest_stat = max(changed_candidates, key=lambda item: (item[1].st_mtime_ns, str(item[0])))
    change = "created" if latest not in previous else "modified"
    return {
        "path": str(latest),
        "relative_path": str(latest.relative_to(mathcode_root)),
        "size_bytes": latest_stat.st_size,
        "change": change,
    }


def _parse_aristotle_cli_submit_output(text: str) -> tuple[str, str]:
    project_match = _ARISTOTLE_PROJECT_ID_RE.search(text)
    tarball_match = _ARISTOTLE_TARBALL_RE.search(text)
    if project_match is None:
        raise ValueError(f"Could not parse Aristotle project id from CLI output: {text[:200]!r}")
    if tarball_match is None:
        raise ValueError(f"Could not parse Aristotle tarball path from CLI output: {text[:200]!r}")
    return project_match.group(1), tarball_match.group(1)


def _parse_aristotle_cli_project_id(text: str) -> str:
    project_match = _ARISTOTLE_PROJECT_ID_RE.search(text)
    if project_match is None:
        raise ValueError(f"Could not parse Aristotle project id from CLI output: {text[:200]!r}")
    return project_match.group(1)


def _extract_aristotle_bundle_artifacts(bundle_path: Path) -> tuple[str, str]:
    if not bundle_path.exists():
        raise FileNotFoundError(bundle_path)
    summary_text = ""
    lean_code = ""
    with tarfile.open(bundle_path, "r:gz") as archive:
        members = archive.getmembers()
        summary_member = next((item for item in members if item.name.endswith(".md") and "/ARISTOTLE_SUMMARY_" in item.name), None)
        lean_member = next((item for item in members if item.name.endswith(".lean") and not item.name.endswith("/Main.lean")), None)
        if summary_member is not None:
            extracted = archive.extractfile(summary_member)
            if extracted is not None:
                summary_text = extracted.read().decode("utf-8")
        if lean_member is not None:
            extracted = archive.extractfile(lean_member)
            if extracted is not None:
                lean_code = extracted.read().decode("utf-8")
    if not summary_text and not lean_code:
        raise ValueError(f"Aristotle bundle {bundle_path} did not contain a summary or Lean proof file.")
    return summary_text, lean_code


def _extract_aristotle_result_artifacts(result_path: Path) -> tuple[str, str]:
    if result_path.is_file():
        return _extract_aristotle_bundle_artifacts(result_path)
    if not result_path.exists():
        raise FileNotFoundError(result_path)
    summary_text = ""
    lean_code = ""
    summary_match = next(result_path.rglob("*ARISTOTLE_SUMMARY_*.md"), None)
    lean_match = next(
        (
            path
            for path in result_path.rglob("*.lean")
            if path.name != "Main.lean"
        ),
        None,
    )
    if summary_match is not None:
        summary_text = summary_match.read_text(encoding="utf-8")
    if lean_match is not None:
        lean_code = lean_match.read_text(encoding="utf-8")
    if not summary_text and not lean_code:
        raise ValueError(f"Aristotle result path {result_path} did not contain a summary or Lean proof file.")
    return summary_text, lean_code
