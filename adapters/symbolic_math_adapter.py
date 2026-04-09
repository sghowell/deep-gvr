from __future__ import annotations

from time import perf_counter

from deep_gvr.contracts import AnalysisResults, AnalysisSpec, Backend

from adapters.analysis_utils import analysis_timestamp, build_error_result, measurement
from adapters.base_adapter import AnalysisAdapter

try:
    import sympy
except ImportError:  # pragma: no cover - exercised through structured adapter error handling
    sympy = None


class SymbolicMathAdapter(AnalysisAdapter):
    name = "symbolic_math"

    def __init__(self, *, sympy_module= sympy) -> None:
        self.sympy = sympy_module

    def run(self, spec: AnalysisSpec, backend: Backend) -> AnalysisResults:
        start = perf_counter()
        timestamp = analysis_timestamp()
        if self.sympy is None:
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="SymPy is not installed.",
                errors=["Install SymPy to enable symbolic-math analysis."],
            )

        task = dict(spec.task)
        try:
            if spec.analysis_kind == "expression_equivalence":
                lhs = self.sympy.sympify(task["lhs"])
                rhs = self.sympy.sympify(task["rhs"])
                equivalent = bool(self.sympy.simplify(lhs - rhs) == 0)
                summary = "The symbolic expressions are equivalent." if equivalent else "The symbolic expressions differ."
                measurements = [measurement("equivalent", equivalent)]
                details = {"lhs": str(lhs), "rhs": str(rhs)}
            elif spec.analysis_kind == "derivative_check":
                expression = self.sympy.sympify(task["expression"])
                symbol = self.sympy.Symbol(task["symbol"])
                expected = self.sympy.sympify(task["expected_derivative"])
                derivative = self.sympy.diff(expression, symbol)
                equivalent = bool(self.sympy.simplify(derivative - expected) == 0)
                summary = "The symbolic derivative matches the expected derivative." if equivalent else "The symbolic derivative does not match."
                measurements = [measurement("derivative_matches", equivalent)]
                details = {
                    "expression": str(expression),
                    "symbol": str(symbol),
                    "derived_expression": str(derivative),
                    "expected_derivative": str(expected),
                }
            else:
                return build_error_result(
                    adapter_family=self.name,
                    analysis_kind=spec.analysis_kind,
                    adapter_name=self.name,
                    backend=backend,
                    start=start,
                    timestamp=timestamp,
                    summary="Unsupported symbolic analysis kind.",
                    errors=[f"Unsupported symbolic analysis kind {spec.analysis_kind!r}."],
                    details={"task": task},
                )
        except Exception as exc:  # pragma: no cover - defensive boundary
            return build_error_result(
                adapter_family=self.name,
                analysis_kind=spec.analysis_kind,
                adapter_name=self.name,
                backend=backend,
                start=start,
                timestamp=timestamp,
                summary="The symbolic analysis failed.",
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
            summary=summary,
            measurements=measurements,
            details=details,
            errors=[],
        )
