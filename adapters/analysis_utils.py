from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter

from deep_gvr.contracts import AnalysisMeasurement, AnalysisResults, Backend


def analysis_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def build_error_result(
    *,
    adapter_family: str,
    analysis_kind: str,
    adapter_name: str,
    backend: Backend,
    start: float,
    timestamp: str,
    summary: str,
    errors: list[str],
    details: dict[str, object] | None = None,
) -> AnalysisResults:
    return AnalysisResults(
        adapter_family=adapter_family,
        analysis_kind=analysis_kind,
        adapter_name=adapter_name,
        adapter_version="0.1.0",
        timestamp=timestamp,
        runtime_seconds=perf_counter() - start,
        backend=backend,
        summary=summary,
        measurements=[],
        details=dict(details or {}),
        errors=list(errors),
    )


def measurement(
    name: str,
    value: str | int | float | bool | None,
    *,
    unit: str = "",
    metadata: dict[str, object] | None = None,
) -> AnalysisMeasurement:
    return AnalysisMeasurement(name=name, value=value, unit=unit, metadata=dict(metadata or {}))
