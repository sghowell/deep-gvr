from __future__ import annotations

from deep_gvr.contracts import Tier2Config
from deep_gvr.tier2_support import supported_tier2_families

from adapters.dynamics_adapter import DynamicsAdapter
from adapters.mbqc_graph_state_adapter import MbqcGraphStateAdapter
from adapters.neutral_atom_control_adapter import NeutralAtomControlAdapter
from adapters.optimization_adapter import OptimizationAdapter
from adapters.photonic_linear_optics_adapter import PhotonicLinearOpticsAdapter
from adapters.qec_decoder_benchmark_adapter import QecDecoderBenchmarkAdapter
from adapters.symbolic_math_adapter import SymbolicMathAdapter
from adapters.topological_qec_design_adapter import TopologicalQecDesignAdapter
from adapters.zx_rewrite_verification_adapter import ZxRewriteVerificationAdapter


def build_analysis_adapter(adapter_family: str, *, tier2_config: Tier2Config | None = None):
    registry = {
        "symbolic_math": lambda: SymbolicMathAdapter(),
        "optimization": lambda: OptimizationAdapter(),
        "dynamics": lambda: DynamicsAdapter(),
        "qec_decoder_benchmark": lambda: QecDecoderBenchmarkAdapter(tier2_config=tier2_config),
        "mbqc_graph_state": lambda: MbqcGraphStateAdapter(),
        "photonic_linear_optics": lambda: PhotonicLinearOpticsAdapter(),
        "neutral_atom_control": lambda: NeutralAtomControlAdapter(),
        "topological_qec_design": lambda: TopologicalQecDesignAdapter(),
        "zx_rewrite_verification": lambda: ZxRewriteVerificationAdapter(),
    }
    builder = registry.get(adapter_family)
    if builder is None:
        return None
    return builder()


def supported_analysis_families() -> list[str]:
    return supported_tier2_families()
