# 42 Figure Typography Containment

## Purpose / Big Picture

Fix the remaining public-docs figure regressions after the render-path repair. The user-visible goal is simple: every public SVG figure should keep its text comfortably inside the cards, pills, and panels that visually contain it.

This slice is visual correction only. It must not change the underlying architecture, workflows, or conceptual structure of the diagrams.

## Branch Strategy

Start from `main` and implement this slice on `codex/figure-typography-containment`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result again, push `main`, confirm CI, and delete the feature branch when it is no longer needed.

## Commit Plan

- `add figure typography containment plan`
- `tighten public docs figure typography`

## Progress

- [x] Inspect the public SVG figures and identify the text-overflow hotspots.
- [x] Tighten box geometry, line breaks, and font sizing for all affected public figures.
- [x] Rebuild the hosted docs and confirm the figures render without text overflow.
- [x] Run full validation.
- [ ] Merge locally, revalidate on `main`, push, confirm CI, and delete the feature branch.

## Surprises & Discoveries

- The previous slice fixed asset-path rendering, but the typography still depended too heavily on browser font metrics.
- The issue is broader than the three initially reported figures: `verification-tiers.svg` also uses body lines that are too long for reliable containment.
- The safest fix is a consistent typography pass across the public SVG set, not isolated one-off text nudges.

## Decision Log

- Decision: fix containment in the SVG sources themselves rather than relying on browser-specific text rendering behavior.
- Decision: keep all diagram structure and semantic content intact; only card sizes, line breaks, and font sizes may change.
- Decision: include `verification-tiers.svg` in the containment pass because it shares the same failure mode.

## Outcomes & Retrospective

- Achieved: the public SVG figures now use safer line breaks, slightly reduced body sizes, and larger card geometry where needed, so text no longer depends on optimistic browser font metrics.
- Achieved: `deep-gvr-hero.svg`, `gvr-loop.svg`, `system-model.svg`, and `verification-tiers.svg` all received the containment pass without changing their conceptual structure.
- Validation completed successfully with:
  - `uv run mkdocs build --strict`
  - `uv run python scripts/check_repo.py`
  - `uv run python scripts/run_capability_probes.py`
  - `uv run python -m unittest discover -s tests -v`

## Context and Orientation

- Public SVG figures:
  - `docs/assets/deep-gvr-hero.svg`
  - `docs/assets/gvr-loop.svg`
  - `docs/assets/system-model.svg`
  - `docs/assets/verification-tiers.svg`
- Hosted docs config: `mkdocs.yml`
- Public docs pages that embed these figures:
  - `docs/index.md`
  - `docs/concepts.md`
  - `docs/system-overview.md`
  - `docs/deep-gvr-architecture.md`

## Plan of Work

1. Tighten the public SVG typography and card geometry.
2. Rebuild the hosted docs and confirm the generated pages still render the updated assets.
3. Run the standard validation set.

## Concrete Steps

1. Update the affected SVGs to add safer internal margins:
   - split long body lines
   - reduce font sizes where needed
   - increase card heights or widths where needed
   - adjust connector positions only when box geometry changes require it
2. Rebuild the hosted docs and inspect the generated pages.
3. Re-run the standard repo validation.

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
```

Acceptance evidence:

- The GVR loop figure keeps all card text inside its cards and pills.
- The System model figure keeps all panel and card text inside its shapes.
- The landing-page hero keeps all card text inside its cards.
- The verification tiers figure keeps all tier descriptions inside their cards.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/figure-typography-containment` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions runs for the pushed head are green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Rebuilding the docs site after these fixes should be deterministic.
- The changes should stay local to the SVG assets and plan tracking.

## Interfaces and Dependencies

- Depends on the public docs visual work from plan 40 and the asset-path repair from plan 41.
- Does not change the architecture, docs structure, or release workflow behavior.
