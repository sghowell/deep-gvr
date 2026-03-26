from __future__ import annotations

import unittest

from tests import _path_setup  # noqa: F401

from deep_gvr.contracts import ProbeStatus
from deep_gvr.probes import run_capability_probes


class ProbeTests(unittest.TestCase):
    def test_probe_names_are_stable(self) -> None:
        names = [probe.name for probe in run_capability_probes()]
        self.assertEqual(
            names,
            [
                "per_subagent_model_routing",
                "subagent_mcp_inheritance",
                "session_checkpoint_resume",
                "backend_dispatch",
            ],
        )

    def test_probe_status_is_known(self) -> None:
        for probe in run_capability_probes():
            self.assertIn(probe.status, {ProbeStatus.READY, ProbeStatus.FALLBACK, ProbeStatus.BLOCKED})


if __name__ == "__main__":
    unittest.main()
