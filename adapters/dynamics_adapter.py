from __future__ import annotations

from time import perf_counter

from deep_gvr.contracts import AnalysisResults, AnalysisSpec, Backend

from adapters.analysis_utils import analysis_timestamp, build_error_result, measurement
from adapters.base_adapter import AnalysisAdapter

try:
    from scipy.integrate import solve_ivp
except ImportError:  # pragma: no cover - exercised through structured adapter error handling
    solve_ivp = None

try:
    import qutip
except ImportError:  # pragma: no cover - exercised through structured adapter error handling
    qutip = None


class DynamicsAdapter(AnalysisAdapter):
    name = "dynamics"

    def __init__(self, *, solve_ivp_fn=solve_ivp, qutip_module=qutip) -> None:
        self.solve_ivp = solve_ivp_fn
        self.qutip = qutip_module

    def run(self, spec: AnalysisSpec, backend: Backend) -> AnalysisResults:
        start = perf_counter()
        timestamp = analysis_timestamp()
        try:
            if spec.analysis_kind == "ode_final_value":
                return self._run_ode_final_value(spec, backend, start, timestamp)
            if spec.analysis_kind == "qutip_expectation":
                return self._run_qutip_expectation(spec, backend, start, timestamp)
        except Exception as exc:  # pragma: no cover - defensive boundary
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="The dynamics analysis failed.",
                errors=[f"{type(exc).__name__}: {exc}"],
                details={"task": spec.task},
            )
        return build_error_result(
            adapter_family=self.name,
            analysis_kind=spec.analysis_kind,
            adapter_name=self.name,
            backend=backend,
            start=start,
            timestamp=timestamp,
            summary="Unsupported dynamics analysis kind.",
            errors=[f"Unsupported dynamics analysis kind {spec.analysis_kind!r}."],
            details={"task": spec.task},
        )

    def _run_ode_final_value(self, spec: AnalysisSpec, backend: Backend, start: float, timestamp: str) -> AnalysisResults:
        if self.solve_ivp is None:
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="SciPy is not installed.",
                errors=["Install SciPy to enable ODE analysis."],
            )
        task = dict(spec.task)
        equation = str(task.get("equation", "exponential_decay"))
        y0 = [float(task.get("initial", 1.0))]
        t_start, t_end = [float(item) for item in task.get("t_span", [0.0, 1.0])]
        sample_times = [float(item) for item in task.get("sample_times", [t_end])]
        if equation == "exponential_decay":
            rate = float(task["rate"])

            def rhs(_t: float, values: list[float]) -> list[float]:
                return [-rate * values[0]]

        elif equation == "logistic_growth":
            rate = float(task["rate"])
            carrying_capacity = float(task["carrying_capacity"])

            def rhs(_t: float, values: list[float]) -> list[float]:
                return [rate * values[0] * (1.0 - values[0] / carrying_capacity)]

        else:
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="Unsupported ODE model.",
                errors=[f"Unsupported ODE equation {equation!r}."],
                details={"task": task},
            )

        solution = self.solve_ivp(rhs, (t_start, t_end), y0, t_eval=sample_times)
        final_value = float(solution.y[0][-1]) if solution.success else None
        summary = "The ODE solve completed successfully." if solution.success else "The ODE solve failed."
        return AnalysisResults(
            adapter_family=self.name,
            analysis_kind=spec.analysis_kind,
            adapter_name=self.name,
            adapter_version="0.1.0",
            timestamp=timestamp,
            runtime_seconds=perf_counter() - start,
            backend=backend,
            summary=summary,
            measurements=[measurement("final_value", final_value)],
            details={
                "times": list(solution.t) if solution.success else [],
                "values": [float(item) for item in solution.y[0]] if solution.success else [],
                "equation": equation,
            },
            errors=[] if solution.success else [solution.message],
        )

    def _run_qutip_expectation(self, spec: AnalysisSpec, backend: Backend, start: float, timestamp: str) -> AnalysisResults:
        if self.qutip is None:
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="QuTiP is not installed.",
                errors=["Install QuTiP to enable quantum/open-system dynamics analysis."],
            )
        task = dict(spec.task)
        omega = float(task.get("omega", 1.0))
        end_time = float(task.get("end_time", 1.0))
        sample_points = int(task.get("sample_points", 16))
        basis_state = int(task.get("basis_state", 0))
        times = [end_time * index / max(sample_points - 1, 1) for index in range(sample_points)]
        hamiltonian = 0.5 * omega * self.qutip.sigmax()
        psi0 = self.qutip.basis(2, basis_state)
        result = self.qutip.mesolve(hamiltonian, psi0, times, [], [self.qutip.sigmaz()])
        expectations = result.expect[0]
        final_expectation = float(expectations[-1]) if len(expectations) else None
        return AnalysisResults(
            adapter_family=self.name,
            analysis_kind=spec.analysis_kind,
            adapter_name=self.name,
            adapter_version="0.1.0",
            timestamp=timestamp,
            runtime_seconds=perf_counter() - start,
            backend=backend,
            summary="The QuTiP expectation-value evolution completed successfully.",
            measurements=[measurement("final_expectation", final_expectation)],
            details={"times": times, "expectations": [float(item) for item in expectations]},
            errors=[],
        )
