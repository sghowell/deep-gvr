from __future__ import annotations

import json
import re
import shutil
import subprocess
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contracts import (
    CodexReviewQaCatalog,
    CodexReviewQaExecutionArtifact,
    CodexReviewQaExecutionReport,
    CodexReviewQaExecutionStep,
    ReleaseCheckStatus,
)
from .json_schema import SchemaValidationError, validate

REPO_ROOT_PLACEHOLDER = "__DEEP_GVR_REPO_ROOT__"
_REVIEW_QA_CATALOG_PATH = Path("codex_review_qa/catalog.json")
_IMAGE_SRC_PATTERN = re.compile(r"""<img[^>]+src=["']([^"']+)["']""", flags=re.IGNORECASE)

_PUBLIC_DOCS_VISUAL_TARGETS = [
    {
        "page_id": "landing_page",
        "name": "Landing page",
        "source_path": "docs/index.md",
        "site_path": "site/index.html",
        "route": "/",
    },
    {
        "page_id": "concepts",
        "name": "Concepts",
        "source_path": "docs/concepts.md",
        "site_path": "site/concepts/index.html",
        "route": "/concepts/",
    },
    {
        "page_id": "architecture_and_design",
        "name": "Architecture and Design",
        "source_path": "docs/deep-gvr-architecture.md",
        "site_path": "site/deep-gvr-architecture/index.html",
        "route": "/deep-gvr-architecture/",
    },
    {
        "page_id": "codex_local",
        "name": "Codex Local",
        "source_path": "docs/codex-local.md",
        "site_path": "site/codex-local/index.html",
        "route": "/codex-local/",
    },
    {
        "page_id": "codex_plugin",
        "name": "Codex Plugin",
        "source_path": "docs/codex-plugin.md",
        "site_path": "site/codex-plugin/index.html",
        "route": "/codex-plugin/",
    },
    {
        "page_id": "codex_automations",
        "name": "Codex Automations",
        "source_path": "docs/codex-automations.md",
        "site_path": "site/codex-automations/index.html",
        "route": "/codex-automations/",
    },
    {
        "page_id": "codex_review_qa",
        "name": "Codex Review and Visual QA",
        "source_path": "docs/codex-review-qa.md",
        "site_path": "site/codex-review-qa/index.html",
        "route": "/codex-review-qa/",
    },
]


@dataclass(slots=True)
class CodexReviewQaExecutionOptions:
    workflow_id: str
    output_root: Path
    force: bool = False
    base_ref: str = "main"
    head_ref: str = "HEAD"
    site_dir: Path | None = None
    build_command: tuple[str, ...] | None = None


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def review_qa_catalog_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / _REVIEW_QA_CATALOG_PATH


def _schema_path(name: str, root: Path | None = None) -> Path:
    return (root or repo_root()) / "schemas" / name


def _project_version(root: Path | None = None) -> str:
    payload = tomllib.loads(((root or repo_root()) / "pyproject.toml").read_text(encoding="utf-8"))
    return str(payload["project"]["version"])


def expected_codex_review_qa_catalog(root: Path | None = None) -> CodexReviewQaCatalog:
    effective_root = root or repo_root()
    payload = json.loads((effective_root / "templates" / "codex_review_qa_catalog.template.json").read_text(encoding="utf-8"))
    payload["version"] = _project_version(effective_root)
    return CodexReviewQaCatalog.from_dict(payload)


