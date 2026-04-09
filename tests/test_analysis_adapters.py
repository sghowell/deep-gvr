from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tests import _path_setup  # noqa: F401

from adapters.dynamics_adapter import DynamicsAdapter
from adapters.mbqc_graph_state_adapter import MbqcGraphStateAdapter
from adapters.neutral_atom_control_adapter import NeutralAtomControlAdapter
from adapters.optimization_adapter import OptimizationAdapter
from adapters.photonic_linear_optics_adapter import PhotonicLinearOpticsAdapter
from adapters.qec_decoder_benchmark_adapter import QecDecoderBenchmarkAdapter
from adapters.registry import build_analysis_adapter, supported_analysis_families
from adapters.symbolic_math_adapter import SymbolicMathAdapter
from adapters.topological_qec_design_adapter import TopologicalQecDesignAdapter
from adapters.zx_rewrite_verification_adapter import ZxRewriteVerificationAdapter
from deep_gvr.contracts import (
    AnalysisSpec,
    Backend,
    SimAnalysis,
    SimDataPoint,
    SimResults,
    Tier2Config,
)


def _analysis_spec(adapter_family: str, analysis_kind: str, task: dict[str, object]) -> AnalysisSpec:
    return AnalysisSpec.from_dict(
        {
            "adapter_family": adapter_family,
            "analysis_kind": analysis_kind,
            "task": task,
            "resources": {"timeout_seconds": 30, "max_parallel": 1},
        }
    )


class _FakeExpr:
    def __init__(self, text: str) -> None:
        self.text = text

    def __sub__(self, other: object) -> "_FakeDiff":
        if not isinstance(other, _FakeExpr):
            raise TypeError(other)
        return _FakeDiff(self.text, other.text)

    def __str__(self) -> str:
        return self.text


class _FakeDiff:
    def __init__(self, lhs: str, rhs: str) -> None:
        self.lhs = lhs
        self.rhs = rhs


class _FakeSympy:
    @staticmethod
    def _normalize(text: str) -> str:
        normalized = text.replace(" ", "")
        aliases = {
            "(x+1)^2": "x^2+2x+1",
            "x^2+2x+1": "x^2+2x+1",
            "d/dx(x^3)": "3*x^2",
            "3*x^2": "3*x^2",
            "2*x^2": "2*x^2",
        }
        return aliases.get(normalized, normalized)

    @staticmethod
    def sympify(text: str) -> _FakeExpr:
        return _FakeExpr(str(text))

    @staticmethod
    def Symbol(text: str) -> _FakeExpr:
        return _FakeExpr(str(text))

    @staticmethod
    def diff(expr: _FakeExpr, symbol: _FakeExpr) -> _FakeExpr:
        return _FakeExpr(f"d/d{symbol.text}({expr.text})")

    @classmethod
    def simplify(cls, expr: object) -> int:
        if isinstance(expr, _FakeDiff):
            return 0 if cls._normalize(expr.lhs) == cls._normalize(expr.rhs) else 1
        if isinstance(expr, _FakeExpr):
            return 0
        raise TypeError(expr)


class _FakeBoolVar:
    def __init__(self, row: int, col: int) -> None:
        self.row = row
        self.col = col

    def __radd__(self, other: object) -> int:
        return int(other) if isinstance(other, int) else 0

    def __add__(self, other: object) -> int:
        return int(other) if isinstance(other, int) else 0

    def __rmul__(self, other: object) -> int:
        return 0

    def __mul__(self, other: object) -> int:
        return 0


class _FakeCpModelModule:
    OPTIMAL = 1
    FEASIBLE = 2

    class CpModel:
        def NewBoolVar(self, name: str) -> _FakeBoolVar:
            _, row, col = name.split("_")
            return _FakeBoolVar(int(row), int(col))

        def Add(self, _constraint: object) -> None:
            return None

        def Minimize(self, _expression: object) -> None:
            return None

    class CpSolver:
        def Solve(self, _model: object) -> int:
            return _FakeCpModelModule.OPTIMAL

        def Value(self, variable: _FakeBoolVar) -> int:
            return 1 if (variable.row, variable.col) in {(0, 1), (1, 0)} else 0

        def ObjectiveValue(self) -> int:
            return 3


