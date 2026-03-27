from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Protocol

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
from .formal import FormalVerificationRequest, FormalVerifier
from .probes import probe_model_routing
from .tier1 import (
    GenerationRequest,
    RevisionRequest,
    SessionStore,
    SimulationRequest,
    Tier1LoopRunner,
    VerificationRequest,
)


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
    notes: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BenchmarkCaseResult":
        return cls(
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
    generated_at: str
    suite_path: str
    routing_probe_status: ProbeStatus
    cases: list[BenchmarkCaseResult]
    summary: BenchmarkSummary

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BenchmarkReport":
        return cls(
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


def load_benchmark_suite(path: str | Path) -> list[BenchmarkCase]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [BenchmarkCase.from_dict(item) for item in payload]


def run_benchmark_suite(
    suite_path: str | Path,
    *,
    routing_probe: CapabilityProbeResult | None = None,
) -> BenchmarkReport:
    suite_file = Path(suite_path)
    benchmark_cases = load_benchmark_suite(suite_file)
    probe = routing_probe or probe_model_routing()
    with TemporaryDirectory() as tmpdir:
        evidence_root = Path(tmpdir) / "sessions"
        results = [
            _run_benchmark_case(case, evidence_root=evidence_root, routing_probe=probe)
            for case in benchmark_cases
        ]

    return BenchmarkReport(
        generated_at="2026-03-26T00:00:00Z",
        suite_path=_display_path(suite_file),
        routing_probe_status=probe.status,
        cases=results,
        summary=_summarize_results(results),
    )


def write_benchmark_report(report: BenchmarkReport, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")


def _run_benchmark_case(
    case: BenchmarkCase,
    *,
    evidence_root: Path,
    routing_probe: CapabilityProbeResult,
) -> BenchmarkCaseResult:
    config = DeepGvrConfig()
    config.evidence.directory = str(evidence_root / case.id)
    config.loop.max_iterations = 1
    config.verification.tier3.enabled = True
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
        notes=notes,
    )


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


def _display_path(path: Path) -> str:
    repo_root = Path(__file__).resolve().parents[2]
    try:
        return path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


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
                timestamp="2026-03-26T00:00:00Z",
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
                timestamp="2026-03-26T00:00:00Z",
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


def benchmark_routing_probe(status: ProbeStatus) -> CapabilityProbeResult:
    return CapabilityProbeResult(
        name="per_subagent_model_routing",
        status=status,
        summary="Benchmark routing probe override.",
        preferred_outcome="Route generator and verifier to distinct providers or models.",
        fallback="Use prompt separation plus temperature decorrelation and record the limitation.",
        details={"source": "benchmark_fixture"},
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
