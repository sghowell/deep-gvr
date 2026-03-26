# Evaluation and Release

## Purpose / Big Picture

Turn the readiness scaffold and implementation slices into a release candidate with benchmark evidence and contributor-facing docs.

## Branch Strategy

Start from the integration branch and work on `codex/eval-release`. Merge back locally after validation passes.

## Commit Plan

- `expand benchmark suite`
- `document release and install flow`
- `finalize release checks`

## Progress

- [ ] Release preparation has not started.

## Surprises & Discoveries

- None yet.

## Decision Log

- Decision: benchmark evidence is required before calling the harness implementation-ready for public use.
  Rationale: false-positive verification is the most important failure mode to detect early.
  Date/Author: 2026-03-26 / Codex

## Outcomes & Retrospective

Pending implementation.

## Context and Orientation

This plan expands the benchmark corpus, finalizes docs, and prepares the repo for public release and ongoing maintenance.

## Plan of Work

Build out the evaluation harness, record benchmark results, finalize installation docs, and tighten any remaining release checks.

## Concrete Steps

1. Expand `eval/known_problems.json`.
2. Add benchmark-running support and result recording.
3. Finalize installation and release documentation.

## Validation and Acceptance

- `python scripts/check_repo.py`
- `python scripts/run_capability_probes.py`
- `python -m unittest discover -s tests -v`

Acceptance: the repo includes benchmark evidence, release-facing docs, and a stable readiness baseline.

## Merge, Push, and Cleanup

Merge locally only after validation passes. Validate the merged result again, push the integrated branch, and delete `codex/eval-release` when it is no longer needed.

## Idempotence and Recovery

Benchmark runs should be repeatable and the release docs should remain valid after reruns.

## Interfaces and Dependencies

Primary paths: `eval/`, `README.md`, install scripts, CI, and any release notes or example outputs.
