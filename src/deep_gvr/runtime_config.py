from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .contracts import DeepGvrConfig
from .json_schema import validate
from .runtime_paths import default_config_path as _default_config_path

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_config_path() -> Path:
    return _default_config_path()


def default_config_payload() -> dict[str, Any]:
    return DeepGvrConfig().to_dict()


def resolve_config_path(path: str | Path | None = None) -> Path:
    if path is None:
        return default_config_path()
    return Path(path).expanduser()


def write_default_config(path: str | Path | None = None, *, force: bool = False) -> Path:
    config_path = resolve_config_path(path)
    if config_path.exists() and not force:
        return config_path

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.safe_dump(default_config_payload(), sort_keys=False),
        encoding="utf-8",
    )
    return config_path


def load_runtime_config(path: str | Path | None = None, *, create_if_missing: bool = True) -> DeepGvrConfig:
    config_path = resolve_config_path(path)
    if not config_path.exists() and create_if_missing:
        write_default_config(config_path)

    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    schema = json.loads((_repo_root() / "schemas" / "config.schema.json").read_text(encoding="utf-8"))
    validate(payload, schema)
    return DeepGvrConfig.from_dict(payload)