def codex_review_qa_surface_errors(root: Path | None = None) -> list[str]:
    effective_root = root or repo_root()
    errors: list[str] = []
    catalog_path = review_qa_catalog_path(effective_root)
    schema = json.loads(_schema_path("codex_review_qa_catalog.schema.json", effective_root).read_text(encoding="utf-8"))

    if not catalog_path.exists():
        return [f"{catalog_path.relative_to(effective_root)}: required Codex review/QA catalog is missing"]

    try:
        actual_catalog_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        validate(actual_catalog_payload, schema)
        actual_catalog = CodexReviewQaCatalog.from_dict(actual_catalog_payload)
    except (json.JSONDecodeError, OSError, SchemaValidationError, ValueError) as exc:
        return [f"{catalog_path.relative_to(effective_root)}: invalid Codex review/QA catalog: {exc}"]

    expected_catalog = expected_codex_review_qa_catalog(effective_root)
    if actual_catalog.to_dict() != expected_catalog.to_dict():
        errors.append(
            f"{catalog_path.relative_to(effective_root)}: Codex review/QA catalog is out of sync with repo metadata"
        )

    for spec in expected_catalog.templates:
        template_path = effective_root / spec.template_path
        if not template_path.exists():
            errors.append(f"{template_path.relative_to(effective_root)}: required Codex review/QA template is missing")
            continue
        actual_template = template_path.read_text(encoding="utf-8")
        if actual_template != spec.prompt:
            errors.append(
                f"{template_path.relative_to(effective_root)}: review/QA template is out of sync with the catalog"
            )

    required_paths = [
        effective_root / "scripts" / "export_codex_review_qa.py",
        effective_root / "scripts" / "codex_review_qa_execute.py",
        effective_root / "schemas" / "codex_review_qa_execution.schema.json",
        effective_root / "templates" / "codex_review_qa_execution.template.json",
    ]
    for path in required_paths:
        if not path.exists():
            errors.append(f"{path.relative_to(effective_root)}: required Codex review/QA execution asset is missing")
    return errors


def export_codex_review_qa_bundle(
    output_root: Path,
    *,
    root: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    effective_root = (root or repo_root()).resolve()
    effective_output_root = output_root.expanduser().resolve()
    catalog = expected_codex_review_qa_catalog(effective_root)
    exported_paths: list[str] = []

    for spec in catalog.templates:
        export_path = effective_output_root / spec.export_path
        if export_path.exists() and not force:
            raise FileExistsError(f"Refusing to replace existing review/QA export at {export_path} without --force.")
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
        raise FileExistsError(f"Refusing to replace existing review/QA catalog export at {export_catalog_path} without --force.")
    export_catalog_path.parent.mkdir(parents=True, exist_ok=True)
    export_catalog_path.write_text(json.dumps(export_catalog_payload, indent=2) + "\n", encoding="utf-8")

    return {
        "catalog_path": str(export_catalog_path),
        "export_root": str(effective_output_root),
        "exported_paths": exported_paths,
        "template_count": len(exported_paths),
    }


def execute_codex_review_qa(
    options: CodexReviewQaExecutionOptions,
    *,
    root: Path | None = None,
) -> CodexReviewQaExecutionReport:
    effective_root = (root or repo_root()).resolve()
    effective_output_root = options.output_root.expanduser().resolve()
    _prepare_output_root(effective_output_root, force=options.force)

    if options.workflow_id == "pull_request_review":
        report = _execute_pull_request_review(options, effective_root, effective_output_root)
    elif options.workflow_id == "public_docs_visual_qa":
        report = _execute_public_docs_visual_qa(options, effective_root, effective_output_root)
    else:
        raise ValueError(
            f"Unsupported Codex review/QA workflow {options.workflow_id!r}. "
            "Expected one of: pull_request_review, public_docs_visual_qa."
        )

    report_path = effective_output_root / "report.json"
    report_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    return report


def _prepare_output_root(output_root: Path, *, force: bool) -> None:
    if output_root.exists():
        if not force:
            raise FileExistsError(f"Refusing to replace existing review/QA output at {output_root} without --force.")
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)


