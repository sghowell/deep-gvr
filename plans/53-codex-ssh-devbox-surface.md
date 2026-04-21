# 53 Codex SSH Devbox Surface

## Purpose / Big Picture

Add a first-class Codex `ssh/devbox` operator surface for `deep-gvr`. This slice should make remote validator and simulation-heavy use explicit and supportable without pretending that the repo provisions Codex remote sessions itself.

The repo-owned outcome is:

- a checked-in Codex `ssh/devbox` prompt bundle tailored to remote validator work
- export and install helpers for that bundle
- a dedicated Codex preflight mode for `ssh/devbox` operator readiness
- public/operator docs that describe the remote path clearly and honestly

## Branch Strategy

Start from `main` and implement this slice on `codex/codex-ssh-devbox-surface`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result again, push `main`, confirm CI, and delete the feature branch when it is no longer needed.

## Commit Plan

- `add codex ssh devbox bundle`
- `wire codex ssh devbox preflight`
- `document codex ssh devbox surface`

## Progress

- [x] Draft the plan and index it from `plans/README.md`.
- [x] Add the checked-in Codex `ssh/devbox` bundle, export helper, schema, and tests.
- [x] Add a dedicated Codex preflight mode for `ssh/devbox` operator readiness.
- [x] Update release metadata, repo checks, and public/operator docs.
- [ ] Run validation, merge locally, revalidate on `main`, push, confirm CI, and delete the feature branch.

## Surprises & Discoveries

- The repo already mentions `ssh/devbox` use in the review/QA pack and Codex-local docs, but it does not yet ship a dedicated remote-operator surface or a remote-specific preflight path.
- The strongest repo-owned boundary is still a checked-in bundle plus preflight/docs. The repo should not claim to create or manage Codex SSH/devbox sessions directly.
- `deep-gvr` already has a real Tier 2 SSH backend readiness probe, so the Codex remote surface can reuse existing backend evidence instead of inventing another remote-state mechanism.

## Decision Log

- Decision: ship the Codex `ssh/devbox` surface as a checked-in prompt bundle plus export helper, following the same repo-owned pattern as the automation and review/QA surfaces.
- Decision: add a dedicated `--ssh-devbox` Codex preflight mode that requires the SSH Tier 2 path to be ready when the operator explicitly wants the remote-validator path.
- Decision: keep the docs explicit that the repo supports operating from Codex over SSH/devboxes, but does not provision the Codex remote environment itself.

## Outcomes & Retrospective

- Added a checked-in Codex `ssh/devbox` bundle at `codex_ssh_devbox/` plus an export helper at `scripts/export_codex_ssh_devbox.py`.
- Added a dedicated `--ssh-devbox` Codex preflight mode that turns the existing SSH Tier 2 backend evidence into an explicit remote-operator readiness report.
- Updated release metadata, repo checks, tests, and public/operator docs so the remote path is enforced instead of implied.

## Context and Orientation

- Existing Codex local surface: `codex_skill/SKILL.md`, `scripts/install_codex.sh`, `scripts/codex_preflight.py`
- Existing Codex review/QA pack: `codex_review_qa/catalog.json`, `docs/codex-review-qa.md`
- Existing Tier 2 SSH readiness probe: `src/deep_gvr/probes.py`
- Existing release surface enforcement: `src/deep_gvr/release_surface.py`, `src/deep_gvr/repo_checks.py`

## Plan of Work

1. Add a checked-in Codex `ssh/devbox` bundle for remote validator and backend-triage work.
2. Add a dedicated preflight mode that turns the existing SSH backend evidence into an explicit Codex remote-operator readiness report.
3. Update release metadata, repo checks, and docs so the new surface is enforced and discoverable.

## Concrete Steps

1. Add:
   - `codex_ssh_devbox/catalog.json`
   - `codex_ssh_devbox/templates/remote_validator_run.prompt.md`
   - `codex_ssh_devbox/templates/remote_backend_triage.prompt.md`
   - `src/deep_gvr/codex_ssh_devbox.py`
   - `scripts/export_codex_ssh_devbox.py`
   - matching schema/template/test coverage
2. Extend `scripts/install_codex.sh` with `--ssh-devbox-root <dir>`.
3. Extend `scripts/codex_preflight.py` and `src/deep_gvr/release_surface.py` with a `--ssh-devbox` mode that requires SSH Tier 2 readiness.
4. Update `release/agentskills.publication.json`, `src/deep_gvr/repo_checks.py`, and public/operator docs.

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
uv run python scripts/export_codex_ssh_devbox.py --output-root /tmp/deep-gvr-codex-ssh-devbox --force --json
uv run python scripts/codex_preflight.py --json
uv run python scripts/codex_preflight.py --ssh-devbox --json
```

Acceptance evidence:

- The repo contains a checked-in Codex `ssh/devbox` bundle and export helper.
- Codex preflight can report the remote-validator path explicitly with `--ssh-devbox`.
- Release/preflight/repo checks fail if the new surface drifts or disappears.
- Public/operator docs explain what the Codex `ssh/devbox` surface is and what it is not.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/codex-ssh-devbox-surface` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions runs for the pushed head are green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- The export helper should be rerunnable and refuse to overwrite existing exports without `--force`.
- The `--ssh-devbox` preflight mode should reuse existing backend probe logic instead of creating a second source of truth for SSH readiness.
- If the operator environment does not configure the Tier 2 SSH backend, report that explicitly instead of weakening the remote path into a docs-only claim.

## Interfaces and Dependencies

- Depends on the existing Codex local surface and installer.
- Depends on the Tier 2 SSH backend readiness probe in `src/deep_gvr/probes.py`.
- Depends on Codex product support for SSH/devbox-connected sessions, but the repo should stay honest that it does not provision that environment itself.
