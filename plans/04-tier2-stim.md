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

- [x] Stim local execution and output normalization are implemented with Stim plus PyMatching.
- [x] The loop runner mediates verifier-requested simulation through persisted spec/results artifacts.
- [x] Tests cover local adapter execution, unsupported backends, and verifier -> simulator -> verifier flow.

## Surprises & Discoveries

- The Python Stim API was a better fit than relying on a `stim` CLI binary, because the package exposes generated circuits and detector sampling directly.
- Tier 2 mediation fit cleanly into the existing checkpoint/evidence model by adding a `simulate` phase and artifact writes, without changing the verifier isolation boundary.

## Decision Log

- Decision: Stim is the first empirical backend.
  Rationale: it covers the initial QEC benchmark surface with a well-known simulator.
  Date/Author: 2026-03-26 / Codex
- Decision: use Stim's Python API with PyMatching decoding for the local backend.
  Rationale: it keeps the adapter self-contained, testable in CI, and independent of a separate system-level CLI install.
  Date/Author: 2026-03-26 / Codex

## Outcomes & Retrospective

The repo now has a working Tier 2 baseline: the Stim adapter executes local rotated-memory surface-code experiments, normalizes results, and the loop runner can mediate a quantitative verifier request by running simulation and passing the results back into verification.

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
