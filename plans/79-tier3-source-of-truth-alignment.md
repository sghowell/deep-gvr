# 79 Tier 3 Source of Truth Alignment

## Purpose / Big Picture

Align the repo's Tier 3 source-of-truth surfaces after the OpenGauss backend
became a shipped bounded local CLI backend. The user-visible outcome is that the
Hermes skill, public docs, architecture ledger, support roadmap, and repo checks
all agree that Aristotle, MathCode, and OpenGauss are shipped Tier 3 backends
with different lifecycle contracts.

## Branch Strategy

Start from `main` on `codex/tier3-source-of-truth-alignment`. Merge back into
`main` locally with a fast-forward only after branch validation passes, then
validate the merged result again, push `main`, confirm CI and Docs, and delete
the feature branch when it is no longer needed.

## Commit Plan

- `plan tier3 source of truth alignment`
- `align tier3 source of truth`

## Progress

- [x] Add this plan and index it from `plans/README.md`.
- [ ] Align `SKILL.md`, public docs, architecture status, and roadmap plans with
      the shipped Tier 3 backend set.
- [ ] Add semantic repo-check coverage for the canonical Tier 3 shipped-backend
      contract.
- [ ] Run validation, merge locally, revalidate on `main`, push, confirm CI and
      Docs, and delete the feature branch.

## Surprises & Discoveries

- Pending implementation.

## Decision Log

- Treat the canonical shipped Tier 3 backend set as Aristotle, MathCode, and
  OpenGauss.
- Keep lifecycle language precise: Aristotle has submission, polling, and
  checkpointed resume; MathCode and OpenGauss are bounded local CLI paths.
- Keep delegated verifier-direct MCP as a separate external blocker under plan
  26. OpenGauss source-of-truth alignment must not weaken that separate open
  item.

## Outcomes & Retrospective

- Pending implementation.

## Context and Orientation

- Tier 3 runtime and probes:
  - `src/deep_gvr/formal.py`
  - `src/deep_gvr/probes.py`
  - `src/deep_gvr/release_surface.py`
- Source-of-truth docs:
  - `SKILL.md`
  - `docs/architecture-status.md`
  - `docs/tier2-tier3-support-matrix.md`
  - `docs/system-overview.md`
  - `docs/concepts.md`
  - `docs/examples.md`
  - `docs/plugin-privacy.md`
  - `plans/67-tier2-tier3-completion-roadmap.md`
  - `plans/71-tier3-completion-and-opengauss-unblock.md`
- Repo guardrails:
  - `src/deep_gvr/repo_checks.py`
  - `tests/test_repo_checks.py`

## Plan of Work

1. Remove stale language that says OpenGauss is externally blocked, merely
   planned, or outside the shipped Tier 3 path.
2. Normalize public docs so they describe the three shipped formal backends and
   their lifecycle differences consistently.
3. Update roadmap closeout state now that plan 72 and plan 31 are realized.
4. Add a semantic repo check that rejects the stale phrases and requires the
   canonical Tier 3 support statement in the key source-of-truth files.

## Concrete Steps

1. Update `SKILL.md` so Hermes operators treat OpenGauss as shipped when the
   installed `gauss` runtime and config are ready.
2. Update public docs and architecture status to name Aristotle, MathCode, and
   OpenGauss together where the shipped Tier 3 backend set is described.
3. Update plans 67 and 71 so their progress, discoveries, decisions, outcomes,
   and recovery notes match the current completed Tier 3 and parity state.
4. Add `check_tier3_source_of_truth()` to `src/deep_gvr/repo_checks.py` and a
   focused regression test that proves stale OpenGauss-blocked language is
   caught.
5. Run:
   - `uv run python scripts/check_repo.py`
   - `uv run python scripts/run_capability_probes.py --json`
   - `uv run python -m unittest discover -s tests -v`
   - `uv run mkdocs build --strict`

## Validation and Acceptance

Required validation:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py --json
uv run python -m unittest discover -s tests -v
uv run mkdocs build --strict
```

Acceptance evidence:

- No source-of-truth doc describes OpenGauss as blocked, merely planned, or
  outside the shipped Tier 3 backend set.
- Public docs consistently name Aristotle, MathCode, and OpenGauss as the
  shipped Tier 3 backends.
- Repo checks fail on the stale OpenGauss-blocked wording that triggered this
  slice.
- Existing capability probes and deterministic tests remain green.

## Merge, Push, and Cleanup

- Stage and commit the plan/index update first with
  `plan tier3 source of truth alignment`.
- Stage and commit the docs/check/test alignment with
  `align tier3 source of truth`.
- Validate the feature branch before merge.
- Fast-forward merge `codex/tier3-source-of-truth-alignment` into `main`
  locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the remote CI and Docs workflows are green.
- Delete the local feature branch, and delete the remote feature branch too if
  one was created.

## Idempotence and Recovery

- Re-running this slice should keep the same canonical Tier 3 backend set:
  Aristotle, MathCode, and OpenGauss.
- If a future backend is added or removed, update the semantic repo check in the
  same branch as the docs and support matrix.
- If OpenGauss is unavailable in a particular operator environment, describe it
  as an environment readiness failure, not as an unshipped backend.

## Interfaces and Dependencies

- Depends on the completed OpenGauss formal backend slice in
  `plans/31-opengauss-formal-backend.md`.
- Depends on the completed Codex-Hermes parity slice in
  `plans/72-codex-hermes-backend-parity.md`.
- Does not change Tier 3 runtime behavior; it aligns docs, roadmap state, and
  repo guardrails with the behavior already shipped.
