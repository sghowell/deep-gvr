# Capability Probes

## Purpose / Big Picture

Turn the P0 architecture unknowns into explicit implementation probes with defaults, fallbacks, and evidence capture.

## Branch Strategy

Start from the integration branch and work on `codex/capability-probes`. Merge back locally after validation passes.

## Commit Plan

- `add hermes capability probe harness`
- `record probe outcomes and fallbacks`

## Progress

- [ ] Probe harness is scaffolded but not yet deepened with Hermes-specific runtime evidence.

## Surprises & Discoveries

- None yet. Update during real probe work.

## Decision Log

- Decision: default to safe fallbacks until Hermes capabilities are explicitly proven.
  Rationale: the verifier loop must remain implementable even if model routing or MCP inheritance is unavailable.
  Date/Author: 2026-03-26 / Codex

## Outcomes & Retrospective

Pending implementation.

## Context and Orientation

This plan covers per-subagent model routing, MCP inheritance, session resume mechanics, and backend dispatch assumptions.

## Plan of Work

Extend the probe scripts to gather runtime evidence from Hermes, record outcomes in docs, and promote the chosen default behavior into implementation constraints.

## Concrete Steps

1. Add Hermes-aware checks for each P0 unknown.
2. Record evidence and chosen fallbacks.
3. Update docs and tests to reflect the outcome.

## Validation and Acceptance

- `python scripts/run_capability_probes.py`
- `python scripts/check_repo.py`
- `python -m unittest discover -s tests -v`

Acceptance: each P0 unknown has a documented status, preferred outcome, and fallback path.

## Merge, Push, and Cleanup

Merge locally only after validation passes. Validate the merged result again, push the integrated branch, and delete `codex/capability-probes` when it is no longer needed.

## Idempotence and Recovery

Probe commands should be safe to re-run. If a capability remains unverified, keep the fallback as the active default.

## Interfaces and Dependencies

Probe outputs use `CapabilityProbeResult` and the capability probe schema and template.
