# 52 Codex Review and Visual QA

## Purpose / Big Picture

Package a first-class, repo-owned Codex review and visual-QA surface for `deep-gvr`. The goal is to make high-signal pull-request review and browser-driven docs QA reproducible, exportable, and enforceable from the repository without pretending that `deep-gvr` owns Codex's live GitHub review settings, browser state, or computer-use session state.

This slice should stay thin. It is about review prompts, export helpers, release discipline, and operator clarity. It is not a new runtime backend and it is not a claim that the repo can directly register GitHub auto-review or browser automations inside Codex for the operator.

## Branch Strategy

Start from `main` and implement this slice on `codex/codex-review-and-visual-qa`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result again, push `main`, confirm CI, and delete the feature branch when it is no longer needed.

## Commit Plan

- `add codex review qa pack`
- `wire codex review qa release checks`
- `document codex review qa surface`

## Progress

- [x] Add the numbered plan and index entry.
- [x] Add the checked-in Codex review/QA catalog and prompt templates.
- [x] Add an export helper and wire the Codex install path to it.
- [x] Extend release checks, repo checks, schemas, and tests to cover the new surface.
- [x] Update public/operator docs and the architecture ledger.
- [x] Run full validation.
- [x] Merge locally, revalidate on `main`, push, confirm CI, and delete the feature branch.

## Surprises & Discoveries

- The best repo-owned boundary is a prompt kit, not a fake live-integration claim. Codex can now review PRs, use an in-app browser, and use computer control, but the repo cannot honestly provision those product-level capabilities itself.
- The existing Codex automation slice already covers recurring benchmark, CI, release, and docs-smoke workflows. This slice is complementary: higher-signal human-in-the-loop review and visual QA prompts rather than another scheduled-job pack.
- The same export pattern used for Codex automations works well here too: keep checkout-agnostic prompt templates in version control, then materialize the current repo root only at export time.

## Decision Log

- Decision: ship the review/QA surface as a checked-in prompt kit with a catalog and export helper rather than trying to wire live Codex product settings from the repo.
- Decision: scope the first pack to two concrete workflows: pull-request review and public-docs visual QA.
- Decision: keep this surface Codex-specific and human/operator-facing; do not turn it into a second `deep-gvr` runtime path.

## Outcomes & Retrospective

- Added a checked-in `codex_review_qa/` pack with contract-backed catalog metadata and exportable prompt templates.
- Added `scripts/export_codex_review_qa.py` plus `scripts/install_codex.sh --review-qa-root <dir>` to materialize a reviewable prompt bundle for the current checkout.
- Extended release metadata, repo checks, and preflight checks so the review/QA pack is enforced as part of the supported Codex surface.
- Updated public/operator docs to explain what the repo ships, how to use it from Codex, and where the boundary still lives.

## Context and Orientation

- Existing Codex surfaces: `codex_skill/SKILL.md`, `plugins/deep-gvr/.codex-plugin/plugin.json`, `codex_automations/catalog.json`, `docs/codex-local.md`, `docs/codex-plugin.md`, `docs/codex-automations.md`
- Release surface: `src/deep_gvr/release_surface.py`, `release/agentskills.publication.json`
- Public docs: `README.md`, `docs/index.md`, `docs/start-here.md`, `docs/release-workflow.md`

## Plan of Work

1. Add a checked-in Codex review/QA catalog and prompt pack for high-signal pull-request review and docs visual QA.
2. Add an export path that materializes the current checkout path safely without mutating live Codex product state.
3. Make release/preflight/check surfaces and public docs aware of the new Codex review/QA surface.

## Concrete Steps

1. Add `codex_review_qa/catalog.json` and checked-in markdown prompt templates for:
   - pull-request review
   - public-docs visual QA
2. Add a small export helper plus `scripts/install_codex.sh --review-qa-root <dir>` so operators can materialize a reviewable bundle for the current checkout.
3. Extend contracts, schemas, release metadata, and repo checks to cover the prompt pack.
4. Update human-facing docs and the architecture ledger so the Codex review/QA surface is explicit and accurately scoped.

## Validation and Acceptance

Required validation:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
uv run mkdocs build --strict
```

Acceptance evidence:

- The repo contains a valid Codex review/QA catalog and checked-in prompt templates for the supported workflows.
- The export helper materializes prompt bundles for the current checkout without mutating repo state.
- Release and Codex preflight checks fail if the review/QA pack drifts or disappears.
- Public/operator docs explain what the review/QA surface is and what it is not.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/codex-review-and-visual-qa` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions runs for the pushed head are green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Re-exporting the review/QA bundle should be safe and repeatable with `--force`.
- The checked-in prompt templates should remain checkout-agnostic by keeping repo-root substitution in the export step rather than in version control.
- If Codex changes its review or browser surfaces upstream, keep the repo surface narrow and truthful instead of weakening it into vague "review support" language.

## Interfaces and Dependencies

- Depends on the existing Codex-local and Codex plugin surfaces but does not replace them.
- Depends on current Codex PR review, browser, and computer-use support in the Codex product for the highest-value interactive flows.
- Uses only repo-owned prompt packs and export helpers; it does not depend on private Codex cache layout assumptions.
