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
    AnalysisMeasurement,
    AnalysisResults,
    AnalyticalCheck,
    AnalyticalStatus,
    Backend,
    BranchStrategy,
    CapabilityProbeResult,
    CandidateSolution,
    DeepGvrConfig,
    OrchestratorBackend,
    ProbeStatus,
    ProofStatus,
    Tier1Report,
    Tier2Report,
    Tier3ClaimResult,
    VerificationReport,
    VerificationVerdict,
)
from .domain_context import load_domain_context
from .formal import FormalVerificationRequest, FormalVerifier, build_formal_verifier
from .live_runtime import resolve_live_role_timeout_seconds, resolve_live_role_toolsets
from .orchestrator import (
    _candidate_response_contract,
    _candidate_response_schema,
    _codex_effective_route,
    _codex_route_notes,
    _effective_route_payload,
    _route_with_fallback_note,
    _verification_response_contract,
    _verification_response_schema,
)
from .prompt_profiles import DEFAULT_PROMPT_PROFILE, build_live_role_query
from .probes import probe_model_routing
from .routing import EffectiveModelRoute, build_live_routing_plan, build_native_role_routing_plan
from .runtime_config import load_runtime_config
from .tier2_support import tier2_support_case_ids
from .tier1 import (
    AnalysisRequest,
    GenerationRequest,
    RevisionRequest,
    SessionPaths,
    SessionStore,
    Tier1LoopRunner,
    VerificationRequest,
)