def _execute_pull_request_review(
    options: CodexReviewQaExecutionOptions,
    root: Path,
    output_root: Path,
) -> CodexReviewQaExecutionReport:
    steps: list[CodexReviewQaExecutionStep] = []
    artifacts: list[CodexReviewQaExecutionArtifact] = []

    branch_name_completed = _run_command(["git", "rev-parse", "--abbrev-ref", options.head_ref], cwd=root)
    head_completed = _run_command(["git", "rev-parse", options.head_ref], cwd=root)
    base_completed = _run_command(["git", "rev-parse", options.base_ref], cwd=root)
    merge_base_completed = _run_command(["git", "merge-base", options.base_ref, options.head_ref], cwd=root)
    status_completed = _run_command(["git", "status", "--short"], cwd=root)

    git_commands = [
        ("branch_name", branch_name_completed),
        ("head_ref", head_completed),
        ("base_ref", base_completed),
        ("merge_base", merge_base_completed),
        ("git_status", status_completed),
    ]
    failed_git = [(name, completed) for name, completed in git_commands if completed.returncode != 0]
    if failed_git:
        steps.append(
            CodexReviewQaExecutionStep(
                name="review_target",
                status=ReleaseCheckStatus.BLOCKED,
                summary="Git review target resolution failed before the review evidence bundle could be built.",
                details={
                    "failures": [
                        {
                            "name": name,
                            "returncode": completed.returncode,
                            "stdout": completed.stdout,
                            "stderr": completed.stderr,
                        }
                        for name, completed in failed_git
                    ]
                },
                guidance="Resolve the Git reference failure, then rerun the review evidence helper from the repo root.",
            )
        )
        return _build_execution_report(
            workflow_id="pull_request_review",
            root=root,
            output_root=output_root,
            steps=steps,
            artifacts=artifacts,
            summary="The pull-request review evidence bundle could not be prepared because Git target resolution failed.",
        )

    branch_name = branch_name_completed.stdout.strip()
    head_commit = head_completed.stdout.strip()
    base_commit = base_completed.stdout.strip()
    merge_base = merge_base_completed.stdout.strip()
    diff_range = [merge_base] if options.head_ref == "HEAD" else [merge_base, options.head_ref]

    name_only_completed = _run_command(["git", "diff", "--name-only", *diff_range], cwd=root)
    name_status_completed = _run_command(["git", "diff", "--name-status", *diff_range], cwd=root)
    stat_completed = _run_command(["git", "diff", "--stat", *diff_range], cwd=root)
    patch_completed = _run_command(["git", "diff", *diff_range], cwd=root)
    diff_commands = [
        ("name_only", name_only_completed),
        ("name_status", name_status_completed),
        ("diff_stat", stat_completed),
        ("patch", patch_completed),
    ]
    failed_diff = [(name, completed) for name, completed in diff_commands if completed.returncode != 0]
    if failed_diff:
        steps.append(
            CodexReviewQaExecutionStep(
                name="diff_capture",
                status=ReleaseCheckStatus.BLOCKED,
                summary="The review target was resolved, but Git diff capture failed.",
                details={
                    "branch": branch_name,
                    "base_ref": options.base_ref,
                    "head_ref": options.head_ref,
                    "merge_base": merge_base,
                    "diff_range": diff_range,
                    "failures": [
                        {
                            "name": name,
                            "returncode": completed.returncode,
                            "stdout": completed.stdout,
                            "stderr": completed.stderr,
                        }
                        for name, completed in failed_diff
                    ],
                },
                guidance="Ensure the selected base/head refs are valid in this checkout, then rerun the helper.",
            )
        )
        return _build_execution_report(
            workflow_id="pull_request_review",
            root=root,
            output_root=output_root,
            steps=steps,
            artifacts=artifacts,
            summary="The pull-request review evidence bundle could not be completed because Git diff capture failed.",
        )

    changed_files = [line for line in name_only_completed.stdout.splitlines() if line.strip()]
    review_target_payload = {
        "branch": branch_name,
        "base_ref": options.base_ref,
        "head_ref": options.head_ref,
        "base_commit": base_commit,
        "head_commit": head_commit,
        "merge_base": merge_base,
        "diff_range": diff_range,
        "changed_files": changed_files,
        "changed_file_count": len(changed_files),
        "dirty_status": [line for line in status_completed.stdout.splitlines() if line.strip()],
    }
    review_target_path = output_root / "review_target.json"
    _write_json(review_target_path, review_target_payload)
    diff_stat_path = output_root / "diff_stat.txt"
    diff_stat_path.write_text(stat_completed.stdout, encoding="utf-8")
    name_status_path = output_root / "name_status.txt"
    name_status_path.write_text(name_status_completed.stdout, encoding="utf-8")
    changed_files_path = output_root / "changed_files.txt"
    changed_files_path.write_text(name_only_completed.stdout, encoding="utf-8")
    patch_path = output_root / "diff.patch"
    patch_path.write_text(patch_completed.stdout, encoding="utf-8")
    git_status_path = output_root / "git_status.txt"
    git_status_path.write_text(status_completed.stdout, encoding="utf-8")

    artifacts.extend(
        [
            _artifact("review_target", "Review target metadata", "json", review_target_path, "Resolved branch and diff target metadata."),
            _artifact("diff_stat", "Diff stat", "text", diff_stat_path, "Summarizes the change size against the selected base ref."),
            _artifact("name_status", "Changed file status list", "text", name_status_path, "Lists changed files and their Git status codes."),
            _artifact("changed_files", "Changed files", "text", changed_files_path, "Lists the changed files in the selected review target."),
            _artifact("patch", "Unified diff", "text", patch_path, "Contains the full unified diff against the selected base ref."),
            _artifact("git_status", "Working tree status", "text", git_status_path, "Captures the current working tree state when the evidence bundle was prepared."),
        ]
    )

    review_target_status = ReleaseCheckStatus.READY if changed_files else ReleaseCheckStatus.ATTENTION
    review_target_summary = (
        f"Prepared local review evidence for {branch_name} against {options.base_ref} with {len(changed_files)} changed file(s)."
        if changed_files
        else f"Prepared local review evidence for {branch_name}, but no changed files were found against {options.base_ref}."
    )
    steps.append(
        CodexReviewQaExecutionStep(
            name="review_target",
            status=review_target_status,
            summary=review_target_summary,
            details=review_target_payload,
            guidance="Review the changed-files and diff artifacts first so the Codex review stays anchored to the real branch delta.",
        )
    )

    from .release_surface import collect_release_preflight

    release_preflight = collect_release_preflight()
    release_preflight_path = output_root / "release_preflight.json"
    _write_json(release_preflight_path, release_preflight.to_dict())
    artifacts.append(
        _artifact(
            "release_preflight",
            "Release preflight snapshot",
            "json",
            release_preflight_path,
            "Captures the current release-surface and operator-readiness state for the same checkout.",
        )
    )

    if release_preflight.release_surface_ready:
        preflight_status = ReleaseCheckStatus.READY if release_preflight.operator_ready else ReleaseCheckStatus.ATTENTION
    else:
        preflight_status = ReleaseCheckStatus.BLOCKED
    preflight_summary = (
        "The release-surface snapshot is ready and the operator environment is fully ready."
        if release_preflight.operator_ready
        else "The release-surface snapshot is ready, but the operator environment still has attention items."
        if release_preflight.release_surface_ready
        else "The release-surface snapshot found structural blockers that should be part of the review."
    )
    steps.append(
        CodexReviewQaExecutionStep(
            name="release_preflight",
            status=preflight_status,
            summary=preflight_summary,
            details={
                "overall_status": release_preflight.overall_status.value,
                "release_surface_ready": release_preflight.release_surface_ready,
                "operator_ready": release_preflight.operator_ready,
                "check_count": len(release_preflight.checks),
            },
            guidance="Use the nested release_preflight.json artifact to call out release-surface drift or readiness regressions in the review.",
        )
    )

    if review_target_status == ReleaseCheckStatus.READY and preflight_status == ReleaseCheckStatus.READY:
        summary = "The pull-request review evidence bundle is ready for Codex review."
    elif preflight_status == ReleaseCheckStatus.BLOCKED:
        summary = "The pull-request review evidence bundle is ready, but the release-surface snapshot found structural blockers."
    else:
        summary = "The pull-request review evidence bundle is ready, but it still includes attention items that the review should cover explicitly."
    return _build_execution_report(
        workflow_id="pull_request_review",
        root=root,
        output_root=output_root,
        steps=steps,
        artifacts=artifacts,
        summary=summary,
    )


