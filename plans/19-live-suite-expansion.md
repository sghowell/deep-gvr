# 19 Live Suite Expansion

## Purpose / Big Picture

Turn the current one-case live benchmark proof into a repeatable multi-case operator workflow. The repo now has a passing live run for `known-correct-surface-threshold`, but the benchmark corpus in `eval/known_problems.json` spans known-correct, known-incorrect, simulation-required, and formalizable cases. This slice should add a small reusable live-suite selection and reporting surface so operators can run representative multi-case live subsets without hand-picking case IDs each time, record artifact roots and mismatches case by case, and use the resulting live artifacts to decide where prompt or runtime tuning is still needed.

## Branch Strategy

Start from `main` and implement this slice on `codex/live-suite-expansion`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result, push `main`, confirm CI, and delete the feature branch.

## Commit Plan

- `add live suite expansion plan`
- `add live subset selection workflow`
- `tighten live tier request contracts`
- `document live suite expansion workflow`

## Progress

- [x] Add the new plan and index it from `plans/README.md`.
- [x] Add reusable benchmark-subset selection for representative live multi-case runs.
- [x] Add richer per-case report output that records mismatches and artifact roots in a repeatable operator-facing form.
- [x] Extend tests for subset selection and summary formatting.
- [x] Run targeted tests, repo-wide validation, and a real live subset across the remaining benchmark categories.

## Surprises & Discoveries

- The current `eval/run_eval.py` already supports repeated `--case-id`, but it has no repo-local notion of a representative live subset, so every multi-case run is still an ad hoc shell command.
- The JSON report already contains enough information to diagnose live runs, but the CLI summary is too terse for practical multi-case sweeps because it does not print per-case status, mismatch notes, or case artifact roots.
- The current benchmark corpus already contains suitable representative cases for the remaining live categories, so this slice can stay focused on workflow and reporting instead of inventing a new suite.
- The live simulation path exposed a real packaging bug first: `src/deep_gvr/tier1.py` assumed the repo root was always on `sys.path` when importing `adapters.stim_adapter`.
- Once the adapter import was fixed, live Tier 2 exposed two stable verifier behaviors that were better handled in code than prompt folklore: common Stim noise-model aliases such as `uniform_depolarizing`, and impractical live simulation budgets such as `shots_per_point=10000000`.
- The second verifier pass after Tier 2 evidence routinely needed more wall-clock budget than the initial audit, so the verifier timeout policy had to become evidence-aware instead of role-only.
- Known-incorrect live cases can surface as honest generator refutations instead of `FLAWS_FOUND` verdicts. Treating those verified refutations as benchmark success is more faithful than forcing the generator to role-play a false claim.
- Even after the harness fixes, the full live subset still shows some model variance: the `simulation-verified-distance5` case has a clean single-case Tier 2 pass, but the final three-case sweep still produced one run where the verifier accepted the claim at Tier 1 instead of requesting Tier 2.

## Decision Log

- Keep the existing benchmark JSON file as the source of truth; add reusable subset selection in code instead of creating a second benchmark manifest.
- Use a named live subset for representative coverage across the remaining categories instead of requiring operators to remember a long `--case-id` list.
- Improve the eval CLI output rather than adding another standalone wrapper script.
- Keep deterministic and live mode on the same selection/reporting surface so tests can cover the new workflow without relying on real Hermes calls.
- Normalize common Tier 2 verifier aliases and clamp live simulation requests in code so the harness does not depend on prompt-perfect `simulation_spec` payloads.
- Give evidence-bearing verifier rechecks a larger live timeout floor instead of inflating every live role call.
- Accept a verified direct refutation as success for known-incorrect live benchmark cases.

## Outcomes & Retrospective

- The repo now has a named live subset workflow (`live-expansion`) plus richer CLI case summaries with mismatch notes and case artifact roots.
- The live Tier 2 path is materially more robust than it was at the start of the slice: the runner now survives reduced `sys.path` entrypoints, normalizes common noise-model aliases, clamps live simulation budgets, and avoids reporting the test physical error rate as a false threshold estimate.
- The strongest single-case live evidence roots for the remaining categories are:
  - `/tmp/deep-gvr-live-suite-expansion-known-incorrect-final/report.json`
  - `/tmp/deep-gvr-live-suite-expansion-sim-final-6/report.json`
  - `/tmp/deep-gvr-live-suite-expansion-formal-final-3/report.json`
