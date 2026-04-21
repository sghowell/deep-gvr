# 65 OpenAI-Native Backend Evaluation

## Purpose / Big Picture

Evaluate whether `deep-gvr` should add a third orchestrator backend,
`openai_native`, that targets OpenAI's official API and harness surfaces rather
than Hermes delegation or Codex app-managed state. The user-visible outcome of
this slice is a repo-local decision about whether that backend is worth
pursuing now, what exact OpenAI surface it should target first, and what the
follow-on implementation slice must own.

This slice does not implement the backend. It records the decision and the
required shape of the next implementation plan.

## Branch Strategy

Start from `main` and implement this evaluation on
`codex/openai-native-backend-evaluation`. Merge back into `main` locally with a
fast-forward only after branch validation passes, then validate the merged
result again, push `main`, confirm CI and Docs, and delete the feature branch
when it is no longer needed.

## Commit Plan

- `plan openai native backend evaluation`
- `document openai native backend direction`

## Progress

- [x] Review the current `hermes` and `codex_local` backend seam.
- [x] Compare the candidate OpenAI-native surfaces against the current runtime
      contract.
- [x] Decide whether an `openai_native` backend is worth planning now.
- [x] Choose the preferred first implementation target.
- [x] Add the follow-on implementation plan and index the new plans.
- [ ] Run validation, merge locally, revalidate on `main`, push, confirm CI and
      Docs, and delete the feature branch.

## Surprises & Discoveries

- The remaining Codex limitation is not primarily a Codex problem anymore. The
  repo already owns a real native `codex_local` backend, so the next useful
  OpenAI-side expansion is a backend that depends on documented API or SDK
  contracts rather than Codex app state.
- The current official OpenAI surface is now strong enough to justify planning
  this. The Responses API exposes tool use, remote MCP, and background-mode
  patterns, while the April 15, 2026 Agents SDK update adds a model-native
  harness with sandbox execution, configurable memory, AGENTS.md, skills, shell,
  and apply-patch support.
- The same official Agents SDK update also says additional capabilities,
  including code mode and subagents, are still being worked on for Python and
  TypeScript. That makes a direct Agents-SDK backend plausible, but not yet the
  safest first implementation target for `deep-gvr`.
- The repo's evidence and checkpoint model is local-file-first and already
  stable. That argues for starting with the lower-level Responses API as the
  first repo-owned transport and treating the Agents SDK as a later harness
  acceleration layer.

## Decision Log

- Decision: plan an `openai_native` backend as a real repo-owned expansion.
- Decision: do not try to reach feature parity by owning deeper Codex app state.
  If this work proceeds, it should target OpenAI's documented API and harness
  layers instead.
- Decision: treat the Responses API as the preferred first implementation
  target, because it gives the repo the cleanest ownership boundary for role
  calls, tool selection, transcripts, checkpoints, and evidence.
- Decision: treat the Agents SDK as an optional later accelerator for sandboxed
  execution, durable state, and richer orchestration after the base backend
  contract exists.
- Decision: do not make this a public release requirement. It is a planned
  backend expansion, not a blocker on the current shipped surfaces.

## Outcomes & Retrospective

- The repo now has a concrete answer instead of a chat-only idea: an
  `openai_native` backend is worth planning, but it should start with the
  Responses API rather than deeper Codex app integration.
- The repo also now treats the current Codex-versus-Hermes asymmetries as
  explicit architecture context instead of leaving them implied:
  - Hermes is still the only backend with a blocked delegated-capability plan
    for real per-subagent route closure and delegated verifier-side Aristotle
    MCP access.
  - Codex local is stronger on native role-separated runtime ownership,
    role-level transcript observability, and repo-owned SSH/devbox execution.
  - Aristotle remains a shared Hermes-shaped formal transport even when
    `codex_local` is the selected orchestrator backend, so Codex is not yet
    fully Hermes-free for that Tier 3 path.
- The architecture ledger now records `openai-native-backend` as planned work.
- The follow-on implementation slice is now materialized in
  `plans/66-openai-native-backend.md`.

## Context and Orientation

- Current backend seam:
  - `src/deep_gvr/contracts.py`
  - `src/deep_gvr/orchestrator.py`
  - `src/deep_gvr/cli.py`
- Current backend status and boundaries:
  - `docs/architecture-status.md`
  - `docs/system-overview.md`
  - `docs/deep-gvr-architecture.md`
  - `docs/codex-local.md`
  - `plans/26-subagent-capability-closure.md`
  - `plans/63-codex-native-delegation-evaluation.md`
- Official OpenAI references used for this evaluation:
  - Responses API and tool surfaces
  - remote MCP / connectors
  - model availability on the Responses API
  - April 15, 2026 Agents SDK update

## Plan of Work

1. Compare the current `hermes` and `codex_local` backends against a possible
   OpenAI-native backend target.
2. Evaluate the viable OpenAI-native transport layers.
3. Choose the narrowest honest backend that the repo could actually own.
4. Materialize the next implementation slice from that decision.

## Concrete Steps

1. Inspect the current backend seam and identify what the repo would need a new
   backend to own:
   - role execution
   - routing
   - transcripts
   - evidence
   - checkpoint and resume behavior
   - Tier 2 and Tier 3 integration boundaries
2. Compare candidate OpenAI-native surfaces:
   - Responses API
   - Agents SDK
3. Decide the preferred first implementation target.
4. Add a follow-on implementation plan that is specific enough to execute
   without chat context.
5. Update the architecture ledger and technical docs so the new planned
   backend is explicit and the current runtime boundary stays honest.

## Current Backend Gap Snapshot

| Area | Hermes backend today | Codex backend today | Current gap |
|---|---|---|---|
| Core orchestrator execution | Delegated Hermes skill wrapper | Native role-separated `codex exec` loop | Hermes does not yet expose the same repo-owned per-role transcript and parsed-response surface |
| Live delegated subagent closure | Intended target, but still blocked in plan 26 | Intentionally stays outside the runtime contract and remains product-managed/operator-pack territory | No backend currently ships repo-owned live delegated subagent closure |
| Aristotle Tier 3 transport | Primary shipped path via Hermes MCP with CLI fallback | Uses the same shared formal layer | `codex_local` still depends on Hermes-shaped Aristotle transport when Aristotle is selected |
| Remote stronger-machine execution | No backend-specific orchestrator remote bootstrap path | Repo-owned SSH/devbox bootstrap and runtime-backed execution helper | Codex has a stronger repo-owned remote execution surface today |

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
uv run mkdocs build --strict
```

Acceptance evidence:

- The repo records a clear decision about whether to pursue an
  `openai_native` backend.
- The preferred first implementation target is explicit.
- A follow-on implementation plan exists in `plans/`.
- The architecture docs describe the planned backend without claiming it is
  already implemented.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/openai-native-backend-evaluation` into `main`
  locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm CI and Docs are green.
- Delete the local feature branch, and delete the remote feature branch too if
  one was created.

## Idempotence and Recovery

- Keep the slice documentary and architectural. Do not imply the backend exists
  before implementation work begins.
- If official OpenAI surface details change later, update this evaluation and
  the follow-on plan in the same branch that changes the backend strategy.

## Interfaces and Dependencies

- Depends on the existing orchestrator backend seam in `src/deep_gvr/`.
- Depends on official OpenAI-documented platform surfaces, especially the
  Responses API and the Agents SDK.
- Prepares `plans/66-openai-native-backend.md`.