_DETERMINISTIC_TIMESTAMP = "2026-03-26T00:00:00Z"
_DETERMINISTIC_RUN_ID = "baseline"
_ENABLED_TIERS = [1, 2, 3]
_BASELINE_REPORT_PATH = Path("eval/results/baseline_results.json")
_LIVE_ANALYTICAL_BREADTH_CASES: tuple[str, ...] = (
    "known-correct-surface-threshold",
    "known-correct-planar-qubits",
    "known-correct-union-find",
    "known-incorrect-surface-threshold-5pct",
    "known-incorrect-color-codes-all-noise-models",
)
_LIVE_ESCALATION_BREADTH_CASES: tuple[str, ...] = (
    "simulation-verified-distance5",
    "simulation-rejected-distance7",
    "formal-proved-repetition-majority",
    "formal-unavailable-repetition-scaling",
)
_LIVE_EXPANSION_CASES: tuple[str, ...] = (
    "known-incorrect-surface-threshold-5pct",
    "simulation-verified-distance5",
    "formal-proved-repetition-majority",
)
_CORE_SCIENCE_CASES: tuple[str, ...] = (
    "symbolic-verified-equivalence",
    "symbolic-rejected-derivative",
    "optimization-verified-linear-program",
    "optimization-rejected-assignment",
    "dynamics-verified-decay",
)
_PHOTONIC_MBQC_CASES: tuple[str, ...] = (
    "mbqc-verified-graphix-pattern",
    "photonic-verified-basic-state",
    "neutral-atom-verified-register",
)
_TIER2_SUPPORT_CASES: tuple[str, ...] = tier2_support_case_ids()
_TIER3_SUPPORT_CASES: tuple[str, ...] = (
    "formal-proved-repetition-majority",
    "formal-unavailable-repetition-scaling",
    "formal-mathcode-nat-add-zero",
)
_QUANTUM_OSS_CASES: tuple[str, ...] = (
    "simulation-verified-distance5",
    "simulation-rejected-distance7",
    "mbqc-verified-graphix-pattern",
    "photonic-verified-basic-state",
    "neutral-atom-verified-register",
    "tqec-verified-gallery-block-graph",
    "zx-verified-qasm-rewrite",
    "formal-proved-repetition-majority",
)
_BENCHMARK_SUBSETS: dict[str, tuple[str, ...]] = {
    "core-science": _CORE_SCIENCE_CASES,
    "photonic-mbqc": _PHOTONIC_MBQC_CASES,
    "tier2-support": _TIER2_SUPPORT_CASES,
    "tier3-support": _TIER3_SUPPORT_CASES,
    "quantum-oss": _QUANTUM_OSS_CASES,
    "analysis-full": _CORE_SCIENCE_CASES + _QUANTUM_OSS_CASES + ("formal-unavailable-repetition-scaling", "formal-mathcode-nat-add-zero", "orchestration-fanout-threshold"),
    "live-analytical-breadth": _LIVE_ANALYTICAL_BREADTH_CASES,
    "live-escalation-breadth": _LIVE_ESCALATION_BREADTH_CASES,
    "live-expansion": _LIVE_EXPANSION_CASES,
    "live-full": _LIVE_ANALYTICAL_BREADTH_CASES + _LIVE_ESCALATION_BREADTH_CASES,
}


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
    formal_backend: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BenchmarkCase":
        return cls(
            id=data["id"],
            category=data["category"],
            prompt=data["prompt"],
            scenario=data["scenario"],
            expected_verdict=VerificationVerdict(data["expected_verdict"]),
            expected_tiers=[int(item) for item in data["expected_tiers"]],
            formal_backend=data.get("formal_backend"),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = _serialize(self)
        if self.formal_backend is None:
            payload.pop("formal_backend", None)
        return payload


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
    strict_verdict_match: bool
    verdict_accepted: bool
    tiers_matched_expected: bool
    accepted_refutation: bool
    outcome: str
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
        strict_verdict_match = bool(data.get("strict_verdict_match", data["actual_verdict"] == data["expected_verdict"]))
        accepted_refutation = bool(data.get("accepted_refutation", False))
        verdict_accepted = bool(data.get("verdict_accepted", strict_verdict_match or accepted_refutation))
        tiers_matched_expected = bool(
            data.get("tiers_matched_expected", list(data.get("actual_tiers", [])) == list(data.get("expected_tiers", [])))
        )
        error = data.get("error")
        outcome = data.get("outcome") or _classify_case_outcome(
            error=error,
            verdict_accepted=verdict_accepted,
            tiers_matched_expected=tiers_matched_expected,
            accepted_refutation=accepted_refutation,
        )
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
            strict_verdict_match=strict_verdict_match,
            verdict_accepted=verdict_accepted,
            tiers_matched_expected=tiers_matched_expected,
            accepted_refutation=accepted_refutation,
            outcome=outcome,
            routing_mode=data["routing_mode"],
            provider=data["provider"],
            model_used=data["model_used"],
            session_id=data["session_id"],
            artifacts=list(data.get("artifacts", [])),
            runtime_seconds=float(data.get("runtime_seconds", 0.0)),
            error=error,
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
    direct_match_cases: int = 0
    accepted_refutation_cases: int = 0
    tier_mismatch_failures: int = 0
    verdict_mismatch_failures: int = 0
    execution_error_failures: int = 0

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
            direct_match_cases=int(data.get("direct_match_cases", 0)),
            accepted_refutation_cases=int(data.get("accepted_refutation_cases", 0)),
            tier_mismatch_failures=int(data.get("tier_mismatch_failures", 0)),
            verdict_mismatch_failures=int(data.get("verdict_mismatch_failures", 0)),
            execution_error_failures=int(data.get("execution_error_failures", 0)),
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


@dataclass(slots=True)
class BenchmarkConsistencyRun:
    run_index: int
    run_id: str
    output_root: str
    report_path: str
    passed_cases: int
    failed_cases: int
    failed_case_ids: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BenchmarkConsistencyRun":
        return cls(
            run_index=int(data["run_index"]),
            run_id=data["run_id"],
            output_root=data["output_root"],
            report_path=data["report_path"],
            passed_cases=int(data["passed_cases"]),
            failed_cases=int(data["failed_cases"]),
            failed_case_ids=list(data.get("failed_case_ids", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class BenchmarkConsistencyCase:
    id: str
    category: str
    scenario: str
    expected_verdict: VerificationVerdict
    expected_tiers: list[int]
    total_runs: int
    passed_runs: int
    failed_runs: int
    direct_match_runs: int
    accepted_refutation_runs: int
    tier_mismatch_failures: int
    verdict_mismatch_failures: int
    execution_error_failures: int
    pass_rate: float
    actual_verdicts: list[VerificationVerdict]
    actual_tier_signatures: list[str]
    outcomes: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BenchmarkConsistencyCase":
        return cls(
            id=data["id"],
            category=data["category"],
            scenario=data["scenario"],
            expected_verdict=VerificationVerdict(data["expected_verdict"]),
            expected_tiers=[int(item) for item in data["expected_tiers"]],
            total_runs=int(data["total_runs"]),
            passed_runs=int(data["passed_runs"]),
            failed_runs=int(data["failed_runs"]),
            direct_match_runs=int(data["direct_match_runs"]),
            accepted_refutation_runs=int(data["accepted_refutation_runs"]),
            tier_mismatch_failures=int(data["tier_mismatch_failures"]),
            verdict_mismatch_failures=int(data["verdict_mismatch_failures"]),
            execution_error_failures=int(data["execution_error_failures"]),
            pass_rate=float(data["pass_rate"]),
            actual_verdicts=[VerificationVerdict(item) for item in data.get("actual_verdicts", [])],
            actual_tier_signatures=list(data.get("actual_tier_signatures", [])),
            outcomes=list(data.get("outcomes", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class BenchmarkConsistencySummary:
    repeat_count: int
    total_cases: int
    total_case_runs: int
    passed_case_runs: int
    failed_case_runs: int
    fully_passing_runs: int
    stable_case_passes: int
    unstable_cases: int
    case_pass_rate: float
    run_pass_rate: float
    all_runs_passed: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BenchmarkConsistencySummary":
        return cls(
            repeat_count=int(data["repeat_count"]),
            total_cases=int(data["total_cases"]),
            total_case_runs=int(data["total_case_runs"]),
            passed_case_runs=int(data["passed_case_runs"]),
            failed_case_runs=int(data["failed_case_runs"]),
            fully_passing_runs=int(data["fully_passing_runs"]),
            stable_case_passes=int(data["stable_case_passes"]),
            unstable_cases=int(data["unstable_cases"]),
            case_pass_rate=float(data["case_pass_rate"]),
            run_pass_rate=float(data["run_pass_rate"]),
            all_runs_passed=bool(data["all_runs_passed"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class BenchmarkConsistencyReport:
    mode: str
    repeat_count: int
    run_id: str
    output_root: str
    generated_at: str
    suite_path: str
    routing_probe_status: ProbeStatus
    subset: str | None
    selected_case_ids: list[str]
    runs: list[BenchmarkConsistencyRun]
    cases: list[BenchmarkConsistencyCase]
    summary: BenchmarkConsistencySummary

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BenchmarkConsistencyReport":
        return cls(
            mode=data["mode"],
            repeat_count=int(data["repeat_count"]),
            run_id=data["run_id"],
            output_root=data["output_root"],
            generated_at=data["generated_at"],
            suite_path=data["suite_path"],
            routing_probe_status=ProbeStatus(data["routing_probe_status"]),
            subset=data.get("subset"),
            selected_case_ids=list(data.get("selected_case_ids", [])),
            runs=[BenchmarkConsistencyRun.from_dict(item) for item in data.get("runs", [])],
            cases=[BenchmarkConsistencyCase.from_dict(item) for item in data.get("cases", [])],
            summary=BenchmarkConsistencySummary.from_dict(data["summary"]),
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
    analyzer: Any | None = None
    formal_verifier: FormalVerifier | None = None


@dataclass(slots=True)
class LiveEvalConfig:
    hermes_binary: str = "hermes"
    codex_binary: str = "codex"
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
    backend: str
    role: str
    provider: str
    model: str
    command: list[str]
    prompt_path: str
    query: str
    response: str
    selected_route: dict[str, Any] | None = None
    response_object: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = _serialize(self)
        if self.selected_route is None:
            payload.pop("selected_route", None)
        if self.response_object is None:
            payload.pop("response_object", None)
        if self.error is None:
            payload.pop("error", None)
        return payload


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
            "branch_id": request.branch_id,
            "branch_strategy": request.branch_strategy.value,
            "branch_parent_id": request.branch_parent_id,
            "branch_rationale": request.branch_rationale,
            "trigger_flaws": list(request.trigger_flaws),
        }
        response, actual_route = self._run_role(
            role="generator",
            prompt_file="generator.md",
            route=request.route,
            response_contract=_candidate_response_contract(),
            payload=payload,
        )
        request.route = actual_route
        return CandidateSolution.from_dict(_extract_json_object(response))

    def verifier(self, request: VerificationRequest) -> VerificationReport:
        payload = {
            "session_id": request.session_id,
            "iteration": request.iteration,
            "candidate": request.candidate.to_dict(),
            "analysis_results": request.analysis_results.to_dict() if request.analysis_results else None,
            "formal_results": [item.to_dict() for item in request.formal_results] if request.formal_results else None,
        }
        response, actual_route = self._run_role(
            role="verifier",
            prompt_file="verifier.md",
            route=request.route,
            response_contract=_verification_response_contract(),
            payload=payload,
        )
        request.route = actual_route
        return VerificationReport.from_dict(_extract_json_object(response))

    def reviser(self, request: RevisionRequest) -> CandidateSolution:
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
        response, actual_route = self._run_role(
            role="reviser",
            prompt_file="reviser.md",
            route=request.route,
            response_contract=_candidate_response_contract(),
            payload=payload,
        )
        request.route = actual_route
        return CandidateSolution.from_dict(_extract_json_object(response))

    def _run_role(
        self,
        *,
        role: str,
        prompt_file: str,
        route: EffectiveModelRoute,
        response_contract: dict[str, Any],
        payload: dict[str, Any],
    ) -> tuple[str, EffectiveModelRoute]:
        prompt_path = self._resolve_prompt_path(role, prompt_file)
        prompt_text = prompt_path.read_text(encoding="utf-8")
        candidates = [route, *route.fallback_routes]
        prior_route: EffectiveModelRoute | None = None
        for index, base_candidate in enumerate(candidates):
            candidate = base_candidate
            if index > 0 and prior_route is not None:
                candidate = _route_with_fallback_note(base_candidate, prior_route)
            query = self._build_query(
                role=role,
                prompt_text=prompt_text,
                payload=payload,
                response_contract=response_contract,
                route_notes=candidate.notes,
                route_temperature=candidate.temperature,
            )
            command = [self.config.hermes_binary, "chat", "-Q", "-q", query]
            if candidate.provider not in {"", "default", "adapter"}:
                command.extend(["--provider", candidate.provider])
            if candidate.model not in {"", "configured-by-hermes", "provider-default"}:
                command.extend(["--model", candidate.model])
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
                    resolve_live_role_timeout_seconds(
                        role,
                        self.config.command_timeout_seconds,
                        has_analysis_results=bool(payload.get("analysis_results")),
                        has_formal_results=bool(payload.get("formal_results")),
                    ),
                )
            transcript = LiveRoleTranscript(
                backend=OrchestratorBackend.HERMES.value,
                role=role,
                provider=candidate.provider,
                model=candidate.model,
                command=list(command),
                prompt_path=_display_path(prompt_path),
                query=query,
                response=result.stdout if result.returncode == 0 else f"{result.stdout}\n{result.stderr}".strip(),
                selected_route=_effective_route_payload(candidate),
            )
            self.transcripts.append(transcript)
            if result.returncode == 0:
                if _looks_like_live_route_configuration_error(result.stdout.strip()):
                    if index + 1 < len(candidates):
                        prior_route = candidate
                        continue
                    raise RuntimeError(
                        f"Hermes role {role!r} emitted a live route configuration error: {result.stdout.strip()}"
                    )
                try:
                    transcript.response_object = _extract_json_object(result.stdout)
                except ValueError:
                    transcript.response_object = None
                return result.stdout, candidate
            if index + 1 < len(candidates) and _looks_like_live_route_configuration_error(
                result.stderr.strip() or result.stdout.strip()
            ):
                prior_route = candidate
                continue
            transcript.error = (
                f"Hermes role {role!r} failed with exit code {result.returncode}: "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
            raise RuntimeError(
                f"Hermes role {role!r} failed with exit code {result.returncode}: {result.stderr.strip() or result.stdout.strip()}"
            )
        raise RuntimeError(f"Hermes role {role!r} exhausted all live route candidates without a result.")

    def _resolve_prompt_path(self, role: str, prompt_file: str) -> Path:
        if self.config.prompt_profile == "compact" and role == "verifier":
            compact_path = self.prompt_root / f"{Path(prompt_file).stem}_compact.md"
            if compact_path.exists():
                return compact_path
        return self.prompt_root / prompt_file

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


class CodexPromptRoleRunner:
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
            "branch_id": request.branch_id,
            "branch_strategy": request.branch_strategy.value,
            "branch_parent_id": request.branch_parent_id,
            "branch_rationale": request.branch_rationale,
            "trigger_flaws": list(request.trigger_flaws),
        }
        response, actual_route = self._run_role(
            role="generator",
            prompt_file="generator.md",
            route=request.route,
            response_contract=_candidate_response_contract(),
            response_schema=_candidate_response_schema(),
            payload=payload,
        )
        request.route = actual_route
        return CandidateSolution.from_dict(_extract_json_object(response))

    def verifier(self, request: VerificationRequest) -> VerificationReport:
        payload = {
            "session_id": request.session_id,
            "iteration": request.iteration,
            "candidate": request.candidate.to_dict(),
            "analysis_results": request.analysis_results.to_dict() if request.analysis_results else None,
            "formal_results": [item.to_dict() for item in request.formal_results] if request.formal_results else None,
        }
        response, actual_route = self._run_role(
            role="verifier",
            prompt_file="verifier.md",
            route=request.route,
            response_contract=_verification_response_contract(),
            response_schema=_verification_response_schema(),
            payload=payload,
        )
        request.route = actual_route
        return VerificationReport.from_dict(_extract_json_object(response))

    def reviser(self, request: RevisionRequest) -> CandidateSolution:
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
        response, actual_route = self._run_role(
            role="reviser",
            prompt_file="reviser.md",
            route=request.route,
            response_contract=_candidate_response_contract(),
            response_schema=_candidate_response_schema(),
            payload=payload,
        )
        request.route = actual_route
        return CandidateSolution.from_dict(_extract_json_object(response))

    def _run_role(
        self,
        *,
        role: str,
        prompt_file: str,
        route: EffectiveModelRoute,
        response_contract: dict[str, Any],
        response_schema: dict[str, Any],
        payload: dict[str, Any],
    ) -> tuple[str, EffectiveModelRoute]:
        prompt_path = self._resolve_prompt_path(role, prompt_file)
        prompt_text = prompt_path.read_text(encoding="utf-8")
        candidates = [route, *route.fallback_routes]
        prior_route: EffectiveModelRoute | None = None
        for index, base_candidate in enumerate(candidates):
            candidate = _codex_effective_route(base_candidate)
            if index > 0 and prior_route is not None:
                candidate = _route_with_fallback_note(candidate, prior_route)
            query = build_live_role_query(
                role=role,
                prompt_text=prompt_text,
                payload=payload,
                response_contract=response_contract,
                route_notes=_codex_route_notes(candidate),
                route_temperature=candidate.temperature,
                prompt_profile=self.config.prompt_profile,
            )
            command, result, response_text = self._run_codex_command(
                query=query,
                response_schema=response_schema,
                route=candidate,
                role=role,
                has_analysis_results=bool(payload.get("analysis_results")),
                has_formal_results=bool(payload.get("formal_results")),
            )
            transcript = LiveRoleTranscript(
                backend=OrchestratorBackend.CODEX_LOCAL.value,
                role=role,
                provider=candidate.provider,
                model=candidate.model,
                command=list(command),
                prompt_path=_display_path(prompt_path),
                query=query,
                response=response_text,
                selected_route=_effective_route_payload(candidate),
            )
            self.transcripts.append(transcript)
            if result.returncode != 0:
                transcript.error = (
                    f"Codex role {role!r} failed with exit code {result.returncode}: "
                    f"{result.stderr.strip() or result.stdout.strip()}"
                )
                if index + 1 < len(candidates) and _looks_like_live_route_configuration_error(response_text):
                    prior_route = candidate
                    continue
                raise RuntimeError(transcript.error)
            try:
                transcript.response_object = _extract_json_object(response_text)
            except ValueError as exc:
                transcript.error = f"Codex role {role!r} did not return a valid JSON payload: {exc}"
                raise RuntimeError(transcript.error) from exc
            return response_text, candidate
        raise RuntimeError(f"Codex role {role!r} exhausted all live route candidates without a result.")

    def _run_codex_command(
        self,
        *,
        query: str,
        response_schema: dict[str, Any],
        route: EffectiveModelRoute,
        role: str,
        has_analysis_results: bool,
        has_formal_results: bool,
    ) -> tuple[list[str], CommandExecutionResult, str]:
        with TemporaryDirectory(prefix="deep-gvr-live-codex-role-") as tmpdir:
            temp_root = Path(tmpdir)
            response_schema_path = temp_root / "role_response.schema.json"
            output_path = temp_root / "role_response.json"
            response_schema_path.write_text(json.dumps(response_schema, indent=2), encoding="utf-8")
            command = [
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
                command.extend(["-c", f'model_provider="{route.provider}"'])
            if route.model not in {"", "configured-by-codex", "provider-default"}:
                command.extend(["--model", route.model])
            command.append(query)
            if self.executor is not None:
                result = self.executor(command, temp_root)
            else:
                result = _default_executor(
                    command,
                    temp_root,
                    resolve_live_role_timeout_seconds(
                        role,
                        self.config.command_timeout_seconds,
                        has_analysis_results=has_analysis_results,
                        has_formal_results=has_formal_results,
                    ),
                )
            response_text = output_path.read_text(encoding="utf-8").strip() if output_path.exists() else ""
            if not response_text:
                response_text = result.stdout if result.returncode == 0 else f"{result.stdout}\n{result.stderr}".strip()
            return command, result, response_text

    def _resolve_prompt_path(self, role: str, prompt_file: str) -> Path:
        if self.config.prompt_profile == "compact" and role == "verifier":
            compact_path = self.prompt_root / f"{Path(prompt_file).stem}_compact.md"
            if compact_path.exists():
                return compact_path
        return self.prompt_root / prompt_file


def load_benchmark_suite(
    path: str | Path,
    *,
    case_ids: list[str] | tuple[str, ...] = (),
    categories: list[str] | tuple[str, ...] = (),
    subset: str | None = None,
    max_cases: int | None = None,
) -> list[BenchmarkCase]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = [BenchmarkCase.from_dict(item) for item in payload]
    if subset:
        try:
            subset_ids = set(_BENCHMARK_SUBSETS[subset])
        except KeyError as exc:
            available = ", ".join(sorted(_BENCHMARK_SUBSETS))
            raise ValueError(f"Unknown benchmark subset {subset!r}. Expected one of: {available}.") from exc
        available_ids = {item.id for item in cases}
        missing = sorted(subset_ids - available_ids)
        if missing:
            raise ValueError(f"Benchmark subset {subset!r} references unknown case ids: {', '.join(missing)}.")
        cases = [item for item in cases if item.id in subset_ids]
    if categories:
        allowed_categories = {item.category for item in cases} if subset else {item.category for item in cases}
        requested = set(categories)
        unknown = sorted(requested - allowed_categories)
        if unknown:
            available = ", ".join(sorted(allowed_categories))
            raise ValueError(f"Unknown benchmark categories: {', '.join(unknown)}. Available categories: {available}.")
        cases = [item for item in cases if item.category in requested]
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
    categories: list[str] | tuple[str, ...] = (),
    subset: str | None = None,
    max_cases: int | None = None,
    live_config: LiveEvalConfig | None = None,
    executor: CommandExecutor | None = None,
    clock: Callable[[], datetime] | None = None,
) -> BenchmarkReport:
    suite_file = Path(suite_path)
    benchmark_cases = load_benchmark_suite(
        suite_file,
        case_ids=case_ids,
        categories=categories,
        subset=subset,
        max_cases=max_cases,
    )
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
        runtime_config = load_runtime_config(config_path) if config_path is not None else DeepGvrConfig()
        results = _run_live_suite(
            benchmark_cases,
            routing_probe=probe,
            base_config=runtime_config,
            output_root=resolved_output_root,
            run_id=resolved_run_id,
            live_config=live_config or LiveEvalConfig(),
            executor=executor,
        )
        generated_at = _isoformat(now)
        runner_backend = _live_runner_backend(runtime_config)
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


def run_repeated_benchmark_suite(
    suite_path: str | Path,
    *,
    repeat_count: int,
    routing_probe: CapabilityProbeResult | None = None,
    mode: str = "live",
    config_path: str | Path | None = None,
    output_root: str | Path | None = None,
    run_id: str | None = None,
    case_ids: list[str] | tuple[str, ...] = (),
    categories: list[str] | tuple[str, ...] = (),
    subset: str | None = None,
    max_cases: int | None = None,
    live_config: LiveEvalConfig | None = None,
    executor: CommandExecutor | None = None,
    clock: Callable[[], datetime] | None = None,
) -> BenchmarkConsistencyReport:
    if repeat_count < 1:
        raise ValueError("repeat_count must be at least 1.")

    probe = routing_probe or probe_model_routing()
    clock = clock or _utc_now
    now = clock()
    suite_file = Path(suite_path)
    resolved_run_id = run_id or (
        now.strftime("%Y%m%dT%H%M%SZ") if mode == "live" else f"{_DETERMINISTIC_RUN_ID}-repeat"
    )
    resolved_output_root = _resolve_consistency_output_root(mode=mode, output_root=output_root, run_id=resolved_run_id)
    reports: list[BenchmarkReport] = []
    runs: list[BenchmarkConsistencyRun] = []

    for run_index in range(1, repeat_count + 1):
        run_label = f"run-{run_index:03d}"
        run_output_root = resolved_output_root / "runs" / run_label
        report = run_benchmark_suite(
            suite_file,
            routing_probe=probe,
            mode=mode,
            config_path=config_path,
            output_root=run_output_root,
            run_id=f"{resolved_run_id}-{run_label}",
            case_ids=case_ids,
            categories=categories,
            subset=subset,
            max_cases=max_cases,
            live_config=live_config,
            executor=executor,
            clock=clock,
        )
        report_path = run_output_root / "report.json"
        write_benchmark_report(report, report_path)
        reports.append(report)
        runs.append(
            BenchmarkConsistencyRun(
                run_index=run_index,
                run_id=report.run_id,
                output_root=_display_path(run_output_root),
                report_path=_display_path(report_path),
                passed_cases=report.summary.passed_cases,
                failed_cases=report.summary.failed_cases,
                failed_case_ids=[case.id for case in report.cases if not case.passed],
            )
        )

    case_summaries = _summarize_consistency_cases(reports)
    return BenchmarkConsistencyReport(
        mode=mode,
        repeat_count=repeat_count,
        run_id=resolved_run_id,
        output_root=_display_path(resolved_output_root),
        generated_at=_isoformat(now),
        suite_path=_display_path(suite_file),
        routing_probe_status=probe.status,
        subset=subset,
        selected_case_ids=[case.id for case in reports[0].cases] if reports else [],
        runs=runs,
        cases=case_summaries,
        summary=_summarize_consistency(runs, case_summaries),
    )


def write_benchmark_consistency_report(report: BenchmarkConsistencyReport, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")


def available_benchmark_subsets() -> dict[str, tuple[str, ...]]:
    return dict(_BENCHMARK_SUBSETS)


def format_benchmark_report_overview(report: BenchmarkReport) -> list[str]:
    lines: list[str] = []
    for case in report.cases:
        status = "PASS" if case.passed else "FAIL"
        expected_tiers = ",".join(str(item) for item in case.expected_tiers) or "-"
        actual_tiers = ",".join(str(item) for item in case.actual_tiers) or "-"
        lines.append(
            f"{status} {case.id} [{case.category}] "
            f"outcome={case.outcome} "
            f"expected={case.expected_verdict.value} actual={case.actual_verdict.value} "
            f"tiers={actual_tiers}/{expected_tiers}"
        )
        if case.notes:
            lines.append(f"  note: {case.notes[0]}")
        if case.error:
            lines.append(f"  error: {case.error}")
        if report.mode == "live":
            lines.append(f"  case_root: {Path(report.output_root) / 'cases' / case.id}")
    return lines


def format_benchmark_consistency_overview(report: BenchmarkConsistencyReport) -> list[str]:
    lines: list[str] = []
    for case in report.cases:
        if case.pass_rate == 1.0:
            status = "STABLE"
        elif case.pass_rate == 0.0:
            status = "FAIL"
        else:
            status = "UNSTABLE"
        tier_signatures = ", ".join(case.actual_tier_signatures) or "-"
        outcomes = ", ".join(case.outcomes) or "-"
        lines.append(
            f"{status} {case.id} [{case.category}] "
            f"pass_rate={case.pass_rate:.3f} outcomes={outcomes} tiers={tier_signatures}"
        )
    return lines


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


def _live_runner_backend(config: DeepGvrConfig) -> str:
    if config.runtime.orchestrator_backend is OrchestratorBackend.CODEX_LOCAL:
        return "codex_native_role_harness"
    return "hermes_prompt_harness"


def _run_fixture_case(
    case: BenchmarkCase,
    *,
    evidence_root: Path,
    routing_probe: CapabilityProbeResult,
) -> BenchmarkCaseResult:
    config = _benchmark_config(str(evidence_root / case.id))
    if case.formal_backend:
        config.verification.tier3.backend = case.formal_backend
    if case.category == "orchestration_required":
        config.loop.max_iterations = 3
        config.loop.alternative_approach = True
        config.loop.max_alternatives = 2
    session_store = SessionStore(config.evidence.directory)
    tier_runner = Tier1LoopRunner(
        config,
        session_store=session_store,
        routing_probe=routing_probe,
    )
    agents = _fixture_agents(case)
    result = tier_runner.run(
        problem=case.prompt,
        generator=agents.generator,
        verifier=agents.verifier,
        reviser=agents.reviser,
        analyzer=agents.analyzer,
        formal_verifier=agents.formal_verifier,
        session_id=f"eval_{case.id}",
    )
    evidence = session_store.read_evidence(result.session_id)
    verify_record = next(record for record in reversed(evidence) if record.phase == "verify")
    notes: list[str] = []
    strict_verdict_match = result.final_report.verdict is case.expected_verdict
    verdict_accepted = strict_verdict_match
    tiers_matched_expected = verify_record.tiers_applied == case.expected_tiers
    accepted_refutation = False
    if not strict_verdict_match:
        notes.append(
            f"Expected verdict {case.expected_verdict.value}, got {result.final_report.verdict.value}."
        )
    if not tiers_matched_expected:
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
        strict_verdict_match=strict_verdict_match,
        verdict_accepted=verdict_accepted,
        tiers_matched_expected=tiers_matched_expected,
        accepted_refutation=accepted_refutation,
        outcome=_classify_case_outcome(
            error=None,
            verdict_accepted=verdict_accepted,
            tiers_matched_expected=tiers_matched_expected,
            accepted_refutation=accepted_refutation,
        ),
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
    if case.formal_backend:
        config.verification.tier3.backend = case.formal_backend
    domain, literature_context = load_domain_context(config)
    session_store = SessionStore(config.evidence.directory)
    if config.runtime.orchestrator_backend is OrchestratorBackend.CODEX_LOCAL:
        routing_plan = build_native_role_routing_plan(config, routing_probe=routing_probe)
        live_runner: HermesPromptRoleRunner | CodexPromptRoleRunner = CodexPromptRoleRunner(
            live_config,
            prompt_root=prompt_root,
            executor=executor,
            cwd=_repo_root(),
        )
    else:
        routing_plan = build_live_routing_plan(config, routing_probe=routing_probe)
        live_runner = HermesPromptRoleRunner(
            live_config,
            prompt_root=prompt_root,
            executor=executor,
            cwd=_repo_root(),
        )
    tier_runner = Tier1LoopRunner(
        config,
        session_store=session_store,
        routing_probe=routing_probe,
        routing_plan=routing_plan,
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
    strict_verdict_match = False
    verdict_accepted = False
    tiers_matched_expected = False
    accepted_refutation = False
    try:
        result = tier_runner.run(
            problem=case.prompt,
            domain=domain,
            literature_context=literature_context,
            generator=live_runner.generator,
            verifier=live_runner.verifier,
            reviser=live_runner.reviser,
            analyzer=None,
            formal_verifier=build_formal_verifier(
                config.verification.tier3,
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
        strict_verdict_match = result.final_report.verdict is case.expected_verdict
        verdict_accepted = strict_verdict_match
        if not strict_verdict_match and _accept_verified_refutation(
            case, result.final_report.verdict, result.final_candidate
        ):
            verdict_accepted = True
            accepted_refutation = True
            notes.append("Accepted a verified refutation as success for this benchmark case.")
        if not verdict_accepted:
            notes.append(
                f"Expected verdict {case.expected_verdict.value}, got {result.final_report.verdict.value}."
            )
        tiers_matched_expected = verify_record.tiers_applied == case.expected_tiers
        if not tiers_matched_expected:
            notes.append(f"Expected tiers {case.expected_tiers}, got {verify_record.tiers_applied}.")
        if verify_record.routing_temperature is not None:
            notes.append("The live role harness does not expose temperature overrides; prompt separation only was applied.")
        if literature_context:
            notes.append(f"Injected {len(literature_context)} domain context note(s) into the live run.")
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
    passed = error is None and verdict_accepted and tiers_matched_expected
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
        strict_verdict_match=strict_verdict_match,
        verdict_accepted=verdict_accepted,
        tiers_matched_expected=tiers_matched_expected,
        accepted_refutation=accepted_refutation,
        outcome=_classify_case_outcome(
            error=error,
            verdict_accepted=verdict_accepted,
            tiers_matched_expected=tiers_matched_expected,
            accepted_refutation=accepted_refutation,
        ),
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


def _accept_verified_refutation(
    case: BenchmarkCase,
    actual_verdict: VerificationVerdict,
    candidate: CandidateSolution,
) -> bool:
    if actual_verdict is not VerificationVerdict.VERIFIED:
        return False

    text = " ".join(
        [
            candidate.hypothesis,
            candidate.approach,
            *candidate.technical_details,
            *candidate.limitations,
            *candidate.revision_notes,
        ]
    ).lower()

    match case.scenario:
        case "known_incorrect_surface_threshold_5pct":
            explicit_rejection_markers = (
                "false",
                "not defensible",
                "indefensible",
                "unsupported",
                "incorrect",
            )
            threshold_refutation_markers = (
                "sub-1%",
                "sub 1%",
                "well below 5%",
                "well below 1%",
                "order of magnitude lower",
                "~0.6-0.8%",
                "0.6-0.8%",
            )
            return (
                "5%" in text
                and any(marker in text for marker in explicit_rejection_markers)
                and any(marker in text for marker in threshold_refutation_markers)
            )
        case "simulation_rejected_distance7":
            return (
                any(marker in text for marker in ("false", "does not achieve", "fails to achieve", "well above 1e-4"))
                and "1e-4" in text
                and any(marker in text for marker in ("p=0.005", "p = 0.005", "distance 7", "d=7"))
            )
        case "known_incorrect_color_codes_all_noise_models":
            return (
                "color code" in text
                and "surface code" in text
                and "all noise models" in text
                and any(marker in text for marker in ("not", "unsupported", "incorrect", "false"))
            )
        case _:
            return False


def _looks_like_live_route_configuration_error(message: str) -> bool:
    lowered = message.lower()
    if "timed out" in lowered:
        return False
    patterns = (
        "badrequesterror",
        "authenticationerror",
        "error code: 400",
        "error code: 401",
        "unknown model",
        "unsupported model",
        "invalid model",
        "your api key is invalid",
        "out of funds",
        "model not found",
        "no such provider",
        "provider unavailable",
    )
    return any(pattern in lowered for pattern in patterns)


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


def _classify_case_outcome(
    *,
    error: str | None,
    verdict_accepted: bool,
    tiers_matched_expected: bool,
    accepted_refutation: bool,
) -> str:
    if error is not None:
        return "execution_error"
    if verdict_accepted and tiers_matched_expected:
        return "accepted_refutation" if accepted_refutation else "direct_match"
    if verdict_accepted:
        return "tier_mismatch"
    return "verdict_mismatch"


def _summarize_results(results: list[BenchmarkCaseResult]) -> BenchmarkSummary:
    total_cases = len(results)
    passed_cases = sum(1 for item in results if item.passed)
    failed_cases = total_cases - passed_cases
    verified_cases = [item for item in results if item.expected_verdict is VerificationVerdict.VERIFIED]
    negative_cases = [item for item in results if item.expected_verdict is VerificationVerdict.FLAWS_FOUND]
    non_verified_cases = [item for item in results if item.expected_verdict is not VerificationVerdict.VERIFIED]
    cannot_verify_cases = [item for item in results if item.expected_verdict is VerificationVerdict.CANNOT_VERIFY]
    direct_match_cases = sum(1 for item in results if item.outcome == "direct_match")
    accepted_refutation_cases = sum(1 for item in results if item.outcome == "accepted_refutation")
    tier_mismatch_failures = sum(1 for item in results if item.outcome == "tier_mismatch")
    verdict_mismatch_failures = sum(1 for item in results if item.outcome == "verdict_mismatch")
    execution_error_failures = sum(1 for item in results if item.outcome == "execution_error")
    true_negative_hits = sum(1 for item in negative_cases if item.verdict_accepted)
    strict_false_positives = sum(
        1 for item in non_verified_cases if item.actual_verdict is VerificationVerdict.VERIFIED and not item.accepted_refutation
    )
    return BenchmarkSummary(
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=failed_cases,
        verdict_match_rate=_ratio(sum(1 for item in results if item.verdict_accepted), total_cases),
        true_positive_rate=_ratio(
            sum(1 for item in verified_cases if item.verdict_accepted),
            len(verified_cases),
        ),
        true_negative_rate=_ratio(true_negative_hits, len(negative_cases)),
        false_positive_rate=_ratio(strict_false_positives, len(non_verified_cases)),
        tier_accuracy=_ratio(sum(1 for item in results if item.tiers_matched_expected), total_cases),
        iteration_efficiency=round(sum(item.iterations for item in results) / total_cases, 3) if total_cases else 0.0,
        failure_admission_rate=_ratio(
            sum(1 for item in cannot_verify_cases if item.actual_verdict is VerificationVerdict.CANNOT_VERIFY),
            len(cannot_verify_cases),
        ),
        meets_false_positive_bar=_ratio(strict_false_positives, len(non_verified_cases)) < 0.2,
        direct_match_cases=direct_match_cases,
        accepted_refutation_cases=accepted_refutation_cases,
        tier_mismatch_failures=tier_mismatch_failures,
        verdict_mismatch_failures=verdict_mismatch_failures,
        execution_error_failures=execution_error_failures,
    )


def _summarize_consistency_cases(reports: list[BenchmarkReport]) -> list[BenchmarkConsistencyCase]:
    if not reports:
        return []
    ordered_ids = [case.id for case in reports[0].cases]
    case_groups = {case_id: [] for case_id in ordered_ids}
    for report in reports:
        for case in report.cases:
            case_groups.setdefault(case.id, []).append(case)

    summaries: list[BenchmarkConsistencyCase] = []
    for case_id in ordered_ids:
        group = case_groups[case_id]
        first = group[0]
        actual_verdicts = _dedupe_preserve_order([item.actual_verdict for item in group])
        actual_tier_signatures = _dedupe_preserve_order([_tier_signature(item.actual_tiers) for item in group])
        outcomes = _dedupe_preserve_order([item.outcome for item in group])
        summaries.append(
            BenchmarkConsistencyCase(
                id=first.id,
                category=first.category,
                scenario=first.scenario,
                expected_verdict=first.expected_verdict,
                expected_tiers=list(first.expected_tiers),
                total_runs=len(group),
                passed_runs=sum(1 for item in group if item.passed),
                failed_runs=sum(1 for item in group if not item.passed),
                direct_match_runs=sum(1 for item in group if item.outcome == "direct_match"),
                accepted_refutation_runs=sum(1 for item in group if item.outcome == "accepted_refutation"),
                tier_mismatch_failures=sum(1 for item in group if item.outcome == "tier_mismatch"),
                verdict_mismatch_failures=sum(1 for item in group if item.outcome == "verdict_mismatch"),
                execution_error_failures=sum(1 for item in group if item.outcome == "execution_error"),
                pass_rate=_ratio(sum(1 for item in group if item.passed), len(group)),
                actual_verdicts=actual_verdicts,
                actual_tier_signatures=actual_tier_signatures,
                outcomes=outcomes,
            )
        )
    return summaries


def _summarize_consistency(
    runs: list[BenchmarkConsistencyRun],
    cases: list[BenchmarkConsistencyCase],
) -> BenchmarkConsistencySummary:
    total_case_runs = sum(case.total_runs for case in cases)
    passed_case_runs = sum(case.passed_runs for case in cases)
    failed_case_runs = total_case_runs - passed_case_runs
    unstable_cases = sum(
        1
        for case in cases
        if case.pass_rate not in {0.0, 1.0}
        or len(case.outcomes) > 1
        or len(case.actual_tier_signatures) > 1
        or len(case.actual_verdicts) > 1
    )
    repeat_count = runs[-1].run_index if runs else 0
    return BenchmarkConsistencySummary(
        repeat_count=repeat_count,
        total_cases=len(cases),
        total_case_runs=total_case_runs,
        passed_case_runs=passed_case_runs,
        failed_case_runs=failed_case_runs,
        fully_passing_runs=sum(1 for run in runs if run.failed_cases == 0),
        stable_case_passes=sum(1 for case in cases if case.pass_rate == 1.0),
        unstable_cases=unstable_cases,
        case_pass_rate=_ratio(passed_case_runs, total_case_runs),
        run_pass_rate=_ratio(sum(1 for run in runs if run.failed_cases == 0), len(runs)),
        all_runs_passed=all(run.failed_cases == 0 for run in runs),
    )


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 3)


def _dedupe_preserve_order(items: list[Any]) -> list[Any]:
    seen: list[Any] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def _tier_signature(tiers: list[int]) -> str:
    return ",".join(str(item) for item in tiers) or "-"


def _resolve_consistency_output_root(*, mode: str, output_root: str | Path | None, run_id: str) -> Path:
    if output_root is not None:
        return Path(output_root)
    if mode == "live":
        return Path("eval/results/live") / f"{run_id}-repeat"
    return Path("eval/results/repeated") / run_id


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
            stderr=f"Live role command timed out after {timeout_text} seconds.",
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
    raise ValueError(f"Could not parse a JSON object from backend output: {text[:200]!r}")


def _fixture_agents(case: BenchmarkCase) -> FixtureAgents:
    def generator(request: GenerationRequest) -> CandidateSolution:
        if case.scenario == "orchestration_fanout_threshold":
            if request.branch_strategy is BranchStrategy.PRIMARY:
                hypothesis = (
                    "The surface-code threshold claim follows from a generic unsupported threshold-theorem inference."
                )
            elif request.branch_strategy is BranchStrategy.ALTERNATIVE_APPROACH:
                hypothesis = "The surface code has a threshold under standard depolarizing noise assumptions."
            else:
                hypothesis = "The threshold claim should be decomposed into smaller literature-backed subclaims."
            return CandidateSolution(
                hypothesis=hypothesis,
                approach="Evaluate the claim against the deterministic orchestration fixture.",
                technical_details=[f"Scenario fixture: {case.scenario} on {request.branch_strategy.value}."],
                expected_results=["The benchmark verdict should match the known answer for this case."],
                assumptions=["The deterministic fixture encodes the intended orchestration ground truth."],
                limitations=["This release benchmark uses fixture agents instead of live Hermes subagents."],
                references=["Fowler et al. 2012", "Dennis et al. 2002"],
                revision_notes=[],
            )
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
        if case.scenario == "orchestration_fanout_threshold" and request.branch_strategy is BranchStrategy.PRIMARY:
            return CandidateSolution(
                hypothesis="The surface-code threshold claim still relies on an unsupported generic threshold-theorem inference.",
                approach="Patch the original unsupported argument without changing its core basis.",
                technical_details=["The revision keeps leaning on the same unsupported theorem-level shortcut."],
                expected_results=["The verifier should still reject the candidate and trigger fan-out."],
                assumptions=["The benchmark fixture expects the primary path to remain unsupported."],
                limitations=["This fixture revision intentionally fails to repair the core flaw."],
                references=["Dennis et al. 2002"],
                revision_notes=["Retried the same unsupported inference without changing the approach."],
            )
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
                if request.analysis_results is None:
                    return _analysis_request_report(
                        reason="Empirical confirmation is required for the quantitative claim.",
                        adapter_family="qec_decoder_benchmark",
                        analysis_kind="rotated_surface_code_memory",
                        distance=[3, 5],
                        error_rate=0.001,
                    )
                return _verified_with_tier2(
                    request.analysis_results,
                    "The simulated trend supports the claimed logical-error behavior.",
                )
            case "simulation_rejected_distance7":
                if request.analysis_results is None:
                    return _analysis_request_report(
                        reason="Empirical confirmation is required for the quantitative claim.",
                        adapter_family="qec_decoder_benchmark",
                        analysis_kind="rotated_surface_code_memory",
                        distance=[5, 7],
                        error_rate=0.005,
                    )
                return _flawed_with_tier2(
                    request.analysis_results,
                    "The simulated logical error rate does not support the claim.",
                )
            case "symbolic_verified_equivalence":
                if request.analysis_results is None:
                    return _analysis_request_report_generic(
                        reason="A symbolic equivalence check is required for the algebraic claim.",
                        adapter_family="symbolic_math",
                        analysis_kind="expression_equivalence",
                        task={"lhs": "(x + 1)**2", "rhs": "x**2 + 2*x + 1"},
                    )
                return _verified_with_tier2(request.analysis_results, "The symbolic analysis confirms the identity.")
            case "symbolic_rejected_derivative":
                if request.analysis_results is None:
                    return _analysis_request_report_generic(
                        reason="A symbolic derivative check is required for the calculus claim.",
                        adapter_family="symbolic_math",
                        analysis_kind="derivative_check",
                        task={
                            "expression": "x**3",
                            "symbol": "x",
                            "expected_derivative": "2*x**2",
                        },
                    )
                return _flawed_with_tier2(request.analysis_results, "The symbolic derivative does not match the claim.")
            case "optimization_verified_linear_program":
                if request.analysis_results is None:
                    return _analysis_request_report_generic(
                        reason="A solver-backed optimum check is required for the optimization claim.",
                        adapter_family="optimization",
                        analysis_kind="linear_program",
                        task={
                            "objective": [1, 2],
                            "goal": "min",
                            "A_ub": [[-1, -1]],
                            "b_ub": [-3],
                            "bounds": [[0, None], [0, None]],
                        },
                    )
                return _verified_with_tier2(request.analysis_results, "The optimization analysis confirms the optimum claim.")
            case "optimization_rejected_assignment":
                if request.analysis_results is None:
                    return _analysis_request_report_generic(
                        reason="A solver-backed assignment check is required for the combinatorial claim.",
                        adapter_family="optimization",
                        analysis_kind="assignment_problem",
                        task={"cost_matrix": [[4, 1], [2, 3]]},
                    )
                return _flawed_with_tier2(request.analysis_results, "The assignment optimum does not match the claim.")
            case "dynamics_verified_decay":
                if request.analysis_results is None:
                    return _analysis_request_report_generic(
                        reason="Numerical integration is required for the dynamics claim.",
                        adapter_family="dynamics",
                        analysis_kind="ode_final_value",
                        task={
                            "equation": "exponential_decay",
                            "initial": 1.0,
                            "rate": 1.0,
                            "t_span": [0.0, 2.0],
                            "sample_times": [0.0, 1.0, 2.0],
                        },
                    )
                return _verified_with_tier2(request.analysis_results, "The dynamics analysis confirms the decay trend.")
            case "mbqc_verified_graphix_pattern":
                if request.analysis_results is None:
                    return _analysis_request_report_generic(
                        reason="Graph-state transpilation is required for the MBQC claim.",
                        adapter_family="mbqc_graph_state",
                        analysis_kind="transpile_pattern",
                        task={"qubits": 2, "gates": [{"gate": "h", "qubit": 0}, {"gate": "h", "qubit": 1}]},
                    )
                return _verified_with_tier2(request.analysis_results, "The MBQC analysis confirms the pattern construction.")
            case "photonic_verified_basic_state":
                if request.analysis_results is None:
                    return _analysis_request_report_generic(
                        reason="A photonic state check is required for the linear-optics claim.",
                        adapter_family="photonic_linear_optics",
                        analysis_kind="basic_state_summary",
                        task={"input_state": [1, 0], "modes": 2, "processor_backend": "SLOS"},
                    )
                return _verified_with_tier2(request.analysis_results, "The photonic analysis confirms the mode and photon counts.")
            case "neutral_atom_verified_register":
                if request.analysis_results is None:
                    return _analysis_request_report_generic(
                        reason="A neutral-atom register construction check is required for the control claim.",
                        adapter_family="neutral_atom_control",
                        analysis_kind="register_sequence_summary",
                        task={"layout": "square", "side": 2, "spacing": 5.0},
                    )
                return _verified_with_tier2(request.analysis_results, "The neutral-atom analysis confirms the register construction.")
            case "tqec_verified_gallery_block_graph":
                if request.analysis_results is None:
                    return _analysis_request_report_generic(
                        reason="A topological-QEC design check is required for the block-graph claim.",
                        adapter_family="topological_qec_design",
                        analysis_kind="gallery_block_graph",
                        task={
                            "gallery_module": "tqec.gallery.steane_encoding",
                            "gallery_function": "steane_encoding",
                        },
                    )
                return _verified_with_tier2(request.analysis_results, "The tqec gallery analysis confirms the block-graph construction.")
            case "zx_verified_qasm_rewrite":
                if request.analysis_results is None:
                    return _analysis_request_report_generic(
                        reason="A ZX rewrite check is required for the circuit-equivalence claim.",
                        adapter_family="zx_rewrite_verification",
                        analysis_kind="qasm_rewrite_summary",
                        task={
                            "qasm": "OPENQASM 2.0; include \"qelib1.inc\"; qreg q[1]; h q[0]; h q[0];"
                        },
                    )
                return _verified_with_tier2(request.analysis_results, "The ZX rewrite confirms the circuit-equivalence claim.")
            case "formal_proved_repetition_majority":
                if request.formal_results is None:
                    return _formal_request_report(
                        "For every odd repetition-code distance d, majority decoding corrects up to (d-1)/2 bit flips.",
                        backend=case.formal_backend or "aristotle",
                    )
                return _verified_with_tier3(
                    list(request.formal_results),
                    "The formal result confirms the benchmark theorem statement.",
                )
            case "formal_unavailable_repetition_scaling":
                if request.formal_results is None:
                    return _formal_request_report(
                        "For the repetition code of odd distance d, the logical error rate is O(p^((d+1)/2)).",
                        backend=case.formal_backend or "aristotle",
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
            case "formal_mathcode_nat_add_zero":
                if request.formal_results is None:
                    return _formal_request_report(
                        "For every natural number n, 0 + n = n.",
                        backend=case.formal_backend or "mathcode",
                    )
                return _verified_with_tier3(
                    list(request.formal_results),
                    "The MathCode-backed formal result confirms the natural-number identity.",
                )
            case "orchestration_fanout_threshold":
                if (
                    "threshold-theorem inference" in request.candidate.hypothesis
                    and "unsupported" in request.candidate.hypothesis
                ):
                    return _flawed_tier1_report("The candidate keeps relying on the same unsupported threshold shortcut.")
                return _verified_tier1_report(
                    "The alternative literature-grounded branch matches the benchmark ground truth."
                )
            case _:
                raise ValueError(f"Unknown benchmark scenario {case.scenario!r}.")

    def analyzer(request: AnalysisRequest) -> AnalysisResults:
        if case.scenario == "simulation_verified_distance5":
            return AnalysisResults(
                adapter_family="qec_decoder_benchmark",
                analysis_kind=request.analysis_spec.analysis_kind,
                adapter_name="qec_decoder_benchmark",
                adapter_version="0.1.0",
                timestamp=_DETERMINISTIC_TIMESTAMP,
                runtime_seconds=0.2,
                backend=Backend.LOCAL,
                summary="The deterministic QEC analysis supports the distance-ordering claim.",
                measurements=[
                    AnalysisMeasurement(
                        name="threshold_estimate",
                        value=0.001,
                        unit="",
                        metadata={"method": "fixture_supports_claim", "below_threshold_distances": [5]},
                    )
                ],
                details={"engine": "stim", "fixture": case.scenario},
                errors=[],
            )
        if case.scenario == "simulation_rejected_distance7":
            return AnalysisResults(
                adapter_family="qec_decoder_benchmark",
                analysis_kind=request.analysis_spec.analysis_kind,
                adapter_name="qec_decoder_benchmark",
                adapter_version="0.1.0",
                timestamp=_DETERMINISTIC_TIMESTAMP,
                runtime_seconds=0.2,
                backend=Backend.LOCAL,
                summary="The deterministic QEC analysis refutes the target logical-error claim.",
                measurements=[
                    AnalysisMeasurement(
                        name="threshold_estimate",
                        value=0.005,
                        unit="",
                        metadata={"method": "fixture_refutes_claim", "below_threshold_distances": []},
                    )
                ],
                details={"engine": "stim", "fixture": case.scenario},
                errors=[],
            )
        if case.scenario == "symbolic_verified_equivalence":
            return _fixture_analysis_results(
                "symbolic_math",
                "expression_equivalence",
                "The symbolic expressions simplify to the same form.",
                [AnalysisMeasurement(name="equivalent", value=True, unit="", metadata={})],
            )
        if case.scenario == "symbolic_rejected_derivative":
            return _fixture_analysis_results(
                "symbolic_math",
                "derivative_check",
                "The claimed derivative is incorrect.",
                [AnalysisMeasurement(name="derivative_matches", value=False, unit="", metadata={})],
            )
        if case.scenario == "optimization_verified_linear_program":
            return _fixture_analysis_results(
                "optimization",
                "linear_program",
                "The linear program optimum is 3.",
                [AnalysisMeasurement(name="objective_value", value=3.0, unit="", metadata={})],
            )
        if case.scenario == "optimization_rejected_assignment":
            return _fixture_analysis_results(
                "optimization",
                "assignment_problem",
                "The assignment optimum is 3, not the claimed higher value.",
                [AnalysisMeasurement(name="objective_value", value=3, unit="", metadata={})],
            )
        if case.scenario == "dynamics_verified_decay":
            return _fixture_analysis_results(
                "dynamics",
                "ode_final_value",
                "The exponential-decay final value is below the claimed threshold.",
                [AnalysisMeasurement(name="final_value", value=0.1353, unit="", metadata={})],
            )
        if case.scenario == "mbqc_verified_graphix_pattern":
            return _fixture_analysis_results(
                "mbqc_graph_state",
                "transpile_pattern",
                "The Graphix transpilation produced a non-empty measurement pattern.",
                [AnalysisMeasurement(name="command_count", value=6, unit="", metadata={})],
            )
        if case.scenario == "photonic_verified_basic_state":
            return _fixture_analysis_results(
                "photonic_linear_optics",
                "basic_state_summary",
                "The photonic input state has one photon over two modes.",
                [AnalysisMeasurement(name="photon_count", value=1, unit="", metadata={})],
            )
        if case.scenario == "neutral_atom_verified_register":
            return _fixture_analysis_results(
                "neutral_atom_control",
                "register_sequence_summary",
                "The Pulser-style register contains four qubits.",
                [AnalysisMeasurement(name="qubit_count", value=4, unit="", metadata={})],
            )
        if case.scenario == "tqec_verified_gallery_block_graph":
            return _fixture_analysis_results(
                "topological_qec_design",
                "gallery_block_graph",
                "The tqec gallery graph exposes correlation surfaces.",
                [AnalysisMeasurement(name="correlation_surface_count", value=7, unit="", metadata={})],
            )
        if case.scenario == "zx_verified_qasm_rewrite":
            return _fixture_analysis_results(
                "zx_rewrite_verification",
                "qasm_rewrite_summary",
                "The ZX rewrite preserves the circuit while reducing the two-qubit count.",
                [
                    AnalysisMeasurement(name="two_qubit_count_before", value=0, unit="", metadata={}),
                    AnalysisMeasurement(name="two_qubit_count_after", value=0, unit="", metadata={}),
                    AnalysisMeasurement(name="equivalent", value=True, unit="", metadata={}),
                ],
            )
        raise ValueError(f"Unexpected analysis-adapter call for {case.scenario!r}.")

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
        if case.scenario == "formal_mathcode_nat_add_zero":
            return [
                Tier3ClaimResult(
                    claim=request.claims[0].claim,
                    backend=request.backend,
                    proof_status=ProofStatus.PROVED,
                    details="The benchmark fixture marks the MathCode theorem as proved.",
                    lean_code="theorem zero_add_nat (n : Nat) : 0 + n = n := by simp",
                    proof_time_seconds=0.8,
                )
            ]
        raise ValueError(f"Unexpected formal verifier call for {case.scenario!r}.")

    return FixtureAgents(
        generator=generator,
        verifier=verifier,
        reviser=reviser,
        analyzer=analyzer if 2 in case.expected_tiers else None,
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
        case "symbolic_verified_equivalence":
            return "The identity (x + 1)^2 = x^2 + 2x + 1 holds exactly."
        case "symbolic_rejected_derivative":
            return "The derivative of x^3 is 2x^2."
        case "optimization_verified_linear_program":
            return "The optimum of the benchmark linear program is 3."
        case "optimization_rejected_assignment":
            return "The benchmark assignment problem has optimum cost 7."
        case "dynamics_verified_decay":
            return "An exponential decay with rate 1 reaches a value below 0.2 by t = 2."
        case "mbqc_verified_graphix_pattern":
            return "A simple two-qubit Clifford circuit transpiles to a non-empty MBQC pattern."
        case "photonic_verified_basic_state":
            return "The benchmark photonic state contains one photon over two modes."
        case "neutral_atom_verified_register":
            return "A 2x2 neutral-atom square register contains four qubits."
        case "tqec_verified_gallery_block_graph":
            return "The tqec Steane-encoding gallery graph exposes non-zero correlation surfaces."
        case "zx_verified_qasm_rewrite":
            return "Applying H twice on one qubit is ZX-equivalent to the identity."
        case "formal_proved_repetition_majority":
            return "Majority decoding for odd repetition codes corrects up to (d-1)/2 bit flips."
        case "formal_unavailable_repetition_scaling":
            return "The repetition-code logical error rate scales as O(p^((d+1)/2))."
        case "formal_mathcode_nat_add_zero":
            return "For every natural number n, 0 + n = n."
        case "orchestration_fanout_threshold":
            return "The surface-code threshold claim follows from a generic unsupported threshold-theorem inference."
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


def _analysis_request_report(
    *,
    reason: str,
    adapter_family: str,
    analysis_kind: str,
    distance: list[int],
    error_rate: float,
) -> VerificationReport:
    flaw = "Tier 2 analysis evidence is required before accepting the quantitative claim."
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
            analysis_requested=True,
            reason=reason,
            analysis_spec={
                "adapter_family": adapter_family,
                "analysis_kind": analysis_kind,
                "task": {
                    "engine": "stim",
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


def _analysis_request_report_generic(
    *,
    reason: str,
    adapter_family: str,
    analysis_kind: str,
    task: dict[str, Any],
) -> VerificationReport:
    flaw = "Tier 2 analysis evidence is required before accepting the claim."
    return VerificationReport(
        verdict=VerificationVerdict.FLAWS_FOUND,
        tier1=Tier1Report(
            checks=[
                AnalyticalCheck(
                    check="computational_support",
                    status=AnalyticalStatus.UNCERTAIN,
                    detail="The benchmark case requires a Tier 2 analysis adapter check.",
                )
            ],
            overall=VerificationVerdict.FLAWS_FOUND,
            flaws=[flaw],
            caveats=[],
        ),
        tier2=Tier2Report(
            analysis_requested=True,
            reason=reason,
            analysis_spec={
                "adapter_family": adapter_family,
                "analysis_kind": analysis_kind,
                "task": task,
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


def _fixture_analysis_results(
    adapter_family: str,
    analysis_kind: str,
    summary: str,
    measurements: list[AnalysisMeasurement],
    *,
    details: dict[str, Any] | None = None,
) -> AnalysisResults:
    return AnalysisResults(
        adapter_family=adapter_family,
        analysis_kind=analysis_kind,
        adapter_name=adapter_family,
        adapter_version="0.1.0",
        timestamp=_DETERMINISTIC_TIMESTAMP,
        runtime_seconds=0.2,
        backend=Backend.LOCAL,
        summary=summary,
        measurements=measurements,
        details=dict(details or {}),
        errors=[],
    )


def _verified_with_tier2(analysis_results: AnalysisResults, interpretation: str) -> VerificationReport:
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
            analysis_requested=True,
            reason="The quantitative claim requires empirical confirmation.",
            analysis_spec=None,
            results=analysis_results.to_dict(),
            interpretation=interpretation,
        ),
        tier3=[],
        flaws=[],
        caveats=[],
        cannot_verify_reason=None,
    )


def _flawed_with_tier2(analysis_results: AnalysisResults, interpretation: str) -> VerificationReport:
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
            analysis_requested=True,
            reason="The quantitative claim requires empirical confirmation.",
            analysis_spec=None,
            results=analysis_results.to_dict(),
            interpretation=interpretation,
        ),
        tier3=[],
        flaws=[flaw],
        caveats=[],
        cannot_verify_reason=None,
    )


def _formal_request_report(claim: str, *, backend: str = "aristotle") -> VerificationReport:
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
                backend=backend,
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
