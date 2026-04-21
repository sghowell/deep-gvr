from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from .contracts import (
    CodexNativeDelegationCapability,
    CodexNativeDelegationEvaluationReport,
    CodexNativeDelegationEvidence,
    CodexNativeDelegationRecommendation,
    ReleaseCheckStatus,
)
from .release_surface import project_version, repo_root


@dataclass(slots=True)
class CommandExecutionResult:
    returncode: int
    stdout: str
    stderr: str


CommandExecutor = Callable[[list[str], Path], CommandExecutionResult]

_DEFAULT_OUTPUT_PREFIX = "deep-gvr-codex-native-delegation"
_CODEX_APP_DOC_URL = "https://openai.com/index/introducing-the-codex-app/"
_CODEX_PRODUCT_DOC_URL = "https://openai.com/index/codex-for-almost-everything/"
_CODEX_CLOUD_DOC_URL = "https://platform.openai.com/docs/codex/overview"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _isoformat(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _default_executor(command: list[str], cwd: Path) -> CommandExecutionResult:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return CommandExecutionResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _resolve_output_root(output_root: str | Path | None, now: datetime) -> Path:
    if output_root is not None:
        return Path(output_root).expanduser().resolve()
    return Path("/tmp") / f"{_DEFAULT_OUTPUT_PREFIX}-{now.strftime('%Y%m%dT%H%M%SZ')}"


def _repo_evidence(path: str, summary: str) -> CodexNativeDelegationEvidence:
    return CodexNativeDelegationEvidence(
        kind="repo_file",
        reference=path,
        summary=summary,
    )


def _official_doc(reference: str, summary: str) -> CodexNativeDelegationEvidence:
    return CodexNativeDelegationEvidence(
        kind="official_doc",
        reference=reference,
        summary=summary,
    )


def _probe_codex_binary(
    codex_binary: str,
    *,
    root: Path,
    executor: CommandExecutor,
    verify_path: bool,
) -> tuple[bool, str, str]:
    if verify_path:
        resolved = shutil.which(codex_binary)
        if resolved is None:
            return False, "", f"{codex_binary} is not currently available on PATH."
    try:
        result = executor([codex_binary, "--version"], root)
    except FileNotFoundError:
        return False, "", f"{codex_binary} is not currently available on PATH."
    output = (result.stdout or result.stderr).strip()
    if result.returncode != 0:
        return False, "", output or f"{codex_binary} --version exited with code {result.returncode}."
    version = output.splitlines()[0].strip() if output else ""
    return True, version, ""


def _build_capabilities() -> list[CodexNativeDelegationCapability]:
    return [
        CodexNativeDelegationCapability(
            capability_id="native_role_execution",
            title="Native role-isolated runtime execution",
            current_boundary="runtime_backend",
            status=ReleaseCheckStatus.READY,
            promote_into_runtime=True,
            promotion_decision="already_realized",
            summary=(
                "The highest-value Codex-native delegation behavior for deep-gvr is already runtime-owned: "
                "Generator, Verifier, and Reviser execute as separate native Codex role calls over the typed loop."
            ),
            rationale=[
                "The native codex_local backend already drives Tier1LoopRunner through separate Generator, Verifier, and Reviser calls.",
                "The runtime preserves checkpoint, evidence, escalation, Tier 2, and Tier 3 ownership while Codex handles role execution.",
                "This captures the backend value of Codex-native delegation without coupling the runtime to Codex app-state internals.",
            ],
            evidence=[
                _repo_evidence(
                    "src/deep_gvr/orchestrator.py",
                    "CodexLocalOrchestratorRunner executes Generator, Verifier, and Reviser as separate native role calls.",
                ),
                _repo_evidence(
                    "src/deep_gvr/cli.py",
                    "CLI capability evidence already records codex_native_role_execution for native backend runs.",
                ),
                _repo_evidence(
                    "plans/58-codex-native-subagent-backend.md",
                    "Plan 58 established the native role-separated Codex backend boundary.",
                ),
                _repo_evidence(
                    "plans/60-codex-runtime-hardening.md",
                    "Plan 60 hardened transcript and capability-evidence capture for native Codex role execution.",
                ),
            ],
        ),
        CodexNativeDelegationCapability(
            capability_id="parallel_work_ownership",
            title="Parallel work ownership and worktree coordination",
            current_boundary="operator_pack",
            status=ReleaseCheckStatus.ATTENTION,
            promote_into_runtime=False,
            promotion_decision="keep_operator_pack",
            summary=(
                "Parallel multi-agent work ownership should stay in the shipped Codex subagent operator pack rather "
                "than becoming a runtime scheduling API inside deep-gvr."
            ),
            rationale=[
                "The repo already ships a checked-in subagent pack with safe worktree, scope, and integration rules.",
                "deep-gvr's runtime value is typed evidence and verification orchestration, not direct management of concurrent Codex agents.",
                "Promoting parallel work ownership into the runtime would duplicate product-managed worktree and thread behavior without adding stronger verification guarantees.",
            ],
            evidence=[
                _repo_evidence(
                    "docs/codex-subagents.md",
                    "The current subagent surface is explicitly documented as an operator coordination layer rather than the backend itself.",
                ),
                _repo_evidence(
                    "codex_subagents/catalog.json",
                    "The shipped Codex subagent pack already encodes disjoint scopes, worktree isolation, and main-agent integration ownership.",
                ),
                _official_doc(
                    _CODEX_APP_DOC_URL,
                    "OpenAI's Codex app docs describe multi-agent threads and built-in worktrees as product-managed coordination features.",
                ),
            ],
        ),
        CodexNativeDelegationCapability(
            capability_id="delegation_observability",
            title="Delegation observability and evidence capture",
            current_boundary="repo_owned_evidence",
            status=ReleaseCheckStatus.READY,
            promote_into_runtime=True,
            promotion_decision="already_realized",
            summary=(
                "The observability that deep-gvr actually needs is already repo-owned through transcripts, parsed role payloads, "
                "capability-evidence artifacts, and review/QA evidence bundles."
            ),
            rationale=[
                "The native backend transcript captures per-role selected routes, parsed response payloads, and failures.",
                "Review/QA and SSH/devbox flows already prepare repo-owned evidence bundles before live human or Codex inspection.",
                "What remains outside the repo contract is Codex's own internal thread state, which is not necessary for deep-gvr's typed verification evidence model.",
            ],
            evidence=[
                _repo_evidence(
                    "src/deep_gvr/orchestrator.py",
                    "Native Codex role transcripts persist selected routes, parsed response objects, and structured failures.",
                ),
                _repo_evidence(
                    "src/deep_gvr/cli.py",
                    "CLI capability evidence emits codex_native_role_execution without conflating it with Hermes-only delegated-capability probes.",
                ),
                _repo_evidence(
                    "docs/contracts-and-artifacts.md",
                    "The standard artifact surface already documents Codex-native transcript and capability-evidence files.",
                ),
                _repo_evidence(
                    "plans/62-codex-review-qa-execution.md",
                    "Plan 62 added repo-owned evidence workflows for PR review and public-docs visual QA.",
                ),
            ],
        ),
        CodexNativeDelegationCapability(
            capability_id="live_subagent_state_integration",
            title="Live Codex subagent-state integration",
            current_boundary="product_managed",
            status=ReleaseCheckStatus.BLOCKED,
            promote_into_runtime=False,
            promotion_decision="defer_product_owned",
            summary=(
                "deep-gvr should not attempt to own Codex's live subagent state, spawning, or app-managed delegation internals "
                "until OpenAI exposes a stable repo-usable contract for that surface."
            ),
            rationale=[
                "Current official Codex docs describe multi-agent threads, cloud tasks, browser/computer-use, and remote devboxes as product-managed client capabilities.",
                "The repo can export prompts, install skills/plugins, prepare evidence, and run the native backend, but it cannot reliably own Codex's internal live delegation state today.",
                "Treating live subagent state as a backend contract now would overclaim support and create coupling to product behavior outside the repo's control.",
            ],
            blocking_dependencies=[
                "A stable OpenAI-supported programmatic contract for live Codex delegation or subagent-state control.",
                "A repo-owned artifact and resume model that can honestly represent that external state without guessing.",
            ],
            evidence=[
                _official_doc(
                    _CODEX_APP_DOC_URL,
                    "The Codex app docs describe a product-managed command center for multiple agents and worktrees, not a repo-controlled delegation API.",
                ),
                _official_doc(
                    _CODEX_PRODUCT_DOC_URL,
                    "The April 16, 2026 Codex product update expands product-managed capabilities such as browser, computer use, SSH/devboxes, and ongoing work.",
                ),
                _official_doc(
                    _CODEX_CLOUD_DOC_URL,
                    "OpenAI's Codex cloud overview describes parallel background delegation in cloud sandboxes as a separate Codex product surface.",
                ),
                _repo_evidence(
                    "docs/codex-subagents.md",
                    "The current repo docs already keep the boundary honest: the repo does not claim to configure Codex's live subagent runtime or app state.",
                ),
            ],
        ),
    ]


def _build_recommendation() -> CodexNativeDelegationRecommendation:
    return CodexNativeDelegationRecommendation(
        decision="keep_current_boundary",
        summary=(
            "Keep the current Codex boundary: native role-separated codex_local execution stays runtime-owned, while deeper "
            "parallel delegation and live subagent state remain operator-pack or product-managed surfaces."
        ),
        rationale=[
            "The backend value of Codex-native delegation is already captured by the realized native role-separated codex_local runtime.",
            "The repo already ships the right operator surfaces for parallel work, review, visual QA, SSH/devbox execution, and remote bootstrap.",
            "Deeper live delegation integration would currently overstep into product-managed Codex state without a stable repo-owned contract.",
        ],
        next_slice="plans/64-codex-cloud-surface.md",
    )


def evaluate_codex_native_delegation(
    *,
    output_root: str | Path | None = None,
    codex_binary: str = "codex",
    executor: CommandExecutor | None = None,
    clock: Callable[[], datetime] | None = None,
) -> CodexNativeDelegationEvaluationReport:
    effective_root = repo_root()
    clock = clock or _utc_now
    now = clock()
    resolved_output_root = _resolve_output_root(output_root, now)
    resolved_output_root.mkdir(parents=True, exist_ok=True)
    using_default_executor = executor is None
    executor = executor or _default_executor

    codex_available, codex_version, codex_note = _probe_codex_binary(
        codex_binary,
        root=effective_root,
        executor=executor,
        verify_path=using_default_executor,
    )
    notes: list[str] = []
    overall_status = ReleaseCheckStatus.READY
    if codex_available:
        notes.append(f"Observed local Codex binary version via `{codex_binary} --version`: {codex_version}.")
    else:
        overall_status = ReleaseCheckStatus.ATTENTION
        notes.append(codex_note)

    return CodexNativeDelegationEvaluationReport(
        skill_name="deep-gvr",
        version=project_version(effective_root),
        generated_at=_isoformat(now),
        repo_root=str(effective_root),
        output_root=str(resolved_output_root),
        overall_status=overall_status,
        codex_binary=codex_binary,
        codex_available=codex_available,
        codex_version=codex_version,
        evaluation_scope=[
            "native_codex_role_backend",
            "exported_subagent_operator_pack",
            "repo_owned_evidence_surface",
            "current_official_codex_product_boundary",
        ],
        notes=notes,
        capabilities=_build_capabilities(),
        recommendation=_build_recommendation(),
    )


def write_codex_native_delegation_evaluation_report(
    report: CodexNativeDelegationEvaluationReport,
    output_path: str | Path,
) -> Path:
    resolved_output_path = Path(output_path).expanduser().resolve()
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    return resolved_output_path


def format_codex_native_delegation_overview(
    report: CodexNativeDelegationEvaluationReport,
) -> list[str]:
    lines = [
        f"Codex native delegation evaluation: {report.overall_status.value}",
        f"Recommendation: {report.recommendation.decision}",
        report.recommendation.summary,
    ]
    if report.codex_available and report.codex_version:
        lines.append(f"Observed Codex version: {report.codex_version}")
    elif report.notes:
        lines.append(report.notes[0])
    return lines
