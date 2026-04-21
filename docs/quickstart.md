# Quickstart

This guide gets a new operator from a local checkout to a first successful `deep-gvr` run.

## Prerequisites

- Python 3.12
- `uv`
- Hermes Agent installed if you want the Hermes `/deep-gvr` path or the `hermes` backend
- Codex local installed if you want the Codex-local surface
- a Codex client/workspace with plugin support if you want to use the packaged Codex plugin surface
- Access to whichever model provider route your selected runtime config uses. On the shipped path today, that still means the Hermes delegated backend.

Optional extras:

- `uv sync --extra analysis` for the broader scientific analysis families
- `uv sync --extra quantum_oss` for the broader OSS quantum families

## Install the Project Environment

```bash
uv sync
uv sync --extra analysis --extra quantum_oss
```

## Install a Supported Surface

Hermes and direct CLI path:

```bash
bash scripts/install.sh
```

Codex-local path:

```bash
bash scripts/install_codex.sh
```

The Codex install path installs the Codex-local skill and also refreshes the Hermes skill/runtime surface by default so both backend paths remain available.

If you only want the Codex-native backend path on that machine:

```bash
bash scripts/install_codex.sh --skip-hermes-install
```

Optional plugin export path:

```bash
bash scripts/install_codex.sh --plugin-root /tmp/deep-gvr-codex-plugin
```

Optional `ssh/devbox` remote-operator export path:

```bash
bash scripts/install_codex.sh --ssh-devbox-root /tmp/deep-gvr-codex-ssh-devbox
```

## Run Preflight

Hermes and direct CLI path:

```bash
uv run python scripts/release_preflight.py --json
uv run python scripts/release_preflight.py --operator --config ${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/config.yaml
```

Codex-local path:

```bash
uv run python scripts/codex_preflight.py --json
uv run python scripts/codex_preflight.py --operator
```

Codex `ssh/devbox` remote-operator path:

```bash
uv run python scripts/codex_preflight.py --ssh-devbox --json
uv run python scripts/codex_preflight.py --ssh-devbox --operator
```

If you intend to use Aristotle as a Tier 3 backend:

```bash
bash scripts/setup_mcp.sh --install --check
```

## Start a First Run

CLI path:

```bash
uv run deep-gvr run "Explain why the surface code is understood to have a threshold."
```

Hermes path:

```text
/deep-gvr "Explain why the surface code is understood to have a threshold."
```

Codex-local path:

```bash
codex exec -C /path/to/deep-gvr "Use the deep-gvr skill to answer: Explain why the surface code is understood to have a threshold."
```

## Resume a Prior Run

```bash
uv run deep-gvr resume <session_id>
```

Or in Hermes:

```text
/deep-gvr resume <session_id>
```

Or in Codex local:

```bash
codex exec -C /path/to/deep-gvr "Use the deep-gvr skill to resume session <session_id>."
```

## Where Outputs Land

- Config: `${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/config.yaml`
- Sessions: `${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/sessions/<session_id>/`
- Checkpoint: `${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/sessions/<session_id>/checkpoint.json`
- Artifacts: `${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/sessions/<session_id>/artifacts/`
- Hermes memory summary target: `~/.hermes/memories/MEMORY.md`

The Codex-local surface uses the same runtime state and artifact locations.

## How to Tell a Run Succeeded

A healthy run should give you:

- a structured result summary in the CLI or Hermes response
- a session directory for the run
- a checkpoint file
- artifacts that match the work performed

Examples:

- Tier 1-only runs should still leave evidence and checkpoint artifacts
- Tier 2 runs should leave analysis request and result artifacts
- Tier 3 runs should leave formal request, transport, lifecycle, and result artifacts

If the run stops early, the session directory is usually the fastest way to see whether the failure was provider-side, verification-side, or backend-side.
