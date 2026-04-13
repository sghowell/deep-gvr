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

from deep_gvr.release_surface import (  # noqa: E402
    expected_release_tag,
    project_version,
    publication_manifest_errors,
    release_metadata_errors,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate deep-gvr release version metadata against the checked-in changelog and manifest."
    )
    parser.add_argument("--tag", help="Git tag to validate. Expected format: v<project-version>.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human-readable text.")
    args = parser.parse_args()

    version = project_version(REPO_ROOT)
    errors = [
        *publication_manifest_errors(REPO_ROOT),
        *release_metadata_errors(REPO_ROOT, tag=args.tag),
    ]
    payload = {
        "ok": not errors,
        "version": version,
        "expected_tag": expected_release_tag(REPO_ROOT),
        "tag": args.tag,
        "errors": errors,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"deep-gvr release metadata for version {version}")
        print(f"  expected_tag: {payload['expected_tag']}")
        if args.tag is not None:
            print(f"  provided_tag: {args.tag}")
        if errors:
            print("  status: blocked")
            for error in errors:
                print(f"  - {error}")
        else:
            print("  status: ready")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
