# Codex Local

This guide covers the supported Codex-local surface for `deep-gvr`.

Codex local is a first-class operator surface for the project, but it is not a separate runtime backend. It operates the same typed `deep-gvr` runtime and writes the same configs, checkpoints, evidence, and artifacts as the Hermes and direct CLI paths.

If you specifically want the packaged bundle surface, see [Codex Plugin](codex-plugin.md). If you want recurring scheduled work around the same checkout, see [Codex Automations](codex-automations.md). If you want a Codex-native review and visual-QA prompt pack, see [Codex Review and Visual QA](codex-review-qa.md).

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
- Access to the model provider route used by your Hermes runtime

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

This installs the Codex-local `deep-gvr` skill into `~/.codex/skills/deep-gvr` and refreshes the underlying Hermes skill/runtime install used by the shipped delegated backend.

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
uv run python scripts/release_preflight.py --operator --config ~/.hermes/deep-gvr/config.yaml
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

The Codex-local surface uses the same underlying runtime state as the Hermes and direct CLI paths:

- Config: `~/.hermes/deep-gvr/config.yaml`
- Sessions: `~/.hermes/deep-gvr/sessions/<session_id>/`
- Checkpoint: `~/.hermes/deep-gvr/sessions/<session_id>/checkpoint.json`
- Artifacts: `~/.hermes/deep-gvr/sessions/<session_id>/artifacts/`

Codex-local review and visual-QA work can also be run from an SSH/devbox-connected Codex session when your validation stack lives on a remote machine. That does not change the runtime boundary; it only changes where Codex is operating from.

## Current Boundary

Codex local is a supported peer surface over the same runtime. It does not replace the delegated Hermes execution backend on the shipped path today.

That means:

- Codex local should be treated as a supported way to operate `deep-gvr`
- Hermes still needs to be installed and working underneath
- provider, Tier 2, and Tier 3 readiness still depend on the same operator environment
