# Live Route Tuning

## Purpose / Big Picture

Let live benchmark runs use the same repo-local model routing config as the `deep-gvr` CLI instead of always inheriting the default Hermes route, so operators can tune provider/model choice for live evaluation without editing code or mutating the global Hermes defaults.

## Branch Strategy

Start from `main` and implement this slice on `codex/live-route-tuning`. Merge back locally into `main` only after validation passes.

## Commit Plan

- `add live route tuning plan`
- `wire config driven live routing`
- `document live route tuning workflow`

## Progress

- [x] The new live-route-tuning plan has been added.
- [x] The live benchmark runner can load a runtime config file instead of always using the benchmark defaults.
- [x] Live eval preserves benchmark-safe overrides such as evidence directory and single-iteration behavior while honoring configured model routes.
- [x] Tests prove that live eval picks up configured provider/model values from the selected config path.
- [x] Docs explain how CLI and eval now share the same route-tuning surface.

## Surprises & Discoveries

- The CLI already loads `~/.hermes/deep-gvr/config.yaml`, but `eval/run_eval.py` still synthesizes a fresh `DeepGvrConfig`, which means benchmark runs do not benefit from any tuned model routing.
- In fallback routing mode, live eval currently collapses onto the orchestrator route, so the configured `models.orchestrator` path is the main tuning lever in this environment.
- The recent compact-prompt slice reduced query size but did not resolve generator latency, which makes route selection the next practical lever.
- In the local route-tuned smokes, both eval and CLI transcripts showed the explicit configured route `nous/claude-opus-4-6`, but that route still timed out at 20 seconds on the generator, which points to timeout budget or provider/model choice as the remaining operator lever.

## Decision Log

- Decision: reuse the existing repo-local config contract instead of inventing a benchmark-only route override surface.
  Rationale: CLI and eval should interpret the same routing source of truth to avoid drift and duplicated tuning knobs.
  Date/Author: 2026-03-27 / Codex
- Decision: keep benchmark-specific safety overrides limited to evidence location and iteration budget.
  Rationale: live eval still needs reproducible artifact isolation and one-pass benchmark semantics even when it honors the operator's routing config.
  Date/Author: 2026-03-27 / Codex

## Outcomes & Retrospective

This slice leaves the repo with one route-tuning surface for both live session runs and live evaluation. `eval/run_eval.py --config ...` now honors the same routing config as the CLI while still isolating benchmark artifacts under its live output root. In the observed local smokes, the configured route was applied correctly in transcripts and reports, but the chosen `nous/claude-opus-4-6` path still timed out at 20 seconds, so the next lever is selecting a faster configured route or increasing timeout budget rather than further wiring work.

## Context and Orientation

The repo already has:

- Config-driven routing for the `deep-gvr` CLI in `src/deep_gvr/cli.py`
- Deterministic and live benchmark execution in `src/deep_gvr/evaluation.py` and `eval/run_eval.py`
- A routing helper in `src/deep_gvr/routing.py`
- Config schemas and templates in `schemas/` and `templates/`
- Recent live benchmark artifacts showing generator timeouts on the inherited Hermes default route

What is still missing is a way for live evaluation to share the same route-tuning config that the CLI already uses.

## Plan of Work

Add config-path support to the live benchmark runner, derive the live eval routing plan from that config, preserve benchmark-local evidence overrides, and document the shared CLI/eval tuning workflow.

## Concrete Steps

1. Add the new plan to `plans/` and index it from `plans/README.md`.
2. Extend the live benchmark runner so it can load a selected config file and clone its routing settings into the benchmark session config.
3. Keep benchmark-local overrides limited to isolated evidence output and `max_iterations=1`.
4. Thread the config-path option through `eval/run_eval.py`.
5. Add tests that verify live eval uses configured provider/model values.
6. Update `README.md`, `eval/README.md`, `SKILL.md`, and the plan with the route-tuning workflow.
7. Run targeted live smokes with an isolated config that forces a specific route and inspect the recorded transcripts and reports.

## Validation and Acceptance

- `python scripts/check_repo.py`
- `python scripts/run_capability_probes.py`
- `python -m unittest discover -s tests -v`
- `python eval/run_eval.py --mode live --config /tmp/deep-gvr-live-route-config.yaml --routing-probe fallback --case-id known-correct-surface-threshold --command-timeout-seconds 20`
- `python -m deep_gvr.cli run "Explain why the surface code has a threshold." --config /tmp/deep-gvr-live-route-config.yaml --command-timeout-seconds 20`

Acceptance:

- Live eval can load a runtime config file.
- Live eval and CLI honor the same configured model routing fields.
- Benchmark sessions still write to isolated evidence roots and keep single-iteration benchmark behavior.
- Docs explain config-driven route tuning for live execution.

## Merge, Push, and Cleanup

Merge locally only after validation passes. Validate the merged result again, push the integrated branch, confirm CI, and delete `codex/live-route-tuning` when it is no longer needed.

## Idempotence and Recovery

Changing the config path must only affect the live route choice and other config-backed runtime settings, not the benchmark artifact schema. If a tuned route still times out, operators should be able to adjust the same config file and rerun without any code changes.

## Interfaces and Dependencies

Primary paths: `src/deep_gvr/evaluation.py`, `eval/run_eval.py`, `src/deep_gvr/cli.py`, `src/deep_gvr/routing.py`, `src/deep_gvr/contracts.py`, config templates/schemas, `tests/test_evaluation.py`, `README.md`, `SKILL.md`, `eval/README.md`, and `plans/README.md`.
