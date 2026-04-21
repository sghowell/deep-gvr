from __future__ import annotations

import json
import os
import re
import shutil
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .codex_automations import automation_catalog_path, codex_automation_surface_errors
from .codex_review_qa import codex_review_qa_surface_errors, review_qa_catalog_path
from .contracts import (
    DeepGvrConfig,
    ProbeStatus,
    ReleaseCheck,
    ReleaseCheckStatus,
    ReleasePreflightReport,
    ReleasePublicationManifest,
)
from .json_schema import SchemaValidationError, validate
from .probes import (
    probe_analysis_adapter_families,
    probe_aristotle_transport,
    probe_backend_dispatch,
    probe_mathcode_transport,
    probe_opengauss_transport,
)
from .runtime_config import default_config_path, load_runtime_config

_PUBLICATION_MANIFEST_PATH = Path("release/agentskills.publication.json")
_CHANGELOG_PATH = Path("CHANGELOG.md")
_CODEX_PLUGIN_MANIFEST_PATH = Path("plugins/deep-gvr/.codex-plugin/plugin.json")
_CODEX_PLUGIN_SKILL_PATH = Path("plugins/deep-gvr/skills/deep-gvr/SKILL.md")
_CODEX_PLUGIN_MARKETPLACE_PATH = Path(".agents/plugins/marketplace.json")
_PROVIDER_ENV_MAP = {
    "anthropic": ["ANTHROPIC_API_KEY"],
    "google": ["GOOGLE_API_KEY"],
    "nous": ["NOUS_API_KEY", "NOUS_API_TOKEN"],
    "openai": ["OPENAI_API_KEY"],
    "openrouter": ["OPENROUTER_API_KEY"],
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_skills_dir() -> Path:
    hermes_home = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes")).expanduser()
    return hermes_home / "skills"


def default_codex_skills_dir() -> Path:
    codex_home = Path(os.getenv("CODEX_HOME", Path.home() / ".codex")).expanduser()
    return codex_home / "skills"


def default_hermes_config_path() -> Path:
    hermes_home = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes")).expanduser()
    return hermes_home / "config.yaml"


def publication_manifest_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / _PUBLICATION_MANIFEST_PATH


def codex_plugin_manifest_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / _CODEX_PLUGIN_MANIFEST_PATH


def codex_plugin_skill_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / _CODEX_PLUGIN_SKILL_PATH


def codex_plugin_marketplace_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / _CODEX_PLUGIN_MARKETPLACE_PATH


def changelog_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / _CHANGELOG_PATH


def _schema_path(name: str, root: Path | None = None) -> Path:
    return (root or repo_root()) / "schemas" / name


def _skill_frontmatter(root: Path | None = None) -> dict[str, Any]:
    skill_path = (root or repo_root()) / "SKILL.md"
    payload = skill_path.read_text(encoding="utf-8")
    if not payload.startswith("---\n"):
        raise ValueError("SKILL.md is missing YAML frontmatter.")
    _, frontmatter, _ = payload.split("---", 2)
    return yaml.safe_load(frontmatter)


def _codex_skill_payload(root: Path | None = None) -> str:
    return ((root or repo_root()) / "codex_skill" / "SKILL.md").read_text(encoding="utf-8")


def _pyproject_metadata(root: Path | None = None) -> dict[str, Any]:
    pyproject_path = (root or repo_root()) / "pyproject.toml"
    return tomllib.loads(pyproject_path.read_text(encoding="utf-8"))


def project_version(root: Path | None = None) -> str:
    return str(_pyproject_metadata(root)["project"]["version"])


def expected_release_tag(root: Path | None = None) -> str:
    return f"v{project_version(root)}"


def expected_publication_manifest(root: Path | None = None) -> ReleasePublicationManifest:
    effective_root = root or repo_root()
    skill_manifest = _skill_frontmatter(effective_root)
    return ReleasePublicationManifest(
        name=skill_manifest["name"],
        version=project_version(effective_root),
        description=skill_manifest["description"],
        package_layout="hermes_skill_and_codex_surface_bundle",
        distribution_targets=["github", "agentskills.io"],
        skill_manifest_path="SKILL.md",
        codex_skill_manifest_path="codex_skill/SKILL.md",
        codex_plugin_manifest_path="plugins/deep-gvr/.codex-plugin/plugin.json",
        codex_plugin_skill_manifest_path="plugins/deep-gvr/skills/deep-gvr/SKILL.md",
        codex_plugin_marketplace_path=".agents/plugins/marketplace.json",
        codex_automation_catalog_path="codex_automations/catalog.json",
        codex_review_qa_catalog_path="codex_review_qa/catalog.json",
        readme_path="README.md",
        install_script="scripts/install.sh",
        preflight_script="scripts/release_preflight.py",
        setup_mcp_script="scripts/setup_mcp.sh",
        config_template_path="templates/config.template.yaml",
        benchmark_baseline_path="eval/results/baseline_results.json",
        public_commands=[
            "/deep-gvr <question>",
            "/deep-gvr resume <session_id>",
            'codex exec -C /path/to/deep-gvr "Use the deep-gvr skill to answer: <question>"',
            "uv run deep-gvr run \"<question>\"",
            "uv run deep-gvr resume <session_id>",
        ],
        operator_validation_commands=[
            "bash scripts/install.sh",
            "bash scripts/install_codex.sh",
            "python scripts/export_codex_automations.py --output-root /tmp/deep-gvr-codex-automations --force",
            "python scripts/export_codex_review_qa.py --output-root /tmp/deep-gvr-codex-review-qa --force",
            "uv run python scripts/release_preflight.py --operator --config ~/.hermes/deep-gvr/config.yaml",
            "uv run python scripts/codex_preflight.py --operator",
            "bash scripts/setup_mcp.sh --install --check",
        ],
        auto_improve=False,
        auto_improve_enablement=(
            "Run uv run python scripts/evaluate_auto_improve.py --output /tmp/deep-gvr-auto-improve/report.json, "
            "review the report, then set auto_improve to true in release/agentskills.publication.json only after "
            "human review and republish the same validated release bundle."
        ),
    )


def expected_codex_plugin_manifest(root: Path | None = None) -> dict[str, Any]:
    effective_root = root or repo_root()
    return {
        "name": "deep-gvr",
        "version": project_version(effective_root),
        "description": "Operate the deep-gvr verification workflow from Codex local as a packaged plugin surface.",
        "author": {
            "name": "Sean Howell",
            "url": "https://github.com/sghowell",
        },
        "homepage": "https://sghowell.github.io/deep-gvr/codex-plugin/",
        "repository": "https://github.com/sghowell/deep-gvr",
        "license": "MIT",
        "keywords": ["verification", "research", "science", "codex", "hermes"],
        "skills": "./skills/",
        "interface": {
            "displayName": "deep-gvr",
            "shortDescription": "Verification-first research workflow for Codex local",
            "longDescription": (
                "Use deep-gvr from Codex as a packaged local workflow over the same typed runtime, "
                "evidence system, and tiered verification stack used by the Hermes and CLI surfaces."
            ),
            "developerName": "Sean Howell",
            "category": "Coding",
            "capabilities": ["Interactive", "Write"],
            "websiteURL": "https://sghowell.github.io/deep-gvr/codex-plugin/",
            "privacyPolicyURL": "https://sghowell.github.io/deep-gvr/plugin-privacy/",
            "termsOfServiceURL": "https://sghowell.github.io/deep-gvr/plugin-terms/",
            "defaultPrompt": [
                "Use the deep-gvr plugin to investigate a technical claim with explicit evidence and tiered verification."
            ],
            "brandColor": "#0F7B6C",
            "composerIcon": "./assets/deep-gvr-plugin-small.svg",
            "logo": "./assets/deep-gvr-plugin.svg",
            "screenshots": [],
        },
    }


def expected_codex_plugin_marketplace(root: Path | None = None) -> dict[str, Any]:
    _ = root or repo_root()
    return {
        "name": "deep-gvr-local",
        "interface": {
            "displayName": "deep-gvr local plugins",
        },
        "plugins": [
            {
                "name": "deep-gvr",
                "source": {
                    "source": "local",
                    "path": "./plugins/deep-gvr",
                },
                "policy": {
                    "installation": "AVAILABLE",
                    "authentication": "ON_INSTALL",
                },
                "category": "Coding",
            }
        ],
    }


def codex_plugin_surface_errors(root: Path | None = None) -> list[str]:
    effective_root = root or repo_root()
    errors: list[str] = []
    manifest_path = codex_plugin_manifest_path(effective_root)
    skill_path = codex_plugin_skill_path(effective_root)
    marketplace_path = codex_plugin_marketplace_path(effective_root)
    plugin_schema = json.loads(_schema_path("codex_plugin.schema.json", effective_root).read_text(encoding="utf-8"))
    marketplace_schema = json.loads(
        _schema_path("codex_plugin_marketplace.schema.json", effective_root).read_text(encoding="utf-8")
    )

    if not manifest_path.exists():
        errors.append(f"{manifest_path.relative_to(effective_root)}: required Codex plugin manifest is missing")
    else:
        try:
            actual_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            validate(actual_manifest, plugin_schema)
        except (json.JSONDecodeError, OSError, SchemaValidationError, ValueError) as exc:
            errors.append(f"{manifest_path.relative_to(effective_root)}: invalid Codex plugin manifest: {exc}")
        else:
            expected_manifest = expected_codex_plugin_manifest(effective_root)
            if actual_manifest != expected_manifest:
                errors.append(
                    f"{manifest_path.relative_to(effective_root)}: Codex plugin manifest is out of sync with repo metadata"
                )

    source_skill_path = effective_root / "codex_skill" / "SKILL.md"
    if not skill_path.exists():
        errors.append(f"{skill_path.relative_to(effective_root)}: required Codex plugin skill is missing")
    elif not source_skill_path.exists():
        errors.append("codex_skill/SKILL.md: required Codex skill source is missing")
    else:
        if skill_path.read_text(encoding="utf-8") != _codex_skill_payload(effective_root):
            errors.append(
                f"{skill_path.relative_to(effective_root)}: plugin-packaged skill does not match codex_skill/SKILL.md"
            )

    for relative in (
        Path("plugins/deep-gvr/assets/deep-gvr-plugin-small.svg"),
        Path("plugins/deep-gvr/assets/deep-gvr-plugin.svg"),
    ):
        asset_path = effective_root / relative
        if not asset_path.exists():
            errors.append(f"{relative}: required Codex plugin asset is missing")

    if not marketplace_path.exists():
        errors.append(f"{marketplace_path.relative_to(effective_root)}: required Codex plugin marketplace is missing")
    else:
        try:
            actual_marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
            validate(actual_marketplace, marketplace_schema)
        except (json.JSONDecodeError, OSError, SchemaValidationError, ValueError) as exc:
            errors.append(f"{marketplace_path.relative_to(effective_root)}: invalid Codex plugin marketplace: {exc}")
        else:
            expected_marketplace = expected_codex_plugin_marketplace(effective_root)
            if actual_marketplace != expected_marketplace:
                errors.append(
                    f"{marketplace_path.relative_to(effective_root)}: Codex plugin marketplace is out of sync with repo metadata"
                )

    return errors


def load_publication_manifest(root: Path | None = None) -> ReleasePublicationManifest:
    manifest_path = publication_manifest_path(root)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema = json.loads(_schema_path("release_publication.schema.json", root).read_text(encoding="utf-8"))
    validate(payload, schema)
    return ReleasePublicationManifest.from_dict(payload)


def publication_manifest_errors(root: Path | None = None) -> list[str]:
    effective_root = root or repo_root()
    errors: list[str] = []
    manifest_path = publication_manifest_path(effective_root)
    if not manifest_path.exists():
        return [f"{manifest_path.relative_to(effective_root)}: required publication manifest is missing"]

    try:
        actual = load_publication_manifest(effective_root).to_dict()
    except (json.JSONDecodeError, OSError, SchemaValidationError, ValueError) as exc:
        return [f"{manifest_path.relative_to(effective_root)}: invalid publication manifest: {exc}"]

    expected = expected_publication_manifest(effective_root).to_dict()
    if actual != expected:
        errors.append(
            f"{manifest_path.relative_to(effective_root)}: publication manifest is out of sync with repo metadata"
        )
    return errors


def _changelog_sections(text: str) -> dict[str, str]:
    heading_pattern = re.compile(r"^## \[(?P<label>[^\]]+)\](?: - \d{4}-\d{2}-\d{2})?\s*$", flags=re.MULTILINE)
    matches = list(heading_pattern.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        label = match.group("label")
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[label] = text[start:end].strip()
    return sections


def release_notes_for_version(version: str, root: Path | None = None) -> str:
    payload = changelog_path(root).read_text(encoding="utf-8")
    sections = _changelog_sections(payload)
    notes = sections.get(version, "").strip()
    if not notes:
        raise ValueError(f"CHANGELOG.md is missing a non-empty section for version {version}.")
    return notes


def release_metadata_errors(root: Path | None = None, *, tag: str | None = None) -> list[str]:
    effective_root = root or repo_root()
    errors: list[str] = []
    changelog = changelog_path(effective_root)
    version = project_version(effective_root)
    expected_tag = expected_release_tag(effective_root)

    if not changelog.exists():
        return [f"{changelog.relative_to(effective_root)}: required changelog is missing"]

    payload = changelog.read_text(encoding="utf-8")
    if "# Changelog" not in payload:
        errors.append("CHANGELOG.md: missing top-level changelog heading")
    if "## [Unreleased]" not in payload:
        errors.append("CHANGELOG.md: missing required [Unreleased] section")

    try:
        release_notes_for_version(version, effective_root)
    except ValueError as exc:
        errors.append(str(exc))

    if tag is not None and tag != expected_tag:
        errors.append(
            f"tag mismatch: repo version {version} expects {expected_tag}, got {tag}"
        )

    return errors


def collect_release_preflight(
    *,
    config_path: Path | None = None,
    skills_dir: Path | None = None,
    hermes_config_path: Path | None = None,
) -> ReleasePreflightReport:
    effective_root = repo_root()
    effective_config_path = (config_path or default_config_path()).expanduser()
    effective_skills_dir = (skills_dir or default_skills_dir()).expanduser()
    effective_hermes_config_path = (hermes_config_path or default_hermes_config_path()).expanduser()
    checks: list[ReleaseCheck] = []

    checks.append(_check_skill_install(effective_skills_dir))
    config_check, runtime_config = _check_runtime_config(effective_config_path)
    checks.append(config_check)
    checks.append(_check_hermes_cli())
    checks.append(_check_provider_credentials(runtime_config))
    checks.append(_check_analysis_adapter_families(runtime_config))
    checks.append(_check_tier2_backend(runtime_config))
    checks.append(_check_tier3_transport(runtime_config, effective_hermes_config_path))
    checks.append(_check_publication_manifest(effective_root))
    checks.append(_check_codex_plugin_surface(effective_root))
    checks.append(_check_codex_automation_surface(effective_root))
    checks.append(_check_codex_review_qa_surface(effective_root))
    checks.append(_check_release_metadata(effective_root))
    checks.append(_check_auto_improve_policy(effective_root))

    structural_names = {
        "skill_install",
        "runtime_config",
        "publication_manifest",
        "codex_plugin_surface",
        "codex_automation_surface",
        "codex_review_qa_surface",
        "release_metadata",
        "auto_improve_policy",
    }
    release_surface_ready = all(
        check.status == ReleaseCheckStatus.READY for check in checks if check.name in structural_names
    )
    operator_ready = all(check.status == ReleaseCheckStatus.READY for check in checks)
    if not release_surface_ready:
        overall_status = ReleaseCheckStatus.BLOCKED
    elif operator_ready:
        overall_status = ReleaseCheckStatus.READY
    else:
        overall_status = ReleaseCheckStatus.ATTENTION

    manifest_path = publication_manifest_path(effective_root)
    version = expected_publication_manifest(effective_root).version
    return ReleasePreflightReport(
        skill_name="deep-gvr",
        version=version,
        generated_at=datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        overall_status=overall_status,
        release_surface_ready=release_surface_ready,
        operator_ready=operator_ready,
        config_path=str(effective_config_path),
        hermes_config_path=str(effective_hermes_config_path),
        publication_manifest_path=str(manifest_path),
        checks=checks,
    )


def collect_codex_preflight(
    *,
    config_path: Path | None = None,
    codex_skills_dir: Path | None = None,
    hermes_skills_dir: Path | None = None,
    hermes_config_path: Path | None = None,
) -> ReleasePreflightReport:
    effective_root = repo_root()
    effective_config_path = (config_path or default_config_path()).expanduser()
    effective_codex_skills_dir = (codex_skills_dir or default_codex_skills_dir()).expanduser()
    effective_hermes_skills_dir = (hermes_skills_dir or default_skills_dir()).expanduser()
    effective_hermes_config_path = (hermes_config_path or default_hermes_config_path()).expanduser()
    checks: list[ReleaseCheck] = []

    checks.append(_check_codex_cli())
    checks.append(_check_codex_skill_install(effective_codex_skills_dir, effective_root))
    checks.append(_check_codex_plugin_surface(effective_root))
    checks.append(_check_codex_automation_surface(effective_root))
    checks.append(_check_codex_review_qa_surface(effective_root))
    checks.append(_check_skill_install(effective_hermes_skills_dir))
    config_check, runtime_config = _check_runtime_config(effective_config_path)
    checks.append(config_check)
    checks.append(_check_hermes_cli())
    checks.append(_check_provider_credentials(runtime_config))
    checks.append(_check_analysis_adapter_families(runtime_config))
    checks.append(_check_tier2_backend(runtime_config))
    checks.append(_check_tier3_transport(runtime_config, effective_hermes_config_path))

    structural_names = {
        "codex_cli",
        "codex_skill_install",
        "codex_plugin_surface",
        "codex_automation_surface",
        "codex_review_qa_surface",
        "skill_install",
        "runtime_config",
    }
    release_surface_ready = all(
        check.status == ReleaseCheckStatus.READY for check in checks if check.name in structural_names
    )
    operator_ready = all(check.status == ReleaseCheckStatus.READY for check in checks)
    if not release_surface_ready:
        overall_status = ReleaseCheckStatus.BLOCKED
    elif operator_ready:
        overall_status = ReleaseCheckStatus.READY
    else:
        overall_status = ReleaseCheckStatus.ATTENTION

    manifest_path = publication_manifest_path(effective_root)
    version = expected_publication_manifest(effective_root).version
    return ReleasePreflightReport(
        skill_name="deep-gvr",
        version=version,
        generated_at=datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        overall_status=overall_status,
        release_surface_ready=release_surface_ready,
        operator_ready=operator_ready,
        config_path=str(effective_config_path),
        hermes_config_path=str(effective_hermes_config_path),
        publication_manifest_path=str(manifest_path),
        checks=checks,
    )


def _check_skill_install(skills_dir: Path) -> ReleaseCheck:
    install_path = skills_dir / "deep-gvr"
    skill_manifest_path = install_path / "SKILL.md"
    if skill_manifest_path.exists():
        return ReleaseCheck(
            name="skill_install",
            status=ReleaseCheckStatus.READY,
            summary="The deep-gvr skill bundle is installed in the Hermes skills directory.",
            details={"install_path": str(install_path), "skill_manifest_path": str(skill_manifest_path)},
            guidance="Re-run bash scripts/install.sh if the installed bundle is stale.",
        )
    return ReleaseCheck(
        name="skill_install",
        status=ReleaseCheckStatus.BLOCKED,
        summary="The deep-gvr skill bundle is not installed under the target Hermes skills directory.",
        details={"install_path": str(install_path), "skill_manifest_path": str(skill_manifest_path)},
        guidance="Run bash scripts/install.sh before invoking /deep-gvr from Hermes.",
    )


def _check_codex_cli() -> ReleaseCheck:
    codex_binary = shutil.which("codex")
    if codex_binary is not None:
        return ReleaseCheck(
            name="codex_cli",
            status=ReleaseCheckStatus.READY,
            summary="Codex CLI is available on PATH.",
            details={"codex_binary": codex_binary},
            guidance="Use the same Codex install for the local deep-gvr skill and codex exec smoke runs.",
        )
    return ReleaseCheck(
        name="codex_cli",
        status=ReleaseCheckStatus.BLOCKED,
        summary="Codex CLI is not installed or not available on PATH.",
        details={"codex_binary": None},
        guidance="Install Codex local and ensure the codex binary is on PATH before using the Codex surface.",
    )


def _check_codex_skill_install(codex_skills_dir: Path, root: Path) -> ReleaseCheck:
    install_path = codex_skills_dir / "deep-gvr"
    skill_manifest_path = install_path / "SKILL.md"
    source_manifest_path = root / "codex_skill" / "SKILL.md"
    if not source_manifest_path.exists():
        return ReleaseCheck(
            name="codex_skill_install",
            status=ReleaseCheckStatus.BLOCKED,
            summary="The repo-local Codex skill source is missing.",
            details={"source_manifest_path": str(source_manifest_path)},
            guidance="Restore codex_skill/SKILL.md before using the Codex-local install surface.",
        )

    if skill_manifest_path.exists():
        source_payload = source_manifest_path.read_text(encoding="utf-8")
        installed_payload = skill_manifest_path.read_text(encoding="utf-8")
        if installed_payload == source_payload:
            return ReleaseCheck(
                name="codex_skill_install",
                status=ReleaseCheckStatus.READY,
                summary="The deep-gvr Codex-local skill is installed and matches the repo copy.",
                details={
                    "install_path": str(install_path),
                    "skill_manifest_path": str(skill_manifest_path),
                    "source_manifest_path": str(source_manifest_path),
                },
                guidance="Re-run bash scripts/install_codex.sh if the installed Codex skill is stale.",
            )
        return ReleaseCheck(
            name="codex_skill_install",
            status=ReleaseCheckStatus.ATTENTION,
            summary="The deep-gvr Codex-local skill is installed, but it does not match the repo copy.",
            details={
                "install_path": str(install_path),
                "skill_manifest_path": str(skill_manifest_path),
                "source_manifest_path": str(source_manifest_path),
            },
            guidance="Re-run bash scripts/install_codex.sh --force to refresh the installed Codex skill.",
        )

    return ReleaseCheck(
        name="codex_skill_install",
        status=ReleaseCheckStatus.BLOCKED,
        summary="The deep-gvr Codex-local skill is not installed under the target Codex skills directory.",
        details={
            "install_path": str(install_path),
            "skill_manifest_path": str(skill_manifest_path),
            "source_manifest_path": str(source_manifest_path),
        },
        guidance="Run bash scripts/install_codex.sh before invoking deep-gvr through Codex local.",
    )


def _check_runtime_config(config_path: Path) -> tuple[ReleaseCheck, DeepGvrConfig | None]:
    if not config_path.exists():
        return (
            ReleaseCheck(
                name="runtime_config",
                status=ReleaseCheckStatus.BLOCKED,
                summary="The runtime config file does not exist.",
                details={"config_path": str(config_path)},
                guidance="Run uv run deep-gvr init-config or bash scripts/install.sh to create the default config.",
            ),
            None,
        )

    try:
        runtime_config = load_runtime_config(config_path, create_if_missing=False)
    except Exception as exc:  # pragma: no cover - defensive wrapper around schema validation
        return (
            ReleaseCheck(
                name="runtime_config",
                status=ReleaseCheckStatus.BLOCKED,
                summary="The runtime config file is present but does not validate against the repo schema.",
                details={"config_path": str(config_path), "error": str(exc)},
                guidance="Restore the config from templates/config.template.yaml or fix the invalid fields.",
            ),
            None,
        )

    return (
        ReleaseCheck(
            name="runtime_config",
            status=ReleaseCheckStatus.READY,
            summary="The runtime config exists and validates against the repo schema.",
            details={
                "config_path": str(config_path),
                "tier2_backend": runtime_config.verification.tier2.default_backend.value,
                "default_adapter_family": runtime_config.verification.tier2.default_adapter_family,
                "tier3_enabled": runtime_config.verification.tier3.enabled,
            },
            guidance="Keep the runtime config aligned with the checked-in YAML template.",
        ),
        runtime_config,
    )


def _check_hermes_cli() -> ReleaseCheck:
    hermes_binary = shutil.which("hermes")
    if hermes_binary is not None:
        return ReleaseCheck(
            name="hermes_cli",
            status=ReleaseCheckStatus.READY,
            summary="Hermes CLI is available on PATH.",
            details={"hermes_binary": hermes_binary},
            guidance="Use the same Hermes install for /deep-gvr and release preflight runs.",
        )
    return ReleaseCheck(
        name="hermes_cli",
        status=ReleaseCheckStatus.BLOCKED,
        summary="Hermes CLI is not installed or not available on PATH.",
        details={"hermes_binary": None},
        guidance="Install Hermes Agent and ensure the hermes binary is on PATH before operator use.",
    )


def _check_provider_credentials(runtime_config: DeepGvrConfig | None) -> ReleaseCheck:
    if runtime_config is None:
        return ReleaseCheck(
            name="provider_credentials",
            status=ReleaseCheckStatus.BLOCKED,
            summary="Provider credentials cannot be validated until the runtime config is valid.",
            guidance="Fix the runtime config first, then rerun release preflight.",
        )

    explicit_roles: dict[str, list[str]] = {}
    model_config = runtime_config.models
    for role_name in ("orchestrator", "generator", "verifier", "reviser"):
        selection = getattr(model_config, role_name)
        provider = selection.provider.strip().lower()
        if provider in {"", "default", "auto"}:
            continue
        explicit_roles.setdefault(provider, []).append(role_name)

    if not explicit_roles:
        return ReleaseCheck(
            name="provider_credentials",
            status=ReleaseCheckStatus.READY,
            summary="All configured routes use the Hermes default provider selection, so credential resolution stays inside Hermes.",
            details={"providers": {}},
            guidance="If you pin explicit providers later, rerun release preflight to validate the expected API keys.",
        )

    provider_details: dict[str, Any] = {}
    blocked_providers: list[str] = []
    attention_providers: list[str] = []

    for provider, roles in explicit_roles.items():
        known_env_vars = _PROVIDER_ENV_MAP.get(provider, [])
        if known_env_vars:
            present_env_vars = [name for name in known_env_vars if os.getenv(name)]
            missing_env_vars = [name for name in known_env_vars if name not in present_env_vars]
            provider_details[provider] = {
                "roles": roles,
                "required_env_vars": known_env_vars,
                "present_env_vars": present_env_vars,
                "missing_env_vars": missing_env_vars,
            }
            if not present_env_vars:
                blocked_providers.append(provider)
        else:
            provider_details[provider] = {
                "roles": roles,
                "required_env_vars": [],
                "present_env_vars": [],
                "missing_env_vars": [],
            }
            attention_providers.append(provider)

    if blocked_providers:
        return ReleaseCheck(
            name="provider_credentials",
            status=ReleaseCheckStatus.BLOCKED,
            summary="At least one explicitly configured provider is missing its expected environment credential.",
            details={"providers": provider_details, "blocked_providers": blocked_providers},
            guidance="Export the expected provider API key before using the configured route in Hermes.",
        )
    if attention_providers:
        return ReleaseCheck(
            name="provider_credentials",
            status=ReleaseCheckStatus.ATTENTION,
            summary="One or more explicit providers do not have a repo-local credential mapping and require manual operator verification.",
            details={"providers": provider_details, "attention_providers": attention_providers},
            guidance="Verify the provider credential manually in Hermes, then rerun preflight after updating the repo mapping if needed.",
        )
    return ReleaseCheck(
        name="provider_credentials",
        status=ReleaseCheckStatus.READY,
        summary="All explicitly configured providers have the expected credential environment variables.",
        details={"providers": provider_details},
        guidance="Keep provider env vars available in the shell that launches Hermes.",
    )


def _check_tier2_backend(runtime_config: DeepGvrConfig | None) -> ReleaseCheck:
    if runtime_config is None:
        return ReleaseCheck(
            name="tier2_backend",
            status=ReleaseCheckStatus.BLOCKED,
            summary="Tier 2 backend readiness cannot be evaluated until the runtime config is valid.",
            guidance="Fix the runtime config first, then rerun release preflight.",
        )

    tier2 = runtime_config.verification.tier2
    if not tier2.enabled:
        return ReleaseCheck(
            name="tier2_backend",
            status=ReleaseCheckStatus.READY,
            summary="Tier 2 is disabled in the runtime config, so no backend readiness is required for operator use.",
            details={"selected_backend": tier2.default_backend.value},
            guidance="Enable Tier 2 only after the chosen backend is configured and ready.",
        )

    probe = probe_backend_dispatch(runtime_config)
    selected_backend = tier2.default_backend.value
    selected_key = f"{selected_backend}_ready"
    selected_ready = bool(probe.details.get(selected_key))
    if selected_ready:
        return ReleaseCheck(
            name="tier2_backend",
            status=ReleaseCheckStatus.READY,
            summary=f"The selected Tier 2 backend ({selected_backend}) is ready in this environment.",
            details={"selected_backend": selected_backend, **probe.details},
            guidance="Use scripts/run_capability_probes.py --config ~/.hermes/deep-gvr/config.yaml when backend settings change.",
        )
    return ReleaseCheck(
        name="tier2_backend",
        status=ReleaseCheckStatus.BLOCKED,
        summary=f"The selected Tier 2 backend ({selected_backend}) is not ready in this environment.",
        details={"selected_backend": selected_backend, **probe.details},
        guidance="Install or configure the selected backend prerequisites, or switch the default backend to one that is ready.",
    )


def _check_analysis_adapter_families(runtime_config: DeepGvrConfig | None) -> ReleaseCheck:
    if runtime_config is None:
        return ReleaseCheck(
            name="analysis_adapter_families",
            status=ReleaseCheckStatus.BLOCKED,
            summary="Analysis-adapter readiness cannot be evaluated until the runtime config is valid.",
            guidance="Fix the runtime config first, then rerun release preflight.",
        )

    tier2 = runtime_config.verification.tier2
    if not tier2.enabled:
        return ReleaseCheck(
            name="analysis_adapter_families",
            status=ReleaseCheckStatus.READY,
            summary="Tier 2 analysis is disabled in the runtime config, so adapter-family readiness is not required for operator use.",
            details={"default_adapter_family": tier2.default_adapter_family},
            guidance="Enable Tier 2 only after the required analysis adapter families are installed.",
        )

    probe = probe_analysis_adapter_families()
    default_family = tier2.default_adapter_family
    family_details = dict(probe.details.get("families", {}))
    default_family_ready = bool(family_details.get(default_family, {}).get("ready"))
    status = ReleaseCheckStatus.READY if probe.status is ProbeStatus.READY else ReleaseCheckStatus.ATTENTION
    summary = (
        "All configured OSS analysis adapter families have their local Python dependencies available."
        if status is ReleaseCheckStatus.READY
        else "One or more OSS analysis adapter families are missing local Python dependencies."
    )
    guidance = (
        "Install the missing OSS analysis libraries before using those adapter families in live operator runs."
        if status is ReleaseCheckStatus.ATTENTION
        else "Rerun release preflight after changing the local Python environment or adapter-family defaults."
    )
    if not default_family_ready:
        status = ReleaseCheckStatus.BLOCKED
        summary = (
            f"The configured default analysis adapter family ({default_family}) is not ready in this environment."
        )
        guidance = (
            "Install the missing dependencies for the configured default adapter family or change the default to a ready family."
        )
    return ReleaseCheck(
        name="analysis_adapter_families",
        status=status,
        summary=summary,
        details={
            "default_adapter_family": default_family,
            "default_adapter_family_ready": default_family_ready,
            **probe.details,
        },
        guidance=guidance,
    )


def _check_tier3_transport(runtime_config: DeepGvrConfig | None, hermes_config_path: Path) -> ReleaseCheck:
    if runtime_config is None:
        return ReleaseCheck(
            name="tier3_transport",
            status=ReleaseCheckStatus.BLOCKED,
            summary="Tier 3 transport readiness cannot be evaluated until the runtime config is valid.",
            guidance="Fix the runtime config first, then rerun release preflight.",
        )

    tier3 = runtime_config.verification.tier3
    if not tier3.enabled:
        return ReleaseCheck(
            name="tier3_transport",
            status=ReleaseCheckStatus.READY,
            summary="Tier 3 is disabled in the runtime config, so the configured formal backend transport is not required for operator use.",
            details={"backend": tier3.backend, "hermes_config_path": str(hermes_config_path)},
            guidance="Verify the configured formal backend before enabling Tier 3 for operator use.",
        )

    if tier3.backend == "mathcode":
        probe = probe_mathcode_transport(runtime_config)
        if probe.status.value == "ready":
            return ReleaseCheck(
                name="tier3_transport",
                status=ReleaseCheckStatus.READY,
                summary="The configured Tier 3 transport is ready for local MathCode proof dispatch.",
                details=probe.details,
                guidance="Tier 3 proof attempts will use the configured MathCode root and run script on the shipped harness path.",
            )
        return ReleaseCheck(
            name="tier3_transport",
            status=ReleaseCheckStatus.BLOCKED,
            summary="Tier 3 is enabled, but the configured MathCode transport is not ready in this environment.",
            details=probe.details,
            guidance="Install or fix the local MathCode checkout and verify AUTOLEAN, lean-workspace, and the run script path before enabling Tier 3 live use.",
        )
    if tier3.backend == "opengauss":
        probe = probe_opengauss_transport()
        return ReleaseCheck(
            name="tier3_transport",
            status=ReleaseCheckStatus.BLOCKED,
            summary="The configured Tier 3 backend (opengauss) is still blocked on upstream installability and is not implemented on the shipped harness path.",
            details=probe.details,
            guidance="Run uv run python scripts/diagnose_opengauss.py --json to separate local checkout issues from upstream installer failures, then keep Tier 3 on Aristotle or MathCode until plan 31 resumes.",
        )
    if tier3.backend != "aristotle":
        return ReleaseCheck(
            name="tier3_transport",
            status=ReleaseCheckStatus.BLOCKED,
            summary=f"The configured Tier 3 backend ({tier3.backend}) is not implemented in the shipped release surface.",
            details={"backend": tier3.backend},
            guidance="Select a supported Tier 3 backend or complete the owning backend slice before operator use.",
        )

    probe = probe_aristotle_transport()
    if probe.status.value == "ready":
        return ReleaseCheck(
            name="tier3_transport",
            status=ReleaseCheckStatus.READY,
            summary="The configured Tier 3 transport is ready for Aristotle proof dispatch.",
            details=probe.details,
            guidance="Proof polling and resume will use the configured Aristotle transport on the shipped harness path.",
        )
    return ReleaseCheck(
        name="tier3_transport",
        status=ReleaseCheckStatus.BLOCKED,
        summary="Tier 3 is enabled, but Aristotle transport is not ready in this environment.",
        details=probe.details,
        guidance="Run bash scripts/setup_mcp.sh --install --check and verify ARISTOTLE_API_KEY before enabling Tier 3 live use.",
    )


def _check_publication_manifest(root: Path) -> ReleaseCheck:
    errors = publication_manifest_errors(root)
    manifest_path = publication_manifest_path(root)
    if errors:
        return ReleaseCheck(
            name="publication_manifest",
            status=ReleaseCheckStatus.BLOCKED,
            summary="The checked-in publication manifest is missing or out of sync with repo metadata.",
            details={"manifest_path": str(manifest_path), "errors": errors},
            guidance="Regenerate or update the publication manifest so it matches SKILL.md, pyproject.toml, and the release scripts.",
        )
    return ReleaseCheck(
        name="publication_manifest",
        status=ReleaseCheckStatus.READY,
        summary="The checked-in publication manifest matches the current repo metadata and release surface.",
        details={"manifest_path": str(manifest_path)},
        guidance="Use the manifest as the publication bundle source for GitHub and agentskills.io release work.",
    )


def _check_codex_plugin_surface(root: Path) -> ReleaseCheck:
    errors = codex_plugin_surface_errors(root)
    manifest_path = codex_plugin_manifest_path(root)
    marketplace_path = codex_plugin_marketplace_path(root)
    if errors:
        return ReleaseCheck(
            name="codex_plugin_surface",
            status=ReleaseCheckStatus.BLOCKED,
            summary="The checked-in Codex plugin bundle is missing or out of sync with the repo surface.",
            details={
                "manifest_path": str(manifest_path),
                "marketplace_path": str(marketplace_path),
                "errors": errors,
            },
            guidance=(
                "Restore or update the checked-in Codex plugin bundle and marketplace so the repo can act "
                "as a valid local plugin source."
            ),
        )
    return ReleaseCheck(
        name="codex_plugin_surface",
        status=ReleaseCheckStatus.READY,
        summary="The checked-in Codex plugin bundle and local marketplace metadata match the repo surface.",
        details={
            "manifest_path": str(manifest_path),
            "marketplace_path": str(marketplace_path),
        },
        guidance="Use bash scripts/install_codex.sh --plugin-root <dir> to export a standalone local plugin marketplace root when needed.",
    )


def _check_codex_automation_surface(root: Path) -> ReleaseCheck:
    errors = codex_automation_surface_errors(root)
    catalog_path = automation_catalog_path(root)
    if errors:
        return ReleaseCheck(
            name="codex_automation_surface",
            status=ReleaseCheckStatus.BLOCKED,
            summary="The checked-in Codex automation pack is missing or out of sync with the repo surface.",
            details={"catalog_path": str(catalog_path), "errors": errors},
            guidance=(
                "Restore or update the checked-in Codex automation catalog and templates so recurring Codex workflows "
                "stay reviewable and exportable from the repo."
            ),
        )
    return ReleaseCheck(
        name="codex_automation_surface",
        status=ReleaseCheckStatus.READY,
        summary="The checked-in Codex automation catalog and templates match the repo surface.",
        details={"catalog_path": str(catalog_path)},
        guidance=(
            "Use python scripts/export_codex_automations.py --output-root <dir> or bash scripts/install_codex.sh "
            "--automation-root <dir> to export a reviewable automation bundle for Codex."
        ),
    )


def _check_codex_review_qa_surface(root: Path) -> ReleaseCheck:
    errors = codex_review_qa_surface_errors(root)
    catalog_path = review_qa_catalog_path(root)
    if errors:
        return ReleaseCheck(
            name="codex_review_qa_surface",
            status=ReleaseCheckStatus.BLOCKED,
            summary="The checked-in Codex review/QA prompt pack is missing or out of sync with the repo surface.",
            details={"catalog_path": str(catalog_path), "errors": errors},
            guidance=(
                "Restore or update the checked-in Codex review/QA catalog and prompt templates so Codex review and "
                "visual-QA workflows stay reviewable and exportable from the repo."
            ),
        )
    return ReleaseCheck(
        name="codex_review_qa_surface",
        status=ReleaseCheckStatus.READY,
        summary="The checked-in Codex review/QA catalog and prompt templates match the repo surface.",
        details={"catalog_path": str(catalog_path)},
        guidance=(
            "Use python scripts/export_codex_review_qa.py --output-root <dir> or bash scripts/install_codex.sh "
            "--review-qa-root <dir> to export a reviewable Codex review/QA bundle."
        ),
    )


def _check_release_metadata(root: Path) -> ReleaseCheck:
    errors = release_metadata_errors(root)
    changelog = changelog_path(root)
    version = project_version(root)
    if errors:
        return ReleaseCheck(
            name="release_metadata",
            status=ReleaseCheckStatus.BLOCKED,
            summary="The checked-in release metadata is missing or out of sync with the current project version.",
            details={
                "version": version,
                "expected_tag": expected_release_tag(root),
                "changelog_path": str(changelog),
                "errors": errors,
            },
            guidance="Add or update CHANGELOG.md so the current project version has release notes before cutting a public release.",
        )
    return ReleaseCheck(
        name="release_metadata",
        status=ReleaseCheckStatus.READY,
        summary="The checked-in changelog and release tag policy match the current project version.",
        details={
            "version": version,
            "expected_tag": expected_release_tag(root),
            "changelog_path": str(changelog),
        },
        guidance="Render release notes directly from CHANGELOG.md when cutting a tagged release.",
    )


def _check_auto_improve_policy(root: Path) -> ReleaseCheck:
    try:
        manifest = load_publication_manifest(root)
    except Exception as exc:  # pragma: no cover - defensive wrapper
        return ReleaseCheck(
            name="auto_improve_policy",
            status=ReleaseCheckStatus.BLOCKED,
            summary="The auto_improve release policy cannot be evaluated because the publication manifest is invalid.",
            details={"error": str(exc)},
            guidance="Fix the publication manifest before release.",
        )

    return evaluate_auto_improve_policy_manifest(manifest)


def evaluate_auto_improve_policy_manifest(manifest: ReleasePublicationManifest) -> ReleaseCheck:
    if not manifest.auto_improve:
        return ReleaseCheck(
            name="auto_improve_policy",
            status=ReleaseCheckStatus.READY,
            summary="The published release policy ships with auto_improve disabled by default.",
            details={"auto_improve": manifest.auto_improve},
            guidance=(
                "Only opt in after running uv run python scripts/evaluate_auto_improve.py "
                "--output /tmp/deep-gvr-auto-improve/report.json and reviewing the report."
            ),
        )
    return ReleaseCheck(
        name="auto_improve_policy",
        status=ReleaseCheckStatus.BLOCKED,
        summary="The publication manifest currently enables auto_improve, which violates the documented release default.",
        details={"auto_improve": manifest.auto_improve},
        guidance=(
            "Set auto_improve back to false before cutting a public release, or complete and review "
            "the auto-improve evaluation workflow first."
        ),
    )