def _execute_public_docs_visual_qa(
    options: CodexReviewQaExecutionOptions,
    root: Path,
    output_root: Path,
) -> CodexReviewQaExecutionReport:
    steps: list[CodexReviewQaExecutionStep] = []
    artifacts: list[CodexReviewQaExecutionArtifact] = []
    build_command = list(options.build_command or ("uv", "run", "mkdocs", "build", "--strict"))
    build_completed = _run_command(build_command, cwd=root)
    build_log_path = output_root / "build.log"
    build_log_path.write_text(
        "\n".join(
            [
                f"$ {' '.join(build_command)}",
                "",
                "## stdout",
                build_completed.stdout,
                "",
                "## stderr",
                build_completed.stderr,
            ]
        ).rstrip()
        + "\n",
        encoding="utf-8",
    )
    artifacts.append(
        _artifact(
            "build_log",
            "MkDocs build log",
            "text",
            build_log_path,
            "Captured stdout and stderr from the docs build step.",
        )
    )
    site_dir = (options.site_dir or (root / "site")).resolve()
    if build_completed.returncode != 0:
        steps.append(
            CodexReviewQaExecutionStep(
                name="mkdocs_build",
                status=ReleaseCheckStatus.BLOCKED,
                summary="The docs build failed, so the public visual-QA bundle could not be prepared.",
                details={
                    "command": build_command,
                    "returncode": build_completed.returncode,
                    "site_dir": str(site_dir),
                },
                guidance="Fix the mkdocs build failure first. The build log artifact captures the exact stdout and stderr.",
            )
        )
        return _build_execution_report(
            workflow_id="public_docs_visual_qa",
            root=root,
            output_root=output_root,
            steps=steps,
            artifacts=artifacts,
            summary="The public docs visual-QA evidence bundle is blocked because the docs build failed.",
        )

    steps.append(
        CodexReviewQaExecutionStep(
            name="mkdocs_build",
            status=ReleaseCheckStatus.READY,
            summary="The public docs built successfully with uv run mkdocs build --strict.",
            details={"command": build_command, "returncode": 0, "site_dir": str(site_dir)},
            guidance="If you need a live preview, serve the site directory locally or inspect the built HTML paths directly in Codex.",
        )
    )

    page_manifest, missing_pages, missing_assets = _build_public_docs_manifest(root, site_dir)
    visual_targets_path = output_root / "visual_targets.json"
    _write_json(visual_targets_path, page_manifest)
    artifacts.append(
        _artifact(
            "visual_targets",
            "Visual target manifest",
            "json",
            visual_targets_path,
            "Lists the key public pages, their built HTML paths, and the image assets referenced from those pages.",
        )
    )

    preview_targets_path = output_root / "preview_targets.json"
    preview_payload = {
        "site_dir": str(site_dir),
        "pages": [
            {
                "page_id": page["page_id"],
                "name": page["name"],
                "route": page["route"],
                "html_path": page["html_path"],
                "file_url": Path(page["html_path"]).resolve().as_uri() if page["exists"] else None,
            }
            for page in page_manifest["pages"]
        ],
    }
    _write_json(preview_targets_path, preview_payload)
    artifacts.append(
        _artifact(
            "preview_targets",
            "Preview target manifest",
            "json",
            preview_targets_path,
            "Provides browser-ready file URLs for the built HTML pages when local preview is sufficient.",
        )
    )

    if missing_pages or missing_assets:
        manifest_status = ReleaseCheckStatus.BLOCKED
        manifest_summary = "The visual target manifest found missing built pages or missing image assets."
    else:
        manifest_status = ReleaseCheckStatus.ATTENTION
        manifest_summary = "The built page and asset manifest is complete, but the public docs still need live visual review for layout and typography defects."

    steps.append(
        CodexReviewQaExecutionStep(
            name="page_manifest",
            status=manifest_status,
            summary=manifest_summary,
            details={
                "target_count": len(page_manifest["pages"]),
                "missing_pages": missing_pages,
                "missing_assets": missing_assets,
            },
            guidance="Use the preview target manifest in Codex, then look for clipped text, broken images, and layout regressions on the listed pages.",
        )
    )

    summary = (
        "The docs visual-QA evidence bundle is ready, but the built page manifest still needs live visual inspection for layout and typography defects."
        if manifest_status == ReleaseCheckStatus.ATTENTION
        else "The docs visual-QA evidence bundle found structural page or asset issues before live visual inspection."
    )
    return _build_execution_report(
        workflow_id="public_docs_visual_qa",
        root=root,
        output_root=output_root,
        steps=steps,
        artifacts=artifacts,
        summary=summary,
    )


