# 77 Hosted Docs Nav Polish

## Purpose / Big Picture

Retire the remaining hosted-docs nav drift now that the release and clean-room
install surfaces are in place. The user-visible outcome is that
`plugin-privacy.md` and `plugin-terms.md` become intentional parts of the
hosted docs instead of pages that exist on disk but only show up as MkDocs nav
warnings.

## Branch Strategy

Start from `main` and implement this slice on
`codex/hosted-docs-nav-polish`. Merge back into `main` locally with a
fast-forward only after branch validation passes, then validate the merged
result again, push `main`, confirm the CI and Docs workflows are green, and
delete the feature branch.

## Commit Plan

- `plan hosted docs nav polish`
- `polish hosted docs nav`

## Progress

- [x] Add this plan and index it from `plans/README.md`.
- [x] Inspect the current hosted-docs nav surface and confirm which pages are
      still outside nav.
- [ ] Update the hosted-docs nav so the plugin privacy and terms pages are
      intentionally included.
- [ ] Add a repo check so future hosted-docs pages cannot drift out of nav
      silently.
- [ ] Run the required repo validation commands and a strict docs build.
- [ ] Merge locally, revalidate on `main`, push, confirm remote CI and Docs,
      and delete the feature branch.

## Surprises & Discoveries

- The remaining MkDocs nav warning is not about missing content; both
  `docs/plugin-privacy.md` and `docs/plugin-terms.md` already exist and are
  required release-surface assets.
- The current `mkdocs.yml` nav lists the main Codex pages and the technical
  reference, but it does not include the two plugin policy pages anywhere.
- `src/deep_gvr/repo_checks.py` validates release-surface existence for those
  plugin pages, but it does not currently enforce hosted-docs nav coverage, so
  future public pages could drift out of nav without failing local repo checks.

## Decision Log

- Keep this as a narrow hosted-docs polish slice rather than broadening into
  public-docs information architecture work.
- Make the hosted nav intentional by grouping the plugin overview plus policy
  pages under the same Codex plugin nav section.
- Encode a stable repo rule: every hosted docs Markdown page that is not in
  `exclude_docs` must appear in `mkdocs.yml` nav.

## Outcomes & Retrospective

- The hosted docs will stop emitting the nav warning for plugin privacy and
  terms pages.
- The plugin page itself will point readers at the associated privacy and terms
  pages.
- Repo checks will catch future hosted-docs nav drift before CI or docs deploy
  time.

## Context and Orientation

- Hosted docs config: `mkdocs.yml`
- Plugin docs pages: `docs/codex-plugin.md`, `docs/plugin-privacy.md`,
  `docs/plugin-terms.md`
- Repo guardrails: `src/deep_gvr/repo_checks.py`
- Existing repo-check tests: `tests/test_repo_checks.py`

## Plan of Work

1. Add and index this plan.
2. Update `mkdocs.yml` so the plugin overview and plugin policy pages are part
   of the hosted docs nav.
3. Link the policy pages directly from `docs/codex-plugin.md`.
4. Extend repo checks to ensure non-excluded hosted docs pages are included in
   nav and add focused tests for that behavior.
5. Run the standard repo validation suite plus a strict hosted-docs build.

## Concrete Steps

1. Add `plans/77-hosted-docs-nav-polish.md` and index it in `plans/README.md`.
2. Update `mkdocs.yml` so `codex-plugin.md`, `plugin-privacy.md`, and
   `plugin-terms.md` sit under one intentional `Codex Plugin` nav section.
3. Update `docs/codex-plugin.md` with direct links to:
   - `plugin-privacy.md`
   - `plugin-terms.md`
4. Extend `src/deep_gvr/repo_checks.py` with a hosted-docs nav coverage check
   that:
   - loads `mkdocs.yml`
   - respects `docs_dir` and `exclude_docs`
   - fails if any non-excluded Markdown page under the hosted docs tree is not
     present in nav
5. Add focused coverage in `tests/test_repo_checks.py` for the new hosted-docs
   nav rule.
6. Run:
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

- `mkdocs.yml` includes `plugin-privacy.md` and `plugin-terms.md` in the
  hosted docs nav instead of leaving them as out-of-nav pages.
- `docs/codex-plugin.md` links readers directly to the plugin privacy and
  terms pages.
- `src/deep_gvr/repo_checks.py` enforces hosted-docs nav coverage and the new
  rule is covered by tests.
- `uv run mkdocs build --strict` completes without the prior nav warning about
  plugin privacy and terms pages existing outside nav.

## Merge, Push, and Cleanup

- Stage and commit the plan/index update first with
  `plan hosted docs nav polish`.
- Stage and commit the docs/nav/check changes with
  `polish hosted docs nav`.
- Validate the feature branch before merge.
- Fast-forward merge `codex/hosted-docs-nav-polish` into `main` locally only
  after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the remote CI and Docs workflows are green.
- Delete the local feature branch, and delete the remote feature branch too if
  one was created.

## Idempotence and Recovery

- Re-running this slice should leave the same hosted-docs pages covered by nav
  and the same repo rule enforced.
- If more hosted docs pages are added later, contributors will need to either
  add them to nav or explicitly move them into `exclude_docs`.
- If the hosted docs structure changes later, the new repo check can be updated
  in the same narrow maintenance pattern without touching runtime code.

## Interfaces and Dependencies

- Depends on `mkdocs.yml` remaining the source of truth for the hosted docs
  surface.
- Affects only hosted docs organization, plugin policy discoverability, and
  repo-local docs guardrails.
- Does not change the runtime, release bundle, operator preflight, or backend
  behavior.
