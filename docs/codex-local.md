# Codex Local

This guide covers the supported Codex-local surface for `deep-gvr`.

Codex local is a first-class operator surface for the project, and `runtime.orchestrator_backend=codex_local` is now a real native backend option. The Codex-local path writes the same configs, checkpoints, evidence, and artifacts as the Hermes and direct CLI paths, but it no longer needs Hermes underneath when the Codex backend is selected. The native Codex backend now executes Generator, Verifier, and Reviser as separate Codex role calls over the same typed Tier 1 loop rather than routing the whole session through one opaque summary prompt.

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
- Hermes Agent installed and available as `hermes` if you want the Hermes `/deep-gvr` path or the `hermes` backend
- Access to the model provider route used by your selected runtime config

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

This installs the Codex-local `deep-gvr` skill into `~/.codex/skills/deep-gvr` and, by default, also refreshes the Hermes skill/runtime surface so both backend paths remain available on the same machine.

If you only want the Codex-native backend path and do not need the Hermes surface on that machine:

```bash
bash scripts/install_codex.sh --skip-hermes-install
```

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

If you also want to validate the Hermes slash-command path directly, run:

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

## Native Role Backend

When `runtime.orchestrator_backend=codex_local` is selected, `deep-gvr` now uses Codex local for the role loop itself:

- Generator, Verifier, and Reviser run as separate native Codex calls
- the checked-in role prompts under `prompts/` remain authoritative
- checkpoints, evidence, branch escalation, Tier 2 analysis, and Tier 3 formal verification remain owned by the typed Python runtime
- the transcript artifact records the individual Codex role calls instead of only one backend-summary exchange
- successful role calls persist parsed JSON payloads in the transcript artifact, and failed role calls still leave a structured error record there
- the existing capability-evidence artifact now includes a Codex-specific `codex_native_role_execution` record when the native backend runs

That is the main architectural difference between the current Codex backend and the earlier thin-wrapper phase.

## Shared Runtime State

The Codex-local surface uses the same underlying runtime state as the Hermes and direct CLI paths. The runtime home is selected through `DEEP_GVR_HOME` when set and otherwise falls back to the compatibility path under `${HERMES_HOME:-~/.hermes}/deep-gvr`:

- Config: `${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/config.yaml`
- Sessions: `${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/sessions/<session_id>/`
- Checkpoint: `${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/sessions/<session_id>/checkpoint.json`
- Artifacts: `${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/sessions/<session_id>/artifacts/`

Codex-local review, subagent fanout, and visual-QA work can also be run from an SSH/devbox-connected Codex session when your validation stack lives on a remote machine. With `runtime.orchestrator_backend=codex_local`, that remote Codex session can also execute the native Codex backend from the stronger environment through `uv run python scripts/codex_ssh_devbox_run.py ...`. For the explicit remote-validator/operator path, use [Codex SSH Devbox](codex-ssh-devbox.md).

If you want the repo to materialize the remote skill/config surface on that machine first, use:

```bash
uv run python scripts/codex_remote_bootstrap.py --json
```

## Current Boundary

Codex local now covers three supported cases:

- Codex as a first-class operator surface over the same typed runtime
- Codex as the selected native orchestrator backend when `runtime.orchestrator_backend=codex_local`
- Codex as the same native backend when it is executed from a remote Codex SSH/devbox session

That means:

- `uv run deep-gvr run ...` can execute through Codex natively when the backend is set to `codex_local`
- the Codex backend now runs Generator, Verifier, and Reviser as separate native role executions over the typed loop
- `uv run python scripts/codex_ssh_devbox_run.py run ...` can gate and execute that same native backend from a remote Codex SSH/devbox session
- Hermes is only required if you also want the Hermes `/deep-gvr` surface or the `hermes` backend
- provider, Tier 2, and Tier 3 readiness still depend on the same operator environment
