# Tier 1 Loop

## Purpose / Big Picture

Implement the first working generator-verifier-reviser loop with analytical verification and evidence recording.

## Branch Strategy

Start from the integration branch and work on `codex/tier1-loop`. Merge back locally after validation passes.

## Commit Plan

- `implement orchestrator session setup`
- `add tier1 verifier flow and evidence recording`
- `add tier1 acceptance tests`

## Progress

- [ ] Tier 1 loop is planned but not implemented.

## Surprises & Discoveries

- None yet.

## Decision Log

- Decision: ship the analytical loop before simulator or formal integration.
  Rationale: Tier 1 is mandatory and defines the baseline harness behavior.
  Date/Author: 2026-03-26 / Codex

## Outcomes & Retrospective

Pending implementation.

## Context and Orientation

This plan covers the first working `deep-gvr` session lifecycle: intake, grounding, generation, verification, revision, evidence logging, and resume-safe checkpoints.

## Plan of Work

Implement the orchestrator logic in the skill scaffold and supporting Python helpers, keeping the verifier isolated from the original problem statement.

## Concrete Steps

1. Implement session initialization and evidence file creation.
2. Implement generator, verifier, and reviser orchestration for Tier 1.
3. Add tests for verdict handling, revision looping, and failure admission.

## Validation and Acceptance

- `python scripts/check_repo.py`
- `python scripts/run_capability_probes.py`
- `python -m unittest discover -s tests -v`

Acceptance: the harness can execute a Tier 1-only research loop and record append-only evidence.

## Merge, Push, and Cleanup

Merge locally only after validation passes. Validate the merged result again, push the integrated branch, and delete `codex/tier1-loop` when it is no longer needed.

## Idempotence and Recovery

Resume must start from the last complete checkpoint. Partial runs should not corrupt prior evidence records.

## Interfaces and Dependencies

Primary paths: `SKILL.md`, `prompts/generator.md`, `prompts/verifier.md`, `prompts/reviser.md`, evidence artifacts, and session helpers.
