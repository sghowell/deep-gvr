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

from deep_gvr.auto_improve import (  # noqa: E402
    evaluate_auto_improve,
    format_auto_improve_evaluation_overview,
    write_auto_improve_evaluation_report,
)
from deep_gvr.evaluation import LiveEvalConfig  # noqa: E402
from deep_gvr.prompt_profiles import DEFAULT_PROMPT_PROFILE, PROMPT_PROFILES  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate the deep-gvr auto_improve policy against isolated benchmark comparisons."
    )
    parser.add_argument(
        "--suite",
        default="eval/known_problems.json",
        help="Benchmark suite path. Default: eval/known_problems.json",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional JSON output path. Defaults to /tmp/deep-gvr-auto-improve-<timestamp>/report.json.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full evaluation report JSON to stdout.",
    )
    parser.add_argument(
        "--deterministic-subset",
        default="analysis-full",
        help="Named deterministic benchmark subset to compare. Default: analysis-full",
    )
    parser.add_argument(
        "--deterministic-repeat",
        type=int,
        default=3,
        help="Repeat count for the deterministic comparison. Default: 3",
    )
    parser.add_argument(
        "--include-live",
        action="store_true",
        help="Also run a live benchmark comparison using the provided runtime config.",
    )
    parser.add_argument(
        "--live-subset",
        default="live-expansion",
        help="Named live benchmark subset to compare when --include-live is set. Default: live-expansion",
    )
    parser.add_argument(
        "--live-repeat",
        type=int,
        default=2,
        help="Repeat count for the live comparison. Default: 2",
    )
    parser.add_argument(
        "--config",
        default="",
        help="Runtime config path for live evaluation. Required with --include-live.",
    )
    parser.add_argument(
        "--hermes-binary",
        default="hermes",
        help="Hermes executable to use for live evaluation.",
    )
    parser.add_argument(
        "--prompt-root",
        default="prompts",
        help="Prompt directory for live Hermes calls.",
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
        help="Base Hermes command timeout for live role calls.",
    )
    parser.add_argument(
        "--toolsets",
        action="append",
        default=[],
        help="Comma-separated Hermes toolsets for live evaluation. Repeat the flag to add more values.",
    )
    parser.add_argument(
        "--skills",
        action="append",
        default=[],
        help="Comma-separated Hermes skills for live evaluation. Repeat the flag to add more values.",
    )
    return parser.parse_args()


def _split_csv_flags(values: list[str]) -> list[str]:
    items: list[str] = []
    for value in values:
        items.extend(part.strip() for part in value.split(",") if part.strip())
    return items


def main() -> int:
    args = parse_args()
    if args.deterministic_repeat < 1:
        raise SystemExit("--deterministic-repeat must be at least 1.")
    if args.live_repeat < 1:
        raise SystemExit("--live-repeat must be at least 1.")
    if args.include_live and not args.config:
        raise SystemExit("--config is required when --include-live is set.")

    live_config = None
    if args.include_live:
        live_config = LiveEvalConfig(
            hermes_binary=args.hermes_binary,
            prompt_root=args.prompt_root,
            prompt_profile=args.prompt_profile,
            command_timeout_seconds=args.command_timeout_seconds,
            toolsets=_split_csv_flags(args.toolsets),
            skills=_split_csv_flags(args.skills),
        )

    report = evaluate_auto_improve(
        args.suite,
        output_root=Path(args.output).parent if args.output else None,
        deterministic_subset=args.deterministic_subset,
        deterministic_repeat_count=args.deterministic_repeat,
        include_live=args.include_live,
        live_subset=args.live_subset,
        live_repeat_count=args.live_repeat,
        config_path=args.config or None,
        live_config=live_config,
    )

    output_path = Path(args.output) if args.output else Path(report.output_root) / "report.json"
    write_auto_improve_evaluation_report(report, output_path)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"Wrote auto-improve evaluation report to {output_path}")
        for line in format_auto_improve_evaluation_overview(report):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
