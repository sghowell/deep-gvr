from __future__ import annotations

import os
from pathlib import Path


def runtime_home_literal() -> str:
    configured = os.getenv("DEEP_GVR_HOME")
    if configured:
        return configured

    hermes_home = os.getenv("HERMES_HOME")
    if hermes_home:
        return str(Path(hermes_home) / "deep-gvr")

    return "~/.hermes/deep-gvr"


def deep_gvr_home() -> Path:
    return Path(runtime_home_literal()).expanduser()


def default_config_path() -> Path:
    return deep_gvr_home() / "config.yaml"


def default_sessions_directory() -> Path:
    return deep_gvr_home() / "sessions"


def default_sessions_directory_literal() -> str:
    return str(Path(runtime_home_literal()) / "sessions")


def runtime_home_description() -> str:
    return "${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}"
