# Cross-Model Routing

## Purpose / Big Picture

Implement the decorrelated model strategy so generator and verifier do not share the same default model path when a stronger option is available.

## Branch Strategy

Start from the integration branch and work on `codex/cross-model-routing`. Merge back locally after validation passes.

## Commit Plan

- `implement model routing strategy`
- `add fallback routing and documentation`
- `add routing validation cases`

## Progress

- [ ] Cross-model routing is not implemented.

## Surprises & Discoveries

- None yet.

## Decision Log

- Decision: treat prompt and temperature decorrelation as the documented fallback, not the preferred design.
  Rationale: the architecture depends on independent failure modes when the platform allows it.
  Date/Author: 2026-03-26 / Codex

## Outcomes & Retrospective

Pending implementation.

## Context and Orientation

This plan covers generator, verifier, and reviser model selection, capability-driven fallback behavior, and the evidence trail for which model path was used.

## Plan of Work

Implement a routing layer that prefers distinct providers or models and records the effective path in evidence artifacts.

## Concrete Steps

1. Confirm Hermes routing support through probes.
2. Add the effective model-selection logic.
3. Add tests for preferred and fallback paths.

## Validation and Acceptance

- `python scripts/check_repo.py`
- `python scripts/run_capability_probes.py`
- `python -m unittest discover -s tests -v`

Acceptance: the harness records distinct generator and verifier routes when supported and degrades cleanly otherwise.

## Merge, Push, and Cleanup

Merge locally only after validation passes. Validate the merged result again, push the integrated branch, and delete `codex/cross-model-routing` when it is no longer needed.

## Idempotence and Recovery

Routing decisions must remain deterministic from config plus capability state so runs are reproducible.

## Interfaces and Dependencies

Primary paths: config contract, routing helpers, probe results, and evidence records.
