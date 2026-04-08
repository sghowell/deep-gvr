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
            self.assertIn("delegated orchestrator runtime", transcripts["calls"][0]["query"])
            self.assertIn("--skills", transcripts["calls"][0]["hermes_command"])
            self.assertIn("deep-gvr", transcripts["calls"][0]["hermes_command"])
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
            self.assertIn("--toolsets", transcripts["calls"][0]["hermes_command"])
            self.assertIn("search", transcripts["calls"][0]["hermes_command"])

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
