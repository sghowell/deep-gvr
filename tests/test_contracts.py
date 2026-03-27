from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests import _path_setup  # noqa: F401

from deep_gvr.contracts import (
    CandidateSolution,
    CapabilityProbeResult,
    DeepGvrConfig,
    EvidenceRecord,
    ProofStatus,
    SessionCheckpoint,
    SessionIndex,
    SimResults,
    SimSpec,
    Tier3ClaimResult,
    VerificationReport,
)
from deep_gvr.json_schema import validate

ROOT = Path(__file__).resolve().parents[1]


class ContractRoundTripTests(unittest.TestCase):
    def _load_json(self, relative_path: str) -> dict:
        return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))

    def test_candidate_solution_round_trip(self) -> None:
        payload = self._load_json("templates/candidate_solution.template.json")
        model = CandidateSolution.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)

    def test_config_round_trip(self) -> None:
        payload = self._load_json("templates/config.template.json")
        model = DeepGvrConfig.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)

    def test_verification_report_round_trip(self) -> None:
        payload = self._load_json("templates/verification_report.template.json")
        model = VerificationReport.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)

    def test_sim_spec_round_trip(self) -> None:
        payload = self._load_json("templates/sim_spec.template.json")
        model = SimSpec.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)

    def test_sim_results_round_trip(self) -> None:
        payload = self._load_json("templates/sim_results.template.json")
        model = SimResults.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)

    def test_evidence_round_trip(self) -> None:
        payload = self._load_json("templates/evidence_record.template.json")
        model = EvidenceRecord.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)

    def test_session_index_round_trip(self) -> None:
        payload = self._load_json("templates/session_index.template.json")
        model = SessionIndex.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)

    def test_session_checkpoint_round_trip(self) -> None:
        payload = self._load_json("templates/session_checkpoint.template.json")
        model = SessionCheckpoint.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)

    def test_capability_probe_round_trip(self) -> None:
        payload = self._load_json("templates/capability_probe.template.json")
        model = CapabilityProbeResult.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)

    def test_config_fixture_validates(self) -> None:
        schema = self._load_json("schemas/config.schema.json")
        fixture = self._load_json("templates/config.template.json")
        validate(fixture, schema)

    def test_session_checkpoint_fixture_validates(self) -> None:
        schema = self._load_json("schemas/session_checkpoint.schema.json")
        fixture = self._load_json("templates/session_checkpoint.template.json")
        validate(fixture, schema)

    def test_tier3_claim_round_trip(self) -> None:
        payload = {
            "claim": "A formal claim",
            "backend": "aristotle",
            "proof_status": "proved",
            "details": "Proof succeeded.",
            "lean_code": "theorem example : True := by trivial",
            "proof_time_seconds": 1.5,
        }
        model = Tier3ClaimResult.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)
        self.assertEqual(model.proof_status, ProofStatus.PROVED)


if __name__ == "__main__":
    unittest.main()
