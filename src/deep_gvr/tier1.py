from __future__ import annotations

import importlib
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Protocol
from uuid import uuid4

from .contracts import (
    AnalysisResults,
    AnalysisSpec,
    Backend,
    BranchStatus,
    BranchStrategy,
    CapabilityProbeResult,
    CandidateSolution,
    DeepGvrConfig,
    EvidenceRecord,
    EscalationAction,
    FormalProofLifecycle,
    HypothesisBranch,
    ProofStatus,
    RoutingMode,
    SessionCheckpoint,
    SessionIndex,
    SessionSummary,
    Tier2Report,
    Tier3ClaimResult,
    VerificationHistoryEntry,
    VerificationReport,
    VerificationVerdict,
)
from .evidence import build_memory_summary, build_parallax_manifest, hermes_memory_file, persist_memory_summary
from .formal import (
    FormalVerificationRequest,
    FormalVerificationResultSet,
    FormalVerifier,
    build_formal_verifier,
)
from .routing import EffectiveModelRoute, RoutingPlan, build_routing_plan


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _isoformat(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _relative_to_root(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _load_analysis_adapter_builder() -> Callable[..., object]:
    repo_root = str(Path(__file__).resolve().parents[2])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    module = importlib.import_module("adapters.registry")
    return getattr(module, "build_analysis_adapter")


def _load_stim_adapter_class():
    repo_root = str(Path(__file__).resolve().parents[2])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    module = importlib.import_module("adapters.stim_adapter")
    return getattr(module, "StimAdapter")


@dataclass(slots=True)
class GenerationRequest:
    session_id: str
    problem: str
    domain: str
    literature_context: list[str]
    prior_verdicts: list[VerificationHistoryEntry]
    route: EffectiveModelRoute
    branch_id: str = "branch_1"
    branch_strategy: BranchStrategy = BranchStrategy.PRIMARY
    branch_parent_id: str | None = None
    branch_rationale: str = "Primary research path derived directly from the original problem."
    trigger_flaws: tuple[str, ...] = ()


@dataclass(slots=True)
class VerificationRequest:
    session_id: str
    iteration: int
    candidate: CandidateSolution
    route: EffectiveModelRoute
    analysis_results: AnalysisResults | None = None
    formal_results: list[Tier3ClaimResult] | None = None

    @property
    def simulation_results(self) -> AnalysisResults | None:
        return self.analysis_results


@dataclass(slots=True)
class RevisionRequest:
    session_id: str
    iteration: int
    candidate: CandidateSolution
    verification_report: VerificationReport
    route: EffectiveModelRoute
    branch_id: str = "branch_1"
    branch_strategy: BranchStrategy = BranchStrategy.PRIMARY
    branch_parent_id: str | None = None
    branch_rationale: str = "Primary research path derived directly from the original problem."


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
class AnalysisRequest:
    session_id: str
    iteration: int
    analysis_spec: AnalysisSpec
    backend: Backend

    @property
    def sim_spec(self) -> AnalysisSpec:
        return self.analysis_spec


class Analyzer(Protocol):
    def __call__(self, request: AnalysisRequest) -> AnalysisResults:
        ...


SimulationRequest = AnalysisRequest
Simulator = Analyzer


@dataclass(slots=True, frozen=True)
class SessionPaths:
    session_id: str
    session_dir: Path
    evidence_log: Path
    checkpoint_file: Path
    artifacts_dir: Path
    memory_summary_file: Path
    parallax_manifest_file: Path
    hermes_memory_file: Path


@dataclass(slots=True)
class Tier1RunResult:
    session_id: str
    session_paths: SessionPaths
    checkpoint: SessionCheckpoint
    final_candidate: CandidateSolution
    final_report: VerificationReport


class SessionStore:
    def __init__(
        self,
        root_directory: str | Path,
        clock: Callable[[], datetime] | None = None,
        *,
        persist_to_memory: bool = True,
    ) -> None:
        self.root_directory = Path(root_directory).expanduser()
        self.clock = clock or _utc_now
        self.persist_to_memory = persist_to_memory

    def session_paths(self, session_id: str) -> SessionPaths:
        session_dir = self.root_directory / session_id
        return SessionPaths(
            session_id=session_id,
            session_dir=session_dir,
            evidence_log=self.root_directory / f"{session_id}.jsonl",
            checkpoint_file=session_dir / "checkpoint.json",
            artifacts_dir=session_dir / "artifacts",
            memory_summary_file=session_dir / "artifacts" / "session_memory_summary.json",
            parallax_manifest_file=session_dir / "artifacts" / "parallax_manifest.json",
            hermes_memory_file=hermes_memory_file(self.root_directory),
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
            active_branch_id="branch_1",
            branches=[
                HypothesisBranch(
                    branch_id="branch_1",
                    strategy=BranchStrategy.PRIMARY,
                    status=BranchStatus.ACTIVE,
                    rationale="Primary research path derived directly from the original problem.",
                    created_iteration=0,
                    activated_iteration=0,
                )
            ],
            literature_context=list(literature_context),
            candidate=None,
            verification_report=None,
            verdict_history=[],
            result_summary="Session initialized and ready to generate the first candidate.",
            final_verdict="PENDING",
            evidence_file=_relative_to_root(self.root_directory, paths.evidence_log),
            artifacts_dir=_relative_to_root(self.root_directory, paths.artifacts_dir),
            memory_summary_file=_relative_to_root(self.root_directory, paths.memory_summary_file),
            parallax_manifest_file=_relative_to_root(self.root_directory, paths.parallax_manifest_file),
            formal_lifecycle=None,
            artifacts=[
                _relative_to_root(self.root_directory, paths.memory_summary_file),
                _relative_to_root(self.root_directory, paths.parallax_manifest_file),
            ],
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
        memory_summary_relative = _relative_to_root(self.root_directory, paths.memory_summary_file)
        parallax_manifest_relative = _relative_to_root(self.root_directory, paths.parallax_manifest_file)
        checkpoint.memory_summary_file = memory_summary_relative
        checkpoint.parallax_manifest_file = parallax_manifest_relative
        if memory_summary_relative not in checkpoint.artifacts:
            checkpoint.artifacts.append(memory_summary_relative)
        if parallax_manifest_relative not in checkpoint.artifacts:
            checkpoint.artifacts.append(parallax_manifest_relative)
        self._write_json(paths.checkpoint_file, checkpoint.to_dict())
        self._write_json(self.root_directory / "index.json", self._updated_index(checkpoint).to_dict())
        self._sync_derived_artifacts(checkpoint, paths)

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
            memory_summary_file=checkpoint.memory_summary_file,
            parallax_manifest_file=checkpoint.parallax_manifest_file,
        )
        return index

    def _sync_derived_artifacts(self, checkpoint: SessionCheckpoint, paths: SessionPaths) -> None:
        evidence_records = self.read_evidence(checkpoint.session_id)
        generated_at = _isoformat(self.clock())
        memory_summary = build_memory_summary(
            root_directory=self.root_directory,
            checkpoint=checkpoint,
            evidence_records=evidence_records,
            checkpoint_file=paths.checkpoint_file,
            memory_file=paths.hermes_memory_file,
            generated_at=generated_at,
            persisted_to_memory=self.persist_to_memory,
        )
        self._write_json(paths.memory_summary_file, memory_summary.to_dict())
        if self.persist_to_memory:
            persist_memory_summary(paths.hermes_memory_file, memory_summary)
        manifest = build_parallax_manifest(
            root_directory=self.root_directory,
            checkpoint=checkpoint,
            evidence_records=evidence_records,
            checkpoint_file=paths.checkpoint_file,
            artifacts_dir=paths.artifacts_dir,
            memory_summary=memory_summary,
        )
        self._write_json(paths.parallax_manifest_file, manifest.to_dict())

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
        routing_probe: CapabilityProbeResult | None = None,
        routing_plan: RoutingPlan | None = None,
    ) -> None:
        self.config = config
        self.clock = clock or _utc_now
        self.session_store = session_store or SessionStore(
            config.evidence.directory,
            clock=self.clock,
            persist_to_memory=config.evidence.persist_to_memory,
        )
        self.routing_plan = routing_plan or build_routing_plan(config, routing_probe=routing_probe)

    def run(
        self,
        *,
        problem: str,
        generator: Generator,
        verifier: Verifier,
        reviser: Reviser,
        analyzer: Analyzer | None = None,
        simulator: Analyzer | None = None,
        formal_verifier: FormalVerifier | None = None,
        literature_context: list[str] | tuple[str, ...] = (),
        domain: str | None = None,
        session_id: str | None = None,
    ) -> Tier1RunResult:
        resolved_analyzer = analyzer or simulator
        checkpoint = self.session_store.initialize_session(
            problem=problem,
            domain=domain or self.config.domain.default,
            max_iterations=self.config.loop.max_iterations,
            literature_context=list(literature_context),
            session_id=session_id,
        )
        return self._drive(
            checkpoint,
            generator=generator,
            verifier=verifier,
            reviser=reviser,
            analyzer=resolved_analyzer,
            formal_verifier=formal_verifier,
        )

    def resume(
        self,
        session_id: str,
        *,
        generator: Generator,
        verifier: Verifier,
        reviser: Reviser,
        analyzer: Analyzer | None = None,
        simulator: Analyzer | None = None,
        formal_verifier: FormalVerifier | None = None,
    ) -> Tier1RunResult:
        resolved_analyzer = analyzer or simulator
        checkpoint = self.session_store.load_checkpoint(session_id)
        return self._drive(
            checkpoint,
            generator=generator,
            verifier=verifier,
            reviser=reviser,
            analyzer=resolved_analyzer,
            formal_verifier=formal_verifier,
        )

    def _drive(
        self,
        checkpoint: SessionCheckpoint,
        *,
        generator: Generator,
        verifier: Verifier,
        reviser: Reviser,
        analyzer: Analyzer | None,
        formal_verifier: FormalVerifier | None,
    ) -> Tier1RunResult:
        while checkpoint.next_phase != "complete":
            if checkpoint.next_phase == "generate":
                checkpoint = self._generate(checkpoint, generator)
                continue
            if checkpoint.next_phase == "verify":
                checkpoint = self._verify(checkpoint, verifier, analyzer, formal_verifier)
                if checkpoint.next_phase == "formalize":
                    break
                continue
            if checkpoint.next_phase == "formalize":
                checkpoint = self._continue_formalize(checkpoint, verifier, formal_verifier)
                if checkpoint.next_phase == "formalize":
                    break
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

    def _active_branch(self, checkpoint: SessionCheckpoint) -> HypothesisBranch:
        for branch in checkpoint.branches:
            if branch.branch_id == checkpoint.active_branch_id:
                return branch
        raise ValueError(f"Session {checkpoint.session_id!r} references unknown branch {checkpoint.active_branch_id!r}.")

    def _queued_branches(self, checkpoint: SessionCheckpoint) -> list[HypothesisBranch]:
        return [branch for branch in checkpoint.branches if branch.status is BranchStatus.QUEUED]

    def _available_fanout_slots(self, checkpoint: SessionCheckpoint) -> int:
        created_alternatives = sum(1 for branch in checkpoint.branches if branch.strategy is not BranchStrategy.PRIMARY)
        remaining_alternative_slots = max(0, self.config.loop.max_alternatives - created_alternatives)
        remaining_iteration_slots = max(0, checkpoint.max_iterations - checkpoint.current_iteration)
        return min(remaining_alternative_slots, remaining_iteration_slots)

    def _spawn_fanout_branches(
        self,
        checkpoint: SessionCheckpoint,
        *,
        parent_branch: HypothesisBranch,
        report: VerificationReport,
    ) -> list[HypothesisBranch]:
        if not self.config.loop.alternative_approach:
            return []

        slots = self._available_fanout_slots(checkpoint)
        if slots <= 0:
            return []

        strategy_specs: list[tuple[BranchStrategy, str]] = []
        flaw_summary = self._flaw_summary(report.flaws)
        strategy_specs.append(
            (
                BranchStrategy.ALTERNATIVE_APPROACH,
                f"Try a materially different approach that addresses: {flaw_summary}",
            )
        )
        while len(strategy_specs) < slots:
            strategy_specs.append(
                (
                    BranchStrategy.DECOMPOSITION,
                    "Decompose the problem into smaller claims, keep only defensible subclaims, "
                    f"and rebuild the answer around: {flaw_summary}",
                )
            )

        next_branch_number = len(checkpoint.branches) + 1
        spawned: list[HypothesisBranch] = []
        for offset, (strategy, rationale) in enumerate(strategy_specs):
            branch = HypothesisBranch(
                branch_id=f"branch_{next_branch_number + offset}",
                strategy=strategy,
                status=BranchStatus.QUEUED,
                rationale=rationale,
                parent_branch_id=parent_branch.branch_id,
                created_iteration=checkpoint.current_iteration,
            )
            checkpoint.branches.append(branch)
            spawned.append(branch)
        return spawned

    def _activate_next_branch(self, checkpoint: SessionCheckpoint) -> HypothesisBranch | None:
        queued = self._queued_branches(checkpoint)
        if not queued:
            return None
        next_branch = queued[0]
        next_branch.status = BranchStatus.ACTIVE
        if next_branch.activated_iteration is None:
            next_branch.activated_iteration = checkpoint.current_iteration
        checkpoint.active_branch_id = next_branch.branch_id
        checkpoint.candidate = None
        checkpoint.verification_report = None
        checkpoint.formal_lifecycle = None
        return next_branch

    def _abandon_inactive_branches(self, checkpoint: SessionCheckpoint, *, keep_branch_id: str) -> None:
        for branch in checkpoint.branches:
            if branch.branch_id == keep_branch_id:
                continue
            if branch.status in {BranchStatus.QUEUED, BranchStatus.ACTIVE}:
                branch.status = BranchStatus.ABANDONED
                branch.closed_iteration = checkpoint.current_iteration

    def _record_escalation(
        self,
        checkpoint: SessionCheckpoint,
        *,
        branch: HypothesisBranch,
        action: EscalationAction,
        flaws: list[str],
        output_summary: str,
        queued_branch_ids: list[str],
    ) -> None:
        self.session_store.append_evidence(
            checkpoint.session_id,
            self._evidence_record(
                checkpoint=checkpoint,
                phase="escalate",
                verdict=None,
                tiers_applied=[],
                flaws=list(flaws),
                input_summary=(
                    f"Escalation triggered after verifier feedback on {branch.branch_id}: "
                    f"{self._flaw_summary(flaws)}"
                ),
                output_summary=output_summary,
                route=self.routing_plan.orchestrator,
                branch=branch,
                escalation_action=action,
                queued_branch_ids=queued_branch_ids,
            ),
        )

    def _generate(self, checkpoint: SessionCheckpoint, generator: Generator) -> SessionCheckpoint:
        branch = self._active_branch(checkpoint)
        request = GenerationRequest(
            session_id=checkpoint.session_id,
            problem=checkpoint.problem,
            domain=checkpoint.domain,
            literature_context=list(checkpoint.literature_context),
            prior_verdicts=list(checkpoint.verdict_history),
            route=self.routing_plan.generator,
            branch_id=branch.branch_id,
            branch_strategy=branch.strategy,
            branch_parent_id=branch.parent_branch_id,
            branch_rationale=branch.rationale,
            trigger_flaws=tuple(checkpoint.verification_report.flaws) if checkpoint.verification_report is not None else (),
        )
        candidate = generator(request)
        checkpoint.current_iteration += 1
        checkpoint.candidate = candidate
        checkpoint.verification_report = None
        checkpoint.last_updated = self._timestamp()
        checkpoint.result_summary = (
            f"Generated candidate {checkpoint.current_iteration} on {branch.branch_id} "
            f"({branch.strategy.value}) for Tier 1 verification."
        )
        checkpoint.next_phase = "verify"
        self.session_store.append_evidence(
            checkpoint.session_id,
            self._evidence_record(
                checkpoint=checkpoint,
                phase="generate",
                verdict=None,
                tiers_applied=[],
                flaws=[],
                input_summary=(
                    f"Research problem: {checkpoint.problem} "
                    f"[branch={branch.branch_id} strategy={branch.strategy.value}]"
                ),
                output_summary=f"Hypothesis: {candidate.hypothesis}",
                route=request.route,
                branch=branch,
            ),
        )
        self.session_store.save_checkpoint(checkpoint)
        return checkpoint

    def _verify(
        self,
        checkpoint: SessionCheckpoint,
        verifier: Verifier,
        analyzer: Analyzer | None,
        formal_verifier: FormalVerifier | None,
    ) -> SessionCheckpoint:
        candidate = self._require_candidate(checkpoint)
        request = VerificationRequest(
            session_id=checkpoint.session_id,
            iteration=checkpoint.current_iteration,
            candidate=candidate,
            route=self.routing_plan.verifier,
        )
        report = verifier(request)
        analysis_results = None
        formal_results: list[Tier3ClaimResult] | None = None
        if self._should_run_analysis(report):
            analysis_results = self._analyze(checkpoint, report, analyzer)
        if self._should_run_formal(report):
            checkpoint.verification_report = report
            outcome = self._formalize(
                checkpoint,
                report,
                formal_verifier,
                lifecycle_state=None,
            )
            if outcome.pending:
                checkpoint.formal_lifecycle = outcome.lifecycle_state
                checkpoint.status = "awaiting_formal"
                checkpoint.final_verdict = "PENDING"
                checkpoint.result_summary = (
                    f"Tier 3 proof polling is still in progress for candidate {checkpoint.current_iteration}."
                )
                checkpoint.next_phase = "formalize"
                self.session_store.save_checkpoint(checkpoint)
                return checkpoint
            formal_results = outcome.results

        return self._complete_verification(
            checkpoint,
            verifier=verifier,
            base_report=report,
            candidate=candidate,
            analysis_results=analysis_results,
            formal_results=formal_results,
            initial_request=request,
        )

    def _continue_formalize(
        self,
        checkpoint: SessionCheckpoint,
        verifier: Verifier,
        formal_verifier: FormalVerifier | None,
    ) -> SessionCheckpoint:
        candidate = self._require_candidate(checkpoint)
        report = self._require_report(checkpoint)
        if checkpoint.formal_lifecycle is None:
            raise ValueError("Formal resume requires persisted formal lifecycle state.")
        outcome = self._formalize(
            checkpoint,
            report,
            formal_verifier,
            lifecycle_state=checkpoint.formal_lifecycle,
        )
        if outcome.pending:
            checkpoint.formal_lifecycle = outcome.lifecycle_state
            checkpoint.status = "awaiting_formal"
            checkpoint.final_verdict = "PENDING"
            checkpoint.result_summary = (
                f"Tier 3 proof polling is still in progress for candidate {checkpoint.current_iteration}."
            )
            checkpoint.next_phase = "formalize"
            self.session_store.save_checkpoint(checkpoint)
            return checkpoint
        return self._complete_verification(
            checkpoint,
            verifier=verifier,
            base_report=report,
            candidate=candidate,
            analysis_results=None,
            formal_results=outcome.results,
            initial_request=None,
        )

    def _complete_verification(
        self,
        checkpoint: SessionCheckpoint,
        *,
        verifier: Verifier,
        base_report: VerificationReport,
        candidate: CandidateSolution,
        analysis_results: AnalysisResults | None,
        formal_results: list[Tier3ClaimResult] | None,
        initial_request: VerificationRequest | None,
    ) -> SessionCheckpoint:
        report = base_report
        request = initial_request or VerificationRequest(
            session_id=checkpoint.session_id,
            iteration=checkpoint.current_iteration,
            candidate=candidate,
            route=self.routing_plan.verifier,
        )
        if analysis_results is not None or formal_results is not None:
            request = VerificationRequest(
                session_id=checkpoint.session_id,
                iteration=checkpoint.current_iteration,
                candidate=candidate,
                route=self.routing_plan.verifier,
                analysis_results=analysis_results,
                formal_results=formal_results,
            )
            report = verifier(request)
            if analysis_results is not None:
                self._attach_analysis_results(report, analysis_results)
            if formal_results is not None:
                self._attach_formal_results(report, formal_results)

        active_branch = self._active_branch(checkpoint)
        checkpoint.verification_report = report
        checkpoint.formal_lifecycle = None
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
                analysis_results=analysis_results,
                formal_results=formal_results,
                route=request.route,
                branch=active_branch,
            ),
        )

        if report.verdict is VerificationVerdict.VERIFIED:
            active_branch.status = BranchStatus.COMPLETED
            active_branch.closed_iteration = checkpoint.current_iteration
            self._abandon_inactive_branches(checkpoint, keep_branch_id=active_branch.branch_id)
            checkpoint.status = "completed"
            checkpoint.result_summary = (
                f"Verification passed on candidate {checkpoint.current_iteration} "
                f"from {active_branch.branch_id}."
            )
            checkpoint.next_phase = "complete"
        elif report.verdict is VerificationVerdict.CANNOT_VERIFY:
            active_branch.status = BranchStatus.FAILED
            active_branch.closed_iteration = checkpoint.current_iteration
            checkpoint.status = "cannot_verify"
            checkpoint.result_summary = (
                "Verification could not complete: "
                f"{report.cannot_verify_reason or 'no blocker summary was provided.'}"
            )
            checkpoint.next_phase = "complete"
        else:
            active_branch.failure_count += 1
            if checkpoint.current_iteration >= checkpoint.max_iterations:
                active_branch.status = BranchStatus.FAILED
                active_branch.closed_iteration = checkpoint.current_iteration
                checkpoint.status = "failed"
                checkpoint.result_summary = (
                    f"Iteration budget exhausted after {len(checkpoint.verdict_history)} verification attempt(s)."
                )
                checkpoint.next_phase = "complete"
                self._record_escalation(
                    checkpoint,
                    branch=active_branch,
                    action=EscalationAction.HALT,
                    flaws=report.flaws,
                    output_summary="Halting after iteration budget exhaustion.",
                    queued_branch_ids=[branch.branch_id for branch in self._queued_branches(checkpoint)],
                )
            elif active_branch.failure_count == 1:
                checkpoint.status = "in_progress"
                checkpoint.result_summary = (
                    f"Verifier found flaws in candidate {checkpoint.current_iteration} on "
                    f"{active_branch.branch_id}; revision required."
                )
                checkpoint.next_phase = "revise"
            else:
                queued_before = self._queued_branches(checkpoint)
                active_branch.status = BranchStatus.FAILED
                active_branch.closed_iteration = checkpoint.current_iteration
                next_branch = None
                escalation_action = EscalationAction.SWITCH_BRANCH
                output_summary = ""
                if queued_before:
                    next_branch = self._activate_next_branch(checkpoint)
                    output_summary = (
                        f"Switched from exhausted {active_branch.branch_id} to queued "
                        f"{next_branch.branch_id} ({next_branch.strategy.value})."
                    )
                else:
                    spawned = self._spawn_fanout_branches(checkpoint, parent_branch=active_branch, report=report)
                    if spawned:
                        next_branch = self._activate_next_branch(checkpoint)
                        escalation_action = EscalationAction.FANOUT
                        spawned_ids = ", ".join(branch.branch_id for branch in spawned)
                        output_summary = (
                            f"Spawned fan-out branches [{spawned_ids}] after repeated failure on "
                            f"{active_branch.branch_id}; continuing with {next_branch.branch_id} "
                            f"({next_branch.strategy.value})."
                        )
                    else:
                        escalation_action = EscalationAction.HALT
                        checkpoint.status = "failed"
                        checkpoint.result_summary = (
                            "Repeated verification failure exhausted the configured alternative-approach budget."
                        )
                        checkpoint.next_phase = "complete"
                        output_summary = (
                            f"Halting after repeated failure on {active_branch.branch_id}; no alternative "
                            "or decomposition branches remain within budget."
                        )

                self._record_escalation(
                    checkpoint,
                    branch=active_branch,
                    action=escalation_action,
                    flaws=report.flaws,
                    output_summary=output_summary,
                    queued_branch_ids=[branch.branch_id for branch in self._queued_branches(checkpoint)],
                )
                if next_branch is not None:
                    checkpoint.status = "in_progress"
                    checkpoint.result_summary = (
                        f"Escalated from {active_branch.branch_id} to {next_branch.branch_id} "
                        f"({next_branch.strategy.value})."
                    )
                    checkpoint.next_phase = "generate"

        self.session_store.save_checkpoint(checkpoint)
        return checkpoint

    def _revise(self, checkpoint: SessionCheckpoint, reviser: Reviser) -> SessionCheckpoint:
        candidate = self._require_candidate(checkpoint)
        report = self._require_report(checkpoint)
        branch = self._active_branch(checkpoint)
        next_iteration = checkpoint.current_iteration + 1
        request = RevisionRequest(
            session_id=checkpoint.session_id,
            iteration=next_iteration,
            candidate=candidate,
            verification_report=report,
            route=self.routing_plan.reviser,
            branch_id=branch.branch_id,
            branch_strategy=branch.strategy,
            branch_parent_id=branch.parent_branch_id,
            branch_rationale=branch.rationale,
        )
        revised_candidate = reviser(request)
        checkpoint.current_iteration = next_iteration
        checkpoint.candidate = revised_candidate
        checkpoint.verification_report = None
        checkpoint.formal_lifecycle = None
        checkpoint.last_updated = self._timestamp()
        checkpoint.result_summary = (
            f"Revised candidate {checkpoint.current_iteration} on {branch.branch_id} from verifier feedback."
        )
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
                route=request.route,
                branch=branch,
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
        analysis_results: AnalysisResults | None = None,
        formal_results: list[Tier3ClaimResult] | None = None,
        route: EffectiveModelRoute | None = None,
        branch: HypothesisBranch | None = None,
        escalation_action: EscalationAction | None = None,
        queued_branch_ids: list[str] | None = None,
    ) -> EvidenceRecord:
        resolved_route = route or self._route_for_phase(phase)
        resolved_branch = branch or self._active_branch(checkpoint)
        return EvidenceRecord(
            iteration=checkpoint.current_iteration,
            timestamp=checkpoint.last_updated,
            phase=phase,
            branch_id=resolved_branch.branch_id,
            branch_strategy=resolved_branch.strategy,
            branch_parent_id=resolved_branch.parent_branch_id,
            branch_rationale=resolved_branch.rationale,
            input_summary=input_summary,
            output_summary=output_summary,
            verdict=verdict,
            tiers_applied=tiers_applied,
            flaws=flaws,
            analysis_results=analysis_results.to_dict() if analysis_results is not None else None,
            formal_verification_results=[item.to_dict() for item in formal_results] if formal_results is not None else None,
            model_used=resolved_route.model,
            provider=resolved_route.provider,
            routing_mode=resolved_route.routing_mode,
            routing_temperature=resolved_route.temperature,
            routing_notes=list(resolved_route.notes),
            tokens_in=0,
            tokens_out=0,
            duration_seconds=0.0,
            escalation_action=escalation_action,
            queued_branch_ids=list(queued_branch_ids or []),
            artifacts=list(checkpoint.artifacts),
        )

    def _route_for_phase(self, phase: str) -> EffectiveModelRoute:
        if phase == "generate":
            return self.routing_plan.generator
        if phase == "verify":
            return self.routing_plan.verifier
        if phase == "escalate":
            return self.routing_plan.orchestrator
        if phase == "analyze":
            return EffectiveModelRoute(
                provider="adapter",
                model=self.config.verification.tier2.default_adapter_family,
                routing_mode=RoutingMode.DIRECT,
                notes=["Tier 2 analysis routing is handled by the adapter boundary."],
            )
        if phase == "formalize":
            return EffectiveModelRoute(
                provider="adapter",
                model=self.config.verification.tier3.backend,
                routing_mode=RoutingMode.DIRECT,
                notes=["Formal verification routing is handled by the orchestrator adapter boundary."],
            )
        return self.routing_plan.reviser

    def _tiers_applied(self, report: VerificationReport) -> list[int]:
        tiers = [1]
        if report.tier2 is not None and (
            report.tier2.analysis_requested or report.tier2.results is not None or report.tier2.analysis_spec is not None
        ):
            tiers.append(2)
        if report.tier3:
            tiers.append(3)
        return tiers

    def _verification_summary(self, report: VerificationReport) -> str:
        if report.verdict is VerificationVerdict.VERIFIED:
            caveat_text = "; ".join(report.caveats) or "No caveats recorded."
            if report.tier2 and report.tier2.results is not None:
                interpretation = report.tier2.interpretation or "Analysis results were incorporated."
                if report.tier3 and all(item.proof_status is not ProofStatus.REQUESTED for item in report.tier3):
                    return (
                        f"Verified with Tier 2 and Tier 3 evidence. {interpretation} "
                        f"Formal statuses: {self._formal_status_summary(report.tier3)}. Caveats: {caveat_text}"
                    )
                return f"Verified with Tier 2 evidence. {interpretation} Caveats: {caveat_text}"
            if report.tier3 and all(item.proof_status is not ProofStatus.REQUESTED for item in report.tier3):
                return (
                    f"Verified with Tier 3 evidence. Formal statuses: {self._formal_status_summary(report.tier3)}. "
                    f"Caveats: {caveat_text}"
                )
            return f"Verified. Caveats: {caveat_text}"
        if report.verdict is VerificationVerdict.CANNOT_VERIFY:
            return f"Cannot verify. Blocker: {report.cannot_verify_reason or 'unspecified'}"
        return f"Flaws found: {self._flaw_summary(report.flaws)}"

    def _flaw_summary(self, flaws: list[str]) -> str:
        return "; ".join(flaws) if flaws else "No flaw details recorded."

    def _formal_status_summary(self, results: list[Tier3ClaimResult]) -> str:
        return "; ".join(f"{item.claim} -> {item.proof_status.value}" for item in results)

    def _require_candidate(self, checkpoint: SessionCheckpoint) -> CandidateSolution:
        if checkpoint.candidate is None:
            raise ValueError("A candidate is required before verification or revision.")
        return checkpoint.candidate

    def _require_report(self, checkpoint: SessionCheckpoint) -> VerificationReport:
        if checkpoint.verification_report is None:
            raise ValueError("A verification report is required before revision.")
        return checkpoint.verification_report

    def _should_run_analysis(self, report: VerificationReport) -> bool:
        return bool(
            self.config.verification.tier2.enabled
            and report.tier2 is not None
            and report.tier2.analysis_requested
            and report.tier2.analysis_spec is not None
            and report.tier2.results is None
        )

    def _should_run_formal(self, report: VerificationReport) -> bool:
        return bool(
            self.config.verification.tier3.enabled
            and report.tier3
            and any(item.proof_status in {ProofStatus.REQUESTED, ProofStatus.PENDING} for item in report.tier3)
        )

    def _analyze(
        self,
        checkpoint: SessionCheckpoint,
        report: VerificationReport,
        analyzer: Analyzer | None,
    ) -> AnalysisResults:
        tier2 = report.tier2
        if tier2 is None or tier2.analysis_spec is None:
            raise ValueError("Tier 2 analysis mediation requires an analysis spec.")

        analysis_spec_payload = dict(tier2.analysis_spec)
        try:
            analysis_spec = AnalysisSpec.from_dict(analysis_spec_payload)
        except (KeyError, TypeError, ValueError) as exc:
            analysis_results = AnalysisResults(
                adapter_family=str(
                    analysis_spec_payload.get("adapter_family", self.config.verification.tier2.default_adapter_family)
                ),
                analysis_kind=str(analysis_spec_payload.get("analysis_kind", "analysis")),
                adapter_name=str(analysis_spec_payload.get("adapter_family", "unknown")),
                adapter_version="0.1.0",
                timestamp=self._timestamp(),
                runtime_seconds=0.0,
                backend=self.config.verification.tier2.default_backend,
                summary="Verifier returned an invalid analysis spec.",
                measurements=[],
                details={"task": analysis_spec_payload.get("task", {})},
                errors=[f"Verifier returned an invalid analysis_spec: {type(exc).__name__}: {exc}"],
            )
        else:
            request = AnalysisRequest(
                session_id=checkpoint.session_id,
                iteration=checkpoint.current_iteration,
                analysis_spec=analysis_spec,
                backend=self.config.verification.tier2.default_backend,
            )
            analysis_results = analyzer(request) if analyzer is not None else self._run_analysis_request(request)
            analysis_spec_payload = analysis_spec.to_dict()

        spec_artifact = self.session_store.write_artifact_json(
            checkpoint.session_id,
            f"iteration_{checkpoint.current_iteration}_analysis_spec.json",
            analysis_spec_payload,
        )
        results_artifact = self.session_store.write_artifact_json(
            checkpoint.session_id,
            f"iteration_{checkpoint.current_iteration}_analysis_results.json",
            analysis_results.to_dict(),
        )
        checkpoint.artifacts = self._merge_artifacts(checkpoint.artifacts, [spec_artifact, results_artifact])
        checkpoint.last_updated = self._timestamp()
        checkpoint.result_summary = f"Completed Tier 2 analysis for candidate {checkpoint.current_iteration}."

        self.session_store.append_evidence(
            checkpoint.session_id,
            self._evidence_record(
                checkpoint=checkpoint,
                phase="analyze",
                verdict=None,
                tiers_applied=[2],
                flaws=[],
                input_summary=f"Analysis requested: {tier2.reason}",
                output_summary=self._analysis_summary(analysis_results),
                analysis_results=analysis_results,
            ),
        )
        self.session_store.save_checkpoint(checkpoint)
        return analysis_results

    def _run_analysis_request(self, request: AnalysisRequest) -> AnalysisResults:
        build_analysis_adapter = _load_analysis_adapter_builder()
        adapter = build_analysis_adapter(
            request.analysis_spec.adapter_family,
            tier2_config=self.config.verification.tier2,
        )
        if adapter is None:
            return AnalysisResults(
                adapter_family=request.analysis_spec.adapter_family,
                analysis_kind=request.analysis_spec.analysis_kind,
                adapter_name=request.analysis_spec.adapter_family,
                adapter_version="0.1.0",
                timestamp=self._timestamp(),
                runtime_seconds=0.0,
                backend=request.backend,
                summary="The requested adapter family is not configured in this environment.",
                measurements=[],
                details={"task": request.analysis_spec.task},
                errors=[
                    f"Adapter family {request.analysis_spec.adapter_family!r} is not configured in this environment.",
                ],
            )
        return adapter.run(request.analysis_spec, request.backend)

    def _attach_analysis_results(self, report: VerificationReport, analysis_results: AnalysisResults) -> None:
        if report.tier2 is None:
            report.tier2 = Tier2Report(
                analysis_requested=True,
                reason="Tier 2 analysis was executed by the orchestrator.",
                analysis_spec=None,
                results=analysis_results.to_dict(),
                interpretation=None,
            )
            return

        if report.tier2.results is None:
            report.tier2.results = analysis_results.to_dict()

    def _formalize(
        self,
        checkpoint: SessionCheckpoint,
        report: VerificationReport,
        formal_verifier: FormalVerifier | None,
        *,
        lifecycle_state: FormalProofLifecycle | None,
    ) -> FormalVerificationResultSet:
        requested_claims = [
            item for item in report.tier3 if item.proof_status in {ProofStatus.REQUESTED, ProofStatus.PENDING}
        ]
        request = FormalVerificationRequest(
            session_id=checkpoint.session_id,
            iteration=checkpoint.current_iteration,
            claims=requested_claims,
            backend=self.config.verification.tier3.backend,
            timeout_seconds=self.config.verification.tier3.timeout_seconds,
            lifecycle_state=lifecycle_state,
            enable_lifecycle=True,
        )
        verifier = formal_verifier or build_formal_verifier(self.config.verification.tier3)
        outcome = verifier(request)
        if isinstance(outcome, FormalVerificationResultSet):
            result_set = outcome
        else:
            result_set = FormalVerificationResultSet(results=list(outcome))

        request_artifact = self.session_store.write_artifact_json(
            checkpoint.session_id,
            f"iteration_{checkpoint.current_iteration}_formal_request.json",
            {
                "backend": request.backend,
                "timeout_seconds": request.timeout_seconds,
                "enable_lifecycle": request.enable_lifecycle,
                "lifecycle_state": (
                    request.lifecycle_state.to_dict() if request.lifecycle_state is not None else None
                ),
                "claims": [item.to_dict() for item in request.claims],
            },
        )
        results_artifact = self.session_store.write_artifact_json(
            checkpoint.session_id,
            f"iteration_{checkpoint.current_iteration}_formal_results.json",
            {
                "backend": request.backend,
                "pending": result_set.pending,
                "results": [item.to_dict() for item in result_set.results],
            },
        )
        artifact_paths = [request_artifact, results_artifact]
        if result_set.lifecycle_state is not None:
            artifact_paths.append(
                self.session_store.write_artifact_json(
                    checkpoint.session_id,
                    f"iteration_{checkpoint.current_iteration}_formal_lifecycle.json",
                    result_set.lifecycle_state.to_dict(),
                )
            )
        if result_set.transport_artifact is not None:
            artifact_paths.append(
                self.session_store.write_artifact_json(
                    checkpoint.session_id,
                    f"iteration_{checkpoint.current_iteration}_formal_transport.json",
                    result_set.transport_artifact,
                )
            )
        checkpoint.artifacts = self._merge_artifacts(checkpoint.artifacts, artifact_paths)
        checkpoint.last_updated = self._timestamp()
        checkpoint.result_summary = (
            f"Tier 3 proof polling remains in progress for candidate {checkpoint.current_iteration}."
            if result_set.pending
            else f"Completed Tier 3 formal mediation for candidate {checkpoint.current_iteration}."
        )

        self.session_store.append_evidence(
            checkpoint.session_id,
            self._evidence_record(
                checkpoint=checkpoint,
                phase="formalize",
                verdict=None,
                tiers_applied=[3],
                flaws=[],
                input_summary=f"Formal verification requested for {len(request.claims)} claim(s).",
                output_summary=self._formal_summary(result_set),
                formal_results=result_set.results,
            ),
        )
        return result_set

    def _attach_formal_results(self, report: VerificationReport, formal_results: list[Tier3ClaimResult]) -> None:
        if not report.tier3:
            report.tier3 = list(formal_results)
            return

        results_by_claim = {item.claim: item for item in formal_results}
        merged: list[Tier3ClaimResult] = []
        for item in report.tier3:
            if item.claim in results_by_claim:
                merged.append(results_by_claim.pop(item.claim))
            else:
                merged.append(item)
        merged.extend(results_by_claim.values())
        report.tier3 = merged

    def _analysis_summary(self, analysis_results: AnalysisResults) -> str:
        if analysis_results.errors:
            return f"Analysis returned errors: {'; '.join(analysis_results.errors)}"
        return (
            f"Analysis via {analysis_results.adapter_family} ({analysis_results.analysis_kind}) on "
            f"{analysis_results.backend.value} produced {len(analysis_results.measurements)} measurement(s). "
            f"{analysis_results.summary}"
        )

    def _formal_summary(self, result_set: FormalVerificationResultSet) -> str:
        summary = f"Formal verification results: {self._formal_status_summary(result_set.results)}"
        if result_set.pending:
            return f"{summary} Proof polling remains in progress."
        return summary

    def _merge_artifacts(self, current: list[str], additions: list[str]) -> list[str]:
        merged = list(current)
        for artifact in additions:
            if artifact not in merged:
                merged.append(artifact)
        return merged

    def _timestamp(self) -> str:
        return _isoformat(self.clock())
