# 16 Live Verifier Throughput

## Purpose / Big Picture

Reduce live verifier latency on the real Hermes path without weakening the harness. The current live artifacts show that the verifier completed when its compact query was about 6.9k characters, but timed out after the shared domain-context slice pushed the verifier query above 8k characters. This slice should keep the same adversarial verification behavior while making the compact live verifier request materially smaller and more targeted.

## Branch Strategy

Start from `main` and implement this slice on `codex/live-verifier-throughput`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result, push `main`, confirm CI, and delete the feature branch.

## Commit Plan

- `add live verifier throughput plan`
- `compact live verifier request path`
- `document live verifier compact path`

## Progress

- [ ] Added the new plan and indexed it from `plans/README.md`.
- [ ] Added a verifier-specific compact live query builder that trims prompt and contract overhead without changing the runtime contract shape.
- [ ] Reduced verifier payload noise in compact mode while keeping the parser-compatible verification report structure.
- [ ] Added tests that prove the compact verifier query is smaller than the current generic compact form and still parses into a `VerificationReport`.
- [ ] Re-ran a narrow live smoke and recorded whether verifier throughput improved on the real route.

## Surprises & Discoveries

- `/tmp/deep-gvr-live-runtime-policy-2/cases/known-correct-surface-threshold/role_transcripts.json` shows a successful verifier run with a query length of about 6928 characters.
- `/tmp/deep-gvr-live-domain-context-2/cases/known-correct-surface-threshold/role_transcripts.json` shows the verifier timing out after the compact query grew to about 8161 characters.
- The added domain context improved generator quality, but the resulting longer candidate artifact now pushes the verifier query past the apparent throughput cliff on the default route.

## Decision Log

- Prefer a verifier-specific compact query path before changing global runtime defaults again. The evidence points to verifier prompt/payload size more than control-flow failure.
- Keep the formal parser contract stable. The compact prompt may describe optional fields more tightly, but the runtime should continue producing the same `VerificationReport` structure after JSON parsing.
- Treat live smoke evidence as required acceptance for this slice, because the timeout problem only appears on the real Hermes path.

## Outcomes & Retrospective

This slice should leave the repo with a smaller verifier-specific compact live request path, new tests around the compact verifier builder, and at least one fresh live artifact that shows whether verifier throughput improved. If the verifier still times out after the request is narrowed, the next slice should move to route selection or timeout policy rather than more prompt reshaping.

## Context and Orientation

- Runtime path: `src/deep_gvr/evaluation.py`
- Prompt shaping: `src/deep_gvr/prompt_profiles.py`
- Live runtime defaults: `src/deep_gvr/live_runtime.py`
- Verifier prompt: `prompts/verifier.md`
- Live smoke evidence:
  - `/tmp/deep-gvr-live-runtime-policy-2/cases/known-correct-surface-threshold/role_transcripts.json`
  - `/tmp/deep-gvr-live-domain-context-2/cases/known-correct-surface-threshold/role_transcripts.json`

## Plan of Work

1. Add a verifier-specific compact query builder in `src/deep_gvr/prompt_profiles.py`.
2. Wire the live verifier path to use the compact verifier builder while keeping full profile behavior unchanged.
3. Trim optional verifier prompt/contract text and payload noise that do not help the initial live pass.
4. Add targeted tests for query length and parser compatibility.
5. Re-run a narrow live smoke on the same benchmark case and capture the outcome in this plan and the docs.

## Concrete Steps

1. Add `plans/16-live-verifier-throughput.md` and index it from `plans/README.md`.
2. Update `src/deep_gvr/prompt_profiles.py` with a compact verifier query path and any helper functions needed to keep the builder readable.
3. Update `src/deep_gvr/evaluation.py` only where necessary so the verifier role uses the new compact path in live mode.
4. Update `tests/test_evaluation.py` to cover the smaller verifier query and successful report parsing under the compact verifier path.
5. If the runtime behavior changes in a stable way, update the minimal docs in `README.md`, `SKILL.md`, `eval/README.md`, and `docs/system-overview.md`.
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
uv run python -m unittest tests.test_evaluation tests.test_cli -v
```

Acceptance evidence:

- A targeted test proves the compact verifier query is shorter than the previous generic compact form.
- Live verifier JSON still parses into `VerificationReport`.
- A fresh live smoke on `known-correct-surface-threshold` either completes verifier successfully or records a materially smaller verifier query in the transcript for the next slice.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/live-verifier-throughput` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- The prompt-profile changes should be additive and local to live compact execution. Re-running the branch work should not mutate committed benchmark baselines.
- If the live smoke still times out, preserve the new transcript artifact and record the measured verifier query size in this plan instead of reverting the narrowing work.
- If a compact verifier response omits optional fields, keep `VerificationReport.from_dict` compatibility by treating those fields as optional rather than forcing prompt verbosity back up.

## Interfaces and Dependencies

- `HermesPromptRoleRunner` in `src/deep_gvr/evaluation.py` depends on `build_live_role_query(...)`.
- `VerificationReport.from_dict(...)` in `src/deep_gvr/contracts.py` already tolerates omitted optional fields such as `tier2` and `tier3`.
- The live benchmark documentation in `eval/README.md` and `README.md` should continue to describe `compact` as the default live profile.
