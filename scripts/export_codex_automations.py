#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "codex_automations" / "catalog.json"


def _load_catalog() -> dict[str, object]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def export_codex_automation_bundle(output_root: Path, *, force: bool) -> dict[str, object]:
    catalog = _load_catalog()
    placeholder = str(catalog["repo_root_placeholder"])
    effective_output_root = output_root.expanduser().resolve()
    exported_paths: list[str] = []

    for item in catalog["templates"]:
        template = dict(item)
        template_path = REPO_ROOT / str(template["template_path"])
        export_path = effective_output_root / str(template["export_path"])
        if export_path.exists() and not force:
            raise FileExistsError(f"Refusing to replace existing automation export at {export_path} without --force.")
        export_path.parent.mkdir(parents=True, exist_ok=True)
        rendered_payload = template_path.read_text(encoding="utf-8").replace(placeholder, str(REPO_ROOT))
        export_path.write_text(rendered_payload, encoding="utf-8")
        exported_paths.append(str(export_path))
        template["cwds"] = [str(cwd).replace(placeholder, str(REPO_ROOT)) for cwd in template["cwds"]]

    export_catalog_path = effective_output_root / "catalog.json"
    if export_catalog_path.exists() and not force:
        raise FileExistsError(f"Refusing to replace existing automation catalog export at {export_catalog_path} without --force.")

    export_catalog = dict(catalog)
    export_catalog["templates"] = []
    for item in catalog["templates"]:
        template = dict(item)
        template["cwds"] = [str(cwd).replace(placeholder, str(REPO_ROOT)) for cwd in template["cwds"]]
        export_catalog["templates"].append(template)
    export_catalog_path.parent.mkdir(parents=True, exist_ok=True)
    export_catalog_path.write_text(json.dumps(export_catalog, indent=2) + "\n", encoding="utf-8")

    return {
        "catalog_path": str(export_catalog_path),
        "export_root": str(effective_output_root),
        "exported_paths": exported_paths,
        "template_count": len(exported_paths),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the checked-in deep-gvr Codex automation pack.")
    parser.add_argument("--output-root", type=Path, required=True, help="Directory that will receive the export bundle.")
    parser.add_argument("--force", action="store_true", help="Replace existing exported files.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human-readable output.")
    args = parser.parse_args()

    try:
        report = export_codex_automation_bundle(args.output_root, force=args.force)
    except FileExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Exported {report['template_count']} Codex automation templates to {report['export_root']}")
        print(f"Catalog: {report['catalog_path']}")
        for path in report["exported_paths"]:
            print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
