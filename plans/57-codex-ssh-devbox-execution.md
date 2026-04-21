# 57 Codex SSH Devbox Execution

## Purpose / Big Picture

Expand the Codex backend work so the existing `ssh/devbox` surface is no longer only a prompt/export bundle plus preflight report. The user-visible outcome is that a remote Codex SSH/devbox session can gate and execute the native `codex_local` backend from the stronger machine, while still reusing the existing typed runtime, evidence system, and Tier 2/Tier 3 backend contracts.

This slice should make the docs honest in the stronger direction: the repo still does not provision Codex remote sessions, but once the operator is already on a remote Codex SSH/devbox machine, the repo now supports a real runtime-backed execution path there.

## Branch Strategy

Start from `main` and implement this slice on `codex/codex-ssh-devbox-execution`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result again, push `main`, confirm CI and Docs, and delete the feature branch when it is no longer needed.

## Commit Plan

- `add codex ssh devbox runtime gate`
- `wire codex ssh devbox release surface`
- `document codex ssh devbox execution`

## Progress

- [x] Draft the plan and index it from `plans/README.md`.
- [x] Add a runtime-backed Codex SSH/devbox execution helper over the native `codex_local` backend.
- [x] Make `--ssh-devbox` preflight backend-sensitive instead of hardcoding SSH Tier 2 readiness.
- [x] Add targeted tests for backend gating and remote execution helpers.
- [ ] Run validation, merge locally, revalidate on `main`, push, confirm CI and Docs, and delete the feature branch.

## Surprises & Discoveries

- Plan 53 explicitly stopped at a narrow repo-owned surface: prompt bundle, export helper, and preflight. That was intentional at the time, but it left the remote Codex path underspecified after the native `codex_local` backend landed in plan 56.
- The current `--ssh-devbox` preflight check was still effectively “is the SSH Tier 2 backend ready?”, which is too narrow once the remote machine itself can be the strong execution host for the native Codex backend.
- The cleanest runtime expansion is not a third orchestrator backend. A remote Codex SSH/devbox session is still the same `codex_local` backend, just running on a stronger machine.

## Decision Log

- Decision: keep the orchestrator backend set to `codex_local` for remote Codex execution rather than inventing a separate `codex_ssh_devbox` backend.
- Decision: make the remote preflight require `runtime.orchestrator_backend=codex_local` and evaluate the selected Tier 2 backend, not blindly the SSH Tier 2 backend.
- Decision: ship a dedicated `scripts/codex_ssh_devbox_run.py` helper that gates on remote Codex preflight before invoking the existing run/resume runtime entrypoints.
- Decision: keep the repo honest that it still does not provision Codex remote sessions itself.

## Outcomes & Retrospective

- Added a runtime-backed Codex SSH/devbox execution helper over the native `codex_local` backend.
- Expanded Codex preflight so the remote path now checks for the native Codex backend plus the selected Tier 2 backend, instead of treating SSH Tier 2 as the only legitimate remote path.
- Updated the human-facing docs and release metadata so the remote Codex path is described as a real execution mode rather than a prompt-only add-on.

## Context and Orientation

- Existing remote-surface plan: `plans/53-codex-ssh-devbox-surface.md`
- Native Codex backend prerequisite: `plans/56-codex-local-backend.md`
- Runtime integration points:
  - `src/deep_gvr/orchestrator.py`
  - `src/deep_gvr/cli.py`
  - `src/deep_gvr/release_surface.py`
- Existing Codex remote bundle:
  - `codex_ssh_devbox/catalog.json`
  - `docs/codex-ssh-devbox.md`

## Plan of Work

1. Add a runtime-backed helper that gates on Codex SSH/devbox readiness and then invokes the existing native `codex_local` runtime path.
2. Fix the remote preflight semantics so they reflect the selected orchestrator backend and selected Tier 2 backend.
3. Update the checked-in prompt bundle, release metadata, and public/operator docs so the remote Codex execution path is discoverable and enforced.

## Concrete Steps

1. Add a new runtime helper module plus a script entrypoint for:
   - remote preflight gating
   - `run`
   - `resume`
2. Extend `src/deep_gvr/release_surface.py` so `ssh/devbox` readiness:
   - requires `runtime.orchestrator_backend=codex_local`
   - uses the selected Tier 2 backend as the readiness source of truth
   - stays explicit when Tier 2 is disabled
3. Update:
   - `release/agentskills.publication.json`
   - `README.md`
   - `docs/codex-local.md`
   - `docs/codex-ssh-devbox.md`
   - `docs/quickstart.md`
   - `docs/system-overview.md`
   - `docs/deep-gvr-architecture.md`
   - `docs/architecture-status.md`
4. Update the checked-in Codex SSH/devbox catalog and prompt templates so they point at the runtime-backed remote execution helper.
5. Add targeted tests for:
   - remote preflight readiness with `codex_local` plus selected local backend
   - remote preflight blocked state when the backend is not `codex_local`
   - runtime-backed remote execution helper success and help output

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
uv run python scripts/codex_preflight.py --ssh-devbox --json
uv run python scripts/codex_ssh_devbox_run.py run --help
uv run python -m unittest tests.test_codex_ssh_devbox_runtime tests.test_release_scripts tests.test_cli -v
```

Acceptance evidence:

- The repo ships a runtime-backed remote Codex execution helper for `run` and `resume`.
- `--ssh-devbox` preflight blocks when the orchestrator backend is not `codex_local`.
- `--ssh-devbox` preflight can report ready for either a strong remote local backend or another selected Tier 2 backend.
- Public/operator docs describe the remote Codex path as a real execution mode without claiming repo-managed session provisioning.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/codex-ssh-devbox-execution` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions and Docs runs for the pushed head are green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- The new remote execution helper must fail explicitly with preflight details instead of trying to limp through a blocked remote path.
- The helper should reuse the existing runtime commands and evidence flow rather than creating a second session artifact system.
- Remote readiness must continue to rely on repo-owned runtime/probe truth, not on prompt text alone.

## Interfaces and Dependencies

- Depends on the native `codex_local` backend from `plans/56-codex-local-backend.md`.
- Depends on the checked-in Codex SSH/devbox surface from `plans/53-codex-ssh-devbox-surface.md`.
- Depends on the existing Tier 2 backend readiness probe and release/codex preflight surfaces.
- Must remain aligned with the same evidence directories, checkpoint artifacts, and runtime config schema already used by the main CLI and Codex-local backend.
