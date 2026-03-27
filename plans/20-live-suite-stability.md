# 20 Live Suite Stability

## Purpose / Big Picture

Turn the new live-suite workflow into a stable operator tool instead of a one-off debugging surface. The repo now has a representative `live-expansion` subset, richer per-case summaries, a passing Tier 2 single-case run, and a passing Tier 3 single-case run. What is still missing is repeatable live stability: the same subset can still vary between runs, especially on `simulation-verified-distance5`, and the current report surface does not separate honest-refutation passes from true verdict/tier mismatches clearly enough for operators. This slice should add stability-oriented reporting, a small consistency-run surface, and tighter live Tier 2 discipline for empirically testable quantitative claims.

## Branch Strategy

Start from `main` and implement this slice on `codex/live-suite-stability`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result, push `main`, confirm CI, and delete the feature branch.

## Commit Plan

- `add live suite stability plan`
- `add live suite stability reporting`
- `stabilize simulation-required live checks`
- `document live suite stability workflow`

## Progress

- [x] Add the new plan and index it from `plans/README.md`.
- [x] Extend live benchmark result reporting so accepted-refutation passes and tier mismatches are explicit, machine-readable fields rather than only inferred from notes.
- [x] Add a repeatable consistency-run surface for the `live-expansion` subset.
- [x] Tighten the live verifier/generator behavior for empirically testable simulation-required claims so Tier 2 is requested more reliably in multi-case sweeps.
- [x] Run targeted tests, repo-wide validation, and repeat live subset checks, then record the artifact roots and residual variance here.

## Surprises & Discoveries

- The current live benchmark surface already has the information needed to explain most failures, but it still compresses too much into `notes`, which makes accepted-refutation passes and tier mismatches harder to separate.
- The `simulation-verified-distance5` case can pass cleanly by itself while still occasionally verifying at Tier 1 in a full `live-expansion` sweep, so the remaining gap is stability rather than missing harness plumbing.
- Honest generator refutations are a real behavior on known-incorrect prompts. Treating them as benchmark success is correct, but that needs to be visible directly in the report structure instead of only as a free-form note.
- The tightened Tier 2 trigger did move the live simulation case in the intended direction: repeated live evidence now shows `simulation-verified-distance5` reliably requesting and running Tier 2 instead of collapsing to a Tier 1-only pass.
- The remaining live variance is now mostly content/runtime variance, not missing mediation. In the repeated two-case live run, one known-incorrect run timed out in the verifier and one simulation run still ended `FLAWS_FOUND` even though the attached Tier 2 evidence confirmed the core ordering claim.

## Decision Log

- Keep `eval/known_problems.json` as the source of truth for case definitions and expected tiers.
- Extend the existing eval runner/report surface instead of adding another top-level live-suite wrapper.
- Prefer generic verifier-discipline improvements for empirically testable claims over benchmark-only hardcoding where practical.
- Add explicit consistency-run support so operators can measure live stability across repeated sweeps instead of inferring it from ad hoc reruns.
- Keep the repeated two-case live run as the main recorded stability artifact for this slice after the full three-case repeat stalled on runtime budget. It still exercises the accepted-refutation path plus the simulation-required Tier 2 path, which were the main stability targets of this slice.

## Outcomes & Retrospective

