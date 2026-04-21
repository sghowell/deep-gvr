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

- [x] Design the evaluation protocol.
- [x] Add controlled before/after evaluation helpers.
- [x] Run repeated benchmark comparisons with and without `auto_improve`.
- [x] Update the release policy based on evidence.
- [x] Run full validation.
- [x] Merge locally, revalidate on `main`, push, confirm CI, and delete the feature branch.

## Surprises & Discoveries

- `auto_improve` is currently a release-surface policy field, not a repo-local runtime input. The evaluation harness therefore measures policy toggles against isolated benchmark and release-policy comparisons instead of pretending the typed runtime consumes the flag directly.
- A deterministic repeated comparison is enough to prove the repo-local point today: toggling the policy variant produced no benchmark drift, but the experimental `auto_improve: true` variant still fails the documented public-release default.
- Actual evaluation evidence was written to `/tmp/deep-gvr-auto-improve/report.json`: deterministic `analysis-full` repeated 3 times yielded `48/48` passed case-runs with zero differing case outcomes between the baseline and experimental policy variants; live evaluation was intentionally skipped in this slice.

## Decision Log

- Decision: keep `auto_improve: false` as the shipped default until this slice is complete.
- Decision: keep `auto_improve: false` as the shipped default after this slice as well; the new evidence does not justify enabling it by default.
- Decision: require `scripts/evaluate_auto_improve.py` as the explicit opt-in gate before anyone edits `release/agentskills.publication.json`.

## Outcomes & Retrospective

- Added `src/deep_gvr/auto_improve.py` and `scripts/evaluate_auto_improve.py` as the repeatable evaluation path for the release policy.
- Added `schemas/auto_improve_evaluation.schema.json` and `templates/auto_improve_evaluation.template.json` so the new artifact is contract-backed.
- Recorded the current recommendation in the release surface and docs: keep `auto_improve` disabled by default until future evidence shows a real operator benefit without drift.
- The implemented evaluator now makes the current limitation explicit: the repo can prove policy isolation and benchmark stability, but a future slice would still need real live operator evidence before the public default changes.

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

Implementation result:

1. Added a dedicated evaluator that:
   - compares baseline vs experimental `auto_improve` policy variants
   - writes an `AutoImproveEvaluationReport`
   - checks manifest/worktree isolation before and after the run
2. Ran the deterministic comparison path and recorded the result:
   - no repo-local benchmark drift was observed
   - the experimental policy variant remains release-blocked by design
3. Kept the checked-in release policy disabled by default and updated the release docs to require the evaluator before any opt-in edit.

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
