from __future__ import annotations

import unittest
from pathlib import Path

from tests import _path_setup  # noqa: F401

from deep_gvr.contracts import DeepGvrConfig
from scripts.reassess_plan26 import (
    CapabilityCheckReport,
    build_mcp_check_config,
    build_route_check_config,
    infer_reassessment_conclusion,
)


class Plan26ReassessmentTests(unittest.TestCase):
    def test_build_route_check_config_disables_escalation_and_memory(self) -> None:
        config = build_route_check_config(DeepGvrConfig(), evidence_dir=Path("/tmp/route-check"))
        self.assertEqual(config.loop.max_iterations, 1)
        self.assertFalse(config.loop.alternative_approach)
        self.assertFalse(config.verification.tier2.enabled)
        self.assertFalse(config.verification.tier3.enabled)
        self.assertEqual(config.evidence.directory, "/tmp/route-check")
        self.assertFalse(config.evidence.persist_to_memory)
        self.assertEqual(config.domain.default, "math")

    def test_build_mcp_check_config_enables_selected_backend(self) -> None:
        config = build_mcp_check_config(
            DeepGvrConfig(),
            evidence_dir=Path("/tmp/mcp-check"),
            backend="mathcode",
        )
        self.assertEqual(config.loop.max_iterations, 1)
        self.assertFalse(config.verification.tier2.enabled)
        self.assertTrue(config.verification.tier3.enabled)
        self.assertEqual(config.verification.tier3.backend, "mathcode")
        self.assertEqual(config.evidence.directory, "/tmp/mcp-check")
        self.assertFalse(config.evidence.persist_to_memory)
        self.assertEqual(config.domain.default, "qec")

    def test_infer_reassessment_conclusion_reports_full_closure(self) -> None:
        route = CapabilityCheckReport(
            name="per_subagent_model_routing",
            session_id="route",
            question="q",
            domain="math",
            config_path="/tmp/route.yaml",
            status="completed",
            final_verdict="VERIFIED",
            result_summary="ok",
            error=None,
            evidence_log="/tmp/route.jsonl",
            checkpoint_file="/tmp/route-checkpoint.json",
            artifacts_dir="/tmp/route-artifacts",
            artifacts=[],
            capability_evidence={"per_subagent_model_routing": {"distinct_routes_verified": True}},
        )
        mcp = CapabilityCheckReport(
            name="subagent_mcp_inheritance",
            session_id="mcp",
            question="q",
            domain="qec",
            config_path="/tmp/mcp.yaml",
            status="completed",
            final_verdict="VERIFIED",
            result_summary="ok",
            error=None,
            evidence_log="/tmp/mcp.jsonl",
            checkpoint_file="/tmp/mcp-checkpoint.json",
            artifacts_dir="/tmp/mcp-artifacts",
            artifacts=[],
            capability_evidence={"subagent_mcp_inheritance": {"delegated_mcp_verified": True}},
        )
        conclusion = infer_reassessment_conclusion(route, mcp)
        self.assertEqual(conclusion["plan26_status"], "ready_for_implementation")

    def test_infer_reassessment_conclusion_distinguishes_environment_block(self) -> None:
        route = CapabilityCheckReport(
            name="per_subagent_model_routing",
            session_id="route",
            question="q",
            domain="math",
            config_path="/tmp/route.yaml",
            status="failed",
            final_verdict="CANNOT_VERIFY",
            result_summary="error",
            error="RuntimeError: provider failed",
            evidence_log="/tmp/route.jsonl",
            checkpoint_file="/tmp/route-checkpoint.json",
            artifacts_dir="/tmp/route-artifacts",
            artifacts=[],
            capability_evidence={},
        )
        mcp = CapabilityCheckReport(
            name="subagent_mcp_inheritance",
            session_id="mcp",
            question="q",
            domain="qec",
            config_path="/tmp/mcp.yaml",
            status="failed",
            final_verdict="CANNOT_VERIFY",
            result_summary="error",
            error=None,
            evidence_log="/tmp/mcp.jsonl",
            checkpoint_file="/tmp/mcp-checkpoint.json",
            artifacts_dir="/tmp/mcp-artifacts",
            artifacts=[],
            capability_evidence={},
        )
        conclusion = infer_reassessment_conclusion(route, mcp)
        self.assertEqual(conclusion["plan26_status"], "environment_blocked")
