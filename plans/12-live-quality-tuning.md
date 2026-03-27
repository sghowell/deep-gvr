# Live Prompt Quality Tuning

## Purpose / Big Picture

Improve the throughput and reliability of real live runs by adding an explicit prompt-profile tuning surface for Hermes-backed execution, shrinking live query payloads by default, and documenting how to use the compact path for benchmark and CLI runs.

## Branch Strategy

Start from `main` and implement this slice on `codex/live-quality-tuning`. Merge back locally into `main` only after validation passes.

## Commit Plan

- `add live quality tuning plan`
- `add compact live prompt profile`
- `document live prompt tuning workflow`

## Progress

- [x] The new live-quality-tuning plan has been added.
- [x] Live execution supports an explicit prompt profile instead of one fixed verbose query shape.
- [x] The compact prompt profile is wired through both the live benchmark runner and the `deep-gvr` CLI path.
- [x] Tests prove the compact profile emits a smaller query while preserving the JSON contract shape.
- [x] Docs and operator guidance explain when to use `compact` versus `full`.

## Surprises & Discoveries

- The live prompts themselves are not unusually large, but the runtime scaffolding around them repeats JSON contracts and payloads with pretty-print formatting, which inflates token count for every Hermes role call.
- The current live benchmark timeout evidence shows that end-to-end failures can happen before Tier 3, so prompt/runtime tuning needs to cover generator and verifier calls, not only the formal boundary.
- Hermes exposes toolset and model selection flags, but the cleanest immediate throughput lever inside the repo is prompt-shape reduction because it requires no Hermes changes and no user-global config edits.
- In the local transcript comparison, the compact generator query was about 200 characters shorter than the older full-profile live query, but the current Hermes default route still timed out at 20 to 30 seconds on simple known-correct cases.

## Decision Log

- Decision: introduce prompt profiles in the repo-local live runtime instead of editing the static prompt markdown files for benchmark-specific brevity.
  Rationale: the base prompts should stay readable and role-focused, while runtime tuning for live throughput is an execution concern.
  Date/Author: 2026-03-26 / Codex
- Decision: make `compact` the default profile for live execution surfaces.
  Rationale: live benchmark and CLI runs benefit from shorter queries by default, and operators can still opt into `full` when debugging prompt behavior.
  Date/Author: 2026-03-26 / Codex

## Outcomes & Retrospective

This slice leaves the repo with a documented, testable prompt-tuning lever for live runs, smaller Hermes query payloads by default, and operator guidance for switching between compact and full prompt scaffolding. The compact profile now shortens live Hermes queries measurably, but the observed local smokes still timed out in the generator on the current `configured-by-hermes` default route, which means the next live-quality lever is model routing or timeout policy rather than additional prompt framing changes alone.

## Context and Orientation

The repo already has:

- Live benchmark execution in `eval/run_eval.py` and `src/deep_gvr/evaluation.py`
- A shared Hermes role runner used by the benchmark path and the `deep-gvr` CLI
- A live Aristotle transport path in `src/deep_gvr/formal.py`
- Prompt files in `prompts/`
- Recorded live timeout artifacts showing that the current end-to-end path can stall before verification completes

What is still missing is a repo-local way to tune live prompt verbosity without hand-editing prompt files or mutating the global Hermes config.

## Plan of Work

Add prompt-profile selection to the shared live execution helpers, use a smaller compact query shape by default for Hermes-backed runs, pass that profile through CLI and eval entrypoints, and update tests/docs to match.

## Concrete Steps

1. Add the new plan to `plans/` and index it from `plans/README.md`.
2. Extend the shared live execution config in `src/deep_gvr/evaluation.py` with a prompt-profile setting.
3. Add a compact query builder path for generator, verifier, reviser, and formalizer calls that preserves the same JSON contract but uses tighter scaffolding and compact JSON serialization.
4. Thread prompt-profile selection through `src/deep_gvr/cli.py` and `eval/run_eval.py`.
5. Add tests covering compact versus full query construction and CLI/eval wiring.
6. Update `README.md`, `SKILL.md`, `eval/README.md`, and the new plan with the tuning workflow.
7. Run targeted live smokes with the compact profile and inspect the recorded artifacts.

## Validation and Acceptance

- `python scripts/check_repo.py`
- `python scripts/run_capability_probes.py`
- `python -m unittest discover -s tests -v`
- `python eval/run_eval.py --mode live --routing-probe fallback --case-id known-correct-surface-threshold --prompt-profile compact --command-timeout-seconds 20`
- `python -m deep_gvr.cli run "Explain why the surface code has a threshold." --prompt-profile compact --command-timeout-seconds 20`

Acceptance:

- Live execution surfaces expose `compact` and `full` prompt profiles.
- The compact profile produces a materially shorter Hermes query than the full profile while keeping the same JSON response contract.
- The CLI and eval runner both use the shared prompt-profile mechanism.
- Docs explain the compact profile as the default live path and `full` as the debugging path.

## Merge, Push, and Cleanup

Merge locally only after validation passes. Validate the merged result again, push the integrated branch, confirm CI, and delete `codex/live-quality-tuning` when it is no longer needed.

## Idempotence and Recovery

Switching prompt profiles must not change artifact shapes, only the live query scaffolding. If a compact-profile live run still times out, rerunning with `--prompt-profile full` should remain available as a debugging fallback without requiring code changes.

## Interfaces and Dependencies

Primary paths: `src/deep_gvr/evaluation.py`, `src/deep_gvr/formal.py`, `src/deep_gvr/cli.py`, `eval/run_eval.py`, `prompts/`, `tests/test_evaluation.py`, `tests/test_formal.py`, `tests/test_cli.py`, `README.md`, `SKILL.md`, `eval/README.md`, and `plans/README.md`.
