# Codex SSH Devbox

This page covers the supported Codex `ssh/devbox` operator surface for `deep-gvr`.

This surface is for the case where Codex is already operating from a remote devbox or SSH-accessible machine and you want `deep-gvr` to use that stronger environment for simulation-heavy validation, backend checks, or artifact inspection.

The repo-owned boundary is now:

- the repo ships a checked-in `ssh/devbox` prompt bundle
- the repo ships export and install helpers for that bundle
- the repo ships a dedicated Codex preflight mode for the remote-validator path
- the repo ships a runtime-backed remote execution helper over the native `codex_local` backend

It does not claim to create or manage Codex SSH/devbox sessions for you.

## What the Repo Ships

The checked-in `ssh/devbox` bundle lives at:

- `codex_ssh_devbox/catalog.json`
- `codex_ssh_devbox/templates/remote_validator_run.prompt.md`
- `codex_ssh_devbox/templates/remote_backend_triage.prompt.md`

The repo also ships two export paths plus a native remote execution helper:

- `uv run python scripts/export_codex_ssh_devbox.py --output-root <dir>`
- `bash scripts/install_codex.sh --ssh-devbox-root <dir>`
- `uv run python scripts/codex_ssh_devbox_run.py run "<question>"`

## When to Use This Surface

This path is useful when:

- your simulator or validator stack lives on a remote machine
- your laptop is not the right place to run heavier analysis or backend checks
- you want Codex to inspect the same checkout from a remote devbox or SSH-connected environment

It is especially useful when either:

- the remote machine itself is the right place to run the selected local Tier 2 backend
- the remote machine should operate the existing typed `ssh` or `modal` Tier 2 backend from a stronger Codex environment

## Export the Bundle

Minimal export:

```bash
uv run python scripts/export_codex_ssh_devbox.py --output-root /tmp/deep-gvr-codex-ssh-devbox
```

If you are already installing the Codex-local surface, you can export the `ssh/devbox` bundle at the same time:

```bash
bash scripts/install_codex.sh --ssh-devbox-root /tmp/deep-gvr-codex-ssh-devbox
```

Both commands produce an export bundle containing:

- `catalog.json`
- `prompts/remote_validator_run.md`
- `prompts/remote_backend_triage.md`

## Remote Preflight

Structural check:

```bash
uv run python scripts/codex_preflight.py --ssh-devbox --json
```

Full remote-operator check:

```bash
uv run python scripts/codex_preflight.py --ssh-devbox --operator
```

That mode now reports whether the native `codex_local` backend plus the selected Tier 2 backend are actually ready for remote execution from the SSH/devbox machine.

## Run a Remote Session

New session:

```bash
uv run python scripts/codex_ssh_devbox_run.py run "Explain why the surface code is understood to have a threshold."
```

Resume:

```bash
uv run python scripts/codex_ssh_devbox_run.py resume <session_id>
```

## What the Remote Check Requires

The `--ssh-devbox` operator path expects:

- a valid `deep-gvr` runtime config
- Codex local available as `codex`
- `runtime.orchestrator_backend=codex_local`
- the installed Codex `deep-gvr` skill as part of the supported Codex-local surface bundle
- Hermes installed only if Tier 3 or another selected path still requires it
- the checked-in Codex `ssh/devbox` prompt pack present in the repo
- the selected Tier 2 backend ready in the remote environment

In practice, that usually means:

- if `verification.tier2.default_backend=local`, the remote machine has the needed local analysis stack
- if `verification.tier2.default_backend=ssh`, `verification.tier2.ssh.host` and `verification.tier2.ssh.remote_workspace` are set and `ssh`/`scp` are available
- if `verification.tier2.default_backend=modal`, the remote machine has the configured Modal CLI and stub path available
- provider credentials are present in the shell that launches the run

## Current Boundary

The shipped `ssh/devbox` surface is:

- versioned in the repo
- validated by repo checks and release preflight
- exportable with the current checkout path substituted into the prompts
- executable through `scripts/codex_ssh_devbox_run.py` when the native Codex backend is selected

It is not:

- a second `deep-gvr` runtime backend beyond the existing backend selector
- a claim that the repo can provision Codex SSH/devbox sessions directly

If you want the main interactive local operator path, see [Codex Local](codex-local.md). If you want a browser-driven review workflow, see [Codex Review and Visual QA](codex-review-qa.md). If you want a multi-agent operating pack, see [Codex Subagents](codex-subagents.md).
