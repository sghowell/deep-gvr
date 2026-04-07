from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

import yaml

from .contracts import ProofStatus, Tier3ClaimResult
from .prompt_profiles import DEFAULT_PROMPT_PROFILE, build_formal_query


@dataclass(slots=True)
class FormalVerificationRequest:
    session_id: str
    iteration: int
    claims: list[Tier3ClaimResult]
    backend: str
    timeout_seconds: int


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


class FormalVerifier(Protocol):
    def __call__(self, request: FormalVerificationRequest) -> FormalVerificationResultSet | list[Tier3ClaimResult]:
        ...


_ARISTOTLE_PROJECT_ID_RE = re.compile(r"Project created:\s*([0-9a-fA-F-]+)")
_ARISTOTLE_TARBALL_RE = re.compile(r"Project saved to\s+([^\s]+\.tar\.gz)")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_hermes_config_path() -> Path:
    return Path("~/.hermes/config.yaml").expanduser()


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
                return FormalVerificationResultSet(results=list(outcome))
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
        primary_result = self._run_via_hermes_mcp(request, transport)
        fallback_result = self._maybe_run_cli_fallback(request, primary_result)
        return fallback_result or primary_result

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
        )


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


def _parse_aristotle_cli_submit_output(text: str) -> tuple[str, str]:
    project_match = _ARISTOTLE_PROJECT_ID_RE.search(text)
    tarball_match = _ARISTOTLE_TARBALL_RE.search(text)
    if project_match is None:
        raise ValueError(f"Could not parse Aristotle project id from CLI output: {text[:200]!r}")
    if tarball_match is None:
        raise ValueError(f"Could not parse Aristotle tarball path from CLI output: {text[:200]!r}")
    return project_match.group(1), tarball_match.group(1)


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
