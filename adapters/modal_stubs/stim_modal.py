from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from deep_gvr.contracts import Backend, SimSpec

from adapters.stim_adapter import StimAdapter


def main() -> int:
    parser = argparse.ArgumentParser(description="Modal entrypoint for the deep-gvr Stim adapter")
    parser.add_argument("--spec", required=True, help="Path to the simulation spec JSON file")
    parser.add_argument("--output", required=True, help="Path to write the normalized results JSON file")
    parser.add_argument("--backend", default="modal", choices=["modal"], help="Normalized backend label for the result")
    args = parser.parse_args()

    spec = SimSpec.from_dict(json.loads(Path(args.spec).read_text(encoding="utf-8")))
    results = StimAdapter().run(spec, Backend.LOCAL)
    results.backend = Backend(args.backend)
    Path(args.output).write_text(json.dumps(results.to_dict(), indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
