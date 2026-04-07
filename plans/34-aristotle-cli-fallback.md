# 34 Aristotle CLI Fallback

## Purpose / Big Picture

Add a direct Aristotle CLI fallback for Tier 3 so deep-gvr can still complete formal verification when the Hermes->MCP transport is configured but fails at runtime. The user-visible outcome is that Tier 3 records a real proof result when direct `aristotle submit --wait ...` succeeds, instead of stopping at a generic MCP error.

## Branch Strategy

Start from `main` and implement this slice on `codex/aristotle-cli-fallback`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result again, push `main`, confirm CI, and delete the feature branch when it is no longer needed.

## Commit Plan

- `add aristotle cli fallback transport`
- `document aristotle fallback behavior`

## Progress

- [x] Add the new plan and index it from `plans/README.md`.
- [x] Extend the Tier 3 formal transport to retry through direct Aristotle CLI when Hermes->MCP fails.
- [x] Add unit coverage for CLI fallback success and fallback unavailability.
- [x] Update docs to describe the fallback path and its artifact behavior.
- [x] Run repo validation for the branch.

## Surprises & Discoveries

- In this environment, Aristotle MCP readiness can report healthy while direct MCP prove/formalize calls still return a generic processing error.
- After `uv tool install aristotle`, direct Aristotle CLI submission succeeds, including long queue delays before execution starts.
- The direct CLI returns a tarball bundle with a summary markdown file and Lean files that can be mined for proof artifacts.

## Decision Log

- Keep Hermes->MCP as the primary Tier 3 path.
- Use direct Aristotle CLI only as a fallback path after transport/runtime failure, not as the first choice.
- Record fallback provenance in the formal transport artifact so downstream evidence can distinguish Hermes->MCP from direct CLI success.

## Outcomes & Retrospective

- Added a runtime fallback from Hermes->MCP Tier 3 failures to direct `aristotle submit --wait` execution.
- Preserved primary transport failure details while allowing successful direct-CLI proof bundles to upgrade the formal result.
- Added focused unit tests plus full repo validation to lock the fallback behavior in place.

## Context and Orientation

- Primary Tier 3 runtime: `src/deep_gvr/formal.py`
- Tier 3 tests: `tests/test_formal.py`
- Capability docs: `docs/capability-probes.md`
- Architecture status ledger: `docs/architecture-status.md`
- Existing temporary gap tracking: `plans/27-formal-proof-lifecycle.md`

## Plan of Work

1. Add a direct Aristotle CLI execution path inside the formal verifier.
2. Invoke that path only when the Hermes->MCP path fails in retryable ways.
3. Parse CLI output into the existing formal result contracts and transport artifacts.
4. Document the new fallback behavior and validate it with unit tests.

## Concrete Steps

1. Update `src/deep_gvr/formal.py` to detect retryable Hermes->MCP failures and attempt `aristotle submit --wait` when the CLI is installed and `ARISTOTLE_API_KEY` is present.
2. Add helpers to build the direct Aristotle prompt, parse the returned project id and tarball path, and extract Lean code plus summary text from the tarball.
3. Preserve the original Hermes->MCP failure details in the transport artifact, but overwrite the final transport status when the CLI fallback succeeds.
4. Extend `tests/test_formal.py` with coverage for fallback success, fallback unavailability, and transport-artifact provenance.
5. Update `docs/capability-probes.md` and `docs/architecture-status.md` so the fallback is explicit in the supported runtime behavior.

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Targeted validation:

```bash
uv run python -m unittest tests.test_formal -v
```

Acceptance evidence:

- A retryable Hermes->MCP Tier 3 failure can produce a proved result through direct Aristotle CLI fallback.
- The formal transport artifact records both the failed primary transport and the successful fallback transport.
- Existing structured unavailability behavior remains intact when neither path is runnable.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/aristotle-cli-fallback` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Fallback should not run when Hermes->MCP already returns a successful terminal proof result.
- Fallback artifacts must stay machine-readable and preserve the original failure context for debugging.
- If direct CLI fallback also fails, the verifier should return the original structured failure plus the fallback failure notes instead of inventing proof success.

## Interfaces and Dependencies

- Depends on local availability of the `aristotle` CLI and `ARISTOTLE_API_KEY` for the fallback path.
- Extends the Tier 3 transport artifact shape with direct-CLI provenance and extracted bundle metadata.
- Must remain compatible with the existing `FormalVerificationResultSet` and `Tier3ClaimResult` contracts.
