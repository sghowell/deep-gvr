# 33 Domain Adapter Expansion

## Purpose / Big Picture

Expand the architecture beyond the current Stim-centric Tier 2 path by implementing the planned non-Stim adapters for FBQC, decoder evaluation, and resource-state optimization. This slice completes the architecture’s claim that domain specialization lives in prompts and adapters rather than in one hard-coded simulator path.

## Branch Strategy

Start from `main` and implement this slice on `codex/domain-adapter-expansion`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result, push `main`, confirm CI, and delete the feature branch.

## Commit Plan

- `add fbqc adapter contracts`
- `add decoder and resource adapters`
- `document domain adapter expansion`

## Progress

- [ ] Add the new plan and index it from `plans/README.md`.
- [ ] Implement FBQC adapter support through the shared simulator boundary.
- [ ] Implement decoder-evaluation and resource-state adapter support.
- [ ] Extend prompts, benchmarks, and docs for the expanded domain surface.

## Surprises & Discoveries

- The repo already carries FBQC domain context, so the main gap is executable adapter support and matching evaluation cases.
- Adapter expansion will require benchmark growth, not only new adapter modules.

## Decision Log

- New adapters must conform to the same simulator contract and evidence rules as Stim.
- Domain-specific prompts and context should stay additive and local to the adapter/domain paths.
- Benchmarks are required for every new adapter family.

## Outcomes & Retrospective

- Pending implementation.

## Context and Orientation

- Domain context: `domain/`
- Current adapter baseline: `adapters/stim_adapter.py`
- Prompt surfaces: `prompts/`
- Architecture ledger item: `domain-adapter-expansion`

## Plan of Work

1. Extend the adapter contracts for FBQC, decoder-evaluation, and resource-state workloads.
2. Implement the new adapters and wire them through the simulator boundary.
3. Add domain prompts, context, and benchmark coverage for the new adapter families.

## Concrete Steps

1. Add the new adapter modules and supporting contracts.
2. Update simulator mediation so the `simulator` field selects the right adapter family.
3. Add prompts, schemas, templates, and benchmark cases for the new domain paths.
4. Add tests and docs that validate the expanded adapter surface.

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Targeted validation:

```bash
uv run python -m unittest tests.test_contracts tests.test_evaluation -v
```

Acceptance evidence:

- FBQC, decoder-evaluation, and resource-state adapters execute through the shared simulator boundary.
- Prompts, contracts, and benchmarks cover the new domain surfaces.
- The adapter architecture is no longer effectively Stim-only.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/domain-adapter-expansion` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Keep adapter additions isolated by domain so partial work does not corrupt the existing Stim path.
- Preserve the shared adapter contract while extending it.
- Do not add a new adapter family without the matching benchmark and docs updates.

## Interfaces and Dependencies

- Depends on the completed backend-dispatch work from plan 28.
- Touches adapter contracts, prompts, domain context, and benchmarks.
- Must keep domain specialization in adapters and prompts rather than in hard-coded loop logic.
