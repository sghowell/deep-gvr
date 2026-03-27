# Cross-Model Routing

## Purpose / Big Picture

Implement the decorrelated model strategy so generator and verifier do not share the same default model path when a stronger option is available.

## Branch Strategy

Start from the integration branch and work on `codex/cross-model-routing`. Merge back locally after validation passes.

## Commit Plan

- `implement model routing strategy`
- `document routing fallback behavior`

## Progress

- [x] Added a deterministic routing plan driven by config plus the routing probe.
- [x] Threaded effective generator, verifier, and reviser routes into Tier 1 requests and evidence records.
- [x] Added tests for preferred direct routing and temperature-decorrelation fallback behavior.
- [ ] Run full branch validation, merge locally, push, confirm CI, and clean up.

## Surprises & Discoveries

- The repo needed an explicit orchestrator route in `DeepGvrConfig` so fallback evidence can record the inherited model path instead of leaving it implicit.
- A ready routing probe is not enough by itself; the runner still needs a same-model fallback when generator and verifier config resolve to the same provider/model pair.

## Decision Log

- Decision: treat prompt and temperature decorrelation as the documented fallback, not the preferred design.
  Rationale: the architecture depends on independent failure modes when the platform allows it.
  Date/Author: 2026-03-26 / Codex
- Decision: add `models.orchestrator` to the config contract and use it as the shared inherited path when per-subagent routing is unavailable.
  Rationale: fallback evidence must record the effective model path deterministically from repo-local state.
  Date/Author: 2026-03-26 / Codex

## Outcomes & Retrospective

Implementation is complete; merge and release steps remain.

## Context and Orientation

This plan covers generator, verifier, and reviser model selection, capability-driven fallback behavior, and the evidence trail for which model path was used.

## Plan of Work

Implement a routing layer that prefers distinct providers or models and records the effective path in evidence artifacts.

## Concrete Steps

1. Confirm Hermes routing support through probes and treat the result as routing input, not hidden environment lore.
2. Add deterministic effective model-selection logic for orchestrator, generator, verifier, and reviser roles.
3. Record the effective route, routing mode, and any temperature fallback in evidence artifacts.
4. Add tests for preferred direct routing, same-model fallback, and orchestrator-inherited fallback.

## Validation and Acceptance

- `python scripts/check_repo.py`
- `python scripts/run_capability_probes.py`
- `python -m unittest discover -s tests -v`

Acceptance: the harness records distinct generator and verifier routes when supported and degrades cleanly otherwise.

## Merge, Push, and Cleanup

Merge locally only after validation passes. Validate the merged result again, push the integrated branch, and delete `codex/cross-model-routing` when it is no longer needed.

## Idempotence and Recovery

Routing decisions must remain deterministic from config plus capability state so runs are reproducible.

## Interfaces and Dependencies

Primary paths: `src/deep_gvr/contracts.py`, `src/deep_gvr/routing.py`, `src/deep_gvr/tier1.py`, config/evidence schemas and templates, probe results, and routing-focused tests.
