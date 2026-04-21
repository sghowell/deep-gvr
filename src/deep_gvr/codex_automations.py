from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

from .contracts import CodexAutomationCatalog, CodexAutomationSpec
from .json_schema import SchemaValidationError, validate

REPO_ROOT_PLACEHOLDER = "__DEEP_GVR_REPO_ROOT__"
_AUTOMATION_CATALOG_PATH = Path("codex_automations/catalog.json")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def automation_catalog_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / _AUTOMATION_CATALOG_PATH


def _schema_path(name: str, root: Path | None = None) -> Path:
    return (root or repo_root()) / "schemas" / name


def _project_version(root: Path | None = None) -> str:
    payload = tomllib.loads(((root or repo_root()) / "pyproject.toml").read_text(encoding="utf-8"))
    return str(payload["project"]["version"])


def expected_codex_automation_catalog(root: Path | None = None) -> CodexAutomationCatalog:
    effective_root = root or repo_root()
    version = _project_version(effective_root)
    return CodexAutomationCatalog(
        name="deep-gvr",
        version=version,
        repo_root_placeholder=REPO_ROOT_PLACEHOLDER,
        templates=[
            CodexAutomationSpec(
                automation_id="benchmark_subset_sweep",
                name="deep-gvr benchmark sweep",
                description="Run deterministic benchmark subsets and summarize only regressions or new failures.",
                schedule_summary="Weekdays at 9:00 AM",
                template_path="codex_automations/templates/benchmark_subset_sweep.automation.toml",
                export_path="automations/benchmark_subset_sweep/automation.toml",
                kind="cron",
                status="PAUSED",
                rrule="FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=9;BYMINUTE=0",
                execution_environment="local",
                model="gpt-5.3-codex",
                reasoning_effort="high",
                cwds=[REPO_ROOT_PLACEHOLDER],
                prompt=(
                    "Run deterministic deep-gvr benchmark subsets from the repo root using uv-managed commands. "
                    "Use the checked-in subsets `core-science`, `quantum-oss`, and `photonic-mbqc`, write outputs "
                    "under /tmp/deep-gvr-codex-automation-benchmarks, and compare outcomes against the checked-in "
                    "baseline. Summarize only regressions, flaky behavior, or newly failing cases. Do not edit "
                    "files, change release policy, or push anything."
                ),
            ),
            CodexAutomationSpec(
                automation_id="ci_failure_triage",
                name="deep-gvr CI triage",
                description="Inspect the newest GitHub Actions runs and summarize only actionable CI or Docs failures.",
                schedule_summary="Every 6 hours on weekdays",
                template_path="codex_automations/templates/ci_failure_triage.automation.toml",
                export_path="automations/ci_failure_triage/automation.toml",
                kind="cron",
                status="PAUSED",
                rrule="FREQ=HOURLY;INTERVAL=6;BYDAY=MO,TU,WE,TH,FR",
                execution_environment="local",
                model="gpt-5.3-codex",
                reasoning_effort="medium",
                cwds=[REPO_ROOT_PLACEHOLDER],
                prompt=(
                    "Inspect the newest GitHub Actions runs for the deep-gvr repository. If the latest CI or Docs run "
                    "on main is failing, identify the failing job, summarize the concrete error, point to the likeliest "
                    "offending files or workflow definitions, and propose the smallest next fix. If the latest runs are "
                    "green, say that no triage is needed. Do not edit files or push changes."
                ),
            ),
            CodexAutomationSpec(
                automation_id="release_candidate_sweep",
                name="deep-gvr release sweep",
                description="Run the release-critical validation path and summarize blockers for cutting the next tag.",
                schedule_summary="Fridays at 10:00 AM",
                template_path="codex_automations/templates/release_candidate_sweep.automation.toml",
                export_path="automations/release_candidate_sweep/automation.toml",
                kind="cron",
                status="PAUSED",
                rrule="FREQ=WEEKLY;BYDAY=FR;BYHOUR=10;BYMINUTE=0",
                execution_environment="local",
                model="gpt-5.3-codex",
                reasoning_effort="high",
                cwds=[REPO_ROOT_PLACEHOLDER],
                prompt=(
                    "From the deep-gvr repo root, run the release-critical validation path: `uv run python "
                    "scripts/check_repo.py`, `uv run python scripts/run_capability_probes.py`, `uv run python -m "
                    "unittest discover -s tests -v`, `uv run python scripts/release_preflight.py --json`, `uv run "
                    "python scripts/codex_preflight.py --json`, and `uv run mkdocs build --strict`. Summarize blockers "
                    "for cutting the next tagged release and point to the exact failing surface. Do not modify version, "
                    "changelog, or publication manifests automatically."
                ),
            ),
            CodexAutomationSpec(
                automation_id="docs_surface_smoke",
                name="deep-gvr docs smoke",
                description="Run the hosted-docs safety path and summarize public-docs regressions.",
                schedule_summary="Daily at 1:00 PM",
                template_path="codex_automations/templates/docs_surface_smoke.automation.toml",
                export_path="automations/docs_surface_smoke/automation.toml",
                kind="cron",
                status="PAUSED",
                rrule="FREQ=HOURLY;INTERVAL=24",
                execution_environment="local",
                model="gpt-5.3-codex",
                reasoning_effort="medium",
                cwds=[REPO_ROOT_PLACEHOLDER],
                prompt=(
                    "Run the deep-gvr hosted-docs safety path from the repo root: `uv run mkdocs build --strict`. "
                    "Then inspect the public docs entrypoints `README.md`, `docs/index.md`, `docs/start-here.md`, "
                    "`docs/codex-local.md`, `docs/codex-plugin.md`, and `docs/codex-automations.md` for broken links, "
                    "missing assets, or obvious public-surface drift. Summarize only actionable issues. Do not edit "
                    "files or push changes automatically."
                ),
            ),
        ],
    )


