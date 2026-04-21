# 63 Codex Native Delegation Evaluation

## Purpose / Big Picture

Evaluate whether `deep-gvr` should go beyond the current native role-separated
Codex backend and the current subagent operator pack into deeper Codex-native
delegation or subagent-state integration.

This is explicitly an evaluation slice first. The goal is to produce grounded
evidence about whether deeper Codex-native delegation is worth promoting into
the runtime boundary.

## Branch Strategy

Start from `main` and implement this slice on
`codex/codex-native-delegation-evaluation`. Merge back into `main` locally with
a fast-forward only after branch validation passes, then validate the merged
result again, push `main`, confirm CI and Docs, and delete the feature branch
when it is no longer needed.

## Commit Plan

- `plan codex native delegation evaluation`
- `add codex delegation evaluation surface`
- `document codex delegation findings`

## Progress

- [ ] Define the specific Codex-native delegation behaviors worth evaluating.
- [ ] Add a safe evaluation path and evidence format.
- [ ] Record the findings and recommended boundary.

## Surprises & Discoveries

- Pending.

## Decision Log

- Decision: do not promise deeper Codex-native delegation until the repo has
  actual evaluation evidence for it.

## Outcomes & Retrospective

- Pending implementation.

## Context and Orientation

- `docs/codex-subagents.md`
- `src/deep_gvr/orchestrator.py`
- `plans/54-codex-subagent-integration.md`
- `plans/58-codex-native-subagent-backend.md`

## Plan of Work

1. Define the delegation behaviors that matter most to `deep-gvr`.
2. Add a safe evaluation path for those behaviors.
3. Record whether the current operator-pack boundary should stay or expand.

## Concrete Steps

1. Identify evaluation targets such as:
   - deeper multi-agent role mapping
   - richer Codex-native parallel work ownership
   - agent-state or delegation observability worth exposing
2. Add a bounded evaluation harness, report, or artifact path.
3. Update docs/roadmap surfaces with the conclusion.

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Acceptance evidence:

- The repo contains a concrete evaluation result rather than only opinions about
  deeper Codex-native delegation.
- The resulting docs stay honest about what is runtime-owned versus
  product-owned.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/codex-native-delegation-evaluation` into `main`
  locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm CI and Docs are green.
- Delete the feature branch when it is no longer needed.

## Idempotence and Recovery

- Keep the slice evaluation-first. Do not smuggle in unvalidated runtime
  behavior under the label of “delegation support”.

## Interfaces and Dependencies

- Depends on current Codex local/native role execution and the existing
  subagent operator pack.
- Depends on current Codex product delegation capabilities remaining available.
