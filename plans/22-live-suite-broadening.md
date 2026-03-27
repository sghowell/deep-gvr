# 22 Live Suite Broadening

## Purpose / Big Picture

Broaden live benchmark coverage beyond the current representative `live-expansion` subset. The repo now has a stable repeated live gate for three cases, but the full corpus in `eval/known_problems.json` includes additional Tier 1, Tier 2, and Tier 3 scenarios that are not yet grouped into repeatable live subsets. This slice should add named breadth-oriented subsets, exercise them with real live runs, and promote the broader workflow into the operator docs without losing the existing stable representative gate.

## Branch Strategy

Start from `main` and implement this slice on `codex/live-suite-broadening`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result, push `main`, confirm CI, and delete the feature branch.

## Commit Plan

- `add live suite broadening plan`
- `add broader live benchmark subsets`
- `stabilize live breadth subsets`
- `document live suite broadening workflow`

## Progress

- [x] Add the new plan and index it from `plans/README.md`.
- [x] Define broader named live subsets that cover the remaining benchmark categories outside the current representative `live-expansion` gate.
- [x] Add or update tests so subset selection and repeated reporting continue to work with the broader live coverage.
- [x] Run live checks across the new breadth-oriented subsets and record any new failures or stability gaps here.
- [x] Update repo docs to show which subset is the representative stable gate and which subsets are for broader live coverage.

## Surprises & Discoveries

- The first broad Tier 1 sweep at `/tmp/deep-gvr-live-analytical-breadth/report.json` showed that simply broadening coverage immediately surfaces tier-discipline and content-scoping failures that the smaller `live-expansion` gate does not catch.
- `known-correct-surface-threshold` over-escalated to Tier 2 when the generator turned a literature-grounded threshold explanation into a simulator-ready ordering claim.
- `known-correct-union-find` failed because the generator answered a scaling question with extra threshold comparisons and an incorrect worst-case per-operation claim; tightening prompt/domain scope fixed that case.
- The first escalation sweep at `/tmp/deep-gvr-live-escalation-breadth/report.json` revealed two benchmark-scoring gaps: simulation-backed direct refutations should count as accepted passes, and theorem-style cases with failed Tier 3 proof transport should not remain `VERIFIED`.
- `formal-unavailable-repetition-scaling` is environment-sensitive now that Aristotle transport is configured. The live benchmark still needs to admit failure when proof transport returns `error`, but it should no longer assume that Tier 3 is structurally unavailable on this machine.

## Decision Log

- Keep `live-expansion` as the small representative stability gate unless live breadth data proves it is no longer representative.
- Prefer named subsets over new CLI flags so the breadth workflow stays inspectable through `--list-subsets` and existing tests.
- Split broader live coverage by verification shape when practical so Tier 1-only, Tier 2, and Tier 3 behavior can be exercised intentionally instead of through one monolithic run.

## Outcomes & Retrospective

- Added three broader named subsets in `src/deep_gvr/evaluation.py`: `live-analytical-breadth`, `live-escalation-breadth`, and `live-full`.
- `uv run python eval/run_eval.py --list-subsets` now exposes those coverage sweeps, and `tests/test_evaluation.py` covers their selection and CLI discovery.
- Broader live coverage is now a first-class operator workflow, but it is not yet the stable repeated gate. `live-expansion` remains the representative repeated stability subset.
- Analytical breadth is still noisy. The reruns at `/tmp/deep-gvr-live-analytical-breadth-final/report.json` and `/tmp/deep-gvr-live-analytical-breadth-final-2/report.json` narrowed the remaining problems to intermittent threshold over-escalation and a live verifier timeout on `known-correct-planar-qubits`.
- Escalation breadth is materially better after this slice. The original broad sweep at `/tmp/deep-gvr-live-escalation-breadth/report.json` exposed the scoring/formal-policy issues, and the targeted rerun at `/tmp/deep-gvr-live-escalation-breadth-failures-final/report.json` finished `2/2` passed for the previously failing cases.

