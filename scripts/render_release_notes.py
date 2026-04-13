#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from deep_gvr.release_surface import project_version, release_notes_for_version  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Render release notes for a deep-gvr version from CHANGELOG.md")
    parser.add_argument(
        "--version",
        default=project_version(REPO_ROOT),
        help="Version to render. Defaults to the current project version.",
    )
    parser.add_argument("--output", type=Path, help="Optional output path for the rendered notes.")
    args = parser.parse_args()

    notes = release_notes_for_version(args.version, REPO_ROOT)
    if args.output is not None:
        args.output.write_text(notes + "\n", encoding="utf-8")
    else:
        print(notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
