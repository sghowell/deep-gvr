# Quickstart

This guide gets a new operator from a local checkout to a first successful `deep-gvr` run.

## Prerequisites

- Python 3.12
- `uv`
- Hermes Agent installed if you want the Hermes `/deep-gvr` path or the `hermes` backend
- Codex local installed if you want the Codex-local surface
- a Codex client/workspace with plugin support if you want to use the packaged Codex plugin surface
- Access to whichever model provider route your selected runtime config uses.

Optional extras:

- `uv sync --all-extras` for the validated full-portfolio environment
- `uv sync --extra analysis` for the broader scientific analysis families only
- `uv sync --extra quantum_oss` for the broader OSS quantum families only

## Install the Project Environment

```bash
uv sync
uv sync --all-extras
```

`uv sync` is the minimal path. `uv sync --all-extras` is the recommended path when you want the full shipped Tier 2 portfolio available on the same machine and want to match the repo’s validated CI/release environment.

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

If you want to prove the documented install and structural preflight flows from
throwaway temp homes instead of your real operator home, run:

```bash
uv run python scripts/clean_room_install_smoke.py --json
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
uv run python scripts/codex_remote_bootstrap.py --json
uv run python scripts/codex_preflight.py --ssh-devbox --json
uv run python scripts/codex_preflight.py --ssh-devbox --operator
```

Important Tier 2 boundary:

- only `qec_decoder_benchmark` currently supports `modal` or `ssh` Tier 2
  execution
- the other shipped Tier 2 families are local-only today and should keep
  `verification.tier2.default_backend: local`

Use [Tier 2 and Tier 3 Support Matrix](tier2-tier3-support-matrix.md) before
changing the default adapter family or Tier 2 backend.

If you intend to use Aristotle as a Tier 3 backend:

```bash
bash scripts/setup_mcp.sh --install --check
```

Important Tier 3 boundary:

- Aristotle is the shipped submission, polling, and resume path, using Hermes
  MCP as the primary transport with direct CLI fallback
- MathCode is the shipped bounded local CLI path and does not provide a
  submission, polling, or resume lifecycle
- OpenGauss is the shipped bounded local CLI path over `gauss chat -Q`; it can
  capture session identifiers and transcript paths when the CLI emits them, but
  it does not provide a shipped submission, polling, or resume lifecycle

Use [Tier 2 and Tier 3 Support Matrix](tier2-tier3-support-matrix.md) before
switching Tier 3 backends for operator use.

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

Codex `ssh/devbox` native remote-execution path:

```bash
uv run python scripts/codex_ssh_devbox_run.py run "Explain why the surface code is understood to have a threshold."
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

Or from a Codex SSH/devbox session:

```bash
uv run python scripts/codex_ssh_devbox_run.py resume <session_id>
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
