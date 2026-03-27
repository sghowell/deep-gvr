from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from tests import _path_setup  # noqa: F401

from deep_gvr.contracts import ProofStatus, Tier3ClaimResult
from deep_gvr.formal import AristotleFormalVerifier, FormalVerificationRequest


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
            results = AristotleFormalVerifier()(request)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].proof_status, ProofStatus.UNAVAILABLE)
        self.assertIn("ARISTOTLE_API_KEY", results[0].details)

    def test_present_api_key_still_returns_structured_unavailable_without_transport(self) -> None:
        request = _request()
        with patch.dict(os.environ, {"ARISTOTLE_API_KEY": "configured"}):
            results = AristotleFormalVerifier()(request)

        self.assertEqual(results[0].proof_status, ProofStatus.UNAVAILABLE)
        self.assertIn("transport is not wired", results[0].details)

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

        results = AristotleFormalVerifier(executor=executor)(request)
        self.assertEqual(results[0].proof_status, ProofStatus.PROVED)
        self.assertEqual(results[0].proof_time_seconds, 2.0)

    def test_executor_timeout_maps_to_timeout_status(self) -> None:
        request = _request()

        def executor(incoming: FormalVerificationRequest) -> list[Tier3ClaimResult]:
            raise TimeoutError("timed out")

        results = AristotleFormalVerifier(executor=executor)(request)
        self.assertEqual(results[0].proof_status, ProofStatus.TIMEOUT)
        self.assertEqual(results[0].proof_time_seconds, 30.0)


if __name__ == "__main__":
    unittest.main()
