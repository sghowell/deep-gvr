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

from deep_gvr.codex_ssh_devbox_runtime import (  # noqa: E402
    CodexSshDevboxPreflightError,
    codex_ssh_devbox_blocked_result,
    resume_codex_ssh_devbox_session,
    run_codex_ssh_devbox_session,
)
from deep_gvr.prompt_profiles import PROMPT_PROFILES  # noqa: E402
from deep_gvr.runtime_paths import runtime_home_description  # noqa: E402


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        type=Path,
        help=f"Runtime config path. Default: {runtime_home_description()}/config.yaml",
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
        "--prompt-root",
        type=Path,
        default=Path("prompts"),
        help="Prompt root directory. Default: prompts",
    )
    parser.add_argument(
        "--prompt-profile",
        default="compact",
        choices=sorted(PROMPT_PROFILES),
        help="Prompt profile for the orchestrator backend.",
    )
    parser.add_argument(
        "--routing-probe",
        choices=["auto", "ready", "fallback"],
        default="auto",
        help="Routing probe mode to thread into the orchestrator runtime.",
    )
    parser.add_argument(
        "--command-timeout-seconds",
        type=int,
        default=120,
        help="Backend command timeout in seconds.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of a short human-readable summary.",
    )


def _print_human_result(payload: dict[str, object]) -> None:
    preflight = payload["preflight"]
    session = payload.get("session")
    if not isinstance(preflight, dict):
        raise ValueError("Missing preflight payload.")

    print("Codex SSH/devbox execution gate")
    print(f"  overall_status: {preflight['overall_status']}")
    print(f"  operator_ready: {preflight['operator_ready']}")
    if not preflight["operator_ready"]:
        print("  blocking_checks:")
        for check in preflight["checks"]:
            if isinstance(check, dict) and check.get("status") != "ready":
                print(f"  - {check['name']}: {check['summary']}")
        return

    if not isinstance(session, dict):
        print("  session: not started")
        return

    print("Session summary")
    print(f"  command: {session['command']}")
    print(f"  session_id: {session['session_id']}")
    print(f"  final_verdict: {session['final_verdict']}")
    print(f"  result_summary: {session['result_summary']}")
    print(f"  artifacts_dir: {session['artifacts_dir']}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run deep-gvr from a Codex SSH/devbox session with the native codex_local backend gate."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a new deep-gvr session through the Codex SSH/devbox path.")
    run_parser.add_argument("problem", help="Question or claim to investigate.")
    run_parser.add_argument("--session-id", help="Optional session id override.")
    _add_common_args(run_parser)

    resume_parser = subparsers.add_parser(
        "resume",
        help="Resume an existing deep-gvr session through the Codex SSH/devbox path.",
    )
    resume_parser.add_argument("session_id", help="Existing session id to resume.")
    _add_common_args(resume_parser)

    args = parser.parse_args()

    try:
        if args.command == "run":
            result = run_codex_ssh_devbox_session(
                args.problem,
                config_path=args.config,
                codex_skills_dir=args.codex_skills_dir,
                hermes_skills_dir=args.hermes_skills_dir,
                hermes_config_path=args.hermes_config,
                prompt_root=args.prompt_root,
                prompt_profile=args.prompt_profile,
                routing_probe_mode=args.routing_probe,
                command_timeout_seconds=args.command_timeout_seconds,
                session_id=args.session_id,
            )
        else:
            result = resume_codex_ssh_devbox_session(
                args.session_id,
                config_path=args.config,
                codex_skills_dir=args.codex_skills_dir,
                hermes_skills_dir=args.hermes_skills_dir,
                hermes_config_path=args.hermes_config,
                prompt_root=args.prompt_root,
                prompt_profile=args.prompt_profile,
                routing_probe_mode=args.routing_probe,
                command_timeout_seconds=args.command_timeout_seconds,
            )
        payload = result.to_dict()
    except CodexSshDevboxPreflightError as exc:
        payload = codex_ssh_devbox_blocked_result(exc)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            _print_human_result(payload)
        return 2

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        _print_human_result(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
