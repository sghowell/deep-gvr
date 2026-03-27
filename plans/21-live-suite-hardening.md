# 21 Live Suite Hardening

## Purpose / Big Picture

Turn the remaining live-suite variance into a smaller, more explicit target. The repo now has repeatable live-suite reporting and a two-case consistency artifact, but the recorded live evidence still shows one runtime failure and one content-level failure. This slice should harden the live generator/verifier behavior for the remaining unstable cases, reduce avoidable verifier timeouts, and rerun the repeated live checks to see whether the remaining variance is content, runtime, or both.

## Branch Strategy

Start from `main` and implement this slice on `codex/live-suite-hardening`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result, push `main`, confirm CI, and delete the feature branch.

## Commit Plan

- `add live suite hardening plan`
- `narrow live simulation and refutation prompts`
- `tune live verifier timeout policy`
- `document live suite hardening workflow`

## Progress

- [x] Add the new plan and index it from `plans/README.md`.
- [x] Tighten live generator/verifier prompt behavior so simulation-required cases stay scoped to the benchmarked claim and known-incorrect refutations stay concise.
- [x] Raise or otherwise tune the live verifier timeout policy enough to reduce avoidable known-incorrect verifier timeouts.
- [x] Run targeted tests, repo-wide validation, and repeated live checks, then record the new artifact roots and residual variance here.

## Surprises & Discoveries

- The repeated two-case live artifact at `/tmp/deep-gvr-live-suite-stability-two-case/consistency_report.json` shows that Tier 2 triggering is no longer the main issue for `simulation-verified-distance5`; the remaining failure is a post-simulation verdict mismatch.
- In the failing simulation run, the verifier accepted the core Tier 2 ordering evidence but still returned `FLAWS_FOUND` because the generator added an unsupported X-basis sub-claim and an over-specific noise-model description.
- In the failing known-incorrect run, the instability was a verifier timeout rather than a content disagreement, so runtime policy still matters.
- The broader `live-expansion` repeat after the first hardening pass narrowed the remaining instability to evaluator scoring: one known-incorrect run produced a correct verified refutation but missed the accepted-refutation heuristic because it used conservative range language (`~0.6-0.8%`, `order of magnitude lower`) instead of the exact earlier marker phrases.

## Decision Log

- Keep the new consistency-report surface from plan 20 as the source of truth for live instability evidence.
- Prefer generic prompt-scoping rules over benchmark-only hardcoding where practical.
- Allow a modest verifier-timeout increase if that is the smallest change that removes avoidable live timeout variance.
- Reuse the same repeated two-case live run first before reattempting the broader `live-expansion` repeat.

## Outcomes & Retrospective

- The prompt hardening worked: the repeated two-case live run at `/tmp/deep-gvr-live-suite-hardening-two-case/consistency_report.json` finished `4/4` case-runs passed with `fully_passing_runs=2/2` and `unstable_cases=0`.
- The first broader rerun at `/tmp/deep-gvr-live-suite-hardening/consistency_report.json` showed that simulation and formal cases were stable, and narrowed the only remaining instability to accepted-refutation scoring for `known-incorrect-surface-threshold-5pct`.
- The evaluator now accepts explicit verified refutations of the 5% circuit-level threshold claim when they use conservative range language such as `well below 1%`, `~0.6-0.8%`, or `order of magnitude lower`, provided the candidate also clearly rejects the claim.
- The final representative repeated live sweep at `/tmp/deep-gvr-live-suite-hardening-final/consistency_report.json` finished `6/6` case-runs passed with `fully_passing_runs=2/2` and `unstable_cases=0`.

## Context and Orientation

- Current instability record: `plans/20-live-suite-stability.md`
- Live benchmark runner: `eval/run_eval.py`
- Benchmark execution/reporting: `src/deep_gvr/evaluation.py`
- Runtime timeout/tool policy: `src/deep_gvr/live_runtime.py`
- Prompt shaping: `prompts/generator.md`, `prompts/verifier.md`, `prompts/verifier_compact.md`, `src/deep_gvr/prompt_profiles.py`
- Main failing artifacts:
  - `/tmp/deep-gvr-live-suite-stability-two-case/consistency_report.json`
  - `/tmp/deep-gvr-live-suite-stability-two-case/runs/run-002/cases/known-incorrect-surface-threshold-5pct/live_error.json`
  - `/tmp/deep-gvr-live-suite-stability-two-case/runs/run-002/cases/simulation-verified-distance5/verification_report.json`

## Plan of Work

1. Add and index the new implementation plan.
2. Tighten generator instructions so simulation-required answers do not add unsupported basis variants or overly specific noise-channel details.
3. Tighten verifier instructions so Tier-2-confirmed core claims treat auxiliary scope drift as caveats unless it overturns the core claim.
4. Tune the live verifier timeout floor to reduce avoidable verifier timeouts on concise Tier 1 refutation cases.
5. Run targeted tests plus repeated live checks and record the resulting artifact roots and residual variance here.

## Concrete Steps

1. Add `plans/21-live-suite-hardening.md` and update `plans/README.md`.
2. Update `prompts/generator.md` and any compact prompt/profile surfaces so simulation-required claims stay scoped to the exact ordering or threshold statement under test.
3. Update `prompts/verifier.md`, `prompts/verifier_compact.md`, and `src/deep_gvr/prompt_profiles.py` so Tier-2-confirmed core claims downgrade auxiliary unsupported variants to caveats when appropriate.
4. Update `src/deep_gvr/live_runtime.py` and the affected tests if the verifier timeout floor changes.
5. Add or update tests in `tests/test_evaluation.py` and any other affected test modules.
6. Run targeted tests such as:

```bash
uv run python -m unittest tests.test_evaluation -v
```

7. Run the required repo checks and then repeated live checks such as:

```bash
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --case-id known-incorrect-surface-threshold-5pct --case-id simulation-verified-distance5 --prompt-profile compact --command-timeout-seconds 90 --repeat 2 --output-root /tmp/deep-gvr-live-suite-hardening-two-case
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --subset live-expansion --prompt-profile compact --command-timeout-seconds 120 --repeat 2 --output-root /tmp/deep-gvr-live-suite-hardening
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --subset live-expansion --prompt-profile compact --command-timeout-seconds 120 --repeat 2 --output-root /tmp/deep-gvr-live-suite-hardening-final
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

- The generator is less likely to emit unsupported X-basis or over-detailed noise-model claims for the simulation-required benchmark case.
- The known-incorrect live case no longer times out as often, or any remaining timeout variance is explicitly recorded in the updated plan.
- Repeated live runs show improved stability, or the remaining instability is narrowed to a smaller and better-understood cause than in plan 20.
- Final acceptance target met: the representative repeated `live-expansion` sweep reaches `fully_passing_runs=2/2` with `unstable_cases=0`.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/live-suite-hardening` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- The prompt hardening should stay additive and should not break deterministic fixtures or the existing report contract.
- If repeated live runs still fail, keep the new artifact roots and summarize the narrower failure mode here rather than reverting to ad hoc anecdotes.
- If the verifier timeout floor increases, keep the change modest and justified by observed live failures.

## Interfaces and Dependencies

- `eval/run_eval.py` remains the operator-facing live benchmark boundary.
- `src/deep_gvr/live_runtime.py` owns the repo-local default timeout/tool policy for live role calls.
- `prompts/` and `src/deep_gvr/prompt_profiles.py` jointly define live generator/verifier behavior.
- `plans/20-live-suite-stability.md` remains the prior slice record; this plan should build directly on its recorded artifacts instead of rediscovering them.
