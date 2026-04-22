from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import _path_setup  # noqa: F401

from deep_gvr.contracts import DeepGvrConfig, ProbeStatus
from deep_gvr.probes import (
    probe_analysis_adapter_families,
    probe_aristotle_transport,
    probe_backend_dispatch,
    probe_mathcode_transport,
    probe_mcp_inheritance,
    probe_model_routing,
    probe_opengauss_transport,
    run_capability_probes,
)
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
                "mathcode_transport",
                "opengauss_transport",
                "session_checkpoint_resume",
                "analysis_adapter_families",
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

    def test_analysis_adapter_probe_reports_family_readiness(self) -> None:
        with patch("deep_gvr.probes._package_available") as package_available:
            package_available.side_effect = lambda name: name not in {"graphix", "pyzx"}
            probe = probe_analysis_adapter_families()

        self.assertEqual(probe.status, ProbeStatus.FALLBACK)
        self.assertFalse(probe.details["families"]["mbqc_graph_state"]["ready"])
        self.assertFalse(probe.details["families"]["zx_rewrite_verification"]["ready"])
        self.assertEqual(probe.details["families"]["mbqc_graph_state"]["supported_backends"], ["local"])
        self.assertEqual(probe.details["families"]["mbqc_graph_state"]["required_extras"], ["quantum_oss"])
        self.assertEqual(probe.details["families"]["dynamics"]["required_extras"], ["analysis", "quantum_oss"])
        self.assertEqual(probe.details["families"]["dynamics"]["recommended_sync_command"], "uv sync --extra analysis --extra quantum_oss")
        self.assertEqual(probe.details["families"]["qec_decoder_benchmark"]["supported_backends"], ["local", "modal", "ssh"])
        self.assertEqual(probe.details["families"]["mbqc_graph_state"]["missing_packages"], ["graphix"])
        self.assertEqual(probe.details["portfolio_required_extras"], ["analysis", "quantum_oss"])
        self.assertEqual(probe.details["full_portfolio_sync_command"], "uv sync --all-extras")
        self.assertEqual(probe.details["ready_family_count"], 7)

    def test_mathcode_transport_probe_reports_ready_for_complete_local_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mathcode_root = Path(tmpdir) / "mathcode"
            (mathcode_root / "AUTOLEAN").mkdir(parents=True, exist_ok=True)
            (mathcode_root / "lean-workspace").mkdir(parents=True, exist_ok=True)
            run_script = mathcode_root / "run"
            run_script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            run_script.chmod(0o755)

            config = DeepGvrConfig()
            config.verification.tier3.mathcode.root = str(mathcode_root)
            config.verification.tier3.mathcode.run_script = str(run_script)
            probe = probe_mathcode_transport(config)

        self.assertEqual(probe.status, ProbeStatus.READY)
        self.assertTrue(probe.details["run_script_executable"])
        self.assertEqual(probe.details["transport_shape"], "bounded_local_cli")
        self.assertFalse(probe.details["lifecycle_support"])
        self.assertEqual(probe.details["generated_artifact_tracking"], "new_or_modified_lean_formalization_only")

    def test_aristotle_transport_probe_surfaces_lifecycle_boundary(self) -> None:
        with patch(
            "deep_gvr.probes.inspect_aristotle_transport",
            return_value=type(
                "AristotleTransportStub",
                (),
                {
                    "hermes_available": True,
                    "aristotle_key_present": True,
                    "hermes_config_path": "/tmp/.hermes/config.yaml",
                    "hermes_config_exists": True,
                    "mcp_server_name": "aristotle",
                    "mcp_server_configured": True,
                    "configured_mcp_servers": ["aristotle"],
                    "ready": True,
                },
            )(),
        ):
            probe = probe_aristotle_transport()

        self.assertEqual(probe.status, ProbeStatus.READY)
        self.assertEqual(probe.details["transport_shape"], "submission_poll_resume")
        self.assertTrue(probe.details["lifecycle_support"])
        self.assertTrue(probe.details["cli_fallback_supported"])

    def test_opengauss_transport_probe_reports_ready_for_installed_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            opengauss_root = Path(tmpdir) / "OpenGauss"
            (opengauss_root / "scripts").mkdir(parents=True, exist_ok=True)
            (opengauss_root / "scripts" / "install.sh").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            launcher = opengauss_root / "gauss"
            launcher.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            launcher.chmod(0o755)

            bin_dir = Path(tmpdir) / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            gauss_binary = bin_dir / "gauss"
            gauss_binary.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            gauss_binary.chmod(0o755)

            config_path = Path(tmpdir) / ".gauss" / "config.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("model:\n  default: test\n", encoding="utf-8")

            probe = probe_opengauss_transport(
                opengauss_root=opengauss_root,
                gauss_binary=gauss_binary,
                gauss_config_path=config_path,
            )

        self.assertEqual(probe.status, ProbeStatus.READY)
        self.assertTrue(probe.details["gauss_available"])
        self.assertTrue(probe.details["gauss_config_exists"])

    def test_backend_dispatch_probe_reports_qec_only_scope(self) -> None:
        with (
            patch("deep_gvr.probes.shutil.which") as which_mock,
            patch("deep_gvr.probes._package_available", return_value=True),
        ):
            which_mock.side_effect = lambda name: f"/usr/local/bin/{name}" if name in {"python3", "modal", "ssh", "scp"} else None
            probe = probe_backend_dispatch(DeepGvrConfig())

        self.assertEqual(probe.details["supported_families"], ["qec_decoder_benchmark"])

    def test_load_capability_evidence_reads_top_level_json_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            evidence_path = Path(tmpdir) / "evidence.json"
            evidence_path.write_text(json.dumps({"per_subagent_model_routing": {"distinct_routes_verified": True}}), encoding="utf-8")
            payload = _load_capability_evidence(evidence_path)
        self.assertTrue(payload["per_subagent_model_routing"]["distinct_routes_verified"])


if __name__ == "__main__":
    unittest.main()
