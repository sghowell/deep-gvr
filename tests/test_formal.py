from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import _path_setup  # noqa: F401

from deep_gvr.contracts import ProofStatus, Tier3ClaimResult
from deep_gvr.formal import (
    AristotleFormalVerifier,
    CommandExecutionResult,
    FormalVerificationRequest,
    inspect_aristotle_transport,
)


def _request() -> FormalVerificationRequest:
    return FormalVerificationRequest(
        session_id="session_formal",
        iteration=1,
        claims=[
            Tier3ClaimResult(
                claim="forall d >= 1, a repetition code has distance d",
                backend="aristotle",
                proof_status=ProofStatus.REQUESTED,
                details="Formalization requested by verifier.",
                lean_code="",
                proof_time_seconds=None,
            )
        ],
        backend="aristotle",
        timeout_seconds=30,
    )


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
            )(request)

        self.assertEqual(result_set.results[0].proof_status, ProofStatus.TIMEOUT)
        self.assertEqual(result_set.transport_artifact["status"], "timeout")


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


if __name__ == "__main__":
    unittest.main()
