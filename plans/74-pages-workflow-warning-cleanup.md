# 74 Pages Workflow Warning Cleanup

## Purpose / Big Picture

Retire the remaining GitHub Pages workflow runtime deprecation warning now that
the first public release is cut. The user-visible outcome is that the hosted
docs workflow stays functionally identical but moves to the current GitHub
Pages action line, and the repo guardrails encode that version floor so the
warning does not regress later.

## Branch Strategy

Start from `main` and implement this slice on
`codex/pages-workflow-warning-cleanup`. Merge back into `main` locally with a
fast-forward only after branch validation passes, then validate the merged
result again, push `main`, confirm the docs workflow is green, and delete the
feature branch.

## Commit Plan

- `plan pages workflow warning cleanup`
- `upgrade docs pages actions`

## Progress

- [x] Add this plan and index it from `plans/README.md`.
- [x] Confirm the current official GitHub Pages action versions to use.
- [x] Update `.github/workflows/docs.yml` to the current Pages action line.
- [x] Update repo checks so the new Pages action versions are enforced.
- [ ] Run the required repo validation commands and a strict hosted-docs build.
- [ ] Merge locally, revalidate on `main`, push, confirm the docs workflow, and
      delete the feature branch.

## Surprises & Discoveries

- The repo already cleaned up the Node 20 warning for the CI workflow in plan
  36; the remaining warning is isolated to the docs/pages workflow.
- `src/deep_gvr/repo_checks.py` currently enforces the older Pages artifact and
  deploy action lines, so the workflow update and the guardrail must land
  together.
- Official GitHub Marketplace listings now show the current supported Pages
  line as `actions/configure-pages@v6`,
  `actions/upload-pages-artifact@v5`, and `actions/deploy-pages@v5`.

## Decision Log

- Keep this as a narrow maintenance slice rather than mixing it with broader
  post-release or backend work.
- Encode the supported Pages action versions in repo checks so future action
  drift becomes a local validation failure instead of a review-only detail.
- Preserve the existing docs workflow structure and permissions unless the new
  Pages action line forces a functional change during validation.

## Outcomes & Retrospective

- The hosted docs workflow will use the current Pages action line instead of
  the older warning-producing versions.
- Repo checks will reject accidental downgrades of the Pages workflow surface.

## Context and Orientation

- Docs workflow: `.github/workflows/docs.yml`
- Repo guardrails: `src/deep_gvr/repo_checks.py`
- Related maintenance precedent: `plans/36-node24-actions.md`

## Plan of Work

1. Add and index this maintenance plan.
2. Confirm the current official GitHub Pages action versions from official
   GitHub sources.
3. Update the docs workflow to the current Pages action versions.
4. Update repo checks so the Pages version floor is encoded locally.
5. Run the standard repo validation suite plus the hosted docs build.

## Concrete Steps

1. Add `plans/74-pages-workflow-warning-cleanup.md` and index it in
   `plans/README.md`.
2. Update `.github/workflows/docs.yml` to use the current official Pages action
   line:
   - `actions/configure-pages@v6`
   - `actions/upload-pages-artifact@v5`
   - `actions/deploy-pages@v5`
3. Update `src/deep_gvr/repo_checks.py` so local repo validation enforces those
   workflow entries instead of the old v5/v4/v4 Pages line.
4. Run:
   - `uv run python scripts/check_repo.py`
   - `uv run python scripts/run_capability_probes.py`
   - `uv run python -m unittest discover -s tests -v`
   - `uv run mkdocs build --strict`
5. Fast-forward merge `codex/pages-workflow-warning-cleanup` into `main`,
   rerun the same validation commands on `main`, push, and confirm the Docs
   workflow is green without the old runtime deprecation warning.

## Validation and Acceptance

Required validation:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
uv run mkdocs build --strict
```

Acceptance evidence:

- `.github/workflows/docs.yml` uses the current Pages action line.
- `src/deep_gvr/repo_checks.py` enforces the same workflow version floor.
- The local validation suite passes on the feature branch and again after the
  local merge into `main`.
- The next Docs workflow run completes cleanly without the prior GitHub Pages
  runtime deprecation warning.

## Merge, Push, and Cleanup

- Stage and commit the plan/index update first with
  `plan pages workflow warning cleanup`.
- Stage and commit the workflow plus repo-check update with
  `upgrade docs pages actions`.
- Validate the feature branch before merge.
- Fast-forward merge `codex/pages-workflow-warning-cleanup` into `main` locally
  only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the Docs workflow for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if
  one was created.

## Idempotence and Recovery

- Re-running this slice should leave the docs workflow pinned to the same
  supported Pages action versions.
- If a newer official Pages action line is released later, a future narrow
  maintenance slice can repeat the same update pattern without changing the
  repo's Python or runtime surface.

## Interfaces and Dependencies

- Depends on the official `actions/configure-pages`,
  `actions/upload-pages-artifact`, and `actions/deploy-pages` release lines.
- Affects GitHub-hosted docs deployment behavior only; it does not change the
  `deep-gvr` runtime, release bundle, or public docs content.
