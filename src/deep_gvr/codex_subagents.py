from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

from .contracts import CodexReviewQaCatalog
from .json_schema import SchemaValidationError, validate

REPO_ROOT_PLACEHOLDER = "__DEEP_GVR_REPO_ROOT__"
_SUBAGENT_CATALOG_PATH = Path("codex_subagents/catalog.json")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def subagent_catalog_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / _SUBAGENT_CATALOG_PATH


def _schema_path(name: str, root: Path | None = None) -> Path:
    return (root or repo_root()) / "schemas" / name


def _project_version(root: Path | None = None) -> str:
    payload = tomllib.loads(((root or repo_root()) / "pyproject.toml").read_text(encoding="utf-8"))
    return str(payload["project"]["version"])


def expected_codex_subagent_catalog(root: Path | None = None) -> CodexReviewQaCatalog:
    effective_root = root or repo_root()
    payload = json.loads((effective_root / "templates" / "codex_subagents_catalog.template.json").read_text(encoding="utf-8"))
    payload["version"] = _project_version(effective_root)
    return CodexReviewQaCatalog.from_dict(payload)


def codex_subagent_surface_errors(root: Path | None = None) -> list[str]:
    effective_root = root or repo_root()
    errors: list[str] = []
    catalog_path = subagent_catalog_path(effective_root)
    schema = json.loads(_schema_path("codex_subagents_catalog.schema.json", effective_root).read_text(encoding="utf-8"))

    if not catalog_path.exists():
        return [f"{catalog_path.relative_to(effective_root)}: required Codex subagent catalog is missing"]

    try:
        actual_catalog_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        validate(actual_catalog_payload, schema)
        actual_catalog = CodexReviewQaCatalog.from_dict(actual_catalog_payload)
    except (json.JSONDecodeError, OSError, SchemaValidationError, ValueError) as exc:
        return [f"{catalog_path.relative_to(effective_root)}: invalid Codex subagent catalog: {exc}"]

    expected_catalog = expected_codex_subagent_catalog(effective_root)
    if actual_catalog.to_dict() != expected_catalog.to_dict():
        errors.append(
            f"{catalog_path.relative_to(effective_root)}: Codex subagent catalog is out of sync with repo metadata"
        )

    for spec in expected_catalog.templates:
        template_path = effective_root / spec.template_path
        if not template_path.exists():
            errors.append(f"{template_path.relative_to(effective_root)}: required Codex subagent template is missing")
            continue
        actual_template = template_path.read_text(encoding="utf-8")
        if actual_template != spec.prompt:
            errors.append(
                f"{template_path.relative_to(effective_root)}: subagent template is out of sync with the catalog"
            )
    return errors


def export_codex_subagent_bundle(
    output_root: Path,
    *,
    root: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    effective_root = (root or repo_root()).resolve()
    effective_output_root = output_root.expanduser().resolve()
    catalog = expected_codex_subagent_catalog(effective_root)
    exported_paths: list[str] = []

    for spec in catalog.templates:
        export_path = effective_output_root / spec.export_path
        if export_path.exists() and not force:
            raise FileExistsError(f"Refusing to replace existing subagent export at {export_path} without --force.")
        export_path.parent.mkdir(parents=True, exist_ok=True)
        rendered_payload = (effective_root / spec.template_path).read_text(encoding="utf-8").replace(
            REPO_ROOT_PLACEHOLDER,
            str(effective_root),
        )
        export_path.write_text(rendered_payload, encoding="utf-8")
        exported_paths.append(str(export_path))

    export_catalog_payload = catalog.to_dict()
    for template in export_catalog_payload["templates"]:
        template["prompt"] = str(template["prompt"]).replace(REPO_ROOT_PLACEHOLDER, str(effective_root))

    export_catalog_path = effective_output_root / "catalog.json"
    if export_catalog_path.exists() and not force:
        raise FileExistsError(
            f"Refusing to replace existing subagent catalog export at {export_catalog_path} without --force."
        )
    export_catalog_path.parent.mkdir(parents=True, exist_ok=True)
    export_catalog_path.write_text(json.dumps(export_catalog_payload, indent=2) + "\n", encoding="utf-8")

    return {
        "catalog_path": str(export_catalog_path),
        "export_root": str(effective_output_root),
        "exported_paths": exported_paths,
        "template_count": len(exported_paths),
    }
