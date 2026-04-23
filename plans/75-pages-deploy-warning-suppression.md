# 75 Pages Deploy Warning Suppression

## Purpose / Big Picture

Retire the remaining upstream `punycode` deprecation warning in the hosted docs
workflow now that plan 74 already moved the repo to the current GitHub Pages
action line. The user-visible outcome is that the Docs workflow completes
without the stray `DEP0040` deploy-step warning even though the latest official
`actions/deploy-pages` release still bundles the warning-producing dependency.

## Branch Strategy

Start from `main` and implement this slice on
`codex/pages-deploy-warning-suppression`. Merge back into `main` locally with a
fast-forward only after branch validation passes, then validate the merged
result again, push `main`, confirm the docs workflow is green, and delete the
feature branch.

## Commit Plan

- `plan pages deploy warning suppression`
- `suppress pages deploy deprecation warning`

## Progress

- [x] Add this plan and index it from `plans/README.md`.
- [x] Confirm the remaining warning is still upstream in the latest official
      `actions/deploy-pages` line.
- [x] Add a narrow workflow-level suppression scoped to the deploy action step.
- [x] Update repo checks so the suppression rule stays encoded locally.
- [ ] Run the required repo validation commands and a strict hosted-docs build.
- [ ] Merge locally, revalidate on `main`, push, confirm the Docs workflow log
      is clean, and delete the feature branch.

## Surprises & Discoveries

- After plan 74, the old Node 20 Pages warning was gone, but the Docs workflow
  still emitted `(node:...) [DEP0040] DeprecationWarning: The punycode module
  is deprecated` during `actions/deploy-pages@v5`.
- GitHub's official `actions/deploy-pages` issue tracker now has an open issue
  for this exact warning: issue `#413`, opened on April 9, 2026.
- The current official Pages major line is still `actions/deploy-pages@v5`, so
  there is no newer in-repo action upgrade available to take today.

## Decision Log

- Treat this as a narrow log-hygiene workaround, not as a fake upstream fix.
- Scope the suppression only to the `Deploy to GitHub Pages` step instead of
  muting warnings across the whole workflow.
- Use `NODE_OPTIONS: --no-deprecation` rather than a broader warning kill
  switch so the workaround targets deprecation noise specifically.

## Outcomes & Retrospective

- The Docs workflow will stay on the current official Pages action line while
  suppressing the known upstream deploy-step deprecation noise.
- Repo checks will reject accidental removal of the scoped workaround before the
  upstream action is actually clean.

## Context and Orientation

- Docs workflow: `.github/workflows/docs.yml`
- Repo guardrails: `src/deep_gvr/repo_checks.py`
- Related maintenance slices: `plans/74-pages-workflow-warning-cleanup.md`,
  `plans/36-node24-actions.md`

## Plan of Work

1. Add and index this maintenance plan.
2. Record the upstream-state discovery and keep the action version unchanged.
3. Add a narrow deploy-step environment override that suppresses the upstream
   deprecation warning.
4. Update repo checks so the workaround is enforced locally.
5. Run the standard repo validation suite plus the hosted docs build.

## Concrete Steps

1. Add `plans/75-pages-deploy-warning-suppression.md` and index it in
   `plans/README.md`.
2. Update `.github/workflows/docs.yml` so the `Deploy to GitHub Pages` step
   keeps `actions/deploy-pages@v5` but adds a step-local environment override:
   - `NODE_OPTIONS: --no-deprecation`
3. Update `src/deep_gvr/repo_checks.py` so local repo validation enforces both
   the current Pages action line and the deploy-step deprecation workaround.
4. Run:
   - `uv run python scripts/check_repo.py`
   - `uv run python scripts/run_capability_probes.py`
   - `uv run python -m unittest discover -s tests -v`
   - `uv run mkdocs build --strict`
5. Fast-forward merge `codex/pages-deploy-warning-suppression` into `main`,
   rerun the same validation commands on `main`, push, and confirm the remote
   Docs workflow log no longer emits `DEP0040`.

## Validation and Acceptance

Required validation:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
uv run mkdocs build --strict
```

Acceptance evidence:

- `.github/workflows/docs.yml` keeps the current Pages action line and scopes
  `NODE_OPTIONS: --no-deprecation` only to the deploy step.
- `src/deep_gvr/repo_checks.py` enforces the same workaround rule.
- The local validation suite passes on the feature branch and again after the
  local merge into `main`.
- The next Docs workflow run completes without the `DEP0040` `punycode`
  warning in the deploy step log.

## Merge, Push, and Cleanup

- Stage and commit the plan/index update first with
  `plan pages deploy warning suppression`.
- Stage and commit the workflow plus repo-check update with
  `suppress pages deploy deprecation warning`.
- Validate the feature branch before merge.
- Fast-forward merge `codex/pages-deploy-warning-suppression` into `main`
  locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the Docs workflow for the pushed head is green and the deploy-step log
  is clean.
- Delete the local feature branch, and delete the remote feature branch too if
  one was created.

## Idempotence and Recovery

- Re-running this slice should leave the current Pages action line unchanged and
  the deploy-step suppression intact.
- If `actions/deploy-pages` releases a clean version later, a future narrow
  maintenance slice should remove the workaround and revalidate the remote log.

## Interfaces and Dependencies

- Depends on the current official `actions/deploy-pages@v5` release line and
  the still-open upstream warning issue.
- Affects GitHub-hosted docs deployment behavior only; it does not change the
  `deep-gvr` runtime, release bundle, or public docs content.
