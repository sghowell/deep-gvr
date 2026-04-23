# 73 First Tagged Release Reconciliation

## Purpose / Big Picture

Reconcile the checked-in release history and operator release docs with the
current shipped `deep-gvr` surface, then cut the first real public tag from the
now-stable `main` branch. The user-visible outcome is that the repo's first
public tag and GitHub release match what the code, docs, and validation surface
actually ship today, instead of preserving an outdated pre-parity snapshot.

## Branch Strategy

Start from `main` and implement this slice on
`codex/first-tagged-release-reconciliation`. Merge back into `main` locally
with a fast-forward only after branch validation passes, then validate the
merged result, push `main`, cut the reconciled release tag, confirm the release
workflow and docs/CI are green, and delete the feature branch.

## Commit Plan

- `plan first tagged release reconciliation`
- `reconcile first public release metadata`
- `document first public release cut`

## Progress

- [x] Add this plan and index it from `plans/README.md`.
- [x] Audit the current release-history, version, and public-release surface.
- [x] Reconcile the `0.1.0` release notes with the actual shipped repo state.
- [x] Align release docs and checklist guidance with the current shipped surface.
- [x] Validate the reconciled release metadata and rendered release notes.

## Surprises & Discoveries

- The repo-owned Hermes/Codex parity and Tier 3 backend work overtook the old
  `0.1.0` changelog snapshot before any real tag was ever cut.
- The version surface itself is still coherent: `pyproject.toml` and
  `release/agentskills.publication.json` both still point at `0.1.0`.
- The real mismatch is historical and operator-facing, not runtime-facing:
  `CHANGELOG.md` still described OpenGauss as absent from the release path, and
  the release docs still used `0.1.0` as an example rather than a reconciled
  first tag.

## Decision Log

- Keep the first real public tag at `v0.1.0` rather than inventing a new
  version purely because the tag was delayed.
- Reconcile the `0.1.0` changelog entry to the current shipped repo state,
  because there has never been an earlier public tag that would make the newer
  shipped capabilities a separate semantic release.
- Treat this as release-history and operator-surface reconciliation, not as a
  new runtime slice.

## Outcomes & Retrospective

- The release history now matches the current shipped repo state for the first
  public tag.
- The release workflow docs and release checklist now describe the actual Tier 2
  and Tier 3 support surface, including OpenGauss.
- The repo is ready for its first real tagged GitHub release from `main`.

## Context and Orientation

- Release metadata: `pyproject.toml`, `release/agentskills.publication.json`
- Release history: `CHANGELOG.md`
- Release docs: `docs/release-workflow.md`, `release/release-checklist.md`
- Existing public-release plan: `plans/39-public-release-and-distribution.md`

## Plan of Work

1. Materialize this release-reconciliation slice and index it.
2. Reconcile the `0.1.0` release notes and release-history text.
3. Align the release docs and checklist with the actual shipped surface.
4. Validate the release metadata and render the final release notes.

## Concrete Steps

1. Add `plans/73-first-tagged-release-reconciliation.md` and index it in
   `plans/README.md`.
2. Update `CHANGELOG.md` so the `0.1.0` section describes the actual first
   public release surface:
   - full Tier 2 portfolio support
   - Aristotle, MathCode, and OpenGauss Tier 3 support
   - Codex local/plugin/automation/backend parity work
   - explicit `auto_improve: false` release policy
3. Update `docs/release-workflow.md` and `release/release-checklist.md` so the
   release commands and validation steps match the current shipped surface and
   future release practice.
4. Refresh any stale status in `plans/39-public-release-and-distribution.md`
   that still implies the release infrastructure never merged or closed out.
5. Validate the reconciled release surface with:
   - repo checks
   - capability probes
   - full unit tests
   - release metadata check
   - rendered release notes
   - hosted docs build

## Validation and Acceptance

Required validation:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Release-specific validation:

```bash
uv run python scripts/release_preflight.py --json
uv run python scripts/check_release_version.py --tag v0.1.0
uv run python scripts/render_release_notes.py --version 0.1.0
uv run mkdocs build --strict
```

Acceptance evidence:

- The `0.1.0` changelog entry accurately describes the shipped repo state.
- The release docs no longer imply a stale pre-OpenGauss or pre-parity release
  surface.
- The repo validates cleanly for tag `v0.1.0`.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/first-tagged-release-reconciliation` into `main`
  locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions runs for the pushed head are green.
- Create and push tag `v0.1.0`, confirm the Release workflow succeeds, and
  verify the GitHub release contents.
- Delete the local feature branch, and delete the remote feature branch too if
  one was created.

## Idempotence and Recovery

- Re-running the release metadata checks and notes render should be safe and
  deterministic for the same repo state.
- If the tag has not been pushed yet, release-history reconciliation can still
  be amended locally without public drift.
- If the tagged release fails in GitHub Actions, fix `main`, rerun validation,
  and republish the same tag only after the release notes and bundle are still
  correct.

## Interfaces and Dependencies

- Depends on the existing release automation from
  `plans/39-public-release-and-distribution.md`.
- Depends on the completed Tier 2, Tier 3, Codex, and parity slices already
  being present on `main`.
- Does not add a new runtime/backend surface; it reconciles and publishes the
  one that already exists.
