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

from deep_gvr.codex_ssh_devbox import export_codex_ssh_devbox_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the checked-in deep-gvr Codex SSH/devbox prompt pack.")
    parser.add_argument("--output-root", type=Path, required=True, help="Directory that will receive the export bundle.")
    parser.add_argument("--force", action="store_true", help="Replace existing exported files.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human-readable output.")
    args = parser.parse_args()

    try:
        report = export_codex_ssh_devbox_bundle(args.output_root, force=args.force)
    except FileExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Exported {report['template_count']} Codex SSH/devbox prompts to {report['export_root']}")
        print(f"Catalog: {report['catalog_path']}")
        for path in report["exported_paths"]:
            print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