def _run_command(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True, cwd=cwd)


def _build_public_docs_manifest(root: Path, site_dir: Path) -> tuple[dict[str, Any], list[str], list[str]]:
    pages: list[dict[str, Any]] = []
    missing_pages: list[str] = []
    missing_assets: list[str] = []

    for target in _PUBLIC_DOCS_VISUAL_TARGETS:
        html_relative_path = Path(target["site_path"]).relative_to("site")
        html_path = (site_dir / html_relative_path).resolve()
        page_record: dict[str, Any] = {
            **target,
            "html_path": str(html_path),
            "exists": html_path.exists(),
            "images": [],
        }
        if not html_path.exists():
            missing_pages.append(target["page_id"])
            pages.append(page_record)
            continue

        html_text = html_path.read_text(encoding="utf-8")
        images: list[dict[str, Any]] = []
        for src in _IMAGE_SRC_PATTERN.findall(html_text):
            if src.startswith(("http://", "https://", "data:")):
                resolved_path = src
                exists = True
            elif src.startswith("/"):
                resolved_path = str((site_dir / src.lstrip("/")).resolve())
                exists = (site_dir / src.lstrip("/")).exists()
            else:
                resolved_path = str((html_path.parent / src).resolve())
                exists = (html_path.parent / src).exists()
            if not exists and isinstance(resolved_path, str):
                missing_assets.append(f"{target['page_id']}::{src}")
            images.append({"src": src, "resolved_path": resolved_path, "exists": exists})
        page_record["images"] = images
        pages.append(page_record)

    manifest = {
        "site_dir": str(site_dir),
        "pages": pages,
    }
    return manifest, missing_pages, missing_assets


def _build_execution_report(
    *,
    workflow_id: str,
    root: Path,
    output_root: Path,
    steps: list[CodexReviewQaExecutionStep],
    artifacts: list[CodexReviewQaExecutionArtifact],
    summary: str,
) -> CodexReviewQaExecutionReport:
    overall_status = ReleaseCheckStatus.READY
    for step in steps:
        if step.status == ReleaseCheckStatus.BLOCKED:
            overall_status = ReleaseCheckStatus.BLOCKED
            break
        if step.status == ReleaseCheckStatus.ATTENTION:
            overall_status = ReleaseCheckStatus.ATTENTION

    return CodexReviewQaExecutionReport(
        workflow_id=workflow_id,
        generated_at=datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        repo_root=str(root),
        output_root=str(output_root),
        overall_status=overall_status,
        summary=summary,
        artifacts=artifacts,
        steps=steps,
    )


def _artifact(artifact_id: str, name: str, kind: str, path: Path, summary: str) -> CodexReviewQaExecutionArtifact:
    return CodexReviewQaExecutionArtifact(
        artifact_id=artifact_id,
        name=name,
        kind=kind,
        path=str(path),
        summary=summary,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
