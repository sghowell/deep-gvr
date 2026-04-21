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

- [x] Add the new plan and index it from `plans/README.md`.
- [x] Replace env-hint capability probes with runtime-behavior proof scaffolding.
- [ ] Make generator and verifier use distinct routes through actual subagent configuration.
- [ ] Make verifier-side Aristotle MCP access real and supported.
- [ ] Update probes, docs, and evidence recording to describe the closed capability gaps.
- [ ] Remove prompt/temperature decorrelation and orchestrator mediation from the supported runtime surface.

## Surprises & Discoveries

- The current repo already records effective routing and capability outcomes carefully, so the main work is to turn those records from fallback accounting into confirmation of real delegated capabilities.
- The current `per_subagent_model_routing` and `subagent_mcp_inheritance` probes still hinge on environment hints (`DEEP_GVR_HERMES_MODEL_ROUTING` and `DEEP_GVR_SUBAGENT_MCP`) instead of real runtime behavior, so the first concrete implementation step is to replace those hints with runtime-proof scaffolding.
- The delegated orchestrator path in `src/deep_gvr/orchestrator.py` currently exposes only one top-level provider/model pair for the whole Hermes session, which confirms that real per-subagent route closure will need new delegated-runtime wiring instead of just routing-plan math.
- The first runtime slice can still improve the closure path by threading explicit per-role route payloads into the delegated runtime request and transcript artifacts before Hermes-level subagent overrides are fully proven.
- The next useful increment is to require delegated runs to return `capability_evidence` in their structured JSON when they can observe actual role-level routing or delegated MCP behavior, so probe readiness can eventually be driven from recorded runtime artifacts instead of side-channel assumptions.
- The delegated orchestrator wrapper now threads that `capability_evidence` field through the response contract, transcript artifacts, a dedicated capability-evidence artifact file, the returned `SkillSessionSummary`, and the contracts-and-artifacts docs; the delegated skill/runtime contract now also explicitly distinguishes requested `role_routes` from observed capability closure. The remaining step is to make the delegated skill/runtime populate `capability_evidence` from real observed behavior.
- A real delegated CLI run with `--routing-probe ready` still timed out before the skill returned a structured summary, so we do not yet have proof that the delegated runtime is emitting observed `capability_evidence` in practice.
- The dedicated Hermes v0.9 reassessment harness at `scripts/reassess_plan26.py` now makes that failure mode repeatable instead of anecdotal: the first local v0.9 run timed out after 180 seconds on both the route-focused and verifier-MCP-focused checks and returned no observed `capability_evidence`.
- The Hermes v0.10 recheck reached the same blocker state with fresher evidence: both delegated checks still timed out after 180 seconds and returned no observed `capability_evidence`, despite the local Hermes upgrade.
- This slice is explicitly dependent on Hermes platform behavior and may require upstream coordination.

## Decision Log

- Distinct generator/verifier routes are required for the intended architecture and are not optional once supported.
- Verifier-side MCP access becomes the normal Tier 3 path; orchestrator mediation may remain only as migration or test scaffolding during implementation.
- Capability probes must reflect actual supported behavior, not aspirational hints.

## Outcomes & Retrospective

- Partial progress only; this slice remains blocked externally.
- The repo now has honest runtime-evidence probes, delegated `role_routes` payload plumbing, `capability_evidence` response/transcript/artifact plumbing, and stronger delegated-skill instructions about observed-versus-requested behavior.
- A real delegated CLI run with the updated installed skill still timed out after 300 seconds and returned no observed `capability_evidence`, so the repo cannot honestly claim per-subagent route closure or verifier-direct MCP closure yet.
- The first dedicated Hermes v0.9 reassessment run reached the same conclusion with a cleaner harness: both delegated checks timed out after 180 seconds and still produced no observed `capability_evidence`.
- The Hermes v0.10 recheck also reached `environment_blocked` with the same failure mode; see `/tmp/deep-gvr-plan26-v0.10-report.json`.

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

1. Replace the env-hint capability probes in `src/deep_gvr/probes.py` with runtime-behavior proof scaffolding so `ready` can only come from observed delegated behavior, not environment declarations.
2. Extend the delegated orchestrator/runtime path in `src/deep_gvr/orchestrator.py` and the plan/routing integration so explicit per-role route configuration is passed into the delegated role executions.
3. Update the Tier 3 invocation path so the Verifier can call Aristotle directly through delegated MCP access, leaving orchestrator mediation only as migration or test scaffolding while the slice is in flight.
4. Update routing/evidence contracts in `src/deep_gvr/routing.py`, `src/deep_gvr/tier1.py`, and related templates/tests so artifacts describe the actual delegated route rather than fallback intent.
5. Update probes, docs, and tests to require the closed capability state and remove prompt/temperature decorrelation plus orchestrator-mediated Tier 3 from the supported steady-state surface.

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
uv run python scripts/reassess_plan26.py --json
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
