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

from deep_gvr.contracts import ProbeStatus
from deep_gvr.evaluation import LiveEvalConfig, benchmark_routing_probe, run_benchmark_suite, write_benchmark_report
from deep_gvr.prompt_profiles import DEFAULT_PROMPT_PROFILE, PROMPT_PROFILES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the deep-gvr benchmark suite in deterministic or live mode.")
    parser.add_argument(
        "--mode",
        choices=["deterministic", "live"],
        default="deterministic",
        help="Evaluation mode. Deterministic uses fixture agents; live uses Hermes prompt execution.",
    )
    parser.add_argument(
        "--suite",
        default="eval/known_problems.json",
        help="Path to the benchmark suite JSON file.",
    )
    parser.add_argument(
        "--config",
        default="",
        help="Runtime config path for live mode. Uses the repo default path when omitted.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional path for the JSON benchmark report output. Live mode defaults to <output-root>/report.json.",
    )
    parser.add_argument(
        "--output-root",
        default="",
        help="Optional live-run artifact directory. Defaults to eval/results/live/<timestamp>/ for live mode.",
    )
    parser.add_argument(
        "--routing-probe",
        choices=["auto", "ready", "fallback"],
        default="fallback",
        help="Routing probe mode for the benchmark run.",
    )
    parser.add_argument(
        "--case-id",
        action="append",
        default=[],
        help="Run only the named benchmark case. Repeat the flag to select multiple cases.",
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=None,
        help="Optional limit on the number of selected cases to run.",
    )
    parser.add_argument(
        "--run-id",
        default="",
        help="Optional stable run identifier. Live mode uses a UTC timestamp when omitted.",
    )
    parser.add_argument(
        "--hermes-binary",
        default="hermes",
        help="Hermes executable to use for live mode.",
    )
    parser.add_argument(
        "--prompt-root",
        default="prompts",
        help="Prompt directory for live mode.",
    )
    parser.add_argument(
        "--prompt-profile",
        choices=list(PROMPT_PROFILES),
        default=DEFAULT_PROMPT_PROFILE,
        help="Prompt scaffolding profile for live Hermes calls.",
    )
    parser.add_argument(
        "--command-timeout-seconds",
        type=int,
        default=120,
        help="Per-role Hermes command timeout for live mode.",
    )
    parser.add_argument(
        "--toolsets",
        action="append",
        default=[],
        help="Comma-separated Hermes toolsets for live mode. Repeat the flag to add more values.",
    )
    parser.add_argument(
        "--skills",
        action="append",
        default=[],
        help="Comma-separated Hermes skills for live mode. Repeat the flag to add more values.",
    )
    parser.add_argument(
        "--allow-baseline-overwrite",
        action="store_true",
        help="Permit writing a live benchmark report to eval/results/baseline_results.json.",
    )
    return parser.parse_args()


def _split_csv_flags(values: list[str]) -> list[str]:
    items: list[str] = []
    for value in values:
        items.extend(part.strip() for part in value.split(",") if part.strip())
    return items


def _materialize_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def main() -> int:
    args = parse_args()
    routing_probe = None if args.routing_probe == "auto" else benchmark_routing_probe(ProbeStatus(args.routing_probe))
    live_config = None
    if args.mode == "live":
        live_config = LiveEvalConfig(
            hermes_binary=args.hermes_binary,
            prompt_root=args.prompt_root,
            prompt_profile=args.prompt_profile,
            command_timeout_seconds=args.command_timeout_seconds,
            toolsets=_split_csv_flags(args.toolsets),
            skills=_split_csv_flags(args.skills),
        )
    report = run_benchmark_suite(
        args.suite,
        routing_probe=routing_probe,
        mode=args.mode,
        config_path=args.config or None,
        output_root=args.output_root or None,
        run_id=args.run_id or None,
        case_ids=args.case_id,
        max_cases=args.max_cases,
        live_config=live_config,
    )
    output_path: Path | None = None
    if args.output:
        output_path = Path(args.output)
    elif report.mode == "live":
        output_path = _materialize_path(report.output_root) / "report.json"

    if output_path is not None:
        write_benchmark_report(
            report,
            output_path,
            allow_baseline_overwrite=args.allow_baseline_overwrite,
        )
        print(f"Wrote benchmark report to {output_path}")
        if report.mode == "live":
            print(f"Live artifacts root: {_materialize_path(report.output_root)}")
    else:
        print(json.dumps(report.to_dict(), indent=2))

    print(
        "Benchmark summary: "
        f"{report.summary.passed_cases}/{report.summary.total_cases} passed, "
        f"false_positive_rate={report.summary.false_positive_rate:.3f}, "
        f"tier_accuracy={report.summary.tier_accuracy:.3f}"
    )
    return 0 if report.summary.failed_cases == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
