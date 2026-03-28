# 30 Release Surface Completion

## Purpose / Big Picture

Finish the public Hermes release surface promised by the architecture: packaging, install and preflight, operator validation, and agentskills.io-ready publication assets. This slice turns the current repo from an internally complete harness into a release-complete skill bundle.

## Branch Strategy

Start from `main` and implement this slice on `codex/release-surface-completion`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result, push `main`, confirm CI, and delete the feature branch.

## Commit Plan

- `add release preflight and packaging`
- `prepare publication assets`
- `document public release workflow`

## Progress

- [ ] Add the new plan and index it from `plans/README.md`.
- [ ] Complete install, preflight, and operator validation for the intended public surface.
- [ ] Add the publication assets and release docs for Hermes and agentskills.io.
- [ ] Update repo checks and CI for release-surface completeness.

## Surprises & Discoveries

- The repo already has a strong local install story; the missing work is the publication-grade packaging and operator-validation layer around it.
- This slice is also the right place to document the opt-in `auto_improve` policy promised by the architecture.

## Decision Log

- Release completion includes publication assets, not only local install helpers.
- Operator preflight must validate provider credentials, MCP readiness, backend readiness, and config shape.
- Public release docs must match the actual completed runtime path from earlier slices.

## Outcomes & Retrospective

- Pending implementation.

## Context and Orientation

- Current install helpers: `scripts/install.sh`, `scripts/setup_mcp.sh`
- Public docs: `README.md`, `SKILL.md`
- CI surface: `.github/workflows/ci.yml`
- Architecture ledger item: `release-surface-completion`

## Plan of Work

1. Complete the operator preflight and install workflow.
2. Add publication-ready packaging and release assets.
3. Document the public release process and opt-in improvement policy.
4. Update repo checks and CI so the release surface stays complete.

## Concrete Steps

1. Expand install and setup helpers into a full release preflight surface.
2. Add publication metadata or assets required for the Hermes/agentskills.io distribution model.
3. Update docs for install, preflight, troubleshooting, and release publishing.
4. Add CI or repo checks that enforce the release surface requirements.

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Targeted validation:

```bash
bash scripts/install.sh
bash scripts/setup_mcp.sh --install --check
```

Acceptance evidence:

- The repo ships a release-ready install and preflight path.
- Publication assets exist for the intended Hermes/agentskills.io surface.
- Operator docs and CI enforce the release-ready workflow.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/release-surface-completion` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Keep release preflight safe to re-run.
- Ensure publication metadata is derived from repo-local truth rather than hand-maintained one-off notes.
- Do not publish until the runtime-completion slices it depends on are actually done.

## Interfaces and Dependencies

- Depends on completed runtime, evidence, and backend slices.
- Touches install/preflight scripts, docs, CI, and any publication metadata.
- Owns the public release workflow and opt-in `auto_improve` documentation.
