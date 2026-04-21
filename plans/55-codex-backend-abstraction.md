# 55 Codex Backend Abstraction

## Purpose / Big Picture

Add a real orchestrator-backend abstraction so `deep-gvr` is no longer hardwired to Hermes at the runtime boundary. The user-visible outcome should be that the repo has an explicit backend selection seam, backend-neutral runtime-home plumbing, and docs/architecture language that accurately describe Hermes as the shipped default backend rather than the only backend the code can support.

This slice does not claim that the Codex backend is finished. It prepares that work cleanly and keeps the shipped Hermes path working.

## Branch Strategy

Start from `main` and implement this slice on `codex/codex-backend-abstraction`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result again, push `main`, confirm CI and Docs, and delete the feature branch when it is no longer needed.

## Commit Plan

- `add codex backend plans`
- `add orchestrator backend abstraction`
- `document codex backend boundary`

## Progress

- [x] Review the current Hermes-bound orchestrator, Codex-local surface, and SSH/devbox docs.
- [x] Draft this plan and the follow-on Codex-local backend plan, then index them from `plans/README.md`.
- [x] Add an explicit orchestrator backend abstraction and backend selection in runtime config.
- [x] Add backend-neutral runtime-home helpers with compatibility-preserving defaults.
- [x] Update docs, architecture status, and repo checks so the new boundary is explicit and honest.
- [ ] Run validation, merge locally, revalidate on `main`, push, confirm CI and Docs, and delete the feature branch.

## Surprises & Discoveries

- The current docs are not merely underselling Codex. The code really is still Hermes-bound in `src/deep_gvr/orchestrator.py`, `src/deep_gvr/cli.py`, and default runtime paths.
- The cleanest first step is not a big-bang Codex runtime rewrite. It is a backend seam with explicit config selection and a clear not-yet-implemented Codex-local placeholder.
- Runtime paths are still semantically Hermes-owned in multiple places, so backend abstraction also needs a neutral runtime-home helper rather than only a factory rename.

## Decision Log

- Decision: land backend abstraction before implementing a real Codex-local backend.
- Decision: keep Hermes as the default shipped backend for this slice.
- Decision: add a backend-neutral runtime-home environment variable path without breaking existing `~/.hermes/deep-gvr` defaults.
- Decision: keep the Codex-local backend explicit as planned work rather than quietly implying that prompt bundles equal a native backend.

## Outcomes & Retrospective

- The runtime now has a typed orchestrator-backend seam instead of instantiating Hermes directly from the CLI path.
- `runtime.orchestrator_backend=codex_local` is recognized and fails explicitly with a structured unavailable result instead of silently falling back.
- Runtime-home resolution is backend-neutral at the helper layer while preserving the compatibility path under `${HERMES_HOME:-~/.hermes}/deep-gvr` when `DEEP_GVR_HOME` is unset.
- The public and operator docs now describe Hermes as the shipped backend rather than the only backend the code can support.

## Context and Orientation

- Current Hermes-only backend wiring: `src/deep_gvr/orchestrator.py`, `src/deep_gvr/cli.py`
- Current runtime-home defaults: `src/deep_gvr/runtime_config.py`, `src/deep_gvr/evidence.py`, `src/deep_gvr/release_surface.py`
- Current Codex surfaces: `docs/codex-local.md`, `docs/codex-ssh-devbox.md`, `docs/codex-subagents.md`
- Architecture source of truth: `docs/deep-gvr-architecture.md`, `docs/architecture-status.md`

## Plan of Work

1. Introduce a backend selection seam and generic orchestrator runner interface.
2. Move default runtime-home resolution behind backend-neutral helpers with backward-compatible defaults.
3. Update docs, architecture tracking, and tests so the new boundary is visible and enforceable.

## Concrete Steps

1. Add a new runtime/orchestrator backend enum and config field that defaults to `hermes`.
2. Refactor `src/deep_gvr/orchestrator.py` so Hermes is one backend implementation behind a generic runner/factory surface.
3. Add a clear Codex-local backend placeholder path that fails explicitly if selected before the next slice is implemented.
4. Introduce backend-neutral runtime-home helpers and use them for config path resolution and related defaults where practical.
5. Update schemas, templates, tests, docs, and architecture status to reflect the abstraction and the still-open Codex-local backend slice.

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
uv run mkdocs build --strict
```

Acceptance evidence:

- Runtime config contains an explicit orchestrator backend selection.
- CLI/orchestrator code no longer instantiates Hermes directly without going through a backend abstraction.
- The repo has a backend-neutral runtime-home helper path with compatibility-preserving defaults.
- Docs and architecture status no longer imply that Hermes is the only possible backend the runtime can support.
- The repo includes a clear follow-on plan for the real Codex-local backend.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/codex-backend-abstraction` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions and Docs runs for the pushed head are green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Re-running config writes should preserve a valid default backend and runtime-home layout.
- If the new backend selection is set to an unimplemented backend, the runtime should fail explicitly and structurally rather than silently falling back.
- If any runtime-home helper change causes path drift, the branch must be corrected before merge rather than patched later in docs only.

## Interfaces and Dependencies

- Depends on the existing CLI/orchestrator runtime in `src/deep_gvr/cli.py` and `src/deep_gvr/orchestrator.py`.
- Depends on config/schema/template alignment in `src/deep_gvr/contracts.py`, `src/deep_gvr/runtime_config.py`, `schemas/config.schema.json`, and `templates/config.template.yaml`.
- Depends on the public/operator docs for Codex and architecture boundaries.
- Prepares the next slice: `plans/56-codex-local-backend.md`.
