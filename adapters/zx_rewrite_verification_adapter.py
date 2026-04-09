from __future__ import annotations

from time import perf_counter

from deep_gvr.contracts import AnalysisResults, AnalysisSpec, Backend

from adapters.analysis_utils import analysis_timestamp, build_error_result, measurement
from adapters.base_adapter import AnalysisAdapter

try:
    import pyzx as zx
except ImportError:  # pragma: no cover - exercised through structured adapter error handling
    zx = None


class ZxRewriteVerificationAdapter(AnalysisAdapter):
    name = "zx_rewrite_verification"

    def __init__(self, *, pyzx_module=zx) -> None:
        self.zx = pyzx_module

    def run(self, spec: AnalysisSpec, backend: Backend) -> AnalysisResults:
        start = perf_counter()
        timestamp = analysis_timestamp()
        if self.zx is None:
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="PyZX is not installed.",
                errors=["Install PyZX to enable ZX rewrite and verification analysis."],
            )
        if spec.analysis_kind != "qasm_rewrite_summary":
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="Unsupported ZX analysis kind.",
                errors=[f"Unsupported ZX analysis kind {spec.analysis_kind!r}."],
                details={"task": spec.task},
            )
        task = dict(spec.task)
        try:
            circuit = self.zx.Circuit.from_qasm(task["qasm"])
            graph = circuit.to_graph()
            before_two_qubit = int(circuit.twoqubitcount())
            self.zx.full_reduce(graph)
            rewritten = self.zx.extract_circuit(graph)
            after_two_qubit = int(rewritten.twoqubitcount())
            equivalent = circuit.verify_equality(rewritten)
        except Exception as exc:  # pragma: no cover - defensive boundary
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="The PyZX rewrite failed.",
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
            summary="PyZX reduced the circuit and checked rewrite equivalence.",
            measurements=[
                measurement("two_qubit_count_before", before_two_qubit),
                measurement("two_qubit_count_after", after_two_qubit),
                measurement("equivalent", bool(equivalent) if equivalent is not None else None),
            ],
            details={"equivalent": equivalent, "rewritten_qasm": rewritten.to_qasm()},
            errors=[],
        )
