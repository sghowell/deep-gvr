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

from deep_gvr.codex_native_delegation import (  # noqa: E402
    evaluate_codex_native_delegation,
    format_codex_native_delegation_overview,
    write_codex_native_delegation_evaluation_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate how far deep-gvr should promote Codex-native delegation into the runtime boundary."
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional JSON output path. Defaults to /tmp/deep-gvr-codex-native-delegation-<timestamp>/report.json.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full evaluation report JSON to stdout.",
    )
    parser.add_argument(
        "--codex-binary",
        default="codex",
        help="Codex executable to inspect. Default: codex",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = evaluate_codex_native_delegation(
        output_root=Path(args.output).parent if args.output else None,
        codex_binary=args.codex_binary,
    )
    output_path = Path(args.output) if args.output else Path(report.output_root) / "report.json"
    write_codex_native_delegation_evaluation_report(report, output_path)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"Wrote Codex native delegation evaluation report to {output_path}")
        for line in format_codex_native_delegation_overview(report):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
