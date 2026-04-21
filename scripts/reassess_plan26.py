#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from deep_gvr.cli import run_session_command
from deep_gvr.contracts import DeepGvrConfig
from deep_gvr.orchestrator import CommandExecutionResult
from deep_gvr.runtime_config import load_runtime_config, resolve_config_path
from deep_gvr.runtime_paths import runtime_home_description

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROUTE_QUESTION = "Explain why d/dx x^2 = 2x."
DEFAULT_FORMAL_QUESTION = "Formalize the repetition-code logical error scaling statement O(p^((d+1)/2)) and admit failure if the proof transport is unavailable."


@dataclass(slots=True)
class CapabilityCheckReport:
    name: str
    session_id: str
    question: str
    domain: str
    config_path: str
    status: str
    final_verdict: str
    result_summary: str
    error: str | None
    evidence_log: str
    checkpoint_file: str
    artifacts_dir: str
    artifacts: list[str]
    capability_evidence: dict[str, Any]


@dataclass(slots=True)
class Plan26ReassessmentReport:
    timestamp_utc: str
    hermes_version: str
    base_config_path: str
    temp_root: str
    route_check: CapabilityCheckReport
    mcp_check: CapabilityCheckReport
    conclusion: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_route_check_config(base: DeepGvrConfig, *, evidence_dir: Path) -> DeepGvrConfig:
    payload = base.to_dict()
    payload["loop"]["max_iterations"] = 1
    payload["loop"]["alternative_approach"] = False
    payload["loop"]["max_alternatives"] = 1
    payload["verification"]["tier2"]["enabled"] = False
    payload["verification"]["tier3"]["enabled"] = False
    payload["evidence"]["directory"] = str(evidence_dir)
    payload["evidence"]["persist_to_memory"] = False
    payload["domain"]["default"] = "math"
    return DeepGvrConfig.from_dict(payload)


def build_mcp_check_config(
    base: DeepGvrConfig,
    *,
    evidence_dir: Path,
    backend: str,
) -> DeepGvrConfig:
    payload = base.to_dict()
    payload["loop"]["max_iterations"] = 1
    payload["loop"]["alternative_approach"] = False
    payload["loop"]["max_alternatives"] = 1
    payload["verification"]["tier2"]["enabled"] = False
    payload["verification"]["tier3"]["enabled"] = True
    payload["verification"]["tier3"]["backend"] = backend
    payload["evidence"]["directory"] = str(evidence_dir)
    payload["evidence"]["persist_to_memory"] = False
    payload["domain"]["default"] = "qec"
    return DeepGvrConfig.from_dict(payload)


def infer_reassessment_conclusion(
    route_check: CapabilityCheckReport,
    mcp_check: CapabilityCheckReport,
) -> dict[str, Any]:
    route_ready = bool(
        route_check.capability_evidence.get("per_subagent_model_routing", {}).get("distinct_routes_verified")
    )
    mcp_ready = bool(
        mcp_check.capability_evidence.get("subagent_mcp_inheritance", {}).get("delegated_mcp_verified")
    )
    errors = [item for item in [route_check.error, mcp_check.error] if item]

    if route_ready and mcp_ready:
        return {
            "plan26_status": "ready_for_implementation",
            "route_capability_closed": True,
            "mcp_capability_closed": True,
            "reasons": [
                "Delegated runtime evidence confirmed distinct generator/verifier routes.",
                "Delegated runtime evidence confirmed verifier-direct MCP inheritance.",
            ],
        }
    if route_ready or mcp_ready:
        return {
            "plan26_status": "partial_signal_only",
            "route_capability_closed": route_ready,
            "mcp_capability_closed": mcp_ready,
            "reasons": [
                "Only one of the two required delegated capabilities closed from runtime evidence.",
            ],
            "errors": errors,
        }
    if errors:
        return {
            "plan26_status": "environment_blocked",
            "route_capability_closed": False,
            "mcp_capability_closed": False,
            "reasons": [
                "At least one reassessment run failed before capability closure could be observed.",
            ],
            "errors": errors,
        }
    return {
        "plan26_status": "still_blocked_external",
        "route_capability_closed": False,
        "mcp_capability_closed": False,
        "reasons": [
            "Delegated runs completed without observed distinct-route closure or delegated MCP inheritance.",
        ],
    }


def _write_runtime_config(path: Path, config: DeepGvrConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config.to_dict(), sort_keys=False), encoding="utf-8")


