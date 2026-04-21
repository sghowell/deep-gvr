# 66 OpenAI-Native Backend

## Purpose / Big Picture

Implement a third orchestrator backend, `openai_native`, so `deep-gvr` can run
on OpenAI's official API surfaces without depending on Hermes delegation or
Codex app-managed state. The user-visible outcome should be that
`runtime.orchestrator_backend=openai_native` becomes a real supported runtime
option with repo-owned transcript, evidence, checkpoint, and preflight
behavior.

Based on plan 65, the first implementation target should be the Responses API.
The Agents SDK remains a possible later acceleration layer, not the required
first transport.

## Branch Strategy

Start from `main` after plan 65 is merged and implement this slice on
`codex/openai-native-backend`. Merge back into `main` locally with a
fast-forward only after branch validation passes, then validate the merged
result again, push `main`, confirm CI and Docs, and delete the feature branch
when it is no longer needed.

## Commit Plan

- `add openai native backend contracts`
- `implement openai native backend runner`
- `wire openai native backend docs and checks`

## Progress

- [ ] Extend the backend enum and config surface to include `openai_native`.
- [ ] Implement a Responses-API-backed role runner.
- [ ] Map OpenAI-native transcripts and tool calls into the existing evidence
      and checkpoint model.
- [ ] Add backend-sensitive preflight and release checks.
- [ ] Update docs and architecture status.
- [ ] Run validation, merge locally, revalidate on `main`, push, confirm CI and
      Docs, and delete the feature branch.

## Surprises & Discoveries

- Pending implementation.

## Decision Log

- Decision: start with the Responses API as the first `openai_native` transport.
- Decision: keep Tier 2 analysis, Tier 3 formal verification, checkpoints, and
  evidence owned by the existing typed Python runtime.
- Decision: treat the Agents SDK as a later harness option once the base
  backend contract exists and is stable.

## Outcomes & Retrospective

- Pending implementation.

## Context and Orientation

- Backend seam:
  - `src/deep_gvr/contracts.py`
  - `src/deep_gvr/orchestrator.py`
  - `src/deep_gvr/cli.py`
- Routing and prompt ownership:
  - `src/deep_gvr/routing.py`
  - `prompts/`
- Evidence and checkpoint surfaces:
  - `src/deep_gvr/tier1.py`
  - `src/deep_gvr/evidence.py`
  - `docs/contracts-and-artifacts.md`
- Release and operator surfaces:
  - `src/deep_gvr/release_surface.py`
  - `scripts/release_preflight.py`
  - `scripts/codex_preflight.py`
  - `README.md`
  - `docs/system-overview.md`
  - `docs/deep-gvr-architecture.md`

## Plan of Work

1. Add `openai_native` as a supported backend selection in the typed config
   surface.
2. Implement role-separated OpenAI-native execution over the same Tier 1 loop.
3. Preserve transcript, evidence, artifact, and resume semantics.
4. Add the required operator and release checks for the new backend.

## Concrete Steps

1. Extend backend enums, config parsing, schemas, templates, and tests to
   recognize `openai_native`.
2. Add an OpenAI-native runner in `src/deep_gvr/orchestrator.py` that:
   - executes Generator, Verifier, and Reviser as separate role calls
   - uses structured outputs
   - records backend command/request metadata and response payloads
3. Decide and encode the first tool surface for that backend:
   - no tools for role calls initially, or
   - a narrow documented set such as remote MCP when required
4. Add provider credential and backend-preflight coverage for the OpenAI API
   path.
5. Update docs and the architecture ledger to describe the new backend honestly.

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
uv run mkdocs build --strict
```

Targeted validation:

```bash
uv run python scripts/release_preflight.py --json
uv run python -m unittest tests.test_cli -v
uv run python -m unittest tests.test_release_scripts -v
```

Acceptance evidence:

- `runtime.orchestrator_backend=openai_native` is a valid config choice.
- The backend can drive Generator, Verifier, and Reviser without Hermes or
  Codex app state.
- Transcript and capability-evidence artifacts remain repo-owned and inspectable.
- Docs and preflight surfaces describe the new backend without overstating tool
  or formal-transport parity.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/openai-native-backend` into `main` locally only
  after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm CI and Docs are green.
- Delete the local feature branch, and delete the remote feature branch too if
  one was created.

## Idempotence and Recovery

- The new backend must fail explicitly if the OpenAI API prerequisites are not
  satisfied.
- The implementation must reuse the existing session and artifact directories
  rather than inventing a second storage model.
- If OpenAI tool or SDK coverage changes during implementation, keep the
  supported first surface narrow rather than papering over missing behavior.

## Interfaces and Dependencies

- Depends on plan 65's decision to prefer the Responses API as the first
  transport.
- Depends on the existing role prompts, transcript artifact model, and evidence
  pipeline.
- Must stay compatible with Tier 2 and Tier 3 runtime ownership in the typed
  Python layer.
