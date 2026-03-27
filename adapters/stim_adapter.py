from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from deep_gvr.contracts import Backend, SimAnalysis, SimResults, SimSpec
from deep_gvr.contracts import SimDataPoint

from adapters.base_adapter import SimulatorAdapter

try:
    import numpy as np
except ImportError:  # pragma: no cover - exercised through adapter error handling
    np = None

try:
    import pymatching
except ImportError:  # pragma: no cover - exercised through adapter error handling
    pymatching = None

try:
    import stim
except ImportError:  # pragma: no cover - exercised through adapter error handling
    stim = None


TASK_MAP = {
    ("surface_code", "rotated_memory_z"): "surface_code:rotated_memory_z",
    ("surface_code", "rotated_memory_x"): "surface_code:rotated_memory_x",
    ("repetition_code", "memory"): "repetition_code:memory",
}


class StimAdapter(SimulatorAdapter):
    name = "stim"

    def run(self, spec: SimSpec, backend: Backend) -> SimResults:
        start = perf_counter()
        timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        if backend is Backend.LOCAL:
            return self._run_local(spec, backend, timestamp, start)
        if backend is Backend.MODAL:
            return self._unsupported_backend_result(
                backend=backend,
                timestamp=timestamp,
                runtime_seconds=perf_counter() - start,
                message="Modal backend is not implemented yet for the Stim adapter.",
            )
        if backend is Backend.SSH:
            return self._unsupported_backend_result(
                backend=backend,
                timestamp=timestamp,
                runtime_seconds=perf_counter() - start,
                message="SSH backend is not implemented yet for the Stim adapter.",
            )
        raise ValueError(f"Unsupported backend {backend!r}.")

    def _run_local(self, spec: SimSpec, backend: Backend, timestamp: str, start: float) -> SimResults:
        dependency_errors = self._dependency_errors()
        if dependency_errors:
            return self._error_result(
                backend=backend,
                timestamp=timestamp,
                runtime_seconds=perf_counter() - start,
                threshold_method="missing_dependencies",
                errors=dependency_errors,
            )

        try:
            code_task = self._resolve_code_task(spec)
        except ValueError as exc:
            return self._error_result(
                backend=backend,
                timestamp=timestamp,
                runtime_seconds=perf_counter() - start,
                threshold_method="unsupported_task",
                errors=[str(exc)],
            )

        if spec.task.noise_model != "depolarizing":
            return self._error_result(
                backend=backend,
                timestamp=timestamp,
                runtime_seconds=perf_counter() - start,
                threshold_method="unsupported_noise_model",
                errors=[f"Unsupported noise model {spec.task.noise_model!r}; only 'depolarizing' is implemented."],
            )

        if spec.task.decoder != "pymatching":
            return self._error_result(
                backend=backend,
                timestamp=timestamp,
                runtime_seconds=perf_counter() - start,
                threshold_method="unsupported_decoder",
                errors=[f"Unsupported decoder {spec.task.decoder!r}; only 'pymatching' is implemented."],
            )

        data: list[SimDataPoint] = []
        errors: list[str] = []
        for distance in spec.task.distance:
            rounds = self._resolve_rounds(spec.task.rounds_per_distance, distance)
            for error_rate in spec.task.error_rates:
                try:
                    data.append(
                        self._simulate_point(
                            code_task=code_task,
                            distance=distance,
                            rounds=rounds,
                            error_rate=error_rate,
                            shots=spec.task.shots_per_point,
                            decoder=spec.task.decoder,
                        )
                    )
                except Exception as exc:  # pragma: no cover - defensive runtime boundary
                    errors.append(
                        f"Simulation failed for distance={distance} error_rate={error_rate}: {type(exc).__name__}: {exc}"
                    )

        runtime_seconds = perf_counter() - start
        analysis = self._analyze(data) if data else SimAnalysis(
            threshold_estimate=None,
            threshold_method="no_data",
            below_threshold_distances=[],
            scaling_exponent=None,
        )
        return SimResults(
            simulator=self.name,
            adapter_version="0.1.0",
            timestamp=timestamp,
            runtime_seconds=runtime_seconds,
            backend=backend,
            data=data,
            analysis=analysis,
            errors=errors,
        )

    def _simulate_point(
        self,
        *,
        code_task: str,
        distance: int,
        rounds: int,
        error_rate: float,
        shots: int,
        decoder: str,
    ) -> SimDataPoint:
        circuit = stim.Circuit.generated(
            code_task,
            distance=distance,
            rounds=rounds,
            after_clifford_depolarization=error_rate,
        )
        detector_error_model = circuit.detector_error_model(decompose_errors=True)
        matcher = pymatching.Matching.from_detector_error_model(detector_error_model)
        sampler = circuit.compile_detector_sampler()
        detection_events, observable_flips = sampler.sample(shots=shots, separate_observables=True)
        predictions = matcher.decode_batch(detection_events)
        mismatches = np.not_equal(predictions.astype(bool), observable_flips.astype(bool))
        errors_observed = int(np.count_nonzero(mismatches))
        return SimDataPoint(
            distance=distance,
            rounds=rounds,
            physical_error_rate=error_rate,
            logical_error_rate=errors_observed / shots,
            shots=shots,
            errors_observed=errors_observed,
            decoder=decoder,
        )

    def _resolve_code_task(self, spec: SimSpec) -> str:
        key = (spec.task.code, spec.task.task_type)
        if key not in TASK_MAP:
            supported = ", ".join(f"{code}/{task_type}" for code, task_type in sorted(TASK_MAP))
            raise ValueError(
                f"Unsupported Stim task {spec.task.code!r}/{spec.task.task_type!r}. Supported combinations: {supported}."
            )
        return TASK_MAP[key]

    def _resolve_rounds(self, rounds_per_distance: str, distance: int) -> int:
        value = rounds_per_distance.strip().lower()
        if value.isdigit():
            return int(value)

        match = re.fullmatch(r"(?:(\d+)?)d", value)
        if match:
            multiplier = int(match.group(1) or "1")
            return multiplier * distance

        raise ValueError(f"Unsupported rounds_per_distance value {rounds_per_distance!r}.")

    def _analyze(self, data: list[SimDataPoint]) -> SimAnalysis:
        grouped: dict[float, list[SimDataPoint]] = {}
        for point in data:
            grouped.setdefault(point.physical_error_rate, []).append(point)

        monotonic_candidates: list[float] = []
        below_threshold_distances: set[int] = set()
        for error_rate, points in grouped.items():
            ordered = sorted(points, key=lambda item: item.distance)
            if len(ordered) < 2:
                continue
            if all(left.logical_error_rate > right.logical_error_rate for left, right in zip(ordered, ordered[1:])):
                monotonic_candidates.append(error_rate)
                below_threshold_distances.update(point.distance for point in ordered[1:])

        if monotonic_candidates:
            return SimAnalysis(
                threshold_estimate=None,
                threshold_method="monotonic_distance_improvement",
                below_threshold_distances=sorted(below_threshold_distances),
                scaling_exponent=None,
            )

        return SimAnalysis(
            threshold_estimate=None,
            threshold_method="no_crossing_detected",
            below_threshold_distances=[],
            scaling_exponent=None,
        )

    def _dependency_errors(self) -> list[str]:
        errors: list[str] = []
        if stim is None:
            errors.append("Python package 'stim' is not installed.")
        if pymatching is None:
            errors.append("Python package 'pymatching' is not installed.")
        if np is None:
            errors.append("Python package 'numpy' is not installed.")
        return errors

    def _unsupported_backend_result(
        self,
        *,
        backend: Backend,
        timestamp: str,
        runtime_seconds: float,
        message: str,
    ) -> SimResults:
        return self._error_result(
            backend=backend,
            timestamp=timestamp,
            runtime_seconds=runtime_seconds,
            threshold_method="backend_unavailable",
            errors=[message],
        )

    def _error_result(
        self,
        *,
        backend: Backend,
        timestamp: str,
        runtime_seconds: float,
        threshold_method: str,
        errors: list[str],
    ) -> SimResults:
        return SimResults(
            simulator=self.name,
            adapter_version="0.1.0",
            timestamp=timestamp,
            runtime_seconds=runtime_seconds,
            backend=backend,
            data=[],
            analysis=SimAnalysis(
                threshold_estimate=None,
                threshold_method=threshold_method,
                below_threshold_distances=[],
                scaling_exponent=None,
            ),
            errors=errors,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="deep-gvr Stim adapter scaffold")
    parser.add_argument("--spec", required=True, help="Path to a simulation spec JSON file")
    parser.add_argument("--backend", required=True, choices=[item.value for item in Backend])
    parser.add_argument("--output", required=True, help="Path to write normalized results JSON")
    args = parser.parse_args()

    spec_path = Path(args.spec)
    output_path = Path(args.output)
    spec = SimSpec.from_dict(json.loads(spec_path.read_text(encoding="utf-8")))

    adapter = StimAdapter()
    results = adapter.run(spec, Backend(args.backend))
    output_path.write_text(json.dumps(results.to_dict(), indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