def _read_hermes_version(*, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        ["hermes", "--version"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    output = (completed.stdout or completed.stderr).strip()
    return output or f"unavailable (exit={completed.returncode})"


def _build_executor(env: dict[str, str] | None, timeout_seconds: int):
    if env is None:
        return None

    merged_env = dict(os.environ)
    merged_env.update(env)

    def _executor(command: list[str], cwd: Path) -> CommandExecutionResult:
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_seconds,
                env=merged_env,
            )
            return CommandExecutionResult(
                returncode=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        except subprocess.TimeoutExpired:
            return CommandExecutionResult(
                returncode=124,
                stdout="",
                stderr=f"Hermes delegated orchestrator timed out after {timeout_seconds} seconds.",
            )

    return _executor


def _run_capability_check(
    *,
    name: str,
    question: str,
    domain: str,
    config_path: Path,
    session_id: str,
    prompt_profile: str,
    command_timeout_seconds: int,
    env: dict[str, str] | None,
) -> CapabilityCheckReport:
    summary = run_session_command(
        question,
        domain=domain,
        session_id=session_id,
        config_path=config_path,
        prompt_profile=prompt_profile,
        routing_probe_mode="ready",
        command_timeout_seconds=command_timeout_seconds,
        executor=_build_executor(env, command_timeout_seconds),
    )
    return CapabilityCheckReport(
        name=name,
        session_id=summary.session_id,
        question=question,
        domain=domain,
        config_path=str(config_path),
        status=summary.status,
        final_verdict=summary.final_verdict,
        result_summary=summary.result_summary,
        error=summary.error,
        evidence_log=summary.evidence_log,
        checkpoint_file=summary.checkpoint_file,
        artifacts_dir=summary.artifacts_dir,
        artifacts=list(summary.artifacts),
        capability_evidence=dict(summary.capability_evidence or {}),
    )


def build_report(
    *,
    base_config_path: Path,
    route_question: str,
    formal_question: str,
    prompt_profile: str,
    command_timeout_seconds: int,
    formal_backend: str | None = None,
    env: dict[str, str] | None = None,
) -> Plan26ReassessmentReport:
    base_config = load_runtime_config(base_config_path, create_if_missing=False)
    backend = formal_backend or base_config.verification.tier3.backend
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    temp_root = Path(tempfile.mkdtemp(prefix="deep-gvr-plan26-reassess-"))
    route_config_path = temp_root / "route-check-config.yaml"
    mcp_config_path = temp_root / "mcp-check-config.yaml"
    route_config = build_route_check_config(base_config, evidence_dir=temp_root / "route-sessions")
    mcp_config = build_mcp_check_config(base_config, evidence_dir=temp_root / "mcp-sessions", backend=backend)
    _write_runtime_config(route_config_path, route_config)
    _write_runtime_config(mcp_config_path, mcp_config)

    route_check = _run_capability_check(
        name="per_subagent_model_routing",
        question=route_question,
        domain="math",
        config_path=route_config_path,
        session_id=f"plan26-route-{timestamp}",
        prompt_profile=prompt_profile,
        command_timeout_seconds=command_timeout_seconds,
        env=env,
    )
    mcp_check = _run_capability_check(
        name="subagent_mcp_inheritance",
        question=formal_question,
        domain="qec",
        config_path=mcp_config_path,
        session_id=f"plan26-mcp-{timestamp}",
        prompt_profile=prompt_profile,
        command_timeout_seconds=command_timeout_seconds,
        env=env,
    )
    conclusion = infer_reassessment_conclusion(route_check, mcp_check)
    return Plan26ReassessmentReport(
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        hermes_version=_read_hermes_version(env=env),
        base_config_path=str(base_config_path),
        temp_root=str(temp_root),
        route_check=route_check,
        mcp_check=mcp_check,
        conclusion=conclusion,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reassess plan-26 delegated Hermes capabilities against the local runtime.")
    parser.add_argument(
        "--config",
        default="",
        help=f"Base deep-gvr config path used as the starting point for temporary reassessment configs. Default: {runtime_home_description()}/config.yaml",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional JSON output path. Defaults to /tmp/deep-gvr-plan26-reassessment-<timestamp>.json",
    )
    parser.add_argument(
        "--prompt-profile",
        default="compact",
        choices=["compact", "full"],
        help="Prompt profile to use for the delegated reassessment runs.",
    )
    parser.add_argument(
        "--command-timeout-seconds",
        type=int,
        default=180,
        help="Hermes delegated command timeout for each reassessment run.",
    )
    parser.add_argument(
        "--formal-backend",
        default="",
        help="Optional Tier 3 backend override for the verifier-MCP reassessment run.",
    )
    parser.add_argument(
        "--route-question",
        default=DEFAULT_ROUTE_QUESTION,
        help="Question used for the delegated routing reassessment run.",
    )
    parser.add_argument(
        "--formal-question",
        default=DEFAULT_FORMAL_QUESTION,
        help="Question used for the delegated verifier-MCP reassessment run.",
    )
    parser.add_argument(
        "--hermes-home",
        default="",
        help="Optional HERMES_HOME override for the reassessment subprocesses.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    base_config_path = resolve_config_path(args.config)
    env = {"HERMES_HOME": args.hermes_home} if args.hermes_home else None
    report = build_report(
        base_config_path=base_config_path,
        route_question=args.route_question,
        formal_question=args.formal_question,
        prompt_profile=args.prompt_profile,
        command_timeout_seconds=args.command_timeout_seconds,
        formal_backend=args.formal_backend or None,
        env=env,
    )

    payload = report.to_dict()
    output_path = (
        Path(args.output)
        if args.output
        else Path("/tmp") / f"deep-gvr-plan26-reassessment-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Hermes: {report.hermes_version}")
        print(f"Report: {output_path}")
        print(f"Conclusion: {report.conclusion['plan26_status']}")
        for reason in report.conclusion.get("reasons", []):
            print(f"- {reason}")
        if report.conclusion.get("errors"):
            for error in report.conclusion["errors"]:
                print(f"! {error}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
