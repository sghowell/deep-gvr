from __future__ import annotations

import json
import unittest
from pathlib import Path

import yaml

from tests import _path_setup  # noqa: F401

from deep_gvr.contracts import (
    AnalysisResults,
    AnalysisSpec,
    CandidateSolution,
    CapabilityProbeResult,
    CodexAutomationCatalog,
    CodexReviewQaCatalog,
    DeepGvrConfig,
    EvidenceRecord,
    FormalProofHandle,
    FormalProofLifecycle,
    HermesMemorySummary,
    ParallaxEvidenceManifest,
    ProofStatus,
    ReleasePreflightReport,
    ReleasePublicationManifest,
    SessionCheckpoint,
    SessionIndex,
    SimResults,
    SimSpec,
    Tier3ClaimResult,
    VerificationReport,
)
from deep_gvr.evaluation import BenchmarkCase, BenchmarkConsistencyReport, BenchmarkReport
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

    def test_config_round_trip_preserves_mathcode_settings(self) -> None:
        payload = self._load_json("templates/config.template.json")
        payload["verification"]["tier3"]["backend"] = "mathcode"
        payload["verification"]["tier3"]["mathcode"]["root"] = "~/custom-mathcode"
        payload["verification"]["tier3"]["mathcode"]["run_script"] = "~/custom-mathcode/run"

        model = DeepGvrConfig.from_dict(payload)

        self.assertEqual(model.verification.tier3.backend, "mathcode")
        self.assertEqual(model.verification.tier3.mathcode.root, "~/custom-mathcode")
        self.assertEqual(model.verification.tier3.mathcode.run_script, "~/custom-mathcode/run")
        self.assertEqual(model.to_dict(), payload)

    def test_config_accepts_missing_runtime_block_for_backward_compatibility(self) -> None:
        payload = self._load_json("templates/config.template.json")
        del payload["runtime"]

        model = DeepGvrConfig.from_dict(payload)

        self.assertEqual(model.runtime.orchestrator_backend.value, "hermes")
        self.assertEqual(model.to_dict()["runtime"]["orchestrator_backend"], "hermes")

    def test_config_accepts_legacy_tier2_shape_without_modal_or_extended_ssh_fields(self) -> None:
        payload = self._load_json("templates/config.template.json")
        del payload["verification"]["tier2"]["modal"]
        payload["verification"]["tier2"]["ssh"] = {
            "host": "gpu-node",
            "user": "alice",
            "key_path": "~/.ssh/id_ed25519",
        }

        model = DeepGvrConfig.from_dict(payload)

        self.assertEqual(model.verification.tier2.modal.cli_bin, "modal")
        self.assertEqual(model.verification.tier2.modal.stub_path, "adapters/modal_stubs/stim_modal.py")
        self.assertEqual(model.verification.tier2.ssh.host, "gpu-node")
        self.assertEqual(model.verification.tier2.ssh.user, "alice")
        self.assertEqual(model.verification.tier2.ssh.key_path, "~/.ssh/id_ed25519")
        self.assertEqual(model.verification.tier2.ssh.remote_workspace, "")
        self.assertEqual(model.verification.tier2.ssh.python_bin, "python3")

    def test_verification_report_round_trip(self) -> None:
        payload = self._load_json("templates/verification_report.template.json")
        model = VerificationReport.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)

    def test_analysis_spec_round_trip(self) -> None:
        payload = self._load_json("templates/analysis_spec.template.json")
        model = AnalysisSpec.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)

    def test_sim_spec_round_trip(self) -> None:
        payload = self._load_json("templates/sim_spec.template.json")
        model = SimSpec.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)

    def test_sim_spec_normalizes_noise_model_alias_and_caps_requested_budget(self) -> None:
        payload = {
            "simulator": "stim",
            "task": {
                "code": "surface_code",
                "task_type": "rotated_memory_z",
                "distance": [3, 5, 7],
                "rounds_per_distance": "d",
                "noise_model": "uniform_depolarizing",
                "error_rates": [0.001],
                "decoder": "pymatching",
                "shots_per_point": 10_000_000,
            },
            "resources": {
                "timeout_seconds": 600,
                "max_parallel": 12,
            },
        }

        model = SimSpec.from_dict(payload)

        self.assertEqual(model.task.noise_model, "depolarizing")
        self.assertEqual(model.task.shots_per_point, 100_000)
        self.assertEqual(model.resources.max_parallel, 4)

    def test_analysis_results_round_trip(self) -> None:
        payload = self._load_json("templates/analysis_results.template.json")
        model = AnalysisResults.from_dict(payload)
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

    def test_hermes_memory_summary_round_trip(self) -> None:
        payload = self._load_json("templates/hermes_memory_summary.template.json")
        model = HermesMemorySummary.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)

    def test_parallax_manifest_round_trip(self) -> None:
        payload = self._load_json("templates/parallax_manifest.template.json")
        model = ParallaxEvidenceManifest.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)

    def test_release_preflight_round_trip(self) -> None:
        payload = self._load_json("templates/release_preflight.template.json")
        model = ReleasePreflightReport.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)

    def test_codex_automation_catalog_round_trip(self) -> None:
        payload = self._load_json("templates/codex_automation_catalog.template.json")
        model = CodexAutomationCatalog.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)

    def test_release_publication_round_trip(self) -> None:
        payload = self._load_json("templates/release_publication.template.json")
        model = ReleasePublicationManifest.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)

    def test_codex_review_qa_catalog_round_trip(self) -> None:
        payload = self._load_json("templates/codex_review_qa_catalog.template.json")
        model = CodexReviewQaCatalog.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)

    def test_codex_ssh_devbox_catalog_round_trip(self) -> None:
        payload = self._load_json("templates/codex_ssh_devbox_catalog.template.json")
        model = CodexReviewQaCatalog.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)

    def test_codex_subagents_catalog_round_trip(self) -> None:
        payload = self._load_json("templates/codex_subagents_catalog.template.json")
        model = CodexReviewQaCatalog.from_dict(payload)
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

    def test_config_yaml_fixture_matches_json_template(self) -> None:
        schema = self._load_json("schemas/config.schema.json")
        json_fixture = self._load_json("templates/config.template.json")
        yaml_fixture = yaml.safe_load((ROOT / "templates" / "config.template.yaml").read_text(encoding="utf-8"))
        validate(yaml_fixture, schema)
        self.assertEqual(yaml_fixture, json_fixture)

    def test_benchmark_suite_round_trip(self) -> None:
        payload = self._load_json("templates/benchmark_suite.template.json")
        model = [BenchmarkCase.from_dict(item) for item in payload]
        self.assertEqual([item.to_dict() for item in model], payload)

    def test_eval_results_round_trip(self) -> None:
        payload = self._load_json("templates/eval_results.template.json")
        model = BenchmarkReport.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)

    def test_eval_consistency_round_trip(self) -> None:
        payload = self._load_json("templates/eval_consistency.template.json")
        model = BenchmarkConsistencyReport.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)

    def test_benchmark_suite_fixture_validates(self) -> None:
        schema = self._load_json("schemas/benchmark_suite.schema.json")
        fixture = self._load_json("templates/benchmark_suite.template.json")
        validate(fixture, schema)

    def test_analysis_spec_fixture_validates(self) -> None:
        schema = self._load_json("schemas/analysis_spec.schema.json")
        fixture = self._load_json("templates/analysis_spec.template.json")
        validate(fixture, schema)

    def test_analysis_results_fixture_validates(self) -> None:
        schema = self._load_json("schemas/analysis_results.schema.json")
        fixture = self._load_json("templates/analysis_results.template.json")
        validate(fixture, schema)

    def test_eval_results_fixture_validates(self) -> None:
        schema = self._load_json("schemas/eval_results.schema.json")
        fixture = self._load_json("templates/eval_results.template.json")
        validate(fixture, schema)

    def test_eval_consistency_fixture_validates(self) -> None:
        schema = self._load_json("schemas/eval_consistency.schema.json")
        fixture = self._load_json("templates/eval_consistency.template.json")
        validate(fixture, schema)

    def test_codex_automation_catalog_fixture_validates(self) -> None:
        schema = self._load_json("schemas/codex_automation_catalog.schema.json")
        fixture = self._load_json("templates/codex_automation_catalog.template.json")
        validate(fixture, schema)

    def test_codex_review_qa_catalog_fixture_validates(self) -> None:
        schema = self._load_json("schemas/codex_review_qa_catalog.schema.json")
        fixture = self._load_json("templates/codex_review_qa_catalog.template.json")
        validate(fixture, schema)

    def test_codex_ssh_devbox_catalog_fixture_validates(self) -> None:
        schema = self._load_json("schemas/codex_ssh_devbox_catalog.schema.json")
        fixture = self._load_json("templates/codex_ssh_devbox_catalog.template.json")
        validate(fixture, schema)

    def test_codex_subagents_catalog_fixture_validates(self) -> None:
        schema = self._load_json("schemas/codex_subagents_catalog.schema.json")
        fixture = self._load_json("templates/codex_subagents_catalog.template.json")
        validate(fixture, schema)

    def test_session_checkpoint_fixture_validates(self) -> None:
        schema = self._load_json("schemas/session_checkpoint.schema.json")
        fixture = self._load_json("templates/session_checkpoint.template.json")
        validate(fixture, schema)

    def test_hermes_memory_summary_fixture_validates(self) -> None:
        schema = self._load_json("schemas/hermes_memory_summary.schema.json")
        fixture = self._load_json("templates/hermes_memory_summary.template.json")
        validate(fixture, schema)

    def test_parallax_manifest_fixture_validates(self) -> None:
        schema = self._load_json("schemas/parallax_manifest.schema.json")
        fixture = self._load_json("templates/parallax_manifest.template.json")
        validate(fixture, schema)

    def test_release_preflight_fixture_validates(self) -> None:
        schema = self._load_json("schemas/release_preflight.schema.json")
        fixture = self._load_json("templates/release_preflight.template.json")
        validate(fixture, schema)

    def test_release_publication_fixture_validates(self) -> None:
        schema = self._load_json("schemas/release_publication.schema.json")
        fixture = self._load_json("templates/release_publication.template.json")
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

    def test_tier3_claim_defaults_backend_when_missing(self) -> None:
        payload = {
            "claim": "A formal claim",
            "proof_status": "requested",
            "details": "Needs Tier 3.",
        }
        model = Tier3ClaimResult.from_dict(payload)
        self.assertEqual(model.backend, "aristotle")
        self.assertEqual(model.proof_status, ProofStatus.REQUESTED)

    def test_tier3_claim_defaults_requested_status_and_reason_details(self) -> None:
        payload = {
            "claim": "A formal claim",
            "reason": "This theorem should be formalized.",
        }
        model = Tier3ClaimResult.from_dict(payload)
        self.assertEqual(model.backend, "aristotle")
        self.assertEqual(model.proof_status, ProofStatus.REQUESTED)
        self.assertEqual(model.details, "This theorem should be formalized.")

    def test_tier3_claim_accepts_statement_shape(self) -> None:
        payload = {
            "obligation": "majority_decode_correctness",
            "statement": "For all odd d >= 1, majority decoding recovers the codeword.",
            "reason": "Short formal theorem.",
        }
        model = Tier3ClaimResult.from_dict(payload)
        self.assertEqual(model.claim, "For all odd d >= 1, majority decoding recovers the codeword.")
        self.assertEqual(model.proof_status, ProofStatus.REQUESTED)
        self.assertEqual(model.details, "Short formal theorem.")

    def test_formal_proof_lifecycle_round_trip(self) -> None:
        payload = {
            "backend": "aristotle",
            "transport": "aristotle_cli_lifecycle",
            "proof_status": "pending",
            "handles": [
                {
                    "claim": "majority decoding is correct up to (d-1)/2 flips",
                    "backend": "aristotle",
                    "project_id": "123e4567-e89b-12d3-a456-426614174000",
                    "transport": "aristotle_cli_lifecycle",
                    "proof_status": "pending",
                    "submitted_at": "2026-04-07T12:00:00Z",
                    "last_polled_at": "2026-04-07T12:05:00Z",
                    "poll_count": 1,
                    "details": "Result polling is still in progress.",
                }
            ],
            "last_transition": "2026-04-07T12:05:00Z",
            "details": "pending=1 proved=0 error=0",
        }
        model = FormalProofLifecycle.from_dict(payload)
        self.assertEqual(model.to_dict(), payload)
        self.assertEqual(model.proof_status, ProofStatus.PENDING)
        self.assertIsInstance(model.handles[0], FormalProofHandle)


if __name__ == "__main__":
    unittest.main()
