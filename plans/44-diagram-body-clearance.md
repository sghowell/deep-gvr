# 44 Diagram Body Clearance

## Purpose / Big Picture

Fix the last remaining layout collisions in the public GVR Loop and System Model figures. The specific goal is to keep diagram bodies from encroaching on the heading blocks and to finish the text containment cleanup inside the Evidence Ledger card.

This slice is corrective only. It must not alter the diagrams' meaning, flow, or architecture.

## Branch Strategy

Start from `main` and implement this slice on `codex/diagram-heading-clearance-fixes`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result again, push `main`, confirm CI, and delete the feature branch when it is no longer needed.

## Commit Plan

- `add diagram body clearance plan`
- `clear public diagram heading collisions`

## Progress

- [x] Re-render the two affected figures from the current SVG sources.
- [x] Confirm that the remaining issue is body geometry crowding the heading areas.
- [x] Move the figure bodies down to create real heading clearance.
- [x] Loosen the Evidence Ledger inner-card typography and widths.
- [x] Run full validation.
- [ ] Merge locally, revalidate on `main`, push, confirm CI, and delete the feature branch.

## Surprises & Discoveries

- The remaining problem was not heading font size anymore; it was the main diagram bodies beginning too high and visually colliding with the title/subtitle blocks.
- The Evidence Ledger needed a small card-width increase in addition to reduced type size to make the inner labels reliably fit.

## Decision Log

- Decision: keep the fix geometric instead of continuing to shrink heading typography.
- Decision: use translated diagram-body groups so the structural relationships inside each figure remain unchanged.

## Outcomes & Retrospective

- Achieved: the GVR Loop figure body is now translated down far enough that the heading block reads cleanly without card collisions.
- Achieved: the System Model figure body is translated down far enough that the subtitle block is no longer obscured by the orchestrator panel.
- Achieved: the Evidence Ledger inner cards and labels were loosened enough to keep the text contained.
- Validation completed successfully with:
  - `uv run python scripts/check_repo.py`
  - `uv run python scripts/run_capability_probes.py`
  - `uv run python -m unittest discover -s tests -v`
  - `uv run mkdocs build --strict`

## Context and Orientation

- Public figures:
  - `docs/assets/gvr-loop.svg`
  - `docs/assets/system-model.svg`
- Render-preview tooling used for acceptance:
  - `qlmanage -t -s 2000 -o /tmp ...`
- Public docs pages that embed these figures:
  - `docs/concepts.md`
  - `docs/system-overview.md`
  - `docs/deep-gvr-architecture.md`

## Plan of Work

1. Push the GVR Loop and System Model bodies down far enough to clear the heading blocks.
2. Finish the remaining Evidence Ledger containment cleanup.
3. Re-render the figures and confirm the visible collisions are gone.
4. Run the standard validation set and close the slice.

## Concrete Steps

1. Update `gvr-loop.svg`:
   - translate the main diagram body downward without changing node order or routing semantics
2. Update `system-model.svg`:
   - translate the main diagram body downward
   - reduce Evidence Ledger typography slightly
   - widen the Evidence Ledger inner cards slightly
3. Re-render both figures with Quick Look and inspect the results.
4. Re-run repo validation.

## Validation and Acceptance

Required validation:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
uv run mkdocs build --strict
```

Acceptance evidence:

- The GVR Loop figure body no longer overlaps or crowds the heading block.
- The System Model figure body no longer obscures the heading block.
- Evidence Ledger labels stay inside their cards.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/diagram-heading-clearance-fixes` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions runs for the pushed head are green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Re-rendering the same SVGs should be deterministic.
- The fixes remain local to the two affected figure assets and plan tracking.

## Interfaces and Dependencies

- Depends on the earlier public-figure work in plans 40 through 43.
- Does not change the public docs structure or the diagrams' conceptual content.
