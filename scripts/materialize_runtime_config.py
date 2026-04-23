#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def _yaml_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def materialize_runtime_config(
    *,
    template_path: Path,
    output_path: Path,
    orchestrator_backend: str,
    force: bool = False,
) -> Path:
    template_payload = template_path.expanduser().read_text(encoding="utf-8").splitlines()
    resolved_output_path = output_path.expanduser()
    if resolved_output_path.exists() and not force:
        return resolved_output_path

    sessions_directory = str((resolved_output_path.parent / "sessions").expanduser())
    current_section: str | None = None
    replaced_backend = False
    replaced_directory = False
    rendered_lines: list[str] = []

    for line in template_payload:
        stripped = line.strip()
        if line and not line.startswith(" "):
            current_section = stripped[:-1] if stripped.endswith(":") else None
            rendered_lines.append(line)
            continue

        if current_section == "runtime" and stripped.startswith("orchestrator_backend:"):
            rendered_lines.append(f"  orchestrator_backend: {orchestrator_backend}")
            replaced_backend = True
            continue

        if current_section == "evidence" and stripped.startswith("directory:"):
            rendered_lines.append(f"  directory: {_yaml_quote(sessions_directory)}")
            replaced_directory = True
            continue

        rendered_lines.append(line)

    if not replaced_backend:
        raise ValueError("config template is missing runtime.orchestrator_backend")
    if not replaced_directory:
        raise ValueError("config template is missing evidence.directory")

    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.write_text("\n".join(rendered_lines) + "\n", encoding="utf-8")
    return resolved_output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize a deep-gvr runtime config from the checked-in template")
    parser.add_argument("--template", type=Path, required=True, help="Source config template path")
    parser.add_argument("--output", type=Path, required=True, help="Target runtime config path")
    parser.add_argument(
        "--orchestrator-backend",
        choices=["hermes", "codex_local"],
        default="hermes",
        help="Runtime orchestrator backend to stamp into the materialized config",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite the target config if it already exists")
    args = parser.parse_args()

    path = materialize_runtime_config(
        template_path=args.template,
        output_path=args.output,
        orchestrator_backend=args.orchestrator_backend,
        force=args.force,
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
