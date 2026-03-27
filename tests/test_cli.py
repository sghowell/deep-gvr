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
from deep_gvr.evaluation import CommandExecutionResult
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
        if "Role: generator" in query:
            payload = {
                "hypothesis": "The surface code has a threshold under standard depolarizing noise assumptions.",
                "approach": "Use established threshold literature as the candidate basis.",
                "technical_details": ["Threshold behavior is already well established in the cited literature."],
                "expected_results": ["The verifier should accept the claim analytically."],
                "assumptions": ["Standard depolarizing-noise assumptions apply."],
                "limitations": ["This is a test fixture response."],
                "references": ["Dennis et al. 2002"],
                "revision_notes": [],
            }
            return CommandExecutionResult(returncode=0, stdout=json.dumps(payload), stderr="")
        if "Role: verifier" in query:
            payload = {
                "verdict": "VERIFIED",
                "tier1": {
                    "checks": [
                        {
                            "check": "benchmark_ground_truth",
                            "status": "pass",
                            "detail": "The claim matches established threshold literature.",
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
            return CommandExecutionResult(returncode=0, stdout=json.dumps(payload), stderr="")
        return CommandExecutionResult(returncode=1, stdout="", stderr=f"Unexpected command: {command}")

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
            self.assertTrue(any(path.endswith("_run_role_transcripts.json") for path in summary.artifacts))
            transcript_path = next(Path(path) for path in summary.artifacts if path.endswith("_run_role_transcripts.json"))
            self.assertTrue(transcript_path.exists())
            checkpoint = json.loads(Path(summary.checkpoint_file).read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(checkpoint["literature_context"]), 1)

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
            self.assertTrue(any(path.endswith("_resume_role_transcripts.json") for path in summary.artifacts))

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
