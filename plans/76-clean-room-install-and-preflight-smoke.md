# 76 Clean-Room Install And Preflight Smoke

## Purpose / Big Picture

Prove that the shipped install and preflight flows work from a real clean-room
starting point instead of only from this already-prepared machine or narrow
unit tests. The user-visible outcome is that `scripts/install.sh`,
`scripts/install_codex.sh`, `scripts/release_preflight.py`, and
`scripts/codex_preflight.py` all behave correctly when pointed at isolated
runtime and operator homes, including the Codex-native `--skip-hermes-install`
path.

## Branch Strategy

Start from `main` and implement this slice on
`codex/clean-room-install-and-preflight-smoke`. Merge back into `main`
locally with a fast-forward only after branch validation passes, then validate
the merged result again, push `main`, confirm CI and Docs are green, and
delete the feature branch.

## Commit Plan

- `plan clean-room install smoke`
- `fix clean-room install config materialization`
- `add clean-room install smoke`

## Progress

- [x] Add this plan and index it from `plans/README.md`.
- [x] Audit the current install and preflight helpers against the documented
      isolated-home story.
- [ ] Fix the install helpers so runtime config materialization respects
      `DEEP_GVR_HOME` and the Codex-native `--skip-hermes-install` path.
- [ ] Add bounded clean-room smoke coverage for the documented Hermes and
      Codex install/preflight flows.
- [ ] Wire the clean-room smoke into the release-validation surface and CI.
- [ ] Run the required repo validation commands and any new smoke directly.
- [ ] Merge locally, revalidate on `main`, push, confirm remote CI and Docs,
      and delete the feature branch.

## Surprises & Discoveries

- The runtime already treats `DEEP_GVR_HOME` as the authoritative runtime-home
  override, but `scripts/install.sh` and `scripts/install_codex.sh` still copy
  the static `templates/config.template.yaml` file directly.
- That static template hardcodes both `runtime.orchestrator_backend: hermes`
  and `evidence.directory: ~/.hermes/deep-gvr/sessions`, so copying it
  directly is wrong for isolated runtime homes and for the Codex-native
  `--skip-hermes-install` path.
- `scripts/install_codex.sh --skip-hermes-install` currently skips the Hermes
  install but also skips creation of a Codex-native runtime config, which
  leaves the documented clean-room Codex path structurally blocked.

## Decision Log

- Keep the fix repo-local and low-dependency: materialize the runtime config
  from the checked-in template through a stdlib-only helper instead of relying
  on `uv` or PyYAML during bare install.
- Treat the clean-room proof as a real executable smoke script and CI step, not
  just more unit assertions.
- Preserve the current runtime-home contract
  `${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}` instead of inventing a
  second Codex-only default runtime location in this slice.

## Outcomes & Retrospective

- The install scripts will create the right runtime config for isolated Hermes,
  hybrid Codex+Hermes, and Codex-native clean-room installs.
- A dedicated clean-room smoke will prove the documented install and structural
  preflight flows in disposable temp homes.
- CI and release validation will continuously exercise that clean-room smoke so
  install-surface regressions do not depend on manual review.

## Context and Orientation

- Hermes install helper: `scripts/install.sh`
- Codex install helper: `scripts/install_codex.sh`
- Structural preflight helpers: `scripts/release_preflight.py`,
  `scripts/codex_preflight.py`
- Runtime-home helpers: `src/deep_gvr/runtime_paths.py`,
  `src/deep_gvr/runtime_config.py`
- Release contract: `src/deep_gvr/release_surface.py`,
  `release/agentskills.publication.json`
- Current operator docs: `docs/release-workflow.md`, `docs/quickstart.md`
- Existing tests: `tests/test_release_scripts.py`

## Plan Of Work

1. Add and index this plan.
2. Introduce a small runtime-config materializer that can stamp the checked-in
   config template with the correct runtime-home evidence path and selected
   orchestrator backend.
3. Update `scripts/install.sh` and `scripts/install_codex.sh` to use that
   materializer instead of copying the template directly.
