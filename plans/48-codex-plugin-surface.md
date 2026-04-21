# 48 Codex Plugin Surface

## Purpose / Big Picture

Package `deep-gvr` as a real Codex plugin surface, not just a checked-in standalone skill. The plugin must stay thin: it should expose the existing Codex-local workflow as a bundled, first-class distribution asset without inventing a second runtime or drifting from the Hermes-backed execution path.

This slice is about packaging, release discipline, and operator clarity. It is not a Codex Cloud slice and it is not a new orchestration backend.

## Branch Strategy

Start from `main` and implement this slice on `codex/codex-plugin-surface`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result again, push `main`, confirm CI, and delete the feature branch when it is no longer needed.

## Commit Plan

- `add codex plugin bundle`
- `wire codex plugin release checks`
- `document codex plugin surface`

## Progress

- [x] Add the numbered plan and index entry.
- [x] Add the checked-in Codex plugin bundle and local marketplace metadata.
- [x] Wire repo checks, preflight, and release metadata to the plugin surface.
- [x] Update public/operator docs.
- [x] Run full validation.
- [ ] Merge locally, revalidate on `main`, push, confirm CI, and delete the feature branch.

## Surprises & Discoveries

- The current repo can ship a clean Codex plugin bundle without pretending to own Codex’s internal install cache layout. The stable, repo-owned surface is the checked-in plugin bundle plus a local marketplace manifest; explicit export from `scripts/install_codex.sh --plugin-root <dir>` is enough for local testing and distribution.
- The local `codex` CLI still reports `plugins` as an under-development feature flag on this machine, so the plugin slice needs to stay honest about what is repo-complete versus what still depends on Codex product availability.
- OpenAI’s March 26, 2026 plugin launch notes make the right packaging boundary clear: plugins are reusable bundles for skills plus optional apps/MCP, and availability follows workspace app controls.

## Decision Log

- Decision: keep the plugin surface thin and skill-backed. The plugin should package the existing Codex-local workflow instead of introducing a second runtime.
- Decision: use a checked-in local marketplace at `.agents/plugins/marketplace.json` so the repo itself can act as the plugin source of truth.
- Decision: keep actual plugin export/install explicit rather than guessing at an opaque Codex cache layout.

## Outcomes & Retrospective

- Added a checked-in plugin bundle at `plugins/deep-gvr/` plus `.agents/plugins/marketplace.json` so the repository can act as a local Codex plugin source.
- Extended `scripts/install_codex.sh` so it can export a standalone local marketplace root with `--plugin-root`.
- Added repo-enforced schemas, release/preflight checks, and tests so the plugin surface is validated instead of being a docs-only claim.
- Updated the public/operator docs so Codex local and the packaged Codex plugin are presented as related but distinct surfaces over the same runtime.

## Context and Orientation

- Existing Codex-local surface: `codex_skill/SKILL.md`, `scripts/install_codex.sh`, `scripts/codex_preflight.py`
- Release surface: `src/deep_gvr/release_surface.py`, `release/agentskills.publication.json`
- Public docs: `README.md`, `docs/codex-local.md`, `docs/release-workflow.md`

## Plan of Work

1. Add a checked-in Codex plugin bundle that packages the existing deep-gvr Codex skill.
2. Make the release/preflight/check surfaces aware of the new plugin assets.
3. Update the public/operator docs so the plugin surface is explicit and supportable.

## Concrete Steps

1. Add `plugins/deep-gvr/.codex-plugin/plugin.json`, plugin assets, and the plugin-packaged skill.
2. Add `.agents/plugins/marketplace.json` so the repo can act as a local plugin marketplace root.
3. Extend `scripts/install_codex.sh` so it can export the plugin bundle into a standalone local marketplace root when requested.
4. Update release/preflight code and repo checks so the plugin bundle is enforced as part of the supported Codex surface.
5. Add or update human-facing docs for the plugin surface and its current boundary.

## Validation and Acceptance

Required validation:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Acceptance evidence:

- The repo contains a valid Codex plugin bundle and local marketplace manifest.
- The plugin-packaged skill stays aligned with the existing Codex-local skill.
- Release and Codex preflight checks fail if the plugin surface drifts or disappears.
- Public/operator docs explain what the plugin surface is and what it is not.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/codex-plugin-surface` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions runs for the pushed head are green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Plugin bundle generation should be entirely checked in and repeatable; a repo clone must contain the same plugin surface without needing hidden local state.
- Exporting a standalone local marketplace root must be safe to repeat with `--force`.
- If Codex plugin availability changes upstream, keep the checked-in bundle accurate and narrow instead of weakening it into vague docs-only support.

## Interfaces and Dependencies

- Depends on the existing Codex-local skill content in `codex_skill/SKILL.md`.
- Depends on the public docs site for stable plugin URLs.
- Depends on current Codex plugin availability and workspace app controls for actual discovery inside Codex.
