from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import yaml

from .json_schema import SchemaValidationError, validate
from .release_surface import codex_plugin_surface_errors, publication_manifest_errors, release_metadata_errors

REQUIRED_PLAN_HEADINGS = [
    "# ",
    "## Purpose / Big Picture",
    "## Branch Strategy",
    "## Commit Plan",
    "## Progress",
    "## Surprises & Discoveries",
    "## Decision Log",
    "## Outcomes & Retrospective",
    "## Context and Orientation",
    "## Plan of Work",
    "## Concrete Steps",
    "## Validation and Acceptance",
    "## Merge, Push, and Cleanup",
    "## Idempotence and Recovery",
    "## Interfaces and Dependencies",
]

REQUIRED_WORKFLOW_PHRASES = {
    "AGENTS.md": [
        "feature branch",
        "sensible, reviewable chunks",
        "concise descriptive commit messages",
        "Merge locally",
        "Push after the merge result is validated",
        "Clean up the feature branch",
    ],
    "CONTRIBUTING.md": [
        "create a feature branch",
        "Commit in sensible chunks",
        "Merge locally",
        "Push the integrated branch",
        "Delete the feature branch",
    ],
    "PLANS.md": [
        "branch name or naming rule",
        "expected commit boundaries",
        "local merge steps",
        "push",
        "cleanup",
    ],
    ".github/PULL_REQUEST_TEMPLATE.md": [
        "work happened on a feature branch",
        "changes were committed in sensible chunks",
        "local merge completed only after validation passed",
        "integrated branch is ready to push",
        "feature branch cleanup is planned",
    ],
}

REQUIRED_PROMPT_MARKERS = {
    "generator.md": ["## Candidate Solution", "### Hypothesis", "### References"],
    "verifier.md": ["## Verification Report", "### Verdict:", "### Tier 1: Analytical Verification"],
    "reviser.md": ["### Revision Notes", "candidate solution", "specific flaws"],
    "formalizer.md": ["## Formal Verification Results", "Aristotle MCP", "Do not fabricate proof success"],
    "simulator.md": ["analysis adapter", "confidence assessment", "If the analysis fails"],
}

OPEN_ARCHITECTURE_ITEMS = {
    "subagent-capability-closure": "26-subagent-capability-closure.md",
    "opengauss-formal-backend": "31-opengauss-formal-backend.md",
}

ALLOWED_OPEN_ARCHITECTURE_STATUSES = {"temporary_gap", "planned", "blocked_external"}

REQUIRED_RETIREMENT_REFERENCES = {
    "SKILL.md": [
        "Retirement slice: [plans/26-subagent-capability-closure.md](plans/26-subagent-capability-closure.md)",
    ],
    "docs/capability-probes.md": [
        "Retirement slice: [26-subagent-capability-closure.md](../plans/26-subagent-capability-closure.md)",
    ],
}

PUBLIC_DOCS = [
    "README.md",
    "docs/index.md",
    "docs/start-here.md",
    "docs/codex-local.md",
    "docs/codex-plugin.md",
    "docs/quickstart.md",
    "docs/concepts.md",
    "docs/domain-portfolio.md",
    "docs/examples.md",
    "docs/faq.md",
    "docs/system-overview.md",
    "docs/release-workflow.md",
    "docs/deep-gvr-architecture.md",
]

PUBLIC_DOC_LINK_REQUIREMENTS = {
    "README.md": [
        "docs/index.md",
        "docs/start-here.md",
        "docs/codex-local.md",
        "docs/codex-plugin.md",
        "docs/quickstart.md",
        "docs/concepts.md",
        "docs/domain-portfolio.md",
        "docs/examples.md",
        "docs/faq.md",
        "docs/system-overview.md",
        "docs/release-workflow.md",
        "docs/deep-gvr-architecture.md",
    ],
    "docs/start-here.md": [
        "index.md",
        "codex-local.md",
        "codex-plugin.md",
        "quickstart.md",
        "concepts.md",
        "domain-portfolio.md",
        "examples.md",
        "faq.md",
        "system-overview.md",
        "release-workflow.md",
        "deep-gvr-architecture.md",
    ],
}

PUBLIC_DOC_INTERNAL_LINK_TARGETS = {
    "AGENTS.md",
    "PLANS.md",
    "CONTRIBUTING.md",
    "SKILL.md",
    "docs/README.md",
    "docs/capability-probes.md",
    "docs/contracts-and-artifacts.md",
    "eval/README.md",
}

