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


@dataclass(slots=True)
class Tier2Config:
    enabled: bool = True
    default_simulator: str = "stim"
    default_backend: Backend = Backend.LOCAL
    timeout_seconds: int = 3600
    ssh: SSHConfig = field(default_factory=SSHConfig)


@dataclass(slots=True)
class Tier3Config:
    enabled: bool = False
    backend: str = "aristotle"
    timeout_seconds: int = 300


@dataclass(slots=True)
class VerificationConfig:
    tier1: TierToggleConfig = field(default_factory=TierToggleConfig)
    tier2: Tier2Config = field(default_factory=Tier2Config)
    tier3: Tier3Config = field(default_factory=Tier3Config)


@dataclass(slots=True)
class ModelsConfig:
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
        return cls(
            loop=LoopConfig(
                max_iterations=int(data["loop"]["max_iterations"]),
                alternative_approach=bool(data["loop"]["alternative_approach"]),
                max_alternatives=int(data["loop"]["max_alternatives"]),
            ),
            verification=VerificationConfig(
                tier1=TierToggleConfig(enabled=bool(verification["tier1"]["enabled"])),
                tier2=Tier2Config(
                    enabled=bool(verification["tier2"]["enabled"]),
                    default_simulator=verification["tier2"]["default_simulator"],
                    default_backend=Backend(verification["tier2"]["default_backend"]),
                    timeout_seconds=int(verification["tier2"]["timeout_seconds"]),
                    ssh=SSHConfig(
                        host=verification["tier2"]["ssh"]["host"],
                        user=verification["tier2"]["ssh"]["user"],
                        key_path=verification["tier2"]["ssh"]["key_path"],
                    ),
                ),
                tier3=Tier3Config(
                    enabled=bool(verification["tier3"]["enabled"]),
                    backend=verification["tier3"]["backend"],
                    timeout_seconds=int(verification["tier3"]["timeout_seconds"]),
                ),
            ),
            models=ModelsConfig(
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
    simulation_requested: bool
    reason: str
    simulation_spec: dict[str, Any] | None = None
    results: dict[str, Any] | None = None
    interpretation: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Tier2Report":
        return cls(
            simulation_requested=bool(data["simulation_requested"]),
            reason=data["reason"],
            simulation_spec=data.get("simulation_spec"),
            results=data.get("results"),
            interpretation=data.get("interpretation"),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class Tier3ClaimResult:
    claim: str
    backend: str
    proof_status: str
    details: str
    lean_code: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Tier3ClaimResult":
        return cls(
            claim=data["claim"],
            backend=data["backend"],
            proof_status=data["proof_status"],
            details=data["details"],
            lean_code=data.get("lean_code", ""),
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
            noise_model=data["noise_model"],
            error_rates=[float(item) for item in data["error_rates"]],
            decoder=data["decoder"],
            shots_per_point=int(data["shots_per_point"]),
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
            max_parallel=int(data["max_parallel"]),
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
class EvidenceRecord:
    iteration: int
    timestamp: str
    phase: str
    input_summary: str
    output_summary: str
    verdict: VerificationVerdict | None
    tiers_applied: list[int]
    flaws: list[str]
    simulation_results: dict[str, Any] | None
    formal_verification_results: list[dict[str, Any]] | None
    model_used: str
    provider: str
    tokens_in: int
    tokens_out: int
    duration_seconds: float
    artifacts: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceRecord":
        verdict = data.get("verdict")
        return cls(
            iteration=int(data["iteration"]),
            timestamp=data["timestamp"],
            phase=data["phase"],
            input_summary=data["input_summary"],
            output_summary=data["output_summary"],
            verdict=VerificationVerdict(verdict) if verdict else None,
            tiers_applied=[int(item) for item in data.get("tiers_applied", [])],
            flaws=list(data.get("flaws", [])),
            simulation_results=data.get("simulation_results"),
            formal_verification_results=data.get("formal_verification_results"),
            model_used=data.get("model_used", ""),
            provider=data.get("provider", ""),
            tokens_in=int(data.get("tokens_in", 0)),
            tokens_out=int(data.get("tokens_out", 0)),
            duration_seconds=float(data.get("duration_seconds", 0.0)),
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
