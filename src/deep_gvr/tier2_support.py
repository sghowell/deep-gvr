from __future__ import annotations

from dataclasses import dataclass

from .contracts import Backend


@dataclass(frozen=True, slots=True)
class Tier2FamilySupport:
    adapter_family: str
    required_packages: tuple[str, ...]
    supported_backends: tuple[Backend, ...]
    benchmark_cases: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "adapter_family": self.adapter_family,
            "required_packages": list(self.required_packages),
            "supported_backends": [backend.value for backend in self.supported_backends],
            "benchmark_cases": list(self.benchmark_cases),
        }


_TIER2_SUPPORT_MATRIX: tuple[Tier2FamilySupport, ...] = (
    Tier2FamilySupport(
        adapter_family="symbolic_math",
        required_packages=("sympy",),
        supported_backends=(Backend.LOCAL,),
        benchmark_cases=("symbolic-verified-equivalence", "symbolic-rejected-derivative"),
    ),
    Tier2FamilySupport(
        adapter_family="optimization",
        required_packages=("scipy", "ortools"),
        supported_backends=(Backend.LOCAL,),
        benchmark_cases=("optimization-verified-linear-program", "optimization-rejected-assignment"),
    ),
    Tier2FamilySupport(
        adapter_family="dynamics",
        required_packages=("scipy", "qutip"),
        supported_backends=(Backend.LOCAL,),
        benchmark_cases=("dynamics-verified-decay",),
    ),
    Tier2FamilySupport(
        adapter_family="qec_decoder_benchmark",
        required_packages=("numpy", "stim", "pymatching"),
        supported_backends=(Backend.LOCAL, Backend.MODAL, Backend.SSH),
        benchmark_cases=("simulation-verified-distance5", "simulation-rejected-distance7"),
    ),
    Tier2FamilySupport(
        adapter_family="mbqc_graph_state",
        required_packages=("graphix",),
        supported_backends=(Backend.LOCAL,),
        benchmark_cases=("mbqc-verified-graphix-pattern",),
    ),
    Tier2FamilySupport(
        adapter_family="photonic_linear_optics",
        required_packages=("perceval",),
        supported_backends=(Backend.LOCAL,),
        benchmark_cases=("photonic-verified-basic-state",),
    ),
    Tier2FamilySupport(
        adapter_family="neutral_atom_control",
        required_packages=("pulser",),
        supported_backends=(Backend.LOCAL,),
        benchmark_cases=("neutral-atom-verified-register",),
    ),
    Tier2FamilySupport(
        adapter_family="topological_qec_design",
        required_packages=("tqec",),
        supported_backends=(Backend.LOCAL,),
        benchmark_cases=("tqec-verified-gallery-block-graph",),
    ),
    Tier2FamilySupport(
        adapter_family="zx_rewrite_verification",
        required_packages=("pyzx",),
        supported_backends=(Backend.LOCAL,),
        benchmark_cases=("zx-verified-qasm-rewrite",),
    ),
)


def tier2_family_support_matrix() -> tuple[Tier2FamilySupport, ...]:
    return _TIER2_SUPPORT_MATRIX


def supported_tier2_families() -> list[str]:
    return [item.adapter_family for item in _TIER2_SUPPORT_MATRIX]


def tier2_family_support(adapter_family: str) -> Tier2FamilySupport | None:
    for item in _TIER2_SUPPORT_MATRIX:
        if item.adapter_family == adapter_family:
            return item
    return None


def tier2_support_case_ids() -> tuple[str, ...]:
    case_ids: list[str] = []
    for item in _TIER2_SUPPORT_MATRIX:
        case_ids.extend(item.benchmark_cases)
    return tuple(case_ids)


def backend_dispatch_supported_families() -> tuple[str, ...]:
    return tuple(
        item.adapter_family
        for item in _TIER2_SUPPORT_MATRIX
        if any(backend is not Backend.LOCAL for backend in item.supported_backends)
    )