class AnalysisAdapterTests(unittest.TestCase):
    def test_registry_lists_supported_families(self) -> None:
        self.assertEqual(
            supported_analysis_families(),
            [
                "symbolic_math",
                "optimization",
                "dynamics",
                "qec_decoder_benchmark",
                "mbqc_graph_state",
                "photonic_linear_optics",
                "neutral_atom_control",
                "topological_qec_design",
                "zx_rewrite_verification",
            ],
        )
        self.assertIsNotNone(build_analysis_adapter("symbolic_math"))
        self.assertIsNone(build_analysis_adapter("missing-family"))

    def test_symbolic_math_adapter_checks_equivalence(self) -> None:
        adapter = SymbolicMathAdapter(sympy_module=_FakeSympy())
        results = adapter.run(
            _analysis_spec(
                "symbolic_math",
                "expression_equivalence",
                {"lhs": "(x + 1)^2", "rhs": "x^2 + 2x + 1"},
            ),
            Backend.LOCAL,
        )

        self.assertEqual(results.adapter_family, "symbolic_math")
        self.assertFalse(results.errors)
        self.assertEqual(results.measurements[0].name, "equivalent")
        self.assertTrue(results.measurements[0].value)

    def test_optimization_adapter_solves_linear_program(self) -> None:
        fake_result = SimpleNamespace(success=True, fun=3.0, x=[3.0, 0.0], status=0, message="optimal")
        adapter = OptimizationAdapter(linprog_fn=lambda **_: fake_result, cp_model_module=_FakeCpModelModule())
        results = adapter.run(
            _analysis_spec(
                "optimization",
                "linear_program",
                {
                    "goal": "min",
                    "objective": [1, 2],
                    "A_ub": [[-1, -1]],
                    "b_ub": [-3],
                    "bounds": [[0, None], [0, None]],
                },
            ),
            Backend.LOCAL,
        )

        self.assertFalse(results.errors)
        self.assertEqual(results.measurements[1].name, "objective_value")
        self.assertEqual(results.measurements[1].value, 3.0)

    def test_optimization_adapter_solves_assignment_problem(self) -> None:
        adapter = OptimizationAdapter(linprog_fn=None, cp_model_module=_FakeCpModelModule())
        results = adapter.run(
            _analysis_spec(
                "optimization",
                "assignment_problem",
                {"cost_matrix": [[4, 1], [2, 3]]},
            ),
            Backend.LOCAL,
        )

        self.assertFalse(results.errors)
        self.assertEqual(results.measurements[1].value, 3)
        self.assertEqual(len(results.details["assignment"]), 2)

    def test_dynamics_adapter_runs_ode_and_qutip_paths(self) -> None:
        fake_ode_result = SimpleNamespace(success=True, y=[[0.1353]], t=[0.0, 2.0], message="ok")
        fake_qutip = SimpleNamespace(
            sigmax=lambda: 1.0,
            sigmaz=lambda: "sigmaz",
            basis=lambda n, i: (n, i),
            mesolve=lambda *_args, **_kwargs: SimpleNamespace(expect=[[1.0, -1.0]]),
        )
        adapter = DynamicsAdapter(solve_ivp_fn=lambda *args, **kwargs: fake_ode_result, qutip_module=fake_qutip)

        ode_results = adapter.run(
            _analysis_spec(
                "dynamics",
                "ode_final_value",
                {"equation": "exponential_decay", "rate": 1.0, "initial": 1.0, "t_span": [0.0, 2.0]},
            ),
            Backend.LOCAL,
        )
        qutip_results = adapter.run(
            _analysis_spec(
                "dynamics",
                "qutip_expectation",
                {"omega": 1.0, "end_time": 1.0, "sample_points": 2, "basis_state": 0},
            ),
            Backend.LOCAL,
        )

        self.assertEqual(ode_results.measurements[0].value, 0.1353)
        self.assertEqual(qutip_results.measurements[0].value, -1.0)

    def test_mbqc_graph_state_adapter_transpiles_pattern(self) -> None:
        class FakePattern:
            seq = [1, 2, 3]
            output_nodes = [0]
            Nnode = 2

        class FakeCircuit:
            def __init__(self, qubits: int) -> None:
                self.qubits = qubits

            def h(self, _qubit: int) -> None:
                return None

            def cnot(self, _control: int, _target: int) -> None:
                return None

            def transpile(self) -> SimpleNamespace:
                return SimpleNamespace(pattern=FakePattern())

        adapter = MbqcGraphStateAdapter(circuit_cls=FakeCircuit)
        results = adapter.run(
            _analysis_spec(
                "mbqc_graph_state",
                "transpile_pattern",
                {"qubits": 2, "gates": [{"gate": "h", "qubit": 0}, {"gate": "cnot", "control": 0, "target": 1}]},
            ),
            Backend.LOCAL,
        )

        self.assertFalse(results.errors)
        self.assertEqual(results.measurements[0].value, 2)
        self.assertEqual(results.measurements[1].value, 3)

    def test_photonic_linear_optics_adapter_summarizes_basic_state(self) -> None:
        class FakeProcessor:
            def __init__(self, backend_name: str, mode_count: int) -> None:
                self.backend_name = backend_name
                self.mode_count = mode_count
                self.input_state = None

            def with_input(self, input_state: object) -> None:
                self.input_state = input_state

        fake_pcvl = SimpleNamespace(BasicState=lambda state: tuple(state), Processor=FakeProcessor)
        adapter = PhotonicLinearOpticsAdapter(perceval_module=fake_pcvl)
        results = adapter.run(
            _analysis_spec(
                "photonic_linear_optics",
                "basic_state_summary",
                {"input_state": [1, 0], "modes": 2, "processor_backend": "SLOS"},
            ),
            Backend.LOCAL,
        )

        self.assertFalse(results.errors)
        self.assertEqual(results.measurements[0].value, 2)
        self.assertEqual(results.measurements[1].value, 1)

    def test_neutral_atom_control_adapter_builds_register(self) -> None:
        class FakeRegister:
            def __init__(self, qubit_ids: list[str]) -> None:
                self.qubit_ids = qubit_ids
                self.dimensionality = 2

            @classmethod
            def square(cls, side: int, spacing: float) -> "FakeRegister":
                del spacing
                return cls([f"q{i}" for i in range(side * side)])

        class FakeSequence:
            def __init__(self, register: FakeRegister, device: object) -> None:
                del register, device
                self.available_channels = {"rydberg_global": object()}

        adapter = NeutralAtomControlAdapter(register_cls=FakeRegister, sequence_cls=FakeSequence, device_cls=object())
        results = adapter.run(
            _analysis_spec(
                "neutral_atom_control",
                "register_sequence_summary",
                {"layout": "square", "side": 2, "spacing": 5.0},
            ),
            Backend.LOCAL,
        )

        self.assertFalse(results.errors)
        self.assertEqual(results.measurements[0].value, 4)
        self.assertEqual(results.measurements[2].value, 1)

    def test_topological_qec_design_adapter_builds_gallery_graph(self) -> None:
        adapter = TopologicalQecDesignAdapter(tqec_available=True)

        class FakeGraph:
            @staticmethod
            def find_correlation_surfaces() -> list[int]:
                return [1, 2, 3, 4]

        fake_module = SimpleNamespace(steane_encoding=lambda: FakeGraph())
        with patch("adapters.topological_qec_design_adapter.importlib.import_module", return_value=fake_module):
            results = adapter.run(
                _analysis_spec(
                    "topological_qec_design",
                    "gallery_block_graph",
                    {"gallery_module": "tqec.gallery.steane_encoding", "gallery_function": "steane_encoding"},
                ),
                Backend.LOCAL,
            )

        self.assertFalse(results.errors)
        self.assertEqual(results.measurements[0].value, 4)

    def test_zx_rewrite_verification_adapter_rewrites_qasm(self) -> None:
        class FakeCircuit:
            def __init__(self, qasm: str, count: int) -> None:
                self.qasm = qasm
                self.count = count

            @classmethod
            def from_qasm(cls, qasm: str) -> "FakeCircuit":
                return cls(qasm, 1)

            def to_graph(self) -> dict[str, object]:
                return {"graph": self.qasm}

            def twoqubitcount(self) -> int:
                return self.count

            def verify_equality(self, _other: object) -> bool:
                return True

            def to_qasm(self) -> str:
                return "OPENQASM 2.0;"

        fake_zx = SimpleNamespace(
            Circuit=FakeCircuit,
            full_reduce=lambda _graph: None,
            extract_circuit=lambda _graph: FakeCircuit("rewritten", 0),
        )
        adapter = ZxRewriteVerificationAdapter(pyzx_module=fake_zx)
        results = adapter.run(
            _analysis_spec(
                "zx_rewrite_verification",
                "qasm_rewrite_summary",
                {"qasm": "OPENQASM 2.0; qreg q[1]; h q[0]; h q[0];"},
            ),
            Backend.LOCAL,
        )

        self.assertFalse(results.errors)
        self.assertTrue(results.measurements[2].value)
        self.assertEqual(results.measurements[1].value, 0)

    def test_qec_decoder_benchmark_adapter_wraps_stim_results(self) -> None:
        class FakeStimAdapter:
            def run(self, _spec: object, backend: Backend) -> SimResults:
                return SimResults(
                    simulator="stim",
                    adapter_version="0.1.0",
                    timestamp="2026-04-08T00:00:00Z",
                    runtime_seconds=0.2,
                    backend=backend,
                    data=[
                        SimDataPoint(
                            distance=3,
                            rounds=3,
                            physical_error_rate=0.001,
                            logical_error_rate=0.0002,
                            shots=100,
                            errors_observed=2,
                            decoder="pymatching",
                        )
                    ],
                    analysis=SimAnalysis(
                        threshold_estimate=0.001,
                        threshold_method="fixture",
                        below_threshold_distances=[3],
                    ),
                    errors=[],
                )

        adapter = QecDecoderBenchmarkAdapter(tier2_config=Tier2Config())
        adapter.stim_adapter = FakeStimAdapter()
        results = adapter.run(
            _analysis_spec(
                "qec_decoder_benchmark",
                "rotated_surface_code_memory",
                {
                    "engine": "stim",
                    "code": "surface_code",
                    "task_type": "rotated_memory_z",
                    "distance": [3],
                    "rounds_per_distance": "d",
                    "noise_model": "depolarizing",
                    "error_rates": [0.001],
                    "decoder": "pymatching",
                    "shots_per_point": 100,
                },
            ),
            Backend.LOCAL,
        )

        self.assertFalse(results.errors)
        self.assertEqual(results.adapter_family, "qec_decoder_benchmark")
        self.assertEqual(results.measurements[0].name, "logical_error_rate")
        self.assertEqual(results.measurements[1].name, "threshold_estimate")


if __name__ == "__main__":
    unittest.main()
