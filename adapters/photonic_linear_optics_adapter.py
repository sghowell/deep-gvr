from __future__ import annotations

from time import perf_counter

from deep_gvr.contracts import AnalysisResults, AnalysisSpec, Backend

from adapters.analysis_utils import analysis_timestamp, build_error_result, measurement
from adapters.base_adapter import AnalysisAdapter

try:
    import perceval as pcvl
except ImportError:  # pragma: no cover - exercised through structured adapter error handling
    pcvl = None


class PhotonicLinearOpticsAdapter(AnalysisAdapter):
    name = "photonic_linear_optics"

    def __init__(self, *, perceval_module=pcvl) -> None:
        self.pcvl = perceval_module

    def run(self, spec: AnalysisSpec, backend: Backend) -> AnalysisResults:
        start = perf_counter()
        timestamp = analysis_timestamp()
        if self.pcvl is None:
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="Perceval is not installed.",
                errors=["Install Perceval to enable photonic linear-optics analysis."],
            )
        if spec.analysis_kind != "basic_state_summary":
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="Unsupported photonic analysis kind.",
                errors=[f"Unsupported photonic analysis kind {spec.analysis_kind!r}."],
                details={"task": spec.task},
            )
        task = dict(spec.task)
        try:
            input_state = self.pcvl.BasicState(task["input_state"])
            mode_count = int(task.get("modes", len(task["input_state"])))
            processor_backend = str(task.get("processor_backend", "SLOS"))
            processor = self.pcvl.Processor(processor_backend, mode_count)
            processor.with_input(input_state)
            photon_count = sum(int(item) for item in task["input_state"])
        except Exception as exc:  # pragma: no cover - defensive boundary
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="The Perceval photonic analysis failed.",
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
            summary="The Perceval processor accepted the photonic input state.",
            measurements=[
                measurement("mode_count", mode_count),
                measurement("photon_count", photon_count),
            ],
            details={"processor_backend": processor_backend, "input_state": list(task["input_state"])},
            errors=[],
        )
