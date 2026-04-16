# 45 Hermes v0.9 Capability Reassessment

## Purpose / Big Picture

Reassess the two externally blocked plan-26 capabilities against Hermes Agent v0.9.0 before treating them as still blocked or resuming deeper release work. The goal is to turn this from ad hoc manual checking into a repeatable repo-local reassessment path that can prove whether Hermes now supports real delegated per-subagent routing and delegated verifier-side MCP access.

This slice is diagnostic and enabling. It should not claim plan 26 is closed unless real runtime evidence shows that the delegated Hermes path now produces the required observed behavior.

## Branch Strategy

Start from `main` and implement this slice on `codex/hermes-v0.9-capability-reassessment`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result again, push `main`, confirm CI, and delete the feature branch when it is no longer needed.

## Commit Plan

- `add hermes v0.9 reassessment plan`
- `add delegated capability reassessment harness`
- `document hermes v0.9 reassessment workflow`

## Progress

- [x] Draft the reassessment plan and index it from `plans/README.md`.
- [x] Add a reusable reassessment script for the two blocked plan-26 capabilities.
- [x] Add tests for the reassessment config/report logic.
- [x] Run the reassessment against the local Hermes v0.9 install and record the result.
- [x] Update plan-26-facing docs with the new reassessment path and findings.
- [x] Run full validation.
- [ ] Merge locally, revalidate on `main`, push, confirm CI, and delete the feature branch.

## Surprises & Discoveries

- Hermes v0.9.0 is installed locally on this machine (`Hermes Agent v0.9.0 (2026.4.13)`).
- The v0.9 CLI surface adds features that may matter to deep-gvr, but the release notes do not explicitly claim delegated per-subagent model override or delegated MCP inheritance closure.
- The current repo already has the internal contract surface needed for reassessment: delegated `role_routes`, `capability_evidence`, transcript capture, and probe-driven readiness accounting.
- The first real Hermes v0.9 reassessment did not close either blocker: both the route-focused and verifier-MCP-focused delegated runs timed out after 180 seconds and returned no observed `capability_evidence`.

## Decision Log

- Decision: add a dedicated reassessment harness instead of relying on free-form manual `hermes chat` runs.
- Decision: keep plan 26 blocked until observed runtime evidence, not release-note interpretation, proves otherwise.
- Decision: separate the two capability checks into a route-focused run and a verifier-MCP-focused run so failures are attributable.

## Outcomes & Retrospective

- Achieved: the repo now has a repeatable reassessment harness at `scripts/reassess_plan26.py`.
- Achieved: the reassessment harness writes isolated temp configs plus a structured JSON report instead of relying on free-form manual Hermes sessions.
- Current result: the first local Hermes v0.9 reassessment report is `environment_blocked`, with both delegated checks timing out after 180 seconds and no observed capability closure.
- Evidence: `/tmp/deep-gvr-plan26-v0.9-report.json`
- Validation completed successfully with:
  - `uv run python scripts/check_repo.py`
  - `uv run python scripts/run_capability_probes.py`
  - `uv run python -m unittest discover -s tests -v`

## Context and Orientation

- Plan 26 target: `plans/26-subagent-capability-closure.md`
- Capability docs: `docs/capability-probes.md`
- Delegated runtime: `src/deep_gvr/orchestrator.py`, `src/deep_gvr/cli.py`
- Probe logic: `src/deep_gvr/probes.py`

## Plan of Work

1. Add a repeatable reassessment harness that exercises the delegated runtime with capability-evidence capture.
2. Run one routing-focused check and one verifier-MCP-focused check against Hermes v0.9.
3. Update plan-26-facing docs based on observed evidence rather than assumptions.

## Concrete Steps

1. Add `scripts/reassess_plan26.py`:
   - capture Hermes version information
   - build temporary runtime configs that isolate the route and MCP checks
   - run delegated `deep-gvr` sessions with `--routing-probe ready`
   - emit a structured JSON report with summaries, errors, artifacts, and observed `capability_evidence`
2. Add tests for the temporary-config overlays and conclusion logic.
3. Run the script against the local Hermes v0.9 environment and save the report under `/tmp`.
4. Update `docs/capability-probes.md` and `plans/26-subagent-capability-closure.md` with the reassessment path and findings.
5. Run the standard repo validation set.

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Targeted validation:

```bash
uv run python scripts/reassess_plan26.py --json
```

Acceptance evidence:

- The repo has a repeatable reassessment command for plan 26.
- The reassessment output records Hermes version, the two delegated check results, and the observed `capability_evidence`.
- The plan-26-facing docs state whether Hermes v0.9 actually changed the blocker status.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/hermes-v0.9-capability-reassessment` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions runs for the pushed head are green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- The reassessment script should be rerunnable; each invocation should write a fresh isolated temp config and report.
- Capability closure remains blocked until observed runtime evidence says otherwise.
- If the live reassessment fails for environment or provider reasons, record that explicitly instead of inferring a Hermes capability result.

## Interfaces and Dependencies

- Depends on the delegated runtime surface in `src/deep_gvr/orchestrator.py` and `src/deep_gvr/cli.py`.
- Depends on a working Hermes CLI plus a configured local provider environment for live reassessment.
- Must keep capability probes, docs, and observed evidence semantics aligned with plan 26.
