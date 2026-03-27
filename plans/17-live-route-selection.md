# 17 Live Route Selection

## Purpose / Big Picture

Improve live-route selection and live benchmark quality without loosening the harness. The current live runner issues separate top-level `hermes chat` calls for generator, verifier, and reviser, but it still inherits the generic fallback routing plan that was designed for Hermes subagent uncertainty. This slice should let live runs prefer explicit role routes when they are configured, fall back cleanly when a provider/model path is invalid, and tighten the QEC anchor notes for the specific content errors the verifier is now surfacing.

## Branch Strategy

Start from `main` and implement this slice on `codex/live-route-selection`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result, push `main`, confirm CI, and delete the feature branch.

## Commit Plan

- `add live route selection plan`
- `add live route fallback policy`
- `document live route selection behavior`

## Progress

- [ ] Added the new plan and indexed it from `plans/README.md`.
- [ ] Added a live-specific routing helper that prefers explicit top-level role routes while keeping a shared-route fallback for invalid live provider/model paths.
- [ ] Wired CLI and live eval to use the live-specific routing helper instead of the generic subagent fallback plan.
- [ ] Ensured evidence records and transcripts reflect the actual route used after any live fallback.
- [ ] Tightened repo-local QEC anchors and generator guidance for the threshold/content issues now identified by live verification.
- [ ] Added tests for live-route fallback and actual-route evidence recording.
- [ ] Re-ran a narrow live smoke and recorded whether explicit-route fallback behaved as intended on this machine.

## Surprises & Discoveries

- The current live runner makes separate top-level `hermes chat` calls, so the `per_subagent_model_routing` probe is too conservative if applied directly to live role routing.
- A direct probe of `hermes chat --provider openrouter --model deepseek-r1` on this machine failed quickly with a provider-side `400`, so simply forcing configured role routes would be brittle.
- The latest verifier findings are now narrower and more content-specific: the main recurring issues are independent-X/Z-vs-depolarizing threshold language and citation drift around Raussendorf-Harrington versus standard 2D planar/rotated surface-code threshold references.

## Decision Log

- Keep the generic routing plan for the core harness and deterministic tests; add a separate live-specific routing helper instead of changing the baseline semantics globally.
- Treat explicit live provider/model failures as route-selection errors, not candidate-quality failures, and fall back to the shared route only for those route errors.
- Record actual live fallback routes in evidence and transcripts so live artifacts remain trustworthy.
- Tighten QEC anchor notes in repo-local domain context rather than relying on repeated chat-only corrections.

## Outcomes & Retrospective

This slice should leave the repo with a live-specific routing path that can try explicit role routes first, fall back when those routes are invalid, and still record the actual provider/model used in evidence. It should also leave the QEC benchmark anchors more specific about code-capacity noise semantics and standard circuit-level citations so the generator stops repeating the same threshold-language mistakes.

## Context and Orientation

- Generic routing helper: `src/deep_gvr/routing.py`
- Tier 1 runner route application: `src/deep_gvr/tier1.py`
- Live runner and eval path: `src/deep_gvr/evaluation.py`
- CLI path: `src/deep_gvr/cli.py`
- QEC anchors: `domain/known_results.md`
- Generator guidance: `prompts/generator.md`
- Live evidence motivating the slice:
  - `/tmp/deep-gvr-live-verifier-throughput/report.json`
  - `/tmp/deep-gvr-live-verifier-throughput-2/report.json`

## Plan of Work

1. Add a live-specific routing helper that can prefer explicit role routes while retaining shared-route fallback candidates.
2. Teach the live role runner to retry only when the failure looks like a route/provider/model configuration error.
3. Make the Tier 1 evidence path record the actual route used by the live role runner after any fallback.
4. Tighten the QEC anchor notes and generator instructions around code-capacity threshold semantics and standard surface-code citations.
5. Add tests for live-route fallback and actual-route evidence recording.
6. Re-run a narrow live smoke and capture the behavior in this plan and the docs.

## Concrete Steps

1. Add `plans/17-live-route-selection.md` and index it from `plans/README.md`.
2. Update `src/deep_gvr/routing.py` with a live-specific routing helper and any supporting route metadata needed for fallback.
3. Update `src/deep_gvr/tier1.py`, `src/deep_gvr/evaluation.py`, and `src/deep_gvr/cli.py` so live runs use the live-specific plan and evidence records carry the actual route.
4. Update `domain/known_results.md` and `prompts/generator.md` with the new QEC anchors.
5. Add or update tests in `tests/test_routing.py`, `tests/test_evaluation.py`, and any necessary Tier 1 tests.
6. Run targeted tests, then the required repo-wide checks, then a narrow live smoke.

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Targeted validation during implementation:

```bash
uv run python -m unittest tests.test_routing tests.test_evaluation tests.test_cli tests.test_tier1_loop -v
```

Acceptance evidence:

- A targeted test proves a live run can fall back from an invalid explicit provider/model route to the shared route and still succeed.
- Evidence and transcript artifacts record the actual fallback route used.
- Repo-local QEC anchor notes explicitly distinguish independent-X/Z code-capacity thresholds from full depolarizing threshold language and warn against misusing Raussendorf-Harrington 2007 as the standard 2D surface-code circuit-level citation.
- A fresh live smoke records either successful explicit-route fallback or a clear structured transcript showing which route failed and which route was used next.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/live-route-selection` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Route-fallback logic should be additive and only active on the live CLI/eval path.
- If a live explicit route fails, preserve the transcript of the failed attempt and continue with the shared-route fallback when the error is clearly route-related.
- If the narrow live smoke still fails after the shared-route fallback, preserve the artifact set and record the exact route sequence here instead of reverting the fallback machinery.

## Interfaces and Dependencies

- `Tier1LoopRunner` currently builds its own routing plan; this slice may need an injected routing-plan override for live callers.
- `HermesPromptRoleRunner` in `src/deep_gvr/evaluation.py` is the boundary where live provider/model failures are visible and retryable.
- Evidence records in `src/deep_gvr/contracts.py`, `schemas/evidence.schema.json`, and `templates/evidence_record.template.json` already capture provider/model/routing notes, so actual-route recording can stay within the existing artifact shape.
