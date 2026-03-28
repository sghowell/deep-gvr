# 26 Subagent Capability Closure

## Purpose / Big Picture

Close the two P0 architecture gaps that still block the intended adversarial design: per-subagent model routing and verifier-side MCP access. This slice makes those capabilities real, updates probes to report the true supported state, and retires prompt/temperature decorrelation plus orchestrator-mediated Tier 3 as the normal runtime path.

## Branch Strategy

Start from `main` and implement this slice on `codex/subagent-capability-closure`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result, push `main`, confirm CI, and delete the feature branch.

## Commit Plan

- `implement subagent model routing`
- `enable verifier side mcp access`
- `retire fallback routing policy`

## Progress

- [ ] Add the new plan and index it from `plans/README.md`.
- [ ] Make generator and verifier use distinct routes through actual subagent configuration.
- [ ] Make verifier-side Aristotle MCP access real and supported.
- [ ] Update probes, docs, and evidence recording to describe the closed capability gaps.
- [ ] Remove prompt/temperature decorrelation and orchestrator mediation from the supported runtime surface.

## Surprises & Discoveries

- The current repo already records effective routing and capability outcomes carefully, so the main work is to turn those records from fallback accounting into confirmation of real delegated capabilities.
- This slice is explicitly dependent on Hermes platform behavior and may require upstream coordination.

## Decision Log

- Distinct generator/verifier routes are required for the intended architecture and are not optional once supported.
- Verifier-side MCP access becomes the normal Tier 3 path; orchestrator mediation may remain only as migration or test scaffolding during implementation.
- Capability probes must reflect actual supported behavior, not aspirational hints.

## Outcomes & Retrospective

- Pending implementation.

## Context and Orientation

- Capability probes: `src/deep_gvr/probes.py`, `docs/capability-probes.md`
- Routing logic: `src/deep_gvr/routing.py`
- Formal transport: `src/deep_gvr/formal.py`
- Architecture ledger item: `subagent-capability-closure`

## Plan of Work

1. Prove or enable real per-subagent model routing.
2. Prove or enable delegated verifier MCP access.
3. Wire the runtime to use those capabilities directly.
4. Retire the current shared-route and orchestrator-mediated norms.

## Concrete Steps

1. Update the Hermes-native orchestrator path to pass explicit per-role route configuration.
2. Update Tier 3 invocation so the Verifier can call Aristotle directly through delegated MCP access.
3. Update routing/evidence contracts to reflect the actual delegated route rather than fallback intent.
4. Update probes, docs, and tests to require the closed capability state.

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Targeted validation:

```bash
uv run python scripts/run_capability_probes.py
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --subset live-expansion --prompt-profile compact
```

Acceptance evidence:

- `per_subagent_model_routing` reports `ready` based on real runtime behavior.
- `subagent_mcp_inheritance` reports `ready` based on real delegated MCP access.
- Generator and Verifier run on distinct supported routes.
- Verifier-side Tier 3 execution no longer relies on orchestrator mediation as the standard path.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/subagent-capability-closure` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Keep probe and runtime changes tightly coupled so capability reporting cannot drift from behavior.
- If Hermes still blocks one of these capabilities, leave the ledger item open as `blocked_external` and record the exact platform dependency rather than re-normalizing the workaround.
- Preserve evidence compatibility while the route and Tier 3 paths change.

## Interfaces and Dependencies

- Depends on Hermes support for delegated route configuration and delegated MCP tool access.
- Touches `src/deep_gvr/routing.py`, `src/deep_gvr/probes.py`, and the delegated runtime introduced by plan 25.
- Must leave the benchmark and evidence contracts internally consistent.
