# 27 Formal Proof Lifecycle

## Purpose / Big Picture

Extend Tier 3 from a single bounded proof attempt into a full proof lifecycle: submission, polling, checkpointed resume, and long-running completion. This slice aligns the formal path with the architecture’s expectation that proofs may outlive one command timeout and must survive resume boundaries.

## Branch Strategy

Start from `main` and implement this slice on `codex/formal-proof-lifecycle`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result, push `main`, confirm CI, and delete the feature branch.

## Commit Plan

- `add proof lifecycle contracts`
- `wire proof polling and resume`
- `document formal lifecycle`

## Progress

- [ ] Add the new plan and index it from `plans/README.md`.
- [ ] Extend the formal contracts to represent proof handles, polling state, and terminal results.
- [ ] Persist proof lifecycle artifacts and integrate them into checkpoint/resume.
- [ ] Add runtime logic for submission, polling, timeout, and restart-safe completion.
- [ ] Validate the new Tier 3 lifecycle on live proof cases.

## Surprises & Discoveries

- The repo already persists useful formal request and transport artifacts, which should become the basis for the new lifecycle state rather than being replaced.
- The biggest missing feature is not proof content; it is proof state management across time and resumes.

## Decision Log

- Proof state becomes a first-class session artifact.
- Resume must continue outstanding proofs instead of re-submitting them blindly.
- Timeout must distinguish “proof still running” from “proof failed.”

## Outcomes & Retrospective

- Pending implementation.

## Context and Orientation

- Current formal runtime: `src/deep_gvr/formal.py`
- Current Tier 1 integration: `src/deep_gvr/tier1.py`
- Current formal benchmark cases: `eval/known_problems.json`
- Architecture ledger item: `formal-proof-lifecycle`

## Plan of Work

1. Expand the formal contracts to represent multi-step proof state.
2. Persist that state under the existing session artifact structure.
3. Update resume logic to poll or continue existing proof attempts.
4. Update benchmarks and docs so Tier 3 completion expectations match the new lifecycle.

## Concrete Steps

1. Add proof lifecycle fields and artifacts in the formal contracts and schemas.
2. Update `src/deep_gvr/formal.py` to support submission and polling steps.
3. Update `src/deep_gvr/tier1.py` so formal state survives checkpoints and resume.
4. Add tests for submission, polling, terminal success, timeout, resume, and retry semantics.
5. Update operator docs and benchmark expectations.

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Targeted validation:

```bash
uv run python -m unittest tests.test_formal tests.test_tier1_loop -v
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --case-id formal-proved-repetition-majority --prompt-profile compact
```

Acceptance evidence:

- Tier 3 proof attempts persist submission and polling state.
- Resume can continue a pending proof attempt without losing state.
- Benchmarks can distinguish pending proof work from genuine proof failure.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/formal-proof-lifecycle` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Proof lifecycle artifacts must be append-only or safely replaceable by monotonic state transitions.
- Resume must be safe to re-run after partial proof polling.
- Keep old completed proof artifacts readable while adding the new lifecycle structure.

## Interfaces and Dependencies

- Depends on the Tier 3 transport path and the checkpoint/resume machinery.
- Extends formal artifacts, Tier 3 results, and benchmark case expectations.
- Must remain compatible with the delegated runtime and the eventual verifier-direct Tier 3 path.
