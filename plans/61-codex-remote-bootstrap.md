# 61 Codex Remote Bootstrap

## Purpose / Big Picture

Strengthen the Codex SSH/devbox path so `deep-gvr` does more than gate and
document remote execution. The goal is to make a stronger remote machine easier
to use as a first-class validator and simulation host without pretending that
the repo provisions Codex SSH/devbox sessions itself.

## Branch Strategy

Start from `main` and implement this slice on `codex-remote-bootstrap`. The
intended branch name was `codex/codex-remote-bootstrap`, but this checkout's
local git ref layout rejected nested `codex/...` branch creation, so the slice
uses the closest `codex-` prefixed branch instead. Merge back into `main`
locally with a fast-forward only after branch validation passes, then validate
the merged result again, push `main`, confirm CI and Docs, and delete the
feature branch when it is no longer needed.

## Commit Plan

- `plan codex remote bootstrap`
- `add codex remote bootstrap helpers`
- `document codex remote bootstrap`

## Progress

- [x] Validate the current remote bootstrap pain points from the SSH/devbox path.
- [x] Add repo-owned helpers for remote environment materialization where the
      boundary is honest.
- [x] Update remote preflight/docs accordingly.

## Surprises & Discoveries

- The local git ref layout in this checkout refused nested `codex/...` branch
  creation even though the repo normally uses that naming convention, so this
  slice used `codex-remote-bootstrap`.
- The strongest repo-owned remote bootstrap boundary is not remote session
  provisioning; it is config sync plus local surface installation plus the same
  typed preflight report already used elsewhere.

## Decision Log

- Decision: keep session provisioning and Codex SSH/devbox creation out of
  scope; focus on repo-owned remote environment readiness and repeatability.
- Decision: implement remote bootstrap as a dedicated script and typed report
  rather than extending `codex_preflight.py` with mutation flags. That keeps
  preflight read-only and makes bootstrap actions auditable.
- Decision: normalize `runtime.orchestrator_backend=codex_local` during remote
  bootstrap. The helper is for the Codex SSH/devbox path specifically, so that
  mutation is part of the contract rather than a surprising side effect.
- Decision: treat Hermes install as policy-driven during remote bootstrap. Skip
  it by default when the remote config does not require it, but keep Aristotle
  and explicit operator overrides able to refresh the Hermes surface.

## Outcomes & Retrospective

- The repo now ships `scripts/codex_remote_bootstrap.py` plus
  `src/deep_gvr/codex_remote_bootstrap.py` as a rerunnable remote-machine
  bootstrap path for Codex SSH/devbox operators.
- The helper can create or sync the runtime config, normalize the backend to
  `codex_local`, install the Codex skill surface, optionally export a standalone
  plugin root, ensure the evidence directory exists, and then emit the nested
  `--ssh-devbox` preflight report.
- The public/operator docs, release manifest, schemas, templates, and tests now
  treat that bootstrap report as part of the supported Codex remote surface.

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
