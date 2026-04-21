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

from deep_gvr.codex_review_qa import CodexReviewQaExecutionOptions, execute_codex_review_qa


def _print_human_report(report: dict[str, object]) -> None:
    print(f"Codex review/QA workflow: {report['workflow_id']}")
    print(f"  overall_status: {report['overall_status']}")
    print(f"  output_root: {report['output_root']}")
    print(f"  summary: {report['summary']}")
    print("steps:")
    for step in report["steps"]:
        if not isinstance(step, dict):
            continue
        print(f"- {step['name']}: {step['status']}")
        print(f"  summary: {step['summary']}")
        guidance = step.get("guidance")
        if guidance:
            print(f"  guidance: {guidance}")
    print("artifacts:")
    for artifact in report["artifacts"]:
        if not isinstance(artifact, dict):
            continue
        print(f"- {artifact['artifact_id']}: {artifact['path']}")
        print(f"  summary: {artifact['summary']}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare a repo-owned Codex review/QA evidence bundle for deep-gvr."
    )
    parser.add_argument(
        "workflow",
        choices=["pull_request_review", "public_docs_visual_qa"],
        help="Which review/QA workflow to materialize into a local evidence bundle.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        required=True,
        help="Directory that will receive the generated review/QA evidence bundle.",
    )
    parser.add_argument("--force", action="store_true", help="Replace an existing output bundle in place.")
    parser.add_argument("--base-ref", default="main", help="Base Git ref for the pull_request_review workflow.")
    parser.add_argument("--head-ref", default="HEAD", help="Head Git ref for the pull_request_review workflow.")
    parser.add_argument(
        "--site-dir",
        type=Path,
        help="Optional built site directory override for the public_docs_visual_qa workflow. Defaults to site/ under the repo root.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human-readable output.")
    args = parser.parse_args()

    try:
        report = execute_codex_review_qa(
            CodexReviewQaExecutionOptions(
                workflow_id=args.workflow,
                output_root=args.output_root,
                force=args.force,
                base_ref=args.base_ref,
                head_ref=args.head_ref,
                site_dir=args.site_dir,
            )
        ).to_dict()
    except (FileExistsError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_human_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
