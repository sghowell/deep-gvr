# 58 Codex Native Subagent Backend

## Purpose / Big Picture

Expand the `codex_local` backend so it no longer behaves like a single opaque
`codex exec` orchestrator prompt that returns a session summary. The user-visible
outcome is that `deep-gvr` can execute the Generator, Verifier, and Reviser as
separate native Codex role calls over the typed Tier 1 loop, while still
reusing the existing checkpoint, evidence, Tier 2 analysis, and Tier 3 formal
verification machinery.

This slice should make the Codex backend materially first-class:

- `runtime.orchestrator_backend=codex_local` uses native role-isolated Codex
  execution for Generator, Verifier, and Reviser
- role prompts come from the checked-in repo prompt set, not from an
  all-in-one backend wrapper prompt
- Tier 2 and Tier 3 remain on the existing adapter boundaries
- transcripts and docs make the native Codex role path explicit

This slice does **not** claim Codex Cloud support, repo-managed Codex app state,
or closure of Hermes plan 26.

## Branch Strategy

Start from `main` and implement this slice on
`codex/codex-native-subagent-backend`. Merge back into `main` locally with a
fast-forward only after branch validation passes, then validate the merged
result again, push `main`, confirm CI and Docs, and delete the feature branch
when it is no longer needed.

## Commit Plan

- `add codex native subagent backend plan`
- `implement codex native role loop`
- `document codex native role execution`

## Progress

- [x] Draft the plan and index it from `plans/README.md`.
- [x] Replace the single-shot Codex backend summary path with a native role
      execution path over `Tier1LoopRunner`.
- [x] Add typed Codex role executors, response contracts, transcript coverage,
      and focused tests.
- [x] Update Codex-facing docs and the architecture ledger.
- [ ] Run validation, merge locally, revalidate on `main`, push, confirm CI and
      Docs, and delete the feature branch.

## Surprises & Discoveries

- Plan 54 intentionally stopped at a prompt/export subagent pack, which kept the
  operator story useful but left the runtime backend unchanged.
- Plan 56 made `codex_local` a real backend, but the implementation still
  delegated the whole session through one `codex exec` summary prompt.
- The repo already has the right abstraction for a stronger backend:
  `Tier1LoopRunner` can own checkpoint/evidence/state transitions if Codex role
  executors return typed `CandidateSolution` and `VerificationReport` objects.

## Decision Log

- Decision: implement native Codex role execution by attaching separate Codex
  generator/verifier/reviser executors to `Tier1LoopRunner` instead of trying
  to manage Codex app subagent state directly.
- Decision: keep Tier 2 analysis and Tier 3 formal verification on the existing
  Python adapter/formal boundaries.
- Decision: keep the existing exported Codex subagent prompt pack, but update
  docs so it is clearly an operator pack layered on top of a real native Codex
  backend rather than the backend itself.
- Decision: record multiple backend transcript entries for Codex role execution
  so the evidence surface shows the role-separated runtime path explicitly.

## Outcomes & Retrospective

- `codex_local` now drives the typed Tier 1 loop through separate native Codex
  generator, verifier, and reviser calls instead of a single summary-only
  backend prompt.
- The routing layer now exposes a dedicated native-role plan so explicit Codex
  role routes can be exercised without pretending that Hermes delegated
  capability closure is complete.
- Transcript artifacts now show multiple Codex role calls with selected routes,
  which makes the backend behavior inspectable.
- Public docs now describe the Codex subagent pack as an operator pack layered
  on top of a real native Codex backend rather than implying that the pack is
  the backend.

## Context and Orientation

- Existing Codex backend abstraction: `src/deep_gvr/orchestrator.py`,
  `src/deep_gvr/cli.py`, `src/deep_gvr/runtime_paths.py`
- Existing typed loop and adapter boundaries: `src/deep_gvr/tier1.py`
- Existing role prompts: `prompts/generator.md`, `prompts/verifier.md`,
  `prompts/verifier_compact.md`, `prompts/reviser.md`
- Existing Codex operator pack: `docs/codex-subagents.md`,
  `codex_subagents/catalog.json`
- Existing Codex backend docs: `docs/codex-local.md`,
  `docs/codex-ssh-devbox.md`

## Plan of Work

1. Add a native Codex role-execution layer that can run generator, verifier,
   and reviser requests as separate `codex exec` calls with typed JSON
   contracts.
2. Wire the `codex_local` backend to drive the existing `Tier1LoopRunner`
   instead of returning only a top-level summary from one opaque Codex prompt.
3. Update transcripts, tests, docs, and the architecture ledger so the new
   runtime boundary is explicit and enforced.

## Concrete Steps

1. Add native Codex role execution helpers in `src/deep_gvr/orchestrator.py`
   (or a nearby backend module) for:
   - generator
   - verifier
   - reviser
   - per-role JSON schema / contract handling
   - multi-call transcript recording
2. Rework the `codex_local` backend path so `run` and `resume`:
   - load the runtime config
   - build a role-aware routing plan suitable for native Codex execution
   - run `Tier1LoopRunner` with Codex-native role executors
   - preserve the existing session summary return shape for the CLI wrapper
3. Add focused tests covering:
   - native Codex backend run path
   - resume path
   - multi-call transcript contents
   - role prompt selection for compact/full verifier profiles
4. Update:
   - `plans/README.md`
   - `docs/codex-local.md`
   - `docs/codex-subagents.md`
   - `docs/system-overview.md`
   - `docs/deep-gvr-architecture.md`
   - `docs/architecture-status.md`

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
uv run python -m unittest tests.test_cli -v
uv run python scripts/codex_preflight.py --json
uv run python scripts/codex_ssh_devbox_run.py run --help
```

Acceptance evidence:

- `runtime.orchestrator_backend=codex_local` uses separate native Codex role
  executions for Generator, Verifier, and Reviser.
- The typed loop still owns checkpoint, evidence, branch escalation, Tier 2,
  and Tier 3 behavior.
- Codex backend transcripts record multiple role calls rather than one opaque
  summary-only call.
- Docs describe Codex as a real native role backend while keeping the boundary
  honest around Codex Cloud and live app-state management.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/codex-native-subagent-backend` into `main` locally
  only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions and Docs runs for the pushed head are green.
- Delete the local feature branch, and delete the remote feature branch too if
  one was created.

## Idempotence and Recovery

- The native Codex role backend must keep using the existing session/evidence
  directories instead of inventing a second artifact tree.
- If a role call fails, the wrapper should still return a structured session
  failure summary with transcript artifacts, just like the existing CLI path.
- The backend should reuse repo-owned prompts and typed contracts so prompt or
  artifact drift remains testable.

## Interfaces and Dependencies

- Depends on `Tier1LoopRunner` in `src/deep_gvr/tier1.py`.
- Depends on the checked-in role prompts under `prompts/`.
- Depends on the `codex` CLI being available for the native backend path.
- Must remain compatible with the existing CLI summary shape, release preflight,
  Codex-local docs, and SSH/devbox execution helper.
