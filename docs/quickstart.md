# Quickstart

This guide gets a new operator from a local checkout to a first successful `deep-gvr` run.

## Prerequisites

- Python 3.12
- `uv`
- Hermes Agent installed if you want the shipped delegated runtime path
- Codex local installed if you want the Codex-local surface
- Access to whichever model provider route your Hermes setup uses

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

The Codex install path installs the Codex-local skill and also refreshes the underlying Hermes skill/runtime install used by the shipped delegated backend.

## Run Preflight

Hermes and direct CLI path:

```bash
uv run python scripts/release_preflight.py --json
uv run python scripts/release_preflight.py --operator --config ~/.hermes/deep-gvr/config.yaml
```

Codex-local path:

```bash
uv run python scripts/codex_preflight.py --json
uv run python scripts/codex_preflight.py --operator
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

- Config: `~/.hermes/deep-gvr/config.yaml`
- Sessions: `~/.hermes/deep-gvr/sessions/<session_id>/`
- Checkpoint: `~/.hermes/deep-gvr/sessions/<session_id>/checkpoint.json`
- Artifacts: `~/.hermes/deep-gvr/sessions/<session_id>/artifacts/`
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
