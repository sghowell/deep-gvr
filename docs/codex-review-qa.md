# Codex Review and Visual QA

This page covers the shipped Codex review and visual-QA surface for `deep-gvr`.

The review/QA surface is intentionally narrow. The repo ships a reviewable prompt pack and export helpers for Codex; it does not claim to register live GitHub review settings, browser sessions, or computer-use jobs inside Codex for you.

## What the Repo Ships

The checked-in review/QA pack lives at:

- `codex_review_qa/catalog.json`
- `codex_review_qa/templates/pull_request_review.prompt.md`
- `codex_review_qa/templates/public_docs_visual_qa.prompt.md`

The repo also ships two export paths:

- `uv run python scripts/export_codex_review_qa.py --output-root <dir>`
- `bash scripts/install_codex.sh --review-qa-root <dir>`

Those exports materialize the current checkout path into the shipped prompts so they are ready for review in Codex.

## Included Prompts

### Pull Request Review

Use this when you want Codex to inspect the current branch or a specific PR with a bug-risk-first review style.

The shipped prompt is tuned for:

- findings first
- severity ordering
- explicit file references
- release-surface and docs drift
- missing tests and behavioral regressions

### Public Docs Visual QA

Use this when you want Codex to build the hosted docs and run a visual QA pass over the public pages and diagrams.

The shipped prompt is tuned for:

- broken or missing images
- clipped or overflowing diagram text
- unreadable figure typography
- obvious layout breakage
- public-surface regressions across the main docs entrypoints

## Export the Prompt Pack

Minimal export:

```bash
uv run python scripts/export_codex_review_qa.py --output-root /tmp/deep-gvr-codex-review-qa
```

If you are already installing the Codex-local surface, you can export the review/QA pack at the same time:

```bash
bash scripts/install_codex.sh --review-qa-root /tmp/deep-gvr-codex-review-qa
```

Both commands produce an export bundle containing:

- `catalog.json`
- `prompts/pull_request_review.md`
- `prompts/public_docs_visual_qa.md`

## Local and SSH/Devbox Use

The review/QA pack works well in:

- a normal local Codex app session
- a local `codex exec` or Codex CLI workflow
- a Codex session connected to a remote devbox or SSH-accessible validator machine

That last case is especially useful when your validation stack, simulators, or remote artifacts live on a more capable machine than your laptop.

The repo boundary is still the same:

- `deep-gvr` already owns the runtime-side SSH backend for Tier 2
- the Codex review/QA pack is only a prompt surface over that environment
- the repo does not provision or manage Codex remote-devbox sessions itself

## Current Boundary

The shipped review/QA pack is:

- versioned in the repo
- validated by repo checks and release preflight
- exportable with the current checkout path substituted into the prompts

It is not:

- a new `deep-gvr` runtime backend
- a replacement for Hermes as the shipped delegated execution backend
- a claim that the repo can directly enable live GitHub auto-review or browser automation inside Codex

If you want the main interactive operator path, see [Codex Local](codex-local.md) and [Codex Plugin](codex-plugin.md). If you want recurring scheduled work instead, see [Codex Automations](codex-automations.md). If you want a multi-agent operating pack, see [Codex Subagents](codex-subagents.md). If you want the explicit remote-validator/operator path, see [Codex SSH Devbox](codex-ssh-devbox.md).
