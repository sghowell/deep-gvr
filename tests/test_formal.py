from __future__ import annotations

import json
import os
import shutil
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import _path_setup  # noqa: F401

from deep_gvr.contracts import FormalProofHandle, FormalProofLifecycle, ProofStatus, Tier3ClaimResult
from deep_gvr.formal import (
    AristotleFormalVerifier,
    AristotleTransportStatus,
    MathCodeFormalVerifier,
    MathCodeTransportStatus,
    OpenGaussTransportStatus,
    CommandExecutionResult,
    FormalVerificationRequest,
    build_formal_verifier,
    inspect_aristotle_transport,
    inspect_mathcode_transport,
    inspect_opengauss_transport,
)


def _request(*, backend: str = "aristotle") -> FormalVerificationRequest:
    return FormalVerificationRequest(
        session_id="session_formal",
        iteration=1,
        claims=[
            Tier3ClaimResult(
                claim="forall d >= 1, a repetition code has distance d",
                backend=backend,
                proof_status=ProofStatus.REQUESTED,
                details="Formalization requested by verifier.",
                lean_code="",
                proof_time_seconds=None,
            )
        ],
        backend=backend,
        timeout_seconds=30,
    )


def _write_aristotle_bundle(tmpdir: str, *, summary: str, lean_code: str) -> str:
    root = Path(tmpdir) / "bundle_root"
    project_dir = root / "RequestProject"
    project_dir.mkdir(parents=True, exist_ok=True)
    (root / "ARISTOTLE_SUMMARY_test.md").write_text(summary, encoding="utf-8")
    (project_dir / "Main.lean").write_text("import Mathlib\n", encoding="utf-8")
    (project_dir / "Proof.lean").write_text(lean_code, encoding="utf-8")
    tarball = Path(tmpdir) / "proof-bundle.tar.gz"
    with tarfile.open(tarball, "w:gz") as archive:
        archive.add(root, arcname="test_project")
    return str(tarball)


def _write_aristotle_result_dir(tmpdir: str, *, summary: str, lean_code: str) -> str:
    root = Path(tmpdir) / "result_dir"
    project_dir = root / "RequestProject"
    project_dir.mkdir(parents=True, exist_ok=True)
    (root / "ARISTOTLE_SUMMARY_test.md").write_text(summary, encoding="utf-8")
    (project_dir / "Main.lean").write_text("import Mathlib\n", encoding="utf-8")
    (project_dir / "Proof.lean").write_text(lean_code, encoding="utf-8")
    return str(root)


def _write_mathcode_root(tmpdir: str) -> Path:
    root = Path(tmpdir) / "mathcode"
    (root / "AUTOLEAN").mkdir(parents=True, exist_ok=True)
    (root / "lean-workspace").mkdir(parents=True, exist_ok=True)
    run_script = root / "run"
    run_script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    run_script.chmod(0o755)
    return root


def _write_opengauss_root(tmpdir: str) -> Path:
    root = Path(tmpdir) / "OpenGauss"
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "scripts" / "install.sh").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    launcher = root / "gauss"
    launcher.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    launcher.chmod(0o755)
    return root


