from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests import _path_setup  # noqa: F401

from deep_gvr.contracts import ProbeStatus, VerificationVerdict
from deep_gvr.evaluation import (
    CommandExecutionResult,
    HermesPromptRoleRunner,
    LiveEvalConfig,
    benchmark_routing_probe,
    load_benchmark_suite,
    run_benchmark_suite,
    write_benchmark_report,
)

ROOT = Path(__file__).resolve().parents[1]


class EvaluationTests(unittest.TestCase):
    def _successful_live_executor(self, command: list[str], cwd: Path) -> CommandExecutionResult:
        del cwd
        query = command[command.index("-q") + 1]
        if "Role: generator" in query:
            payload = {
                "hypothesis": "The surface code has a threshold under standard depolarizing noise assumptions.",
                "approach": "State the well-known threshold claim directly.",
                "technical_details": ["Threshold behavior follows from the benchmark fixture context."],
                "expected_results": ["The verifier should accept the claim at Tier 1."],
                "assumptions": ["Standard depolarizing noise assumptions apply."],
                "limitations": ["This is a test executor response."],
                "references": ["Dennis et al. 2002"],
                "revision_notes": [],
            }
            return CommandExecutionResult(
                returncode=0,
                stdout=f"session: live-test\n{json.dumps(payload)}\n",
                stderr="",
            )
        if "Role: verifier" in query:
            payload = {
                "verdict": "VERIFIED",
                "tier1": {
                    "checks": [
                        {
                            "check": "benchmark_ground_truth",
                            "status": "pass",
                            "detail": "The claim matches the benchmark ground truth.",
                        }
                    ],
                    "overall": "VERIFIED",
                    "flaws": [],
                    "caveats": [],
                },
                "tier2": None,
                "tier3": [],
                "flaws": [],
                "caveats": [],
                "cannot_verify_reason": None,
            }
            return CommandExecutionResult(
                returncode=0,
                stdout=f"{json.dumps(payload)}\nsession: live-test\n",
                stderr="",
            )
        return CommandExecutionResult(returncode=1, stdout="", stderr=f"Unexpected command: {command}")

    def _failing_live_executor(self, command: list[str], cwd: Path) -> CommandExecutionResult:
        del command, cwd
        return CommandExecutionResult(returncode=1, stdout="", stderr="simulated hermes failure")

    def test_load_benchmark_suite_reads_expected_cases(self) -> None:
        cases = load_benchmark_suite(ROOT / "eval" / "known_problems.json")
        self.assertGreaterEqual(len(cases), 8)
        self.assertEqual(cases[0].id, "known-correct-surface-threshold")

    def test_load_benchmark_suite_filters_cases(self) -> None:
        cases = load_benchmark_suite(
            ROOT / "eval" / "known_problems.json",
            case_ids=["formal-proved-repetition-majority"],
        )
        self.assertEqual([item.id for item in cases], ["formal-proved-repetition-majority"])

    def test_run_benchmark_suite_matches_expected_baseline(self) -> None:
        report = run_benchmark_suite(
            ROOT / "eval" / "known_problems.json",
            routing_probe=benchmark_routing_probe(ProbeStatus.FALLBACK),
        )

        self.assertEqual(report.mode, "deterministic")
        self.assertEqual(report.run_id, "baseline")
        self.assertEqual(report.runner_backend, "fixture")
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
            self.assertEqual(payload["mode"], "deterministic")
            self.assertEqual(payload["summary"]["failed_cases"], 0)
            self.assertEqual(payload["suite_path"], "eval/known_problems.json")

    def test_live_mode_records_artifacts_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_root = Path(tmpdir) / "live-results"
            report = run_benchmark_suite(
                ROOT / "eval" / "known_problems.json",
                routing_probe=benchmark_routing_probe(ProbeStatus.FALLBACK),
                mode="live",
                output_root=output_root,
                case_ids=["known-correct-surface-threshold"],
                live_config=LiveEvalConfig(),
                executor=self._successful_live_executor,
            )

            self.assertEqual(report.mode, "live")
            self.assertEqual(report.runner_backend, "hermes_chat")
            self.assertEqual(report.summary.total_cases, 1)
            self.assertEqual(report.summary.failed_cases, 0)
            case = report.cases[0]
            self.assertTrue(case.passed)
            self.assertEqual(case.actual_verdict, VerificationVerdict.VERIFIED)
            self.assertIsNone(case.error)
            self.assertGreaterEqual(case.runtime_seconds, 0.0)
            self.assertTrue(any("temperature overrides" in note for note in case.notes))
            self.assertTrue(any(item.endswith("candidate_solution.json") for item in case.artifacts))
            self.assertTrue(any(item.endswith("role_transcripts.json") for item in case.artifacts))
            self.assertTrue((output_root / "cases" / case.id / "candidate_solution.json").exists())
            self.assertTrue((output_root / "cases" / case.id / "verification_report.json").exists())
            self.assertTrue((output_root / "cases" / case.id / "case_result.json").exists())
            transcripts = json.loads(
                (output_root / "cases" / case.id / "role_transcripts.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(transcripts["calls"]), 2)
            self.assertIn("Response budget:", transcripts["calls"][0]["query"])

    def test_compact_prompt_profile_emits_shorter_query_than_full(self) -> None:
        prompt_root = ROOT / "prompts"
        compact_runner = HermesPromptRoleRunner(
            LiveEvalConfig(prompt_profile="compact"),
            prompt_root=prompt_root,
        )
        full_runner = HermesPromptRoleRunner(
            LiveEvalConfig(prompt_profile="full"),
            prompt_root=prompt_root,
        )
        payload = {
            "session_id": "session_eval",
            "problem": "Explain why the surface code has a threshold.",
            "domain": "qec",
            "literature_context": [],
            "prior_verdicts": [],
        }
        response_contract = {
            "hypothesis": "string",
            "approach": "string",
            "technical_details": ["string"],
            "expected_results": ["string"],
            "assumptions": ["string"],
            "limitations": ["string"],
            "references": ["string"],
            "revision_notes": ["string"],
        }
        prompt_text = (prompt_root / "generator.md").read_text(encoding="utf-8")

        compact_query = compact_runner._build_query(
            role="generator",
            prompt_text=prompt_text,
            payload=payload,
            response_contract=response_contract,
            route_notes=["Use prompt separation plus temperature decorrelation and record the limitation."],
            route_temperature=0.7,
        )
        full_query = full_runner._build_query(
            role="generator",
            prompt_text=prompt_text,
            payload=payload,
            response_contract=response_contract,
            route_notes=["Use prompt separation plus temperature decorrelation and record the limitation."],
            route_temperature=0.7,
        )

        self.assertIn("Response budget:", compact_query)
        self.assertNotIn("Response budget:", full_query)
        self.assertLess(len(compact_query), len(full_query))

    def test_live_mode_records_error_artifact_on_executor_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_root = Path(tmpdir) / "live-results"
            report = run_benchmark_suite(
                ROOT / "eval" / "known_problems.json",
                routing_probe=benchmark_routing_probe(ProbeStatus.FALLBACK),
                mode="live",
                output_root=output_root,
                case_ids=["known-correct-surface-threshold"],
                live_config=LiveEvalConfig(),
                executor=self._failing_live_executor,
            )

            case = report.cases[0]
            self.assertFalse(case.passed)
            self.assertEqual(case.iterations, 0)
            self.assertIsNotNone(case.error)
            self.assertTrue(any(item.endswith("live_error.json") for item in case.artifacts))
            self.assertTrue((output_root / "cases" / case.id / "live_error.json").exists())

    def test_live_mode_refuses_to_overwrite_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_root = Path(tmpdir) / "live-results"
            report = run_benchmark_suite(
                ROOT / "eval" / "known_problems.json",
                routing_probe=benchmark_routing_probe(ProbeStatus.FALLBACK),
                mode="live",
                output_root=output_root,
                case_ids=["known-correct-surface-threshold"],
                live_config=LiveEvalConfig(),
                executor=self._successful_live_executor,
            )

            with self.assertRaises(ValueError):
                write_benchmark_report(report, ROOT / "eval" / "results" / "baseline_results.json")

    def test_committed_baseline_matches_runner_output(self) -> None:
        report = run_benchmark_suite(
            ROOT / "eval" / "known_problems.json",
            routing_probe=benchmark_routing_probe(ProbeStatus.FALLBACK),
        )
        baseline = json.loads((ROOT / "eval" / "results" / "baseline_results.json").read_text(encoding="utf-8"))
        self.assertEqual(report.to_dict(), baseline)


if __name__ == "__main__":
    unittest.main()
