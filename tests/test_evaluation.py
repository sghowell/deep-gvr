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
from deep_gvr.contracts import CandidateSolution, DeepGvrConfig, ProbeStatus, VerificationVerdict
from deep_gvr.evaluation import (
    CommandExecutionResult,
    HermesPromptRoleRunner,
    LiveEvalConfig,
    benchmark_routing_probe,
    load_benchmark_suite,
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
            self.assertIn("--toolsets", transcripts["calls"][0]["command"])
            self.assertIn("clarify", transcripts["calls"][0]["command"])

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
        self.assertEqual(mocked_executor.call_args.args[2], 90)

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
            "simulation_results": None,
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
                "simulation_requested": "boolean",
                "reason": "string",
                "simulation_spec": "object | null",
                "results": "object | null",
                "interpretation": "string | null",
            },
            "tier3": [
                {
                    "claim": "string",
                    "backend": "string",
                    "proof_status": "requested|proved|disproved|timeout|error|unavailable",
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

    def test_live_mode_does_not_clip_formal_transport_to_live_role_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_root = Path(tmpdir) / "live-results"
            with patch("deep_gvr.evaluation.AristotleFormalVerifier") as verifier_ctor:
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