- The final representative three-case live subset run is `/tmp/deep-gvr-live-suite-expansion-final-2/report.json`. It records:
  - `known-incorrect-surface-threshold-5pct` as a pass via verified direct refutation at Tier 1
  - `formal-proved-repetition-majority` as a pass at Tiers 1 and 3
  - `simulation-verified-distance5` as the remaining mismatch in that sweep because the verifier accepted the claim at Tier 1 instead of requesting Tier 2
- That residual mismatch is now clearly documented as live model variance rather than missing harness infrastructure. The workflow, artifacts, and single-case Tier 2/Tier 3 passes are in place.

## Context and Orientation

- Benchmark corpus: `eval/known_problems.json`
- Eval CLI: `eval/run_eval.py`
- Benchmark selection and execution: `src/deep_gvr/evaluation.py`
- Current eval tests: `tests/test_evaluation.py`
- Operator docs: `README.md`, `eval/README.md`, `SKILL.md`, `docs/system-overview.md`

## Plan of Work

1. Add and index the new implementation plan.
2. Extend benchmark selection so named subsets and category filters can be reused from the existing eval CLI.
3. Improve the CLI summary so multi-case runs print per-case pass/fail state, mismatch notes, and case artifact roots.
4. Add tests for subset selection, invalid subset handling, and CLI reporting.
5. Run a real live subset spanning the remaining benchmark categories and record the resulting artifact path and outcome here.
6. Stabilize any live prompt/runtime issues exposed by those artifacts without breaking the deterministic baseline.

## Concrete Steps

1. Add `plans/19-live-suite-expansion.md` and update `plans/README.md`.
2. Update `src/deep_gvr/evaluation.py` with reusable benchmark subset metadata plus selection/report-formatting helpers.
3. Update `eval/run_eval.py` to expose the new subset/category options and richer case-by-case output.
4. Add tests in `tests/test_evaluation.py` for subset filtering and CLI reporting.
5. Run targeted tests such as:

```bash
uv run python -m unittest tests.test_evaluation -v
```

6. Run the required repo checks and then a real live subset such as:

```bash
uv run python eval/run_eval.py --mode live --routing-probe fallback --subset live-expansion --prompt-profile compact --command-timeout-seconds 120 --output-root /tmp/deep-gvr-live-suite-expansion
```

7. During this slice, also run targeted live category reruns to isolate the remaining failures:

```bash
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --case-id formal-proved-repetition-majority --prompt-profile compact --command-timeout-seconds 120 --output-root /tmp/deep-gvr-live-suite-expansion-formal-final-3
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --case-id simulation-verified-distance5 --prompt-profile compact --command-timeout-seconds 120 --output-root /tmp/deep-gvr-live-suite-expansion-sim-final-6
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --case-id known-incorrect-surface-threshold-5pct --prompt-profile compact --command-timeout-seconds 120 --output-root /tmp/deep-gvr-live-suite-expansion-known-incorrect-final
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --subset live-expansion --prompt-profile compact --command-timeout-seconds 120 --output-root /tmp/deep-gvr-live-suite-expansion-final-2
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
uv run python -m unittest tests.test_evaluation tests.test_contracts tests.test_tier1_loop tests.test_stim_adapter -v
```

Acceptance evidence:

- The eval CLI accepts a named subset that spans representative live categories beyond the already-proven single correct case.
- The CLI prints per-case pass/fail summaries with artifact roots and mismatch notes so live multi-case sweeps are operationally useful.
- Tests pin the new subset-selection and reporting behavior without relying on live Hermes calls.
- Real live category runs are recorded with their output roots and summarized outcomes in this plan.
- The final representative live subset output root is recorded here even though one case still shows model variance in the full three-case sweep.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/live-suite-expansion` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Subset selection and reporting should be additive; existing `--case-id` workflows must continue to work.
- If the real live subset exposes content/runtime failures, keep the artifacts and record the exact output root here instead of removing the workflow changes.
- If a live subset times out mid-run, the case-by-case report should still leave enough output to identify which case failed and where its artifacts landed.

## Interfaces and Dependencies

- `eval/run_eval.py` is the operator-facing boundary for deterministic and live suite runs.
- `src/deep_gvr/evaluation.py` owns benchmark selection, execution, and report summarization.
- `eval/known_problems.json` remains the source of truth for case definitions; reusable subsets should point into this corpus rather than duplicating it.
