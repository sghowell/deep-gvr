# Repo Bootstrap Readiness

## Purpose / Big Picture

Bootstrap the repository so later feature work starts from explicit rules, contracts, prompts, schemas, tests, and CI instead of ad hoc chat context.

## Branch Strategy

Start from the integration branch and work on `codex/repo-bootstrap`. Merge back locally after validation passes.

## Commit Plan

- `bootstrap repo policy docs`
- `add readiness scaffolding and checks`
- `wire ci and tests`

## Progress

- [ ] Bootstrap branch has not yet been fully validated end-to-end.

## Surprises & Discoveries

- None yet. Update this section as implementation proceeds.

## Decision Log

- Decision: make the repo self-validating with stdlib-only checks.
  Rationale: readiness work should not depend on optional third-party tooling to prove basic consistency.
  Date/Author: 2026-03-26 / Codex

## Outcomes & Retrospective

Pending implementation.

## Context and Orientation

This plan sets up the operating model, docs, package skeleton, schemas, fixtures, scripts, tests, and CI required for all subsequent plans.

## Plan of Work

Create the root governance docs, scaffold the Python package and adapter directories, add prompts and fixtures, then add tests and CI that enforce the readiness rules.

## Concrete Steps

1. Create the repo structure and policy docs.
2. Add typed contracts, schemas, prompts, fixtures, and probes.
3. Add tests and CI.
4. Run repo checks, probes, and unit tests.

## Validation and Acceptance

- `python scripts/check_repo.py`
- `python scripts/run_capability_probes.py`
- `python -m unittest discover -s tests -v`

Acceptance: all readiness checks pass and the repo contains the expected scaffold.

## Merge, Push, and Cleanup

Merge locally only after validation passes. Validate the merged result again, push the integrated branch, and delete `codex/repo-bootstrap` when it is no longer needed.

## Idempotence and Recovery

All steps are additive. Re-running the checks is safe. If a doc or schema falls out of sync, update the source files and re-run validation.

## Interfaces and Dependencies

Use Python 3.12, `uv`, stdlib tests, and the repo-local schemas and prompts as the initial dependency surface.
