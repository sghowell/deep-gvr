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

- [x] Expanded the benchmark corpus across Tier 1, Tier 2, and Tier 3 cases.
- [x] Added a deterministic evaluation runner plus committed baseline results.
- [x] Replaced the install and MCP setup placeholders with usable release helpers.
- [x] Added benchmark validation to CI and repo checks.
- [ ] Run full branch validation, merge locally, push, confirm CI, and clean up.

## Surprises & Discoveries

- The release benchmark needed to use deterministic fixture agents instead of live Hermes calls so the baseline remains repeatable in CI and on contributor machines.
- Recording the benchmark baseline as a committed artifact required schema validation and a stable, repo-relative suite path to avoid machine-specific drift.

## Decision Log

- Decision: benchmark evidence is required before calling the harness implementation-ready for public use.
  Rationale: false-positive verification is the most important failure mode to detect early.
  Date/Author: 2026-03-26 / Codex

## Outcomes & Retrospective

Implementation is complete; merge and release confirmation steps remain.

## Context and Orientation

This plan expands the benchmark corpus, finalizes docs, and prepares the repo for public release and ongoing maintenance.

## Plan of Work

Build out the evaluation harness, record benchmark results, finalize installation docs, and tighten any remaining release checks.

## Concrete Steps

1. Expand `eval/known_problems.json` to cover analytical, simulation-mediated, and formal-mediation cases.
2. Add a deterministic benchmark runner and commit the generated baseline report under `eval/results/`.
3. Finalize `README.md`, `eval/README.md`, `scripts/install.sh`, and `scripts/setup_mcp.sh`.
4. Add release checks for benchmark smoke, artifact validation, and executable release helpers.

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

Primary paths: `eval/`, `src/deep_gvr/evaluation.py`, benchmark/result schemas and templates, `README.md`, install/setup scripts, CI, and release validation checks.
