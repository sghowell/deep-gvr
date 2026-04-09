from __future__ import annotations

from time import perf_counter

from deep_gvr.contracts import AnalysisResults, AnalysisSpec, Backend

from adapters.analysis_utils import analysis_timestamp, build_error_result, measurement
from adapters.base_adapter import AnalysisAdapter

try:
    from graphix.transpiler import Circuit as GraphixCircuit
except ImportError:  # pragma: no cover - exercised through structured adapter error handling
    GraphixCircuit = None


class MbqcGraphStateAdapter(AnalysisAdapter):
    name = "mbqc_graph_state"

    def __init__(self, *, circuit_cls=GraphixCircuit) -> None:
        self.circuit_cls = circuit_cls

    def run(self, spec: AnalysisSpec, backend: Backend) -> AnalysisResults:
        start = perf_counter()
        timestamp = analysis_timestamp()
        if self.circuit_cls is None:
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="Graphix is not installed.",
                errors=["Install Graphix to enable MBQC graph-state analysis."],
            )
        if spec.analysis_kind != "transpile_pattern":
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="Unsupported MBQC analysis kind.",
                errors=[f"Unsupported MBQC analysis kind {spec.analysis_kind!r}."],
                details={"task": spec.task},
            )
        task = dict(spec.task)
        try:
            circuit = self.circuit_cls(int(task["qubits"]))
            for gate in task.get("gates", []):
                gate_name = str(gate["gate"]).lower()
                method = getattr(circuit, gate_name, None)
                if method is None:
                    raise ValueError(f"Unsupported Graphix gate {gate_name!r}.")
                if gate_name in {"cnot", "cx"}:
                    method(int(gate["control"]), int(gate["target"]))
                elif gate_name in {"rx", "ry", "rz"}:
                    method(int(gate["qubit"]), float(gate["angle"]))
                else:
                    method(int(gate["qubit"]))
            transpiled = circuit.transpile()
            pattern = getattr(transpiled, "pattern", transpiled)
            command_count = len(getattr(pattern, "seq", []))
            node_count = int(
                getattr(pattern, "Nnode", getattr(pattern, "n_node", getattr(pattern, "num_nodes", task["qubits"])))
            )
            output_nodes = list(getattr(pattern, "output_nodes", []))
        except Exception as exc:  # pragma: no cover - defensive boundary
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="The Graphix transpilation failed.",
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
            summary="The Graphix circuit transpiled into an MBQC measurement pattern.",
            measurements=[
                measurement("node_count", node_count),
                measurement("command_count", command_count),
                measurement("output_node_count", len(output_nodes)),
            ],
            details={"output_nodes": output_nodes, "qubits": int(task["qubits"])},
            errors=[],
        )
