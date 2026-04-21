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
from deep_gvr.codex_automations import codex_automation_surface_errors
from deep_gvr.codex_review_qa import codex_review_qa_surface_errors
from deep_gvr.codex_subagents import codex_subagent_surface_errors
from deep_gvr.codex_ssh_devbox import codex_ssh_devbox_surface_errors
from deep_gvr.release_surface import (
    codex_plugin_surface_errors,
    collect_codex_preflight,
    collect_release_preflight,
    expected_release_tag,
    project_version,
    publication_manifest_errors,
    release_metadata_errors,
    release_notes_for_version,
)

ROOT = Path(__file__).resolve().parents[1]


class ReleaseScriptTests(unittest.TestCase):
    def test_install_script_creates_indexable_symlink_install(self) -> None:
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
            self.assertTrue(install_path.is_dir())
            self.assertFalse(install_path.is_symlink())
            self.assertTrue((install_path / "SKILL.md").is_symlink())
            self.assertEqual((install_path / "SKILL.md").resolve(), (ROOT / "SKILL.md").resolve())
            discovered = [path for path in install_path.rglob("SKILL.md")]
            self.assertIn(install_path / "SKILL.md", discovered)
            config_path = Path(tmpdir) / ".hermes" / "deep-gvr" / "config.yaml"
            self.assertTrue(config_path.exists())
            self.assertIn("default", config_path.read_text(encoding="utf-8"))

    def test_install_script_uses_hermes_home_override_for_default_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            hermes_home = Path(tmpdir) / "custom-hermes-home"
            env = dict(os.environ)
            env["HOME"] = tmpdir
            env["HERMES_HOME"] = str(hermes_home)
            completed = subprocess.run(
                ["bash", str(ROOT / "scripts" / "install.sh")],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((hermes_home / "skills" / "deep-gvr" / "SKILL.md").exists())
            self.assertTrue((hermes_home / "deep-gvr" / "config.yaml").exists())

    def test_install_codex_script_installs_codex_skill_and_underlying_hermes_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            codex_home = Path(tmpdir) / "custom-codex-home"
            env = dict(os.environ)
            env["HOME"] = tmpdir
            env["CODEX_HOME"] = str(codex_home)
            completed = subprocess.run(
                ["bash", str(ROOT / "scripts" / "install_codex.sh")],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((codex_home / "skills" / "deep-gvr" / "SKILL.md").exists())
            self.assertTrue((Path(tmpdir) / ".hermes" / "skills" / "deep-gvr" / "SKILL.md").exists())
            self.assertTrue((Path(tmpdir) / ".hermes" / "deep-gvr" / "config.yaml").exists())

    def test_install_codex_script_supports_skip_hermes_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            codex_home = Path(tmpdir) / "custom-codex-home"
            env = dict(os.environ)
            env["HOME"] = tmpdir
            env["CODEX_HOME"] = str(codex_home)
            completed = subprocess.run(
                ["bash", str(ROOT / "scripts" / "install_codex.sh"), "--skip-hermes-install"],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((codex_home / "skills" / "deep-gvr" / "SKILL.md").exists())
            self.assertFalse((Path(tmpdir) / ".hermes" / "skills" / "deep-gvr" / "SKILL.md").exists())

    def test_install_codex_script_exports_plugin_marketplace_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_root = Path(tmpdir) / "codex-plugin-root"
            env = dict(os.environ)
            env["HOME"] = tmpdir
            completed = subprocess.run(
                [
                    "bash",
                    str(ROOT / "scripts" / "install_codex.sh"),
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
            self.assertTrue((plugin_root / "plugins" / "deep-gvr" / ".codex-plugin" / "plugin.json").exists())
            self.assertTrue((plugin_root / "plugins" / "deep-gvr" / "skills" / "deep-gvr" / "SKILL.md").exists())
            self.assertTrue((plugin_root / ".agents" / "plugins" / "marketplace.json").exists())

    def test_install_codex_script_exports_automation_bundle_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            automation_root = Path(tmpdir) / "codex-automation-root"
            env = dict(os.environ)
            env["HOME"] = tmpdir
            completed = subprocess.run(
                [
                    "bash",
                    str(ROOT / "scripts" / "install_codex.sh"),
                    "--automation-root",
                    str(automation_root),
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((automation_root / "catalog.json").exists())
            self.assertTrue((automation_root / "automations" / "benchmark_subset_sweep" / "automation.toml").exists())
            rendered = (automation_root / "automations" / "benchmark_subset_sweep" / "automation.toml").read_text(
                encoding="utf-8"
            )
            self.assertNotIn("__DEEP_GVR_REPO_ROOT__", rendered)
            self.assertIn(str(ROOT), rendered)

    def test_install_codex_script_exports_review_qa_bundle_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            review_root = Path(tmpdir) / "codex-review-qa-root"
            env = dict(os.environ)
            env["HOME"] = tmpdir
            completed = subprocess.run(
                [
                    "bash",
                    str(ROOT / "scripts" / "install_codex.sh"),
                    "--review-qa-root",
                    str(review_root),
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((review_root / "catalog.json").exists())
            self.assertTrue((review_root / "prompts" / "pull_request_review.md").exists())
            rendered = (review_root / "prompts" / "pull_request_review.md").read_text(encoding="utf-8")
            self.assertNotIn("__DEEP_GVR_REPO_ROOT__", rendered)
            self.assertIn(str(ROOT), rendered)

    def test_install_codex_script_exports_subagent_bundle_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            subagents_root = Path(tmpdir) / "codex-subagents-root"
            env = dict(os.environ)
            env["HOME"] = tmpdir
            completed = subprocess.run(
                [
                    "bash",
                    str(ROOT / "scripts" / "install_codex.sh"),
                    "--subagents-root",
                    str(subagents_root),
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((subagents_root / "catalog.json").exists())
            self.assertTrue((subagents_root / "prompts" / "parallel_validator_fanout.md").exists())
            rendered = (subagents_root / "prompts" / "parallel_validator_fanout.md").read_text(encoding="utf-8")
            self.assertNotIn("__DEEP_GVR_REPO_ROOT__", rendered)
            self.assertIn(str(ROOT), rendered)

    def test_install_codex_script_exports_ssh_devbox_bundle_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ssh_devbox_root = Path(tmpdir) / "codex-ssh-devbox-root"
            env = dict(os.environ)
            env["HOME"] = tmpdir
            completed = subprocess.run(
                [
                    "bash",
                    str(ROOT / "scripts" / "install_codex.sh"),
                    "--ssh-devbox-root",
                    str(ssh_devbox_root),
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((ssh_devbox_root / "catalog.json").exists())
            self.assertTrue((ssh_devbox_root / "prompts" / "remote_validator_run.md").exists())
            rendered = (ssh_devbox_root / "prompts" / "remote_validator_run.md").read_text(encoding="utf-8")
            self.assertNotIn("__DEEP_GVR_REPO_ROOT__", rendered)
            self.assertIn(str(ROOT), rendered)

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

    def test_release_preflight_reports_structural_release_surface_after_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir) / "skills"
            env = dict(os.environ)
            env["HOME"] = tmpdir
            install = subprocess.run(
                ["bash", str(ROOT / "scripts" / "install.sh"), "--target", str(target_dir)],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
            )
            self.assertEqual(install.returncode, 0, install.stderr)

            completed = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "release_preflight.py"),
                    "--json",
                    "--skills-dir",
                    str(target_dir),
                    "--config",
                    str(Path(tmpdir) / ".hermes" / "deep-gvr" / "config.yaml"),
                    "--hermes-config",
                    str(Path(tmpdir) / ".hermes" / "config.yaml"),
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn('"release_surface_ready": true', completed.stdout)
            self.assertIn('"operator_ready": false', completed.stdout)

    def test_codex_preflight_reports_structural_surface_after_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            codex_home = Path(tmpdir) / "codex-home"
            codex_target_dir = codex_home / "skills"
            hermes_target_dir = Path(tmpdir) / ".hermes" / "skills"
            bin_dir = Path(tmpdir) / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            for binary_name in ("codex", "hermes"):
                binary_path = bin_dir / binary_name
                binary_path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
                binary_path.chmod(0o755)

            env = dict(os.environ)
            env["HOME"] = tmpdir
            env["CODEX_HOME"] = str(codex_home)
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
            install = subprocess.run(
                ["bash", str(ROOT / "scripts" / "install_codex.sh")],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
            )
            self.assertEqual(install.returncode, 0, install.stderr)

            completed = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "codex_preflight.py"),
                    "--json",
                    "--codex-skills-dir",
                    str(codex_target_dir),
                    "--hermes-skills-dir",
                    str(hermes_target_dir),
                    "--config",
                    str(Path(tmpdir) / ".hermes" / "deep-gvr" / "config.yaml"),
                    "--hermes-config",
                    str(Path(tmpdir) / ".hermes" / "config.yaml"),
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn('"release_surface_ready": true', completed.stdout)
            self.assertIn('"operator_ready": false', completed.stdout)

    def test_collect_codex_preflight_reports_ready_mathcode_transport_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            codex_home = Path(tmpdir) / "codex-home"
            codex_target_dir = codex_home / "skills"
            hermes_target_dir = Path(tmpdir) / ".hermes" / "skills"
            mathcode_root = Path(tmpdir) / "mathcode"
            (mathcode_root / "AUTOLEAN").mkdir(parents=True, exist_ok=True)
            (mathcode_root / "lean-workspace").mkdir(parents=True, exist_ok=True)
            run_script = mathcode_root / "run"
            run_script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            run_script.chmod(0o755)

            bin_dir = Path(tmpdir) / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            for binary_name in ("codex", "hermes"):
                binary_path = bin_dir / binary_name
                binary_path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
                binary_path.chmod(0o755)

            env = dict(os.environ)
            env["HOME"] = tmpdir
            env["CODEX_HOME"] = str(codex_home)
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
            install = subprocess.run(
                ["bash", str(ROOT / "scripts" / "install_codex.sh")],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
            )
            self.assertEqual(install.returncode, 0, install.stderr)

            config_path = Path(tmpdir) / ".hermes" / "deep-gvr" / "config.yaml"
            payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            payload["verification"]["tier3"]["enabled"] = True
            payload["verification"]["tier3"]["backend"] = "mathcode"
            payload["verification"]["tier3"]["mathcode"]["root"] = str(mathcode_root)
            payload["verification"]["tier3"]["mathcode"]["run_script"] = str(run_script)
            config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

            prior_path = os.environ.get("PATH")
            os.environ["PATH"] = env["PATH"]
            try:
                report = collect_codex_preflight(
                    config_path=config_path,
                    codex_skills_dir=codex_target_dir,
                    hermes_skills_dir=hermes_target_dir,
                    hermes_config_path=Path(tmpdir) / ".hermes" / "config.yaml",
                )
            finally:
                if prior_path is None:
                    del os.environ["PATH"]
                else:
                    os.environ["PATH"] = prior_path

        tier3_check = next(check for check in report.checks if check.name == "tier3_transport")
        self.assertEqual(tier3_check.status.value, "ready")
        self.assertIn("MathCode", tier3_check.summary)

    def test_collect_codex_preflight_reports_ready_ssh_devbox_backend_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            codex_home = Path(tmpdir) / "codex-home"
            codex_target_dir = codex_home / "skills"
            hermes_target_dir = Path(tmpdir) / ".hermes" / "skills"
            bin_dir = Path(tmpdir) / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            for binary_name in ("codex", "hermes", "ssh", "scp"):
                binary_path = bin_dir / binary_name
                binary_path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
                binary_path.chmod(0o755)

            env = dict(os.environ)
            env["HOME"] = tmpdir
            env["CODEX_HOME"] = str(codex_home)
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
            install = subprocess.run(
                ["bash", str(ROOT / "scripts" / "install_codex.sh")],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
            )
            self.assertEqual(install.returncode, 0, install.stderr)

            config_path = Path(tmpdir) / ".hermes" / "deep-gvr" / "config.yaml"
            payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            payload["verification"]["tier2"]["ssh"]["host"] = "validator-node"
            payload["verification"]["tier2"]["ssh"]["remote_workspace"] = "/srv/deep-gvr"
            payload["verification"]["tier2"]["ssh"]["python_bin"] = "python3"
            config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

            report = collect_codex_preflight(
                config_path=config_path,
                codex_skills_dir=codex_target_dir,
                hermes_skills_dir=hermes_target_dir,
                hermes_config_path=Path(tmpdir) / ".hermes" / "config.yaml",
                ssh_devbox=True,
            )

        remote_check = next(check for check in report.checks if check.name == "ssh_devbox_backend")
        self.assertEqual(remote_check.status.value, "ready")
        self.assertTrue(remote_check.details["ssh_ready"])

    def test_collect_codex_preflight_does_not_require_hermes_for_codex_backend(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            codex_home = Path(tmpdir) / "codex-home"
            codex_target_dir = codex_home / "skills"
            hermes_target_dir = Path(tmpdir) / ".hermes" / "skills"
            runtime_home = Path(tmpdir) / "deep-gvr-runtime"
            config_path = runtime_home / "config.yaml"
            evidence_dir = runtime_home / "sessions"
            bin_dir = Path(tmpdir) / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            codex_path = bin_dir / "codex"
            codex_path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            codex_path.chmod(0o755)

            env = dict(os.environ)
            env["HOME"] = tmpdir
            env["CODEX_HOME"] = str(codex_home)
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
            install = subprocess.run(
                ["bash", str(ROOT / "scripts" / "install_codex.sh"), "--skip-hermes-install"],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
            )
            self.assertEqual(install.returncode, 0, install.stderr)

            payload = DeepGvrConfig().to_dict()
            payload["runtime"]["orchestrator_backend"] = "codex_local"
            payload["evidence"]["directory"] = str(evidence_dir)
            for role in ("orchestrator", "generator", "verifier", "reviser"):
                payload["models"][role]["provider"] = "default"
                payload["models"][role]["model"] = ""
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

            report = collect_codex_preflight(
                config_path=config_path,
                codex_skills_dir=codex_target_dir,
                hermes_skills_dir=hermes_target_dir,
                hermes_config_path=Path(tmpdir) / ".hermes" / "config.yaml",
            )

        checks = {check.name: check for check in report.checks}
        self.assertEqual(checks["orchestrator_backend"].status.value, "ready")
        self.assertEqual(checks["codex_cli"].status.value, "ready")
        self.assertEqual(checks["skill_install"].status.value, "ready")
        self.assertIn("not required", checks["skill_install"].summary)
        self.assertEqual(checks["hermes_cli"].status.value, "ready")
        self.assertIn("not required", checks["hermes_cli"].summary)

    def test_collect_release_preflight_uses_codex_backend_requirements_when_selected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_home = Path(tmpdir) / "deep-gvr-runtime"
            config_path = runtime_home / "config.yaml"
            evidence_dir = runtime_home / "sessions"
            bin_dir = Path(tmpdir) / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            codex_path = bin_dir / "codex"
            codex_path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            codex_path.chmod(0o755)

            env = dict(os.environ)
            env["HOME"] = tmpdir
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

            payload = DeepGvrConfig().to_dict()
            payload["runtime"]["orchestrator_backend"] = "codex_local"
            payload["evidence"]["directory"] = str(evidence_dir)
            for role in ("orchestrator", "generator", "verifier", "reviser"):
                payload["models"][role]["provider"] = "default"
                payload["models"][role]["model"] = ""
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

            prior_path = os.environ.get("PATH")
            os.environ["PATH"] = env["PATH"]
            try:
                report = collect_release_preflight(
                    config_path=config_path,
                    skills_dir=Path(tmpdir) / ".hermes" / "skills",
                    hermes_config_path=Path(tmpdir) / ".hermes" / "config.yaml",
                )
            finally:
                if prior_path is None:
                    del os.environ["PATH"]
                else:
                    os.environ["PATH"] = prior_path

        checks = {check.name: check for check in report.checks}
        self.assertEqual(checks["orchestrator_backend"].status.value, "ready")
        self.assertEqual(checks["codex_cli"].status.value, "ready")
        self.assertEqual(checks["skill_install"].status.value, "ready")
        self.assertIn("not required", checks["skill_install"].summary)
        self.assertEqual(checks["hermes_cli"].status.value, "ready")
        self.assertIn("not required", checks["hermes_cli"].summary)

    def test_release_metadata_errors_are_empty_for_repo(self) -> None:
        self.assertEqual(release_metadata_errors(ROOT), [])

    def test_release_notes_for_current_version_are_non_empty(self) -> None:
        notes = release_notes_for_version(project_version(ROOT), ROOT)
        self.assertIn("GitHub Releases", notes)

    def test_check_release_version_script_accepts_current_tag(self) -> None:
        completed = subprocess.run(
            [
                "python3",
                str(ROOT / "scripts" / "check_release_version.py"),
                "--tag",
                expected_release_tag(ROOT),
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["tag"], expected_release_tag(ROOT))

    def test_render_release_notes_script_writes_requested_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "release-notes.md"
            version = project_version(ROOT)
            completed = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "render_release_notes.py"),
                    "--version",
                    version,
                    "--output",
                    str(output_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(output_path.exists())
            self.assertIn("GitHub Releases", output_path.read_text(encoding="utf-8"))

    def test_release_preflight_operator_mode_requires_configured_provider_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir) / "skills"
            bin_dir = Path(tmpdir) / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            hermes_path = bin_dir / "hermes"
            hermes_path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            hermes_path.chmod(0o755)

            env = dict(os.environ)
            env["HOME"] = tmpdir
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
            install = subprocess.run(
                ["bash", str(ROOT / "scripts" / "install.sh"), "--target", str(target_dir)],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
            )
            self.assertEqual(install.returncode, 0, install.stderr)

            completed = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "release_preflight.py"),
                    "--operator",
                    "--json",
                    "--skills-dir",
                    str(target_dir),
                    "--config",
                    str(Path(tmpdir) / ".hermes" / "deep-gvr" / "config.yaml"),
                    "--hermes-config",
                    str(Path(tmpdir) / ".hermes" / "config.yaml"),
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn('"name": "provider_credentials"', completed.stdout)
            self.assertIn('"status": "blocked"', completed.stdout)

    def test_publication_manifest_matches_repo_metadata(self) -> None:
        self.assertEqual(publication_manifest_errors(ROOT), [])

    def test_codex_plugin_surface_matches_repo_metadata(self) -> None:
        self.assertEqual(codex_plugin_surface_errors(ROOT), [])

    def test_codex_automation_surface_matches_repo_metadata(self) -> None:
        self.assertEqual(codex_automation_surface_errors(ROOT), [])

    def test_codex_review_qa_surface_matches_repo_metadata(self) -> None:
        self.assertEqual(codex_review_qa_surface_errors(ROOT), [])

    def test_codex_subagent_surface_matches_repo_metadata(self) -> None:
        self.assertEqual(codex_subagent_surface_errors(ROOT), [])

    def test_codex_ssh_devbox_surface_matches_repo_metadata(self) -> None:
        self.assertEqual(codex_ssh_devbox_surface_errors(ROOT), [])

    def test_release_preflight_uses_mathcode_transport_when_selected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir) / "skills"
            hermes_home = Path(tmpdir) / ".hermes"
            mathcode_root = Path(tmpdir) / "mathcode"
            (mathcode_root / "AUTOLEAN").mkdir(parents=True, exist_ok=True)
            (mathcode_root / "lean-workspace").mkdir(parents=True, exist_ok=True)
            run_script = mathcode_root / "run"
            run_script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            run_script.chmod(0o755)

            env = dict(os.environ)
            env["HOME"] = tmpdir
            install = subprocess.run(
                ["bash", str(ROOT / "scripts" / "install.sh"), "--target", str(target_dir)],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
            )
            self.assertEqual(install.returncode, 0, install.stderr)

            config_path = hermes_home / "deep-gvr" / "config.yaml"
            payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            payload["verification"]["tier3"]["enabled"] = True
            payload["verification"]["tier3"]["backend"] = "mathcode"
            payload["verification"]["tier3"]["mathcode"]["root"] = str(mathcode_root)
            payload["verification"]["tier3"]["mathcode"]["run_script"] = str(run_script)
            config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

            report = collect_release_preflight(
                config_path=config_path,
                skills_dir=target_dir,
                hermes_config_path=hermes_home / "config.yaml",
            )

        tier3_check = next(check for check in report.checks if check.name == "tier3_transport")
        self.assertEqual(tier3_check.status.value, "ready")
        self.assertIn("MathCode", tier3_check.summary)

    def test_release_preflight_blocks_opengauss_backend_with_diagnostics_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            payload = yaml.safe_load((ROOT / "templates" / "config.template.yaml").read_text(encoding="utf-8"))
            payload["verification"]["tier3"]["enabled"] = True
            payload["verification"]["tier3"]["backend"] = "opengauss"
            config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

            report = collect_release_preflight(
                config_path=config_path,
                skills_dir=Path(tmpdir) / "skills",
                hermes_config_path=Path(tmpdir) / "hermes-config.yaml",
            )

        tier3_check = next(check for check in report.checks if check.name == "tier3_transport")
        self.assertEqual(tier3_check.status.value, "blocked")
        self.assertIn("opengauss", tier3_check.summary)
        self.assertIn("diagnose_opengauss.py", tier3_check.guidance)

    def test_opengauss_diagnostics_script_reports_ready_for_fake_install(self) -> None:
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

            gauss_config = Path(tmpdir) / ".gauss" / "config.yaml"
            gauss_config.parent.mkdir(parents=True, exist_ok=True)
            gauss_config.write_text("model:\n  default: test\n", encoding="utf-8")

            completed = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "diagnose_opengauss.py"),
                    "--json",
                    "--skip-doctor",
                    "--skip-morph",
                    "--opengauss-root",
                    str(opengauss_root),
                    "--gauss-binary",
                    str(gauss_binary),
                    "--gauss-config",
                    str(gauss_config),
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('"overall_status": "ready"', completed.stdout)
        self.assertIn('"gauss_available": true', completed.stdout)


if __name__ == "__main__":
    unittest.main()
