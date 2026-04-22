# 37 OpenGauss Unblock Diagnostics

## Purpose / Big Picture

Add a focused OpenGauss diagnostics slice that makes the current external blocker machine-visible without pretending plan 31 is unblocked. The user-visible outcome is a repo-local command and readiness probe that separate three different states cleanly: no local checkout, broken raw checkout, and healthy installed `gauss` runtime.

## Branch Strategy

Start from `main` and implement this slice on `codex/opengauss-unblock-diagnostics`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result again, push `main`, confirm CI, and delete the feature branch when it is no longer needed.

## Commit Plan

- `add opengauss diagnostics surface`
- `document opengauss unblock workflow`

## Progress

- [x] Review the existing OpenGauss plan, architecture ledger, and local probe surface.
- [x] Reproduce the current local failure mode from the OpenGauss checkout and the Morph targets.
- [x] Add this plan and index it from `plans/README.md`.
- [x] Implement a blocked-state OpenGauss inspection/probe plus a dedicated diagnostics script.
- [x] Update docs and tests to point operators at the new diagnostics path.
- [x] Run the required repo validation commands.
- [ ] Merge locally, revalidate on `main`, push, confirm CI, and delete the feature branch.

## Surprises & Discoveries

- The current Morph targets still redirect first, so a shallow status check can look healthier than the real final result. Following the redirect still lands on `404`.
- The raw OpenGauss checkout on this machine still fails earlier than any Lean/Gauss workflow validation because required Python dependencies are missing. The exact missing import depends on the local partial environment state; the latest diagnostics run hit `prompt_toolkit`.
- This is useful repo-owned work even though plan 31 remains blocked, because it lets operators distinguish an upstream installer/distribution failure from a deep-gvr backend-integration gap.

## Decision Log

- Keep plan 31 as the owning architecture slice for real OpenGauss backend integration.
- Land this as a support slice rather than partial OpenGauss transport work.
- Add a new blocked-state probe and diagnostics command instead of weakening the existing architecture target.
- Do not add OpenGauss as a supported Tier 3 release backend in this slice.

## Outcomes & Retrospective

- Added a blocked-state `opengauss_transport` capability probe so the missing local runtime is visible in the standard readiness surface.
- Added `scripts/diagnose_opengauss.py`, which records local checkout state, optional `./gauss doctor` output, and the final Morph target status in one report.
- At the time of this slice, the raw checkout still failed before real Gauss validation and both the default and README-pinned Morph targets still ended in `404` after redirects.
- Plan 71 later superseded that external-blocker conclusion: the official installer and published Morph targets are healthy again, and the diagnostics surface now needs to keep installed-runtime readiness distinct from raw-checkout failures.

## Context and Orientation

- Open architecture item: `docs/architecture-status.md`
- Existing blocked slice: `plans/31-opengauss-formal-backend.md`
- Probe surface: `src/deep_gvr/probes.py`
- Tier 3 inspection helpers: `src/deep_gvr/formal.py`
- Operator checks: `scripts/run_capability_probes.py`, `scripts/release_preflight.py`

## Plan of Work

1. Add a short, explicit OpenGauss diagnostics plan and index entry.
2. Implement a local OpenGauss inspection helper and capability probe.
3. Add a dedicated diagnostics script that can optionally run the raw checkout doctor and probe the published Morph targets.
4. Update docs and tests so the blocked state is explicit and actionable.

## Concrete Steps

1. Add `plans/37-opengauss-unblock-diagnostics.md` and index it in `plans/README.md`.
2. Extend the Tier 3 inspection helpers with an `inspect_opengauss_transport` function that reports local checkout, launcher, installed `gauss`, and config state without attempting real backend integration.
3. Add an `opengauss_transport` capability probe and wire it into `scripts/run_capability_probes.py`.
4. Add `scripts/diagnose_opengauss.py` with human-readable and JSON output, optional `./gauss doctor` execution, and optional Morph target probing.
5. Update the release preflight guidance for `backend: opengauss` so it points to diagnostics instead of the generic “not implemented” message.
6. Update the relevant docs and tests.

## Validation and Acceptance

Required validation:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Targeted validation:

```bash
uv run python scripts/diagnose_opengauss.py --json
```

Acceptance evidence:

- `scripts/run_capability_probes.py` reports a dedicated OpenGauss blocked-state probe instead of silently omitting OpenGauss.
- `scripts/diagnose_opengauss.py` reports the local checkout and installed-runtime state in a machine-readable way.
- The docs explain the current OpenGauss state precisely, and the unblock path is explicit and reproducible.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/opengauss-unblock-diagnostics` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Re-running the diagnostics script should not mutate the local OpenGauss checkout.
- Capability probe output should stay deterministic for the same local environment.
- If the upstream installer path changes again, this slice should make that visible through a localized script/doc update rather than another architecture-wide rewrite.

## Interfaces and Dependencies

- Depends on the existing Tier 3 inspection pattern in `src/deep_gvr/formal.py`.
- Adds only diagnostics and blocked-state visibility; it does not add OpenGauss as a shipped formal backend.
- May perform optional network checks against `morph.new` only inside the explicit diagnostics script, not inside the standard probe path.
