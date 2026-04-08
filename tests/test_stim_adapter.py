from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import _path_setup  # noqa: F401

from deep_gvr.contracts import Backend, ModalConfig, SSHConfig, SimDataPoint, SimSpec, Tier2Config

from adapters.stim_adapter import StimAdapter

ROOT = Path(__file__).resolve().parents[1]


class StimAdapterSmokeTests(unittest.TestCase):
    def _spec(self) -> SimSpec:
        return SimSpec.from_dict(
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

    def _write_executable(self, path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755)

    def test_adapter_runs_local_surface_code_spec(self) -> None:
        results = StimAdapter().run(self._spec(), Backend.LOCAL)

        self.assertEqual(results.simulator, "stim")
        self.assertEqual(results.backend, Backend.LOCAL)
        self.assertEqual(len(results.data), 4)
        self.assertEqual(results.errors, [])
        self.assertGreaterEqual(results.runtime_seconds, 0.0)
        self.assertIn(results.analysis.threshold_method, {"monotonic_distance_improvement", "no_crossing_detected"})

    def test_adapter_runs_modal_backend_through_fake_modal_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            bin_dir.mkdir()
            self._write_executable(
                bin_dir / "modal",
                "#!/bin/sh\n"
                "if [ \"$1\" != \"run\" ]; then\n"
                "  exit 2\n"
                "fi\n"
                "shift\n"
                f"exec \"{sys.executable}\" \"$@\"\n",
            )

            with patch.dict(os.environ, {"PATH": f"{bin_dir}:{os.environ.get('PATH', '')}"}, clear=False):
                results = StimAdapter().run(self._spec(), Backend.MODAL)

        self.assertEqual(results.backend, Backend.MODAL)
        self.assertEqual(len(results.data), 4)
        self.assertEqual(results.errors, [])
        self.assertIn(results.analysis.threshold_method, {"monotonic_distance_improvement", "no_crossing_detected"})

    def test_adapter_runs_ssh_backend_through_fake_ssh_and_scp_binaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            bin_dir = tmp_path / "bin"
            bin_dir.mkdir()
            remote_workspace = tmp_path / "remote-workspace"
            remote_workspace.mkdir()
            (remote_workspace / "adapters").symlink_to(ROOT / "adapters", target_is_directory=True)
            (remote_workspace / "src").symlink_to(ROOT / "src", target_is_directory=True)

            self._write_executable(
                bin_dir / "ssh",
                textwrap.dedent(
                    f"""\
                    #!{sys.executable}
                    import subprocess
                    import sys

                    args = sys.argv[1:]
                    while args and args[0].startswith("-"):
                        flag = args.pop(0)
                        if flag in {{"-i", "-o"}} and args:
                            args.pop(0)
                    if args:
                        args.pop(0)
                    command = args[0] if args else ""
                    completed = subprocess.run(command, shell=True, capture_output=True, text=True, check=False)
                    sys.stdout.write(completed.stdout)
                    sys.stderr.write(completed.stderr)
                    raise SystemExit(completed.returncode)
                    """
                ),
            )
            self._write_executable(
                bin_dir / "scp",
                textwrap.dedent(
                    f"""\
                    #!{sys.executable}
                    import pathlib
                    import shutil
                    import sys

                    args = sys.argv[1:]
                    while args and args[0].startswith("-"):
                        flag = args.pop(0)
                        if flag in {{"-i", "-o"}} and args:
                            args.pop(0)

                    src, dst = args

                    def resolve(value: str) -> pathlib.Path:
                        if ":" in value:
                            value = value.split(":", 1)[1]
                        return pathlib.Path(value)

                    resolved_src = resolve(src)
                    resolved_dst = resolve(dst)
                    resolved_dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(resolved_src, resolved_dst)
                    """
                ),
            )

            config = Tier2Config(
                ssh=SSHConfig(
                    host="gpu-node",
                    user="alice",
                    remote_workspace=str(remote_workspace),
                    python_bin=sys.executable,
                )
            )

            with patch.dict(os.environ, {"PATH": f"{bin_dir}:{os.environ.get('PATH', '')}"}, clear=False):
                results = StimAdapter(tier2_config=config).run(self._spec(), Backend.SSH)

        self.assertEqual(results.backend, Backend.SSH)
        self.assertEqual(len(results.data), 4)
        self.assertEqual(results.errors, [])
        self.assertIn(results.analysis.threshold_method, {"monotonic_distance_improvement", "no_crossing_detected"})

    def test_adapter_returns_structured_error_for_misconfigured_ssh_backend(self) -> None:
        results = StimAdapter(tier2_config=Tier2Config(ssh=SSHConfig())).run(self._spec(), Backend.SSH)

        self.assertEqual(results.backend, Backend.SSH)
        self.assertEqual(results.data, [])
        self.assertEqual(results.analysis.threshold_method, "backend_misconfigured")
        self.assertNotEqual(results.errors, [])

    def test_adapter_cli_writes_normalized_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_path = Path(tmpdir) / "spec.json"
            output_path = Path(tmpdir) / "results.json"
            spec_path.write_text(json.dumps(self._spec().to_dict()), encoding="utf-8")
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
        self.assertEqual(len(payload["data"]), 4)
        self.assertEqual(payload["errors"], [])

    def test_monotonic_analysis_does_not_report_test_error_rate_as_threshold(self) -> None:
        analysis = StimAdapter()._analyze(
            [
                SimDataPoint(
                    distance=3,
                    rounds=3,
                    physical_error_rate=0.001,
                    logical_error_rate=2.2e-4,
                    shots=100000,
                    errors_observed=22,
                    decoder="pymatching",
                ),
                SimDataPoint(
                    distance=5,
                    rounds=5,
                    physical_error_rate=0.001,
                    logical_error_rate=3.0e-5,
                    shots=100000,
                    errors_observed=3,
                    decoder="pymatching",
                ),
                SimDataPoint(
                    distance=7,
                    rounds=7,
                    physical_error_rate=0.001,
                    logical_error_rate=1.0e-5,
                    shots=100000,
                    errors_observed=1,
                    decoder="pymatching",
                ),
            ]
        )

        self.assertEqual(analysis.threshold_method, "monotonic_distance_improvement")
        self.assertIsNone(analysis.threshold_estimate)
        self.assertEqual(analysis.below_threshold_distances, [5, 7])


if __name__ == "__main__":
    unittest.main()
