# 18 Live Content Accuracy

## Purpose / Big Picture

Tighten the live generator output on the shared default route so the surface-code threshold benchmark stops failing for content-accuracy reasons after the route-selection work. The latest live smoke already falls back to the correct route and completes generator and verifier execution, but the verifier still flags two specific issues: the candidate mis-attributes the familiar `~10.3%` code-capacity figure to the Nishimori-point mapping instead of reserving that mapping for the higher `~10.9%` maximum-likelihood bit-flip threshold, and it cites Raussendorf-Harrington-Goyal in the body without listing the work in `references`. This slice should encode those corrections in repo-local QEC anchors, the generator prompt, tests, and lightweight docs so future live runs inherit the fix mechanically.

## Branch Strategy

Start from `main` and implement this slice on `codex/live-content-accuracy`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result, push `main`, confirm CI, and delete the feature branch.

## Commit Plan

- `add live content accuracy plan`
- `tighten live threshold attribution guidance`
- `refine live threshold scope guidance`
- `document live content accuracy behavior`

## Progress

- [x] Add the new plan and index it from `plans/README.md`.
- [x] Tighten repo-local QEC anchor notes for the `~10.3%` versus `~10.9%` threshold semantics and citation-discipline rule.
- [x] Strengthen generator instructions so it avoids the Nishimori-point mis-attribution and body/reference drift.
- [x] Extend tests to pin the new live-domain guidance and any prompt/query behavior that should now hold.
- [x] Re-run targeted tests, repo-wide validation, and a narrow live smoke on the default route to see whether the remaining live failure persists or changes.

## Surprises & Discoveries

- The route-selection slice removed the route-blindness problem, so the current live failure is now traceable to the actual model output on the shared default route rather than to provider/model wiring.
- The latest verifier report at `/tmp/deep-gvr-live-route-selection/cases/known-correct-surface-threshold/verification_report.json` isolates only two flaws, which makes this a prompt/domain-quality slice rather than a harness-control-flow slice.
- The generator already includes a partial caveat about independent X/Z decoding, so the remaining threshold bug is not missing context entirely; it is a more precise attribution error that needs stronger anchor language.
- A first follow-up live smoke at `/tmp/deep-gvr-live-content-accuracy-120/report.json` removed the original `~10.3%` and missing-reference flaws but exposed a wrong `Wang, Fowler, Hollenberg` year and an over-broad attribution to the generic threshold theorem.
- A second follow-up live smoke at `/tmp/deep-gvr-live-content-accuracy-final/report.json` showed the next remaining issue was hypothesis scope: the generator was still overloading the main depolarizing claim with toric-code and bit-flip-only details.
- The final live smoke at `/tmp/deep-gvr-live-content-accuracy-final-2/report.json` passed after the prompt/domain guidance told the generator to keep the main claim on circuit-level depolarizing thresholds and to prefer Fowler/Stephens for the sub-1% MWPM range.

## Decision Log

- Keep this slice narrow and grounded in the concrete verifier findings instead of broadening into another general prompt rewrite.
- Encode the `~10.9%` Nishimori-point versus `~10.3%` independent-X/Z decoding distinction in the repo-local domain anchors so both CLI and live eval inherit it automatically.
- Strengthen the generator prompt to prefer omitting marginal citations over naming a work in the body without listing it in `references`.
- Use the existing live domain-context injection tests to pin the new anchor language instead of inventing a separate testing surface.

## Outcomes & Retrospective

This slice succeeded. The repo-local QEC anchors and generator prompt now encode three layers of live-content discipline that the earlier route-focused slices were missing: precise `~10.3%` versus `~10.9%` threshold semantics, explicit body/reference citation discipline, and scope control that keeps generic depolarizing threshold answers centered on the circuit-level surface-code regime instead of dragging in toric-code/bit-flip details. The final live smoke at `/tmp/deep-gvr-live-content-accuracy-final-2/report.json` returned `VERIFIED` for `known-correct-surface-threshold`, with the generator response in `/tmp/deep-gvr-live-content-accuracy-final-2/cases/known-correct-surface-threshold/candidate_solution.json` scoped to the depolarizing circuit-level claim and the verifier response in `/tmp/deep-gvr-live-content-accuracy-final-2/cases/known-correct-surface-threshold/verification_report.json` downgraded the remaining source-precision concerns to caveats instead of flaws.

## Context and Orientation

- Live artifact motivating the slice:
  - `/tmp/deep-gvr-live-route-selection/cases/known-correct-surface-threshold/candidate_solution.json`
  - `/tmp/deep-gvr-live-route-selection/cases/known-correct-surface-threshold/verification_report.json`
  - `/tmp/deep-gvr-live-route-selection/report.json`
- Repo-local QEC anchors: `domain/known_results.md`
- Generator guidance: `prompts/generator.md`
- Live role runner and domain-context injection tests: `src/deep_gvr/evaluation.py`, `tests/test_evaluation.py`
- Plan index: `plans/README.md`

## Plan of Work

1. Add and index the new implementation plan for this slice.
2. Tighten the QEC anchor notes in `domain/known_results.md` around Nishimori-point semantics, independent-X/Z decoding, and citation hygiene.
3. Tighten `prompts/generator.md` so live generation avoids the specific attribution and reference-list failures seen in the latest smoke.
4. Add or update tests that assert the new domain guidance is injected into live queries and remains stable.
5. Run targeted tests, then repo-wide validation, then a narrow live smoke on the default route and record the outcome here.

## Concrete Steps

1. Add `plans/18-live-content-accuracy.md` and update `plans/README.md`.
2. Update `domain/known_results.md` with explicit `~10.9%` versus `~10.3%` wording and a stronger reminder that any named work must appear in `references`.
3. Update `prompts/generator.md` with stricter body/reference and threshold-attribution instructions.
4. Update `tests/test_evaluation.py` so the live query assertions pin the new QEC anchor language.
5. Run targeted tests and the required repo checks.
6. Run a narrow live smoke such as:

```bash
uv run python eval/run_eval.py --mode live --routing-probe fallback --case-id known-correct-surface-threshold --prompt-profile compact --command-timeout-seconds 60 --output-root /tmp/deep-gvr-live-content-accuracy
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

- Live domain-context injection tests assert the query includes the new threshold-attribution guidance.
- The generator prompt explicitly tells the model not to attribute `~10.3%` to the Nishimori-point mapping and to keep body citations aligned with `references`.
- A fresh narrow live smoke reaches `VERIFIED` for `known-correct-surface-threshold` or changes the remaining failure mode away from the current `~10.3%` mis-attribution and missing-reference issues, with the new artifact path recorded here.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/live-content-accuracy` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- The domain and prompt changes are additive; if the live smoke still fails, keep the new artifact set and record the exact remaining flaws here instead of backing out the guidance.
- If the live smoke times out or fails for infrastructure reasons, preserve that artifact set separately from the content-accuracy baseline and note the exact path in this plan.
- Tests should remain deterministic and should only pin the injected prompt/domain content, not any live model output.

## Interfaces and Dependencies

- `domain/known_results.md` is injected into live CLI and eval runs through the shared domain-context loader, so changes there affect both paths.
- `prompts/generator.md` is consumed by `HermesPromptRoleRunner` in `src/deep_gvr/evaluation.py` and by the CLI live path.
- `tests/test_evaluation.py` already exercises live query construction and is the right place to pin the new anchor text.