4. Add clean-room install tests that cover `DEEP_GVR_HOME` and the Codex-native
   `--skip-hermes-install` flow.
5. Add a dedicated clean-room smoke script that runs the documented Hermes,
   hybrid Codex, and Codex-native install/preflight flows in disposable temp
   homes.
6. Wire that smoke into CI, release validation, the publication manifest, and
   the operator docs.

## Concrete Steps

1. Add `plans/76-clean-room-install-and-preflight-smoke.md` and index it in
   `plans/README.md`.
2. Add a stdlib-only helper under `scripts/` that writes a runtime config from
   `templates/config.template.yaml` while overriding:
   - `runtime.orchestrator_backend`
   - `evidence.directory`
3. Update `scripts/install.sh` to:
   - honor `DEEP_GVR_HOME` for runtime config creation
   - create the runtime config through the new helper instead of copying the
     static template directly
4. Update `scripts/install_codex.sh` to:
   - use the same runtime-home calculation
   - create a `codex_local` runtime config when `--skip-hermes-install` is used
     in a clean room
   - keep the default hybrid install path using the Hermes-shaped runtime
     config when Hermes is still part of the selected surface
5. Extend `tests/test_release_scripts.py` to cover:
   - `DEEP_GVR_HOME`-aware install config creation
   - Codex-native `--skip-hermes-install` config creation
6. Add `scripts/clean_room_install_smoke.py` that proves:
   - Hermes clean-room install + structural release preflight
   - hybrid Codex+Hermes clean-room install + structural Codex/release
     preflight
   - Codex-native clean-room install + structural Codex/release preflight
7. Update:
   - `.github/workflows/ci.yml`
   - `.github/workflows/release.yml`
   - `src/deep_gvr/release_surface.py`
   - `release/agentskills.publication.json`
   - `docs/release-workflow.md`
   - `docs/quickstart.md`
   - `release/release-checklist.md`
   so the clean-room smoke is part of the documented and checked release
   surface.

## Validation And Acceptance

Required validation:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
uv run python scripts/clean_room_install_smoke.py --json
uv run mkdocs build --strict
```

Acceptance evidence:

- `scripts/install.sh` creates a runtime config under the correct runtime home
  when `DEEP_GVR_HOME` is set.
- `scripts/install_codex.sh --skip-hermes-install` creates a clean-room
  `codex_local` runtime config instead of leaving Codex structural preflight
  blocked on missing config.
- The dedicated clean-room smoke proves the documented Hermes, hybrid Codex,
  and Codex-native install/preflight flows in disposable temp homes.
- CI and release validation both run the clean-room smoke.

## Merge, Push, And Cleanup

- Stage and commit the plan/index update first with
  `plan clean-room install smoke`.
- Stage and commit the install/config materialization changes with
  `fix clean-room install config materialization`.
- Stage and commit the smoke, workflow, manifest, and doc updates with
  `add clean-room install smoke`.
- Validate the feature branch before merge.
- Fast-forward merge `codex/clean-room-install-and-preflight-smoke` into
  `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the remote CI and Docs workflows are green.
- Delete the local feature branch, and delete the remote feature branch too if
  one was created.

## Idempotence And Recovery

- Re-running the install helpers in a clean room should keep creating the same
  runtime-home-aware config payload.
- Re-running the clean-room smoke should only use disposable temp homes and
  should not dirty the worktree or mutate a real operator home.
- If the smoke starts failing in CI later, it should point directly at an
  install/preflight regression rather than requiring a preconfigured local
  machine to reproduce.

## Interfaces And Dependencies

- Depends on a local `python3` interpreter for install-time config
  materialization; it does not depend on `uv` or third-party Python packages
  during bare install.
- Affects the Hermes and Codex install surfaces, the structural preflight
  helpers, and release/operator validation docs.
- Does not change the Tier 1, Tier 2, or Tier 3 runtime behavior beyond making
  the clean-room config surface match the documented backend/runtime contract.
