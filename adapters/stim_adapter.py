from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from deep_gvr.contracts import Backend, SimAnalysis, SimResults, SimSpec

from adapters.base_adapter import SimulatorAdapter


class StimAdapter(SimulatorAdapter):
    name = "stim"

    def run(self, spec: SimSpec, backend: Backend) -> SimResults:
        timestamp = datetime.now(UTC).isoformat()
        errors: list[str] = []

        if backend is Backend.LOCAL:
            if shutil.which("stim") is None:
                errors.append("Stim CLI not found; this adapter is a readiness scaffold and cannot run local simulations yet.")
            else:
                errors.append("Stim CLI detected, but the full adapter implementation is still pending.")
        elif backend is Backend.MODAL:
            errors.append("Modal backend is scaffolded but not implemented in the readiness phase.")
        elif backend is Backend.SSH:
            errors.append("SSH backend is scaffolded but not implemented in the readiness phase.")

        errors.append(
            f"Requested simulator={spec.simulator} code={spec.task.code} task_type={spec.task.task_type}; replace the scaffold with real circuit generation and decoding."
        )

        return SimResults(
            simulator=self.name,
            adapter_version="0.1.0",
            timestamp=timestamp,
            runtime_seconds=0.0,
            backend=backend,
            data=[],
            analysis=SimAnalysis(
                threshold_estimate=None,
                threshold_method="not_computed",
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
