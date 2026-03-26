from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from deep_gvr.probes import run_capability_probes


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deep-gvr readiness capability probes")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of plain text")
    args = parser.parse_args()

    results = run_capability_probes()
    if args.json:
        print(json.dumps([result.to_dict() for result in results], indent=2))
        return 0

    for result in results:
        print(f"{result.name}: {result.status.value}")
        print(f"  summary: {result.summary}")
        print(f"  preferred: {result.preferred_outcome}")
        print(f"  fallback: {result.fallback}")
        if result.details:
            print(f"  details: {json.dumps(result.details, sort_keys=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
