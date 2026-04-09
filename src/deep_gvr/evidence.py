from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable

from .contracts import (
    EvidenceRecord,
    HermesMemorySummary,
    ParallaxAsset,
    ParallaxEvidenceEntry,
    ParallaxEvidenceManifest,
    SessionCheckpoint,
)

_ENTRY_SEPARATOR = "§"


def infer_hermes_home(root_directory: str | Path, hermes_home: str | Path | None = None) -> Path:
    if hermes_home is not None:
        return Path(hermes_home).expanduser()
    configured = os.getenv("HERMES_HOME")
    if configured:
        return Path(configured).expanduser()

    root = Path(root_directory).expanduser()
    if root.name == "sessions":
        if root.parent.name == "deep-gvr":
            return root.parent.parent
        return root.parent
    return root


def hermes_memory_file(root_directory: str | Path, hermes_home: str | Path | None = None) -> Path:
    return infer_hermes_home(root_directory, hermes_home=hermes_home) / "memories" / "MEMORY.md"


def build_memory_summary(
    *,
    root_directory: str | Path,
    checkpoint: SessionCheckpoint,
    evidence_records: Iterable[EvidenceRecord],
    checkpoint_file: Path,
    memory_file: Path,
    generated_at: str,
    persisted_to_memory: bool,
) -> HermesMemorySummary:
    evidence = list(evidence_records)
    tiers_observed = sorted({tier for record in evidence for tier in record.tiers_applied})
    artifacts = _unique(
        list(checkpoint.artifacts)
        + [artifact for record in evidence for artifact in record.artifacts]
    )
    parallax_manifest_file = checkpoint.parallax_manifest_file
    entry = (
        f"[deep-gvr:{checkpoint.session_id}] {checkpoint.domain} session "
        f"\"{_truncate(checkpoint.problem, 120)}\" is {checkpoint.status} with verdict "
        f"{checkpoint.final_verdict} after {len(checkpoint.verdict_history)} iteration(s). "
        f"Summary: {_truncate(checkpoint.result_summary, 240)} "
        f"Evidence: {checkpoint.evidence_file}. Checkpoint: {_relative_to_root(root_directory, checkpoint_file)}. "
        f"Manifest: {parallax_manifest_file}."
    )
    return HermesMemorySummary(
        session_id=checkpoint.session_id,
        generated_at=generated_at,
        problem=checkpoint.problem,
        domain=checkpoint.domain,
        status=checkpoint.status,
        final_verdict=checkpoint.final_verdict,
        iterations=len(checkpoint.verdict_history),
        result_summary=checkpoint.result_summary,
        evidence_file=checkpoint.evidence_file,
        checkpoint_file=_relative_to_root(root_directory, checkpoint_file),
        parallax_manifest_file=parallax_manifest_file,
        persisted_to_memory=persisted_to_memory,
        memory_file=str(memory_file),
        tiers_observed=tiers_observed,
        artifacts=artifacts,
        memory_entry=entry,
    )


def persist_memory_summary(memory_file: Path, summary: HermesMemorySummary) -> None:
    memory_file.parent.mkdir(parents=True, exist_ok=True)
    marker = f"[deep-gvr:{summary.session_id}]"
    entries = _read_memory_entries(memory_file)
    filtered = [entry for entry in entries if not entry.startswith(marker)]
    filtered.append(summary.memory_entry.strip())
    _atomic_write_text(memory_file, _join_memory_entries(filtered))


