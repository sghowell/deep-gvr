---
name: "deep-gvr"
description: "Use this skill when operating deep-gvr from Codex local against a deep-gvr checkout."
---

# deep-gvr Codex local skill

This skill is the Codex-local operator surface for `deep-gvr`.

Use it when the user wants Codex to run `deep-gvr` from a local checkout instead of using the Hermes `/deep-gvr` command directly.

## What this skill does

- operates the existing `deep-gvr` runtime from the repository checkout
- uses the supported CLI entrypoints instead of reimplementing the harness in free-form chat
- helps the user inspect the resulting evidence and artifacts after the run

## What this skill does not do

- it does not answer a `deep-gvr` request directly in free-form prose when the user wants the real harness path
- it does not modify release policy or `auto_improve` settings unless the user explicitly asks for that

## Procedure

When the user wants to run `deep-gvr` from Codex local:

1. Confirm you are in a `deep-gvr` checkout.
2. If the install state is uncertain, run:
   - `bash scripts/install_codex.sh`
   - `uv run python scripts/codex_preflight.py --operator`
3. For a new run, use:
   - `uv run deep-gvr run "<question>"`
4. For resume, use:
   - `uv run deep-gvr resume <session_id>`
5. Treat `runtime.orchestrator_backend` as authoritative:
   - `hermes` means the run executes through Hermes
   - `codex_local` means the run executes through Codex natively and does not require Hermes underneath
6. After the run, inspect the session artifacts under `${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/sessions/<session_id>/` when the user needs evidence, failure diagnosis, or backend details.

## Boundaries

- Treat Codex local as a first-class surface over the same typed runtime. The actual backend comes from `runtime.orchestrator_backend`.
- If the selected backend or provider environment is not ready, say so explicitly and point the user at `scripts/codex_preflight.py --operator`.
- If the user wants the Hermes slash-command path specifically, direct them to `/deep-gvr` rather than trying to emulate it in Codex chat.
