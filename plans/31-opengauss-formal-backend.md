# 31 OpenGauss Formal Backend

## Purpose / Big Picture

Implement OpenGauss as the interactive formal backend promised by the architecture, alongside Aristotle as the primary default backend. This slice is the phase-2 formal expansion that supports project-scoped or iterative proof work rather than only single-shot Aristotle transport.

## Branch Strategy

Start from `main` and implement this slice on `codex/opengauss-formal-backend`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result, push `main`, confirm CI, and delete the feature branch.

## Commit Plan

- `add opengauss backend contracts`
- `wire opengauss transport`
- `document interactive formal backend`

## Progress

- [ ] Add the new plan and index it from `plans/README.md`.
- [ ] Add backend selection and contracts for OpenGauss.
- [ ] Implement the OpenGauss transport and operator workflow.
- [ ] Extend docs, tests, and benchmarks for the new formal backend.

## Surprises & Discoveries

- OpenGauss is a distinct operator flow from Aristotle, so this slice needs backend-specific setup and lifecycle docs, not just another enum value.
- The benchmark suite should include at least one case that benefits from interactive/project-scoped proof work.

## Decision Log

- Aristotle remains the primary default formal backend unless a case or config selects OpenGauss explicitly.
- OpenGauss must reuse the same Tier 3 result contracts where possible.
- Backend choice must be explicit in evidence and benchmark artifacts.

## Outcomes & Retrospective

- Pending implementation.

## Context and Orientation

- Formal runtime: `src/deep_gvr/formal.py`
- Tier 3 contracts: `src/deep_gvr/contracts.py`
- Architecture ledger item: `opengauss-formal-backend`

## Plan of Work

1. Add formal backend selection and contracts for OpenGauss.
2. Implement transport and operator setup for OpenGauss.
3. Extend benchmarks, docs, and evidence artifacts for multi-backend Tier 3 work.

## Concrete Steps

1. Extend formal backend configuration and contracts to include OpenGauss.
2. Add the OpenGauss transport boundary and lifecycle integration.
3. Update prompts, docs, and operator setup for OpenGauss-backed proof work.
4. Add tests and benchmark cases that exercise the new backend.

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Targeted validation:

```bash
uv run python -m unittest tests.test_formal tests.test_contracts -v
```

Acceptance evidence:

- OpenGauss is selectable as a real Tier 3 backend.
- Evidence and benchmark artifacts identify which formal backend ran.
- Operator docs cover both Aristotle and OpenGauss flows accurately.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/opengauss-formal-backend` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Keep Aristotle as the stable default while OpenGauss integration is being added.
- Reuse existing Tier 3 artifact shapes where possible.
- If the external OpenGauss environment is not ready, keep the slice open rather than weakening the target.

## Interfaces and Dependencies

- Depends on the completed formal lifecycle work from plan 27.
- Touches formal backend contracts, transport code, docs, and benchmark cases.
- Requires external OpenGauss environment and operator setup.