class AristotleFormalVerifierTests(unittest.TestCase):
    def test_missing_api_key_returns_unavailable(self) -> None:
        request = _request()
        with patch.dict(os.environ, {}, clear=True):
            result_set = AristotleFormalVerifier()(request)

        self.assertEqual(len(result_set.results), 1)
        self.assertEqual(result_set.results[0].proof_status, ProofStatus.UNAVAILABLE)
        self.assertIn("ARISTOTLE_API_KEY", result_set.results[0].details)
        self.assertEqual(result_set.transport_artifact["status"], "missing_api_key")

    def test_present_api_key_without_mcp_server_returns_structured_unavailable(self) -> None:
        request = _request()
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(os.environ, {"ARISTOTLE_API_KEY": "configured"}):
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text("model:\n  default: test\n", encoding="utf-8")
            result_set = AristotleFormalVerifier(
                hermes_config_path=config_path,
                hermes_binary="python3",
                allow_cli_fallback=False,
            )(request)

        self.assertEqual(result_set.results[0].proof_status, ProofStatus.UNAVAILABLE)
        self.assertIn("mcp_servers.aristotle", result_set.results[0].details)
        self.assertEqual(result_set.transport_artifact["status"], "missing_mcp_server")

    def test_executor_success_is_returned(self) -> None:
        request = _request()

        def executor(incoming: FormalVerificationRequest) -> list[Tier3ClaimResult]:
            self.assertEqual(incoming.session_id, "session_formal")
            return [
                Tier3ClaimResult(
                    claim=incoming.claims[0].claim,
                    backend="aristotle",
                    proof_status=ProofStatus.PROVED,
                    details="Proof completed successfully.",
                    lean_code="theorem repetition_distance : True := by trivial",
                    proof_time_seconds=2.0,
                )
            ]

        result_set = AristotleFormalVerifier(executor=executor)(request)
        self.assertEqual(result_set.results[0].proof_status, ProofStatus.PROVED)
        self.assertEqual(result_set.results[0].proof_time_seconds, 2.0)
        self.assertIsNone(result_set.transport_artifact)

    def test_executor_timeout_maps_to_timeout_status(self) -> None:
        request = _request()

        def executor(incoming: FormalVerificationRequest) -> list[Tier3ClaimResult]:
            raise TimeoutError("timed out")

        result_set = AristotleFormalVerifier(executor=executor)(request)
        self.assertEqual(result_set.results[0].proof_status, ProofStatus.TIMEOUT)
        self.assertEqual(result_set.results[0].proof_time_seconds, 30.0)
        self.assertEqual(result_set.transport_artifact["status"], "timeout")

    def test_configured_transport_parses_hermes_json_response(self) -> None:
        request = _request()
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(os.environ, {"ARISTOTLE_API_KEY": "configured"}):
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(
                "mcp_servers:\n  aristotle:\n    command: uvx\n    args:\n      - aristotle-mcp\n",
                encoding="utf-8",
            )

            def command_executor(command: list[str], cwd: Path) -> CommandExecutionResult:
                self.assertEqual(command[:4], ["hermes", "chat", "-Q", "-q"])
                payload = {
                    "results": [
                        {
                            "claim": request.claims[0].claim,
                            "backend": "aristotle",
                            "proof_status": "proved",
                            "details": "Aristotle completed the proof.",
                            "lean_code": "theorem repetition_distance : True := by trivial",
                            "proof_time_seconds": 1.5,
                        }
                    ]
                }
                return CommandExecutionResult(returncode=0, stdout=json.dumps(payload), stderr="")

            result_set = AristotleFormalVerifier(
                command_executor=command_executor,
                hermes_config_path=config_path,
            )(request)

        self.assertEqual(result_set.results[0].proof_status, ProofStatus.PROVED)
        self.assertEqual(result_set.results[0].proof_time_seconds, 1.5)
        self.assertEqual(result_set.transport_artifact["status"], "completed")
        self.assertEqual(result_set.transport_artifact["mcp_server_name"], "aristotle")

    def test_configured_transport_timeout_maps_to_timeout_status(self) -> None:
        request = _request()
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(os.environ, {"ARISTOTLE_API_KEY": "configured"}):
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(
                "mcp_servers:\n  aristotle:\n    command: uvx\n    args:\n      - aristotle-mcp\n",
                encoding="utf-8",
            )

            def command_executor(command: list[str], cwd: Path) -> CommandExecutionResult:
                return CommandExecutionResult(
                    returncode=124,
                    stdout="",
                    stderr="Hermes command timed out after 30 seconds.",
                )

            result_set = AristotleFormalVerifier(
                command_executor=command_executor,
                hermes_config_path=config_path,
                allow_cli_fallback=False,
            )(request)

        self.assertEqual(result_set.results[0].proof_status, ProofStatus.TIMEOUT)
        self.assertEqual(result_set.transport_artifact["status"], "timeout")

    def test_cli_fallback_returns_proved_result_after_retryable_hermes_error(self) -> None:
        request = _request()
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(os.environ, {"ARISTOTLE_API_KEY": "configured"}):
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(
                "mcp_servers:\n  aristotle:\n    command: uvx\n    args:\n      - aristotle-mcp\n",
                encoding="utf-8",
            )
            tarball_path = _write_aristotle_bundle(
                tmpdir,
                summary="# Summary of changes\nA direct CLI proof succeeded.",
                lean_code="theorem cli_fallback : True := by trivial\n",
            )
            calls: list[list[str]] = []

            def hermes_executor(command: list[str], cwd: Path) -> CommandExecutionResult:
                calls.append(command)
                return CommandExecutionResult(returncode=1, stdout="", stderr="MCP transport failed")

            def cli_executor(command: list[str], cwd: Path) -> CommandExecutionResult:
                calls.append(command)
                return CommandExecutionResult(
                    returncode=0,
                    stdout=f"Project created: 123e4567-e89b-12d3-a456-426614174000\nProject saved to {tarball_path}\n",
                    stderr="",
                )

            result_set = AristotleFormalVerifier(
                command_executor=hermes_executor,
                cli_command_executor=cli_executor,
                hermes_config_path=config_path,
            )(request)

        self.assertEqual(result_set.results[0].proof_status, ProofStatus.PROVED)
        self.assertIn("123e4567-e89b-12d3-a456-426614174000", result_set.results[0].details)
        self.assertIn("theorem cli_fallback", result_set.results[0].lean_code)
        self.assertEqual(result_set.transport_artifact["transport"], "aristotle_cli_direct")
        self.assertEqual(result_set.transport_artifact["primary_transport"]["transport"], "hermes_mcp")
        self.assertEqual(result_set.transport_artifact["attempts"][0]["tarball_path"], tarball_path)
        self.assertEqual(calls[0][:4], ["hermes", "chat", "-Q", "-q"])
        self.assertEqual(calls[1][:3], ["aristotle", "submit", "--wait"])

    def test_cli_fallback_failure_is_attached_to_primary_failure(self) -> None:
        request = _request()
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(os.environ, {"ARISTOTLE_API_KEY": "configured"}):
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(
                "mcp_servers:\n  aristotle:\n    command: uvx\n    args:\n      - aristotle-mcp\n",
                encoding="utf-8",
            )

            def hermes_executor(command: list[str], cwd: Path) -> CommandExecutionResult:
                return CommandExecutionResult(returncode=1, stdout="", stderr="MCP transport failed")

            def cli_executor(command: list[str], cwd: Path) -> CommandExecutionResult:
                return CommandExecutionResult(returncode=1, stdout="", stderr="CLI fallback failed")

            result_set = AristotleFormalVerifier(
                command_executor=hermes_executor,
                cli_command_executor=cli_executor,
                hermes_config_path=config_path,
            )(request)

        self.assertEqual(result_set.results[0].proof_status, ProofStatus.ERROR)
        self.assertIn("CLI fallback also failed", result_set.results[0].details)
        self.assertEqual(result_set.transport_artifact["transport"], "hermes_mcp")
        self.assertEqual(result_set.transport_artifact["cli_fallback"]["transport"], "aristotle_cli_direct")

    def test_cli_lifecycle_submission_returns_pending_result_and_handle(self) -> None:
        request = _request()
        request.enable_lifecycle = True
        calls: list[list[str]] = []

        def cli_executor(command: list[str], cwd: Path) -> CommandExecutionResult:
            del cwd
            calls.append(command)
            if command[1] == "submit":
                return CommandExecutionResult(
                    returncode=0,
                    stdout="Project created: 123e4567-e89b-12d3-a456-426614174000\n",
                    stderr="",
                )
            self.assertEqual(command[1], "result")
            return CommandExecutionResult(
                returncode=124,
                stdout="",
                stderr="Aristotle CLI command timed out after 30 seconds.",
            )

        with patch.dict(os.environ, {"ARISTOTLE_API_KEY": "configured"}, clear=False):
            result_set = AristotleFormalVerifier(
                cli_command_executor=cli_executor,
                prefer_lifecycle=True,
            )(request)

        self.assertTrue(result_set.pending)
        self.assertEqual(result_set.results[0].proof_status, ProofStatus.PENDING)
        self.assertIsNotNone(result_set.lifecycle_state)
        self.assertEqual(result_set.lifecycle_state.proof_status, ProofStatus.PENDING)
        self.assertEqual(result_set.lifecycle_state.handles[0].project_id, "123e4567-e89b-12d3-a456-426614174000")
        self.assertEqual(calls[0][:2], ["aristotle", "submit"])
        self.assertEqual(calls[1][:2], ["aristotle", "result"])

    def test_cli_lifecycle_resume_polls_existing_project_to_completion(self) -> None:
        request = _request()
        request.enable_lifecycle = True
        request.lifecycle_state = FormalProofLifecycle(
            backend="aristotle",
            transport="aristotle_cli_lifecycle",
            proof_status=ProofStatus.PENDING,
            handles=[
                FormalProofHandle(
                    claim=request.claims[0].claim,
                    backend="aristotle",
                    project_id="123e4567-e89b-12d3-a456-426614174000",
                    transport="aristotle_cli_lifecycle",
                    proof_status=ProofStatus.PENDING,
                    submitted_at="2026-04-07T12:00:00Z",
                    last_polled_at=None,
                    poll_count=0,
                    details="Submitted Aristotle project 123e4567-e89b-12d3-a456-426614174000.",
                )
            ],
            last_transition="2026-04-07T12:00:00Z",
            details="pending=1 proved=0 error=0",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = _write_aristotle_result_dir(
                tmpdir,
                summary="# Summary of changes\nCLI lifecycle proof succeeded.",
                lean_code="theorem lifecycle_resume : True := by trivial\n",
            )

            def cli_executor(command: list[str], cwd: Path) -> CommandExecutionResult:
                del cwd
                self.assertEqual(command[1], "result")
                destination = Path(command[command.index("--destination") + 1])
                shutil.copytree(source_dir, destination, dirs_exist_ok=True)
                return CommandExecutionResult(returncode=0, stdout="Downloaded result.\n", stderr="")

            with patch.dict(os.environ, {"ARISTOTLE_API_KEY": "configured"}, clear=False):
                result_set = AristotleFormalVerifier(cli_command_executor=cli_executor)(request)

        self.assertFalse(result_set.pending)
        self.assertEqual(result_set.results[0].proof_status, ProofStatus.PROVED)
        self.assertIn("lifecycle_resume", result_set.results[0].lean_code)
        self.assertEqual(result_set.lifecycle_state.proof_status, ProofStatus.PROVED)
        self.assertEqual(result_set.lifecycle_state.handles[0].poll_count, 1)

    def test_compact_prompt_profile_emits_shorter_formal_query_than_full(self) -> None:
        request = _request()
        transport = AristotleTransportStatus(
            hermes_available=True,
            aristotle_key_present=True,
            hermes_config_path="/tmp/hermes.yaml",
            hermes_config_exists=True,
            mcp_server_name="aristotle",
            mcp_server_configured=True,
            configured_mcp_servers=["aristotle"],
        )
        prompt_text = "# Formalizer Prompt\n\nReturn normalized results."

        compact_query = AristotleFormalVerifier(prompt_profile="compact")._build_query(
            request,
            prompt_text=prompt_text,
            transport=transport,
        )
        full_query = AristotleFormalVerifier(prompt_profile="full")._build_query(
            request,
            prompt_text=prompt_text,
            transport=transport,
        )

        self.assertIn("Response budget:", compact_query)
        self.assertNotIn("Response budget:", full_query)
        self.assertLess(len(compact_query), len(full_query))


class AristotleTransportInspectionTests(unittest.TestCase):
    def test_inspect_transport_reports_ready_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(os.environ, {"ARISTOTLE_API_KEY": "configured"}):
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(
                "mcp_servers:\n  aristotle:\n    command: uvx\n    args:\n      - aristotle-mcp\n",
                encoding="utf-8",
            )

            status = inspect_aristotle_transport(hermes_config_path=config_path, hermes_binary="python3")

        self.assertTrue(status.ready)
        self.assertTrue(status.mcp_server_configured)


class MathCodeFormalVerifierTests(unittest.TestCase):
    def test_missing_mathcode_root_returns_unavailable(self) -> None:
        request = _request(backend="mathcode")
        result_set = MathCodeFormalVerifier(
            mathcode_root="/tmp/does-not-exist-mathcode",
            run_script="/tmp/does-not-exist-mathcode/run",
        )(request)

        self.assertEqual(result_set.results[0].proof_status, ProofStatus.UNAVAILABLE)
        self.assertIn("does not exist", result_set.results[0].details)
        self.assertEqual(result_set.transport_artifact["status"], "unavailable")

    def test_executor_success_is_returned(self) -> None:
        request = _request(backend="mathcode")

        def executor(incoming: FormalVerificationRequest) -> list[Tier3ClaimResult]:
            self.assertEqual(incoming.backend, "mathcode")
            return [
                Tier3ClaimResult(
                    claim=incoming.claims[0].claim,
                    backend="mathcode",
                    proof_status=ProofStatus.PROVED,
                    details="MathCode completed successfully.",
                    lean_code="theorem zero_add_nat (n : Nat) : 0 + n = n := by simp",
                    proof_time_seconds=1.0,
                )
            ]

        result_set = MathCodeFormalVerifier(executor=executor)(request)
        self.assertEqual(result_set.results[0].proof_status, ProofStatus.PROVED)
        self.assertEqual(result_set.results[0].proof_time_seconds, 1.0)

    def test_transport_parses_structured_output_envelope(self) -> None:
        request = _request(backend="mathcode")
        with tempfile.TemporaryDirectory() as tmpdir:
            mathcode_root = _write_mathcode_root(tmpdir)

            def command_executor(command: list[str], cwd: Path) -> CommandExecutionResult:
                self.assertEqual(cwd, mathcode_root)
                self.assertEqual(command[1:5], ["-p", "--output-format", "json", "--json-schema"])
                payload = {
                    "type": "result",
                    "subtype": "success",
                    "structured_output": {
                        "results": [
                            {
                                "claim": request.claims[0].claim,
                                "proof_status": "proved",
                                "details": "MathCode completed the proof.",
                                "lean_code": "theorem zero_add_nat (n : Nat) : 0 + n = n := by simp",
                                "proof_time_seconds": 1.25,
                            }
                        ]
                    },
                }
                return CommandExecutionResult(returncode=0, stdout=json.dumps(payload), stderr="")

            result_set = MathCodeFormalVerifier(
                command_executor=command_executor,
                mathcode_root=mathcode_root,
                run_script=mathcode_root / "run",
            )(request)

        self.assertEqual(result_set.results[0].proof_status, ProofStatus.PROVED)
        self.assertEqual(result_set.results[0].proof_time_seconds, 1.25)
        self.assertEqual(result_set.transport_artifact["transport"], "mathcode_cli")

    def test_transport_records_new_generated_lean_file(self) -> None:
        request = _request(backend="mathcode")
        with tempfile.TemporaryDirectory() as tmpdir:
            mathcode_root = _write_mathcode_root(tmpdir)
            generated_dir = mathcode_root / "LeanFormalizations" / "session_formal"

            def command_executor(command: list[str], cwd: Path) -> CommandExecutionResult:
                del command
                self.assertEqual(cwd, mathcode_root)
                generated_dir.mkdir(parents=True, exist_ok=True)
                generated_file = generated_dir / "Proof.lean"
                generated_file.write_text("theorem zero_add_nat (n : Nat) : 0 + n = n := by simp\n", encoding="utf-8")
                payload = {
                    "results": [
                        {
                            "claim": request.claims[0].claim,
                            "proof_status": "proved",
                            "details": "MathCode completed the proof.",
                            "lean_code": "theorem zero_add_nat (n : Nat) : 0 + n = n := by simp",
                            "proof_time_seconds": 1.25,
                        }
                    ]
                }
                return CommandExecutionResult(returncode=0, stdout=json.dumps(payload), stderr="")

            result_set = MathCodeFormalVerifier(
                command_executor=command_executor,
                mathcode_root=mathcode_root,
                run_script=mathcode_root / "run",
            )(request)

        generated = result_set.transport_artifact["generated_lean_file"]
        self.assertEqual(generated["relative_path"], "LeanFormalizations/session_formal/Proof.lean")
        self.assertEqual(generated["change"], "created")

    def test_transport_does_not_attribute_stale_preexisting_lean_file(self) -> None:
        request = _request(backend="mathcode")
        with tempfile.TemporaryDirectory() as tmpdir:
            mathcode_root = _write_mathcode_root(tmpdir)
            generated_dir = mathcode_root / "LeanFormalizations" / "session_formal"
            generated_dir.mkdir(parents=True, exist_ok=True)
            stale_file = generated_dir / "Proof.lean"
            stale_file.write_text("theorem stale : True := by trivial\n", encoding="utf-8")

            def command_executor(command: list[str], cwd: Path) -> CommandExecutionResult:
                del command
                self.assertEqual(cwd, mathcode_root)
                payload = {
                    "results": [
                        {
                            "claim": request.claims[0].claim,
                            "proof_status": "proved",
                            "details": "MathCode completed the proof.",
                            "lean_code": "theorem zero_add_nat (n : Nat) : 0 + n = n := by simp",
                            "proof_time_seconds": 1.25,
                        }
                    ]
                }
                return CommandExecutionResult(returncode=0, stdout=json.dumps(payload), stderr="")

            result_set = MathCodeFormalVerifier(
                command_executor=command_executor,
                mathcode_root=mathcode_root,
                run_script=mathcode_root / "run",
            )(request)

        self.assertNotIn("generated_lean_file", result_set.transport_artifact)

    def test_transport_timeout_maps_to_timeout_status(self) -> None:
        request = _request(backend="mathcode")
        with tempfile.TemporaryDirectory() as tmpdir:
            mathcode_root = _write_mathcode_root(tmpdir)

            def command_executor(command: list[str], cwd: Path) -> CommandExecutionResult:
                del command, cwd
                return CommandExecutionResult(returncode=124, stdout="", stderr="MathCode command timed out after 30 seconds.")

            result_set = MathCodeFormalVerifier(
                command_executor=command_executor,
                mathcode_root=mathcode_root,
                run_script=mathcode_root / "run",
            )(request)

        self.assertEqual(result_set.results[0].proof_status, ProofStatus.TIMEOUT)
        self.assertEqual(result_set.transport_artifact["status"], "timeout")

    def test_build_formal_verifier_selects_mathcode_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mathcode_root = _write_mathcode_root(tmpdir)
            verifier = build_formal_verifier(
                type(
                    "Tier3Stub",
                    (),
                    {
                        "backend": "mathcode",
                        "mathcode": type("MathCodeStub", (), {"root": str(mathcode_root), "run_script": str(mathcode_root / "run")})(),
                    },
                )()
            )

        self.assertIsInstance(verifier, MathCodeFormalVerifier)


class MathCodeTransportInspectionTests(unittest.TestCase):
    def test_inspect_transport_reports_ready_when_root_is_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mathcode_root = _write_mathcode_root(tmpdir)
            status = inspect_mathcode_transport(
                mathcode_root=mathcode_root,
                run_script=mathcode_root / "run",
            )

        self.assertTrue(status.ready)
        self.assertTrue(status.run_script_executable)


class OpenGaussTransportInspectionTests(unittest.TestCase):
    def test_inspect_transport_reports_ready_when_binary_and_config_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            opengauss_root = _write_opengauss_root(tmpdir)
            bin_dir = Path(tmpdir) / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            gauss_binary = bin_dir / "gauss"
            gauss_binary.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            gauss_binary.chmod(0o755)
            config_path = Path(tmpdir) / ".gauss" / "config.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("model:\n  default: test\n", encoding="utf-8")

            status = inspect_opengauss_transport(
                opengauss_root=opengauss_root,
                gauss_binary=gauss_binary,
                gauss_config_path=config_path,
            )

        self.assertIsInstance(status, OpenGaussTransportStatus)
        self.assertTrue(status.ready)
        self.assertTrue(status.install_script_exists)
        self.assertTrue(status.local_launcher_exists)
        self.assertTrue(status.gauss_available)
        self.assertTrue(status.gauss_config_exists)


if __name__ == "__main__":
    unittest.main()
