# 28 Remote Backend Completion

## Purpose / Big Picture

Finish the Tier 2 backend-dispatch architecture by implementing real Modal and SSH execution, validating backend readiness, and extending benchmark coverage beyond the local Stim path. The architecture calls for local, Modal, and SSH support; this slice closes that gap.

## Branch Strategy

Start from `main` and implement this slice on `codex/remote-backend-completion`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result, push `main`, confirm CI, and delete the feature branch.

## Commit Plan

- `implement modal stim backend`
- `implement ssh stim backend`
- `add remote backend validation`

## Progress

- [ ] Add the new plan and index it from `plans/README.md`.
- [ ] Implement Modal execution in the Stim adapter.
- [ ] Implement SSH execution in the Stim adapter.
- [ ] Add backend readiness validation and benchmark coverage.
- [ ] Update docs and operator workflows for all supported backends.

## Surprises & Discoveries

- The adapter boundary is already the right place for this work; the main missing pieces are concrete execution plumbing and environment-sensitive readiness checks.
- Backend completion should be coupled to benchmark evidence so “supported” means exercised, not merely callable.

## Decision Log

- Local, Modal, and SSH must share the same normalized adapter contract.
- Backend readiness should be explicit and testable.
- Unsupported backends should disappear from the supported surface once completion lands; they should not remain as permanent “unavailable” runtime paths.

## Outcomes & Retrospective

- Pending implementation.

## Context and Orientation

- Adapter contracts: `adapters/base_adapter.py`
- Current Stim path: `adapters/stim_adapter.py`
- Capability probe: `src/deep_gvr/probes.py`
- Architecture ledger item: `remote-backend-completion`

## Plan of Work

1. Implement real Modal execution in the Stim adapter.
2. Implement real SSH execution in the Stim adapter.
3. Add readiness validation and benchmark coverage for all supported backends.
4. Update docs and operator setup to reflect the completed backend surface.

## Concrete Steps

1. Extend `adapters/stim_adapter.py` and supporting stubs/scripts for Modal execution.
2. Extend `adapters/stim_adapter.py` for SSH execution, including spec shipping and result retrieval.
3. Update capability probes and repo docs to reflect backend readiness.
4. Add tests for local, Modal, and SSH backend selection plus failure handling.
5. Add benchmark or smoke coverage that exercises the remote backends in appropriate environments.

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Targeted validation:

```bash
uv run python -m unittest tests.test_stim_adapter tests.test_tier1_loop -v
uv run python scripts/run_capability_probes.py
```

Acceptance evidence:

- Modal and SSH execute real Stim-backed simulations through the shared adapter contract.
- Backend readiness checks report the actual supported state for all three backends.
- Benchmarks or smoke tests cover the completed remote backends.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/remote-backend-completion` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Keep backend implementations behind the existing adapter interface so retries do not change the public contracts.
- Preserve normalized result shapes across backends.
- If one remote backend is blocked externally, keep the plan item open and document the blocker rather than shipping that backend as permanently unavailable.

## Interfaces and Dependencies

- Depends on the existing adapter CLI/contract and Tier 2 mediation flow.
- Touches `adapters/stim_adapter.py`, capability probes, and backend-oriented docs.
- Requires environment-specific validation for Modal and SSH.
