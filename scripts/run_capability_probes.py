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
from deep_gvr.runtime_config import default_config_path, load_runtime_config


def _load_capability_evidence(path: Path | None) -> dict[str, object]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Capability evidence must be a top-level JSON object.")
    return payload


def _load_probe_runtime_config(path: Path | None):
    if path is not None:
        return load_runtime_config(path)

    configured_default = default_config_path()
    if configured_default.exists():
        return load_runtime_config(configured_default)

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deep-gvr readiness capability probes")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of plain text")
    parser.add_argument(
        "--capability-evidence",
        type=Path,
        help="Optional JSON file with observed runtime capability evidence for delegated routing and MCP inheritance.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional runtime config used for environment-sensitive backend readiness checks.",
    )
    args = parser.parse_args()

    results = run_capability_probes(
        _load_capability_evidence(args.capability_evidence),
        _load_probe_runtime_config(args.config),
    )
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
