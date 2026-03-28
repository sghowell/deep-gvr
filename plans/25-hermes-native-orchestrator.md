# 25 Hermes Native Orchestrator

## Purpose / Big Picture

Replace the current top-level role-by-role `hermes chat` runtime with the architecture-native Hermes skill orchestration model. The goal is for `/deep-gvr` to execute Generator, Verifier, Reviser, and Simulator work through delegated Hermes role execution instead of treating each role as an independent top-level CLI call.

## Branch Strategy

Start from `main` and implement this slice on `codex/hermes-native-orchestrator`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result, push `main`, confirm CI, and delete the feature branch.

## Commit Plan

- `add delegated orchestrator runtime`
- `wire deep gvr command to delegated roles`
- `retire top level live runtime surface`

## Progress

- [ ] Add the new plan and index it from `plans/README.md`.
- [ ] Introduce a delegated Hermes runtime boundary for Generator, Verifier, Reviser, and Simulator execution.
- [ ] Rewire the CLI and skill surface to use delegated runtime execution as the supported path.
- [ ] Retain the current top-level role runner only for tests or delete it if no longer needed.
- [ ] Validate the native orchestrator path with live smoke runs and updated docs.

## Surprises & Discoveries

- The current runtime is structurally closer to a prompt harness than to the delegated-skill architecture described in the original document.
- The current live-route work can inform the delegated implementation, but it should not define the steady-state public runtime once this slice lands.

## Decision Log

- Delegated Hermes execution becomes the supported runtime path for CLI and skill use.
- The current `HermesPromptRoleRunner` may remain only as explicit test infrastructure if it still serves deterministic/live harness testing.
- Evidence and transcript artifacts must remain available after the runtime switch.

## Outcomes & Retrospective

- Pending implementation.

## Context and Orientation

- Target architecture: `docs/deep-gvr-architecture.md`
- Current runtime entrypoints: `src/deep_gvr/cli.py`, `src/deep_gvr/evaluation.py`
- Skill procedure: `SKILL.md`
- Tier 1 loop core: `src/deep_gvr/tier1.py`
- Architecture ledger item: `hermes-native-orchestrator`

## Plan of Work

1. Add a Hermes-native delegated runtime boundary that can execute the role prompts through the skill/orchestrator model.
2. Wire CLI and skill commands to that runtime and preserve session/evidence semantics.
3. Update eval/live harnessing so product runtime and test runtime are clearly separated.
4. Remove or demote the current top-level role runner from the shipped operator surface.

## Concrete Steps

1. Add the delegated runtime abstraction and its supporting contracts under `src/deep_gvr/`.
2. Update `src/deep_gvr/cli.py` and `SKILL.md` to invoke the delegated runtime instead of direct role-by-role prompt execution.
3. Update `src/deep_gvr/evaluation.py` so benchmark execution can either exercise the delegated runtime or keep explicit test-only doubles.
4. Update docs to reflect the new supported runtime boundary and retire the prior temporary-gap wording.
5. Add or update tests that cover delegated role dispatch, artifact persistence, and failure handling.

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Targeted validation:

```bash
uv run deep-gvr run "Explain why the surface code has a threshold."
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --subset live-expansion --prompt-profile compact
```

Acceptance evidence:

- CLI and skill runs use delegated Hermes role execution as the supported runtime path.
- Current evidence, checkpoint, and transcript artifacts remain intact or improve.
- The prior top-level role runner no longer appears as the supported operator surface outside explicit test infrastructure.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/hermes-native-orchestrator` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Keep the runtime switch behind one clear boundary so it can be resumed safely if the branch stops mid-slice.
- Preserve append-only evidence semantics during the runtime migration.
- If Hermes delegated execution reveals a platform blocker, record it explicitly and update the architecture ledger status instead of restoring the top-level runner as the accepted end state.

## Interfaces and Dependencies

- Depends on Hermes delegated role execution semantics.
- `src/deep_gvr/cli.py` and `SKILL.md` remain the user-facing orchestration surface.
- `src/deep_gvr/evaluation.py` may keep explicit harness-only runtime doubles, but the product path must use the delegated orchestrator.
