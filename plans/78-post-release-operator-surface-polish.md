# 78 Post Release Operator Surface Polish

## Purpose / Big Picture

Polish the shipped operator-facing surface now that the core backend and release
work is complete. The user-visible outcome is that a new operator can choose the
right install path more quickly, the docs stop implying that multiple sync
commands should always be run in sequence, and the preflight scripts return a
short actionable next-step list instead of only a long list of raw checks.

## Branch Strategy

Start from `main` and implement this slice on
`codex/post-release-operator-surface-polish`. Merge back into `main` locally
with a fast-forward only after branch validation passes, then validate the
merged result again, push `main`, confirm the remote CI and Docs workflows are
green, and delete the feature branch.

## Commit Plan

- `plan post release operator polish`
- `polish operator surface guidance`

## Progress

- [x] Add this plan and index it from `plans/README.md`.
- [x] Inspect the current public operator docs and preflight/report surfaces.
- [ ] Make the environment sync and install choices explicit in the public docs.
- [ ] Add a concise operator-surface chooser for Hermes, Codex-local, and
      hybrid/local-release use.
- [ ] Extend the release and Codex preflight reports with a short top-level
      next-step list and surface it in the human-readable script output.
- [ ] Update tests, schemas, and templates for the report contract change.
- [ ] Run the required repo validation commands and a strict hosted-docs build.
- [ ] Merge locally, revalidate on `main`, push, confirm remote CI and Docs,
      and delete the feature branch.

## Surprises & Discoveries

- The public docs already explain the difference between `uv sync` and
  `uv sync --all-extras`, but several primary command blocks still show both in
  the same sequence, which reads like a required pair instead of a choice.
- The install scripts and preflight scripts already carry strong per-check
  guidance, but they do not currently summarize the highest-value next actions
  at the report top level.
- The current public entrypoints (`README.md`, `docs/start-here.md`,
  `docs/quickstart.md`, `docs/codex-local.md`, and `docs/release-workflow.md`)
  all participate in the operator story, so this slice should keep them aligned
  instead of patching only one page.

## Decision Log

- Keep this as an operator-surface polish slice, not a new architecture or
  backend slice.
- Use the existing public docs pages instead of creating a large new docs tree;
  add one concise chooser section where it materially helps.
- Extend the typed preflight report contract with a top-level `next_steps`
  field so the JSON and human-readable outputs stay aligned.
- Build the `next_steps` list from the existing check guidance so the repo
  continues to own one guidance source of truth.

## Outcomes & Retrospective

- New operators will see clearly that `uv sync`, `uv sync --all-extras`, and
  targeted extras are alternative environment paths, not a required chained
  sequence.
- The public docs will expose a clearer choose-your-surface path for Hermes,
  Codex-local, and mixed/local release use.
- `release_preflight.py` and `codex_preflight.py` will produce a shorter,
  operator-usable action summary without losing the detailed per-check payload.

## Context and Orientation

- Public entrypoints: `README.md`, `docs/start-here.md`, `docs/quickstart.md`,
  `docs/codex-local.md`, `docs/release-workflow.md`
- Install surfaces: `scripts/install.sh`, `scripts/install_codex.sh`
- Preflight/report logic: `src/deep_gvr/release_surface.py`,
  `scripts/release_preflight.py`, `scripts/codex_preflight.py`
- Report contract: `src/deep_gvr/contracts.py`,
  `schemas/release_preflight.schema.json`,
  `templates/release_preflight.template.json`
- Relevant tests: `tests/test_release_scripts.py`, `tests/test_contracts.py`

## Plan of Work

1. Add and index this plan.
2. Normalize the public docs so environment sync and install paths are presented
   as explicit choices.
3. Add a concise operator-surface chooser to the main public entrypoints.
4. Extend the typed release-preflight report with a top-level `next_steps`
   field derived from the highest-priority blocked/attention guidance.
5. Update the human-readable preflight scripts to print that summary first.
6. Cover the new report contract and output behavior with focused tests.

## Concrete Steps

1. Add `plans/78-post-release-operator-surface-polish.md` and index it in
   `plans/README.md`.
2. Update the public operator docs so they clearly distinguish:
   - minimal local sync: `uv sync`
   - full validated portfolio: `uv sync --all-extras`
   - targeted extra sync paths for narrower Tier 2 families
3. Add or tighten a concise surface chooser across the public entrypoints so
   Hermes, Codex-local, and mixed/local release operators know which path to
   follow first.
4. Update `scripts/install.sh` and `scripts/install_codex.sh` next-step text so
   it matches the clarified docs language.
5. Extend `ReleasePreflightReport` with `next_steps`, update
   `collect_release_preflight()` and `collect_codex_preflight()` to populate it,
   and update `scripts/release_preflight.py` plus `scripts/codex_preflight.py`
   to print it ahead of the raw check list.
6. Update the release-preflight schema, template, and focused tests.
7. Run:
   - `uv run python scripts/check_repo.py`
   - `uv run python scripts/run_capability_probes.py`
   - `uv run python -m unittest discover -s tests -v`
   - `uv run mkdocs build --strict`

## Validation and Acceptance

Required validation:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
uv run mkdocs build --strict
```

Acceptance evidence:

- The main public docs no longer present `uv sync` and `uv sync --all-extras`
  as an implied required pair.
- The public operator entrypoints clearly distinguish Hermes, Codex-local, and
  mixed/local-release usage paths.
- `ReleasePreflightReport` includes a top-level `next_steps` field that survives
  schema validation and round-trip contract tests.
- `scripts/release_preflight.py` and `scripts/codex_preflight.py` print the
  top-level next-step summary in human-readable mode.

## Merge, Push, and Cleanup

- Stage and commit the plan/index update first with
  `plan post release operator polish`.
- Stage and commit the docs/script/report polish changes with
  `polish operator surface guidance`.
- Validate the feature branch before merge.
- Fast-forward merge `codex/post-release-operator-surface-polish` into `main`
  locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the remote CI and Docs workflows are green.
- Delete the local feature branch, and delete the remote feature branch too if
  one was created.

## Idempotence and Recovery

- Re-running this slice should keep the same operator docs choices and the same
  preflight report contract.
- The new `next_steps` field should be derived from existing check guidance, so
  new preflight checks can participate without inventing a second guidance
  system.
- If operator docs grow later, the chooser and sync-path language can keep being
  updated in narrow public-doc slices without changing runtime semantics.

## Interfaces and Dependencies

- Depends on the existing release and Codex preflight checks remaining the
  source of truth for operator readiness.
- Affects public docs, install-script UX text, typed preflight artifacts, and
  focused tests.
- Does not change Tier 1, Tier 2, Tier 3, backend routing, or release metadata
  semantics.
