from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StimAdapterSmokeTests(unittest.TestCase):
    def test_adapter_writes_normalized_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "adapters" / "stim_adapter.py"),
                    "--spec",
                    str(ROOT / "templates" / "sim_spec.template.json"),
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
            self.assertIn("errors", payload)


if __name__ == "__main__":
    unittest.main()