def _expected_automation_toml(spec: CodexAutomationSpec) -> dict[str, Any]:
    return {
        "name": spec.name,
        "prompt": spec.prompt,
        "rrule": spec.rrule,
        "kind": spec.kind,
        "status": spec.status,
        "cwds": list(spec.cwds),
        "executionEnvironment": spec.execution_environment,
        "model": spec.model,
        "reasoningEffort": spec.reasoning_effort,
    }


def codex_automation_surface_errors(root: Path | None = None) -> list[str]:
    effective_root = root or repo_root()
    errors: list[str] = []
    catalog_path = automation_catalog_path(effective_root)
    schema = json.loads(_schema_path("codex_automation_catalog.schema.json", effective_root).read_text(encoding="utf-8"))

    if not catalog_path.exists():
        return [f"{catalog_path.relative_to(effective_root)}: required Codex automation catalog is missing"]

    try:
        actual_catalog_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        validate(actual_catalog_payload, schema)
        actual_catalog = CodexAutomationCatalog.from_dict(actual_catalog_payload)
    except (json.JSONDecodeError, OSError, SchemaValidationError, ValueError) as exc:
        return [f"{catalog_path.relative_to(effective_root)}: invalid Codex automation catalog: {exc}"]

    expected_catalog = expected_codex_automation_catalog(effective_root)
    if actual_catalog.to_dict() != expected_catalog.to_dict():
        errors.append(
            f"{catalog_path.relative_to(effective_root)}: Codex automation catalog is out of sync with repo metadata"
        )

    for spec in expected_catalog.templates:
        template_path = effective_root / spec.template_path
        if not template_path.exists():
            errors.append(f"{template_path.relative_to(effective_root)}: required Codex automation template is missing")
            continue
        try:
            actual_template = tomllib.loads(template_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            errors.append(f"{template_path.relative_to(effective_root)}: invalid TOML automation template: {exc}")
            continue
        expected_template = _expected_automation_toml(spec)
        if actual_template != expected_template:
            errors.append(
                f"{template_path.relative_to(effective_root)}: automation template is out of sync with the catalog"
            )
    return errors


def export_codex_automation_bundle(
    output_root: Path,
    *,
    root: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    effective_root = (root or repo_root()).resolve()
    effective_output_root = output_root.expanduser().resolve()
    catalog = expected_codex_automation_catalog(effective_root)
    exported_paths: list[str] = []

    for spec in catalog.templates:
        export_path = effective_output_root / spec.export_path
        if export_path.exists() and not force:
            raise FileExistsError(f"Refusing to replace existing automation export at {export_path} without --force.")
        export_path.parent.mkdir(parents=True, exist_ok=True)
        rendered_payload = (effective_root / spec.template_path).read_text(encoding="utf-8").replace(
            REPO_ROOT_PLACEHOLDER,
            str(effective_root),
        )
        export_path.write_text(rendered_payload, encoding="utf-8")
        exported_paths.append(str(export_path))

    export_catalog_payload = catalog.to_dict()
    for template in export_catalog_payload["templates"]:
        template["cwds"] = [cwd.replace(REPO_ROOT_PLACEHOLDER, str(effective_root)) for cwd in template["cwds"]]

    export_catalog_path = effective_output_root / "catalog.json"
    if export_catalog_path.exists() and not force:
        raise FileExistsError(f"Refusing to replace existing automation catalog export at {export_catalog_path} without --force.")
    export_catalog_path.parent.mkdir(parents=True, exist_ok=True)
    export_catalog_path.write_text(json.dumps(export_catalog_payload, indent=2) + "\n", encoding="utf-8")

    return {
        "catalog_path": str(export_catalog_path),
        "export_root": str(effective_output_root),
        "exported_paths": exported_paths,
        "template_count": len(exported_paths),
    }
