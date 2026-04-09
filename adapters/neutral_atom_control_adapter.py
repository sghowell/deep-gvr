from __future__ import annotations

from time import perf_counter

from deep_gvr.contracts import AnalysisResults, AnalysisSpec, Backend

from adapters.analysis_utils import analysis_timestamp, build_error_result, measurement
from adapters.base_adapter import AnalysisAdapter

try:
    from pulser import Register, Sequence
    from pulser.devices import MockDevice
except ImportError:  # pragma: no cover - exercised through structured adapter error handling
    Register = None
    Sequence = None
    MockDevice = None


class NeutralAtomControlAdapter(AnalysisAdapter):
    name = "neutral_atom_control"

    def __init__(self, *, register_cls=Register, sequence_cls=Sequence, device_cls=MockDevice) -> None:
        self.register_cls = register_cls
        self.sequence_cls = sequence_cls
        self.device_cls = device_cls

    def run(self, spec: AnalysisSpec, backend: Backend) -> AnalysisResults:
        start = perf_counter()
        timestamp = analysis_timestamp()
        if self.register_cls is None or self.sequence_cls is None or self.device_cls is None:
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="Pulser is not installed.",
                errors=["Install Pulser to enable neutral-atom control analysis."],
            )
        if spec.analysis_kind != "register_sequence_summary":
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="Unsupported neutral-atom analysis kind.",
                errors=[f"Unsupported neutral-atom analysis kind {spec.analysis_kind!r}."],
                details={"task": spec.task},
            )
        task = dict(spec.task)
        try:
            layout = str(task.get("layout", "square"))
            if layout == "square":
                register = self.register_cls.square(int(task.get("side", 2)), spacing=float(task.get("spacing", 5.0)))
            elif layout == "rectangle":
                register = self.register_cls.rectangle(
                    int(task.get("rows", 2)),
                    int(task.get("columns", 2)),
                    spacing=float(task.get("spacing", 5.0)),
                )
            else:
                register = self.register_cls.from_coordinates(task["coordinates"])
            sequence = self.sequence_cls(register, self.device_cls)
            qubit_count = len(getattr(register, "qubit_ids", getattr(register, "qubits", {})))
            dimensionality = int(getattr(register, "dimensionality", 2))
            available_channels = list(getattr(sequence, "available_channels", {}).keys())
        except Exception as exc:  # pragma: no cover - defensive boundary
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="The Pulser neutral-atom analysis failed.",
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
            summary="The Pulser register and sequence were constructed successfully.",
            measurements=[
                measurement("qubit_count", qubit_count),
                measurement("dimensionality", dimensionality),
                measurement("available_channel_count", len(available_channels)),
            ],
            details={"available_channels": available_channels, "layout": layout},
            errors=[],
        )
