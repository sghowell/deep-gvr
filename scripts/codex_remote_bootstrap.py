#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from deep_gvr.codex_remote_bootstrap import CodexRemoteBootstrapOptions, bootstrap_codex_remote
from deep_gvr.runtime_paths import runtime_home_description


def _print_human_report(report: dict[str, object]) -> None:
    print(f"Codex remote bootstrap for {report['skill_name']} {report['version']}")
    print(f"  overall_status: {report['overall_status']}")
    print(f"  release_surface_ready: {report['release_surface_ready']}")
    print(f"  operator_ready: {report['operator_ready']}")
    print(f"  config_path: {report['config_path']}")
    print(f"  hermes_config_path: {report['hermes_config_path']}")
    print("actions:")
    for action in report["actions"]:
        if not isinstance(action, dict):
            continue
        print(f"- {action['name']}: {action['status']}")
        print(f"  changed: {action['changed']}")
        print(f"  summary: {action['summary']}")
        guidance = action.get("guidance")
        if guidance:
            print(f"  guidance: {guidance}")
    print("preflight checks:")
    preflight = report["preflight"]
    if isinstance(preflight, dict):
        for check in preflight.get("checks", []):
            if not isinstance(check, dict):
                continue
            print(f"- {check['name']}: {check['status']}")
            print(f"  summary: {check['summary']}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap a remote Codex SSH/devbox deep-gvr environment from the current checkout."
    )
    parser.add_argument(
        "--config",
        type=Path,
        help=f"Runtime config path. Default: {runtime_home_description()}/config.yaml",
    )
    parser.add_argument(
        "--config-source",
        type=Path,
        help="Optional config file to sync into the remote runtime home before bootstrap.",
    )
    parser.add_argument(
        "--force-config-sync",
        action="store_true",
        help="Replace the target runtime config from --config-source when the files differ.",
    )
    parser.add_argument(
        "--codex-skills-dir",
        type=Path,
        help="Codex skills directory. Default: ~/.codex/skills",
    )
    parser.add_argument(
        "--hermes-skills-dir",
        type=Path,
        help="Hermes skills directory. Default: ~/.hermes/skills",
    )
    parser.add_argument(
        "--hermes-config",
        type=Path,
        help="Hermes config path. Default: ~/.hermes/config.yaml",
    )
    parser.add_argument(
        "--plugin-root",
        type=Path,
        help="Optional export root for a standalone local Codex plugin marketplace bundle.",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy the Codex skill instead of creating a symlink install.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing Codex skill install or plugin export in place.",
    )
    hermes_group = parser.add_mutually_exclusive_group()
    hermes_group.add_argument(
        "--skip-hermes-install",
        action="store_true",
        help="Do not refresh the Hermes surface during bootstrap, even if the config would otherwise use it.",
    )
    hermes_group.add_argument(
        "--install-hermes",
        action="store_true",
        help="Refresh the Hermes surface during bootstrap even if the selected remote path would not require it.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human-readable text.")
    parser.add_argument(
        "--operator",
        action="store_true",
        help="Exit non-zero unless the remote Codex operator path is fully ready after bootstrap.",
    )
    args = parser.parse_args()

    skip_hermes_install: bool | None = None
    if args.skip_hermes_install:
        skip_hermes_install = True
    elif args.install_hermes:
        skip_hermes_install = False

    report = bootstrap_codex_remote(
        CodexRemoteBootstrapOptions(
            config_path=args.config,
            config_source=args.config_source,
            force_config_sync=args.force_config_sync,
            codex_skills_dir=args.codex_skills_dir,
            hermes_skills_dir=args.hermes_skills_dir,
            hermes_config_path=args.hermes_config,
            plugin_root=args.plugin_root,
            copy_install=args.copy,
            force_install=args.force,
            skip_hermes_install=skip_hermes_install,
        )
    ).to_dict()

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_human_report(report)

    if args.operator:
        return 0 if bool(report["operator_ready"]) else 1
    return 0 if bool(report["release_surface_ready"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
