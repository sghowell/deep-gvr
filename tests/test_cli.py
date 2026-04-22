from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
import yaml

from tests import _path_setup  # noqa: F401

from deep_gvr.cli import load_runtime_config, resume_session_command, run_session_command
from deep_gvr.contracts import DeepGvrConfig
from deep_gvr.orchestrator import CommandExecutionResult
from deep_gvr.tier1 import SessionStore

ROOT = Path(__file__).resolve().parents[1]


class SkillCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.codex_queries: list[str] = []

    def _write_config(self, config_path: Path, evidence_dir: Path) -> None:
        payload = DeepGvrConfig().to_dict()
        payload["evidence"]["directory"] = str(evidence_dir)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    def _successful_executor(self, command: list[str], cwd: Path) -> CommandExecutionResult:
        del cwd
        query = command[command.index("-q") + 1]
        self.assertIn("--skills", command)
        self.assertIn("deep-gvr", command[command.index("--skills") + 1])
        self.assertIn("delegated orchestrator runtime", query)
        self.assertIn("Treat `role_routes` as requested routing intent", query)
        self.assertIn("distinct_routes_verified=true", query)
        self.assertIn("delegated_mcp_verified=true", query)
        payload = {
            "command": "run" if '"command": "run"' in query else "resume",
            "session_id": "session_cli_run" if '"command": "run"' in query else "session_cli_resume",
            "status": "completed",
            "final_verdict": "VERIFIED",
            "result_summary": "Delegated orchestration completed.",
            "problem": "Explain why the surface code has a threshold.",
            "domain": "qec",
            "iterations": 1,
            "config_path": "/tmp/config.yaml",
            "config_created": False,
            "evidence_log": "/tmp/evidence.jsonl",
            "checkpoint_file": "/tmp/checkpoint.json",
            "artifacts_dir": "/tmp/artifacts",
            "artifacts": ["/tmp/artifacts/session_summary.json"],
            "capability_evidence": {
                "per_subagent_model_routing": {
                    "distinct_routes_verified": '"command": "run"' in query and '"routing_probe": "ready"' in query,
                    "route_pairs": {
                        "generator": {"provider": "openrouter", "model": "claude-sonnet-4"},
                        "verifier": {"provider": "openrouter", "model": "deepseek-r1"},
                    },
                    "evidence_source": "delegated_runtime_test",
                }
            },
            "error": None,
        }
        return CommandExecutionResult(returncode=0, stdout=json.dumps(payload), stderr="")

    def _failing_executor(self, command: list[str], cwd: Path) -> CommandExecutionResult:
        del command, cwd
        return CommandExecutionResult(returncode=124, stdout="", stderr="Hermes command timed out after 5 seconds.")

    def _failing_codex_executor(self, command: list[str], cwd: Path) -> CommandExecutionResult:
        del cwd
        self.assertEqual(command[:2], ["codex", "exec"])
        output_path = Path(command[command.index("--output-last-message") + 1])
        query = command[-1]
        self.codex_queries.append(query)
        if "Role: generator" in query:
            output_path.write_text("", encoding="utf-8")
            return CommandExecutionResult(returncode=1, stdout="", stderr="generator role transport failed")
        payload = {
            "verdict": "VERIFIED",
            "tier1": {
                "checks": [
                    {"check": "Logical consistency", "status": "pass", "detail": "The claim is internally consistent."}
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
        output_path.write_text(json.dumps(payload), encoding="utf-8")
        return CommandExecutionResult(returncode=0, stdout="", stderr="")

    def _successful_codex_executor(self, command: list[str], cwd: Path) -> CommandExecutionResult:
        self.assertEqual(command[:2], ["codex", "exec"])
        self.assertIn("--output-schema", command)
        self.assertIn("--output-last-message", command)
        self.assertIn("--json", command)
        self.assertIn("--sandbox", command)
        self.assertIn("workspace-write", command)
        schema_path = Path(command[command.index("--output-schema") + 1])
        output_path = Path(command[command.index("--output-last-message") + 1])
        query = command[-1]
        self.codex_queries.append(query)
        self.assertEqual(cwd, output_path.parent)
        self.assertTrue(schema_path.exists())
        self.assertIn("This is a runtime role execution", query)
        self.assertIn("Do not call `uv run deep-gvr run` or `uv run deep-gvr resume`", query)
        role = next(role_name for role_name in ("generator", "verifier", "reviser") if f"Role: {role_name}" in query)
        if role == "generator":
            if "-c" in command:
                self.assertIn('model_provider="openrouter"', command)
                self.assertIn("--model", command)
                self.assertIn("claude-sonnet-4", command)
            payload = {
                "hypothesis": "The surface code exhibits a threshold under standard circuit-level depolarizing noise.",
                "approach": "Use the established surface-code threshold literature to justify the claim.",
                "technical_details": ["Threshold behavior follows from established decoder and circuit-noise studies."],
                "expected_results": ["Below threshold, increasing distance suppresses logical error."],
                "assumptions": ["Standard circuit-level depolarizing noise."],
                "limitations": ["This is a literature-grounded explanation, not a fresh simulation campaign."],
                "references": ["Fowler et al. 2012", "Stephens 2014"],
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
                        {"check": "Logical consistency", "status": "pass", "detail": "The claim stays within the cited threshold literature."},
                        {"check": "Citation validity", "status": "pass", "detail": "The cited sources are standard threshold references."},
                        {"check": "Physical plausibility", "status": "pass", "detail": "The explanation matches the accepted surface-code regime."},
                        {"check": "Completeness", "status": "pass", "detail": "The explanation states the claim, scope, and assumptions."},
                        {"check": "Overclaiming", "status": "pass", "detail": "The candidate does not assert unsupported new quantitative results."},
                    ],
                    "overall": "VERIFIED",
                    "flaws": [],
                    "caveats": ["Literature-grounded explanation only."],
                },
                "tier2": {
                    "analysis_requested": False,
                    "reason": "Tier 1 literature grounding is sufficient for this explanation.",
                    "analysis_spec": None,
                    "results": None,
                    "interpretation": None,
                },
                "tier3": [],
                "flaws": [],
                "caveats": ["Literature-grounded explanation only."],
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
        return CommandExecutionResult(
            returncode=0,
            stdout='{"event":"completed"}\n',
            stderr="",
        )

    def _route_fallback_codex_executor(self, command: list[str], cwd: Path) -> CommandExecutionResult:
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
        return self._successful_codex_executor(command, cwd)

    def test_load_runtime_config_creates_default_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "deep-gvr" / "config.yaml"
            config = load_runtime_config(config_path)
            self.assertTrue(config_path.exists())
            self.assertEqual(config.domain.default, "qec")

    def test_run_session_command_returns_summary_and_transcript_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            evidence_dir = Path(tmpdir) / "sessions"
            self._write_config(config_path, evidence_dir)

            summary = run_session_command(
                "Explain why the surface code has a threshold.",
                config_path=config_path,
                session_id="session_cli_run",
                executor=self._successful_executor,
                command_timeout_seconds=5,
            )

            self.assertEqual(summary.command, "run")
            self.assertEqual(summary.session_id, "session_cli_run")
            self.assertEqual(summary.final_verdict, "VERIFIED")
            self.assertFalse(summary.config_created)
            self.assertIsNotNone(summary.capability_evidence)
            self.assertEqual(summary.capability_evidence["per_subagent_model_routing"]["evidence_source"], "delegated_runtime_test")
            self.assertTrue(any(path.endswith("_run_orchestrator_transcript.json") for path in summary.artifacts))
            self.assertTrue(any(path.endswith("session_memory_summary.json") for path in summary.artifacts))
            self.assertTrue(any(path.endswith("parallax_manifest.json") for path in summary.artifacts))
            transcript_path = next(
                Path(path) for path in summary.artifacts if path.endswith("_run_orchestrator_transcript.json")
            )
            self.assertTrue(transcript_path.exists())
            transcripts = json.loads(transcript_path.read_text(encoding="utf-8"))
            self.assertEqual(transcripts["calls"][0]["backend"], "hermes")
            self.assertIn("delegated orchestrator runtime", transcripts["calls"][0]["query"])
            self.assertIn("--skills", transcripts["calls"][0]["backend_command"])
            self.assertIn("deep-gvr", transcripts["calls"][0]["backend_command"])
            self.assertEqual(transcripts["calls"][0]["backend_command"], transcripts["calls"][0]["hermes_command"])
            self.assertIn("role_routes", transcripts["calls"][0])
            self.assertIn("generator", transcripts["calls"][0]["role_routes"])
            self.assertIn("verifier", transcripts["calls"][0]["role_routes"])
            self.assertIn("capability_evidence", transcripts["calls"][0])
            self.assertEqual(
                transcripts["calls"][0]["capability_evidence"]["per_subagent_model_routing"]["evidence_source"],
                "delegated_runtime_test",
            )

    def test_run_session_command_explicit_toolsets_override_default_restriction(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            evidence_dir = Path(tmpdir) / "sessions"
            self._write_config(config_path, evidence_dir)

            summary = run_session_command(
                "Explain why the surface code has a threshold.",
                config_path=config_path,
                session_id="session_cli_run_toolsets",
                executor=self._successful_executor,
                command_timeout_seconds=5,
                toolsets=["search"],
            )

            transcript_path = next(
                Path(path) for path in summary.artifacts if path.endswith("_run_orchestrator_transcript.json")
            )
            transcripts = json.loads(transcript_path.read_text(encoding="utf-8"))
            self.assertIn("--toolsets", transcripts["calls"][0]["backend_command"])
            self.assertIn("search", transcripts["calls"][0]["backend_command"])

    def test_run_session_command_supports_full_prompt_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            evidence_dir = Path(tmpdir) / "sessions"
            self._write_config(config_path, evidence_dir)

            summary = run_session_command(
                "Explain why the surface code has a threshold.",
                config_path=config_path,
                session_id="session_cli_run_full",
                executor=self._successful_executor,
                command_timeout_seconds=5,
                prompt_profile="full",
            )

            transcript_path = next(
                Path(path) for path in summary.artifacts if path.endswith("_run_orchestrator_transcript.json")
            )
            transcripts = json.loads(transcript_path.read_text(encoding="utf-8"))
            self.assertEqual(transcripts["calls"][0]["prompt_profile"], "full")

    def test_run_session_command_threads_ready_role_routes_into_transcript(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            evidence_dir = Path(tmpdir) / "sessions"
            self._write_config(config_path, evidence_dir)

            summary = run_session_command(
                "Explain why the surface code has a threshold.",
                config_path=config_path,
                session_id="session_cli_run_ready_routes",
                executor=self._successful_executor,
                command_timeout_seconds=5,
                routing_probe_mode="ready",
            )

            transcript_path = next(
                Path(path) for path in summary.artifacts if path.endswith("_run_orchestrator_transcript.json")
            )
            transcripts = json.loads(transcript_path.read_text(encoding="utf-8"))
            role_routes = transcripts["calls"][0]["role_routes"]
            self.assertEqual(role_routes["strategy"], "direct")
            self.assertEqual(role_routes["generator"]["provider"], "openrouter")
            self.assertEqual(role_routes["generator"]["model"], "claude-sonnet-4")
            self.assertEqual(role_routes["verifier"]["provider"], "openrouter")
            self.assertEqual(role_routes["verifier"]["model"], "deepseek-r1")
            capability_evidence = transcripts["calls"][0]["capability_evidence"]
            self.assertTrue(capability_evidence["per_subagent_model_routing"]["distinct_routes_verified"])
            capability_artifact = next(
                Path(path) for path in summary.artifacts if path.endswith("_run_capability_evidence.json")
            )
            payload = json.loads(capability_artifact.read_text(encoding="utf-8"))
            self.assertTrue(payload["capability_evidence"]["per_subagent_model_routing"]["distinct_routes_verified"])
            self.assertTrue(summary.capability_evidence["per_subagent_model_routing"]["distinct_routes_verified"])

    def test_resume_session_command_continues_existing_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            evidence_dir = Path(tmpdir) / "sessions"
            self._write_config(config_path, evidence_dir)
            store = SessionStore(evidence_dir)
            store.initialize_session(
                problem="Resume this session",
                domain="qec",
                max_iterations=3,
                literature_context=["Stored context"],
                session_id="session_cli_resume",
            )

            summary = resume_session_command(
                "session_cli_resume",
                config_path=config_path,
                executor=self._successful_executor,
                command_timeout_seconds=5,
            )

            self.assertEqual(summary.command, "resume")
            self.assertEqual(summary.session_id, "session_cli_resume")
            self.assertEqual(summary.final_verdict, "VERIFIED")
            self.assertTrue(any(path.endswith("_resume_orchestrator_transcript.json") for path in summary.artifacts))

    def test_run_session_command_codex_backend_uses_codex_transport(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            evidence_dir = Path(tmpdir) / "sessions"
            payload = DeepGvrConfig().to_dict()
            payload["runtime"]["orchestrator_backend"] = "codex_local"
            payload["evidence"]["directory"] = str(evidence_dir)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

            summary = run_session_command(
                "Explain why the surface code has a threshold.",
                config_path=config_path,
                session_id="session_cli_codex_backend",
                executor=self._successful_codex_executor,
                command_timeout_seconds=5,
            )

            self.assertEqual(summary.command, "run")
            self.assertEqual(summary.final_verdict, "VERIFIED")
            self.assertIsNone(summary.error)
            transcript_path = next(
                Path(path) for path in summary.artifacts if path.endswith("_run_orchestrator_transcript.json")
            )
            transcripts = json.loads(transcript_path.read_text(encoding="utf-8"))
            self.assertEqual([call["role"] for call in transcripts["calls"]], ["generator", "verifier"])
            self.assertTrue(all(call["backend"] == "codex_local" for call in transcripts["calls"]))
            self.assertTrue(all(call["skills"] == [] for call in transcripts["calls"]))
            self.assertTrue(all("codex" in call["backend_command"][0] for call in transcripts["calls"]))
            self.assertTrue(all("--output-last-message" in call["backend_command"] for call in transcripts["calls"]))
            self.assertTrue(all("hermes_command" not in call for call in transcripts["calls"]))
            self.assertEqual(transcripts["calls"][0]["selected_route"]["provider"], "openrouter")
            self.assertEqual(transcripts["calls"][0]["selected_route"]["model"], "claude-sonnet-4")
            self.assertEqual(transcripts["calls"][1]["selected_route"]["provider"], "openrouter")
            self.assertEqual(transcripts["calls"][1]["selected_route"]["model"], "deepseek-r1")
            self.assertIn("response_object", transcripts["calls"][0])
            self.assertEqual(
                transcripts["calls"][0]["response_object"]["hypothesis"],
                "The surface code exhibits a threshold under standard circuit-level depolarizing noise.",
            )
            self.assertIn("response_object", transcripts["calls"][1])
            self.assertEqual(transcripts["calls"][1]["response_object"]["verdict"], "VERIFIED")
            self.assertIn("Generator Prompt", transcripts["calls"][0]["query"])
            self.assertIn("Compact Verifier Prompt", transcripts["calls"][1]["query"])
            role_routes = transcripts["calls"][0]["role_routes"]
            self.assertEqual(role_routes["strategy"], "direct")
            self.assertEqual(role_routes["generator"]["model"], "claude-sonnet-4")
            self.assertEqual(role_routes["verifier"]["model"], "deepseek-r1")
            self.assertIsNotNone(summary.capability_evidence)
            self.assertEqual(summary.capability_evidence["codex_native_role_execution"]["evidence_source"], "codex_native_backend")
            self.assertTrue(summary.capability_evidence["codex_native_role_execution"]["distinct_generator_verifier_routes"])
            capability_artifact = next(
                Path(path) for path in summary.artifacts if path.endswith("_run_capability_evidence.json")
            )
            capability_payload = json.loads(capability_artifact.read_text(encoding="utf-8"))
            self.assertEqual(
                capability_payload["capability_evidence"]["codex_native_role_execution"]["route_pairs"]["generator"]["model"],
                "claude-sonnet-4",
            )
            self.assertEqual(
                capability_payload["capability_evidence"]["codex_native_role_execution"]["route_pairs"]["verifier"]["model"],
                "deepseek-r1",
            )

    def test_run_session_command_codex_backend_supports_full_verifier_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            evidence_dir = Path(tmpdir) / "sessions"
            payload = DeepGvrConfig().to_dict()
            payload["runtime"]["orchestrator_backend"] = "codex_local"
            payload["evidence"]["directory"] = str(evidence_dir)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

            summary = run_session_command(
                "Explain why the surface code has a threshold.",
                config_path=config_path,
                session_id="session_cli_codex_backend_full",
                executor=self._successful_codex_executor,
                command_timeout_seconds=5,
                prompt_profile="full",
            )

            transcript_path = next(
                Path(path) for path in summary.artifacts if path.endswith("_run_orchestrator_transcript.json")
            )
            transcripts = json.loads(transcript_path.read_text(encoding="utf-8"))
            verifier_call = next(call for call in transcripts["calls"] if call["role"] == "verifier")
            self.assertIn("Verifier Prompt", verifier_call["query"])
            self.assertNotIn("Compact Verifier Prompt", verifier_call["query"])

    def test_run_session_command_codex_backend_falls_back_from_invalid_explicit_role_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            evidence_dir = Path(tmpdir) / "sessions"
            payload = DeepGvrConfig().to_dict()
            payload["runtime"]["orchestrator_backend"] = "codex_local"
            payload["evidence"]["directory"] = str(evidence_dir)
            payload["models"]["orchestrator"]["provider"] = "default"
            payload["models"]["orchestrator"]["model"] = ""
            payload["models"]["generator"]["provider"] = "openrouter"
            payload["models"]["generator"]["model"] = "broken-generator"
            payload["models"]["verifier"]["provider"] = "openrouter"
            payload["models"]["verifier"]["model"] = "broken-verifier"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

            summary = run_session_command(
                "Explain why the surface code has a threshold.",
                config_path=config_path,
                session_id="session_cli_codex_route_fallback",
                executor=self._route_fallback_codex_executor,
                command_timeout_seconds=5,
            )

            self.assertEqual(summary.command, "run")
            self.assertEqual(summary.final_verdict, "VERIFIED")
            transcript_path = next(
                Path(path) for path in summary.artifacts if path.endswith("_run_orchestrator_transcript.json")
            )
            transcripts = json.loads(transcript_path.read_text(encoding="utf-8"))
            self.assertEqual(len(transcripts["calls"]), 4)
            self.assertIn("broken-generator", transcripts["calls"][0]["backend_command"])
            self.assertNotIn("-c", transcripts["calls"][1]["backend_command"])
            self.assertIn("broken-verifier", transcripts["calls"][2]["backend_command"])
            self.assertNotIn("-c", transcripts["calls"][3]["backend_command"])
            self.assertEqual(transcripts["calls"][1]["selected_route"]["model"], "configured-by-codex")
            self.assertEqual(transcripts["calls"][3]["selected_route"]["model"], "configured-by-codex")
            self.assertTrue(
                any("fell back from openrouter/broken-verifier" in note.lower() for note in transcripts["calls"][3]["selected_route"]["notes"])
            )
            capability_artifact = next(
                Path(path) for path in summary.artifacts if path.endswith("_run_capability_evidence.json")
            )
            capability_payload = json.loads(capability_artifact.read_text(encoding="utf-8"))
            self.assertEqual(
                capability_payload["capability_evidence"]["codex_native_role_execution"]["route_pairs"]["verifier"]["model"],
                "configured-by-codex",
            )

    def test_resume_session_command_codex_backend_uses_native_role_loop(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            evidence_dir = Path(tmpdir) / "sessions"
            payload = DeepGvrConfig().to_dict()
            payload["runtime"]["orchestrator_backend"] = "codex_local"
            payload["evidence"]["directory"] = str(evidence_dir)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            store = SessionStore(evidence_dir)
            store.initialize_session(
                problem="Resume this session",
                domain="qec",
                max_iterations=3,
                literature_context=["Stored context"],
                session_id="session_cli_codex_resume",
            )

            summary = resume_session_command(
                "session_cli_codex_resume",
                config_path=config_path,
                executor=self._successful_codex_executor,
                command_timeout_seconds=5,
            )

            self.assertEqual(summary.command, "resume")
            self.assertEqual(summary.final_verdict, "VERIFIED")
            transcript_path = next(
                Path(path) for path in summary.artifacts if path.endswith("_resume_orchestrator_transcript.json")
            )
            transcripts = json.loads(transcript_path.read_text(encoding="utf-8"))
            self.assertEqual([call["role"] for call in transcripts["calls"]], ["generator", "verifier"])

    def test_run_session_command_returns_structured_error_on_role_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            evidence_dir = Path(tmpdir) / "sessions"
            self._write_config(config_path, evidence_dir)

            summary = run_session_command(
                "Explain why the surface code has a threshold.",
                config_path=config_path,
                session_id="session_cli_error",
                executor=self._failing_executor,
                command_timeout_seconds=5,
            )

            self.assertEqual(summary.session_id, "session_cli_error")
            self.assertIsNotNone(summary.error)
            self.assertEqual(summary.final_verdict, "PENDING")
            self.assertTrue(any(path.endswith("_run_error.json") for path in summary.artifacts))
            self.assertTrue(any(path.endswith("session_memory_summary.json") for path in summary.artifacts))
            self.assertTrue(any(path.endswith("parallax_manifest.json") for path in summary.artifacts))

    def test_run_session_command_codex_backend_preserves_failed_role_transcript(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            evidence_dir = Path(tmpdir) / "sessions"
            payload = DeepGvrConfig().to_dict()
            payload["runtime"]["orchestrator_backend"] = "codex_local"
            payload["evidence"]["directory"] = str(evidence_dir)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

            summary = run_session_command(
                "Explain why the surface code has a threshold.",
                config_path=config_path,
                session_id="session_cli_codex_failure",
                executor=self._failing_codex_executor,
                command_timeout_seconds=5,
            )

            self.assertEqual(summary.session_id, "session_cli_codex_failure")
            self.assertIsNotNone(summary.error)
            transcript_path = next(
                Path(path) for path in summary.artifacts if path.endswith("_run_orchestrator_transcript.json")
            )
            transcripts = json.loads(transcript_path.read_text(encoding="utf-8"))
            self.assertEqual(len(transcripts["calls"]), 1)
            self.assertEqual(transcripts["calls"][0]["backend"], "codex_local")
            self.assertEqual(transcripts["calls"][0]["role"], "generator")
            self.assertIn("generator role transport failed", transcripts["calls"][0]["error"])
            self.assertEqual(transcripts["calls"][0]["response"], "generator role transport failed")
            self.assertNotIn("response_object", transcripts["calls"][0])
            self.assertIsNotNone(summary.capability_evidence)
            self.assertEqual(
                summary.capability_evidence["codex_native_role_execution"]["failed_roles"],
                ["generator"],
            )

    def test_console_script_help(self) -> None:
        completed = subprocess.run(
            ["uv", "run", "deep-gvr", "--help"],
            check=False,
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("run", completed.stdout)
        self.assertIn("resume", completed.stdout)


if __name__ == "__main__":
    unittest.main()
