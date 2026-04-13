# 43 Diagram Heading Containment

## Purpose / Big Picture

Fix the last remaining text-overflow regressions in the public Concepts and System Model diagrams. The specific goal is to keep the heading and subtitle blocks inside the figure frame and the orchestrator-panel title inside its dark container.

This slice is corrective only. It must not alter the material structure or meaning of the diagrams.

## Branch Strategy

Start from `main` and implement this slice on `codex/system-model-concepts-overflow-fixes`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result again, push `main`, confirm CI, and delete the feature branch when it is no longer needed.

## Commit Plan

- `add diagram heading containment plan`
- `tighten concepts and system model headings`

## Progress

- [x] Generate rendered previews for the Concepts and System Model figures.
- [x] Identify the remaining overflow points in the heading areas.
- [x] Tighten the heading and subtitle layout in both figures.
- [x] Rebuild the hosted docs and inspect the rendered previews again.
- [x] Run full validation.
- [ ] Merge locally, revalidate on `main`, push, confirm CI, and delete the feature branch.

## Surprises & Discoveries

- The prior typography pass fixed card containment but did not address the figure-level title and subtitle lines, which still overrun the canvas in some renderers.
- The System Model overflow is concentrated in the dark orchestrator panel title, not the smaller downstream cards.

## Decision Log

- Decision: use rendered PNG previews as the acceptance method for this slice instead of inferring containment from SVG source alone.
- Decision: fix only the heading and subtitle blocks that still overflow; do not rework the rest of the diagram geometry again.

## Outcomes & Retrospective

- Achieved: the Concepts figure heading and subtitle are now wrapped and resized to stay inside the figure frame.
- Achieved: the System Model figure subtitle is wrapped inside the frame, and the orchestrator title is split across two lines inside its dark panel.
- Achieved: Quick Look PNG previews now show the previously clipped text fully contained in both figures.
- Validation completed successfully with:
  - `uv run mkdocs build --strict`
  - `uv run python scripts/check_repo.py`
  - `uv run python scripts/run_capability_probes.py`
  - `uv run python -m unittest discover -s tests -v`

## Context and Orientation

- Public figures:
  - `docs/assets/gvr-loop.svg`
  - `docs/assets/system-model.svg`
- Render-preview tooling used for acceptance:
  - `qlmanage -t -s 1800 -o /tmp ...`
- Public docs pages that embed these figures:
  - `docs/concepts.md`
  - `docs/deep-gvr-architecture.md`

## Plan of Work

1. Fix the remaining figure-level heading overflow in the two affected public SVGs.
2. Regenerate rendered previews and confirm containment visually.
3. Run the standard validation set and close the slice.

## Concrete Steps

1. Adjust `gvr-loop.svg`:
   - split the title into two lines
   - split the subtitle into two lines
   - reduce heading block font sizes slightly
2. Adjust `system-model.svg`:
   - split the top subtitle into two lines
   - widen the orchestrator panel
   - split the orchestrator title into two lines
   - move the CTA pills and connectors as needed
3. Re-render the two figures with Quick Look and verify containment.
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

- The Concepts figure title and subtitle stay inside the frame.
- The System Model figure top subtitle stays inside the frame.
- The System Model orchestrator title stays inside the dark panel.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/system-model-concepts-overflow-fixes` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions runs for the pushed head are green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Re-rendering the same SVGs should be deterministic.
- The fixes remain local to the two affected figure assets and plan tracking.

## Interfaces and Dependencies

- Depends on the earlier public-figure work in plans 40 through 42.
- Does not change the public docs structure or the diagrams’ conceptual content.
