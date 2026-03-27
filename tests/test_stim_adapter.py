from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests import _path_setup  # noqa: F401

from deep_gvr.contracts import Backend, SimSpec

from adapters.stim_adapter import StimAdapter

ROOT = Path(__file__).resolve().parents[1]


class StimAdapterSmokeTests(unittest.TestCase):
    def test_adapter_runs_local_surface_code_spec(self) -> None:
        spec = SimSpec.from_dict(
            {
                "simulator": "stim",
                "task": {
                    "code": "surface_code",
                    "task_type": "rotated_memory_z",
                    "distance": [3, 5],
                    "rounds_per_distance": "2d",
                    "noise_model": "depolarizing",
                    "error_rates": [0.003, 0.006],
                    "decoder": "pymatching",
                    "shots_per_point": 100,
                },
                "resources": {
                    "timeout_seconds": 120,
                    "max_parallel": 1,
                },
            }
        )
        results = StimAdapter().run(spec, Backend.LOCAL)

        self.assertEqual(results.simulator, "stim")
        self.assertEqual(results.backend, Backend.LOCAL)
        self.assertEqual(len(results.data), 4)
        self.assertEqual(results.errors, [])
        self.assertGreaterEqual(results.runtime_seconds, 0.0)
        self.assertIn(results.analysis.threshold_method, {"monotonic_distance_improvement", "no_crossing_detected"})

    def test_adapter_returns_structured_error_for_unsupported_backend(self) -> None:
        spec = SimSpec.from_dict(json.loads((ROOT / "templates" / "sim_spec.template.json").read_text(encoding="utf-8")))
        results = StimAdapter().run(spec, Backend.MODAL)

        self.assertEqual(results.backend, Backend.MODAL)
        self.assertEqual(results.data, [])
        self.assertEqual(results.analysis.threshold_method, "backend_unavailable")
        self.assertNotEqual(results.errors, [])

    def test_adapter_cli_writes_normalized_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_path = Path(tmpdir) / "spec.json"
            output_path = Path(tmpdir) / "results.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "simulator": "stim",
                        "task": {
                            "code": "surface_code",
                            "task_type": "rotated_memory_z",
                            "distance": [3],
                            "rounds_per_distance": "2d",
                            "noise_model": "depolarizing",
                            "error_rates": [0.005],
                            "decoder": "pymatching",
                            "shots_per_point": 50,
                        },
                        "resources": {
                            "timeout_seconds": 60,
                            "max_parallel": 1,
                        },
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "adapters" / "stim_adapter.py"),
                    "--spec",
                    str(spec_path),
                    "--backend",
                    "local",
                    "--output",
                    str(output_path),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["simulator"], "stim")
            self.assertEqual(payload["backend"], "local")
            self.assertEqual(len(payload["data"]), 1)
            self.assertEqual(payload["errors"], [])


if __name__ == "__main__":
    unittest.main()
