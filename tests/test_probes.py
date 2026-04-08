from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import _path_setup  # noqa: F401

from deep_gvr.contracts import DeepGvrConfig, ProbeStatus
from deep_gvr.probes import probe_backend_dispatch, probe_mcp_inheritance, probe_model_routing, run_capability_probes
from scripts.run_capability_probes import _load_capability_evidence


class ProbeTests(unittest.TestCase):
    def test_probe_names_are_stable(self) -> None:
        names = [probe.name for probe in run_capability_probes()]
        self.assertEqual(
            names,
            [
                "per_subagent_model_routing",
                "subagent_mcp_inheritance",
                "aristotle_transport",
                "session_checkpoint_resume",
                "backend_dispatch",
            ],
        )

    def test_probe_status_is_known(self) -> None:
        for probe in run_capability_probes():
            self.assertIn(probe.status, {ProbeStatus.READY, ProbeStatus.FALLBACK, ProbeStatus.BLOCKED})

    def test_model_routing_probe_requires_runtime_evidence_for_ready(self) -> None:
        with patch("deep_gvr.probes.shutil.which", return_value="/usr/local/bin/hermes"):
            probe = probe_model_routing(
                {
                    "distinct_routes_verified": True,
                    "route_pairs": {
                        "generator": {"provider": "openrouter", "model": "claude-sonnet-4"},
                        "verifier": {"provider": "openrouter", "model": "deepseek-r1"},
                    },
                    "evidence_source": "delegated_runtime_test",
                }
            )
        self.assertEqual(probe.status, ProbeStatus.READY)
        self.assertEqual(probe.details["evidence_source"], "delegated_runtime_test")

    def test_mcp_inheritance_probe_requires_runtime_evidence_for_ready(self) -> None:
        with patch("deep_gvr.probes.shutil.which", return_value="/usr/local/bin/hermes"):
            probe = probe_mcp_inheritance(
                {
                    "delegated_mcp_verified": True,
                    "mcp_details": {"tool": "mcp_aristotle_formalize", "claim_count": 1},
                    "evidence_source": "delegated_runtime_test",
                }
            )
        self.assertEqual(probe.status, ProbeStatus.READY)
        self.assertEqual(probe.details["mcp_details"]["tool"], "mcp_aristotle_formalize")

    def test_run_capability_probes_threads_runtime_evidence(self) -> None:
        with patch("deep_gvr.probes.shutil.which", return_value="/usr/local/bin/hermes"):
            probes = run_capability_probes(
                {
                    "per_subagent_model_routing": {"distinct_routes_verified": True},
                    "subagent_mcp_inheritance": {"delegated_mcp_verified": True},
                }
            )
        status_by_name = {probe.name: probe.status for probe in probes}
        self.assertEqual(status_by_name["per_subagent_model_routing"], ProbeStatus.READY)
        self.assertEqual(status_by_name["subagent_mcp_inheritance"], ProbeStatus.READY)

    def test_backend_dispatch_probe_uses_runtime_config_to_report_remote_readiness(self) -> None:
        config = DeepGvrConfig()
        config.verification.tier2.ssh.host = "gpu-node"
        config.verification.tier2.ssh.remote_workspace = "/srv/deep-gvr"
        config.verification.tier2.ssh.python_bin = "python3"

        with (
            patch("deep_gvr.probes.shutil.which") as which_mock,
            patch("deep_gvr.probes._package_available", return_value=True),
        ):
            which_mock.side_effect = lambda name: f"/usr/local/bin/{name}" if name in {"python3", "modal", "ssh", "scp"} else None
            probe = probe_backend_dispatch(config)

        self.assertEqual(probe.status, ProbeStatus.READY)
        self.assertTrue(probe.details["modal_ready"])
        self.assertTrue(probe.details["ssh_ready"])
        self.assertTrue(probe.details["ssh_remote_workspace_configured"])

    def test_load_capability_evidence_reads_top_level_json_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            evidence_path = Path(tmpdir) / "evidence.json"
            evidence_path.write_text(json.dumps({"per_subagent_model_routing": {"distinct_routes_verified": True}}), encoding="utf-8")
            payload = _load_capability_evidence(evidence_path)
        self.assertTrue(payload["per_subagent_model_routing"]["distinct_routes_verified"])


if __name__ == "__main__":
    unittest.main()
