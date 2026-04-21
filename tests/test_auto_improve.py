from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests import _path_setup  # noqa: F401

from deep_gvr.auto_improve import AutoImproveEvaluationReport, evaluate_auto_improve, write_auto_improve_evaluation_report
from deep_gvr.json_schema import validate

ROOT = Path(__file__).resolve().parents[1]


class AutoImproveEvaluationTests(unittest.TestCase):
    def _load_json(self, relative_path: str) -> dict:
        return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))

    def test_auto_improve_evaluation_round_trip(self) -> None:
        payload = self._load_json("templates/auto_improve_evaluation.template.json")
        model = AutoImproveEvaluationReport.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)

    def test_auto_improve_evaluation_fixture_validates(self) -> None:
        schema = self._load_json("schemas/auto_improve_evaluation.schema.json")
        fixture = self._load_json("templates/auto_improve_evaluation.template.json")
        validate(fixture, schema)

    def test_evaluate_auto_improve_reports_no_drift_for_deterministic_suite(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report = evaluate_auto_improve(
                ROOT / "eval" / "known_problems.json",
                output_root=Path(tmpdir),
                deterministic_subset="core-science",
                deterministic_repeat_count=1,
                include_live=False,
            )

        deterministic = next(item for item in report.evaluations if item.mode == "deterministic")
        live = next(item for item in report.evaluations if item.mode == "live")
        self.assertEqual(deterministic.status, "completed")
        self.assertFalse(deterministic.drift_detected)
        self.assertEqual(live.status, "skipped")
        self.assertEqual(report.recommendation.decision, "disabled_by_default")
        self.assertTrue(report.policy.experimental_blocks_release)
        self.assertTrue(report.isolation.manifest_unchanged)
        self.assertTrue(report.isolation.worktree_unchanged)

    def test_write_auto_improve_evaluation_report_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report = evaluate_auto_improve(
                ROOT / "eval" / "known_problems.json",
                output_root=Path(tmpdir) / "eval-root",
                deterministic_subset="core-science",
                deterministic_repeat_count=1,
                include_live=False,
            )
            output_path = Path(tmpdir) / "report.json"
            write_auto_improve_evaluation_report(report, output_path)

            self.assertTrue(output_path.exists())
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["recommendation"]["decision"], "disabled_by_default")

    def test_evaluate_auto_improve_script_writes_requested_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "auto-improve-report.json"
            completed = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "evaluate_auto_improve.py"),
                    "--output",
                    str(output_path),
                    "--json",
                    "--deterministic-subset",
                    "core-science",
                    "--deterministic-repeat",
                    "1",
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(output_path.exists())
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["recommendation"]["decision"], "disabled_by_default")


if __name__ == "__main__":
    unittest.main()
