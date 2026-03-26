# Tier 2 Stim Integration

## Purpose / Big Picture

Implement empirical verification through the simulator boundary using the Stim adapter first.

## Branch Strategy

Start from the integration branch and work on `codex/tier2-stim`. Merge back locally after validation passes.

## Commit Plan

- `implement stim adapter local backend`
- `wire simulator mediation through orchestrator`
- `add empirical verification tests`

## Progress

- [ ] Stim adapter is currently a scaffold only.

## Surprises & Discoveries

- None yet.

## Decision Log

- Decision: Stim is the first empirical backend.
  Rationale: it covers the initial QEC benchmark surface with a well-known simulator.
  Date/Author: 2026-03-26 / Codex

## Outcomes & Retrospective

Pending implementation.

## Context and Orientation

This plan turns quantitative verifier requests into simulator runs and feeds normalized results back into verification.

## Plan of Work

Replace the adapter scaffold with a real local Stim path, then add environment-sensitive Modal and SSH dispatch handling without changing the prompt contract.

## Concrete Steps

1. Implement Stim local execution and output normalization.
2. Wire the orchestrator mediation loop.
3. Add smoke tests and benchmark cases.

## Validation and Acceptance

- `python scripts/check_repo.py`
- `python scripts/run_capability_probes.py`
- `python -m unittest discover -s tests -v`

Acceptance: a quantitative claim triggers simulation, results are normalized, and the verifier incorporates them into its verdict.

## Merge, Push, and Cleanup

Merge locally only after validation passes. Validate the merged result again, push the integrated branch, and delete `codex/tier2-stim` when it is no longer needed.

## Idempotence and Recovery

Failed simulator runs must return structured errors rather than partial artifact corruption.

## Interfaces and Dependencies

Primary paths: `adapters/stim_adapter.py`, `prompts/simulator.md`, `schemas/sim_spec.schema.json`, `schemas/sim_results.schema.json`.
