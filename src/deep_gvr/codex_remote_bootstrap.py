from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml

from .contracts import (
    CodexRemoteBootstrapAction,
    CodexRemoteBootstrapReport,
    DeepGvrConfig,
    OrchestratorBackend,
    ReleaseCheckStatus,
)
from .release_surface import (
    collect_codex_preflight,
    default_codex_skills_dir,
    default_hermes_config_path,
    default_skills_dir,
    expected_publication_manifest,
    publication_manifest_path,
    repo_root,
)
from .runtime_config import load_runtime_config, resolve_config_path, write_default_config


@dataclass(slots=True)
class CodexRemoteBootstrapOptions:
    config_path: Path | None = None
    config_source: Path | None = None
    force_config_sync: bool = False
    codex_skills_dir: Path | None = None
    hermes_skills_dir: Path | None = None
    hermes_config_path: Path | None = None
    plugin_root: Path | None = None
    copy_install: bool = False
    force_install: bool = False
    skip_hermes_install: bool | None = None


def _read_yaml(path: Path) -> dict[str, object]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _config_sync_action(
    *,
    config_path: Path,
    config_source: Path | None,
    force_config_sync: bool,
) -> tuple[CodexRemoteBootstrapAction, Path]:
    target_path = config_path.expanduser()
    source_path = config_source.expanduser() if config_source is not None else None
    changed = False
    created_from_template = False
    source_applied = False
    source_conflict = False
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if source_path is not None:
        if not source_path.exists():
            action = CodexRemoteBootstrapAction(
                name="config_sync",
                status=ReleaseCheckStatus.BLOCKED,
                changed=False,
                summary="The requested runtime config source is missing, so remote config sync could not start.",
                details={"config_path": str(target_path), "config_source": str(source_path)},
                guidance="Provide an existing --config-source path or rerun without it to bootstrap from the repo template.",
            )
            return action, target_path

        source_payload = source_path.read_text(encoding="utf-8")
        if not target_path.exists():
            target_path.write_text(source_payload, encoding="utf-8")
            changed = True
            source_applied = True
        elif force_config_sync:
            current_payload = target_path.read_text(encoding="utf-8")
            if current_payload != source_payload:
                target_path.write_text(source_payload, encoding="utf-8")
                changed = True
            source_applied = True
        else:
            current_payload = target_path.read_text(encoding="utf-8")
            if current_payload == source_payload:
                source_applied = True
            else:
                source_conflict = True
    elif not target_path.exists():
        write_default_config(target_path)
        changed = True
        created_from_template = True

    try:
        payload = _read_yaml(target_path)
    except (OSError, yaml.YAMLError) as exc:
        action = CodexRemoteBootstrapAction(
            name="config_sync",
            status=ReleaseCheckStatus.BLOCKED,
            changed=changed,
            summary="The runtime config exists but is not readable as YAML after bootstrap sync.",
            details={
                "config_path": str(target_path),
                "config_source": str(source_path) if source_path is not None else None,
                "source_conflict": source_conflict,
                "error": str(exc),
            },
            guidance="Fix the runtime config YAML or resync it from a valid source before using the remote Codex path.",
        )
        return action, target_path

    runtime_block = payload.setdefault("runtime", {})
    previous_backend = str(runtime_block.get("orchestrator_backend", "hermes"))
    backend_changed = previous_backend != OrchestratorBackend.CODEX_LOCAL.value
    if backend_changed:
        runtime_block["orchestrator_backend"] = OrchestratorBackend.CODEX_LOCAL.value
        _write_yaml(target_path, payload)
        changed = True

    status = ReleaseCheckStatus.READY
    summary_parts: list[str] = []
    guidance_parts: list[str] = []
    if source_path is not None:
        if source_conflict:
            status = ReleaseCheckStatus.ATTENTION
            summary_parts.append("The existing runtime config differed from --config-source and was preserved.")
            guidance_parts.append("Use --force-config-sync to replace the remote runtime config from the supplied source.")
        elif source_applied:
            summary_parts.append("The runtime config was synced from the supplied source.")
    elif created_from_template:
        summary_parts.append("The runtime config was created from the repo template.")
    else:
        summary_parts.append("The existing runtime config was reused.")

    if backend_changed:
        summary_parts.append("The orchestrator backend was normalized to codex_local for remote Codex execution.")
        guidance_parts.append("Keep runtime.orchestrator_backend=codex_local for the SSH/devbox execution path.")
    else:
        summary_parts.append("The orchestrator backend was already codex_local.")

    if not guidance_parts:
        guidance_parts.append("Provide --config-source if you want the remote machine to mirror another validated runtime config.")

    action = CodexRemoteBootstrapAction(
        name="config_sync",
        status=status,
        changed=changed,
        summary=" ".join(summary_parts),
        details={
            "config_path": str(target_path),
            "config_source": str(source_path) if source_path is not None else None,
            "source_applied": source_applied,
            "source_conflict": source_conflict,
            "previous_orchestrator_backend": previous_backend,
            "orchestrator_backend": OrchestratorBackend.CODEX_LOCAL.value,
        },
        guidance=" ".join(guidance_parts),
    )
    return action, target_path


