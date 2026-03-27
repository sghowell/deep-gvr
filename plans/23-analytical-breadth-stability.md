# 23 Analytical Breadth Stability

## Purpose / Big Picture

Stabilize the broader Tier 1 live coverage sweep. The repo now has a stable repeated representative gate in `live-expansion` and a working broader coverage surface in `live-analytical-breadth`, but the latest analytical breadth artifact still shows two avoidable failures: `known-correct-surface-threshold` over-escalates to Tier 2, and `known-correct-planar-qubits` can fail on an initial verifier timeout. This slice should tighten prompt discipline for literature-threshold and pure asymptotic-counting claims, reduce avoidable verifier bulk on the compact analytical path, and rerun the analytical breadth sweep until it is either stable or narrowed to one explicit remaining failure mode.

## Branch Strategy

Start from `main` and implement this slice on `codex/analytical-breadth-stability`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result, push `main`, confirm CI, and delete the feature branch.

## Commit Plan

- `add analytical breadth stability plan`
- `stabilize analytical live verifier path`
- `document analytical breadth stability`

## Progress

- [x] Add the new plan and index it from `plans/README.md`.
- [x] Tighten generator and verifier guidance so literature-grounded threshold explanations and pure counting/scaling answers stay on Tier 1 unless they introduce a genuinely new empirical or formal claim.
- [x] Reduce avoidable compact-verifier overhead for analytical cases and modestly raise the initial verifier timeout floor.
- [x] Run targeted tests, repo-wide validation, and repeated `live-analytical-breadth` checks, then record the resulting artifact roots and final stability state here.

## Surprises & Discoveries

- The latest analytical breadth artifact at `/tmp/deep-gvr-live-analytical-breadth-final-2/report.json` is a clean split between one tier-discipline failure and one runtime failure, not a broad content-quality regression.
- `known-correct-surface-threshold` finished `VERIFIED`, but the verifier still routed it through Tier 2 because the candidate restated generic below-threshold suppression in a way that looked like a fresh simulation target.
- `known-correct-planar-qubits` timed out in the verifier at 120 seconds even though the compact verifier query was only about 6.1k characters and the candidate was already concise, so prompt bulk is part of the problem but not the whole story.
- The current compact verifier prompt duplicates a large fraction of the discipline already restated in the compact query builder, so shortening the prompt file itself is a low-risk way to reduce live verifier payload size without changing the overall contract surface.
- Rebuilding the old failing analytical verifier inputs against the new compact prompt path cut about 875 characters from both the `known-correct-surface-threshold` and `known-correct-planar-qubits` verifier queries.
- The remaining repeated-run blocker is now external to the repo logic: the real Hermes environment is returning a plain-text `AuthenticationError` for `nous/claude-opus-4-6` even when the live runner passes explicit `--provider openrouter --model ...` flags, so the broader analytical sweep now fails uniformly as a structured live route configuration error instead of the earlier mix of tier mismatch and timeout.

## Decision Log

- Prefer generic prompt-discipline rules over benchmark-only hardcoding in the evaluator.
- Fix threshold over-escalation by changing both generator and verifier behavior: the generator should stop phrasing literature-threshold explanations as fresh simulator-ready predictions, and the verifier should keep established threshold-regime explanations at Tier 1 unless the candidate adds a genuinely new empirical target.
- Keep pure counting and asymptotic scaling questions on the Tier 1 path and explicitly tell the verifier to keep those audits short.
- Allow a modest initial verifier-timeout increase if the analytical compact path still needs more room after prompt trimming.

## Outcomes & Retrospective

- The threshold over-escalation is fixed on the real route. The targeted live rerun at `/tmp/deep-gvr-analytical-threshold-stability/report.json` finished `1/1` passed with `known-correct-surface-threshold` staying on Tier 1.
- The compact analytical verifier path is materially smaller now. Rebuilding the old failing verifier inputs against the current prompt/profile path cut about 875 characters from both the `known-correct-surface-threshold` and `known-correct-planar-qubits` verifier queries.
- Provider-only live route selections are now treated as explicit top-level route intent, and Hermes plain-text auth/401 failures are now classified as live route configuration errors instead of bubbling up as JSON parse failures.
- The repeated analytical breadth sweep did not stabilize in this local environment. The consistency report at `/tmp/deep-gvr-live-analytical-breadth-stability/consistency_report.json` finished `0/10` case-runs passed, but every failure is the same `execution_error`: Hermes rejected the active `nous/claude-opus-4-6` provider path during the generator call.
- That means the repo-side analytical-breadth issues are no longer mixed. The remaining blocker is operational: the local Hermes provider credential or default-route setup must be fixed before `live-analytical-breadth` can become a reliable repeated gate here.

