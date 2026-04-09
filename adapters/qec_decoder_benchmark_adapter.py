from __future__ import annotations

from time import perf_counter
from typing import Any

from deep_gvr.contracts import AnalysisResults, AnalysisSpec, Backend, SimSpec, Tier2Config

from adapters.analysis_utils import analysis_timestamp, build_error_result, measurement
from adapters.base_adapter import AnalysisAdapter
from adapters.stim_adapter import StimAdapter


class QecDecoderBenchmarkAdapter(AnalysisAdapter):
    name = "qec_decoder_benchmark"

    def __init__(self, *, tier2_config: Tier2Config | None = None) -> None:
        self.tier2_config = tier2_config or Tier2Config()
        self.stim_adapter = StimAdapter(tier2_config=self.tier2_config)

    def run(self, spec: AnalysisSpec, backend: Backend) -> AnalysisResults:
        start = perf_counter()
        timestamp = analysis_timestamp()
        task = dict(spec.task)
        engine = str(task.get("engine", "stim"))
        if engine != "stim":
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="The requested QEC analysis engine is not configured.",
                errors=[f"Unsupported QEC engine {engine!r}; only 'stim' is currently wired in this adapter."],
                details={"engine": engine},
            )

        try:
            sim_spec = SimSpec.from_dict(
                {
                    "simulator": "stim",
                    "task": {
                        "code": task["code"],
                        "task_type": task["task_type"],
                        "distance": task["distance"],
                        "rounds_per_distance": task["rounds_per_distance"],
                        "noise_model": task["noise_model"],
                        "error_rates": task["error_rates"],
                        "decoder": task["decoder"],
                        "shots_per_point": task["shots_per_point"],
                    },
                    "resources": spec.resources.to_dict(),
                }
            )
        except (KeyError, TypeError, ValueError) as exc:
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="The QEC analysis request could not be normalized.",
                errors=[f"Invalid QEC task payload: {type(exc).__name__}: {exc}"],
                details={"task": task},
            )

        sim_results = self.stim_adapter.run(sim_spec, backend)
        measurements = [
            measurement(
                "logical_error_rate",
                point.logical_error_rate,
                metadata={
                    "distance": point.distance,
                    "rounds": point.rounds,
                    "physical_error_rate": point.physical_error_rate,
                    "shots": point.shots,
                    "errors_observed": point.errors_observed,
                    "decoder": point.decoder,
                },
            )
            for point in sim_results.data
        ]
        if sim_results.analysis.threshold_estimate is not None:
            measurements.append(
                measurement(
                    "threshold_estimate",
                    sim_results.analysis.threshold_estimate,
                    metadata={"method": sim_results.analysis.threshold_method},
                )
            )

        summary = (
            f"Stim produced {len(sim_results.data)} QEC datapoint(s) for {task['task_type']}."
            if not sim_results.errors
            else "Stim returned structured QEC analysis errors."
        )
        details: dict[str, Any] = {
            "engine": "stim",
            "sim_results": sim_results.to_dict(),
        }
        return AnalysisResults(
            adapter_family=self.name,
            analysis_kind=spec.analysis_kind,
            adapter_name=self.name,
            adapter_version="0.1.0",
            timestamp=sim_results.timestamp,
            runtime_seconds=sim_results.runtime_seconds,
            backend=sim_results.backend,
            summary=summary,
            measurements=measurements,
            details=details,
            errors=list(sim_results.errors),
        )
