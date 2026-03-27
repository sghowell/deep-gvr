from __future__ import annotations

import json
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable, Protocol

from .contracts import (
    AnalyticalCheck,
    AnalyticalStatus,
    Backend,
    CapabilityProbeResult,
    CandidateSolution,
    DeepGvrConfig,
    ProbeStatus,
    ProofStatus,
    SimAnalysis,
    SimResults,
    Tier1Report,
    Tier2Report,
    Tier3ClaimResult,
    VerificationReport,
    VerificationVerdict,
)
from .formal import AristotleFormalVerifier, FormalVerificationRequest, FormalVerifier
from .live_runtime import resolve_live_role_timeout_seconds, resolve_live_role_toolsets
from .prompt_profiles import DEFAULT_PROMPT_PROFILE, build_live_role_query
from .probes import probe_model_routing
from .runtime_config import load_runtime_config
from .tier1 import (
    GenerationRequest,
    RevisionRequest,
    SessionPaths,
    SessionStore,
    SimulationRequest,
    Tier1LoopRunner,
    VerificationRequest,
)

_DETERMINISTIC_TIMESTAMP = "2026-03-26T00:00:00Z"
_DETERMINISTIC_RUN_ID = "baseline"
_ENABLED_TIERS = [1, 2, 3]
_BASELINE_REPORT_PATH = Path("eval/results/baseline_results.json")


