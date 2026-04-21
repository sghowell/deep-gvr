from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from .contracts import ReleaseCheckStatus, ReleasePublicationManifest
from .evaluation import (
    CommandExecutor,
    LiveEvalConfig,
    BenchmarkConsistencyReport,
    run_repeated_benchmark_suite,
    write_benchmark_consistency_report,
)
from .release_surface import (
    evaluate_auto_improve_policy_manifest,
    load_publication_manifest,
    project_version,
    publication_manifest_path,
    repo_root,
)

_DEFAULT_DETERMINISTIC_SUBSET = "analysis-full"
_DEFAULT_DETERMINISTIC_REPEAT = 3
_DEFAULT_LIVE_SUBSET = "live-expansion"
_DEFAULT_LIVE_REPEAT = 2


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


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(repo_root()))
    except ValueError:
        return str(path)


@dataclass(slots=True)
class AutoImproveModeEvaluation:
    mode: str
    status: str
    subset: str
    repeat_count: int
    baseline_auto_improve: bool
    experimental_auto_improve: bool
    selected_case_ids: list[str]
    baseline_report_path: str
    experimental_report_path: str
    baseline_summary: dict[str, Any]
    experimental_summary: dict[str, Any]
    drift_detected: bool
    summary_changed: bool
    case_outcomes_changed: bool
    differing_case_ids: list[str]
    notes: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AutoImproveModeEvaluation":
        return cls(
            mode=data["mode"],
            status=data["status"],
            subset=data["subset"],
            repeat_count=int(data["repeat_count"]),
            baseline_auto_improve=bool(data["baseline_auto_improve"]),
            experimental_auto_improve=bool(data["experimental_auto_improve"]),
            selected_case_ids=list(data.get("selected_case_ids", [])),
            baseline_report_path=data.get("baseline_report_path", ""),
            experimental_report_path=data.get("experimental_report_path", ""),
            baseline_summary=dict(data.get("baseline_summary", {})),
            experimental_summary=dict(data.get("experimental_summary", {})),
            drift_detected=bool(data["drift_detected"]),
            summary_changed=bool(data["summary_changed"]),
            case_outcomes_changed=bool(data["case_outcomes_changed"]),
            differing_case_ids=list(data.get("differing_case_ids", [])),
            notes=list(data.get("notes", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class AutoImprovePolicyEvaluation:
    manifest_path: str
    baseline_status: ReleaseCheckStatus
    experimental_status: ReleaseCheckStatus
    experimental_blocks_release: bool
    notes: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AutoImprovePolicyEvaluation":
        return cls(
            manifest_path=data["manifest_path"],
            baseline_status=ReleaseCheckStatus(data["baseline_status"]),
            experimental_status=ReleaseCheckStatus(data["experimental_status"]),
            experimental_blocks_release=bool(data["experimental_blocks_release"]),
            notes=list(data.get("notes", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class AutoImproveIsolationReport:
    manifest_path: str
    manifest_digest_before: str
    manifest_digest_after: str
    manifest_unchanged: bool
    worktree_status_before: list[str]
    worktree_status_after: list[str]
    worktree_clean_before: bool
    worktree_clean_after: bool
    worktree_unchanged: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AutoImproveIsolationReport":
        return cls(
            manifest_path=data["manifest_path"],
            manifest_digest_before=data["manifest_digest_before"],
            manifest_digest_after=data["manifest_digest_after"],
            manifest_unchanged=bool(data["manifest_unchanged"]),
            worktree_status_before=list(data.get("worktree_status_before", [])),
            worktree_status_after=list(data.get("worktree_status_after", [])),
            worktree_clean_before=bool(data["worktree_clean_before"]),
            worktree_clean_after=bool(data["worktree_clean_after"]),
            worktree_unchanged=bool(data["worktree_unchanged"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class AutoImproveRecommendation:
    decision: str
    summary: str
    rationale: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AutoImproveRecommendation":
        return cls(
            decision=data["decision"],
            summary=data["summary"],
            rationale=list(data.get("rationale", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class AutoImproveEvaluationReport:
    skill_name: str
    version: str
    generated_at: str
    output_root: str
    runtime_binding: str
    repo_runtime_consumes_auto_improve: bool
    evaluations: list[AutoImproveModeEvaluation]
    policy: AutoImprovePolicyEvaluation
    isolation: AutoImproveIsolationReport
    recommendation: AutoImproveRecommendation

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AutoImproveEvaluationReport":
        return cls(
            skill_name=data["skill_name"],
            version=data["version"],
            generated_at=data["generated_at"],
            output_root=data["output_root"],
            runtime_binding=data["runtime_binding"],
            repo_runtime_consumes_auto_improve=bool(data["repo_runtime_consumes_auto_improve"]),
            evaluations=[AutoImproveModeEvaluation.from_dict(item) for item in data.get("evaluations", [])],
            policy=AutoImprovePolicyEvaluation.from_dict(data["policy"]),
            isolation=AutoImproveIsolationReport.from_dict(data["isolation"]),
            recommendation=AutoImproveRecommendation.from_dict(data["recommendation"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


def evaluate_auto_improve(
    suite_path: str | Path,
    *,
    output_root: str | Path | None = None,
    deterministic_subset: str = _DEFAULT_DETERMINISTIC_SUBSET,
    deterministic_repeat_count: int = _DEFAULT_DETERMINISTIC_REPEAT,
    include_live: bool = False,
    live_subset: str = _DEFAULT_LIVE_SUBSET,
    live_repeat_count: int = _DEFAULT_LIVE_REPEAT,
    config_path: str | Path | None = None,
    live_config: LiveEvalConfig | None = None,
    executor: CommandExecutor | None = None,
    clock: Callable[[], datetime] | None = None,
) -> AutoImproveEvaluationReport:
    clock = clock or _utc_now
    now = clock()
    resolved_output_root = _resolve_output_root(output_root, now)
    resolved_output_root.mkdir(parents=True, exist_ok=True)

    manifest_path = publication_manifest_path()
    manifest_before = manifest_path.read_text(encoding="utf-8")
    digest_before = _sha256(manifest_before)
    worktree_status_before = _git_status_lines(repo_root())

    baseline_manifest = load_publication_manifest()
    experimental_manifest = _manifest_with_auto_improve(baseline_manifest, True)
    policy = _evaluate_policy(manifest_path, baseline_manifest, experimental_manifest)

    evaluations = [
        _run_mode_evaluation(
            mode="deterministic",
            suite_path=suite_path,
            subset=deterministic_subset,
            repeat_count=deterministic_repeat_count,
            output_root=resolved_output_root / "deterministic",
            config_path=None,
            live_config=None,
            executor=None,
        )
    ]

    if include_live:
        evaluations.append(
            _run_mode_evaluation(
                mode="live",
                suite_path=suite_path,
                subset=live_subset,
                repeat_count=live_repeat_count,
                output_root=resolved_output_root / "live",
                config_path=config_path,
                live_config=live_config or LiveEvalConfig(),
                executor=executor,
            )
        )
    else:
        evaluations.append(
            AutoImproveModeEvaluation(
                mode="live",
                status="skipped",
                subset=live_subset,
                repeat_count=live_repeat_count,
                baseline_auto_improve=False,
                experimental_auto_improve=True,
                selected_case_ids=[],
                baseline_report_path="",
                experimental_report_path="",
                baseline_summary={},
                experimental_summary={},
                drift_detected=False,
                summary_changed=False,
                case_outcomes_changed=False,
                differing_case_ids=[],
                notes=["Live evaluation was not requested for this run."],
            )
        )

    manifest_after = manifest_path.read_text(encoding="utf-8")
    digest_after = _sha256(manifest_after)
    worktree_status_after = _git_status_lines(repo_root())
    isolation = AutoImproveIsolationReport(
        manifest_path=_display_path(manifest_path),
        manifest_digest_before=digest_before,
        manifest_digest_after=digest_after,
        manifest_unchanged=digest_before == digest_after,
        worktree_status_before=worktree_status_before,
        worktree_status_after=worktree_status_after,
        worktree_clean_before=not worktree_status_before,
        worktree_clean_after=not worktree_status_after,
        worktree_unchanged=worktree_status_before == worktree_status_after,
    )

    report = AutoImproveEvaluationReport(
        skill_name=baseline_manifest.name,
        version=project_version(),
        generated_at=_isoformat(now),
        output_root=_display_path(resolved_output_root),
        runtime_binding="publication_manifest_only",
        repo_runtime_consumes_auto_improve=False,
        evaluations=evaluations,
        policy=policy,
        isolation=isolation,
        recommendation=_recommend(evaluations, policy, isolation),
    )
    return report


def write_auto_improve_evaluation_report(report: AutoImproveEvaluationReport, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")


def format_auto_improve_evaluation_overview(report: AutoImproveEvaluationReport) -> list[str]:
    lines = [
        f"decision={report.recommendation.decision}",
        f"runtime_binding={report.runtime_binding}",
        (
            "policy="
            f"{report.policy.baseline_status.value}->{report.policy.experimental_status.value}"
        ),
        (
            "isolation="
            f"manifest_unchanged={report.isolation.manifest_unchanged} "
            f"worktree_unchanged={report.isolation.worktree_unchanged}"
        ),
    ]
    for evaluation in report.evaluations:
        lines.append(
            f"{evaluation.mode}: status={evaluation.status} subset={evaluation.subset} "
            f"repeat={evaluation.repeat_count} drift={evaluation.drift_detected} "
            f"diff_cases={len(evaluation.differing_case_ids)}"
        )
        if evaluation.notes:
            lines.append(f"  note: {evaluation.notes[0]}")
    return lines


def _run_mode_evaluation(
    *,
    mode: str,
    suite_path: str | Path,
    subset: str,
    repeat_count: int,
    output_root: Path,
    config_path: str | Path | None,
    live_config: LiveEvalConfig | None,
    executor: CommandExecutor | None,
) -> AutoImproveModeEvaluation:
    if mode == "live" and config_path is None:
        return AutoImproveModeEvaluation(
            mode=mode,
            status="skipped",
            subset=subset,
            repeat_count=repeat_count,
            baseline_auto_improve=False,
            experimental_auto_improve=True,
            selected_case_ids=[],
            baseline_report_path="",
            experimental_report_path="",
            baseline_summary={},
            experimental_summary={},
            drift_detected=False,
            summary_changed=False,
            case_outcomes_changed=False,
            differing_case_ids=[],
            notes=["Live evaluation requires --config pointing at a real operator runtime config."],
        )

    output_root.mkdir(parents=True, exist_ok=True)
    baseline_path = output_root / "baseline_consistency.json"
    experimental_path = output_root / "experimental_consistency.json"
    baseline_report = run_repeated_benchmark_suite(
        suite_path,
        repeat_count=repeat_count,
        mode=mode,
        config_path=config_path,
        output_root=output_root / "baseline",
        subset=subset,
        live_config=live_config,
        executor=executor,
    )
    experimental_report = run_repeated_benchmark_suite(
        suite_path,
        repeat_count=repeat_count,
        mode=mode,
        config_path=config_path,
        output_root=output_root / "experimental",
        subset=subset,
        live_config=live_config,
        executor=executor,
    )
    write_benchmark_consistency_report(baseline_report, baseline_path)
    write_benchmark_consistency_report(experimental_report, experimental_path)

    summary_changed = baseline_report.summary.to_dict() != experimental_report.summary.to_dict()
    differing_case_ids = _differing_case_ids(baseline_report, experimental_report)
    case_outcomes_changed = bool(differing_case_ids)
    drift_detected = summary_changed or case_outcomes_changed
    notes: list[str] = []
    if drift_detected:
        notes.append("Observed differing benchmark outcomes after toggling the release-policy variant.")
    else:
        notes.append("No repo-local benchmark drift was observed after toggling the release-policy variant.")
    if mode == "live":
        notes.append(
            "The live comparison reuses the same runtime config because auto_improve is not a repo-local runtime input."
        )

    return AutoImproveModeEvaluation(
        mode=mode,
        status="completed",
        subset=subset,
        repeat_count=repeat_count,
        baseline_auto_improve=False,
        experimental_auto_improve=True,
        selected_case_ids=list(baseline_report.selected_case_ids),
        baseline_report_path=_display_path(baseline_path),
        experimental_report_path=_display_path(experimental_path),
        baseline_summary=baseline_report.summary.to_dict(),
        experimental_summary=experimental_report.summary.to_dict(),
        drift_detected=drift_detected,
        summary_changed=summary_changed,
        case_outcomes_changed=case_outcomes_changed,
        differing_case_ids=differing_case_ids,
        notes=notes,
    )


def _differing_case_ids(
    baseline_report: BenchmarkConsistencyReport,
    experimental_report: BenchmarkConsistencyReport,
) -> list[str]:
    baseline_cases = {case.id: case.to_dict() for case in baseline_report.cases}
    experimental_cases = {case.id: case.to_dict() for case in experimental_report.cases}
    case_ids = list(dict.fromkeys([*baseline_cases, *experimental_cases]))
    return [case_id for case_id in case_ids if baseline_cases.get(case_id) != experimental_cases.get(case_id)]


def _evaluate_policy(
    manifest_path: Path,
    baseline_manifest: ReleasePublicationManifest,
    experimental_manifest: ReleasePublicationManifest,
) -> AutoImprovePolicyEvaluation:
    baseline_check = evaluate_auto_improve_policy_manifest(baseline_manifest)
    experimental_check = evaluate_auto_improve_policy_manifest(experimental_manifest)
    notes = [
        "Baseline policy remains release-ready only when auto_improve is false.",
        "The experimental variant intentionally models the proposed opt-in state without mutating the checked-in manifest.",
    ]
    return AutoImprovePolicyEvaluation(
        manifest_path=_display_path(manifest_path),
        baseline_status=baseline_check.status,
        experimental_status=experimental_check.status,
        experimental_blocks_release=experimental_check.status is ReleaseCheckStatus.BLOCKED,
        notes=notes,
    )


def _recommend(
    evaluations: list[AutoImproveModeEvaluation],
    policy: AutoImprovePolicyEvaluation,
    isolation: AutoImproveIsolationReport,
) -> AutoImproveRecommendation:
    rationale: list[str] = []
    if not isolation.manifest_unchanged:
        rationale.append("The evaluation mutated the checked-in publication manifest, so the run is not trustworthy.")
    if not isolation.worktree_unchanged:
        rationale.append("The evaluation changed the worktree state, so rollback guarantees are not yet strong enough.")

    completed_evaluations = [item for item in evaluations if item.status == "completed"]
    if any(item.drift_detected for item in completed_evaluations):
        rationale.append("At least one completed benchmark comparison showed observable drift across policy variants.")
    else:
        rationale.append("Completed benchmark comparisons showed no repo-local drift across policy variants.")

    if policy.experimental_blocks_release:
        rationale.append("The experimental variant still violates the documented public-release default and remains blocked.")

    rationale.append(
        "The repo runtime does not consume auto_improve directly; the field is currently a release-surface policy input."
    )

    live_evaluation = next((item for item in evaluations if item.mode == "live"), None)
    if live_evaluation is None or live_evaluation.status != "completed":
        rationale.append("No completed live operator comparison was collected in this run.")

    return AutoImproveRecommendation(
        decision="disabled_by_default",
        summary=(
            "Keep auto_improve disabled by default until a future evaluation shows a real operator benefit "
            "without introducing benchmark drift or weakening release-surface rollback guarantees."
        ),
        rationale=rationale,
    )


def _manifest_with_auto_improve(
    manifest: ReleasePublicationManifest,
    enabled: bool,
) -> ReleasePublicationManifest:
    payload = manifest.to_dict()
    payload["auto_improve"] = enabled
    return ReleasePublicationManifest.from_dict(payload)


def _resolve_output_root(output_root: str | Path | None, now: datetime) -> Path:
    if output_root is not None:
        return Path(output_root)
    run_id = now.strftime("%Y%m%dT%H%M%SZ")
    return Path("/tmp") / f"deep-gvr-auto-improve-{run_id}"


def _sha256(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _git_status_lines(root: Path) -> list[str]:
    completed = subprocess.run(
        ["git", "status", "--short"],
        check=False,
        capture_output=True,
        text=True,
        cwd=root,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "git status failed"
        return [f"<git-status-error: {message}>"]
    return [line for line in completed.stdout.splitlines() if line.strip()]