PUBLIC_DOC_DISALLOWED_PATTERNS = [
    re.compile(r"retirement slice", flags=re.IGNORECASE),
    re.compile(r"temporary gap", flags=re.IGNORECASE),
    re.compile(r"plans/\d{2}-", flags=re.IGNORECASE),
    re.compile(r"\bplan\s+\d+\b", flags=re.IGNORECASE),
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def run_all_checks() -> list[str]:
    root = repo_root()
    messages: list[str] = []
    messages.extend(check_markdown_links(root))
    messages.extend(check_public_docs_surface(root))
    messages.extend(check_plan_files(root))
    messages.extend(check_workflow_docs(root))
    messages.extend(check_prompt_files(root))
    messages.extend(check_schemas_and_templates(root))
    messages.extend(check_release_surfaces(root))
    messages.extend(check_architecture_completion_tracking(root))
    messages.extend(check_architecture_boundaries(root))
    return messages


def check_public_docs_surface(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in PUBLIC_DOCS:
        path = root / relative
        if not path.exists():
            errors.append(f"{relative}: required public doc is missing")
            continue

    for relative, required_targets in PUBLIC_DOC_LINK_REQUIREMENTS.items():
        path = root / relative
        if not path.exists():
            continue
        targets = set(_markdown_link_targets(path))
        for required_target in required_targets:
            if required_target not in targets:
                errors.append(f"{relative}: missing required public-doc link {required_target!r}")

    for relative in PUBLIC_DOCS:
        path = root / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        targets = set(_markdown_link_targets(path))
        for internal_target in PUBLIC_DOC_INTERNAL_LINK_TARGETS:
            if internal_target in targets:
                errors.append(
                    f"{relative}: should not link public readers to internal doc {internal_target!r}"
                )
        for pattern in PUBLIC_DOC_DISALLOWED_PATTERNS:
            if pattern.search(text):
                errors.append(
                    f"{relative}: public docs should not contain backlog/internal phrase matching "
                    f"{pattern.pattern!r}"
                )
    return errors


def _markdown_link_targets(path: Path) -> list[str]:
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    text = path.read_text(encoding="utf-8")
    return [match.group(1) for match in link_pattern.finditer(text)]


def check_markdown_links(root: Path) -> list[str]:
    errors: list[str] = []
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for path in root.rglob("*.md"):
        if ".git" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for match in link_pattern.finditer(text):
            target = match.group(1)
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                errors.append(f"{path.relative_to(root)}: broken link target {target}")
    return errors


def check_plan_files(root: Path) -> list[str]:
    errors: list[str] = []
    plans_dir = root / "plans"
    for path in plans_dir.glob("*.md"):
        if path.name == "README.md":
            continue
        text = path.read_text(encoding="utf-8")
        for heading in REQUIRED_PLAN_HEADINGS:
            if heading not in text:
                errors.append(f"{path.relative_to(root)}: missing required heading {heading}")
    return errors


def check_workflow_docs(root: Path) -> list[str]:
    errors: list[str] = []
    for relative, phrases in REQUIRED_WORKFLOW_PHRASES.items():
        text = (root / relative).read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase not in text:
                errors.append(f"{relative}: missing required workflow phrase {phrase!r}")
    return errors


def check_prompt_files(root: Path) -> list[str]:
    errors: list[str] = []
    prompts_dir = root / "prompts"
    for name, markers in REQUIRED_PROMPT_MARKERS.items():
        text = (prompts_dir / name).read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                errors.append(f"prompts/{name}: missing prompt marker {marker!r}")
    return errors


def check_schemas_and_templates(root: Path) -> list[str]:
    errors: list[str] = []
    schema_dir = root / "schemas"
    template_dir = root / "templates"
    schema_map = {
        "config.template.json": "config.schema.json",
        "benchmark_suite.template.json": "benchmark_suite.schema.json",
        "candidate_solution.template.json": "candidate_solution.schema.json",
        "eval_consistency.template.json": "eval_consistency.schema.json",
        "eval_results.template.json": "eval_results.schema.json",
        "verification_report.template.json": "verification_report.schema.json",
        "release_preflight.template.json": "release_preflight.schema.json",
        "release_publication.template.json": "release_publication.schema.json",
        "codex_plugin.template.json": "codex_plugin.schema.json",
        "codex_plugin_marketplace.template.json": "codex_plugin_marketplace.schema.json",
        "auto_improve_evaluation.template.json": "auto_improve_evaluation.schema.json",
        "analysis_spec.template.json": "analysis_spec.schema.json",
        "analysis_results.template.json": "analysis_results.schema.json",
        "sim_spec.template.json": "sim_spec.schema.json",
        "sim_results.template.json": "sim_results.schema.json",
        "evidence_record.template.json": "evidence.schema.json",
        "hermes_memory_summary.template.json": "hermes_memory_summary.schema.json",
        "parallax_manifest.template.json": "parallax_manifest.schema.json",
        "session_checkpoint.template.json": "session_checkpoint.schema.json",
        "session_index.template.json": "session_index.schema.json",
        "capability_probe.template.json": "capability_probe.schema.json",
    }
    for template_name, schema_name in schema_map.items():
        schema = json.loads((schema_dir / schema_name).read_text(encoding="utf-8"))
        instance = json.loads((template_dir / template_name).read_text(encoding="utf-8"))
        try:
            validate(instance, schema)
        except SchemaValidationError as exc:
            errors.append(f"{template_name}: schema validation failed: {exc}")

    direct_artifacts = {
        "eval/known_problems.json": "benchmark_suite.schema.json",
        "eval/results/baseline_results.json": "eval_results.schema.json",
        "release/agentskills.publication.json": "release_publication.schema.json",
        "plugins/deep-gvr/.codex-plugin/plugin.json": "codex_plugin.schema.json",
        ".agents/plugins/marketplace.json": "codex_plugin_marketplace.schema.json",
    }
    for artifact_name, schema_name in direct_artifacts.items():
        artifact_path = root / artifact_name
        if not artifact_path.exists():
            errors.append(f"{artifact_name}: required artifact is missing")
            continue
        schema = json.loads((schema_dir / schema_name).read_text(encoding="utf-8"))
        instance = json.loads(artifact_path.read_text(encoding="utf-8"))
        try:
            validate(instance, schema)
        except SchemaValidationError as exc:
            errors.append(f"{artifact_name}: schema validation failed: {exc}")

    yaml_template = template_dir / "config.template.yaml"
    if not yaml_template.exists():
        errors.append("templates/config.template.yaml: required YAML config template is missing")
    else:
        schema = json.loads((schema_dir / "config.schema.json").read_text(encoding="utf-8"))
        instance = yaml.safe_load(yaml_template.read_text(encoding="utf-8"))
        try:
            validate(instance, schema)
        except SchemaValidationError as exc:
            errors.append(f"config.template.yaml: schema validation failed: {exc}")
    return errors


def check_architecture_boundaries(root: Path) -> list[str]:
    errors: list[str] = []
    for path in (root / "src" / "deep_gvr").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if re.search(r"^\s*(from|import)\s+hermes\b", text, flags=re.MULTILINE):
            errors.append(f"{path.relative_to(root)}: direct Hermes imports are not allowed in readiness scaffolding")
    return errors


def check_release_surfaces(root: Path) -> list[str]:
    errors: list[str] = []
    if 'deep-gvr = "deep_gvr.cli:main"' not in (root / "pyproject.toml").read_text(encoding="utf-8"):
        errors.append("pyproject.toml: missing deep-gvr console entrypoint")
    executable_files = [
        root / "scripts" / "install.sh",
        root / "scripts" / "install_codex.sh",
        root / "scripts" / "setup_mcp.sh",
        root / "scripts" / "codex_preflight.py",
        root / "scripts" / "release_preflight.py",
        root / "scripts" / "check_release_version.py",
        root / "scripts" / "render_release_notes.py",
        root / "scripts" / "evaluate_auto_improve.py",
        root / "eval" / "run_eval.py",
    ]
    for path in executable_files:
        if not path.exists():
            errors.append(f"{path.relative_to(root)}: required release helper is missing")
            continue
        if path.stat().st_mode & 0o111 == 0:
            errors.append(f"{path.relative_to(root)}: expected executable bit to be set")
    required_docs = [
        root / "CHANGELOG.md",
        root / "mkdocs.yml",
        root / "docs" / "index.md",
        root / "docs" / "codex-local.md",
        root / "docs" / "codex-plugin.md",
        root / "docs" / "plugin-privacy.md",
        root / "docs" / "plugin-terms.md",
        root / "docs" / "release-workflow.md",
        root / "codex_skill" / "SKILL.md",
        root / "plugins" / "deep-gvr" / ".codex-plugin" / "plugin.json",
        root / ".agents" / "plugins" / "marketplace.json",
        root / "release" / "agentskills.publication.json",
        root / "release" / "release-checklist.md",
        root / ".github" / "workflows" / "docs.yml",
        root / ".github" / "workflows" / "release.yml",
    ]
    for path in required_docs:
        if not path.exists():
            errors.append(f"{path.relative_to(root)}: required release-surface asset is missing")
    errors.extend(publication_manifest_errors(root))
    errors.extend(codex_plugin_surface_errors(root))
    errors.extend(release_metadata_errors(root))
    docs_workflow_path = root / ".github" / "workflows" / "docs.yml"
    if docs_workflow_path.exists():
        docs_workflow = docs_workflow_path.read_text(encoding="utf-8")
        if "actions/upload-pages-artifact@v4" not in docs_workflow:
            errors.append(".github/workflows/docs.yml: missing Pages artifact upload step")
        if "actions/deploy-pages@v4" not in docs_workflow:
            errors.append(".github/workflows/docs.yml: missing Pages deploy step")
        if "github.event_name == 'workflow_dispatch'" in docs_workflow:
            errors.append(
                ".github/workflows/docs.yml: docs deployment should not be gated to workflow_dispatch now that Pages is enabled"
            )
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    dev_dependencies = ((pyproject.get("project") or {}).get("optional-dependencies") or {}).get("dev", [])
    if "mkdocs>=1.6.0" not in dev_dependencies:
        errors.append("pyproject.toml: dev dependencies must include mkdocs>=1.6.0")
    if "mkdocs-material>=9.6.0" not in dev_dependencies:
        errors.append("pyproject.toml: dev dependencies must include mkdocs-material>=9.6.0")
    return errors


def check_architecture_completion_tracking(root: Path) -> list[str]:
    errors: list[str] = []
    ledger_path = root / "docs" / "architecture-status.md"
    if not ledger_path.exists():
        return ["docs/architecture-status.md: required architecture ledger is missing"]

    text = ledger_path.read_text(encoding="utf-8")
    if "## Open Architecture Items" not in text:
        errors.append("docs/architecture-status.md: missing '## Open Architecture Items' section")
    else:
        errors.extend(_check_open_architecture_table(text))

    for relative_path, required_snippets in REQUIRED_RETIREMENT_REFERENCES.items():
        body = (root / relative_path).read_text(encoding="utf-8")
        for snippet in required_snippets:
            if snippet not in body:
                errors.append(f"{relative_path}: missing retirement-slice reference {snippet!r}")
    return errors


def _check_open_architecture_table(text: str) -> list[str]:
    errors: list[str] = []
    rows = _extract_open_architecture_rows(text)
    seen: dict[str, str] = {}

    for line in rows:
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) != 7:
            errors.append(
                "docs/architecture-status.md: open architecture row must have 7 columns: "
                f"{line.strip()}"
            )
            continue
        item_id, status, _target, _current_state, _dependency, owning_slice, retirement_criteria = parts
        if item_id in seen:
            errors.append(f"docs/architecture-status.md: duplicate open architecture item {item_id!r}")
            continue
        seen[item_id] = status
        if item_id not in OPEN_ARCHITECTURE_ITEMS:
            errors.append(f"docs/architecture-status.md: unexpected open architecture item {item_id!r}")
            continue
        if status not in ALLOWED_OPEN_ARCHITECTURE_STATUSES:
            errors.append(
                "docs/architecture-status.md: "
                f"item {item_id!r} must use one of {sorted(ALLOWED_OPEN_ARCHITECTURE_STATUSES)}, got {status!r}"
            )
        expected_plan = OPEN_ARCHITECTURE_ITEMS[item_id]
        expected_link = f"[{expected_plan}](../plans/{expected_plan})"
        if expected_link not in owning_slice:
            errors.append(
                "docs/architecture-status.md: "
                f"item {item_id!r} must link to owning slice {expected_link!r}"
            )
        if not retirement_criteria:
            errors.append(
                "docs/architecture-status.md: "
                f"item {item_id!r} must include retirement criteria"
            )

    for item_id in OPEN_ARCHITECTURE_ITEMS:
        if item_id not in seen:
            errors.append(
                f"docs/architecture-status.md: missing open architecture item {item_id!r}"
            )
    return errors


def _extract_open_architecture_rows(text: str) -> list[str]:
    in_section = False
    rows: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = line == "## Open Architecture Items"
            continue
        if not in_section:
            continue
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if stripped.startswith("| Item ID ") or stripped.startswith("|---"):
            continue
        rows.append(line)
    return rows
