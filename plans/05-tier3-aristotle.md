# Tier 3 Aristotle Integration

## Purpose / Big Picture

Implement formal verification routing for formalizable claims using Aristotle first and graceful degradation when unavailable.

## Branch Strategy

Start from the integration branch and work on `codex/tier3-aristotle`. Merge back locally after validation passes.

## Commit Plan

- `add aristotle verification mediation`
- `record formal verification artifacts`
- `add tier3 tests and fallbacks`

## Progress

- [x] Tier 3 mediation is implemented in the loop runner with formal request/results artifact persistence.
- [x] The default Aristotle runner returns structured unavailable results when transport is not wired.
- [x] Tests cover proof success, timeout mapping, and unavailable-service fallback.

## Surprises & Discoveries

- The repo environment already exposes `ARISTOTLE_API_KEY`, so tests needed to control the environment explicitly instead of assuming the key was absent.
- Without a repo-local Hermes MCP transport API, the most reliable v0.1 slice is a mediated Aristotle boundary plus injected executor support for success and timeout paths.

## Decision Log

- Decision: use Aristotle as the first Tier 3 backend.
  Rationale: it avoids requiring a local Lean toolchain for the initial version.
  Date/Author: 2026-03-26 / Codex
- Decision: implement a default Aristotle runner that emits structured `unavailable` results until a transport is wired.
  Rationale: the plan requires graceful degradation now, while leaving a clean seam for future Hermes MCP integration.
  Date/Author: 2026-03-26 / Codex

## Outcomes & Retrospective

The repo now supports formal-verification mediation end to end: the verifier can request formal checks, the orchestrator persists the request and returned results, the default Aristotle runner degrades gracefully when transport is unavailable, and reverification can consume proof success, timeout, or unavailable outcomes without changing the verifier contract.

## Context and Orientation

This plan covers formalizable-claim detection, proof submission, timeout handling, artifact capture, and verifier integration.

## Plan of Work

Implement direct verifier access if MCP inheritance is supported; otherwise mediate through the orchestrator without changing the verifier contract.

## Concrete Steps

1. Resolve the MCP inheritance path through the capability probes.
2. Implement Aristotle request and response handling.
3. Add timeout, unavailable-service, and proof-failure tests.

## Validation and Acceptance

- `python scripts/check_repo.py`
- `python scripts/run_capability_probes.py`
- `python -m unittest discover -s tests -v`

Acceptance: formalizable claims produce either formal verification output or an explicit structured fallback.

## Merge, Push, and Cleanup

Merge locally only after validation passes. Validate the merged result again, push the integrated branch, and delete `codex/tier3-aristotle` when it is no longer needed.

## Idempotence and Recovery

Long-running proof attempts must be restartable from persisted artifacts or safely timed out.

## Interfaces and Dependencies

Primary paths: verifier logic, Aristotle integration code, evidence artifacts, and Tier 3 schema-aligned outputs.
