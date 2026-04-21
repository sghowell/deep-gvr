# Codex SSH Devbox

This page covers the supported Codex `ssh/devbox` operator surface for `deep-gvr`.

This surface is for the case where Codex is already operating from a remote devbox or SSH-accessible machine and you want `deep-gvr` to use that stronger environment for simulation-heavy validation, backend checks, or artifact inspection.

The repo-owned boundary stays narrow:

- the repo ships a checked-in `ssh/devbox` prompt bundle
- the repo ships export and install helpers for that bundle
- the repo ships a dedicated Codex preflight mode for the remote-validator path

It does not claim to create or manage Codex SSH/devbox sessions for you.

## What the Repo Ships

The checked-in `ssh/devbox` bundle lives at:

- `codex_ssh_devbox/catalog.json`
- `codex_ssh_devbox/templates/remote_validator_run.prompt.md`
- `codex_ssh_devbox/templates/remote_backend_triage.prompt.md`

The repo also ships two export paths:

- `uv run python scripts/export_codex_ssh_devbox.py --output-root <dir>`
- `bash scripts/install_codex.sh --ssh-devbox-root <dir>`

## When to Use This Surface

This path is useful when:

- your simulator or validator stack lives on a remote machine
- your laptop is not the right place to run heavier analysis or backend checks
- you want Codex to inspect the same checkout from a remote devbox or SSH-connected environment

It is especially useful when the `deep-gvr` Tier 2 SSH backend is part of the intended operator path.

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

That mode reuses the existing Tier 2 SSH backend readiness evidence and reports whether the remote-validator path is actually ready.

## What the Remote Check Requires

The `--ssh-devbox` operator path expects:

- a valid `deep-gvr` runtime config
- Codex local available as `codex`
- the installed Codex `deep-gvr` skill
- Hermes installed for the shipped delegated backend
- the checked-in Codex `ssh/devbox` prompt pack present in the repo
- the Tier 2 SSH backend configured and ready

In practice, that usually means:

- `verification.tier2.ssh.host` is set
- `verification.tier2.ssh.remote_workspace` is set
- `ssh` and `scp` are available
- provider credentials are present in the shell that launches the run

## Current Boundary

The shipped `ssh/devbox` surface is:

- versioned in the repo
- validated by repo checks and release preflight
- exportable with the current checkout path substituted into the prompts

It is not:

- a second `deep-gvr` runtime backend
- a replacement for Hermes as the shipped delegated execution backend
- a claim that the repo can provision Codex SSH/devbox sessions directly

If you want the main interactive local operator path, see [Codex Local](codex-local.md). If you want a browser-driven review workflow, see [Codex Review and Visual QA](codex-review-qa.md). If you want a multi-agent operating pack, see [Codex Subagents](codex-subagents.md).
