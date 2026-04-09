# 36 Node 24 Actions

## Purpose / Big Picture

Retire the lingering GitHub Actions Node 20 deprecation warning by updating the CI workflow to the current Node-24-safe action versions. The user-visible outcome is a clean CI run without the known runtime deprecation warning for `actions/checkout` and `astral-sh/setup-uv`.

## Branch Strategy

Start from `main` and implement this slice on `codex/node24-actions`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result again, push `main`, confirm CI, and delete the feature branch when it is no longer needed.

## Commit Plan

- `upgrade ci actions to node24`

## Progress

- [x] Review the repo guidance and inspect the current CI workflow.
- [x] Confirm the current upstream action versions to use for the Node 24 runtime line.
- [x] Add this plan and index it from `plans/README.md`.
- [x] Update the workflow action versions.
- [x] Run the required repo validation commands.
- [ ] Merge locally, revalidate on `main`, push, confirm CI, and delete the feature branch.

## Surprises & Discoveries

- The repository has a single workflow file at `.github/workflows/ci.yml`, so the maintenance surface is narrow.
- The working tree was already on `codex/node24-actions`, which matches the intended branch name for this slice.

## Decision Log

- Keep this as a focused maintenance slice rather than folding it into a larger roadmap plan.
- Update only the action versions needed to retire the warning; do not refactor unrelated workflow logic in the same change.

## Outcomes & Retrospective

- Added a narrow maintenance plan and indexed it from `plans/README.md`.
- Updated the CI workflow from `actions/checkout@v4` to `actions/checkout@v6` and from `astral-sh/setup-uv@v5` to `astral-sh/setup-uv@v7`.
- Completed the standard repo validation suite on the feature branch before merge.

## Context and Orientation

- CI workflow: `.github/workflows/ci.yml`
- Plans index: `plans/README.md`
- Repo validation: `scripts/check_repo.py`, `scripts/run_capability_probes.py`, and the unittest suite

## Plan of Work

1. Add this maintenance plan to the plans index.
2. Upgrade the CI workflow to the current Node-24-safe action versions.
3. Run the standard repo validation commands.
4. Merge, revalidate, push, and confirm that CI no longer emits the Node 20 warning.

## Concrete Steps

1. Add `plans/36-node24-actions.md` and index it in `plans/README.md`.
2. Update `.github/workflows/ci.yml` to use `actions/checkout@v6` and `astral-sh/setup-uv@v7`.
3. Run:
   - `uv run python scripts/check_repo.py`
   - `uv run python scripts/run_capability_probes.py`
   - `uv run python -m unittest discover -s tests -v`
4. Fast-forward merge `codex/node24-actions` into `main`, rerun the same validation commands on `main`, push, and confirm the GitHub Actions run is green.

## Validation and Acceptance

Required validation:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Acceptance evidence:

- `.github/workflows/ci.yml` uses Node-24-safe action versions for checkout and uv setup.
- The local validation suite passes on the feature branch and again after the local merge into `main`.
- The next CI run completes without the previous Node 20 deprecation warning.

## Merge, Push, and Cleanup

- Stage and commit the plan and workflow change together with the message `upgrade ci actions to node24`.
- Validate the feature branch before merge.
- Fast-forward merge `codex/node24-actions` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Re-running this slice should leave the workflow pinned to the same supported action versions.
- If upstream action versions advance again later, a future maintenance slice can repeat the same narrow update pattern without further repo changes.

## Interfaces and Dependencies

- Depends on official upstream GitHub Action releases for `actions/checkout` and `astral-sh/setup-uv`.
- Affects only GitHub Actions runtime behavior; it does not change the repository's Python runtime or application interfaces.
