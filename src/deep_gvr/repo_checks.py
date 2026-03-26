from __future__ import annotations

import json
import re
from pathlib import Path

from .json_schema import SchemaValidationError, validate

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
    "simulator.md": ["python adapters/<simulator>_adapter.py", "confidence assessment", "If the simulation fails"],
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def run_all_checks() -> list[str]:
    root = repo_root()
    messages: list[str] = []
    messages.extend(check_markdown_links(root))
    messages.extend(check_plan_files(root))
    messages.extend(check_workflow_docs(root))
    messages.extend(check_prompt_files(root))
    messages.extend(check_schemas_and_templates(root))
    messages.extend(check_architecture_boundaries(root))
    return messages


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
        "candidate_solution.template.json": "candidate_solution.schema.json",
        "verification_report.template.json": "verification_report.schema.json",
        "sim_spec.template.json": "sim_spec.schema.json",
        "sim_results.template.json": "sim_results.schema.json",
        "evidence_record.template.json": "evidence.schema.json",
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
    return errors


def check_architecture_boundaries(root: Path) -> list[str]:
    errors: list[str] = []
    for path in (root / "src" / "deep_gvr").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if re.search(r"^\s*(from|import)\s+hermes\b", text, flags=re.MULTILINE):
            errors.append(f"{path.relative_to(root)}: direct Hermes imports are not allowed in readiness scaffolding")
    return errors
