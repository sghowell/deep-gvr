# Codex Subagents

This page covers the shipped Codex subagent surface for `deep-gvr`.

The subagent surface is intentionally narrow. The repo ships a reviewable prompt pack and export helpers for Codex multi-agent work; it does not claim to configure Codex's live subagent runtime, delegation settings, or app state for you. The prompt pack now sits on top of a real native Codex backend, but it is still an operator coordination layer rather than the backend implementation itself.

## What the Repo Ships

The checked-in subagent pack lives at:

- `codex_subagents/catalog.json`
- `codex_subagents/templates/parallel_validator_fanout.prompt.md`
- `codex_subagents/templates/parallel_surface_review.prompt.md`

The repo also ships two export paths:

- `uv run python scripts/export_codex_subagents.py --output-root <dir>`
- `bash scripts/install_codex.sh --subagents-root <dir>`

Those exports materialize the current checkout path into the shipped prompts so they are ready to use from Codex against the exact repo state you exported.

## Included Prompts

### Parallel Validator Fanout

Use this when you want Codex to split a `deep-gvr` implementation or validation task across multiple agents safely.

The shipped prompt is tuned for:

- one main agent owning integration
- subagents limited to disjoint scopes
- separate worktrees for concurrent edits
- exact command and file reporting
- full integrated validation after subagents return

### Parallel Surface Review

Use this when you want Codex to review the runtime, tests, public docs, and release surface in parallel.

The shipped prompt is tuned for:

- findings first
- runtime/contracts/tests review
- public-docs and diagram review
- release/install/preflight drift review
- main-agent synthesis instead of conflicting independent conclusions

## Safe Operating Model

The repo-owned boundary is explicit:

- the main agent owns planning, integration, staging, commits, merge, and push decisions
- subagents should either use separate worktrees or clearly disjoint write scopes
- subagents should not push, merge, or silently rewrite shared repo policy

This matters especially in `deep-gvr`, where code, schemas, templates, prompts, docs, and validation often need to move together in the same integrated change.

## Export the Prompt Pack

Minimal export:

```bash
uv run python scripts/export_codex_subagents.py --output-root /tmp/deep-gvr-codex-subagents
```

If you are already installing the Codex-local surface, you can export the subagent pack at the same time:

```bash
bash scripts/install_codex.sh --subagents-root /tmp/deep-gvr-codex-subagents
```

Both commands produce an export bundle containing:

- `catalog.json`
- `prompts/parallel_validator_fanout.md`
- `prompts/parallel_surface_review.md`

## Relationship to Other Codex Surfaces

- [Codex Local](codex-local.md) is the main interactive operator path and now owns the native role-separated Codex backend.
- [Codex Plugin](codex-plugin.md) packages that path as a reusable local bundle.
- [Codex Automations](codex-automations.md) covers recurring scheduled work.
- [Codex Review and Visual QA](codex-review-qa.md) covers single-agent review and browser-driven docs QA.
- [Codex SSH Devbox](codex-ssh-devbox.md) covers the explicit remote validator/operator path.

The subagent pack is different: it is for deliberate multi-agent coordination over the same runtime and checkout discipline.

## Current Boundary

The shipped subagent pack is:

- versioned in the repo
- validated by repo checks and release/preflight
- exportable with the current checkout path substituted into the prompts

It is not:

- the `deep-gvr` runtime backend itself
- a claim that the repo can manage Codex's internal subagent state
- permission for subagents to bypass the repo's branch, validation, or merge discipline
