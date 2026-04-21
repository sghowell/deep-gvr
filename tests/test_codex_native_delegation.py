from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from tests import _path_setup  # noqa: F401

from deep_gvr.codex_native_delegation import (
    CommandExecutionResult,
    CodexNativeDelegationEvaluationReport,
    evaluate_codex_native_delegation,
    write_codex_native_delegation_evaluation_report,
)
from deep_gvr.json_schema import validate

ROOT = Path(__file__).resolve().parents[1]


class CodexNativeDelegationEvaluationTests(unittest.TestCase):
    def _load_json(self, relative_path: str) -> dict:
        return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))

    def test_codex_native_delegation_round_trip(self) -> None:
        payload = self._load_json("templates/codex_native_delegation_evaluation.template.json")
        model = CodexNativeDelegationEvaluationReport.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)

    def test_codex_native_delegation_fixture_validates(self) -> None:
        schema = self._load_json("schemas/codex_native_delegation_evaluation.schema.json")
        fixture = self._load_json("templates/codex_native_delegation_evaluation.template.json")
        validate(fixture, schema)

    def test_evaluate_codex_native_delegation_reports_recommended_boundary(self) -> None:
        def executor(command: list[str], cwd: Path) -> CommandExecutionResult:
            self.assertEqual(command, ["codex", "--version"])
            self.assertEqual(cwd, ROOT)
            return CommandExecutionResult(returncode=0, stdout="codex 0.10.0\n", stderr="")

        with tempfile.TemporaryDirectory() as tmpdir:
            report = evaluate_codex_native_delegation(
                output_root=Path(tmpdir) / "report-root",
                executor=executor,
                clock=lambda: datetime(2026, 4, 21, 0, 0, tzinfo=UTC),
            )

        self.assertEqual(report.overall_status.value, "ready")
        self.assertTrue(report.codex_available)
        self.assertEqual(report.codex_version, "codex 0.10.0")
        self.assertEqual(report.recommendation.decision, "keep_current_boundary")
        by_id = {item.capability_id: item for item in report.capabilities}
        self.assertEqual(by_id["native_role_execution"].promotion_decision, "already_realized")
        self.assertEqual(by_id["parallel_work_ownership"].promotion_decision, "keep_operator_pack")
        self.assertEqual(by_id["live_subagent_state_integration"].status.value, "blocked")

    def test_evaluate_codex_native_delegation_surfaces_missing_codex_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report = evaluate_codex_native_delegation(
                output_root=Path(tmpdir) / "report-root",
                codex_binary="definitely-missing-codex-binary",
                clock=lambda: datetime(2026, 4, 21, 0, 0, tzinfo=UTC),
            )

        self.assertEqual(report.overall_status.value, "attention")
        self.assertFalse(report.codex_available)
        self.assertIn("not currently available on PATH", report.notes[0])
        self.assertEqual(report.recommendation.decision, "keep_current_boundary")

    def test_write_codex_native_delegation_report_writes_json(self) -> None:
        def executor(command: list[str], cwd: Path) -> CommandExecutionResult:
            return CommandExecutionResult(returncode=0, stdout="codex 0.10.0\n", stderr="")

        with tempfile.TemporaryDirectory() as tmpdir:
            report = evaluate_codex_native_delegation(
                output_root=Path(tmpdir) / "report-root",
                executor=executor,
                clock=lambda: datetime(2026, 4, 21, 0, 0, tzinfo=UTC),
            )
            output_path = Path(tmpdir) / "report.json"
            write_codex_native_delegation_evaluation_report(report, output_path)

            self.assertTrue(output_path.exists())
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["recommendation"]["decision"], "keep_current_boundary")

    def test_evaluate_codex_native_delegation_script_writes_requested_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "codex-native-delegation-report.json"
            completed = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "evaluate_codex_native_delegation.py"),
                    "--output",
                    str(output_path),
                    "--json",
                    "--codex-binary",
                    "definitely-missing-codex-binary",
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(output_path.exists())
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["overall_status"], "attention")
            self.assertEqual(payload["recommendation"]["decision"], "keep_current_boundary")


if __name__ == "__main__":
    unittest.main()
