# 46 Codex Local Surface

## Purpose / Big Picture

Add Codex local as a supported first-class operator surface for `deep-gvr` without creating a second orchestration core. The user-visible outcome should be a real Codex install path, a Codex-local operator preflight path, and public docs that treat Codex local as a supported surface rather than an implied workaround.

This slice should stay honest about the current architecture: Codex local is a peer operator surface over the existing typed runtime, while Hermes remains the delegated execution backend on the shipped path today.

## Branch Strategy

Start from `main` and implement this slice on `codex/codex-local-surface`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result again, push `main`, confirm CI, and delete the feature branch when it is no longer needed.

## Commit Plan

- `add codex local surface plans`
- `add codex install and preflight support`
- `document codex local operator surface`

## Progress

- [x] Review the current Hermes-only install, preflight, release-surface, and public-doc paths.
- [x] Confirm the local Codex CLI surface exists and can support a local first-class wrapper path.
- [x] Add this plan and index it from `plans/README.md`.
- [x] Add a Codex-local skill bundle plus install helper.
- [x] Add a Codex-local operator preflight surface and repo checks.
- [x] Update the public docs and architecture language to present Codex local as a supported peer surface.
- [x] Run full validation.
- [ ] Merge locally, revalidate on `main`, push, confirm CI, and delete the feature branch.

## Surprises & Discoveries

- The repo already has a clean typed runtime boundary, so Codex support does not require a second orchestration implementation.
- The local `codex` CLI is present and exposes a stable `exec` surface, which is enough for a documented non-interactive Codex path.
- The current release/publication surface is intentionally Hermes-centered. Adding Codex as a first-class surface requires explicit install, preflight, and docs changes rather than just mentioning Codex in prose.
- The current runtime still defaults its config and delegated execution flow through Hermes state. Codex local therefore needs to be documented as a supported surface over the same runtime, not as an independent backend.
- The isolated Codex-local smoke reached the intended state after sequential install and preflight: `release_surface_ready=true` and `operator_ready=false`, with the remaining operator blockers coming from missing `OPENROUTER_API_KEY` plus optional OSS analysis-family dependencies in the temp environment rather than from the Codex-local surface itself.

## Decision Log

- Decision: implement Codex local first, not Codex cloud.
- Decision: add a dedicated Codex skill bundle and install helper so the surface is enforceable rather than docs-only.
- Decision: keep the existing typed runtime and delegated Hermes execution path as the one source of truth; do not duplicate orchestration logic inside a Codex-only runtime.
- Decision: keep the runtime config and artifacts on the existing `~/.hermes/deep-gvr/` path for now because the shipped runtime still depends on that operator state.

## Outcomes & Retrospective

- Added a dedicated Codex-local skill bundle at `codex_skill/SKILL.md`.
- Added `scripts/install_codex.sh` and `scripts/codex_preflight.py` as the supported Codex-local install and operator-check path.
- Extended the release-surface helper layer and repo checks so the Codex-local surface is enforced rather than treated as docs-only.
- Updated the public docs and architecture language so Codex local is a supported first-class operator surface over the shared runtime.
- Validation completed successfully with:
  - `uv run python scripts/check_repo.py`
  - `uv run python scripts/run_capability_probes.py`
  - `uv run python -m unittest discover -s tests -v`
- Targeted smoke evidence:
  - `HOME=/tmp/deep-gvr-codex-surface-home CODEX_HOME=/tmp/deep-gvr-codex-surface-home/.codex HERMES_HOME=/tmp/deep-gvr-codex-surface-home/.hermes bash scripts/install_codex.sh`
  - `HOME=/tmp/deep-gvr-codex-surface-home CODEX_HOME=/tmp/deep-gvr-codex-surface-home/.codex HERMES_HOME=/tmp/deep-gvr-codex-surface-home/.hermes uv run python scripts/codex_preflight.py --json`
  - `HOME=/tmp/deep-gvr-codex-surface-home CODEX_HOME=/tmp/deep-gvr-codex-surface-home/.codex HERMES_HOME=/tmp/deep-gvr-codex-surface-home/.hermes uv run python scripts/codex_preflight.py --operator`

## Context and Orientation

- Existing release/operator surface: `scripts/install.sh`, `scripts/release_preflight.py`, `src/deep_gvr/release_surface.py`
- Existing public docs: `README.md`, `docs/start-here.md`, `docs/quickstart.md`, `docs/system-overview.md`, `docs/deep-gvr-architecture.md`
- Existing Hermes agent surface: `SKILL.md`
- Existing CLI runtime: `src/deep_gvr/cli.py`, `src/deep_gvr/orchestrator.py`

## Plan of Work

1. Add a dedicated Codex-local skill and install path.
2. Add Codex-local operator preflight and release-surface enforcement.
3. Update the public/docs/architecture surface so Codex local is a documented supported host.

## Concrete Steps

1. Add `codex_skill/SKILL.md` as the Codex-local operator skill.
2. Add `scripts/install_codex.sh`:
   - install the Codex skill into `${CODEX_HOME:-~/.codex}/skills/deep-gvr`
   - ensure the underlying Hermes skill/runtime install path is also prepared unless explicitly skipped
3. Add `scripts/codex_preflight.py` plus the matching helpers in `src/deep_gvr/release_surface.py`.
4. Extend repo checks so the Codex-local surface assets are required and remain wired into the human-facing docs.
5. Update `README.md`, `docs/start-here.md`, `docs/quickstart.md`, `docs/system-overview.md`, `docs/release-workflow.md`, and `docs/deep-gvr-architecture.md` so Codex local is presented as a supported peer surface.
6. Add a dedicated public doc for Codex local usage and operator boundaries.

## Validation and Acceptance

Required validation:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Targeted validation:

```bash
uv run python scripts/codex_preflight.py --json
uv run python scripts/codex_preflight.py --operator
```

Acceptance evidence:

- The repo ships a dedicated Codex-local skill and install helper.
- The repo has a Codex-local operator preflight command.
- Public docs describe Codex local as a supported surface without claiming it is a separate runtime backend.
- Repo checks fail if the Codex-local install/preflight/docs surface drifts out of sync.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/codex-local-surface` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions runs for the pushed head are green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Re-running `scripts/install_codex.sh` with `--force` should safely refresh the installed Codex skill.
- Re-running `scripts/codex_preflight.py` should be safe and should report current environment state rather than mutating it.
- If the Codex surface is installed but the underlying Hermes runtime is not ready, the preflight output must say so explicitly rather than claiming Codex-local readiness.

## Interfaces and Dependencies

- Depends on the existing CLI/orchestrator runtime in `src/deep_gvr/cli.py` and `src/deep_gvr/orchestrator.py`.
- Depends on a working local Codex CLI for the Codex-local surface.
- Depends on the existing Hermes runtime path because the shipped delegated execution path still routes through Hermes today.
- Should add Codex-local operator support without weakening the Hermes release surface or duplicating the runtime core.
