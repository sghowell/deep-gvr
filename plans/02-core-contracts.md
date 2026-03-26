# Core Contracts

## Purpose / Big Picture

Lock the shared contract vocabulary so prompts, schemas, fixtures, evidence, and code use the same artifact names and shapes.

## Branch Strategy

Start from the integration branch and work on `codex/core-contracts`. Merge back locally after validation passes.

## Commit Plan

- `add contract models and schemas`
- `align templates and prompt references`

## Progress

- [ ] Initial contracts are scaffolded and need expansion during implementation.

## Surprises & Discoveries

- None yet.

## Decision Log

- Decision: define the core contracts before feature logic.
  Rationale: deep-gvr depends on prompt, evidence, and adapter alignment more than framework code volume.
  Date/Author: 2026-03-26 / Codex

## Outcomes & Retrospective

Pending implementation.

## Context and Orientation

The core contracts are `DeepGvrConfig`, `CandidateSolution`, `VerificationReport`, `SimSpec`, `SimResults`, `EvidenceRecord`, `SessionIndex`, and `CapabilityProbeResult`.

## Plan of Work

Refine the Python models, schemas, and templates together. Add tests for roundtrip behavior and alignment.

## Concrete Steps

1. Update dataclasses and schemas together.
2. Keep prompt field names aligned with schemas.
3. Extend fixtures and tests.

## Validation and Acceptance

- `python scripts/check_repo.py`
- `python -m unittest discover -s tests -v`

Acceptance: every template validates against its schema and round-trips through the typed model where applicable.

## Merge, Push, and Cleanup

Merge locally only after validation passes. Validate the merged result again, push the integrated branch, and delete `codex/core-contracts` when it is no longer needed.

## Idempotence and Recovery

Schema and model work is additive. Re-run validation after every shape change.

## Interfaces and Dependencies

Primary paths: `src/deep_gvr/contracts.py`, `schemas/`, `templates/`, `prompts/`.
