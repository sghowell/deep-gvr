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

from deep_gvr.release_surface import collect_codex_preflight


def _print_human_report(report: dict[str, object]) -> None:
    print(f"Codex preflight for {report['skill_name']} {report['version']}")
    print(f"  overall_status: {report['overall_status']}")
    print(f"  release_surface_ready: {report['release_surface_ready']}")
    print(f"  operator_ready: {report['operator_ready']}")
    print(f"  config_path: {report['config_path']}")
    print(f"  hermes_config_path: {report['hermes_config_path']}")
    print(f"  publication_manifest_path: {report['publication_manifest_path']}")
    for check in report["checks"]:
        if not isinstance(check, dict):
            continue
        print(f"- {check['name']}: {check['status']}")
        print(f"  summary: {check['summary']}")
        guidance = check.get("guidance")
        if guidance:
            print(f"  guidance: {guidance}")
        details = check.get("details")
        if details:
            print(f"  details: {json.dumps(details, sort_keys=True)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deep-gvr Codex-local preflight checks")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human-readable text")
    parser.add_argument(
        "--operator",
        action="store_true",
        help="Exit non-zero unless the configured Codex-local operator runtime is fully ready.",
    )
    parser.add_argument(
        "--ssh-devbox",
        action="store_true",
        help="Include the Codex SSH/devbox remote-validator readiness path in the report.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Runtime config path. Default: ~/.hermes/deep-gvr/config.yaml",
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
    args = parser.parse_args()

    report = collect_codex_preflight(
        config_path=args.config,
        codex_skills_dir=args.codex_skills_dir,
        hermes_skills_dir=args.hermes_skills_dir,
        hermes_config_path=args.hermes_config,
        ssh_devbox=args.ssh_devbox,
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
