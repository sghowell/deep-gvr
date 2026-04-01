from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from tests import _path_setup  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]


class ReleaseScriptTests(unittest.TestCase):
    def test_install_script_creates_symlink_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir) / "skills"
            env = dict(os.environ)
            env["HOME"] = tmpdir
            completed = subprocess.run(
                ["bash", str(ROOT / "scripts" / "install.sh"), "--target", str(target_dir)],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            install_path = target_dir / "deep-gvr"
            self.assertTrue(install_path.is_symlink())
            self.assertEqual(install_path.resolve(), ROOT.resolve())
            config_path = Path(tmpdir) / ".hermes" / "deep-gvr" / "config.yaml"
            self.assertTrue(config_path.exists())
            self.assertIn("default", config_path.read_text(encoding="utf-8"))

    def test_skill_manifest_exposes_required_frontmatter(self) -> None:
        skill_path = ROOT / "SKILL.md"
        payload = skill_path.read_text(encoding="utf-8")
        self.assertTrue(payload.startswith("---\n"))
        _, frontmatter, _ = payload.split("---", 2)
        manifest = yaml.safe_load(frontmatter)
        self.assertEqual(manifest["name"], "deep-gvr")
        self.assertTrue(manifest["description"])

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

    def test_setup_mcp_script_passes_with_configured_aristotle_server(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            bin_dir = Path(tmpdir) / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            hermes_path = bin_dir / "hermes"
            hermes_path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            hermes_path.chmod(0o755)
            config_path.write_text(
                "mcp_servers:\n  aristotle:\n    command: uvx\n    args:\n      - aristotle-mcp\n",
                encoding="utf-8",
            )
            env = dict(os.environ)
            env["ARISTOTLE_API_KEY"] = "configured"
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
            completed = subprocess.run(
                [
                    "bash",
                    str(ROOT / "scripts" / "setup_mcp.sh"),
                    "--check",
                    "--config",
                    str(config_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("mcp_servers.aristotle", completed.stdout)

    def test_setup_mcp_script_installs_aristotle_server_in_empty_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            completed = subprocess.run(
                [
                    "bash",
                    str(ROOT / "scripts" / "setup_mcp.sh"),
                    "--install",
                    "--config",
                    str(config_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = config_path.read_text(encoding="utf-8")
            self.assertIn("mcp_servers:", payload)
            self.assertIn('command: "uvx"', payload)
            self.assertIn('ARISTOTLE_API_KEY: "${ARISTOTLE_API_KEY}"', payload)

    def test_setup_mcp_script_install_is_idempotent_and_preserves_existing_servers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "model:",
                        "  default: claude-opus-4-6",
                        "mcp_servers:",
                        "  weather:",
                        "    command: uvx",
                        "    args:",
                        "      - weather-mcp",
                        "timezone: America/Los_Angeles",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            first = subprocess.run(
                [
                    "bash",
                    str(ROOT / "scripts" / "setup_mcp.sh"),
                    "--install",
                    "--config",
                    str(config_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
            second = subprocess.run(
                [
                    "bash",
                    str(ROOT / "scripts" / "setup_mcp.sh"),
                    "--install",
                    "--config",
                    str(config_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)

            payload = config_path.read_text(encoding="utf-8")
            self.assertIn("weather:", payload)
            self.assertIn("timezone: America/Los_Angeles", payload)
            self.assertEqual(payload.count("aristotle:"), 1)
            self.assertIn("mcp_servers:", payload)


if __name__ == "__main__":
    unittest.main()
