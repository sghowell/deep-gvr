from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from tests import _path_setup  # noqa: F401

from deep_gvr.codex_ssh_devbox_runtime import (
    CodexSshDevboxPreflightError,
    ensure_codex_ssh_devbox_ready,
    run_codex_ssh_devbox_session,
)
from deep_gvr.contracts import CapabilityProbeResult, DeepGvrConfig, ProbeStatus
from deep_gvr.orchestrator import CommandExecutionResult

ROOT = Path(__file__).resolve().parents[1]


class CodexSshDevboxRuntimeTests(unittest.TestCase):
    def _successful_codex_executor(self, command: list[str], cwd: Path) -> CommandExecutionResult:
        self.assertEqual(command[:2], ["codex", "exec"])
        output_path = Path(command[command.index("--output-last-message") + 1])
        query = command[-1]
        self.assertEqual(cwd, output_path.parent)
        self.assertIn("Codex-local orchestrator backend", query)
        payload = {
            "command": "run",
            "session_id": "session_codex_remote",
            "status": "completed",
            "final_verdict": "VERIFIED",
            "result_summary": "Codex SSH/devbox execution completed.",
            "problem": "Explain why the surface code has a threshold.",
            "domain": "qec",
            "iterations": 1,
            "config_path": "/tmp/config.yaml",
            "config_created": False,
            "evidence_log": "/tmp/evidence.jsonl",
            "checkpoint_file": "/tmp/checkpoint.json",
            "artifacts_dir": "/tmp/artifacts",
            "artifacts": ["/tmp/artifacts/session_summary.json"],
            "capability_evidence": {},
            "error": None,
        }
        output_path.write_text(json.dumps(payload), encoding="utf-8")
        return CommandExecutionResult(returncode=0, stdout='{"event":"completed"}\n', stderr="")

    def test_run_codex_ssh_devbox_session_executes_after_passing_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            codex_home = Path(tmpdir) / "codex-home"
            codex_target_dir = codex_home / "skills"
            hermes_target_dir = Path(tmpdir) / ".hermes" / "skills"
            bin_dir = Path(tmpdir) / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            for binary_name in ("codex", "ssh", "scp"):
                binary_path = bin_dir / binary_name
                binary_path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
                binary_path.chmod(0o755)

            env = dict(os.environ)
            env["HOME"] = tmpdir
            env["CODEX_HOME"] = str(codex_home)
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
            install = subprocess.run(
                ["bash", str(ROOT / "scripts" / "install_codex.sh"), "--skip-hermes-install"],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
            )
            self.assertEqual(install.returncode, 0, install.stderr)

            runtime_home = Path(tmpdir) / "deep-gvr-runtime"
            config_path = runtime_home / "config.yaml"
            evidence_dir = runtime_home / "sessions"
            payload = DeepGvrConfig().to_dict()
            payload["runtime"]["orchestrator_backend"] = "codex_local"
            payload["verification"]["tier2"]["default_backend"] = "ssh"
            payload["verification"]["tier2"]["ssh"]["host"] = "validator-node"
            payload["verification"]["tier2"]["ssh"]["remote_workspace"] = "/srv/deep-gvr"
            payload["verification"]["tier2"]["ssh"]["python_bin"] = "python3"
            payload["evidence"]["directory"] = str(evidence_dir)
            for role in ("orchestrator", "generator", "verifier", "reviser"):
                payload["models"][role]["provider"] = "default"
                payload["models"][role]["model"] = ""
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

            prior_path = os.environ.get("PATH")
            os.environ["PATH"] = env["PATH"]
            try:
                with patch(
                    "deep_gvr.release_surface.probe_analysis_adapter_families",
                    return_value=CapabilityProbeResult(
                        name="analysis_adapter_families",
                        status=ProbeStatus.READY,
                        summary="patched analysis families ready",
                        preferred_outcome="",
                        fallback="",
                        details={
                            "ready_family_count": 9,
                            "total_family_count": 9,
                            "families": {
                                "qec_decoder_benchmark": {
                                    "ready": True,
                                    "packages": {"numpy": True, "stim": True, "pymatching": True},
                                }
                            },
                        },
                    ),
                ):
                    result = run_codex_ssh_devbox_session(
                        "Explain why the surface code has a threshold.",
                        config_path=config_path,
                        codex_skills_dir=codex_target_dir,
                        hermes_skills_dir=hermes_target_dir,
                        hermes_config_path=Path(tmpdir) / ".hermes" / "config.yaml",
                        executor=self._successful_codex_executor,
                        command_timeout_seconds=5,
                        session_id="session_codex_remote",
                    )
            finally:
                if prior_path is None:
                    del os.environ["PATH"]
                else:
                    os.environ["PATH"] = prior_path

        self.assertTrue(result.preflight.operator_ready)
        remote_check = next(check for check in result.preflight.checks if check.name == "ssh_devbox_backend")
        self.assertEqual(remote_check.status.value, "ready")
        self.assertEqual(result.session.final_verdict, "VERIFIED")
        self.assertEqual(result.session.session_id, "session_codex_remote")

    def test_ensure_codex_ssh_devbox_ready_blocks_without_codex_backend(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            codex_home = Path(tmpdir) / "codex-home"
            codex_target_dir = codex_home / "skills"
            hermes_target_dir = Path(tmpdir) / ".hermes" / "skills"
            bin_dir = Path(tmpdir) / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            for binary_name in ("codex", "hermes", "ssh", "scp"):
                binary_path = bin_dir / binary_name
                binary_path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
                binary_path.chmod(0o755)

            env = dict(os.environ)
            env["HOME"] = tmpdir
            env["CODEX_HOME"] = str(codex_home)
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
            install = subprocess.run(
                ["bash", str(ROOT / "scripts" / "install_codex.sh")],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
            )
            self.assertEqual(install.returncode, 0, install.stderr)

            runtime_home = Path(tmpdir) / "deep-gvr-runtime"
            config_path = runtime_home / "config.yaml"
            evidence_dir = runtime_home / "sessions"
            payload = DeepGvrConfig().to_dict()
            payload["runtime"]["orchestrator_backend"] = "hermes"
            payload["verification"]["tier2"]["default_backend"] = "ssh"
            payload["verification"]["tier2"]["ssh"]["host"] = "validator-node"
            payload["verification"]["tier2"]["ssh"]["remote_workspace"] = "/srv/deep-gvr"
            payload["verification"]["tier2"]["ssh"]["python_bin"] = "python3"
            payload["evidence"]["directory"] = str(evidence_dir)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

            prior_path = os.environ.get("PATH")
            os.environ["PATH"] = env["PATH"]
            try:
                with self.assertRaises(CodexSshDevboxPreflightError) as ctx:
                    ensure_codex_ssh_devbox_ready(
                        config_path=config_path,
                        codex_skills_dir=codex_target_dir,
                        hermes_skills_dir=hermes_target_dir,
                        hermes_config_path=Path(tmpdir) / ".hermes" / "config.yaml",
                    )
            finally:
                if prior_path is None:
                    del os.environ["PATH"]
                else:
                    os.environ["PATH"] = prior_path

        remote_check = next(check for check in ctx.exception.report.checks if check.name == "ssh_devbox_backend")
        self.assertEqual(remote_check.status.value, "blocked")
        self.assertEqual(remote_check.details["orchestrator_backend"], "hermes")

    def test_codex_ssh_devbox_run_script_help(self) -> None:
        completed = subprocess.run(
            ["python3", str(ROOT / "scripts" / "codex_ssh_devbox_run.py"), "--help"],
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
