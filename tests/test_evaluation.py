from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from tests import _path_setup  # noqa: F401

from deep_gvr.cli import load_runtime_config
from deep_gvr.contracts import (
    AnalysisMeasurement,
    AnalysisResults,
    Backend,
    CandidateSolution,
    DeepGvrConfig,
    ProbeStatus,
    VerificationVerdict,
)
from deep_gvr.evaluation import (
    CommandExecutionResult,
    HermesPromptRoleRunner,
    LiveEvalConfig,
    _accept_verified_refutation,
    available_benchmark_subsets,
    benchmark_routing_probe,
    format_benchmark_consistency_overview,
    format_benchmark_report_overview,
    load_benchmark_suite,
    run_repeated_benchmark_suite,
    run_benchmark_suite,
    write_benchmark_report,
)
from deep_gvr.prompt_profiles import _build_compact_generic_query
from deep_gvr.routing import EffectiveModelRoute
from deep_gvr.tier1 import VerificationRequest

ROOT = Path(__file__).resolve().parents[1]


class EvaluationTests(unittest.TestCase):
    def _write_config(
        self,
        config_path: Path,
        evidence_dir: Path,
        *,
        orchestrator_backend: str = "hermes",
        provider: str = "default",
        model: str = "",
        generator_provider: str | None = None,
        generator_model: str | None = None,
        verifier_provider: str | None = None,
        verifier_model: str | None = None,
        reviser_provider: str | None = None,
        reviser_model: str | None = None,
        context_file: str = "",
        domain_default: str = "qec",
    ) -> None:
        payload = DeepGvrConfig().to_dict()
        payload["evidence"]["directory"] = str(evidence_dir)
        payload["runtime"]["orchestrator_backend"] = orchestrator_backend
        payload["models"]["orchestrator"]["provider"] = provider
        payload["models"]["orchestrator"]["model"] = model
        if generator_provider is not None:
            payload["models"]["generator"]["provider"] = generator_provider
        if generator_model is not None:
            payload["models"]["generator"]["model"] = generator_model
        if verifier_provider is not None:
            payload["models"]["verifier"]["provider"] = verifier_provider
        if verifier_model is not None:
            payload["models"]["verifier"]["model"] = verifier_model
        if reviser_provider is not None:
            payload["models"]["reviser"]["provider"] = reviser_provider
        if reviser_model is not None:
            payload["models"]["reviser"]["model"] = reviser_model
        payload["domain"]["default"] = domain_default
        payload["domain"]["context_file"] = context_file
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

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

    def _route_fallback_live_executor(self, command: list[str], cwd: Path) -> CommandExecutionResult:
        provider = command[command.index("--provider") + 1] if "--provider" in command else "default"
        model = command[command.index("--model") + 1] if "--model" in command else "configured-by-hermes"
        if provider == "openrouter" and model.startswith("broken-"):
            return CommandExecutionResult(
                returncode=1,
                stdout="",
                stderr="BadRequestError\nError code: 400\nProvider: openrouter\nModel rejected.",
            )
        return self._successful_live_executor(command, cwd)

    def _stdout_route_fallback_live_executor(self, command: list[str], cwd: Path) -> CommandExecutionResult:
        provider = command[command.index("--provider") + 1] if "--provider" in command else "default"
        if provider == "openrouter":
            return CommandExecutionResult(
                returncode=0,
                stdout=(
                    "AuthenticationError\n"
                    "Error code: 401\n"
                    "Provider: openrouter\n"
                    "Your API key is invalid, blocked or out of funds.\n"
                ),
                stderr="",
            )
        return self._successful_live_executor(command, cwd)

    def _accepted_refutation_live_executor(self, command: list[str], cwd: Path) -> CommandExecutionResult:
        del cwd
        query = command[command.index("-q") + 1]
        if "Role: generator" in query:
            payload = {
                "hypothesis": "A 5% circuit-level threshold claim for the surface code is not defensible under standard depolarizing assumptions.",
                "approach": "Refute the 5% claim directly with literature-backed threshold ranges.",
                "technical_details": ["Circuit-level MWPM thresholds remain well below 5%, in the sub-1% regime."],
                "expected_results": ["The verifier should accept the refutation as the correct handling of the benchmark."],
                "assumptions": ["Standard circuit-level depolarizing noise applies."],
                "limitations": ["This is a test executor response."],
                "references": ["Fowler et al. 2012", "Stephens 2014"],
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
                            "check": "benchmark_refutation",
                            "status": "pass",
                            "detail": "The candidate correctly rejects the unsupported 5% threshold claim.",
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

    def _simulation_tier1_only_executor(self, command: list[str], cwd: Path) -> CommandExecutionResult:
        del cwd
        query = command[command.index("-q") + 1]
        if "Role: generator" in query:
            payload = {
                "hypothesis": "At physical error rate 0.001, the logical error rate decreases from distance 3 to 5 to 7 in a rotated surface-code memory experiment.",
                "approach": "State the expected monotonic ordering directly.",
                "technical_details": [
                    "Use rotated surface-code memory with a depolarizing noise model and PyMatching decoding.",
                    "Compare logical error ordering across distances 3, 5, and 7.",
                ],
                "expected_results": ["The verifier should request Tier 2 to test the ordering empirically."],
                "assumptions": ["Standard rotated-memory Stim configuration applies."],
                "limitations": ["This executor intentionally withholds simulation results."],
                "references": ["Stim benchmark fixture"],
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
                            "check": "literature_plausibility",
                            "status": "pass",
                            "detail": "The ordering looks plausible under standard threshold intuition.",
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

    def _successful_codex_live_executor(self, command: list[str], cwd: Path) -> CommandExecutionResult:
        self.assertEqual(command[:2], ["codex", "exec"])
        self.assertIn("--output-schema", command)
        self.assertIn("--output-last-message", command)
        output_path = Path(command[command.index("--output-last-message") + 1])
        query = command[-1]
        self.assertEqual(cwd, output_path.parent)
        role = next(role_name for role_name in ("generator", "verifier", "reviser") if f"Role: {role_name}" in query)
        if role == "generator":
            if "-c" in command:
                self.assertIn('model_provider="openrouter"', command)
                self.assertIn("--model", command)
                self.assertIn("claude-sonnet-4", command)
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
        elif role == "verifier":
            if "-c" in command:
                self.assertIn('model_provider="openrouter"', command)
                self.assertIn("--model", command)
                self.assertIn("deepseek-r1", command)
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
        else:
            payload = {
                "hypothesis": "Revised hypothesis",
                "approach": "Revised approach",
                "technical_details": ["Revised technical detail."],
                "expected_results": ["Revised expected result."],
                "assumptions": ["Revised assumption."],
                "limitations": ["Revised limitation."],
                "references": ["Revised reference"],
                "revision_notes": ["Updated from verifier feedback."],
            }
        output_path.write_text(json.dumps(payload), encoding="utf-8")
        return CommandExecutionResult(returncode=0, stdout='{"event":"completed"}\n', stderr="")

    def _route_fallback_codex_live_executor(self, command: list[str], cwd: Path) -> CommandExecutionResult:
        provider = "default"
        if "-c" in command:
            provider_arg = command[command.index("-c") + 1]
            if provider_arg.startswith('model_provider="') and provider_arg.endswith('"'):
                provider = provider_arg[len('model_provider="') : -1]
        model = command[command.index("--model") + 1] if "--model" in command else "configured-by-codex"
        output_path = Path(command[command.index("--output-last-message") + 1])
        if provider == "openrouter" and model.startswith("broken-"):
            output_path.write_text("", encoding="utf-8")
            return CommandExecutionResult(
                returncode=1,
                stdout="",
                stderr="BadRequestError\nError code: 400\nProvider: openrouter\nModel rejected.",
            )
        return self._successful_codex_live_executor(command, cwd)

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

    def test_load_benchmark_suite_filters_categories(self) -> None:
        cases = load_benchmark_suite(
            ROOT / "eval" / "known_problems.json",
            categories=["formalizable"],
        )
        self.assertEqual(
            [item.id for item in cases],
            [
                "formal-proved-repetition-majority",
                "formal-unavailable-repetition-scaling",
                "formal-mathcode-nat-add-zero",
            ],
        )

    def test_load_benchmark_suite_filters_orchestration_category(self) -> None:
        cases = load_benchmark_suite(
            ROOT / "eval" / "known_problems.json",
            categories=["orchestration_required"],
        )
        self.assertEqual([item.id for item in cases], ["orchestration-fanout-threshold"])

    def test_load_benchmark_suite_filters_named_subset(self) -> None:
        cases = load_benchmark_suite(
            ROOT / "eval" / "known_problems.json",
            subset="live-expansion",
        )
        self.assertEqual(
            [item.id for item in cases],
            list(available_benchmark_subsets()["live-expansion"]),
        )

    def test_available_benchmark_subsets_expose_breadth_groups(self) -> None:
        subsets = available_benchmark_subsets()
        self.assertIn("core-science", subsets)
        self.assertIn("photonic-mbqc", subsets)
        self.assertIn("tier2-support", subsets)
        self.assertIn("tier3-support", subsets)
        self.assertIn("quantum-oss", subsets)
        self.assertIn("analysis-full", subsets)
        self.assertIn("live-analytical-breadth", subsets)
        self.assertIn("live-escalation-breadth", subsets)
        self.assertIn("live-full", subsets)
        self.assertEqual(
            subsets["core-science"],
            (
                "symbolic-verified-equivalence",
                "symbolic-rejected-derivative",
                "optimization-verified-linear-program",
                "optimization-rejected-assignment",
                "dynamics-verified-decay",
            ),
        )
        self.assertEqual(
            subsets["photonic-mbqc"],
            (
                "mbqc-verified-graphix-pattern",
                "photonic-verified-basic-state",
                "neutral-atom-verified-register",
            ),
        )
        self.assertEqual(
            subsets["tier2-support"],
            (
                "symbolic-verified-equivalence",
                "symbolic-rejected-derivative",
                "optimization-verified-linear-program",
                "optimization-rejected-assignment",
                "dynamics-verified-decay",
                "simulation-verified-distance5",
                "simulation-rejected-distance7",
                "mbqc-verified-graphix-pattern",
                "photonic-verified-basic-state",
                "neutral-atom-verified-register",
                "tqec-verified-gallery-block-graph",
                "zx-verified-qasm-rewrite",
            ),
        )
        self.assertEqual(
            subsets["tier3-support"],
            (
                "formal-proved-repetition-majority",
                "formal-unavailable-repetition-scaling",
                "formal-mathcode-nat-add-zero",
            ),
        )
        self.assertIn("zx-verified-qasm-rewrite", subsets["quantum-oss"])
        self.assertEqual(
            subsets["live-analytical-breadth"],
            (
                "known-correct-surface-threshold",
                "known-correct-planar-qubits",
                "known-correct-union-find",
                "known-incorrect-surface-threshold-5pct",
                "known-incorrect-color-codes-all-noise-models",
            ),
        )
        self.assertEqual(
            subsets["live-escalation-breadth"],
            (
                "simulation-verified-distance5",
                "simulation-rejected-distance7",
                "formal-proved-repetition-majority",
                "formal-unavailable-repetition-scaling",
            ),
        )
        self.assertEqual(
            subsets["live-full"],
            subsets["live-analytical-breadth"] + subsets["live-escalation-breadth"],
        )

    def test_load_benchmark_suite_filters_analytical_breadth_subset(self) -> None:
        cases = load_benchmark_suite(
            ROOT / "eval" / "known_problems.json",
            subset="live-analytical-breadth",
        )
        self.assertEqual(
            [item.id for item in cases],
            list(available_benchmark_subsets()["live-analytical-breadth"]),
        )

    def test_load_benchmark_suite_filters_core_science_subset(self) -> None:
        cases = load_benchmark_suite(
            ROOT / "eval" / "known_problems.json",
            subset="core-science",
        )
        self.assertEqual(
            [item.id for item in cases],
            list(available_benchmark_subsets()["core-science"]),
        )

    def test_load_benchmark_suite_filters_tier2_support_subset(self) -> None:
        cases = load_benchmark_suite(
            ROOT / "eval" / "known_problems.json",
            subset="tier2-support",
        )
        self.assertEqual(
            [item.id for item in cases],
            list(available_benchmark_subsets()["tier2-support"]),
        )

    def test_load_benchmark_suite_filters_tier3_support_subset(self) -> None:
        cases = load_benchmark_suite(
            ROOT / "eval" / "known_problems.json",
            subset="tier3-support",
        )
        self.assertEqual(
            [item.id for item in cases],
            list(available_benchmark_subsets()["tier3-support"]),
        )

    def test_load_benchmark_suite_filters_escalation_breadth_subset(self) -> None:
        cases = load_benchmark_suite(
            ROOT / "eval" / "known_problems.json",
            subset="live-escalation-breadth",
        )
        self.assertEqual(
            [item.id for item in cases],
            list(available_benchmark_subsets()["live-escalation-breadth"]),
        )

    def test_load_benchmark_suite_rejects_unknown_subset(self) -> None:
        with self.assertRaises(ValueError):
            load_benchmark_suite(ROOT / "eval" / "known_problems.json", subset="missing-subset")

    def test_accept_verified_refutation_for_known_incorrect_case(self) -> None:
        case = load_benchmark_suite(
            ROOT / "eval" / "known_problems.json",
            case_ids=["known-incorrect-surface-threshold-5pct"],
        )[0]
        candidate = CandidateSolution(
            hypothesis="The claim that the circuit-level threshold is 5% is not defensible; the literature keeps it in the sub-1% regime.",
            approach="Reject the claim on literature grounds instead of fabricating support for it.",
            technical_details=["The circuit-level threshold remains well below 5% under standard depolarizing noise."],
            expected_results=["The verifier should accept the refutation as a correct rejection of the benchmark claim."],
            assumptions=["Standard circuit-level depolarizing assumptions apply."],
            limitations=["This is a benchmark refutation candidate."],
            references=["Fowler et al. 2012", "Stephens 2014"],
            revision_notes=[],
        )

        self.assertTrue(_accept_verified_refutation(case, VerificationVerdict.VERIFIED, candidate))

    def test_accept_verified_refutation_for_known_incorrect_case_with_conservative_range_language(self) -> None:
        case = load_benchmark_suite(
            ROOT / "eval" / "known_problems.json",
            case_ids=["known-incorrect-surface-threshold-5pct"],
        )[0]
        candidate = CandidateSolution(
            hypothesis=(
                "The claim that the circuit-level threshold is 5% is false; the established circuit-level threshold "
                "is in the ~0.6-0.8% range, roughly an order of magnitude lower."
            ),
            approach="Reject the claim on literature grounds instead of fabricating support for it.",
            technical_details=["The circuit-level threshold remains well below 1% under standard depolarizing noise."],
            expected_results=["The verifier should accept the refutation as a correct rejection of the benchmark claim."],
            assumptions=["Standard circuit-level depolarizing assumptions apply."],
            limitations=["This is a benchmark refutation candidate."],
            references=["Fowler et al. 2012", "Stephens 2014"],
            revision_notes=[],
        )

        self.assertTrue(_accept_verified_refutation(case, VerificationVerdict.VERIFIED, candidate))

    def test_accept_verified_refutation_for_simulation_rejected_case(self) -> None:
        case = load_benchmark_suite(
            ROOT / "eval" / "known_problems.json",
            case_ids=["simulation-rejected-distance7"],
        )[0]
        candidate = CandidateSolution(
            hypothesis=(
                "The claim is false: a distance 7 rotated surface code at p=0.005 does not achieve a logical error rate "
                "below 1e-4 under standard MWPM decoding."
            ),
            approach="Reject the target by comparing it against the simulation-backed logical error rate.",
            technical_details=["At p=0.005 the logical error rate remains well above 1e-4 at d=7."],
            expected_results=["Tier 2 should confirm the direct refutation of the 1e-4 claim."],
            assumptions=["Standard circuit-level depolarizing assumptions apply."],
            limitations=["This is a benchmark refutation candidate."],
            references=["Fowler et al. 2012", "Stephens 2014"],
            revision_notes=[],
        )

        self.assertTrue(_accept_verified_refutation(case, VerificationVerdict.VERIFIED, candidate))

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
        self.assertEqual(report.summary.direct_match_cases, len(report.cases))
        self.assertEqual(report.summary.accepted_refutation_cases, 0)
        self.assertTrue(report.summary.meets_false_positive_bar)

    def test_run_benchmark_suite_handles_orchestration_case(self) -> None:
        report = run_benchmark_suite(
            ROOT / "eval" / "known_problems.json",
            routing_probe=benchmark_routing_probe(ProbeStatus.FALLBACK),
            case_ids=["orchestration-fanout-threshold"],
        )

        self.assertEqual(report.summary.total_cases, 1)
        case = report.cases[0]
        self.assertTrue(case.passed)
        self.assertEqual(case.actual_verdict, VerificationVerdict.VERIFIED)
        self.assertEqual(case.actual_tiers, [1])
        self.assertEqual(case.iterations, 3)

    def test_run_benchmark_suite_handles_mathcode_formal_case(self) -> None:
        report = run_benchmark_suite(
            ROOT / "eval" / "known_problems.json",
            routing_probe=benchmark_routing_probe(ProbeStatus.FALLBACK),
            case_ids=["formal-mathcode-nat-add-zero"],
        )

        self.assertEqual(report.summary.total_cases, 1)
        case = report.cases[0]
        self.assertTrue(case.passed)
        self.assertEqual(case.actual_verdict, VerificationVerdict.VERIFIED)
        self.assertEqual(case.actual_tiers, [1, 3])

    def test_run_benchmark_suite_matches_expected_baseline_for_tier2_support_subset(self) -> None:
        report = run_benchmark_suite(
            ROOT / "eval" / "known_problems.json",
            routing_probe=benchmark_routing_probe(ProbeStatus.FALLBACK),
            subset="tier2-support",
        )

        self.assertEqual(report.summary.total_cases, len(available_benchmark_subsets()["tier2-support"]))
        self.assertEqual(report.summary.failed_cases, 0)
        self.assertEqual(report.summary.false_positive_rate, 0.0)

    def test_run_benchmark_suite_matches_expected_baseline_for_tier3_support_subset(self) -> None:
        report = run_benchmark_suite(
            ROOT / "eval" / "known_problems.json",
            routing_probe=benchmark_routing_probe(ProbeStatus.FALLBACK),
            subset="tier3-support",
        )

        self.assertEqual(report.summary.total_cases, len(available_benchmark_subsets()["tier3-support"]))
        self.assertEqual(report.summary.failed_cases, 0)
        self.assertEqual(report.summary.false_positive_rate, 0.0)

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

    def test_eval_cli_lists_named_subsets(self) -> None:
        completed = subprocess.run(
            [
                "python3",
                str(ROOT / "eval" / "run_eval.py"),
                "--list-subsets",
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Available benchmark subsets:", completed.stdout)
        self.assertIn("live-analytical-breadth", completed.stdout)
        self.assertIn("live-escalation-breadth", completed.stdout)
        self.assertIn("live-expansion", completed.stdout)
        self.assertIn("live-full", completed.stdout)
        self.assertIn("formal-proved-repetition-majority", completed.stdout)

    def test_eval_cli_prints_case_summary_for_named_subset(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.json"
            completed = subprocess.run(
                [
                    "python3",
                    str(ROOT / "eval" / "run_eval.py"),
                    "--subset",
                    "live-expansion",
                    "--output",
                    str(output_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("Case results:", completed.stdout)
            self.assertIn(
                "PASS known-incorrect-surface-threshold-5pct [known_incorrect] outcome=direct_match expected=FLAWS_FOUND actual=FLAWS_FOUND",
                completed.stdout,
            )
            self.assertIn(
                "PASS formal-proved-repetition-majority [formalizable] outcome=direct_match expected=VERIFIED actual=VERIFIED",
                completed.stdout,
            )

    def test_eval_cli_repeat_writes_consistency_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_root = Path(tmpdir) / "repeat-results"
            completed = subprocess.run(
                [
                    "python3",
                    str(ROOT / "eval" / "run_eval.py"),
                    "--subset",
                    "live-expansion",
                    "--repeat",
                    "2",
                    "--output-root",
                    str(output_root),
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("Consistency summary:", completed.stdout)
            self.assertIn("Case stability:", completed.stdout)
            payload = json.loads((output_root / "consistency_report.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["repeat_count"], 2)
            self.assertEqual(payload["summary"]["unstable_cases"], 0)
            self.assertEqual(len(payload["runs"]), 2)
            self.assertTrue((output_root / "runs" / "run-001" / "report.json").exists())

    def test_repeated_suite_tracks_case_level_stability(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_repeated_benchmark_suite(
                ROOT / "eval" / "known_problems.json",
                repeat_count=2,
                routing_probe=benchmark_routing_probe(ProbeStatus.FALLBACK),
                mode="deterministic",
                subset="live-expansion",
                output_root=Path(tmpdir) / "repeat-results",
            )

            self.assertEqual(report.summary.repeat_count, 2)
            self.assertEqual(report.summary.fully_passing_runs, 2)
            self.assertEqual(report.summary.unstable_cases, 0)
            self.assertEqual(len(report.cases), 3)
            lines = format_benchmark_consistency_overview(report)
            self.assertTrue(any(line.startswith("STABLE known-incorrect-surface-threshold-5pct") for line in lines))

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
            self.assertEqual(report.runner_backend, "hermes_prompt_harness")
            self.assertEqual(report.summary.total_cases, 1)
            self.assertEqual(report.summary.failed_cases, 0)
            case = report.cases[0]
            self.assertTrue(case.passed)
            self.assertEqual(case.actual_verdict, VerificationVerdict.VERIFIED)
            self.assertTrue(case.strict_verdict_match)
            self.assertTrue(case.verdict_accepted)
            self.assertTrue(case.tiers_matched_expected)
            self.assertEqual(case.outcome, "direct_match")
            self.assertIsNone(case.error)
            self.assertGreaterEqual(case.runtime_seconds, 0.0)
            self.assertTrue(any("Injected" in note or "temperature overrides" in note for note in case.notes))
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
            self.assertIn("--toolsets", transcripts["calls"][0]["command"])
            self.assertIn("clarify", transcripts["calls"][0]["command"])

    def test_live_mode_records_artifacts_and_metadata_for_codex_backend(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_root = Path(tmpdir) / "live-results"
            config_path = Path(tmpdir) / "config.yaml"
            evidence_dir = Path(tmpdir) / "configured-sessions"
            self._write_config(
                config_path,
                evidence_dir,
                orchestrator_backend="codex_local",
            )

            report = run_benchmark_suite(
                ROOT / "eval" / "known_problems.json",
                routing_probe=benchmark_routing_probe(ProbeStatus.FALLBACK),
                mode="live",
                config_path=config_path,
                output_root=output_root,
                case_ids=["known-correct-surface-threshold"],
                live_config=LiveEvalConfig(),
                executor=self._successful_codex_live_executor,
            )

            self.assertEqual(report.mode, "live")
            self.assertEqual(report.runner_backend, "codex_native_role_harness")
            case = report.cases[0]
            self.assertTrue(case.passed)
            self.assertEqual(case.provider, "openrouter")
            self.assertEqual(case.model_used, "deepseek-r1")
            transcripts = json.loads(
                (output_root / "cases" / case.id / "role_transcripts.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(transcripts["calls"]), 2)
            self.assertTrue(all(call["backend"] == "codex_local" for call in transcripts["calls"]))
            self.assertTrue(all("codex" in call["command"][0] for call in transcripts["calls"]))
            self.assertTrue(all("--output-last-message" in call["command"] for call in transcripts["calls"]))
            self.assertEqual(transcripts["calls"][0]["selected_route"]["model"], "claude-sonnet-4")
            self.assertEqual(transcripts["calls"][1]["selected_route"]["model"], "deepseek-r1")
            self.assertIn("response_object", transcripts["calls"][0])
            self.assertIn("response_object", transcripts["calls"][1])

    def test_live_mode_codex_backend_falls_back_from_invalid_explicit_role_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_root = Path(tmpdir) / "live-results"
            config_path = Path(tmpdir) / "config.yaml"
            evidence_dir = Path(tmpdir) / "configured-sessions"
            self._write_config(
                config_path,
                evidence_dir,
                orchestrator_backend="codex_local",
                provider="default",
                model="",
                generator_provider="openrouter",
                generator_model="broken-generator",
                verifier_provider="openrouter",
                verifier_model="broken-verifier",
            )

            report = run_benchmark_suite(
                ROOT / "eval" / "known_problems.json",
                routing_probe=benchmark_routing_probe(ProbeStatus.FALLBACK),
                mode="live",
                config_path=config_path,
                output_root=output_root,
                case_ids=["known-correct-surface-threshold"],
                live_config=LiveEvalConfig(),
                executor=self._route_fallback_codex_live_executor,
            )

            case = report.cases[0]
            self.assertTrue(case.passed)
            self.assertEqual(case.provider, "default")
            self.assertEqual(case.model_used, "configured-by-codex")
            transcripts = json.loads(
                (output_root / "cases" / case.id / "role_transcripts.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(transcripts["calls"]), 4)
            self.assertIn("broken-generator", transcripts["calls"][0]["command"])
            self.assertNotIn("-c", transcripts["calls"][1]["command"])
            self.assertIn("broken-verifier", transcripts["calls"][2]["command"])
            self.assertNotIn("-c", transcripts["calls"][3]["command"])
            evidence_log = Path(next(path for path in case.artifacts if path.endswith(".jsonl")))
            evidence_records = [json.loads(line) for line in evidence_log.read_text(encoding="utf-8").splitlines()]
            verify_record = next(record for record in evidence_records if record["phase"] == "verify")
            self.assertEqual(verify_record["provider"], "default")
            self.assertEqual(verify_record["model_used"], "configured-by-codex")
            self.assertTrue(
                any("fell back from openrouter/broken-verifier" in note.lower() for note in verify_record["routing_notes"])
            )

    def test_format_benchmark_report_overview_includes_case_root_and_note(self) -> None:
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

            lines = format_benchmark_report_overview(report)
            self.assertTrue(
                any(line.startswith("PASS known-correct-surface-threshold [known_correct] outcome=direct_match") for line in lines)
            )
            self.assertTrue(any("Injected" in line or "temperature overrides" in line for line in lines))
            self.assertTrue(any(str(output_root / "cases" / "known-correct-surface-threshold") in line for line in lines))

    def test_live_mode_accepted_refutation_counts_as_pass_without_false_positive(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_root = Path(tmpdir) / "live-results"
            report = run_benchmark_suite(
                ROOT / "eval" / "known_problems.json",
                routing_probe=benchmark_routing_probe(ProbeStatus.FALLBACK),
                mode="live",
                output_root=output_root,
                case_ids=["known-incorrect-surface-threshold-5pct"],
                live_config=LiveEvalConfig(),
                executor=self._accepted_refutation_live_executor,
            )

            case = report.cases[0]
            self.assertTrue(case.passed)
            self.assertFalse(case.strict_verdict_match)
            self.assertTrue(case.verdict_accepted)
            self.assertTrue(case.accepted_refutation)
            self.assertEqual(case.outcome, "accepted_refutation")
            self.assertEqual(report.summary.accepted_refutation_cases, 1)
            self.assertEqual(report.summary.false_positive_rate, 0.0)
            lines = format_benchmark_report_overview(report)
            self.assertTrue(any("outcome=accepted_refutation" in line for line in lines))

    def test_live_mode_records_tier_mismatch_for_simulation_case_without_tier2(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_root = Path(tmpdir) / "live-results"
            report = run_benchmark_suite(
                ROOT / "eval" / "known_problems.json",
                routing_probe=benchmark_routing_probe(ProbeStatus.FALLBACK),
                mode="live",
                output_root=output_root,
                case_ids=["simulation-verified-distance5"],
                live_config=LiveEvalConfig(),
                executor=self._simulation_tier1_only_executor,
            )

            case = report.cases[0]
            self.assertFalse(case.passed)
            self.assertTrue(case.strict_verdict_match)
            self.assertTrue(case.verdict_accepted)
            self.assertFalse(case.tiers_matched_expected)
            self.assertEqual(case.outcome, "tier_mismatch")
            self.assertEqual(report.summary.tier_mismatch_failures, 1)
            self.assertEqual(report.summary.verdict_match_rate, 1.0)
            lines = format_benchmark_report_overview(report)
            self.assertTrue(any("outcome=tier_mismatch" in line for line in lines))

    def test_live_mode_explicit_toolsets_override_restricted_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_root = Path(tmpdir) / "live-results"
            report = run_benchmark_suite(
                ROOT / "eval" / "known_problems.json",
                routing_probe=benchmark_routing_probe(ProbeStatus.FALLBACK),
                mode="live",
                output_root=output_root,
                case_ids=["known-correct-surface-threshold"],
                live_config=LiveEvalConfig(toolsets=["search"]),
                executor=self._successful_live_executor,
            )

            case = report.cases[0]
            self.assertTrue(case.passed)
            transcripts = json.loads(
                (output_root / "cases" / case.id / "role_transcripts.json").read_text(encoding="utf-8")
            )
            self.assertIn("--toolsets", transcripts["calls"][0]["command"])
            self.assertIn("search", transcripts["calls"][0]["command"])
            self.assertNotIn("clarify", transcripts["calls"][0]["command"])

    def test_live_mode_injects_shared_qec_domain_context(self) -> None:
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

            case = report.cases[0]
            self.assertTrue(case.passed)
            self.assertTrue(any("Injected" in note for note in case.notes))
            transcripts = json.loads(
                (output_root / "cases" / case.id / "role_transcripts.json").read_text(encoding="utf-8")
            )
            self.assertIn(
                "Surface-code threshold under standard depolarizing assumptions is commonly reported around the sub-1% regime",
                transcripts["calls"][0]["query"],
            )
            self.assertIn(
                "the familiar ~10.3% number is tied to independent X/Z decoding under code-capacity depolarizing assumptions",
                transcripts["calls"][0]["query"],
            )
            self.assertIn(
                "reserve it for the higher ~10.9% maximum-likelihood bit-flip threshold",
                transcripts["calls"][0]["query"],
            )
            self.assertIn(
                "If a work is named in the body, list it in `references`",
                transcripts["calls"][0]["query"],
            )
            self.assertIn(
                "Do not attribute the surface-code threshold directly to the generic concatenated-code threshold theorem",
                transcripts["calls"][0]["query"],
            )
            self.assertIn(
                "For standard depolarizing surface-code threshold questions, prefer the sub-1% circuit-level regime as the main claim",
                transcripts["calls"][0]["query"],
            )
            self.assertIn(
                "Wang, Fowler, and Hollenberg",
                transcripts["calls"][0]["query"],
            )
            self.assertIn(
                "Physical Review A 83(2) from 2011",
                transcripts["calls"][0]["query"],
            )
            self.assertIn(
                "Prefer Fowler et al. (2012) or Stephens (2014) for the familiar sub-1% circuit-level MWPM threshold range",
                transcripts["calls"][0]["query"],
            )

    def test_live_mode_uses_custom_domain_context_file_from_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_root = Path(tmpdir) / "live-results"
            config_path = Path(tmpdir) / "config.yaml"
            evidence_dir = Path(tmpdir) / "configured-sessions"
            context_file = Path(tmpdir) / "custom_context.md"
            context_file.write_text(
                "# Custom Context\n\n- Custom benchmark anchor for the live eval test.\n",
                encoding="utf-8",
            )
            self._write_config(
                config_path,
                evidence_dir,
                context_file=str(context_file),
            )

            report = run_benchmark_suite(
                ROOT / "eval" / "known_problems.json",
                routing_probe=benchmark_routing_probe(ProbeStatus.FALLBACK),
                mode="live",
                config_path=config_path,
                output_root=output_root,
                case_ids=["known-correct-surface-threshold"],
                live_config=LiveEvalConfig(),
                executor=self._successful_live_executor,
            )

            case = report.cases[0]
            self.assertTrue(case.passed)
            transcripts = json.loads(
                (output_root / "cases" / case.id / "role_transcripts.json").read_text(encoding="utf-8")
            )
            self.assertIn("Custom benchmark anchor for the live eval test.", transcripts["calls"][0]["query"])

    def test_live_mode_uses_configured_orchestrator_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_root = Path(tmpdir) / "live-results"
            config_path = Path(tmpdir) / "config.yaml"
            evidence_dir = Path(tmpdir) / "configured-sessions"
            self._write_config(
                config_path,
                evidence_dir,
                provider="openai",
                model="gpt-5.4-mini",
                generator_provider="default",
                verifier_provider="default",
                reviser_provider="default",
            )
            configured = load_runtime_config(config_path)

            report = run_benchmark_suite(
                ROOT / "eval" / "known_problems.json",
                routing_probe=benchmark_routing_probe(ProbeStatus.FALLBACK),
                mode="live",
                config_path=config_path,
                output_root=output_root,
                case_ids=["known-correct-surface-threshold"],
                live_config=LiveEvalConfig(),
                executor=self._successful_live_executor,
            )

            case = report.cases[0]
            self.assertTrue(case.passed)
            self.assertEqual(case.provider, "openai")
            self.assertEqual(case.model_used, "gpt-5.4-mini")
            self.assertEqual(configured.models.orchestrator.provider, "openai")
            transcripts = json.loads(
                (output_root / "cases" / case.id / "role_transcripts.json").read_text(encoding="utf-8")
            )
            command = transcripts["calls"][0]["command"]
            self.assertIn("--provider", command)
            self.assertIn("--model", command)
            self.assertIn("openai", command)
            self.assertIn("gpt-5.4-mini", command)

    def test_live_mode_falls_back_from_invalid_explicit_role_route_and_records_actual_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_root = Path(tmpdir) / "live-results"
            config_path = Path(tmpdir) / "config.yaml"
            evidence_dir = Path(tmpdir) / "configured-sessions"
            self._write_config(
                config_path,
                evidence_dir,
                provider="default",
                model="",
                generator_provider="openrouter",
                generator_model="broken-generator",
                verifier_provider="openrouter",
                verifier_model="broken-verifier",
            )

            report = run_benchmark_suite(
                ROOT / "eval" / "known_problems.json",
                routing_probe=benchmark_routing_probe(ProbeStatus.FALLBACK),
                mode="live",
                config_path=config_path,
                output_root=output_root,
                case_ids=["known-correct-surface-threshold"],
                live_config=LiveEvalConfig(),
                executor=self._route_fallback_live_executor,
            )

            case = report.cases[0]
            self.assertTrue(case.passed)
            self.assertEqual(case.provider, "default")
            self.assertEqual(case.model_used, "configured-by-hermes")
            transcripts = json.loads(
                (output_root / "cases" / case.id / "role_transcripts.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(transcripts["calls"]), 4)
            self.assertIn("broken-generator", transcripts["calls"][0]["command"])
            self.assertNotIn("--provider", transcripts["calls"][1]["command"])
            self.assertIn("broken-verifier", transcripts["calls"][2]["command"])
            self.assertNotIn("--provider", transcripts["calls"][3]["command"])
            evidence_log = Path(next(path for path in case.artifacts if path.endswith(".jsonl")))
            evidence_records = [json.loads(line) for line in evidence_log.read_text(encoding="utf-8").splitlines()]
            verify_record = next(record for record in evidence_records if record["phase"] == "verify")
            self.assertEqual(verify_record["provider"], "default")
            self.assertEqual(verify_record["model_used"], "configured-by-hermes")
            self.assertTrue(
                any("fell back from openrouter/broken-verifier" in note.lower() for note in verify_record["routing_notes"])
            )

    def test_live_mode_falls_back_from_provider_only_route_when_hermes_emits_auth_error_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_root = Path(tmpdir) / "live-results"
            config_path = Path(tmpdir) / "config.yaml"
            evidence_dir = Path(tmpdir) / "configured-sessions"
            self._write_config(
                config_path,
                evidence_dir,
                provider="default",
                model="",
                generator_provider="openrouter",
                verifier_provider="openrouter",
            )

            report = run_benchmark_suite(
                ROOT / "eval" / "known_problems.json",
                routing_probe=benchmark_routing_probe(ProbeStatus.FALLBACK),
                mode="live",
                config_path=config_path,
                output_root=output_root,
                case_ids=["known-correct-surface-threshold"],
                live_config=LiveEvalConfig(),
                executor=self._stdout_route_fallback_live_executor,
            )

            case = report.cases[0]
            self.assertTrue(case.passed)
            self.assertEqual(case.provider, "default")
            self.assertEqual(case.model_used, "configured-by-hermes")
            transcripts = json.loads(
                (output_root / "cases" / case.id / "role_transcripts.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(transcripts["calls"]), 4)
            self.assertIn("openrouter", transcripts["calls"][0]["command"])
            self.assertIn("claude-sonnet-4", transcripts["calls"][0]["command"])
            self.assertNotIn("--provider", transcripts["calls"][1]["command"])
            self.assertIn("openrouter", transcripts["calls"][2]["command"])
            self.assertIn("deepseek-r1", transcripts["calls"][2]["command"])
            self.assertNotIn("--provider", transcripts["calls"][3]["command"])
            evidence_log = Path(next(path for path in case.artifacts if path.endswith(".jsonl")))
            evidence_records = [json.loads(line) for line in evidence_log.read_text(encoding="utf-8").splitlines()]
            verify_record = next(record for record in evidence_records if record["phase"] == "verify")
            self.assertTrue(
                any("fell back from openrouter/deepseek-r1" in note.lower() for note in verify_record["routing_notes"])
            )

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
        self.assertIn(
            "If you invoke the 2D RBIM or Nishimori-point mapping, reserve it for the higher ~10.9% maximum-likelihood bit-flip threshold",
            compact_query,
        )
        self.assertIn(
            "If a citation is not important enough to list in `references`, do not name it in the body.",
            compact_query,
        )
        self.assertIn(
            "Do not say the surface-code threshold follows directly from the generic fault-tolerance threshold theorem",
            compact_query,
        )
        self.assertIn(
            "For a standard depolarizing surface-code threshold question, keep the main claim on the depolarizing surface-code threshold",
            compact_query,
        )
        self.assertIn(
            "If you are unsure of a bibliographic year, omit the year rather than invent one that conflicts with the journal or volume.",
            compact_query,
        )
        self.assertIn(
            "Prefer Fowler et al. (2012) or Stephens (2014) for the sub-1% circuit-level MWPM range",
            compact_query,
        )
        self.assertIn(
            "For Tier-2-driven quantitative claims, prefer the smallest falsifiable prediction the selected analysis adapter can actually check",
            compact_query,
        )
        self.assertIn(
            "Do not strengthen the core claim into harder-to-verify quantitative subclaims unless the prompt asks for them",
            compact_query,
        )
        self.assertIn(
            "keep the hypothesis literature-backed and scoped to threshold existence or cited threshold regimes",
            compact_query,
        )
        self.assertIn(
            "For literature-grounded threshold-understanding questions, keep `expected_results` on threshold existence, regime separation, or cited threshold ranges",
            compact_query,
        )
        self.assertIn(
            "For pure counting or asymptotic cost questions, prefer one asymptotic statement plus at most one concrete formula or worked example",
            compact_query,
        )
        self.assertIn(
            "For algorithmic scaling questions, keep the candidate on the asymptotic decode complexity the prompt actually asks for",
            compact_query,
        )
        self.assertIn(
            "For compact theorem or asymptotic proof claims, keep `expected_results` on the proof statement or derived asymptotic consequence",
            compact_query,
        )
        self.assertIn(
            "For small-distance analysis-backed claims, keep the hypothesis on the ordering the prompt actually asks for",
            compact_query,
        )
        self.assertIn(
            "In `expected_results`, prefer direct checks over ratio targets or fit-quality claims",
            compact_query,
        )
        self.assertIn(
            "keep `expected_results` scoped to the exact basis, decoder, and noise-model configuration actually under discussion",
            compact_query,
        )
        self.assertIn(
            "prefer the generic label `standard circuit-level depolarizing noise`",
            compact_query,
        )
        self.assertIn(
            "When refuting a known-false claim, keep `expected_results` to the minimal literature-backed consequences",
            compact_query,
        )
        self.assertIn(
            "keep the whole candidate short: one central contradiction",
            compact_query,
        )
        self.assertIn(
            "Do not include CLI/runtime execution limitations in the scientific candidate",
            compact_query,
        )
        self.assertIn(
            "prefer a conservative literature range like `~0.6-0.8%`",
            compact_query,
        )
        self.assertLess(len(compact_query), len(full_query))

    def test_verifier_uses_timeout_floor_with_default_executor(self) -> None:
        runner = HermesPromptRoleRunner(
            LiveEvalConfig(command_timeout_seconds=5),
            prompt_root=ROOT / "prompts",
        )
        request = VerificationRequest(
            session_id="session_eval",
            iteration=1,
            candidate=CandidateSolution(
                hypothesis="Hypothesis",
                approach="Approach",
                technical_details=["Detail"],
                expected_results=["Result"],
                assumptions=["Assumption"],
                limitations=["Limitation"],
                references=["Reference"],
            ),
            route=EffectiveModelRoute(provider="default", model="configured-by-hermes"),
        )
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

        with patch(
            "deep_gvr.evaluation._default_executor",
            return_value=CommandExecutionResult(returncode=0, stdout=json.dumps(payload), stderr=""),
        ) as mocked_executor:
            report = runner.verifier(request)

        self.assertEqual(report.verdict, VerificationVerdict.VERIFIED)
        self.assertEqual(mocked_executor.call_args.args[2], 150)

    def test_verifier_with_analysis_results_uses_followup_timeout_floor(self) -> None:
        runner = HermesPromptRoleRunner(
            LiveEvalConfig(command_timeout_seconds=5),
            prompt_root=ROOT / "prompts",
        )
        request = VerificationRequest(
            session_id="session_eval",
            iteration=1,
            candidate=CandidateSolution(
                hypothesis="Hypothesis",
                approach="Approach",
                technical_details=["Detail"],
                expected_results=["Result"],
                assumptions=["Assumption"],
                limitations=["Limitation"],
                references=["Reference"],
            ),
            route=EffectiveModelRoute(provider="default", model="configured-by-hermes"),
            analysis_results=AnalysisResults(
                adapter_family="qec_decoder_benchmark",
                analysis_kind="rotated_surface_code_memory",
                adapter_name="qec_decoder_benchmark",
                adapter_version="0.1.0",
                timestamp="2026-03-27T00:00:00Z",
                runtime_seconds=0.1,
                backend=Backend.LOCAL,
                summary="Follow-up QEC analysis results are attached.",
                measurements=[
                    AnalysisMeasurement(
                        name="threshold_estimate",
                        value=0.001,
                        unit="",
                        metadata={"method": "monotonic_distance_improvement"},
                    )
                ],
                details={},
                errors=[],
            ),
        )
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

        with patch(
            "deep_gvr.evaluation._default_executor",
            return_value=CommandExecutionResult(returncode=0, stdout=json.dumps(payload), stderr=""),
        ) as mocked_executor:
            report = runner.verifier(request)

        self.assertEqual(report.verdict, VerificationVerdict.VERIFIED)
        self.assertEqual(mocked_executor.call_args.args[2], 180)

    def test_compact_verifier_query_is_shorter_than_generic_compact_form(self) -> None:
        runner = HermesPromptRoleRunner(
            LiveEvalConfig(prompt_profile="compact"),
            prompt_root=ROOT / "prompts",
        )
        payload = {
            "session_id": "session_eval",
            "iteration": 1,
            "candidate": {
                "hypothesis": "The planar surface code has a threshold under standard depolarizing noise assumptions.",
                "approach": "Explain the literature-backed threshold claim with decoder and noise-model qualifiers.",
                "technical_details": [
                    "Code-capacity thresholds are around ten percent.",
                    "Phenomenological thresholds are in the low single-digit percent range.",
                    "Circuit-level thresholds are in the sub-one-percent range.",
                ],
                "expected_results": [
                    "Below threshold the logical error rate decreases with distance.",
                    "At threshold the distance curves cross.",
                ],
                "assumptions": ["Independent depolarizing noise.", "Global decoder access to syndrome history."],
                "limitations": ["Threshold values are decoder-dependent."],
                "references": ["Dennis et al. 2002", "Fowler et al. 2012"],
                "revision_notes": ["Numbers are paired with noise-model qualifiers."],
            },
            "analysis_results": None,
            "formal_results": None,
        }
        route_notes = ["Use prompt separation plus temperature decorrelation and record the limitation."]
        generic_prompt = (ROOT / "prompts" / "verifier.md").read_text(encoding="utf-8")
        compact_prompt = (ROOT / "prompts" / "verifier_compact.md").read_text(encoding="utf-8")
        response_contract = {
            "verdict": "VERIFIED | FLAWS_FOUND | CANNOT_VERIFY",
            "tier1": {
                "checks": [{"check": "string", "status": "pass|fail|uncertain", "detail": "string"}],
                "overall": "VERIFIED | FLAWS_FOUND | CANNOT_VERIFY",
                "flaws": ["string"],
                "caveats": ["string"],
            },
            "tier2": {
                "analysis_requested": "boolean",
                "reason": "string",
                "analysis_spec": "object | null",
                "results": "object | null",
                "interpretation": "string | null",
            },
            "tier3": [
                {
                    "claim": "string",
                    "backend": "string",
                    "proof_status": "requested|pending|proved|disproved|timeout|error|unavailable",
                    "details": "string",
                    "lean_code": "string",
                    "proof_time_seconds": "number | null",
                }
            ],
            "flaws": ["string"],
            "caveats": ["string"],
            "cannot_verify_reason": "string | null",
        }

        verifier_query = runner._build_query(
            role="verifier",
            prompt_text=compact_prompt,
            payload=payload,
            response_contract=response_contract,
            route_notes=route_notes,
            route_temperature=0.1,
        )
        generic_query = _build_compact_generic_query(
            role="verifier",
            prompt_text=generic_prompt,
            payload=payload,
            response_contract=response_contract,
            route_lines=[
                "role=verifier",
                *route_notes,
                "Temperature fallback is recorded only; Hermes CLI cannot enforce it.",
            ],
            profile="compact",
        )

        self.assertIn("prompts/verifier_compact.md", str(runner._resolve_prompt_path("verifier", "verifier.md")))
        self.assertLess(len(verifier_query), len(generic_query))
        self.assertNotIn("revision_notes", verifier_query)
        self.assertIn('"tier3":[]', verifier_query)
        self.assertIn(
            "For literature-grounded threshold explanations that only restate established threshold existence, regime separation, or cited threshold ranges",
            verifier_query,
        )
        self.assertIn(
            "For pure counting or asymptotic scaling claims, keep the audit short and Tier 1",
            verifier_query,
        )
        self.assertIn(
            "emit the normalized repo-local `analysis_spec`, use the canonical Stim noise-model string `depolarizing`",
            verifier_query,
        )
        self.assertIn("shots_per_point <= 100000", verifier_query)
        self.assertIn("max_parallel <= 4", verifier_query)
        self.assertIn(
            "Keep known-false literature-grounded contradictions at Tier 1 unless simulation is genuinely required to resolve the core contradiction",
            verifier_query,
        )
        self.assertIn(
            "treat auxiliary scope drift or over-detailed noise-model wording as caveats",
            verifier_query,
        )
        self.assertIn("Use Tier 3 for compact formal theorem claims or discrete proof obligations", verifier_query)
        self.assertIn(
            "For compact theorem or asymptotic proof claims, do not request Tier 2 just because the candidate lists testable asymptotic consequences",
            verifier_query,
        )
        self.assertIn(
            "If the core theorem claim has attached Tier 3 results with status `pending`, `error`, `timeout`, or `unavailable`, return `CANNOT_VERIFY`",
            verifier_query,
        )

    def test_live_mode_does_not_clip_formal_transport_to_live_role_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_root = Path(tmpdir) / "live-results"
            with patch("deep_gvr.evaluation.build_formal_verifier") as verifier_ctor:
                verifier_ctor.return_value = object()
                report = run_benchmark_suite(
                    ROOT / "eval" / "known_problems.json",
                    routing_probe=benchmark_routing_probe(ProbeStatus.FALLBACK),
                    mode="live",
                    output_root=output_root,
                    case_ids=["known-correct-surface-threshold"],
                    live_config=LiveEvalConfig(command_timeout_seconds=5),
                    executor=self._successful_live_executor,
                )

        self.assertTrue(report.cases[0].passed)
        self.assertNotIn("command_timeout_seconds", verifier_ctor.call_args.kwargs)

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
