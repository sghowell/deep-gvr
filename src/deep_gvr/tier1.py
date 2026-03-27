from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Protocol
from uuid import uuid4

from .contracts import (
    CandidateSolution,
    Backend,
    DeepGvrConfig,
    EvidenceRecord,
    ModelSelection,
    SessionCheckpoint,
    SessionIndex,
    SessionSummary,
    SimAnalysis,
    SimResults,
    SimSpec,
    Tier2Report,
    VerificationHistoryEntry,
    VerificationReport,
    VerificationVerdict,
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _isoformat(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _relative_to_root(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


@dataclass(slots=True)
class GenerationRequest:
    session_id: str
    problem: str
    domain: str
    literature_context: list[str]
    prior_verdicts: list[VerificationHistoryEntry]


@dataclass(slots=True)
class VerificationRequest:
    session_id: str
    iteration: int
    candidate: CandidateSolution
    simulation_results: SimResults | None = None


@dataclass(slots=True)
class RevisionRequest:
    session_id: str
    iteration: int
    candidate: CandidateSolution
    verification_report: VerificationReport


class Generator(Protocol):
    def __call__(self, request: GenerationRequest) -> CandidateSolution:
        ...


class Verifier(Protocol):
    def __call__(self, request: VerificationRequest) -> VerificationReport:
        ...


class Reviser(Protocol):
    def __call__(self, request: RevisionRequest) -> CandidateSolution:
        ...


@dataclass(slots=True)
class SimulationRequest:
    session_id: str
    iteration: int
    sim_spec: SimSpec
    backend: Backend


class Simulator(Protocol):
    def __call__(self, request: SimulationRequest) -> SimResults:
        ...


@dataclass(slots=True, frozen=True)
class SessionPaths:
    session_id: str
    session_dir: Path
    evidence_log: Path
    checkpoint_file: Path
    artifacts_dir: Path


@dataclass(slots=True)
class Tier1RunResult:
    session_id: str
    session_paths: SessionPaths
    checkpoint: SessionCheckpoint
    final_candidate: CandidateSolution
    final_report: VerificationReport


class SessionStore:
    def __init__(self, root_directory: str | Path, clock: Callable[[], datetime] | None = None) -> None:
        self.root_directory = Path(root_directory).expanduser()
        self.clock = clock or _utc_now

    def session_paths(self, session_id: str) -> SessionPaths:
        session_dir = self.root_directory / session_id
        return SessionPaths(
            session_id=session_id,
            session_dir=session_dir,
            evidence_log=self.root_directory / f"{session_id}.jsonl",
            checkpoint_file=session_dir / "checkpoint.json",
            artifacts_dir=session_dir / "artifacts",
        )

    def initialize_session(
        self,
        *,
        problem: str,
        domain: str,
        max_iterations: int,
        literature_context: list[str],
        session_id: str | None = None,
    ) -> SessionCheckpoint:
        session_id = session_id or f"session_{uuid4().hex[:8]}"
        paths = self.session_paths(session_id)
        if paths.checkpoint_file.exists():
            raise FileExistsError(f"Session {session_id!r} already exists.")

        self.root_directory.mkdir(parents=True, exist_ok=True)
        paths.session_dir.mkdir(parents=True, exist_ok=True)
        paths.artifacts_dir.mkdir(parents=True, exist_ok=True)
        paths.evidence_log.touch(exist_ok=True)

        now = _isoformat(self.clock())
        checkpoint = SessionCheckpoint(
            session_id=session_id,
            problem=problem,
            domain=domain,
            started=now,
            last_updated=now,
            status="in_progress",
            current_iteration=0,
            max_iterations=max_iterations,
            next_phase="generate",
            literature_context=list(literature_context),
            candidate=None,
            verification_report=None,
            verdict_history=[],
            result_summary="Session initialized and ready to generate the first candidate.",
            final_verdict="PENDING",
            evidence_file=_relative_to_root(self.root_directory, paths.evidence_log),
            artifacts_dir=_relative_to_root(self.root_directory, paths.artifacts_dir),
            artifacts=[],
        )
        self.save_checkpoint(checkpoint)
        return checkpoint

    def load_checkpoint(self, session_id: str) -> SessionCheckpoint:
        path = self.session_paths(session_id).checkpoint_file
        payload = json.loads(path.read_text(encoding="utf-8"))
        return SessionCheckpoint.from_dict(payload)

    def save_checkpoint(self, checkpoint: SessionCheckpoint) -> None:
        paths = self.session_paths(checkpoint.session_id)
        paths.session_dir.mkdir(parents=True, exist_ok=True)
        paths.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(paths.checkpoint_file, checkpoint.to_dict())
        self._write_json(self.root_directory / "index.json", self._updated_index(checkpoint).to_dict())

    def append_evidence(self, session_id: str, record: EvidenceRecord) -> None:
        self.root_directory.mkdir(parents=True, exist_ok=True)
        evidence_path = self.session_paths(session_id).evidence_log
        with evidence_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict()) + "\n")

    def write_artifact_json(self, session_id: str, filename: str, payload: dict[str, object]) -> str:
        artifact_path = self.session_paths(session_id).artifacts_dir / filename
        self._write_json(artifact_path, payload)
        return _relative_to_root(self.root_directory, artifact_path)

    def read_evidence(self, session_id: str) -> list[EvidenceRecord]:
        evidence_path = self.session_paths(session_id).evidence_log
        if not evidence_path.exists():
            return []
        lines = [line for line in evidence_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return [EvidenceRecord.from_dict(json.loads(line)) for line in lines]

    def _updated_index(self, checkpoint: SessionCheckpoint) -> SessionIndex:
        index_path = self.root_directory / "index.json"
        if index_path.exists():
            payload = json.loads(index_path.read_text(encoding="utf-8"))
            index = SessionIndex.from_dict(payload)
        else:
            index = SessionIndex(sessions={})

        index.sessions[checkpoint.session_id] = SessionSummary(
            problem=checkpoint.problem,
            domain=checkpoint.domain,
            started=checkpoint.started,
            last_updated=checkpoint.last_updated,
            status=checkpoint.status,
            iterations=len(checkpoint.verdict_history),
            final_verdict=checkpoint.final_verdict,
            result_summary=checkpoint.result_summary,
            evidence_file=checkpoint.evidence_file,
        )
        return index

    def _write_json(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(f"{path.suffix}.tmp")
        temp_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        temp_path.replace(path)


class Tier1LoopRunner:
    def __init__(
        self,
        config: DeepGvrConfig,
        *,
        session_store: SessionStore | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.config = config
        self.clock = clock or _utc_now
        self.session_store = session_store or SessionStore(config.evidence.directory, clock=self.clock)

    def run(
        self,
        *,
        problem: str,
        generator: Generator,
        verifier: Verifier,
        reviser: Reviser,
        simulator: Simulator | None = None,
        literature_context: list[str] | tuple[str, ...] = (),
        domain: str | None = None,
        session_id: str | None = None,
    ) -> Tier1RunResult:
        checkpoint = self.session_store.initialize_session(
            problem=problem,
            domain=domain or self.config.domain.default,
            max_iterations=self.config.loop.max_iterations,
            literature_context=list(literature_context),
            session_id=session_id,
        )
        return self._drive(checkpoint, generator=generator, verifier=verifier, reviser=reviser, simulator=simulator)

    def resume(
        self,
        session_id: str,
        *,
        generator: Generator,
        verifier: Verifier,
        reviser: Reviser,
        simulator: Simulator | None = None,
    ) -> Tier1RunResult:
        checkpoint = self.session_store.load_checkpoint(session_id)
        return self._drive(checkpoint, generator=generator, verifier=verifier, reviser=reviser, simulator=simulator)

    def _drive(
        self,
        checkpoint: SessionCheckpoint,
        *,
        generator: Generator,
        verifier: Verifier,
        reviser: Reviser,
        simulator: Simulator | None,
    ) -> Tier1RunResult:
        while checkpoint.next_phase != "complete":
            if checkpoint.next_phase == "generate":
                checkpoint = self._generate(checkpoint, generator)
                continue
            if checkpoint.next_phase == "verify":
                checkpoint = self._verify(checkpoint, verifier, simulator)
                continue
            if checkpoint.next_phase == "revise":
                checkpoint = self._revise(checkpoint, reviser)
                continue
            raise ValueError(f"Unknown next_phase {checkpoint.next_phase!r}.")

        if checkpoint.candidate is None or checkpoint.verification_report is None:
            raise ValueError("Completed sessions must retain the final candidate and verification report.")

        return Tier1RunResult(
            session_id=checkpoint.session_id,
            session_paths=self.session_store.session_paths(checkpoint.session_id),
            checkpoint=checkpoint,
            final_candidate=checkpoint.candidate,
            final_report=checkpoint.verification_report,
        )

    def _generate(self, checkpoint: SessionCheckpoint, generator: Generator) -> SessionCheckpoint:
        request = GenerationRequest(
            session_id=checkpoint.session_id,
            problem=checkpoint.problem,
            domain=checkpoint.domain,
            literature_context=list(checkpoint.literature_context),
            prior_verdicts=list(checkpoint.verdict_history),
        )
        candidate = generator(request)
        checkpoint.current_iteration += 1
        checkpoint.candidate = candidate
        checkpoint.verification_report = None
        checkpoint.last_updated = self._timestamp()
        checkpoint.result_summary = f"Generated candidate {checkpoint.current_iteration} for Tier 1 verification."
        checkpoint.next_phase = "verify"
        self.session_store.append_evidence(
            checkpoint.session_id,
            self._evidence_record(
                checkpoint=checkpoint,
                phase="generate",
                verdict=None,
                tiers_applied=[],
                flaws=[],
                input_summary=f"Research problem: {checkpoint.problem}",
                output_summary=f"Hypothesis: {candidate.hypothesis}",
            ),
        )
        self.session_store.save_checkpoint(checkpoint)
        return checkpoint

    def _verify(self, checkpoint: SessionCheckpoint, verifier: Verifier, simulator: Simulator | None) -> SessionCheckpoint:
        candidate = self._require_candidate(checkpoint)
        request = VerificationRequest(
            session_id=checkpoint.session_id,
            iteration=checkpoint.current_iteration,
            candidate=candidate,
        )
        report = verifier(request)
        simulation_results = None
        if self._should_run_simulation(report):
            simulation_results = self._simulate(checkpoint, report, simulator)
            request = VerificationRequest(
                session_id=checkpoint.session_id,
                iteration=checkpoint.current_iteration,
                candidate=candidate,
                simulation_results=simulation_results,
            )
            report = verifier(request)
            self._attach_simulation_results(report, simulation_results)

        checkpoint.verification_report = report
        checkpoint.verdict_history.append(
            VerificationHistoryEntry(
                iteration=checkpoint.current_iteration,
                verdict=report.verdict,
                flaws=list(report.flaws),
            )
        )
        checkpoint.last_updated = self._timestamp()
        checkpoint.final_verdict = report.verdict.value
        self.session_store.append_evidence(
            checkpoint.session_id,
            self._evidence_record(
                checkpoint=checkpoint,
                phase="verify",
                verdict=report.verdict,
                tiers_applied=self._tiers_applied(report),
                flaws=list(report.flaws),
                input_summary=f"Hypothesis: {candidate.hypothesis}",
                output_summary=self._verification_summary(report),
                simulation_results=simulation_results,
            ),
        )

        if report.verdict is VerificationVerdict.VERIFIED:
            checkpoint.status = "completed"
            checkpoint.result_summary = (
                f"Verification passed on candidate {checkpoint.current_iteration}."
            )
            checkpoint.next_phase = "complete"
        elif report.verdict is VerificationVerdict.CANNOT_VERIFY:
            checkpoint.status = "cannot_verify"
            checkpoint.result_summary = (
                "Verification could not complete: "
                f"{report.cannot_verify_reason or 'no blocker summary was provided.'}"
            )
            checkpoint.next_phase = "complete"
        elif checkpoint.current_iteration >= checkpoint.max_iterations:
            checkpoint.status = "failed"
            checkpoint.result_summary = (
                f"Iteration budget exhausted after {len(checkpoint.verdict_history)} verification attempt(s)."
            )
            checkpoint.next_phase = "complete"
        else:
            checkpoint.status = "in_progress"
            checkpoint.result_summary = f"Verifier found flaws in candidate {checkpoint.current_iteration}; revision required."
            checkpoint.next_phase = "revise"

        self.session_store.save_checkpoint(checkpoint)
        return checkpoint

    def _revise(self, checkpoint: SessionCheckpoint, reviser: Reviser) -> SessionCheckpoint:
        candidate = self._require_candidate(checkpoint)
        report = self._require_report(checkpoint)
        next_iteration = checkpoint.current_iteration + 1
        request = RevisionRequest(
            session_id=checkpoint.session_id,
            iteration=next_iteration,
            candidate=candidate,
            verification_report=report,
        )
        revised_candidate = reviser(request)
        checkpoint.current_iteration = next_iteration
        checkpoint.candidate = revised_candidate
        checkpoint.verification_report = None
        checkpoint.last_updated = self._timestamp()
        checkpoint.result_summary = f"Revised candidate {checkpoint.current_iteration} from verifier feedback."
        checkpoint.next_phase = "verify"
        self.session_store.append_evidence(
            checkpoint.session_id,
            self._evidence_record(
                checkpoint=checkpoint,
                phase="revise",
                verdict=None,
                tiers_applied=[],
                flaws=list(report.flaws),
                input_summary=f"Applying verifier flaws: {self._flaw_summary(report.flaws)}",
                output_summary=f"Revised hypothesis: {revised_candidate.hypothesis}",
            ),
        )
        self.session_store.save_checkpoint(checkpoint)
        return checkpoint

    def _evidence_record(
        self,
        *,
        checkpoint: SessionCheckpoint,
        phase: str,
        verdict: VerificationVerdict | None,
        tiers_applied: list[int],
        flaws: list[str],
        input_summary: str,
        output_summary: str,
        simulation_results: SimResults | None = None,
        model_selection: ModelSelection | None = None,
    ) -> EvidenceRecord:
        selection = model_selection or self._model_for_phase(phase)
        return EvidenceRecord(
            iteration=checkpoint.current_iteration,
            timestamp=checkpoint.last_updated,
            phase=phase,
            input_summary=input_summary,
            output_summary=output_summary,
            verdict=verdict,
            tiers_applied=tiers_applied,
            flaws=flaws,
            simulation_results=simulation_results.to_dict() if simulation_results is not None else None,
            formal_verification_results=None,
            model_used=selection.model,
            provider=selection.provider,
            tokens_in=0,
            tokens_out=0,
            duration_seconds=0.0,
            artifacts=list(checkpoint.artifacts),
        )

    def _model_for_phase(self, phase: str):
        if phase == "generate":
            return self.config.models.generator
        if phase == "verify":
            return self.config.models.verifier
        if phase == "simulate":
            return ModelSelection(provider="adapter", model=self.config.verification.tier2.default_simulator)
        return self.config.models.reviser

    def _tiers_applied(self, report: VerificationReport) -> list[int]:
        tiers = [1]
        if report.tier2 is not None and (
            report.tier2.simulation_requested or report.tier2.results is not None or report.tier2.simulation_spec is not None
        ):
            tiers.append(2)
        if report.tier3:
            tiers.append(3)
        return tiers

    def _verification_summary(self, report: VerificationReport) -> str:
        if report.verdict is VerificationVerdict.VERIFIED:
            caveat_text = "; ".join(report.caveats) or "No caveats recorded."
            if report.tier2 and report.tier2.results is not None:
                interpretation = report.tier2.interpretation or "Simulation results were incorporated."
                return f"Verified with Tier 2 evidence. {interpretation} Caveats: {caveat_text}"
            return f"Verified. Caveats: {caveat_text}"
        if report.verdict is VerificationVerdict.CANNOT_VERIFY:
            return f"Cannot verify. Blocker: {report.cannot_verify_reason or 'unspecified'}"
        return f"Flaws found: {self._flaw_summary(report.flaws)}"

    def _flaw_summary(self, flaws: list[str]) -> str:
        return "; ".join(flaws) if flaws else "No flaw details recorded."

    def _require_candidate(self, checkpoint: SessionCheckpoint) -> CandidateSolution:
        if checkpoint.candidate is None:
            raise ValueError("A candidate is required before verification or revision.")
        return checkpoint.candidate

    def _require_report(self, checkpoint: SessionCheckpoint) -> VerificationReport:
        if checkpoint.verification_report is None:
            raise ValueError("A verification report is required before revision.")
        return checkpoint.verification_report

    def _should_run_simulation(self, report: VerificationReport) -> bool:
        return bool(
            self.config.verification.tier2.enabled
            and report.tier2 is not None
            and report.tier2.simulation_requested
            and report.tier2.simulation_spec is not None
            and report.tier2.results is None
        )

    def _simulate(
        self,
        checkpoint: SessionCheckpoint,
        report: VerificationReport,
        simulator: Simulator | None,
    ) -> SimResults:
        tier2 = report.tier2
        if tier2 is None or tier2.simulation_spec is None:
            raise ValueError("Simulation mediation requires a Tier 2 spec.")

        sim_spec = SimSpec.from_dict(tier2.simulation_spec)
        request = SimulationRequest(
            session_id=checkpoint.session_id,
            iteration=checkpoint.current_iteration,
            sim_spec=sim_spec,
            backend=self.config.verification.tier2.default_backend,
        )
        sim_results = simulator(request) if simulator is not None else self._run_simulation_request(request)

        spec_artifact = self.session_store.write_artifact_json(
            checkpoint.session_id,
            f"iteration_{checkpoint.current_iteration}_simulation_spec.json",
            sim_spec.to_dict(),
        )
        results_artifact = self.session_store.write_artifact_json(
            checkpoint.session_id,
            f"iteration_{checkpoint.current_iteration}_simulation_results.json",
            sim_results.to_dict(),
        )
        checkpoint.artifacts = self._merge_artifacts(checkpoint.artifacts, [spec_artifact, results_artifact])
        checkpoint.last_updated = self._timestamp()
        checkpoint.result_summary = f"Completed Tier 2 simulation for candidate {checkpoint.current_iteration}."

        self.session_store.append_evidence(
            checkpoint.session_id,
            self._evidence_record(
                checkpoint=checkpoint,
                phase="simulate",
                verdict=None,
                tiers_applied=[2],
                flaws=[],
                input_summary=f"Simulation requested: {tier2.reason}",
                output_summary=self._simulation_summary(sim_results),
                simulation_results=sim_results,
            ),
        )
        self.session_store.save_checkpoint(checkpoint)
        return sim_results

    def _run_simulation_request(self, request: SimulationRequest) -> SimResults:
        if request.sim_spec.simulator != self.config.verification.tier2.default_simulator:
            return SimResults(
                simulator=request.sim_spec.simulator,
                adapter_version="0.1.0",
                timestamp=self._timestamp(),
                runtime_seconds=0.0,
                backend=request.backend,
                data=[],
                analysis=_empty_sim_analysis("adapter_not_available"),
                errors=[
                    f"Simulator {request.sim_spec.simulator!r} is not configured in this environment.",
                ],
            )

        from adapters.stim_adapter import StimAdapter

        return StimAdapter().run(request.sim_spec, request.backend)

    def _attach_simulation_results(self, report: VerificationReport, sim_results: SimResults) -> None:
        if report.tier2 is None:
            report.tier2 = Tier2Report(
                simulation_requested=True,
                reason="Simulation was executed by the orchestrator.",
                simulation_spec=None,
                results=sim_results.to_dict(),
                interpretation=None,
            )
            return

        if report.tier2.results is None:
            report.tier2.results = sim_results.to_dict()

    def _simulation_summary(self, sim_results: SimResults) -> str:
        if sim_results.errors:
            return f"Simulation returned errors: {'; '.join(sim_results.errors)}"
        return (
            f"Simulation produced {len(sim_results.data)} data point(s) via {sim_results.simulator} on "
            f"{sim_results.backend.value}; threshold method={sim_results.analysis.threshold_method}."
        )

    def _merge_artifacts(self, current: list[str], additions: list[str]) -> list[str]:
        merged = list(current)
        for artifact in additions:
            if artifact not in merged:
                merged.append(artifact)
        return merged

    def _timestamp(self) -> str:
        return _isoformat(self.clock())


def _empty_sim_analysis(method: str) -> SimAnalysis:
    return SimAnalysis(
        threshold_estimate=None,
        threshold_method=method,
        below_threshold_distances=[],
        scaling_exponent=None,
    )