def _load_runtime_config_action(config_path: Path) -> tuple[CodexRemoteBootstrapAction | None, DeepGvrConfig | None]:
    try:
        runtime_config = load_runtime_config(config_path, create_if_missing=False)
    except Exception as exc:  # pragma: no cover - covered via preflight/script tests
        return (
            CodexRemoteBootstrapAction(
                name="runtime_config_validation",
                status=ReleaseCheckStatus.BLOCKED,
                changed=False,
                summary="The runtime config is present but does not validate against the repo schema.",
                details={"config_path": str(config_path), "error": str(exc)},
                guidance="Fix the runtime config schema violations, then rerun the remote bootstrap command.",
            ),
            None,
        )
    return None, runtime_config


def _hermes_install_policy(runtime_config: DeepGvrConfig, explicit_skip: bool | None) -> tuple[bool, str]:
    if explicit_skip is True:
        return True, "Explicit --skip-hermes-install request"
    if explicit_skip is False:
        return False, "Explicit Hermes install request"
    tier3 = runtime_config.verification.tier3
    if tier3.enabled and tier3.backend == "aristotle":
        return False, "Tier 3 Aristotle transport still needs the Hermes surface on this machine"
    return True, "Selected runtime path does not require the Hermes surface"


def _maybe_exported_plugin(plugin_root: Path | None) -> tuple[str | None, bool]:
    if plugin_root is None:
        return None, False
    manifest_path = plugin_root.expanduser() / "plugins" / "deep-gvr" / ".codex-plugin" / "plugin.json"
    return str(manifest_path), manifest_path.exists()


def _install_codex_surface_action(
    *,
    options: CodexRemoteBootstrapOptions,
    runtime_config: DeepGvrConfig,
) -> CodexRemoteBootstrapAction:
    effective_codex_skills_dir = (options.codex_skills_dir or default_codex_skills_dir()).expanduser()
    effective_hermes_skills_dir = (options.hermes_skills_dir or default_skills_dir()).expanduser()
    effective_plugin_root = options.plugin_root.expanduser() if options.plugin_root is not None else None

    skill_manifest_before = effective_codex_skills_dir / "deep-gvr" / "SKILL.md"
    skill_before = skill_manifest_before.exists()
    plugin_manifest_path, plugin_before = _maybe_exported_plugin(effective_plugin_root)
    hermes_skip, hermes_reason = _hermes_install_policy(runtime_config, options.skip_hermes_install)
    hermes_before = (effective_hermes_skills_dir / "deep-gvr" / "SKILL.md").exists()

    command = ["bash", str(repo_root() / "scripts" / "install_codex.sh"), "--target", str(effective_codex_skills_dir)]
    if effective_plugin_root is not None:
        command.extend(["--plugin-root", str(effective_plugin_root)])
    if options.copy_install:
        command.append("--copy")
    if options.force_install:
        command.append("--force")
    if hermes_skip:
        command.append("--skip-hermes-install")

    env = dict(os.environ)
    if options.codex_skills_dir is not None and effective_codex_skills_dir.name == "skills":
        env["CODEX_HOME"] = str(effective_codex_skills_dir.parent)
    if not hermes_skip and options.hermes_skills_dir is not None and effective_hermes_skills_dir.name == "skills":
        env["HERMES_HOME"] = str(effective_hermes_skills_dir.parent)
    if not hermes_skip and options.hermes_config_path is not None:
        hermes_config_parent = options.hermes_config_path.expanduser().parent
        env.setdefault("HERMES_HOME", str(hermes_config_parent))

    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        cwd=repo_root(),
        env=env,
    )

    skill_after = skill_manifest_before.exists()
    _, plugin_after = _maybe_exported_plugin(effective_plugin_root)
    hermes_after = (effective_hermes_skills_dir / "deep-gvr" / "SKILL.md").exists()
    changed = (not skill_before and skill_after) or (not plugin_before and plugin_after) or (not hermes_before and hermes_after)

    if completed.returncode != 0:
        return CodexRemoteBootstrapAction(
            name="codex_surface_install",
            status=ReleaseCheckStatus.BLOCKED,
            changed=changed,
            summary="The Codex-local surface install failed during remote bootstrap.",
            details={
                "command": command,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "codex_skills_dir": str(effective_codex_skills_dir),
                "plugin_root": str(effective_plugin_root) if effective_plugin_root is not None else None,
                "hermes_skills_dir": str(effective_hermes_skills_dir),
                "skip_hermes_install": hermes_skip,
                "hermes_install_reason": hermes_reason,
            },
            guidance="Fix the install error and rerun the bootstrap command from the repo root on the remote machine.",
        )

    if hermes_skip:
        hermes_summary = "Hermes install was skipped because the selected remote runtime does not require it."
    else:
        hermes_summary = "Hermes install was refreshed because the selected remote runtime still needs it."

    plugin_summary = (
        "A standalone local Codex plugin bundle was exported."
        if effective_plugin_root is not None
        else "No standalone plugin export was requested."
    )
    status = ReleaseCheckStatus.READY
    summary = f"The Codex-local surface was installed on the remote machine. {plugin_summary} {hermes_summary}"
    guidance = "Rerun this command with --force when you want to refresh the installed skill or plugin export in place."
    return CodexRemoteBootstrapAction(
        name="codex_surface_install",
        status=status,
        changed=changed,
        summary=summary,
        details={
            "command": command,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "codex_skills_dir": str(effective_codex_skills_dir),
            "codex_skill_manifest": str(skill_manifest_before),
            "plugin_root": str(effective_plugin_root) if effective_plugin_root is not None else None,
            "plugin_manifest_path": plugin_manifest_path,
            "hermes_skills_dir": str(effective_hermes_skills_dir),
            "skip_hermes_install": hermes_skip,
            "hermes_install_reason": hermes_reason,
        },
        guidance=guidance,
    )