- The eval runner now records explicit case-level stability fields: `strict_verdict_match`, `verdict_accepted`, `tiers_matched_expected`, `accepted_refutation`, and `outcome`.
- The CLI now supports repeated eval runs with `--repeat`, writes per-run reports under `runs/run-###/report.json`, and writes an aggregate `consistency_report.json`.
- The verifier prompt and compact verifier path now default Tier 2 for named threshold/order/error-rate claims that arrive without attached simulation evidence.
- Deterministic validation passed and the committed baseline was regenerated with the richer report shape.
- Real live stability evidence is mixed rather than fully stable:
  - Full three-case repeated attempt at `/tmp/deep-gvr-live-suite-stability/` completed run 1 and showed the simulation case taking the intended Tier 2 path plus the formal case reaching the Aristotle-auth layer, but the bounded repeated sweep was stopped before run 2 after the formal branch consumed too much runtime budget.
  - Repeated two-case live run at `/tmp/deep-gvr-live-suite-stability-two-case/consistency_report.json` finished with `fully_passing_runs=1/2` and `unstable_cases=2`.
  - In that two-case run, `known-incorrect-surface-threshold-5pct` passed once via `accepted_refutation` and failed once with a verifier timeout recorded at `/tmp/deep-gvr-live-suite-stability-two-case/runs/run-002/cases/known-incorrect-surface-threshold-5pct/live_error.json`.
  - `simulation-verified-distance5` passed once with a real Tier 2 verification path and failed once as a `verdict_mismatch` even though Tier 2 confirmed the core ordering claim, recorded at `/tmp/deep-gvr-live-suite-stability-two-case/runs/run-002/cases/simulation-verified-distance5/case_result.json`.

## Context and Orientation

- Live eval runner: `eval/run_eval.py`
- Benchmark execution/reporting: `src/deep_gvr/evaluation.py`
- Prompt shaping: `prompts/generator.md`, `prompts/verifier.md`, `prompts/verifier_compact.md`, `src/deep_gvr/prompt_profiles.py`
- Current live-suite plan and artifacts: `plans/19-live-suite-expansion.md`
- Operator docs: `README.md`, `eval/README.md`, `SKILL.md`, `docs/system-overview.md`

## Plan of Work

1. Add and index the new implementation plan.
2. Extend the live benchmark result model and CLI formatting so accepted-refutation passes, verdict matches, and tier matches are distinct fields.
3. Add a repeatable consistency-run surface for named subsets such as `live-expansion`.
4. Tighten live verifier/generator instructions for empirically testable simulation-required claims.
5. Run targeted tests plus repeated live subset checks and record the artifact roots and outcomes here.

## Concrete Steps

1. Add `plans/20-live-suite-stability.md` and update `plans/README.md`.
2. Update `src/deep_gvr/evaluation.py` so live case results expose explicit status flags instead of only summarizing them in notes.
3. Update `eval/run_eval.py` to expose a small repeat/consistency surface for live subset runs.
4. Tighten `prompts/generator.md`, `prompts/verifier.md`, `prompts/verifier_compact.md`, and `src/deep_gvr/prompt_profiles.py` around empirically testable quantitative claims.
5. Add or update tests in `tests/test_evaluation.py` and any affected contract tests.
6. Run targeted tests such as:

```bash
uv run python -m unittest tests.test_evaluation -v
```

7. Run the required repo checks and then repeated live checks such as:

```bash
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --subset live-expansion --prompt-profile compact --command-timeout-seconds 120 --output-root /tmp/deep-gvr-live-suite-stability
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --case-id known-incorrect-surface-threshold-5pct --case-id simulation-verified-distance5 --prompt-profile compact --command-timeout-seconds 90 --repeat 2 --output-root /tmp/deep-gvr-live-suite-stability-two-case
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
```

Acceptance evidence:

- The live benchmark result surface exposes accepted-refutation passes and verdict/tier matches explicitly instead of only through free-form notes.
- The eval CLI has a repeatable consistency-run surface for named subsets.
- The simulation-required live case is more stable, or any residual instability is explicit in the consistency output and this plan.
- Real live runs are recorded with their artifact roots and summarized outcomes in this plan.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/live-suite-stability` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- The new reporting fields should be additive and should not break existing benchmark report consumers.
- If repeated live runs still show variance, keep the recorded consistency artifacts and summarize the residual instability here instead of hiding it behind a single best run.
- If live consistency runs time out, the output should still identify which case/run failed and where the artifacts landed.

## Interfaces and Dependencies

- `eval/run_eval.py` remains the operator-facing benchmark boundary.
- `src/deep_gvr/evaluation.py` owns case selection, execution, stability reporting, and report summarization.
- `eval/known_problems.json` remains the source of truth for benchmark cases; consistency runs should reuse it rather than duplicating case metadata.
