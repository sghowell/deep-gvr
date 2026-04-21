# Codex Review and Visual QA

This page covers the shipped Codex review and visual-QA surface for `deep-gvr`.

The review/QA surface is still intentionally narrow, but it is no longer prompt-only. The repo now ships:

- a checked-in prompt pack for Codex
- export helpers for that prompt pack
- a typed execution helper that materializes repo-owned review evidence bundles before live Codex review or browser inspection

It still does not claim to register live GitHub review settings, browser sessions, or computer-use jobs inside Codex for you.

## What the Repo Ships

The checked-in review/QA pack lives at:

- `codex_review_qa/catalog.json`
- `codex_review_qa/templates/pull_request_review.prompt.md`
- `codex_review_qa/templates/public_docs_visual_qa.prompt.md`

The repo ships these export paths:

- `uv run python scripts/export_codex_review_qa.py --output-root <dir>`
- `bash scripts/install_codex.sh --review-qa-root <dir>`

Those exports materialize the current checkout path into the shipped prompts so they are ready for review in Codex.

The repo also ships a runtime-backed evidence helper:

- `uv run python scripts/codex_review_qa_execute.py pull_request_review --output-root <dir> --force`
- `uv run python scripts/codex_review_qa_execute.py public_docs_visual_qa --output-root <dir> --force`

That helper does not replace live review or visual inspection. It prepares a local evidence bundle that Codex can inspect first.

## Included Prompts

### Pull Request Review

Use this when you want Codex to inspect the current branch or a specific PR with a bug-risk-first review style.

The shipped prompt is tuned for:

- findings first
- severity ordering
- explicit file references
- release-surface and docs drift
- missing tests and behavioral regressions

The repo-owned evidence helper for this workflow writes:

- `review_target.json`
- `diff.patch`
- `name_status.txt`
- `diff_stat.txt`
- `release_preflight.json`
- `report.json`

On the default local-branch path, that bundle captures the current checkout state against `main`, including uncommitted working-tree changes.

### Public Docs Visual QA

Use this when you want Codex to build the hosted docs and run a visual QA pass over the public pages and diagrams.

The shipped prompt is tuned for:

- broken or missing images
- clipped or overflowing diagram text
- unreadable figure typography
- obvious layout breakage
- public-surface regressions across the main docs entrypoints

The repo-owned evidence helper for this workflow writes:

- `build.log`
- `visual_targets.json`
- `preview_targets.json`
- `report.json`

The helper builds the docs, verifies the key built pages exist, and checks that image assets referenced from those pages resolve inside the built site. Live browser or computer-use inspection is still where layout and typography judgment happens.

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

## Prepare a Review Evidence Bundle

For pull-request or branch review:

```bash
uv run python scripts/codex_review_qa_execute.py pull_request_review \
  --output-root /tmp/deep-gvr-codex-review-qa-evidence/review \
  --force --json
```

For public docs visual QA:

```bash
uv run python scripts/codex_review_qa_execute.py public_docs_visual_qa \
  --output-root /tmp/deep-gvr-codex-review-qa-evidence/docs \
  --force --json
```

Each run writes a typed `report.json` plus workflow-specific artifacts under the selected output root. The intent is to give Codex a repo-owned evidence bundle before it starts a live review or browser pass.

## Local and SSH/Devbox Use

The review/QA pack works well in:

- a normal local Codex app session
- a local `codex exec` or Codex CLI workflow
- a Codex session connected to a remote devbox or SSH-accessible validator machine

That last case is especially useful when your validation stack, simulators, or remote artifacts live on a more capable machine than your laptop.

The repo boundary is still the same:

- `deep-gvr` already owns the runtime-side SSH backend for Tier 2
- the Codex review/QA surface now includes a repo-owned evidence helper over that environment
- the repo does not provision or manage Codex remote-devbox sessions itself

## Current Boundary

The shipped review/QA pack is:

- versioned in the repo
- validated by repo checks and release preflight
- exportable with the current checkout path substituted into the prompts
- able to generate local review evidence bundles for branch review and public-docs QA

It is not:

- a new `deep-gvr` runtime backend
- a replacement for Hermes as the shipped delegated execution backend
- a claim that the repo can directly enable live GitHub auto-review or browser automation inside Codex

If you want the main interactive operator path, see [Codex Local](codex-local.md) and [Codex Plugin](codex-plugin.md). If you want recurring scheduled work instead, see [Codex Automations](codex-automations.md). If you want a multi-agent operating pack, see [Codex Subagents](codex-subagents.md). If you want the explicit remote-validator/operator path, see [Codex SSH Devbox](codex-ssh-devbox.md).