def _ensure_evidence_directory_action(runtime_config: DeepGvrConfig) -> CodexRemoteBootstrapAction:
    evidence_dir = Path(runtime_config.evidence.directory).expanduser()
    existed = evidence_dir.exists()
    try:
        evidence_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return CodexRemoteBootstrapAction(
            name="evidence_directory",
            status=ReleaseCheckStatus.BLOCKED,
            changed=False,
            summary="The configured evidence directory could not be created on the remote machine.",
            details={"evidence_directory": str(evidence_dir), "error": str(exc)},
            guidance="Fix the evidence.directory path or its permissions before using the remote Codex path.",
        )
    return CodexRemoteBootstrapAction(
        name="evidence_directory",
        status=ReleaseCheckStatus.READY,
        changed=not existed,
        summary=(
            "The configured evidence directory was created for remote runs."
            if not existed
            else "The configured evidence directory already existed for remote runs."
        ),
        details={"evidence_directory": str(evidence_dir)},
        guidance="Keep the evidence directory writable from the remote machine so checkpoints and artifacts persist correctly.",
    )


def bootstrap_codex_remote(options: CodexRemoteBootstrapOptions) -> CodexRemoteBootstrapReport:
    effective_config_path = resolve_config_path(options.config_path)
    effective_hermes_config_path = (options.hermes_config_path or default_hermes_config_path()).expanduser()
    actions: list[CodexRemoteBootstrapAction] = []

    config_action, synced_config_path = _config_sync_action(
        config_path=effective_config_path,
        config_source=options.config_source,
        force_config_sync=options.force_config_sync,
    )
    actions.append(config_action)

    validation_action, runtime_config = _load_runtime_config_action(synced_config_path)
    if validation_action is not None:
        actions.append(validation_action)

    if runtime_config is not None:
        install_action = _install_codex_surface_action(options=options, runtime_config=runtime_config)
        actions.append(install_action)
        actions.append(_ensure_evidence_directory_action(runtime_config))

    preflight = collect_codex_preflight(
        config_path=synced_config_path,
        codex_skills_dir=options.codex_skills_dir,
        hermes_skills_dir=options.hermes_skills_dir,
        hermes_config_path=effective_hermes_config_path,
        ssh_devbox=True,
    )

    manifest = expected_publication_manifest()
    return CodexRemoteBootstrapReport(
        skill_name=manifest.name,
        version=manifest.version,
        generated_at=datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        overall_status=preflight.overall_status,
        release_surface_ready=preflight.release_surface_ready,
        operator_ready=preflight.operator_ready,
        config_path=str(synced_config_path),
        hermes_config_path=str(effective_hermes_config_path),
        publication_manifest_path=str(publication_manifest_path(repo_root())),
        actions=actions,
        preflight=preflight,
    )
