# 50 Hermes v0.10 Plan-26 Recheck

## Purpose / Big Picture

Recheck the two externally blocked plan-26 capabilities against Hermes Agent v0.10.0 before treating them as still blocked for the next release cycle. The goal is to reuse the repo-local reassessment harness from plan 45, record the actual v0.10 result, and update the architecture/docs surface based on observed evidence rather than release-note interpretation.

This slice is diagnostic, not aspirational. It should not claim plan 26 is closed unless real runtime evidence shows that the delegated Hermes path now produces distinct subagent routes and delegated verifier-side MCP access.

## Branch Strategy

Start from `main` and implement this slice on `codex/hermes-v0.10-plan26-recheck`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result again, push `main`, confirm CI, and delete the feature branch when it is no longer needed.

## Commit Plan

- `add hermes v0.10 recheck plan`
- `record hermes v0.10 reassessment result`
- `document hermes v0.10 blocker state`

## Progress

- [x] Draft the reassessment plan and index it from `plans/README.md`.
- [x] Run the reassessment against the local Hermes v0.10 install and record the result.
- [x] Update plan-26-facing docs with the new v0.10 findings.
- [x] Run full validation.
- [ ] Merge locally, revalidate on `main`, push, confirm CI, and delete the feature branch.

## Surprises & Discoveries

- Hermes v0.10.0 is installed locally on this machine (`Hermes Agent v0.10.0 (2026.4.16)`).
- The official v0.10.0 release is primarily a Tool Gateway release. The release notes do not explicitly claim delegated per-subagent model override or delegated MCP inheritance closure.
- The existing `scripts/reassess_plan26.py` harness is already the right mechanism for this recheck; a new probe path would just create another source of truth.
- The live v0.10 run did not change the blocker state: both delegated checks still timed out after 180 seconds and returned no observed `capability_evidence`.

## Decision Log

- Decision: reuse the existing reassessment harness instead of building another live-check command.
- Decision: keep plan 26 blocked until observed runtime evidence, not Hermes marketing/release-note language, proves otherwise.

## Outcomes & Retrospective

- Achieved: re-used the existing reassessment harness without adding another live-check path.
- Current result: the local Hermes v0.10 reassessment report is still `environment_blocked`, with both delegated checks timing out after 180 seconds and no observed capability closure.
- Evidence: `/tmp/deep-gvr-plan26-v0.10-report.json`
- Conclusion: plan 26 remains `blocked_external`; v0.10 did not produce observed route or delegated-MCP closure on this machine.

## Context and Orientation

- Existing reassessment harness: `scripts/reassess_plan26.py`
- Previous reassessment slice: `plans/45-hermes-v0.9-capability-reassessment.md`
- Capability docs: `docs/capability-probes.md`
- Blocked architecture item: `plans/26-subagent-capability-closure.md`

## Plan of Work

1. Run the existing reassessment harness against Hermes v0.10.
2. Save the report under `/tmp` with an explicit v0.10-specific output name.
3. Update the plan-26-facing docs and architecture ledger with the observed result.

## Concrete Steps

1. Run:
   - `hermes --version`
   - `uv run python scripts/reassess_plan26.py --json --output /tmp/deep-gvr-plan26-v0.10-report.json`
2. Inspect the structured report for:
   - Hermes version
   - route-focused delegated result
   - verifier-MCP-focused delegated result
   - observed `capability_evidence`
   - reassessment conclusion
3. Update `plans/26-subagent-capability-closure.md`, `docs/capability-probes.md`, and `docs/architecture-status.md` with the v0.10 result.
4. Run the standard repo validation set.

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Targeted validation:

```bash
hermes --version
uv run python scripts/reassess_plan26.py --json --output /tmp/deep-gvr-plan26-v0.10-report.json
```

Acceptance evidence:

- The repo records the actual Hermes v0.10 reassessment result in repo-local docs.
- The architecture ledger and plan-26-facing docs state whether v0.10 changed the blocker status.
- No new runtime claims are added without observed `capability_evidence`.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/hermes-v0.10-plan26-recheck` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions runs for the pushed head are green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- The reassessment command should stay rerunnable; each invocation should write a fresh isolated temp config and report.
- If the live reassessment fails for environment or provider reasons, record that explicitly instead of inferring a Hermes capability result.
- If v0.10 still does not close the blocker, leave plan 26 as `blocked_external` and capture the exact evidence.

## Interfaces and Dependencies

- Depends on the delegated runtime surface in `src/deep_gvr/orchestrator.py` and `src/deep_gvr/cli.py`.
- Depends on a working Hermes CLI plus a configured local provider environment for live reassessment.
- Must keep capability probes, docs, and observed evidence semantics aligned with plan 26.