def build_parallax_manifest(
    *,
    root_directory: str | Path,
    checkpoint: SessionCheckpoint,
    evidence_records: Iterable[EvidenceRecord],
    checkpoint_file: Path,
    artifacts_dir: Path,
    memory_summary: HermesMemorySummary,
) -> ParallaxEvidenceManifest:
    evidence = list(evidence_records)
    assets: list[ParallaxAsset] = []
    seen_paths: set[str] = set()

    def add_asset(path: str, kind: str, media_type: str, *, phase: str | None = None, iteration: int | None = None) -> None:
        if path in seen_paths:
            return
        seen_paths.add(path)
        assets.append(
            ParallaxAsset(
                path=path,
                kind=kind,
                media_type=media_type,
                phase=phase,
                iteration=iteration,
            )
        )

    add_asset(_relative_to_root(root_directory, checkpoint_file), "session_checkpoint", "application/json")
    add_asset(checkpoint.evidence_file, "evidence_log", "application/x-ndjson")
    add_asset(checkpoint.memory_summary_file, "session_memory_summary", "application/json")
    add_asset(checkpoint.parallax_manifest_file, "parallax_manifest", "application/json")
    if memory_summary.memory_file:
        add_asset(memory_summary.memory_file, "hermes_memory", "text/markdown")

    for artifact in checkpoint.artifacts:
        add_asset(
            artifact,
            _infer_asset_kind(artifact),
            _infer_media_type(artifact),
        )
    for record in evidence:
        for artifact in record.artifacts:
            add_asset(
                artifact,
                _infer_asset_kind(artifact),
                _infer_media_type(artifact),
                phase=record.phase,
                iteration=record.iteration,
            )

    return ParallaxEvidenceManifest(
        format="parallax-compatible-evidence-manifest",
        manifest_version="1.0",
        session_id=checkpoint.session_id,
        generated_at=memory_summary.generated_at,
        problem=checkpoint.problem,
        domain=checkpoint.domain,
        status=checkpoint.status,
        final_verdict=checkpoint.final_verdict,
        result_summary=checkpoint.result_summary,
        evidence_file=checkpoint.evidence_file,
        checkpoint_file=_relative_to_root(root_directory, checkpoint_file),
        memory_summary_file=checkpoint.memory_summary_file,
        artifacts_dir=_relative_to_root(root_directory, artifacts_dir),
        hermes_memory_file=memory_summary.memory_file,
        persisted_to_memory=memory_summary.persisted_to_memory,
        evidence_records=[
            ParallaxEvidenceEntry(
                iteration=record.iteration,
                phase=record.phase,
                verdict=record.verdict.value if record.verdict is not None else None,
                tiers_applied=list(record.tiers_applied),
                input_summary=record.input_summary,
                output_summary=record.output_summary,
                artifacts=list(record.artifacts),
            )
            for record in evidence
        ],
        assets=assets,
    )


def _infer_asset_kind(path: str) -> str:
    name = Path(path).name
    if name == "checkpoint.json":
        return "session_checkpoint"
    if name.endswith(".jsonl"):
        return "evidence_log"
    if name == "session_memory_summary.json":
        return "session_memory_summary"
    if name == "parallax_manifest.json":
        return "parallax_manifest"
    if "_analysis_spec." in name:
        return "tier2_analysis_spec"
    if "_analysis_results." in name:
        return "tier2_analysis_results"
    if "_simulation_spec." in name:
        return "tier2_analysis_spec"
    if "_simulation_results." in name:
        return "tier2_analysis_results"
    if "_formal_request." in name:
        return "tier3_formal_request"
    if "_formal_lifecycle." in name:
        return "tier3_formal_lifecycle"
    if "_formal_transport." in name:
        return "tier3_formal_transport"
    if "_formal_results." in name:
        return "tier3_formal_results"
    if "_orchestrator_transcript." in name:
        return "orchestrator_transcript"
    if "_capability_evidence." in name:
        return "capability_evidence"
    if name.endswith("_error.json"):
        return "runtime_error"
    return "session_artifact"


def _infer_media_type(path: str) -> str:
    suffix = Path(path).suffix.lower()
    if suffix == ".json":
        return "application/json"
    if suffix == ".jsonl":
        return "application/x-ndjson"
    if suffix == ".md":
        return "text/markdown"
    if suffix == ".txt":
        return "text/plain"
    return "application/octet-stream"


def _read_memory_entries(path: Path) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    return [entry.strip() for entry in re.split(r"\n+\u00a7\n+", text) if entry.strip()]


def _join_memory_entries(entries: list[str]) -> str:
    body = f"\n{_ENTRY_SEPARATOR}\n".join(entry.strip() for entry in entries if entry.strip())
    return f"{body}\n" if body else ""


def _atomic_write_text(path: Path, text: str) -> None:
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(text, encoding="utf-8")
    temp_path.replace(path)


def _relative_to_root(root_directory: str | Path, path: Path) -> str:
    root = Path(root_directory).expanduser()
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _truncate(text: str, limit: int) -> str:
    value = " ".join(text.split())
    if len(value) <= limit:
        return value
    return f"{value[: limit - 3].rstrip()}..."


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered
