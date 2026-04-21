# 61 Codex Remote Bootstrap

## Purpose / Big Picture

Strengthen the Codex SSH/devbox path so `deep-gvr` does more than gate and
document remote execution. The goal is to make a stronger remote machine easier
to use as a first-class validator and simulation host without pretending that
the repo provisions Codex SSH/devbox sessions itself.

## Branch Strategy

Start from `main` and implement this slice on `codex/codex-remote-bootstrap`.
Merge back into `main` locally with a fast-forward only after branch validation
passes, then validate the merged result again, push `main`, confirm CI and
Docs, and delete the feature branch when it is no longer needed.

## Commit Plan

- `plan codex remote bootstrap`
- `add codex remote bootstrap helpers`
- `document codex remote bootstrap`

## Progress

- [ ] Validate the current remote bootstrap pain points from the SSH/devbox path.
- [ ] Add repo-owned helpers for remote environment materialization where the
      boundary is honest.
- [ ] Update remote preflight/docs accordingly.

## Surprises & Discoveries

- Pending.

## Decision Log

- Decision: keep session provisioning and Codex SSH/devbox creation out of
  scope; focus on repo-owned remote environment readiness and repeatability.

## Outcomes & Retrospective

- Pending implementation.

## Context and Orientation

- `docs/codex-ssh-devbox.md`
- `scripts/codex_ssh_devbox_run.py`
- `scripts/codex_preflight.py`
- `src/deep_gvr/release_surface.py`

## Plan of Work

1. Identify the remote machine state that is still too manual for the current
   Codex SSH/devbox path.
2. Add repo-owned bootstrap helpers and checks for that state.
3. Tighten docs and preflight so remote operators know exactly what is ready and
   what is still missing.

## Concrete Steps

1. Add a remote bootstrap helper or helper set for:
   - syncing runtime config
   - ensuring Codex-local skill/plugin assets are available remotely
   - checking Tier 2/Tier 3 backend dependencies on the remote host
2. Extend Codex preflight and/or the SSH/devbox runner to surface bootstrap
   deltas more explicitly.
3. Update public/operator docs with a concrete remote bootstrap path.

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
uv run mkdocs build --strict
```

Acceptance evidence:

- Remote bootstrap state is easier to materialize and audit from repo-owned
  helpers.
- The SSH/devbox docs and preflight surface become less hand-wavy.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/codex-remote-bootstrap` into `main` locally only
  after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm CI and Docs are green.
- Delete the feature branch when it is no longer needed.

## Idempotence and Recovery

- Bootstrap helpers should be rerunnable and explicit about what they did or did
  not change.
- Keep repo-owned remote bootstrap separate from Codex product session
  provisioning.

## Interfaces and Dependencies

- Depends on the current Codex SSH/devbox execution path.
- Depends on operator access to an SSH/devbox-capable remote machine.
