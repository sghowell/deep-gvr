# Live Harness Evaluation

## Purpose / Big Picture

Add a live evaluation mode that runs the actual generator, verifier, and reviser prompt stack against the benchmark corpus, records real case artifacts separately from the deterministic release baseline, and makes prompt-quality evidence part of the harness workflow.

## Branch Strategy

Start from the integration branch and work on `codex/live-eval`. Merge back locally into `main` only after validation passes.

## Commit Plan

- `add live evaluation mode`
- `record live benchmark artifacts`
- `document live evaluation workflow`

## Progress

- [x] The deterministic fixture-backed release benchmark exists in `eval/`.
- [ ] Live prompt-driven benchmark execution is not implemented.
- [ ] No real benchmark artifacts are recorded for prompt behavior, routing choices, or tier outcomes.
- [ ] The Hermes-facing command path in `SKILL.md` remains scaffolded.

## Surprises & Discoveries

- The release benchmark added in `plans/07-eval-release.md` is intentionally deterministic and fixture-backed, so it is useful for repo readiness but not for measuring real prompt behavior.
- The current evaluation runner already has a stable corpus, metric vocabulary, and output structure, which means the next slice should extend that surface instead of creating a second benchmark tool.

## Decision Log

- Decision: keep deterministic baseline results as the CI-safe release floor, and store live benchmark runs as separate artifacts instead of replacing the committed baseline.
  Rationale: CI needs repeatable, cost-free evidence, while live evaluation needs real model calls and environment-specific metadata.
  Date/Author: 2026-03-26 / Codex
- Decision: record run configuration, routing state, enabled tiers, and artifact locations with every live benchmark result.
  Rationale: live prompt behavior is only interpretable if the exact execution context is reproducible.
  Date/Author: 2026-03-26 / Codex
- Decision: extend `eval/run_eval.py` with a live mode instead of introducing a parallel evaluation entrypoint.
  Rationale: one runner with explicit modes keeps docs, tests, and operator workflow aligned.
  Date/Author: 2026-03-26 / Codex

## Outcomes & Retrospective

Pending implementation.

## Context and Orientation

The repo now has a deterministic benchmark runner in `eval/run_eval.py`, a benchmark corpus in `eval/known_problems.json`, committed baseline results in `eval/results/baseline_results.json`, routing evidence in the Tier 1 loop, and release helpers in `scripts/`. What is still missing is real execution of the prompt stack and harness flow against that corpus.

This plan covers live benchmark execution, run artifact recording, prompt-quality metrics, and the repo-local workflow for running those evaluations safely and repeatably.

## Plan of Work

Extend the existing evaluation harness so it can run in `deterministic` and `live` modes, persist full live-run artifacts under `eval/results/`, and document how contributors should execute and interpret live benchmark runs.

## Concrete Steps

1. Extend the evaluation contracts and runner configuration to represent `deterministic` versus `live` execution, run metadata, and output locations.
2. Add a live execution path in `eval/run_eval.py` and `src/deep_gvr/evaluation.py` that uses the real loop, prompts, routing plan, and enabled verification tiers instead of fixture agents.
3. Record per-case live artifacts such as candidate outputs, verification reports, evidence excerpts, simulation/formal mediation artifacts, final verdicts, and run metadata under a timestamped `eval/results/live/` directory.
4. Preserve the deterministic baseline as-is, and ensure live runs never overwrite `eval/results/baseline_results.json` unless explicitly requested.
5. Add tests for runner mode selection, live-result metadata, artifact path handling, and deterministic/live separation.
6. Update `README.md`, `eval/README.md`, `SKILL.md`, and any local docs needed to explain prerequisites, runtime/cost expectations, and the meaning of live benchmark metrics.

## Validation and Acceptance

- `python scripts/check_repo.py`
- `python scripts/run_capability_probes.py`
- `python -m unittest discover -s tests -v`
- `python eval/run_eval.py --routing-probe fallback --output /tmp/deep-gvr-eval-results.json`
- A documented live benchmark smoke command that writes to a timestamped `eval/results/live/` path without touching the deterministic baseline

Acceptance:
- The evaluation runner supports explicit deterministic and live modes.
- A live run records reproducible metadata, per-case artifacts, and aggregate metrics.
- Deterministic baseline behavior remains unchanged and still passes the repo release checks.
- Repo docs clearly distinguish deterministic readiness evidence from live prompt-quality evidence.

## Merge, Push, and Cleanup

Merge locally only after validation passes. Validate the merged result again, push the integrated branch, confirm CI, and delete `codex/live-eval` when it is no longer needed.

## Idempotence and Recovery

Deterministic runs must remain stable from committed fixtures. Live runs must default to timestamped output directories so reruns append evidence instead of overwriting prior results. If a live run is interrupted, rerunning should create a fresh result directory or explicitly resume from a documented checkpoint path.

## Interfaces and Dependencies

Primary paths: `eval/run_eval.py`, `eval/known_problems.json`, `eval/results/`, `src/deep_gvr/evaluation.py`, `src/deep_gvr/tier1.py`, routing and evidence contracts, `prompts/`, `SKILL.md`, and release/operator docs in `README.md` and `eval/README.md`.
