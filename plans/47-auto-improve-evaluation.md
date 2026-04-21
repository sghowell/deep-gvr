# 47 Auto Improve Evaluation

## Purpose / Big Picture

Evaluate whether `auto_improve` should remain off by default or become an opt-in supported mode for `deep-gvr`. The goal is to measure the actual effect on reproducibility, benchmark stability, operator safety, and rollback rather than treating automatic self-modification as a purely philosophical toggle.

This slice is intentionally evaluative first. It should not enable `auto_improve` by default unless repeated evidence shows that the behavior is stable, explainable, and reversible.

## Branch Strategy

Start from `main` and implement this slice on `codex/auto-improve-evaluation` when it is selected. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result again, push `main`, confirm CI, and delete the feature branch when it is no longer needed.

## Commit Plan

- `add auto improve evaluation harness`
- `record auto improve evidence and policy`
- `document auto improve recommendation`

## Progress

- [ ] Design the evaluation protocol.
- [ ] Add controlled before/after evaluation helpers.
- [ ] Run repeated benchmark comparisons with and without `auto_improve`.
- [ ] Update the release policy based on evidence.
- [ ] Run full validation.
- [ ] Merge locally, revalidate on `main`, push, confirm CI, and delete the feature branch.

## Surprises & Discoveries

- Pending implementation.

## Decision Log

- Decision: keep `auto_improve: false` as the shipped default until this slice is complete.

## Outcomes & Retrospective

- Pending implementation.

## Context and Orientation

- Release policy surface: `release/agentskills.publication.json`, `docs/release-workflow.md`
- Existing release checks: `src/deep_gvr/release_surface.py`, `scripts/release_preflight.py`
- Existing benchmark harness: `eval/run_eval.py`, `src/deep_gvr/evaluation.py`

## Plan of Work

1. Define how `auto_improve` will be evaluated safely.
2. Run repeated comparisons against the existing deterministic and live evaluation surfaces.
3. Update release policy only if the evidence supports it.

## Concrete Steps

1. Add an evaluation harness that can compare baseline and `auto_improve` runs without contaminating the main operator state.
2. Measure:
   - deterministic benchmark drift
   - live benchmark stability
   - artifact integrity
   - rollback and recovery behavior
3. Record the findings in repo-local docs and update the release policy accordingly.

## Validation and Acceptance

Required validation:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Acceptance evidence:

- The repo has a repeatable evaluation method for `auto_improve`.
- The release default is justified by measured evidence rather than assumption.
- Any policy change is documented in the release surface and public docs.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/auto-improve-evaluation` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions runs for the pushed head are green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Evaluation runs must isolate mutable state so repeated comparisons remain interpretable.
- If `auto_improve` causes drift or instability, keep the release default disabled and record the failure mode explicitly.

## Interfaces and Dependencies

- Depends on the release-surface policy in `release/agentskills.publication.json`.
- Depends on the benchmark harness and evidence system to measure drift.
- Should use existing backup/import or equivalent operator-isolation paths when available.