def _serialize(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {key: _serialize(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    return value


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _isoformat(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


@dataclass(slots=True)
class BenchmarkCase:
    id: str
    category: str
    prompt: str
    scenario: str
    expected_verdict: VerificationVerdict
    expected_tiers: list[int]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BenchmarkCase":
        return cls(
            id=data["id"],
            category=data["category"],
            prompt=data["prompt"],
            scenario=data["scenario"],
            expected_verdict=VerificationVerdict(data["expected_verdict"]),
            expected_tiers=[int(item) for item in data["expected_tiers"]],
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class BenchmarkCaseResult:
    mode: str
    id: str
    category: str
    scenario: str
    expected_verdict: VerificationVerdict
    actual_verdict: VerificationVerdict
    expected_tiers: list[int]
    actual_tiers: list[int]
    iterations: int
    passed: bool
    routing_mode: str
    provider: str
    model_used: str
    session_id: str
    artifacts: list[str]
    runtime_seconds: float
    error: str | None = None
    notes: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BenchmarkCaseResult":
        return cls(
            mode=data["mode"],
            id=data["id"],
            category=data["category"],
            scenario=data["scenario"],
            expected_verdict=VerificationVerdict(data["expected_verdict"]),
            actual_verdict=VerificationVerdict(data["actual_verdict"]),
            expected_tiers=[int(item) for item in data["expected_tiers"]],
            actual_tiers=[int(item) for item in data["actual_tiers"]],
            iterations=int(data["iterations"]),
            passed=bool(data["passed"]),
            routing_mode=data["routing_mode"],
            provider=data["provider"],
            model_used=data["model_used"],
            session_id=data["session_id"],
            artifacts=list(data.get("artifacts", [])),
            runtime_seconds=float(data.get("runtime_seconds", 0.0)),
            error=data.get("error"),
            notes=list(data.get("notes", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class BenchmarkSummary:
    total_cases: int
    passed_cases: int
    failed_cases: int
    verdict_match_rate: float
    true_positive_rate: float
    true_negative_rate: float
    false_positive_rate: float
    tier_accuracy: float
    iteration_efficiency: float
    failure_admission_rate: float
    meets_false_positive_bar: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BenchmarkSummary":
        return cls(
            total_cases=int(data["total_cases"]),
            passed_cases=int(data["passed_cases"]),
            failed_cases=int(data["failed_cases"]),
            verdict_match_rate=float(data["verdict_match_rate"]),
            true_positive_rate=float(data["true_positive_rate"]),
            true_negative_rate=float(data["true_negative_rate"]),
            false_positive_rate=float(data["false_positive_rate"]),
            tier_accuracy=float(data["tier_accuracy"]),
            iteration_efficiency=float(data["iteration_efficiency"]),
            failure_admission_rate=float(data["failure_admission_rate"]),
            meets_false_positive_bar=bool(data["meets_false_positive_bar"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class BenchmarkReport:
    mode: str
    run_id: str
    runner_backend: str
    output_root: str
    enabled_tiers: list[int]
    generated_at: str
    suite_path: str
    routing_probe_status: ProbeStatus
    cases: list[BenchmarkCaseResult]
    summary: BenchmarkSummary

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BenchmarkReport":
        return cls(
            mode=data["mode"],
            run_id=data["run_id"],
            runner_backend=data["runner_backend"],
            output_root=data["output_root"],
            enabled_tiers=[int(item) for item in data["enabled_tiers"]],
            generated_at=data["generated_at"],
            suite_path=data["suite_path"],
            routing_probe_status=ProbeStatus(data["routing_probe_status"]),
            cases=[BenchmarkCaseResult.from_dict(item) for item in data["cases"]],
            summary=BenchmarkSummary.from_dict(data["summary"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


class GeneratorFn(Protocol):
    def __call__(self, request: GenerationRequest) -> CandidateSolution:
        ...


class VerifierFn(Protocol):
    def __call__(self, request: VerificationRequest) -> VerificationReport:
        ...


class ReviserFn(Protocol):
    def __call__(self, request: RevisionRequest) -> CandidateSolution:
        ...


@dataclass(slots=True)
class FixtureAgents:
    generator: GeneratorFn
    verifier: VerifierFn
    reviser: ReviserFn
    simulator: Any | None = None
    formal_verifier: FormalVerifier | None = None


@dataclass(slots=True)
class LiveEvalConfig:
    hermes_binary: str = "hermes"
    prompt_root: str | Path = "prompts"
    prompt_profile: str = DEFAULT_PROMPT_PROFILE
    command_timeout_seconds: int = 120
    toolsets: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CommandExecutionResult:
    returncode: int
    stdout: str
    stderr: str


class CommandExecutor(Protocol):
    def __call__(self, command: list[str], cwd: Path) -> CommandExecutionResult:
        ...


@dataclass(slots=True)
class LiveRoleTranscript:
    role: str
    provider: str
    model: str
    command: list[str]
    prompt_path: str
    query: str
    response: str

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


class HermesPromptRoleRunner:
    def __init__(
        self,
        config: LiveEvalConfig,
        *,
        prompt_root: Path,
        executor: CommandExecutor | None = None,
        cwd: Path | None = None,
    ) -> None:
        self.config = config
        self.prompt_root = prompt_root
        self.executor = executor
        self.cwd = cwd or Path.cwd()
        self.transcripts: list[LiveRoleTranscript] = []

    def generator(self, request: GenerationRequest) -> CandidateSolution:
        payload = {
            "session_id": request.session_id,
            "problem": request.problem,
            "domain": request.domain,
            "literature_context": request.literature_context,
            "prior_verdicts": [item.to_dict() for item in request.prior_verdicts],
        }
        response = self._run_role(
            role="generator",
            prompt_file="generator.md",
            route_provider=request.route.provider,
            route_model=request.route.model,
            response_contract={
                "hypothesis": "string",
                "approach": "string",
                "technical_details": ["string"],
                "expected_results": ["string"],
                "assumptions": ["string"],
                "limitations": ["string"],
                "references": ["string"],
                "revision_notes": ["string"],
            },
            payload=payload,
            route_notes=request.route.notes,
            route_temperature=request.route.temperature,
        )
        return CandidateSolution.from_dict(_extract_json_object(response))

    def verifier(self, request: VerificationRequest) -> VerificationReport:
        payload = {
            "session_id": request.session_id,
            "iteration": request.iteration,
            "candidate": request.candidate.to_dict(),
            "simulation_results": request.simulation_results.to_dict() if request.simulation_results else None,
            "formal_results": [item.to_dict() for item in request.formal_results] if request.formal_results else None,
        }
        response = self._run_role(
            role="verifier",
            prompt_file="verifier.md",
            route_provider=request.route.provider,
            route_model=request.route.model,
            response_contract={
                "verdict": "VERIFIED | FLAWS_FOUND | CANNOT_VERIFY",
                "tier1": {
                    "checks": [{"check": "string", "status": "pass|fail|uncertain", "detail": "string"}],
                    "overall": "VERIFIED | FLAWS_FOUND | CANNOT_VERIFY",
                    "flaws": ["string"],
                    "caveats": ["string"],
                },
                "tier2": {
                    "simulation_requested": "boolean",
                    "reason": "string",
                    "simulation_spec": "object | null",
                    "results": "object | null",
                    "interpretation": "string | null",
                },
                "tier3": [
                    {
                        "claim": "string",
                        "backend": "string",
                        "proof_status": "requested|proved|disproved|timeout|error|unavailable",
                        "details": "string",
                        "lean_code": "string",
                        "proof_time_seconds": "number | null",
                    }
                ],
                "flaws": ["string"],
                "caveats": ["string"],
                "cannot_verify_reason": "string | null",
            },
            payload=payload,
            route_notes=request.route.notes,
            route_temperature=request.route.temperature,
        )
        return VerificationReport.from_dict(_extract_json_object(response))

    def reviser(self, request: RevisionRequest) -> CandidateSolution:
        payload = {
            "session_id": request.session_id,
            "iteration": request.iteration,
            "candidate": request.candidate.to_dict(),
            "verification_report": request.verification_report.to_dict(),
        }
        response = self._run_role(
            role="reviser",
            prompt_file="reviser.md",
            route_provider=request.route.provider,
            route_model=request.route.model,
            response_contract={
                "hypothesis": "string",
                "approach": "string",
                "technical_details": ["string"],
                "expected_results": ["string"],
                "assumptions": ["string"],
                "limitations": ["string"],
                "references": ["string"],
                "revision_notes": ["string"],
            },
            payload=payload,
            route_notes=request.route.notes,
            route_temperature=request.route.temperature,
        )
        return CandidateSolution.from_dict(_extract_json_object(response))

    def _run_role(
        self,
        *,
        role: str,
        prompt_file: str,
        route_provider: str,
        route_model: str,
        response_contract: dict[str, Any],
        payload: dict[str, Any],
        route_notes: list[str],
        route_temperature: float | None,
    ) -> str:
        prompt_path = self.prompt_root / prompt_file
        prompt_text = prompt_path.read_text(encoding="utf-8")
        query = self._build_query(
            role=role,
            prompt_text=prompt_text,
            payload=payload,
            response_contract=response_contract,
            route_notes=route_notes,
            route_temperature=route_temperature,
        )
        command = [self.config.hermes_binary, "chat", "-Q", "-q", query]
        if route_provider not in {"", "default", "adapter"}:
            command.extend(["--provider", route_provider])
        if route_model not in {"", "configured-by-hermes", "provider-default"}:
            command.extend(["--model", route_model])
        role_toolsets = resolve_live_role_toolsets(role, self.config.toolsets)
        if role_toolsets:
            command.extend(["--toolsets", ",".join(role_toolsets)])
        if self.config.skills:
            command.extend(["--skills", ",".join(self.config.skills)])

        if self.executor is not None:
            result = self.executor(command, self.cwd)
        else:
            result = _default_executor(
                command,
                self.cwd,
                resolve_live_role_timeout_seconds(role, self.config.command_timeout_seconds),
            )
        transcript = LiveRoleTranscript(
            role=role,
            provider=route_provider,
            model=route_model,
            command=list(command),
            prompt_path=_display_path(prompt_path),
            query=query,
            response=result.stdout if result.returncode == 0 else f"{result.stdout}\n{result.stderr}".strip(),
        )
        self.transcripts.append(transcript)
        if result.returncode != 0:
            raise RuntimeError(
                f"Hermes role {role!r} failed with exit code {result.returncode}: {result.stderr.strip() or result.stdout.strip()}"
            )
        return result.stdout

    def _build_query(
        self,
        *,
        role: str,
        prompt_text: str,
        payload: dict[str, Any],
        response_contract: dict[str, Any],
        route_notes: list[str],
        route_temperature: float | None,
    ) -> str:
        return build_live_role_query(
            role=role,
            prompt_text=prompt_text,
            payload=payload,
            response_contract=response_contract,
            route_notes=route_notes,
            route_temperature=route_temperature,
            prompt_profile=self.config.prompt_profile,
        )


def load_benchmark_suite(
    path: str | Path,
    *,
    case_ids: list[str] | tuple[str, ...] = (),
    max_cases: int | None = None,
) -> list[BenchmarkCase]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = [BenchmarkCase.from_dict(item) for item in payload]
    if case_ids:
        allowed = set(case_ids)
        cases = [item for item in cases if item.id in allowed]
    if max_cases is not None:
        cases = cases[:max_cases]
    return cases


def run_benchmark_suite(
    suite_path: str | Path,
    *,
    routing_probe: CapabilityProbeResult | None = None,
    mode: str = "deterministic",
    config_path: str | Path | None = None,
    output_root: str | Path | None = None,
    run_id: str | None = None,
    case_ids: list[str] | tuple[str, ...] = (),
    max_cases: int | None = None,
    live_config: LiveEvalConfig | None = None,
    executor: CommandExecutor | None = None,
    clock: Callable[[], datetime] | None = None,
) -> BenchmarkReport:
    suite_file = Path(suite_path)
    benchmark_cases = load_benchmark_suite(suite_file, case_ids=case_ids, max_cases=max_cases)
    if not benchmark_cases:
        raise ValueError(f"No benchmark cases selected from {suite_file}.")
    probe = routing_probe or probe_model_routing()
    clock = clock or _utc_now
    now = clock()

    if mode == "deterministic":
        resolved_run_id = run_id or _DETERMINISTIC_RUN_ID
        resolved_output_root = Path(output_root) if output_root is not None else Path("eval/results")
        results = _run_deterministic_suite(benchmark_cases, probe)
        generated_at = _DETERMINISTIC_TIMESTAMP
        runner_backend = "fixture"
    elif mode == "live":
        resolved_run_id = run_id or now.strftime("%Y%m%dT%H%M%SZ")
        resolved_output_root = (
            Path(output_root) if output_root is not None else Path("eval/results/live") / resolved_run_id
        )
        results = _run_live_suite(
            benchmark_cases,
            routing_probe=probe,
            base_config=load_runtime_config(config_path) if config_path is not None else DeepGvrConfig(),
            output_root=resolved_output_root,
            run_id=resolved_run_id,
            live_config=live_config or LiveEvalConfig(),
            executor=executor,
        )
        generated_at = _isoformat(now)
        runner_backend = "hermes_chat"
    else:
        raise ValueError(f"Unsupported benchmark mode {mode!r}.")

    return BenchmarkReport(
        mode=mode,
        run_id=resolved_run_id,
        runner_backend=runner_backend,
        output_root=_display_path(resolved_output_root),
        enabled_tiers=list(_ENABLED_TIERS),
        generated_at=generated_at,
        suite_path=_display_path(suite_file),
        routing_probe_status=probe.status,
        cases=results,
        summary=_summarize_results(results),
    )

def write_benchmark_report(
    report: BenchmarkReport,
    path: str | Path,
    *,
    allow_baseline_overwrite: bool = False,
) -> None:
    output_path = Path(path)
    if report.mode == "live" and not allow_baseline_overwrite and _is_baseline_report_path(output_path):
        raise ValueError(
            "Live benchmark results must not overwrite eval/results/baseline_results.json without explicit approval."
        )
    _write_benchmark_report(report, output_path)


def _write_benchmark_report(report: BenchmarkReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")


def benchmark_routing_probe(status: ProbeStatus) -> CapabilityProbeResult:
    return CapabilityProbeResult(
        name="per_subagent_model_routing",
        status=status,
        summary="Benchmark routing probe override.",
        preferred_outcome="Route generator and verifier to distinct providers or models.",
        fallback="Use prompt separation plus temperature decorrelation and record the limitation.",
        details={"source": "benchmark_fixture"},
    )


def _run_deterministic_suite(
    benchmark_cases: list[BenchmarkCase],
    routing_probe: CapabilityProbeResult,
) -> list[BenchmarkCaseResult]:
    with TemporaryDirectory() as tmpdir:
        evidence_root = Path(tmpdir) / "sessions"
        return [
            _run_fixture_case(case, evidence_root=evidence_root, routing_probe=routing_probe)
            for case in benchmark_cases
        ]


def _run_live_suite(
    benchmark_cases: list[BenchmarkCase],
    *,
    routing_probe: CapabilityProbeResult,
    base_config: DeepGvrConfig,
    output_root: Path,
    run_id: str,
    live_config: LiveEvalConfig,
    executor: CommandExecutor | None,
) -> list[BenchmarkCaseResult]:
    output_root.mkdir(parents=True, exist_ok=True)
    results: list[BenchmarkCaseResult] = []
    for case in benchmark_cases:
        results.append(
            _run_live_case(
                case,
                routing_probe=routing_probe,
                base_config=base_config,
                output_root=output_root,
                run_id=run_id,
                live_config=live_config,
                executor=executor,
            )
        )
    return results


def _run_fixture_case(
    case: BenchmarkCase,
    *,
    evidence_root: Path,
    routing_probe: CapabilityProbeResult,
) -> BenchmarkCaseResult:
    config = _benchmark_config(str(evidence_root / case.id))
    session_store = SessionStore(config.evidence.directory)
    tier_runner = Tier1LoopRunner(config, session_store=session_store, routing_probe=routing_probe)
    agents = _fixture_agents(case)
    result = tier_runner.run(
        problem=case.prompt,
        generator=agents.generator,
        verifier=agents.verifier,
        reviser=agents.reviser,
        simulator=agents.simulator,
        formal_verifier=agents.formal_verifier,
        session_id=f"eval_{case.id}",
    )
    evidence = session_store.read_evidence(result.session_id)
    verify_record = next(record for record in reversed(evidence) if record.phase == "verify")
    notes: list[str] = []
    if result.final_report.verdict is not case.expected_verdict:
        notes.append(
            f"Expected verdict {case.expected_verdict.value}, got {result.final_report.verdict.value}."
        )
    if verify_record.tiers_applied != case.expected_tiers:
        notes.append(f"Expected tiers {case.expected_tiers}, got {verify_record.tiers_applied}.")
    return BenchmarkCaseResult(
        mode="deterministic",
        id=case.id,
        category=case.category,
        scenario=case.scenario,
        expected_verdict=case.expected_verdict,
        actual_verdict=result.final_report.verdict,
        expected_tiers=list(case.expected_tiers),
        actual_tiers=list(verify_record.tiers_applied),
        iterations=len(result.checkpoint.verdict_history),
        passed=not notes,
        routing_mode=verify_record.routing_mode.value,
        provider=verify_record.provider,
        model_used=verify_record.model_used,
        session_id=result.session_id,
        artifacts=[],
        runtime_seconds=0.0,
        error=None,
        notes=notes,
    )


def _run_live_case(
    case: BenchmarkCase,
    *,
    routing_probe: CapabilityProbeResult,
    base_config: DeepGvrConfig,
    output_root: Path,
    run_id: str,
    live_config: LiveEvalConfig,
    executor: CommandExecutor | None,
) -> BenchmarkCaseResult:
    started = time.perf_counter()
    prompt_root = Path(live_config.prompt_root)
    if not prompt_root.is_absolute():
        prompt_root = _repo_root() / prompt_root
    case_root = output_root / "cases" / case.id
    sessions_root = output_root / "sessions"
    case_root.mkdir(parents=True, exist_ok=True)
    config = _benchmark_config(str(sessions_root), base_config=base_config)
    session_store = SessionStore(config.evidence.directory)
    tier_runner = Tier1LoopRunner(config, session_store=session_store, routing_probe=routing_probe)
    live_runner = HermesPromptRoleRunner(
        live_config,
        prompt_root=prompt_root,
        executor=executor,
        cwd=_repo_root(),
    )
    session_id = f"{run_id}_{case.id}"
    route_provider = tier_runner.routing_plan.verifier.provider
    route_model = tier_runner.routing_plan.verifier.model
    notes: list[str] = []
    error: str | None = None
    actual_verdict = VerificationVerdict.CANNOT_VERIFY
    actual_tiers: list[int] = []
    iterations = 0
    artifacts: list[str] = []
    try:
        result = tier_runner.run(
            problem=case.prompt,
            generator=live_runner.generator,
            verifier=live_runner.verifier,
            reviser=live_runner.reviser,
            simulator=None,
            formal_verifier=AristotleFormalVerifier(
                command_executor=executor,
                hermes_binary=live_config.hermes_binary,
                hermes_config_path=Path("~/.hermes/config.yaml").expanduser(),
                prompt_root=prompt_root,
                cwd=_repo_root(),
                prompt_profile=live_config.prompt_profile,
                provider=config.models.orchestrator.provider,
                model=config.models.orchestrator.model,
                toolsets=list(live_config.toolsets),
                skills=list(live_config.skills),
            ),
            session_id=session_id,
        )
        evidence = session_store.read_evidence(result.session_id)
        verify_record = next(record for record in reversed(evidence) if record.phase == "verify")
        actual_verdict = result.final_report.verdict
        actual_tiers = list(verify_record.tiers_applied)
        iterations = len(result.checkpoint.verdict_history)
        route_provider = verify_record.provider
        route_model = verify_record.model_used
        artifacts = _persist_live_case_artifacts(
            case_root=case_root,
            result=result,
            session_store=session_store,
            transcripts=live_runner.transcripts,
        )
        if result.final_report.verdict is not case.expected_verdict:
            notes.append(
                f"Expected verdict {case.expected_verdict.value}, got {result.final_report.verdict.value}."
            )
        if verify_record.tiers_applied != case.expected_tiers:
            notes.append(f"Expected tiers {case.expected_tiers}, got {verify_record.tiers_applied}.")
        if verify_record.routing_temperature is not None:
            notes.append("Hermes CLI does not expose temperature overrides; prompt separation only was applied.")
        routing_mode = verify_record.routing_mode.value
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        notes.append(f"Live benchmark execution failed: {error}")
        routing_mode = tier_runner.routing_plan.verifier.routing_mode.value
        transcript_path = case_root / "role_transcripts.json"
        _write_json(transcript_path, {"calls": [item.to_dict() for item in live_runner.transcripts]})
        _write_json(
            case_root / "live_error.json",
            {"case_id": case.id, "error": error, "notes": notes},
        )
        artifacts = [
            _display_path(case_root / "live_error.json"),
            _display_path(transcript_path),
            *_session_artifact_paths(session_store.session_paths(session_id)),
        ]
    passed = error is None and actual_verdict is case.expected_verdict and actual_tiers == case.expected_tiers
    case_result = BenchmarkCaseResult(
        mode="live",
        id=case.id,
        category=case.category,
        scenario=case.scenario,
        expected_verdict=case.expected_verdict,
        actual_verdict=actual_verdict,
        expected_tiers=list(case.expected_tiers),
        actual_tiers=actual_tiers,
        iterations=iterations,
        passed=passed,
        routing_mode=routing_mode,
        provider=route_provider,
        model_used=route_model,
        session_id=session_id,
        artifacts=artifacts,
        runtime_seconds=round(time.perf_counter() - started, 3),
        error=error,
        notes=notes,
    )
    case_result_path = case_root / "case_result.json"
    if _display_path(case_result_path) not in case_result.artifacts:
        case_result.artifacts.append(_display_path(case_result_path))
    _write_json(case_result_path, case_result.to_dict())
    return case_result


def _persist_live_case_artifacts(
    *,
    case_root: Path,
    result: Any,
    session_store: SessionStore,
    transcripts: list[LiveRoleTranscript],
) -> list[str]:
    artifacts: list[str] = []
    candidate_path = case_root / "candidate_solution.json"
    report_path = case_root / "verification_report.json"
    transcript_path = case_root / "role_transcripts.json"
    _write_json(candidate_path, result.final_candidate.to_dict())
    _write_json(report_path, result.final_report.to_dict())
    _write_json(transcript_path, {"calls": [item.to_dict() for item in transcripts]})
    artifacts.extend(
        [
            _display_path(candidate_path),
            _display_path(report_path),
            _display_path(transcript_path),
            *_session_artifact_paths(result.session_paths),
        ]
    )
    for artifact in result.checkpoint.artifacts:
        artifacts.append(_resolve_session_artifact_path(session_store, result.session_id, artifact))
    deduped: list[str] = []
    for artifact in artifacts:
        if artifact not in deduped:
            deduped.append(artifact)
    return deduped


def _benchmark_config(evidence_directory: str, *, base_config: DeepGvrConfig | None = None) -> DeepGvrConfig:
    config = DeepGvrConfig.from_dict((base_config or DeepGvrConfig()).to_dict())
    config.evidence.directory = evidence_directory
    config.loop.max_iterations = 1
    config.verification.tier3.enabled = True
    return config


def _summarize_results(results: list[BenchmarkCaseResult]) -> BenchmarkSummary:
    total_cases = len(results)
    passed_cases = sum(1 for item in results if item.passed)
    failed_cases = total_cases - passed_cases
    verified_cases = [item for item in results if item.expected_verdict is VerificationVerdict.VERIFIED]
    negative_cases = [item for item in results if item.expected_verdict is VerificationVerdict.FLAWS_FOUND]
    non_verified_cases = [item for item in results if item.expected_verdict is not VerificationVerdict.VERIFIED]
    cannot_verify_cases = [item for item in results if item.expected_verdict is VerificationVerdict.CANNOT_VERIFY]
    return BenchmarkSummary(
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=failed_cases,
        verdict_match_rate=_ratio(passed_cases, total_cases),
        true_positive_rate=_ratio(
            sum(1 for item in verified_cases if item.actual_verdict is VerificationVerdict.VERIFIED),
            len(verified_cases),
        ),
        true_negative_rate=_ratio(
            sum(1 for item in negative_cases if item.actual_verdict is VerificationVerdict.FLAWS_FOUND),
            len(negative_cases),
        ),
        false_positive_rate=_ratio(
            sum(1 for item in non_verified_cases if item.actual_verdict is VerificationVerdict.VERIFIED),
            len(non_verified_cases),
        ),
        tier_accuracy=_ratio(
            sum(1 for item in results if item.expected_tiers == item.actual_tiers),
            total_cases,
        ),
        iteration_efficiency=round(sum(item.iterations for item in results) / total_cases, 3) if total_cases else 0.0,
        failure_admission_rate=_ratio(
            sum(1 for item in cannot_verify_cases if item.actual_verdict is VerificationVerdict.CANNOT_VERIFY),
            len(cannot_verify_cases),
        ),
        meets_false_positive_bar=_ratio(
            sum(1 for item in non_verified_cases if item.actual_verdict is VerificationVerdict.VERIFIED),
            len(non_verified_cases),
        )
        < 0.2,
    )


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 3)


def _display_path(path: str | Path) -> str:
    resolved = Path(path)
    repo_root = _repo_root()
    try:
        return resolved.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return resolved.as_posix()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_executor(
    command: list[str],
    cwd: Path,
    timeout_seconds: int | None = None,
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
    except subprocess.TimeoutExpired as exc:
        timeout_text = timeout_seconds if timeout_seconds is not None else "the configured"
        return CommandExecutionResult(
            returncode=124,
            stdout=exc.stdout or "",
            stderr=f"Hermes command timed out after {timeout_text} seconds.",
        )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _session_artifact_paths(session_paths: SessionPaths) -> list[str]:
    artifacts: list[str] = []
    for path in (session_paths.evidence_log, session_paths.checkpoint_file):
        if path.exists():
            artifacts.append(_display_path(path))
    return artifacts


def _resolve_session_artifact_path(session_store: SessionStore, session_id: str, artifact: str) -> str:
    artifact_path = Path(artifact)
    if artifact_path.is_absolute():
        return _display_path(artifact_path)
    session_root = session_store.session_paths(session_id).session_dir.parent
    return _display_path(session_root / artifact_path)


def _is_baseline_report_path(path: Path) -> bool:
    target = path.expanduser()
    if not target.is_absolute() and target.as_posix() == _BASELINE_REPORT_PATH.as_posix():
        return True
    baseline = (_repo_root() / _BASELINE_REPORT_PATH).resolve()
    try:
        return target.resolve() == baseline
    except FileNotFoundError:
        return target.parent.resolve() == baseline.parent and target.name == baseline.name


def _extract_json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char not in "{[":
            continue
        try:
            payload, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise ValueError(f"Could not parse a JSON object from Hermes output: {text[:200]!r}")


def _fixture_agents(case: BenchmarkCase) -> FixtureAgents:
    def generator(request: GenerationRequest) -> CandidateSolution:
        return CandidateSolution(
            hypothesis=_hypothesis_for_case(case),
            approach="Evaluate the claim against the deterministic benchmark fixture.",
            technical_details=[f"Scenario fixture: {case.scenario}."],
            expected_results=["The benchmark verdict should match the known answer for this case."],
            assumptions=["The deterministic fixture encodes the intended benchmark ground truth."],
            limitations=["This release benchmark uses fixture agents instead of live Hermes subagents."],
            references=["Fowler et al. 2012", "Dennis et al. 2002"],
            revision_notes=[],
        )

    def reviser(request: RevisionRequest) -> CandidateSolution:
        revised = request.candidate.to_dict()
        revised["revision_notes"] = list(request.candidate.revision_notes) + [
            "No benchmark revision path is defined for this fixture."
        ]
        return CandidateSolution.from_dict(revised)

    def verifier(request: VerificationRequest) -> VerificationReport:
        match case.scenario:
            case "known_correct_surface_threshold" | "known_correct_planar_qubits" | "known_correct_union_find":
                return _verified_tier1_report("The claim matches the benchmark ground truth.")
            case "known_incorrect_surface_threshold_5pct" | "known_incorrect_color_codes_all_noise_models":
                return _flawed_tier1_report("The claim contradicts established benchmark knowledge.")
            case "simulation_verified_distance5":
                if request.simulation_results is None:
                    return _simulation_request_report(
                        reason="Empirical confirmation is required for the quantitative claim.",
                        distance=[3, 5],
                        error_rate=0.001,
                    )
                return _verified_with_tier2(
                    request.simulation_results,
                    "The simulated trend supports the claimed logical-error behavior.",
                )
            case "simulation_rejected_distance7":
                if request.simulation_results is None:
                    return _simulation_request_report(
                        reason="Empirical confirmation is required for the quantitative claim.",
                        distance=[5, 7],
                        error_rate=0.005,
                    )
                return _flawed_with_tier2(
                    request.simulation_results,
                    "The simulated logical error rate does not support the claim.",
                )
            case "formal_proved_repetition_majority":
                if request.formal_results is None:
                    return _formal_request_report(
                        "For every odd repetition-code distance d, majority decoding corrects up to (d-1)/2 bit flips."
                    )
                return _verified_with_tier3(
                    list(request.formal_results),
                    "The formal result confirms the benchmark theorem statement.",
                )
            case "formal_unavailable_repetition_scaling":
                if request.formal_results is None:
                    return _formal_request_report(
                        "For the repetition code of odd distance d, the logical error rate is O(p^((d+1)/2))."
                    )
                return VerificationReport(
                    verdict=VerificationVerdict.CANNOT_VERIFY,
                    tier1=Tier1Report(
                        checks=[
                            AnalyticalCheck(
                                check="formal_availability",
                                status=AnalyticalStatus.UNCERTAIN,
                                detail="The benchmark requires a formal proof outcome.",
                            )
                        ],
                        overall=VerificationVerdict.CANNOT_VERIFY,
                        flaws=[],
                        caveats=["Formal verification remained unavailable in the benchmark fixture."],
                    ),
                    tier2=None,
                    tier3=list(request.formal_results),
                    flaws=[],
                    caveats=["Formal verification remained unavailable in the benchmark fixture."],
                    cannot_verify_reason="Tier 3 proof evidence was unavailable for this benchmark case.",
                )
            case _:
                raise ValueError(f"Unknown benchmark scenario {case.scenario!r}.")

    def simulator(request: SimulationRequest) -> SimResults:
        if case.scenario == "simulation_verified_distance5":
            return SimResults(
                simulator="stim",
                adapter_version="0.1.0",
                timestamp=_DETERMINISTIC_TIMESTAMP,
                runtime_seconds=0.2,
                backend=Backend.LOCAL,
                data=[],
                analysis=SimAnalysis(
                    threshold_estimate=0.001,
                    threshold_method="fixture_supports_claim",
                    below_threshold_distances=[5],
                    scaling_exponent=None,
                ),
                errors=[],
            )
        if case.scenario == "simulation_rejected_distance7":
            return SimResults(
                simulator="stim",
                adapter_version="0.1.0",
                timestamp=_DETERMINISTIC_TIMESTAMP,
                runtime_seconds=0.2,
                backend=Backend.LOCAL,
                data=[],
                analysis=SimAnalysis(
                    threshold_estimate=0.005,
                    threshold_method="fixture_refutes_claim",
                    below_threshold_distances=[],
                    scaling_exponent=None,
                ),
                errors=[],
            )
        raise ValueError(f"Unexpected simulator call for {case.scenario!r}.")

    def formal_verifier(request: FormalVerificationRequest) -> list[Tier3ClaimResult]:
        if case.scenario == "formal_proved_repetition_majority":
            return [
                Tier3ClaimResult(
                    claim=request.claims[0].claim,
                    backend=request.backend,
                    proof_status=ProofStatus.PROVED,
                    details="The benchmark fixture marks the theorem as proved.",
                    lean_code="theorem repetition_majority : True := by trivial",
                    proof_time_seconds=1.5,
                )
            ]
        if case.scenario == "formal_unavailable_repetition_scaling":
            return [
                Tier3ClaimResult(
                    claim=request.claims[0].claim,
                    backend=request.backend,
                    proof_status=ProofStatus.UNAVAILABLE,
                    details="The benchmark fixture marks the proof transport unavailable.",
                    lean_code="",
                    proof_time_seconds=None,
                )
            ]
        raise ValueError(f"Unexpected formal verifier call for {case.scenario!r}.")

    return FixtureAgents(
        generator=generator,
        verifier=verifier,
        reviser=reviser,
        simulator=simulator if case.scenario.startswith("simulation_") else None,
        formal_verifier=formal_verifier if case.scenario.startswith("formal_") else None,
    )


def _hypothesis_for_case(case: BenchmarkCase) -> str:
    match case.scenario:
        case "known_correct_surface_threshold":
            return "The surface code has a threshold under standard depolarizing noise assumptions."
        case "known_correct_planar_qubits":
            return "A planar surface code of distance d requires O(d^2) physical qubits."
        case "known_correct_union_find":
            return "Union-Find decoding is near-linear in the size of the syndrome graph."
        case "known_incorrect_surface_threshold_5pct":
            return "The surface-code threshold under circuit-level noise is 5 percent."
        case "known_incorrect_color_codes_all_noise_models":
            return "Color codes outperform surface codes for every noise model."
        case "simulation_verified_distance5":
            return "At physical error rate 0.001, the logical error rate decreases with distance in the rotated surface code."
        case "simulation_rejected_distance7":
            return "At physical error rate 0.005, a distance-7 rotated memory experiment stays below 1e-4 logical error."
        case "formal_proved_repetition_majority":
            return "Majority decoding for odd repetition codes corrects up to (d-1)/2 bit flips."
        case "formal_unavailable_repetition_scaling":
            return "The repetition-code logical error rate scales as O(p^((d+1)/2))."
        case _:
            return case.prompt


def _verified_tier1_report(detail: str) -> VerificationReport:
    return VerificationReport(
        verdict=VerificationVerdict.VERIFIED,
        tier1=Tier1Report(
            checks=[AnalyticalCheck(check="benchmark_ground_truth", status=AnalyticalStatus.PASS, detail=detail)],
            overall=VerificationVerdict.VERIFIED,
            flaws=[],
            caveats=[],
        ),
        tier2=None,
        tier3=[],
        flaws=[],
        caveats=[],
        cannot_verify_reason=None,
    )


def _flawed_tier1_report(detail: str) -> VerificationReport:
    flaw = "The claim conflicts with the benchmark ground truth."
    return VerificationReport(
        verdict=VerificationVerdict.FLAWS_FOUND,
        tier1=Tier1Report(
            checks=[AnalyticalCheck(check="benchmark_ground_truth", status=AnalyticalStatus.FAIL, detail=detail)],
            overall=VerificationVerdict.FLAWS_FOUND,
            flaws=[flaw],
            caveats=[],
        ),
        tier2=None,
        tier3=[],
        flaws=[flaw],
        caveats=[],
        cannot_verify_reason=None,
    )


def _simulation_request_report(*, reason: str, distance: list[int], error_rate: float) -> VerificationReport:
    flaw = "Simulation evidence is required before accepting the quantitative claim."
    return VerificationReport(
        verdict=VerificationVerdict.FLAWS_FOUND,
        tier1=Tier1Report(
            checks=[
                AnalyticalCheck(
                    check="empirical_support",
                    status=AnalyticalStatus.UNCERTAIN,
                    detail="The benchmark case requires a Tier 2 empirical check.",
                )
            ],
            overall=VerificationVerdict.FLAWS_FOUND,
            flaws=[flaw],
            caveats=[],
        ),
        tier2=Tier2Report(
            simulation_requested=True,
            reason=reason,
            simulation_spec={
                "simulator": "stim",
                "task": {
                    "code": "surface_code",
                    "task_type": "rotated_memory_z",
                    "distance": distance,
                    "rounds_per_distance": "2d",
                    "noise_model": "depolarizing",
                    "error_rates": [error_rate],
                    "decoder": "pymatching",
                    "shots_per_point": 100,
                },
                "resources": {
                    "timeout_seconds": 60,
                    "max_parallel": 1,
                },
            },
            results=None,
            interpretation=None,
        ),
        tier3=[],
        flaws=[flaw],
        caveats=[],
        cannot_verify_reason=None,
    )


def _verified_with_tier2(sim_results: SimResults, interpretation: str) -> VerificationReport:
    return VerificationReport(
        verdict=VerificationVerdict.VERIFIED,
        tier1=Tier1Report(
            checks=[
                AnalyticalCheck(
                    check="empirical_support",
                    status=AnalyticalStatus.PASS,
                    detail="The Tier 2 benchmark result supports the claim.",
                )
            ],
            overall=VerificationVerdict.VERIFIED,
            flaws=[],
            caveats=[],
        ),
        tier2=Tier2Report(
            simulation_requested=True,
            reason="The quantitative claim requires empirical confirmation.",
            simulation_spec=None,
            results=sim_results.to_dict(),
            interpretation=interpretation,
        ),
        tier3=[],
        flaws=[],
        caveats=[],
        cannot_verify_reason=None,
    )


def _flawed_with_tier2(sim_results: SimResults, interpretation: str) -> VerificationReport:
    flaw = "The Tier 2 benchmark result refutes the claim."
    return VerificationReport(
        verdict=VerificationVerdict.FLAWS_FOUND,
        tier1=Tier1Report(
            checks=[
                AnalyticalCheck(
                    check="empirical_support",
                    status=AnalyticalStatus.FAIL,
                    detail="The Tier 2 benchmark result does not support the claim.",
                )
            ],
            overall=VerificationVerdict.FLAWS_FOUND,
            flaws=[flaw],
            caveats=[],
        ),
        tier2=Tier2Report(
            simulation_requested=True,
            reason="The quantitative claim requires empirical confirmation.",
            simulation_spec=None,
            results=sim_results.to_dict(),
            interpretation=interpretation,
        ),
        tier3=[],
        flaws=[flaw],
        caveats=[],
        cannot_verify_reason=None,
    )


def _formal_request_report(claim: str) -> VerificationReport:
    flaw = "Formal proof evidence is required before accepting the theorem claim."
    return VerificationReport(
        verdict=VerificationVerdict.FLAWS_FOUND,
        tier1=Tier1Report(
            checks=[
                AnalyticalCheck(
                    check="formalizability",
                    status=AnalyticalStatus.UNCERTAIN,
                    detail="The benchmark case requires a Tier 3 formal check.",
                )
            ],
            overall=VerificationVerdict.FLAWS_FOUND,
            flaws=[flaw],
            caveats=[],
        ),
        tier2=None,
        tier3=[
            Tier3ClaimResult(
                claim=claim,
                backend="aristotle",
                proof_status=ProofStatus.REQUESTED,
                details="The benchmark fixture requests Tier 3 proof output.",
                lean_code="",
                proof_time_seconds=None,
            )
        ],
        flaws=[flaw],
        caveats=[],
        cannot_verify_reason=None,
    )


def _verified_with_tier3(results: list[Tier3ClaimResult], detail: str) -> VerificationReport:
    return VerificationReport(
        verdict=VerificationVerdict.VERIFIED,
        tier1=Tier1Report(
            checks=[
                AnalyticalCheck(
                    check="formalizability",
                    status=AnalyticalStatus.PASS,
                    detail=detail,
                )
            ],
            overall=VerificationVerdict.VERIFIED,
            flaws=[],
            caveats=[],
        ),
        tier2=None,
        tier3=list(results),
        flaws=[],
        caveats=[],
        cannot_verify_reason=None,
    )
