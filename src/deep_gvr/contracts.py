from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


def _serialize(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {key: _serialize(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    return value


class Backend(StrEnum):
    LOCAL = "local"
    MODAL = "modal"
    SSH = "ssh"


class VerificationVerdict(StrEnum):
    VERIFIED = "VERIFIED"
    FLAWS_FOUND = "FLAWS_FOUND"
    CANNOT_VERIFY = "CANNOT_VERIFY"


class AnalyticalStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNCERTAIN = "uncertain"


class ProbeStatus(StrEnum):
    READY = "ready"
    FALLBACK = "fallback"
    BLOCKED = "blocked"


class ReleaseCheckStatus(StrEnum):
    READY = "ready"
    ATTENTION = "attention"
    BLOCKED = "blocked"


class RoutingMode(StrEnum):
    DIRECT = "direct"
    TEMPERATURE_DECORRELATION = "temperature_decorrelation"


class BranchStrategy(StrEnum):
    PRIMARY = "primary"
    ALTERNATIVE_APPROACH = "alternative_approach"
    DECOMPOSITION = "decomposition"


class BranchStatus(StrEnum):
    ACTIVE = "active"
    QUEUED = "queued"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class EscalationAction(StrEnum):
    FANOUT = "fanout"
    SWITCH_BRANCH = "switch_branch"
    HALT = "halt"


class ProofStatus(StrEnum):
    REQUESTED = "requested"
    PENDING = "pending"
    PROVED = "proved"
    DISPROVED = "disproved"
    TIMEOUT = "timeout"
    ERROR = "error"
    UNAVAILABLE = "unavailable"


_SIM_NOISE_MODEL_ALIASES = {
    "depolarizing": "depolarizing",
    "uniform_depolarizing": "depolarizing",
    "iid_depolarizing": "depolarizing",
}
_SIM_MAX_SHOTS_PER_POINT = 100_000
_SIM_MAX_PARALLEL = 4
_ANALYSIS_MAX_PARALLEL = 4


def _normalize_sim_noise_model(value: str) -> str:
    normalized = value.strip().lower()
    return _SIM_NOISE_MODEL_ALIASES.get(normalized, normalized)


def _bounded_positive_int(value: Any, *, maximum: int) -> int:
    return max(1, min(int(value), maximum))


@dataclass(slots=True)
class ModelSelection:
    provider: str = "default"
    model: str = ""


@dataclass(slots=True)
class LoopConfig:
    max_iterations: int = 3
    alternative_approach: bool = True
    max_alternatives: int = 2


@dataclass(slots=True)
class TierToggleConfig:
    enabled: bool = True


@dataclass(slots=True)
class SSHConfig:
    host: str = ""
    user: str = ""
    key_path: str = ""
    remote_workspace: str = ""
    python_bin: str = "python3"


@dataclass(slots=True)
class ModalConfig:
    cli_bin: str = "modal"
    stub_path: str = "adapters/modal_stubs/stim_modal.py"


@dataclass(slots=True)
class Tier2Config:
    enabled: bool = True
    default_adapter_family: str = "qec_decoder_benchmark"
    default_backend: Backend = Backend.LOCAL
    timeout_seconds: int = 3600
    modal: ModalConfig = field(default_factory=ModalConfig)
    ssh: SSHConfig = field(default_factory=SSHConfig)


@dataclass(slots=True)
class MathCodeConfig:
    root: str = "~/dev/mathcode"
    run_script: str = "~/dev/mathcode/run"


@dataclass(slots=True)
class Tier3Config:
    enabled: bool = False
    backend: str = "aristotle"
    timeout_seconds: int = 300
    mathcode: MathCodeConfig = field(default_factory=MathCodeConfig)


@dataclass(slots=True)
class VerificationConfig:
    tier1: TierToggleConfig = field(default_factory=TierToggleConfig)
    tier2: Tier2Config = field(default_factory=Tier2Config)
    tier3: Tier3Config = field(default_factory=Tier3Config)


@dataclass(slots=True)
class ModelsConfig:
    orchestrator: ModelSelection = field(default_factory=ModelSelection)
    generator: ModelSelection = field(default_factory=lambda: ModelSelection(provider="openrouter"))
    verifier: ModelSelection = field(default_factory=lambda: ModelSelection(provider="openrouter"))
    reviser: ModelSelection = field(default_factory=ModelSelection)


@dataclass(slots=True)
class EvidenceConfig:
    directory: str = "~/.hermes/deep-gvr/sessions"
    persist_to_memory: bool = True


@dataclass(slots=True)
class DomainConfig:
    default: str = "qec"
    context_file: str = ""


@dataclass(slots=True)
class DeepGvrConfig:
    loop: LoopConfig = field(default_factory=LoopConfig)
    verification: VerificationConfig = field(default_factory=VerificationConfig)
    models: ModelsConfig = field(default_factory=ModelsConfig)
    evidence: EvidenceConfig = field(default_factory=EvidenceConfig)
    domain: DomainConfig = field(default_factory=DomainConfig)

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeepGvrConfig":
        verification = data["verification"]
        tier2 = verification["tier2"]
        modal = tier2.get("modal") or {}
        ssh = tier2.get("ssh") or {}
        default_adapter_family = tier2.get("default_adapter_family") or tier2.get("default_simulator") or "qec_decoder_benchmark"
        return cls(
            loop=LoopConfig(
                max_iterations=int(data["loop"]["max_iterations"]),
                alternative_approach=bool(data["loop"]["alternative_approach"]),
                max_alternatives=int(data["loop"]["max_alternatives"]),
            ),
            verification=VerificationConfig(
                tier1=TierToggleConfig(enabled=bool(verification["tier1"]["enabled"])),
                tier2=Tier2Config(
                    enabled=bool(tier2["enabled"]),
                    default_adapter_family=default_adapter_family,
                    default_backend=Backend(tier2["default_backend"]),
                    timeout_seconds=int(tier2["timeout_seconds"]),
                    modal=ModalConfig(
                        cli_bin=modal.get("cli_bin", "modal"),
                        stub_path=modal.get("stub_path", "adapters/modal_stubs/stim_modal.py"),
                    ),
                    ssh=SSHConfig(
                        host=ssh.get("host", ""),
                        user=ssh.get("user", ""),
                        key_path=ssh.get("key_path", ""),
                        remote_workspace=ssh.get("remote_workspace", ""),
                        python_bin=ssh.get("python_bin", "python3"),
                    ),
                ),
                tier3=Tier3Config(
                    enabled=bool(verification["tier3"]["enabled"]),
                    backend=verification["tier3"]["backend"],
                    timeout_seconds=int(verification["tier3"]["timeout_seconds"]),
                    mathcode=MathCodeConfig(
                        root=verification["tier3"].get("mathcode", {}).get("root", "~/dev/mathcode"),
                        run_script=verification["tier3"].get("mathcode", {}).get("run_script", "~/dev/mathcode/run"),
                    ),
                ),
            ),
            models=ModelsConfig(
                orchestrator=ModelSelection(**data["models"].get("orchestrator", {})),
                generator=ModelSelection(**data["models"]["generator"]),
                verifier=ModelSelection(**data["models"]["verifier"]),
                reviser=ModelSelection(**data["models"]["reviser"]),
            ),
            evidence=EvidenceConfig(
                directory=data["evidence"]["directory"],
                persist_to_memory=bool(data["evidence"]["persist_to_memory"]),
            ),
            domain=DomainConfig(
                default=data["domain"]["default"],
                context_file=data["domain"]["context_file"],
            ),
        )


@dataclass(slots=True)
class CandidateSolution:
    hypothesis: str
    approach: str
    technical_details: list[str]
    expected_results: list[str]
    assumptions: list[str]
    limitations: list[str]
    references: list[str]
    revision_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CandidateSolution":
        return cls(
            hypothesis=data["hypothesis"],
            approach=data["approach"],
            technical_details=list(data["technical_details"]),
            expected_results=list(data["expected_results"]),
            assumptions=list(data["assumptions"]),
            limitations=list(data["limitations"]),
            references=list(data["references"]),
            revision_notes=list(data.get("revision_notes", [])),
        )


@dataclass(slots=True)
class AnalyticalCheck:
    check: str
    status: AnalyticalStatus
    detail: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalyticalCheck":
        return cls(
            check=data["check"],
            status=AnalyticalStatus(data["status"]),
            detail=data["detail"],
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class Tier1Report:
    checks: list[AnalyticalCheck]
    overall: VerificationVerdict
    flaws: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Tier1Report":
        return cls(
            checks=[AnalyticalCheck.from_dict(item) for item in data["checks"]],
            overall=VerificationVerdict(data["overall"]),
            flaws=list(data.get("flaws", [])),
            caveats=list(data.get("caveats", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class Tier2Report:
    analysis_requested: bool
    reason: str
    analysis_spec: dict[str, Any] | None = None
    results: dict[str, Any] | None = None
    interpretation: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Tier2Report":
        analysis_requested = data.get("analysis_requested")
        if analysis_requested is None:
            analysis_requested = data.get("simulation_requested", False)
        analysis_spec = data.get("analysis_spec")
        if analysis_spec is None:
            analysis_spec = data.get("simulation_spec")
        return cls(
            analysis_requested=bool(analysis_requested),
            reason=data["reason"],
            analysis_spec=analysis_spec,
            results=data.get("results"),
            interpretation=data.get("interpretation"),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)

    @property
    def simulation_requested(self) -> bool:
        return self.analysis_requested

    @property
    def simulation_spec(self) -> dict[str, Any] | None:
        return self.analysis_spec


@dataclass(slots=True)
class Tier3ClaimResult:
    claim: str
    backend: str
    proof_status: ProofStatus
    details: str
    lean_code: str = ""
    proof_time_seconds: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Tier3ClaimResult":
        claim = data.get("claim") or data.get("statement") or data.get("obligation")
        if claim is None:
            raise KeyError("claim")
        return cls(
            claim=claim,
            backend=data.get("backend", "aristotle"),
            proof_status=ProofStatus(data.get("proof_status", ProofStatus.REQUESTED.value)),
            details=data.get("details") or data.get("reason") or data.get("proof_obligation", ""),
            lean_code=data.get("lean_code", ""),
            proof_time_seconds=float(data["proof_time_seconds"]) if data.get("proof_time_seconds") is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class FormalProofHandle:
    claim: str
    backend: str
    project_id: str
    transport: str
    proof_status: ProofStatus
    submitted_at: str
    last_polled_at: str | None = None
    poll_count: int = 0
    details: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FormalProofHandle":
        return cls(
            claim=data["claim"],
            backend=data.get("backend", "aristotle"),
            project_id=data["project_id"],
            transport=data["transport"],
            proof_status=ProofStatus(data.get("proof_status", ProofStatus.PENDING.value)),
            submitted_at=data["submitted_at"],
            last_polled_at=data.get("last_polled_at"),
            poll_count=int(data.get("poll_count", 0)),
            details=data.get("details", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class FormalProofLifecycle:
    backend: str
    transport: str
    proof_status: ProofStatus
    handles: list[FormalProofHandle]
    last_transition: str
    details: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FormalProofLifecycle":
        return cls(
            backend=data.get("backend", "aristotle"),
            transport=data["transport"],
            proof_status=ProofStatus(data.get("proof_status", ProofStatus.PENDING.value)),
            handles=[FormalProofHandle.from_dict(item) for item in data.get("handles", [])],
            last_transition=data["last_transition"],
            details=data.get("details", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class VerificationReport:
    verdict: VerificationVerdict
    tier1: Tier1Report
    tier2: Tier2Report | None = None
    tier3: list[Tier3ClaimResult] = field(default_factory=list)
    flaws: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    cannot_verify_reason: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VerificationReport":
        return cls(
            verdict=VerificationVerdict(data["verdict"]),
            tier1=Tier1Report.from_dict(data["tier1"]),
            tier2=Tier2Report.from_dict(data["tier2"]) if data.get("tier2") else None,
            tier3=[Tier3ClaimResult.from_dict(item) for item in data.get("tier3", [])],
            flaws=list(data.get("flaws", [])),
            caveats=list(data.get("caveats", [])),
            cannot_verify_reason=data.get("cannot_verify_reason"),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class AnalysisResources:
    timeout_seconds: int
    max_parallel: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalysisResources":
        return cls(
            timeout_seconds=int(data["timeout_seconds"]),
            max_parallel=_bounded_positive_int(data["max_parallel"], maximum=_ANALYSIS_MAX_PARALLEL),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class AnalysisSpec:
    adapter_family: str
    analysis_kind: str
    task: dict[str, Any]
    resources: AnalysisResources

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalysisSpec":
        return cls(
            adapter_family=data.get("adapter_family") or data.get("simulator") or "qec_decoder_benchmark",
            analysis_kind=data.get("analysis_kind") or data.get("task", {}).get("task_type") or "analysis",
            task=dict(data["task"]),
            resources=AnalysisResources.from_dict(data["resources"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)

    @property
    def simulator(self) -> str:
        return self.adapter_family


@dataclass(slots=True)
class AnalysisMeasurement:
    name: str
    value: str | int | float | bool | None
    unit: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalysisMeasurement":
        return cls(
            name=data["name"],
            value=data.get("value"),
            unit=data.get("unit", ""),
            metadata=dict(data.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class AnalysisResults:
    adapter_family: str
    analysis_kind: str
    adapter_name: str
    adapter_version: str
    timestamp: str
    runtime_seconds: float
    backend: Backend
    summary: str
    measurements: list[AnalysisMeasurement]
    details: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalysisResults":
        return cls(
            adapter_family=data.get("adapter_family") or data.get("simulator") or "qec_decoder_benchmark",
            analysis_kind=data.get("analysis_kind") or data.get("details", {}).get("task_type") or "analysis",
            adapter_name=data.get("adapter_name") or data.get("simulator") or "",
            adapter_version=data["adapter_version"],
            timestamp=data["timestamp"],
            runtime_seconds=float(data["runtime_seconds"]),
            backend=Backend(data["backend"]),
            summary=data.get("summary", ""),
            measurements=[AnalysisMeasurement.from_dict(item) for item in data.get("measurements", [])],
            details=dict(data.get("details", {})),
            errors=list(data.get("errors", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)

    @property
    def simulator(self) -> str:
        return self.adapter_family


@dataclass(slots=True)
class SimTask:
    code: str
    task_type: str
    distance: list[int]
    rounds_per_distance: str
    noise_model: str
    error_rates: list[float]
    decoder: str
    shots_per_point: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimTask":
        return cls(
            code=data["code"],
            task_type=data["task_type"],
            distance=[int(item) for item in data["distance"]],
            rounds_per_distance=data["rounds_per_distance"],
            noise_model=_normalize_sim_noise_model(data["noise_model"]),
            error_rates=[float(item) for item in data["error_rates"]],
            decoder=data["decoder"],
            shots_per_point=_bounded_positive_int(data["shots_per_point"], maximum=_SIM_MAX_SHOTS_PER_POINT),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class SimResources:
    timeout_seconds: int
    max_parallel: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimResources":
        return cls(
            timeout_seconds=int(data["timeout_seconds"]),
            max_parallel=_bounded_positive_int(data["max_parallel"], maximum=_SIM_MAX_PARALLEL),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class SimSpec:
    simulator: str
    task: SimTask
    resources: SimResources

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimSpec":
        return cls(
            simulator=data["simulator"],
            task=SimTask.from_dict(data["task"]),
            resources=SimResources.from_dict(data["resources"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class SimDataPoint:
    distance: int
    rounds: int
    physical_error_rate: float
    logical_error_rate: float
    shots: int
    errors_observed: int
    decoder: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimDataPoint":
        return cls(
            distance=int(data["distance"]),
            rounds=int(data["rounds"]),
            physical_error_rate=float(data["physical_error_rate"]),
            logical_error_rate=float(data["logical_error_rate"]),
            shots=int(data["shots"]),
            errors_observed=int(data["errors_observed"]),
            decoder=data["decoder"],
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class SimAnalysis:
    threshold_estimate: float | None
    threshold_method: str
    below_threshold_distances: list[int]
    scaling_exponent: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimAnalysis":
        return cls(
            threshold_estimate=float(data["threshold_estimate"]) if data.get("threshold_estimate") is not None else None,
            threshold_method=data["threshold_method"],
            below_threshold_distances=[int(item) for item in data.get("below_threshold_distances", [])],
            scaling_exponent=float(data["scaling_exponent"]) if data.get("scaling_exponent") is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class SimResults:
    simulator: str
    adapter_version: str
    timestamp: str
    runtime_seconds: float
    backend: Backend
    data: list[SimDataPoint]
    analysis: SimAnalysis
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimResults":
        return cls(
            simulator=data["simulator"],
            adapter_version=data["adapter_version"],
            timestamp=data["timestamp"],
            runtime_seconds=float(data["runtime_seconds"]),
            backend=Backend(data["backend"]),
            data=[SimDataPoint.from_dict(item) for item in data.get("data", [])],
            analysis=SimAnalysis.from_dict(data["analysis"]),
            errors=list(data.get("errors", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class HypothesisBranch:
    branch_id: str
    strategy: BranchStrategy
    status: BranchStatus
    rationale: str
    parent_branch_id: str | None = None
    created_iteration: int = 0
    activated_iteration: int | None = None
    closed_iteration: int | None = None
    failure_count: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HypothesisBranch":
        return cls(
            branch_id=data["branch_id"],
            strategy=BranchStrategy(data.get("strategy", BranchStrategy.PRIMARY.value)),
            status=BranchStatus(data.get("status", BranchStatus.ACTIVE.value)),
            rationale=data.get("rationale", "Primary research path derived directly from the original problem."),
            parent_branch_id=data.get("parent_branch_id"),
            created_iteration=int(data.get("created_iteration", 0)),
            activated_iteration=(
                int(data["activated_iteration"]) if data.get("activated_iteration") is not None else None
            ),
            closed_iteration=int(data["closed_iteration"]) if data.get("closed_iteration") is not None else None,
            failure_count=int(data.get("failure_count", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class EvidenceRecord:
    iteration: int
    timestamp: str
    phase: str
    branch_id: str
    branch_strategy: BranchStrategy
    branch_parent_id: str | None
    branch_rationale: str
    input_summary: str
    output_summary: str
    verdict: VerificationVerdict | None
    tiers_applied: list[int]
    flaws: list[str]
    analysis_results: dict[str, Any] | None
    formal_verification_results: list[dict[str, Any]] | None
    model_used: str
    provider: str
    routing_mode: RoutingMode
    routing_temperature: float | None
    routing_notes: list[str]
    tokens_in: int
    tokens_out: int
    duration_seconds: float
    escalation_action: EscalationAction | None
    queued_branch_ids: list[str]
    artifacts: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceRecord":
        verdict = data.get("verdict")
        return cls(
            iteration=int(data["iteration"]),
            timestamp=data["timestamp"],
            phase=data["phase"],
            branch_id=data.get("branch_id", "branch_1"),
            branch_strategy=BranchStrategy(data.get("branch_strategy", BranchStrategy.PRIMARY.value)),
            branch_parent_id=data.get("branch_parent_id"),
            branch_rationale=data.get(
                "branch_rationale",
                "Primary research path derived directly from the original problem.",
            ),
            input_summary=data["input_summary"],
            output_summary=data["output_summary"],
            verdict=VerificationVerdict(verdict) if verdict else None,
            tiers_applied=[int(item) for item in data.get("tiers_applied", [])],
            flaws=list(data.get("flaws", [])),
            analysis_results=data.get("analysis_results") or data.get("simulation_results"),
            formal_verification_results=data.get("formal_verification_results"),
            model_used=data.get("model_used", ""),
            provider=data.get("provider", ""),
            routing_mode=RoutingMode(data.get("routing_mode", RoutingMode.DIRECT.value)),
            routing_temperature=(
                float(data["routing_temperature"]) if data.get("routing_temperature") is not None else None
            ),
            routing_notes=list(data.get("routing_notes", [])),
            tokens_in=int(data.get("tokens_in", 0)),
            tokens_out=int(data.get("tokens_out", 0)),
            duration_seconds=float(data.get("duration_seconds", 0.0)),
            escalation_action=(
                EscalationAction(data["escalation_action"]) if data.get("escalation_action") is not None else None
            ),
            queued_branch_ids=list(data.get("queued_branch_ids", [])),
            artifacts=list(data.get("artifacts", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class VerificationHistoryEntry:
    iteration: int
    verdict: VerificationVerdict
    flaws: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VerificationHistoryEntry":
        return cls(
            iteration=int(data["iteration"]),
            verdict=VerificationVerdict(data["verdict"]),
            flaws=list(data.get("flaws", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class SessionCheckpoint:
    session_id: str
    problem: str
    domain: str
    started: str
    last_updated: str
    status: str
    current_iteration: int
    max_iterations: int
    next_phase: str
    active_branch_id: str
    branches: list[HypothesisBranch]
    literature_context: list[str]
    candidate: CandidateSolution | None
    verification_report: VerificationReport | None
    verdict_history: list[VerificationHistoryEntry]
    result_summary: str
    final_verdict: str
    evidence_file: str
    artifacts_dir: str
    memory_summary_file: str
    parallax_manifest_file: str
    formal_lifecycle: FormalProofLifecycle | None = None
    artifacts: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionCheckpoint":
        candidate = data.get("candidate")
        verification_report = data.get("verification_report")
        verdict_history = [VerificationHistoryEntry.from_dict(item) for item in data.get("verdict_history", [])]
        active_branch_id = data.get("active_branch_id", "branch_1")
        branches_payload = data.get("branches")
        if branches_payload:
            branches = [HypothesisBranch.from_dict(item) for item in branches_payload]
        else:
            synthesized_status = BranchStatus.ACTIVE
            if data.get("status") == "completed":
                synthesized_status = BranchStatus.COMPLETED
            elif data.get("status") in {"failed", "cannot_verify"}:
                synthesized_status = BranchStatus.FAILED
            branches = [
                HypothesisBranch(
                    branch_id=active_branch_id,
                    strategy=BranchStrategy.PRIMARY,
                    status=synthesized_status,
                    rationale="Primary research path derived directly from the original problem.",
                    created_iteration=0,
                    activated_iteration=0,
                    closed_iteration=(
                        int(data["current_iteration"])
                        if synthesized_status in {BranchStatus.COMPLETED, BranchStatus.FAILED}
                        else None
                    ),
                    failure_count=sum(
                        1 for item in verdict_history if item.verdict is VerificationVerdict.FLAWS_FOUND
                    ),
                )
            ]
        return cls(
            session_id=data["session_id"],
            problem=data["problem"],
            domain=data["domain"],
            started=data["started"],
            last_updated=data["last_updated"],
            status=data["status"],
            current_iteration=int(data["current_iteration"]),
            max_iterations=int(data["max_iterations"]),
            next_phase=data["next_phase"],
            active_branch_id=active_branch_id,
            branches=branches,
            literature_context=list(data.get("literature_context", [])),
            candidate=CandidateSolution.from_dict(candidate) if candidate else None,
            verification_report=VerificationReport.from_dict(verification_report) if verification_report else None,
            verdict_history=verdict_history,
            result_summary=data["result_summary"],
            final_verdict=data["final_verdict"],
            evidence_file=data["evidence_file"],
            artifacts_dir=data["artifacts_dir"],
            memory_summary_file=data["memory_summary_file"],
            parallax_manifest_file=data["parallax_manifest_file"],
            formal_lifecycle=(
                FormalProofLifecycle.from_dict(data["formal_lifecycle"])
                if data.get("formal_lifecycle") is not None
                else None
            ),
            artifacts=list(data.get("artifacts", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class SessionSummary:
    problem: str
    domain: str
    started: str
    last_updated: str
    status: str
    iterations: int
    final_verdict: str
    result_summary: str
    evidence_file: str
    memory_summary_file: str
    parallax_manifest_file: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionSummary":
        return cls(
            problem=data["problem"],
            domain=data["domain"],
            started=data["started"],
            last_updated=data["last_updated"],
            status=data["status"],
            iterations=int(data["iterations"]),
            final_verdict=data["final_verdict"],
            result_summary=data["result_summary"],
            evidence_file=data["evidence_file"],
            memory_summary_file=data["memory_summary_file"],
            parallax_manifest_file=data["parallax_manifest_file"],
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class HermesMemorySummary:
    session_id: str
    generated_at: str
    problem: str
    domain: str
    status: str
    final_verdict: str
    iterations: int
    result_summary: str
    evidence_file: str
    checkpoint_file: str
    parallax_manifest_file: str
    persisted_to_memory: bool
    memory_file: str
    tiers_observed: list[int]
    artifacts: list[str]
    memory_entry: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HermesMemorySummary":
        return cls(
            session_id=data["session_id"],
            generated_at=data["generated_at"],
            problem=data["problem"],
            domain=data["domain"],
            status=data["status"],
            final_verdict=data["final_verdict"],
            iterations=int(data["iterations"]),
            result_summary=data["result_summary"],
            evidence_file=data["evidence_file"],
            checkpoint_file=data["checkpoint_file"],
            parallax_manifest_file=data["parallax_manifest_file"],
            persisted_to_memory=bool(data["persisted_to_memory"]),
            memory_file=data["memory_file"],
            tiers_observed=[int(item) for item in data.get("tiers_observed", [])],
            artifacts=list(data.get("artifacts", [])),
            memory_entry=data["memory_entry"],
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class ParallaxAsset:
    path: str
    kind: str
    media_type: str
    phase: str | None = None
    iteration: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ParallaxAsset":
        return cls(
            path=data["path"],
            kind=data["kind"],
            media_type=data["media_type"],
            phase=data.get("phase"),
            iteration=int(data["iteration"]) if data.get("iteration") is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class ParallaxEvidenceEntry:
    iteration: int
    phase: str
    verdict: str | None
    tiers_applied: list[int]
    input_summary: str
    output_summary: str
    artifacts: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ParallaxEvidenceEntry":
        return cls(
            iteration=int(data["iteration"]),
            phase=data["phase"],
            verdict=data.get("verdict"),
            tiers_applied=[int(item) for item in data.get("tiers_applied", [])],
            input_summary=data["input_summary"],
            output_summary=data["output_summary"],
            artifacts=list(data.get("artifacts", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class ParallaxEvidenceManifest:
    format: str
    manifest_version: str
    session_id: str
    generated_at: str
    problem: str
    domain: str
    status: str
    final_verdict: str
    result_summary: str
    evidence_file: str
    checkpoint_file: str
    memory_summary_file: str
    artifacts_dir: str
    hermes_memory_file: str | None
    persisted_to_memory: bool
    evidence_records: list[ParallaxEvidenceEntry]
    assets: list[ParallaxAsset]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ParallaxEvidenceManifest":
        return cls(
            format=data["format"],
            manifest_version=data["manifest_version"],
            session_id=data["session_id"],
            generated_at=data["generated_at"],
            problem=data["problem"],
            domain=data["domain"],
            status=data["status"],
            final_verdict=data["final_verdict"],
            result_summary=data["result_summary"],
            evidence_file=data["evidence_file"],
            checkpoint_file=data["checkpoint_file"],
            memory_summary_file=data["memory_summary_file"],
            artifacts_dir=data["artifacts_dir"],
            hermes_memory_file=data.get("hermes_memory_file"),
            persisted_to_memory=bool(data["persisted_to_memory"]),
            evidence_records=[ParallaxEvidenceEntry.from_dict(item) for item in data.get("evidence_records", [])],
            assets=[ParallaxAsset.from_dict(item) for item in data.get("assets", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class SessionIndex:
    sessions: dict[str, SessionSummary]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionIndex":
        return cls(
            sessions={name: SessionSummary.from_dict(summary) for name, summary in data["sessions"].items()}
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class CapabilityProbeResult:
    name: str
    status: ProbeStatus
    summary: str
    preferred_outcome: str
    fallback: str
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CapabilityProbeResult":
        return cls(
            name=data["name"],
            status=ProbeStatus(data["status"]),
            summary=data["summary"],
            preferred_outcome=data["preferred_outcome"],
            fallback=data["fallback"],
            details=dict(data.get("details", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class ReleaseCheck:
    name: str
    status: ReleaseCheckStatus
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    guidance: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReleaseCheck":
        return cls(
            name=data["name"],
            status=ReleaseCheckStatus(data["status"]),
            summary=data["summary"],
            details=dict(data.get("details", {})),
            guidance=data.get("guidance", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class ReleasePreflightReport:
    skill_name: str
    version: str
    generated_at: str
    overall_status: ReleaseCheckStatus
    release_surface_ready: bool
    operator_ready: bool
    config_path: str
    hermes_config_path: str
    publication_manifest_path: str
    checks: list[ReleaseCheck]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReleasePreflightReport":
        return cls(
            skill_name=data["skill_name"],
            version=data["version"],
            generated_at=data["generated_at"],
            overall_status=ReleaseCheckStatus(data["overall_status"]),
            release_surface_ready=bool(data["release_surface_ready"]),
            operator_ready=bool(data["operator_ready"]),
            config_path=data["config_path"],
            hermes_config_path=data["hermes_config_path"],
            publication_manifest_path=data["publication_manifest_path"],
            checks=[ReleaseCheck.from_dict(item) for item in data.get("checks", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class ReleasePublicationManifest:
    name: str
    version: str
    description: str
    package_layout: str
    distribution_targets: list[str]
    skill_manifest_path: str
    codex_skill_manifest_path: str
    codex_plugin_manifest_path: str
    codex_plugin_skill_manifest_path: str
    codex_plugin_marketplace_path: str
    readme_path: str
    install_script: str
    preflight_script: str
    setup_mcp_script: str
    config_template_path: str
    benchmark_baseline_path: str
    public_commands: list[str]
    operator_validation_commands: list[str]
    auto_improve: bool
    auto_improve_enablement: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReleasePublicationManifest":
        return cls(
            name=data["name"],
            version=data["version"],
            description=data["description"],
            package_layout=data["package_layout"],
            distribution_targets=list(data["distribution_targets"]),
            skill_manifest_path=data["skill_manifest_path"],
            codex_skill_manifest_path=data["codex_skill_manifest_path"],
            codex_plugin_manifest_path=data["codex_plugin_manifest_path"],
            codex_plugin_skill_manifest_path=data["codex_plugin_skill_manifest_path"],
            codex_plugin_marketplace_path=data["codex_plugin_marketplace_path"],
            readme_path=data["readme_path"],
            install_script=data["install_script"],
            preflight_script=data["preflight_script"],
            setup_mcp_script=data["setup_mcp_script"],
            config_template_path=data["config_template_path"],
            benchmark_baseline_path=data["benchmark_baseline_path"],
            public_commands=list(data["public_commands"]),
            operator_validation_commands=list(data["operator_validation_commands"]),
            auto_improve=bool(data["auto_improve"]),
            auto_improve_enablement=data["auto_improve_enablement"],
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)
