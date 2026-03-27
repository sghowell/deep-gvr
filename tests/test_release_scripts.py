from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests import _path_setup  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]


class ReleaseScriptTests(unittest.TestCase):
    def test_install_script_creates_symlink_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir) / "skills"
            completed = subprocess.run(
                ["bash", str(ROOT / "scripts" / "install.sh"), "--target", str(target_dir)],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            install_path = target_dir / "deep-gvr"
            self.assertTrue(install_path.is_symlink())
            self.assertEqual(install_path.resolve(), ROOT.resolve())

    def test_setup_mcp_script_reports_missing_key(self) -> None:
        env = dict(os.environ)
        env.pop("ARISTOTLE_API_KEY", None)
        completed = subprocess.run(
            ["bash", str(ROOT / "scripts" / "setup_mcp.sh"), "--check"],
            check=False,
            capture_output=True,
            text=True,
            cwd=ROOT,
            env=env,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("ARISTOTLE_API_KEY", completed.stderr)


if __name__ == "__main__":
    unittest.main()
