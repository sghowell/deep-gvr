# 49 Codex Automations

## Purpose / Big Picture

Package a first-class, repo-owned Codex automation surface for `deep-gvr`. The goal is to make recurring Codex work reviewable, exportable, and enforceable from the repository without pretending that `deep-gvr` owns Codex's live automation runtime state.

This slice should stay thin. It is about automation templates, export helpers, release discipline, and operator clarity. It is not a new runtime backend and it is not a claim that the repo can directly provision live Codex schedules inside the app-managed automation database.

## Branch Strategy

Start from `main` and implement this slice on `codex/codex-automations`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result again, push `main`, confirm CI, and delete the feature branch when it is no longer needed.

## Commit Plan

- `add codex automation pack`
- `wire codex automation release checks`
- `document codex automation surface`

## Progress

- [x] Add the numbered plan and index entry.
- [x] Add the checked-in Codex automation catalog and templates.
- [x] Add an export helper and wire the Codex install path to it.
- [x] Extend release checks, repo checks, and tests to cover the automation surface.
- [x] Update public/operator docs and the architecture ledger.
- [x] Run full validation.
- [x] Merge locally, revalidate on `main`, push, confirm CI, and delete the feature branch.

## Surprises & Discoveries

- Codex automation runtime state is not a pure file-tree concern: the app stores automation setup as TOML, but run timing state lives elsewhere. The honest repo-owned boundary is therefore a checked-in automation pack plus export helpers, not "automatic install into live Codex state."
- The current Codex product surface is clear enough to support this thin packaging model. OpenAI's February 2, 2026 Codex app launch notes and April 16, 2026 Codex update both frame automations as scheduled background work for recurring engineering tasks, which matches the benchmark, CI triage, release, and docs-smoke pack shipped here.
- Using a repo-root placeholder inside the checked-in TOML templates avoids baking one local checkout path into version-controlled automation definitions while still allowing exported bundles to materialize concrete working directories.

## Decision Log

- Decision: ship automation templates as a checked-in pack with a catalog and export helper rather than writing directly into live Codex app state.
- Decision: keep the automation pack paused by default so exported templates remain safe review artifacts instead of implicitly active background jobs.
- Decision: scope the first pack to four concrete workflows: benchmark sweep, CI triage, release sweep, and docs smoke.

## Outcomes & Retrospective

- Added a checked-in `codex_automations/` pack with a contract-backed catalog and reviewable TOML templates.
- Added `scripts/export_codex_automations.py` plus `scripts/install_codex.sh --automation-root <dir>` to export a concrete bundle for the current checkout.
- Extended release metadata, repo checks, and preflight checks so Codex automations are enforced as part of the supported Codex surface.
- Updated the human-facing docs to treat Codex automations as a supported recurring-work surface with an explicit boundary: exported templates, not repo-controlled live registration.

## Context and Orientation

- Existing Codex surfaces: `codex_skill/SKILL.md`, `plugins/deep-gvr/.codex-plugin/plugin.json`, `docs/codex-local.md`, `docs/codex-plugin.md`
- Release surface: `src/deep_gvr/release_surface.py`, `release/agentskills.publication.json`
- Public docs: `README.md`, `docs/index.md`, `docs/start-here.md`, `docs/release-workflow.md`

## Plan of Work

1. Add a checked-in Codex automation catalog and template pack for recurring `deep-gvr` workflows.
2. Add an export path that materializes the current checkout path safely without mutating live Codex runtime state.
3. Make release/preflight/check surfaces and public docs aware of the new Codex automation surface.

## Concrete Steps

1. Add `codex_automations/catalog.json` and checked-in TOML templates for the supported recurring workflows.
2. Add a small export helper plus `scripts/install_codex.sh --automation-root <dir>` so operators can materialize a reviewable bundle for the current checkout.
3. Extend contracts, schemas, release metadata, and repo checks to cover the automation pack.
4. Update human-facing docs and the architecture ledger so the Codex automation surface is explicit and accurately scoped.

## Validation and Acceptance

Required validation:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
uv run mkdocs build --strict
```

Acceptance evidence:

- The repo contains a valid Codex automation catalog and checked-in TOML templates for the supported recurring workflows.
- The export helper materializes concrete automation bundles for the current checkout without mutating repo state.
- Release and Codex preflight checks fail if the automation pack drifts or disappears.
- Public/operator docs explain what the Codex automation surface is and what it is not.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/codex-automations` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions runs for the pushed head are green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Re-exporting the automation bundle should be safe and repeatable with `--force`.
- The checked-in automation templates should remain checkout-agnostic by keeping repo-root substitution in the export step rather than in version control.
- If Codex changes its automation runtime semantics upstream, keep the repo surface narrow and truthful instead of weakening it into vague "automation support" language.

## Interfaces and Dependencies

- Depends on the existing Codex-local and Codex plugin surfaces but does not replace them.
- Depends on current Codex automation support in the Codex app for actual recurring execution.
- Depends on GitHub connectivity for the CI-triage automation to be fully useful.
- Uses only repo-owned export helpers and checked-in templates; it does not depend on private Codex cache layout assumptions.
