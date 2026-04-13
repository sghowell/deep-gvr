# 41 Docs Render Fixes

## Purpose / Big Picture

Fix the public docs rendering regressions introduced by the recent visual upgrade. The user-visible outcome is that the Concepts and Architecture diagrams render correctly on the hosted site, and the landing-page hero graphic keeps all text inside its intended visual bounds.

This slice is corrective only. It should not change the underlying architecture, workflow, or documentation structure.

## Branch Strategy

Start from `main` and implement this slice on `codex/docs-render-fixes`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result again, push `main`, confirm CI, and delete the feature branch when it is no longer needed.

## Commit Plan

- `add docs render fix plan`
- `fix hosted docs asset paths`
- `tighten landing page hero layout`

## Progress

- [x] Reproduce the current hosted-docs rendering failures from generated site output.
- [x] Confirm the Concepts, System Overview, and Architecture pages are using incorrect nested asset paths.
- [x] Fix nested asset paths for the affected public docs pages.
- [x] Tighten the landing-page hero SVG so all text stays inside the intended boxes.
- [x] Run full validation.
- [ ] Merge locally, revalidate on `main`, push, confirm CI, and delete the feature branch.

## Surprises & Discoveries

- The diagrams were present in the built site, but the generated HTML referenced `assets/...` from nested pages, which resolves incorrectly once MkDocs emits per-page subdirectories.
- The same path issue affected `docs/system-overview.md`, even though the user first noticed the Concepts and Architecture pages.
- The landing-page overflow risk is concentrated in the small Tier 2 and Tier 3 summary boxes on the hero SVG, plus one long evidence-summary line.

## Decision Log

- Decision: fix the public docs image references directly in markdown rather than trying to rewrite them at the theme or site level.
- Decision: correct `docs/system-overview.md` in the same slice because it shares the same broken nested-path pattern.
- Decision: keep the hero artwork and visual language, but tighten line breaks and box geometry instead of redrawing the whole figure.

## Outcomes & Retrospective

- Achieved: the Concepts, System Overview, and Architecture pages now emit `../assets/...` paths from nested MkDocs pages, so the generated site resolves the SVGs correctly.
- Achieved: the landing-page hero keeps its existing visual language, but the long evidence-summary and Tier 2 / Tier 3 labels now fit cleanly inside their cards.
- Validation completed successfully with:
  - `uv run mkdocs build --strict`
  - `rg -n '<img src=\"../assets/' site/concepts/index.html site/system-overview/index.html site/deep-gvr-architecture/index.html`
  - `uv run python scripts/check_repo.py`
  - `uv run python scripts/run_capability_probes.py`
  - `uv run python -m unittest discover -s tests -v`

## Context and Orientation

- Public docs pages: `docs/concepts.md`, `docs/system-overview.md`, `docs/deep-gvr-architecture.md`, `docs/index.md`
- Visual assets: `docs/assets/*.svg`
- Hosted docs config: `mkdocs.yml`
- Repo checks: `src/deep_gvr/repo_checks.py`

## Plan of Work

1. Fix the nested image references on the affected docs pages.
2. Adjust the hero SVG text layout and box sizing where overflow is possible.
3. Rebuild the hosted docs and confirm the generated HTML uses the correct asset paths.

## Concrete Steps

1. Update `docs/concepts.md`, `docs/system-overview.md`, and `docs/deep-gvr-architecture.md` to reference `../assets/...` instead of `assets/...`.
2. Rebuild the hosted docs and inspect `site/*/index.html` to confirm the image sources now resolve correctly.
3. Update `docs/assets/deep-gvr-hero.svg`:
   - split the longest summary lines
   - increase box height where needed
   - reduce font size only where necessary
4. Re-run the standard validation and strict MkDocs build.

## Validation and Acceptance

Required validation:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Additional acceptance validation:

```bash
uv run mkdocs build --strict
rg -n '<img src=\"../assets/' site/concepts/index.html site/system-overview/index.html site/deep-gvr-architecture/index.html
```

Acceptance evidence:

- The Concepts page diagram renders on the hosted site.
- The Architecture and Design system-model diagram renders on the hosted site.
- The System Overview verification-tiers diagram also renders correctly.
- The landing-page hero text stays within its boxes.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/docs-render-fixes` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions runs for the pushed head are green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Rebuilding the docs site after these fixes should be deterministic.
- The fix should remain local to the affected docs pages and assets, with no need to regenerate or replace unrelated visuals.

## Interfaces and Dependencies

- Depends on the public docs visual asset work from plan 40.
- Does not change the docs structure, architecture content, or release workflow behavior.
