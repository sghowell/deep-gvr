from __future__ import annotations

from time import perf_counter

from deep_gvr.contracts import AnalysisResults, AnalysisSpec, Backend

from adapters.analysis_utils import analysis_timestamp, build_error_result, measurement
from adapters.base_adapter import AnalysisAdapter

try:
    from ortools.sat.python import cp_model
except ImportError:  # pragma: no cover - exercised through structured adapter error handling
    cp_model = None

try:
    from scipy.optimize import linprog
except ImportError:  # pragma: no cover - exercised through structured adapter error handling
    linprog = None


class OptimizationAdapter(AnalysisAdapter):
    name = "optimization"

    def __init__(self, *, linprog_fn=linprog, cp_model_module=cp_model) -> None:
        self.linprog = linprog_fn
        self.cp_model = cp_model_module

    def run(self, spec: AnalysisSpec, backend: Backend) -> AnalysisResults:
        start = perf_counter()
        timestamp = analysis_timestamp()
        try:
            if spec.analysis_kind == "linear_program":
                return self._run_linear_program(spec, backend, start, timestamp)
            if spec.analysis_kind == "assignment_problem":
                return self._run_assignment_problem(spec, backend, start, timestamp)
        except Exception as exc:  # pragma: no cover - defensive boundary
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="The optimization analysis failed.",
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
            summary="Unsupported optimization analysis kind.",
            errors=[f"Unsupported optimization analysis kind {spec.analysis_kind!r}."],
            details={"task": spec.task},
        )

    def _run_linear_program(self, spec: AnalysisSpec, backend: Backend, start: float, timestamp: str) -> AnalysisResults:
        if self.linprog is None:
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="SciPy is not installed.",
                errors=["Install SciPy to enable linear-program analysis."],
            )
        task = dict(spec.task)
        objective = list(task["objective"])
        goal = str(task.get("goal", "min"))
        if goal == "max":
            objective = [-float(item) for item in objective]
        result = self.linprog(
            c=objective,
            A_ub=task.get("A_ub"),
            b_ub=task.get("b_ub"),
            A_eq=task.get("A_eq"),
            b_eq=task.get("b_eq"),
            bounds=task.get("bounds"),
            method="highs",
        )
        optimum = float(-result.fun if goal == "max" and result.success else result.fun) if result.success else None
        summary = "The linear program solved successfully." if result.success else "The linear program did not solve successfully."
        return AnalysisResults(
            adapter_family=self.name,
            analysis_kind=spec.analysis_kind,
            adapter_name=self.name,
            adapter_version="0.1.0",
            timestamp=timestamp,
            runtime_seconds=perf_counter() - start,
            backend=backend,
            summary=summary,
            measurements=[
                measurement("success", bool(result.success)),
                measurement("objective_value", optimum),
            ],
            details={
                "x": list(result.x) if result.success and result.x is not None else None,
                "status": int(result.status),
                "message": str(result.message),
                "goal": goal,
            },
            errors=[] if result.success else [str(result.message)],
        )

    def _run_assignment_problem(self, spec: AnalysisSpec, backend: Backend, start: float, timestamp: str) -> AnalysisResults:
        if self.cp_model is None:
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="OR-Tools is not installed.",
                errors=["Install OR-Tools to enable assignment-problem analysis."],
            )
        task = dict(spec.task)
        cost_matrix = task["cost_matrix"]
        model = self.cp_model.CpModel()
        rows = len(cost_matrix)
        cols = len(cost_matrix[0]) if rows else 0
        picks = {}
        for row in range(rows):
            for col in range(cols):
                picks[(row, col)] = model.NewBoolVar(f"x_{row}_{col}")
        for row in range(rows):
            model.Add(sum(picks[(row, col)] for col in range(cols)) == 1)
        for col in range(cols):
            model.Add(sum(picks[(row, col)] for row in range(rows)) == 1)
        model.Minimize(sum(int(cost_matrix[row][col]) * picks[(row, col)] for row in range(rows) for col in range(cols)))
        solver = self.cp_model.CpSolver()
        status = solver.Solve(model)
        feasible = status in {self.cp_model.OPTIMAL, self.cp_model.FEASIBLE}
        assignment = []
        objective_value = None
        if feasible:
            assignment = [
                {"row": row, "col": col, "cost": int(cost_matrix[row][col])}
                for row in range(rows)
                for col in range(cols)
                if solver.Value(picks[(row, col)])
            ]
            objective_value = int(solver.ObjectiveValue())
        summary = "The assignment problem solved successfully." if feasible else "The assignment problem did not solve successfully."
        return AnalysisResults(
            adapter_family=self.name,
            analysis_kind=spec.analysis_kind,
            adapter_name=self.name,
            adapter_version="0.1.0",
            timestamp=timestamp,
            runtime_seconds=perf_counter() - start,
            backend=backend,
            summary=summary,
            measurements=[
                measurement("feasible", feasible),
                measurement("objective_value", objective_value),
            ],
            details={"assignment": assignment, "status": int(status)},
            errors=[] if feasible else [f"OR-Tools solver status {status}"],
        )
