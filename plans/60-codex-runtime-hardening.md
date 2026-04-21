# 60 Codex Runtime Hardening

## Purpose / Big Picture

Harden the native `codex_local` backend now that it is a real role-separated
runtime path. The current backend works, but it still under-reports its own
runtime evidence and can lose useful role-level debug context when a Codex role
call fails before returning valid JSON.

The user-visible outcome is:

- native Codex transcript artifacts preserve failed role calls instead of only
  successful ones
- the existing orchestrator transcript artifact records parsed role payloads as
  structured data rather than only raw text
- the existing capability-evidence artifact includes Codex-specific runtime
  evidence about observed native role execution without polluting the Hermes-only
  plan-26 closure signals

This slice is not a Codex Cloud feature and it is not a claim that Hermes plan
26 is now closed.

## Branch Strategy

Start from `main` and implement this slice on `codex/codex-runtime-hardening`.
Merge back into `main` locally with a fast-forward only after branch validation
passes, then validate the merged result again, push `main`, confirm CI and
Docs, and delete the feature branch when it is no longer needed.

## Commit Plan

- `add codex phase2 roadmap`
- `harden codex runtime evidence`
- `document codex runtime hardening`

## Progress

- [x] Draft the roadmap and execution plan.
- [x] Preserve failed native Codex role calls in transcript artifacts.
- [x] Record structured parsed-response data in Codex transcript entries.
- [x] Emit Codex-specific runtime capability evidence from the existing
      transcript/capability-evidence artifact path.
- [x] Update tests and docs.
- [ ] Run validation, merge locally, revalidate on `main`, push, confirm CI and
      Docs, and delete the feature branch.

## Surprises & Discoveries

- The current transcript artifact already has the right top-level shape for
  role-level evidence, so the cleanest hardening move is to enrich that
  artifact instead of inventing another parallel artifact family.
- The biggest observability gap is failure handling: a Codex role command that
  exits non-zero can currently fail before a role transcript entry is recorded.
- Codex-native route observations should not be written into the Hermes-focused
  `per_subagent_model_routing` evidence key, because that would blur the
  still-blocked plan-26 boundary.

## Decision Log

- Decision: enrich the existing orchestrator transcript artifact rather than add
  a second Codex-only artifact tree.
- Decision: record Codex-native execution evidence under a new Codex-specific
  capability-evidence key instead of reusing the Hermes-only plan-26 keys.
- Decision: preserve failed role calls in transcript artifacts even when the
  role never returned valid JSON.

## Outcomes & Retrospective

- Native Codex transcript entries now retain structured parsed response data for
  successful role calls and structured error data for failed role calls.
- The existing CLI capability-evidence surface now emits a Codex-specific
  `codex_native_role_execution` record derived from the observed role-call
  transcripts.
- The existing transcript and capability-evidence artifact names were preserved,
  so the hardening work improved observability without inventing a second
  Codex-only artifact tree.

## Context and Orientation

- Native Codex backend:
  - `src/deep_gvr/orchestrator.py`
  - `src/deep_gvr/cli.py`
- Existing artifact/evidence flow:
  - `src/deep_gvr/tier1.py`
  - `src/deep_gvr/evidence.py`
  - `docs/contracts-and-artifacts.md`
- Current Codex backend docs:
  - `docs/codex-local.md`
  - `docs/deep-gvr-architecture.md`

## Plan of Work

1. Make Codex role transcript entries survive command failures and invalid JSON
   failures.
2. Enrich transcript entries with parsed role payloads and structured error
   fields.
3. Synthesize Codex-specific native-execution capability evidence from the
   transcript set.
4. Update tests and docs so the hardened artifact surface is explicit.

## Concrete Steps

1. Update `src/deep_gvr/orchestrator.py` so Codex role execution:
   - records transcript entries even when a role command exits non-zero
   - preserves the raw response text on failures
   - stores the parsed JSON payload on successful role executions
2. Update `src/deep_gvr/cli.py` so capability-evidence merging:
   - synthesizes a Codex-specific `codex_native_role_execution` evidence record
     from observed role transcripts
   - threads that evidence into the existing summary and capability-evidence
     artifact path
3. Extend tests in `tests/test_cli.py` to cover:
   - structured parsed-response data in Codex transcript entries
   - Codex-specific capability evidence in summaries and artifacts
   - failed Codex role calls still appearing in transcript artifacts
4. Update:
   - `plans/README.md`
   - `docs/codex-local.md`
   - `docs/contracts-and-artifacts.md`
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
```

Acceptance evidence:

- Codex transcript artifacts include role-level structured response data for
  successful native role calls.
- Failed native Codex role calls still appear in the transcript artifact with a
  structured error field.
- The summary and capability-evidence artifact expose
  `codex_native_role_execution` when the native Codex backend runs.
- The Hermes-only plan-26 capability keys remain unchanged and unclaimed by the
  Codex runtime.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/codex-runtime-hardening` into `main` locally only
  after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions and Docs runs for the pushed head are green.
- Delete the local feature branch, and delete the remote feature branch too if
  one was created.

## Idempotence and Recovery

- The hardened transcript/evidence surface must reuse the existing session
  artifact paths instead of inventing a second Codex-only artifact tree.
- If a role call fails before returning JSON, the transcript should still be
  sufficient to diagnose the failure after the fact.
- Codex-native evidence must remain clearly separate from Hermes delegated
  capability closure evidence.

## Interfaces and Dependencies

- Depends on the native `codex_local` backend from
  `plans/56-codex-local-backend.md` and `plans/58-codex-native-subagent-backend.md`.
- Must remain compatible with the current CLI summary shape, release preflight,
  and existing transcript/capability-evidence artifact paths.
