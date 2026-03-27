from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

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
    "formalizer.md": ["## Formal Verification Results", "Aristotle MCP", "Do not fabricate proof success"],
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
    messages.extend(check_release_surfaces(root))
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
        "benchmark_suite.template.json": "benchmark_suite.schema.json",
        "candidate_solution.template.json": "candidate_solution.schema.json",
        "eval_results.template.json": "eval_results.schema.json",
        "verification_report.template.json": "verification_report.schema.json",
        "sim_spec.template.json": "sim_spec.schema.json",
        "sim_results.template.json": "sim_results.schema.json",
        "evidence_record.template.json": "evidence.schema.json",
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
        root / "scripts" / "setup_mcp.sh",
        root / "eval" / "run_eval.py",
    ]
    for path in executable_files:
        if not path.exists():
            errors.append(f"{path.relative_to(root)}: required release helper is missing")
            continue
        if path.stat().st_mode & 0o111 == 0:
            errors.append(f"{path.relative_to(root)}: expected executable bit to be set")
    return errors