## Context and Orientation

- Current representative stable gate: `plans/21-live-suite-hardening.md`
- Current broader coverage slice: `plans/22-live-suite-broadening.md`
- Live benchmark runner: `eval/run_eval.py`
- Live benchmark/report logic: `src/deep_gvr/evaluation.py`
- Live runtime timeout policy: `src/deep_gvr/live_runtime.py`
- Prompt shaping: `prompts/generator.md`, `prompts/verifier.md`, `prompts/verifier_compact.md`, `src/deep_gvr/prompt_profiles.py`
- Main analytical failure artifacts:
  - `/tmp/deep-gvr-live-analytical-breadth-final-2/report.json`
  - `/tmp/deep-gvr-live-analytical-breadth-final-2/cases/known-correct-surface-threshold/verification_report.json`
  - `/tmp/deep-gvr-live-analytical-breadth-final-2/cases/known-correct-planar-qubits/live_error.json`

## Plan of Work

1. Add and index the new implementation plan.
2. Tighten generator instructions so literature-threshold explanations stay literature-grounded and pure counting/scaling answers stay concise.
3. Tighten verifier instructions so literature-threshold explanations and pure counting/scaling claims remain Tier 1 by default, while still preserving Tier 2 triggers for genuinely new simulation-dependent claims.
4. Reduce compact verifier prompt bulk and, if necessary, modestly raise the initial verifier timeout floor.
5. Run targeted tests plus repeated analytical-breadth live checks and record the resulting artifact roots here.

## Concrete Steps

1. Add `plans/23-analytical-breadth-stability.md` and update `plans/README.md`.
2. Update `prompts/generator.md` with tighter literature-threshold and pure counting/scaling guidance.
3. Update `prompts/verifier.md` and `prompts/verifier_compact.md` so analytical threshold explanations and pure asymptotic-counting claims stay on Tier 1 unless the candidate adds a true empirical or formal obligation.
4. Update `src/deep_gvr/live_runtime.py` and any affected tests if the verifier timeout floor changes.
5. Update `tests/test_evaluation.py` to pin the new prompt guidance and timeout behavior.
6. Run targeted tests such as:

```bash
uv run python -m unittest tests.test_evaluation -v
```

7. Run the required repo checks and then live analytical reruns such as:

```bash
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --case-id known-correct-surface-threshold --prompt-profile compact --command-timeout-seconds 120 --output-root /tmp/deep-gvr-analytical-threshold-stability
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --case-id known-correct-planar-qubits --prompt-profile compact --command-timeout-seconds 120 --output-root /tmp/deep-gvr-analytical-planar-stability
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --case-id known-correct-planar-qubits --prompt-profile compact --command-timeout-seconds 120 --output-root /tmp/deep-gvr-analytical-planar-stability-2
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --subset live-analytical-breadth --prompt-profile compact --command-timeout-seconds 120 --repeat 2 --output-root /tmp/deep-gvr-live-analytical-breadth-stability
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

- The generator no longer turns the threshold-understanding benchmark into a fresh simulator-ready claim.
- The verifier keeps literature-threshold explanations and pure counting/scaling claims at Tier 1 unless the candidate adds a genuinely new empirical or formal obligation.
- The compact analytical verifier path is smaller and/or more tolerant of live route latency than before.
- A repeated `live-analytical-breadth` run either passes cleanly or narrows the remaining instability to one explicit cause with recorded artifacts.
- Final recorded artifact set:
  - Tier 1 threshold rerun without over-escalation: `/tmp/deep-gvr-analytical-threshold-stability/report.json`
  - Provider-auth execution error after the route-fallback hardening: `/tmp/deep-gvr-analytical-planar-stability-2/report.json`
  - Repeated analytical breadth narrowed to one external auth failure mode: `/tmp/deep-gvr-live-analytical-breadth-stability/consistency_report.json`

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/analytical-breadth-stability` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Keep the prompt changes additive and generic so they improve CLI and live-eval behavior together instead of baking in benchmark-only logic.
- If the analytical sweep still fails, preserve the new artifact roots and record the remaining failure mode here instead of silently weakening the benchmark expectations.
- If the initial verifier timeout floor increases, keep the change modest and justified by the recorded analytical timeout artifact.

## Interfaces and Dependencies

- `eval/run_eval.py` remains the operator-facing boundary for repeated live analytical sweeps.
- `src/deep_gvr/live_runtime.py` owns the repo-local default timeout policy for live role calls.
- `prompts/` and `src/deep_gvr/prompt_profiles.py` jointly define the live generator/verifier behavior that drives the analytical sweep.
- `tests/test_evaluation.py` owns the main prompt/runtime coverage for the live analytical path.
