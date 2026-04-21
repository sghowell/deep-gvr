# Codex Local

This guide covers the supported Codex-local surface for `deep-gvr`.

Codex local is a first-class operator surface for the project. The runtime now has an explicit backend-selection seam, but the shipped execution backend today is still Hermes, so the current Codex-local path operates the same typed `deep-gvr` runtime and writes the same configs, checkpoints, evidence, and artifacts as the Hermes and direct CLI paths.

If you specifically want the packaged bundle surface, see [Codex Plugin](codex-plugin.md). If you want recurring scheduled work around the same checkout, see [Codex Automations](codex-automations.md). If you want a Codex-native review and visual-QA prompt pack, see [Codex Review and Visual QA](codex-review-qa.md). If you want a multi-agent operating pack, see [Codex Subagents](codex-subagents.md). If you want the explicit remote validator path, see [Codex SSH Devbox](codex-ssh-devbox.md).

## What Codex Local Means Here

Codex local support is for:

- the Codex desktop app
- the local `codex` CLI
- a local `deep-gvr` checkout on your machine

It is not the same thing as Codex Cloud. The standard shipped path today is local only.

## Prerequisites

- Python 3.12
- `uv`
- Codex local installed and available as `codex`
- Hermes Agent installed and available as `hermes`
- Access to the model provider route used by your selected runtime config. On the shipped path today, that still means the Hermes delegated backend.

Optional extras:

- `uv sync --extra analysis`
- `uv sync --extra quantum_oss`

## Install the Codex Surface

From the repository root:

```bash
uv sync
uv sync --extra analysis --extra quantum_oss
bash scripts/install_codex.sh
```

This installs the Codex-local `deep-gvr` skill into `~/.codex/skills/deep-gvr` and refreshes the underlying Hermes skill/runtime install used by the shipped default backend.

If you also want a standalone local plugin marketplace root exported from the checked-in bundle:

```bash
bash scripts/install_codex.sh --plugin-root /tmp/deep-gvr-codex-plugin
```

If you also want the checked-in Codex automation pack exported for review:

```bash
bash scripts/install_codex.sh --automation-root /tmp/deep-gvr-codex-automations
```

If you also want the Codex review and visual-QA prompt pack exported for review:

```bash
bash scripts/install_codex.sh --review-qa-root /tmp/deep-gvr-codex-review-qa
```

If you also want the Codex subagent prompt pack exported for review:

```bash
bash scripts/install_codex.sh --subagents-root /tmp/deep-gvr-codex-subagents
```

If you also want the Codex `ssh/devbox` remote-operator bundle exported for review:

```bash
bash scripts/install_codex.sh --ssh-devbox-root /tmp/deep-gvr-codex-ssh-devbox
```

## Run Codex Preflight

Structural check:

```bash
uv run python scripts/codex_preflight.py --json
```

Full operator check:

```bash
uv run python scripts/codex_preflight.py --operator
```

If you want to validate the Hermes slash-command path directly as well, run:

```bash
uv run python scripts/release_preflight.py --operator --config ${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/config.yaml
```

## Use It From Codex

In the Codex app, ask Codex to use the installed `deep-gvr` skill against the current checkout.

Examples:

- `Use the deep-gvr skill to explain why the surface code is understood to have a threshold.`
- `Use the deep-gvr skill to resume session <session_id> and summarize the current evidence.`

Non-interactive CLI path:

```bash
codex exec -C /path/to/deep-gvr "Use the deep-gvr skill to answer: Explain why the surface code is understood to have a threshold."
```

## Shared Runtime State

The Codex-local surface uses the same underlying runtime state as the Hermes and direct CLI paths. The runtime home is selected through `DEEP_GVR_HOME` when set and otherwise falls back to the compatibility path under `${HERMES_HOME:-~/.hermes}/deep-gvr`:

- Config: `${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/config.yaml`
- Sessions: `${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/sessions/<session_id>/`
- Checkpoint: `${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/sessions/<session_id>/checkpoint.json`
- Artifacts: `${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/sessions/<session_id>/artifacts/`

Codex-local review, subagent fanout, and visual-QA work can also be run from an SSH/devbox-connected Codex session when your validation stack lives on a remote machine. That does not change the runtime boundary; it only changes where Codex is operating from. For the explicit remote-validator/operator path, use [Codex SSH Devbox](codex-ssh-devbox.md).

## Current Boundary

Codex local is a supported peer surface over the same runtime. The runtime is now backend-abstracted, but Codex local still does not replace the delegated Hermes execution backend on the shipped path today.

That means:

- Codex local should be treated as a supported way to operate `deep-gvr`
- Hermes still needs to be installed and working underneath
- provider, Tier 2, and Tier 3 readiness still depend on the same operator environment
