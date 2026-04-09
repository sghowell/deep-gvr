from __future__ import annotations

import importlib
from time import perf_counter

from deep_gvr.contracts import AnalysisResults, AnalysisSpec, Backend

from adapters.analysis_utils import analysis_timestamp, build_error_result, measurement
from adapters.base_adapter import AnalysisAdapter

try:
    import tqec  # noqa: F401
except ImportError:  # pragma: no cover - exercised through structured adapter error handling
    tqec = None


class TopologicalQecDesignAdapter(AnalysisAdapter):
    name = "topological_qec_design"

    def __init__(self, *, tqec_available: bool | None = None) -> None:
        self.tqec_available = bool(tqec_available) if tqec_available is not None else tqec is not None

    def run(self, spec: AnalysisSpec, backend: Backend) -> AnalysisResults:
        start = perf_counter()
        timestamp = analysis_timestamp()
        if not self.tqec_available:
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="tqec is not installed.",
                errors=["Install tqec to enable topological-QEC design analysis."],
            )
        if spec.analysis_kind != "gallery_block_graph":
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="Unsupported tqec analysis kind.",
                errors=[f"Unsupported tqec analysis kind {spec.analysis_kind!r}."],
                details={"task": spec.task},
            )
        task = dict(spec.task)
        try:
            gallery_module = importlib.import_module(task.get("gallery_module", "tqec.gallery.steane_encoding"))
            constructor = getattr(gallery_module, task.get("gallery_function", "steane_encoding"))
            graph = constructor()
            surfaces = graph.find_correlation_surfaces()
        except Exception as exc:  # pragma: no cover - defensive boundary
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="The tqec gallery analysis failed.",
                errors=[f"{type(exc).__name__}: {exc}"],
                details={"task": task},
            )

        return AnalysisResults(
            adapter_family=self.name,
            analysis_kind=spec.analysis_kind,
            adapter_name=self.name,
            adapter_version="0.1.0",
            timestamp=timestamp,
            runtime_seconds=perf_counter() - start,
            backend=backend,
            summary="The tqec gallery block graph was constructed successfully.",
            measurements=[
                measurement("correlation_surface_count", len(surfaces)),
            ],
            details={
                "gallery_module": task.get("gallery_module", "tqec.gallery.steane_encoding"),
                "gallery_function": task.get("gallery_function", "steane_encoding"),
            },
            errors=[],
        )
