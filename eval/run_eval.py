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
from deep_gvr.evaluation import benchmark_routing_probe, run_benchmark_suite, write_benchmark_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the deep-gvr deterministic benchmark suite.")
    parser.add_argument(
        "--suite",
        default="eval/known_problems.json",
        help="Path to the benchmark suite JSON file.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional path for the JSON benchmark report output.",
    )
    parser.add_argument(
        "--routing-probe",
        choices=["auto", "ready", "fallback"],
        default="fallback",
        help="Routing probe mode for the deterministic benchmark run.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    routing_probe = None if args.routing_probe == "auto" else benchmark_routing_probe(ProbeStatus(args.routing_probe))
    report = run_benchmark_suite(args.suite, routing_probe=routing_probe)
    if args.output:
        write_benchmark_report(report, args.output)
        print(f"Wrote benchmark report to {args.output}")
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
