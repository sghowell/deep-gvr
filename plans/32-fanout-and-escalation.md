# 32 Fanout and Escalation

## Purpose / Big Picture

Add the phase-2 orchestration features that the architecture intentionally deferred: optional multi-hypothesis fan-out and explicit failure escalation/decomposition policy. This slice expands the orchestrator beyond the current sequential loop without weakening checkpoint safety or evidence quality.

## Branch Strategy

Start from `main` and implement this slice on `codex/fanout-and-escalation`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result, push `main`, confirm CI, and delete the feature branch.

## Commit Plan

- `add fanout loop contracts`
- `implement failure escalation policy`
- `document orchestration expansion`

## Progress

- [x] Add the new plan and index it from `plans/README.md`.
- [x] Add optional multi-hypothesis fan-out to the orchestrator state model.
- [x] Implement explicit failure escalation and decomposition policy.
- [x] Extend evidence, benchmarks, and docs for the expanded orchestration model.

## Surprises & Discoveries

- Fan-out must be designed around checkpoint and evidence semantics first; otherwise it will undermine the strongest part of the current harness.
- Failure escalation needs benchmark coverage so it does not become an unbounded “try everything” path.

## Decision Log

- Sequential execution remains the default mode.
- Fan-out and escalation are both opt-in and must be recorded explicitly in evidence.
- Expanded orchestration must preserve the verifier-isolation rule.

## Outcomes & Retrospective

- The loop now persists an active branch plus queued alternative/decomposition branches in the session checkpoint instead of treating repeated failure as an unstructured retry path.
- Repeated failure now emits explicit `escalate` evidence records with bounded `fanout`, `switch_branch`, or `halt` actions, and deterministic benchmark coverage now includes an orchestration-required case.
- Sequential execution still remains the default happy path; fan-out only appears after repeated failure and only within the configured alternative and iteration budgets.

## Context and Orientation

- Current loop runner: `src/deep_gvr/tier1.py`
- Evidence contracts: `src/deep_gvr/contracts.py`
- Benchmark runner: `src/deep_gvr/evaluation.py`
- Architecture ledger item: `fanout-and-escalation`

## Plan of Work

1. Extend the loop contracts to represent multiple concurrent or queued hypotheses.
2. Add explicit failure escalation/decomposition rules.
3. Update evidence, benchmarks, and docs so the expanded orchestration remains auditable.

## Concrete Steps

1. Extend session and evidence contracts for fan-out state and escalation actions.
2. Update the orchestrator loop to support optional fan-out and failure escalation.
3. Add tests for checkpoint safety, evidence integrity, and verifier isolation under fan-out.
4. Add benchmark cases that exercise decomposition or escalation behavior.

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Targeted validation:

```bash
uv run python -m unittest tests.test_tier1_loop tests.test_evaluation -v
```

Acceptance evidence:

- Fan-out is configurable and checkpoint-safe.
- Failure escalation is explicit, evidence-backed, and bounded.
- The verifier remains isolated from orchestrator framing under the expanded loop.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/fanout-and-escalation` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Keep sequential mode stable while fan-out is being added.
- Make fan-out and escalation transitions explicit in evidence so interrupted work can resume safely.
- Avoid hidden heuristics; decomposition and escalation rules must be visible and testable.

## Interfaces and Dependencies

- Depends on the Hermes-native orchestrator and completed evidence system.
- Touches session state, evidence contracts, and benchmarks.
- Must preserve verifier isolation and Tier-selection semantics.
