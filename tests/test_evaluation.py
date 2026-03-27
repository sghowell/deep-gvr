from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests import _path_setup  # noqa: F401

from deep_gvr.contracts import ProbeStatus
from deep_gvr.evaluation import benchmark_routing_probe, load_benchmark_suite, run_benchmark_suite

ROOT = Path(__file__).resolve().parents[1]


class EvaluationTests(unittest.TestCase):
    def test_load_benchmark_suite_reads_expected_cases(self) -> None:
        cases = load_benchmark_suite(ROOT / "eval" / "known_problems.json")
        self.assertGreaterEqual(len(cases), 8)
        self.assertEqual(cases[0].id, "known-correct-surface-threshold")

    def test_run_benchmark_suite_matches_expected_baseline(self) -> None:
        report = run_benchmark_suite(
            ROOT / "eval" / "known_problems.json",
            routing_probe=benchmark_routing_probe(ProbeStatus.FALLBACK),
        )

        self.assertEqual(report.routing_probe_status, ProbeStatus.FALLBACK)
        self.assertEqual(report.summary.total_cases, len(report.cases))
        self.assertEqual(report.summary.failed_cases, 0)
        self.assertEqual(report.summary.false_positive_rate, 0.0)
        self.assertEqual(report.summary.tier_accuracy, 1.0)
        self.assertTrue(report.summary.meets_false_positive_bar)

    def test_eval_cli_writes_results_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.json"
            completed = subprocess.run(
                [
                    "python3",
                    str(ROOT / "eval" / "run_eval.py"),
                    "--routing-probe",
                    "fallback",
                    "--output",
                    str(output_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["failed_cases"], 0)
            self.assertEqual(payload["suite_path"], "eval/known_problems.json")

    def test_committed_baseline_matches_runner_output(self) -> None:
        report = run_benchmark_suite(
            ROOT / "eval" / "known_problems.json",
            routing_probe=benchmark_routing_probe(ProbeStatus.FALLBACK),
        )
        baseline = json.loads((ROOT / "eval" / "results" / "baseline_results.json").read_text(encoding="utf-8"))
        self.assertEqual(report.to_dict(), baseline)


if __name__ == "__main__":
    unittest.main()