## Context and Orientation

- Current stable representative gate: `plans/21-live-suite-hardening.md`
- Benchmark corpus: `eval/known_problems.json`
- Subset selection and repeated reporting: `src/deep_gvr/evaluation.py`, `eval/run_eval.py`
- Current subset tests: `tests/test_evaluation.py`
- Current operator docs: `README.md`, `eval/README.md`, `SKILL.md`, `docs/system-overview.md`

## Plan of Work

1. Add and index the new execution plan.
2. Extend the named benchmark subset map so the remaining Tier 1, Tier 2, and Tier 3 cases can be exercised through stable, documented live commands.
3. Update tests around subset enumeration, deterministic selection, and repeated reporting so the new subsets stay under coverage.
4. Run live breadth checks on the newly added subsets and harden prompts/scoring/runtime only if those runs expose real regressions.
5. Update docs so operators know which subset is the fast representative gate and which subsets cover broader live behavior.

## Concrete Steps

1. Add `plans/22-live-suite-broadening.md` and update `plans/README.md`.
2. Update `src/deep_gvr/evaluation.py` to add the new named subset definitions.
3. Update `tests/test_evaluation.py` for subset discovery, selection, and any repeated-report expectations that depend on subset size.
4. If live breadth runs expose real failures, update the minimum necessary prompt/runtime/scoring surface and the matching tests.
5. Update `README.md`, `eval/README.md`, `SKILL.md`, and `docs/system-overview.md` with the new subset workflow and the current recommended gates.
6. Run targeted tests such as:

```bash
uv run python -m unittest tests.test_evaluation -v
```

7. Run broader live checks such as:

```bash
uv run python eval/run_eval.py --list-subsets
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --subset live-analytical-breadth --prompt-profile compact --output-root /tmp/deep-gvr-live-analytical-breadth
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --subset live-escalation-breadth --prompt-profile compact --command-timeout-seconds 120 --output-root /tmp/deep-gvr-live-escalation-breadth
```

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Targeted validation during implementation:

```bash
uv run python -m unittest tests.test_evaluation -v
uv run python eval/run_eval.py --list-subsets
```

Acceptance evidence:

- `--list-subsets` exposes the new breadth-oriented subset names.
- The new subsets select the expected case IDs under test coverage.
- At least one live run exercises the broader Tier 1-only coverage and one live run exercises the broader escalation coverage.
- Any new live failures found during breadth runs are either fixed in this slice or recorded explicitly in this plan with artifact paths.
- Final artifact record:
  - Analytical breadth sweep: `/tmp/deep-gvr-live-analytical-breadth/report.json`
  - Analytical reruns after prompt hardening: `/tmp/deep-gvr-live-analytical-breadth-final/report.json`, `/tmp/deep-gvr-live-analytical-breadth-final-2/report.json`
  - Escalation breadth sweep: `/tmp/deep-gvr-live-escalation-breadth/report.json`
  - Targeted escalation rerun after scoring/formal-policy fixes: `/tmp/deep-gvr-live-escalation-breadth-failures-final/report.json`

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/live-suite-broadening` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- New subset definitions should be additive and should not change the semantics of existing case IDs or the existing `live-expansion` gate.
- If a broader live subset fails, keep the artifact roots and narrow the failure to the smallest realistic prompt/runtime/scoring change instead of weakening benchmark expectations.
- If a full breadth sweep proves too slow for repeated runs, keep the representative gate small and document the broader subsets as coverage sweeps rather than forcing them into the fast stability path.

## Interfaces and Dependencies

- `eval/run_eval.py` remains the operator-facing entrypoint for subset selection and repeated runs.
- `src/deep_gvr/evaluation.py` owns the named subset map and repeated report generation.
- `tests/test_evaluation.py` owns the main contract coverage for subset discovery and repeated reporting behavior.
- `eval/known_problems.json` remains the source corpus; this plan changes how it is grouped and exercised, not the case IDs themselves.
