from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from tests import _path_setup  # noqa: F401

from deep_gvr.contracts import DeepGvrConfig

ROOT = Path(__file__).resolve().parents[1]


class CodexRemoteBootstrapTests(unittest.TestCase):
    def _base_payload(self) -> dict[str, object]:
        payload = DeepGvrConfig().to_dict()
        for role in ("orchestrator", "generator", "verifier", "reviser"):
            payload["models"][role]["provider"] = "default"
            payload["models"][role]["model"] = ""
        return payload

    def _write_success_bin(self, directory: Path, name: str) -> None:
        path = directory / name
        path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        path.chmod(0o755)

    def test_codex_remote_bootstrap_syncs_config_installs_codex_surface_and_exports_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            runtime_home = tmp / "deep-gvr-runtime"
            config_path = runtime_home / "config.yaml"
            config_source = tmp / "remote-source-config.yaml"
            codex_home = tmp / "codex-home"
            codex_skills_dir = codex_home / "skills"
            hermes_skills_dir = tmp / ".hermes" / "skills"
            hermes_config_path = tmp / ".hermes" / "config.yaml"
            plugin_root = tmp / "plugin-root"

            payload = self._base_payload()
            payload["verification"]["tier2"]["default_backend"] = "ssh"
            payload["verification"]["tier2"]["ssh"]["host"] = "validator-node"
            payload["verification"]["tier2"]["ssh"]["remote_workspace"] = "/srv/deep-gvr"
            payload["verification"]["tier2"]["ssh"]["python_bin"] = "python3"
            config_source.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

            bin_dir = tmp / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            for binary_name in ("codex", "ssh", "scp"):
                self._write_success_bin(bin_dir, binary_name)

            env = dict(os.environ)
            env["HOME"] = tmpdir
            env["CODEX_HOME"] = str(codex_home)
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

            completed = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "codex_remote_bootstrap.py"),
                    "--json",
                    "--config",
                    str(config_path),
                    "--config-source",
                    str(config_source),
                    "--codex-skills-dir",
                    str(codex_skills_dir),
                    "--hermes-skills-dir",
                    str(hermes_skills_dir),
                    "--hermes-config",
                    str(hermes_config_path),
                    "--plugin-root",
                    str(plugin_root),
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(completed.stdout)
            self.assertTrue(report["release_surface_ready"])
            config_action = next(action for action in report["actions"] if action["name"] == "config_sync")
            install_action = next(action for action in report["actions"] if action["name"] == "codex_surface_install")
            self.assertEqual(config_action["status"], "ready")
            self.assertEqual(config_action["details"]["orchestrator_backend"], "codex_local")
            self.assertEqual(install_action["status"], "ready")
            self.assertTrue(install_action["details"]["skip_hermes_install"])

            synced_payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            self.assertEqual(synced_payload["runtime"]["orchestrator_backend"], "codex_local")
            self.assertEqual(synced_payload["verification"]["tier2"]["default_backend"], "ssh")
            self.assertTrue((codex_skills_dir / "deep-gvr" / "SKILL.md").exists())
            self.assertTrue((plugin_root / "plugins" / "deep-gvr" / ".codex-plugin" / "plugin.json").exists())
            self.assertFalse((hermes_skills_dir / "deep-gvr" / "SKILL.md").exists())

    def test_codex_remote_bootstrap_surfaces_config_source_conflict_without_overwriting_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            runtime_home = tmp / "deep-gvr-runtime"
            config_path = runtime_home / "config.yaml"
            config_source = tmp / "remote-source-config.yaml"
            codex_home = tmp / "codex-home"
            codex_skills_dir = codex_home / "skills"
            hermes_skills_dir = tmp / ".hermes" / "skills"
            hermes_config_path = tmp / ".hermes" / "config.yaml"

            target_payload = self._base_payload()
            target_payload["verification"]["tier2"]["default_backend"] = "local"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(yaml.safe_dump(target_payload, sort_keys=False), encoding="utf-8")

            source_payload = self._base_payload()
            source_payload["verification"]["tier2"]["default_backend"] = "ssh"
            source_payload["verification"]["tier2"]["ssh"]["host"] = "validator-node"
            source_payload["verification"]["tier2"]["ssh"]["remote_workspace"] = "/srv/deep-gvr"
            source_payload["verification"]["tier2"]["ssh"]["python_bin"] = "python3"
            config_source.write_text(yaml.safe_dump(source_payload, sort_keys=False), encoding="utf-8")

            bin_dir = tmp / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            self._write_success_bin(bin_dir, "codex")

            env = dict(os.environ)
            env["HOME"] = tmpdir
            env["CODEX_HOME"] = str(codex_home)
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

            completed = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "codex_remote_bootstrap.py"),
                    "--json",
                    "--config",
                    str(config_path),
                    "--config-source",
                    str(config_source),
                    "--codex-skills-dir",
                    str(codex_skills_dir),
                    "--hermes-skills-dir",
                    str(hermes_skills_dir),
                    "--hermes-config",
                    str(hermes_config_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(completed.stdout)
            config_action = next(action for action in report["actions"] if action["name"] == "config_sync")
            self.assertEqual(config_action["status"], "attention")
            self.assertTrue(config_action["details"]["source_conflict"])

            synced_payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            self.assertEqual(synced_payload["verification"]["tier2"]["default_backend"], "local")
            self.assertEqual(synced_payload["runtime"]["orchestrator_backend"], "codex_local")

    def test_codex_remote_bootstrap_script_help(self) -> None:
        completed = subprocess.run(
            ["python3", str(ROOT / "scripts" / "codex_remote_bootstrap.py"), "--help"],
            check=False,
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--config-source", completed.stdout)
        self.assertIn("--plugin-root", completed.stdout)


if __name__ == "__main__":
    unittest.main()
