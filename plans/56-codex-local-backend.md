# 56 Codex Local Backend

## Purpose / Big Picture

Implement a real Codex-local orchestrator backend for `deep-gvr` so the Codex path no longer requires Hermes to be installed or functioning underneath. The user-visible outcome should be that a configured Codex-local backend can run the same typed runtime, checkpoints, evidence flow, and Tier 2/Tier 3 integrations through Codex-native execution rather than through Hermes delegation.

This slice depends on the backend abstraction from plan 55. It should not ship until that seam is in place.

## Branch Strategy

Start from `main` after plan 55 is merged and implement this slice on `codex/codex-local-backend`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result again, push `main`, confirm CI and Docs, and delete the feature branch when it is no longer needed.

## Commit Plan

- `add codex local backend transport`
- `wire codex backend preflight and release checks`
- `document codex native backend`

## Progress

- [x] Wait for plan 55 to land.
- [x] Design the Codex-local backend invocation and transcript contract.
- [x] Implement the backend and integrate it into CLI/config/preflight paths.
- [x] Add targeted tests and update docs and architecture status.
- [ ] Run validation, merge locally, revalidate on `main`, push, confirm CI and Docs, and delete the feature branch.

## Surprises & Discoveries

- The cleanest Codex-native transport is `codex exec` with `--output-schema` plus `--output-last-message`, not the existing skill wrapper. That avoids recursion back through `uv run deep-gvr ...`.
- Release/operator checks still had a hidden Hermes assumption even after the backend seam landed; those needed to become backend-sensitive, not just backend-aware.
- The Codex-local skill and plugin surfaces still matter after the native backend lands, but they now need to describe `runtime.orchestrator_backend` as the source of truth rather than presenting Hermes as mandatory.

## Decision Log

- Decision: implement the backend through direct `codex exec` transport instead of routing through the Codex `deep-gvr` skill, because the skill intentionally wraps `uv run deep-gvr ...` and would recurse.
- Decision: keep Hermes as the default backend in the checked-in config template even after the Codex backend lands.
- Decision: make release preflight check backend-specific CLI/skill requirements instead of assuming Hermes everywhere.

## Outcomes & Retrospective

- The runtime can now execute through a real Codex-local backend when `runtime.orchestrator_backend=codex_local` is selected.
- Codex and release preflight now stop requiring Hermes install/CLI on the operator path when the selected backend is Codex-local.
- Codex-facing docs and skill bundles now describe Codex as a real backend option rather than only a peer surface over Hermes.

## Context and Orientation

- Backend abstraction prerequisite: `plans/55-codex-backend-abstraction.md`
- Current Codex surfaces: `docs/codex-local.md`, `docs/codex-plugin.md`, `docs/codex-ssh-devbox.md`, `scripts/install_codex.sh`, `scripts/codex_preflight.py`
- Runtime integration points: `src/deep_gvr/orchestrator.py`, `src/deep_gvr/cli.py`, `src/deep_gvr/release_surface.py`

## Plan of Work

1. Implement a Codex-local backend transport that can execute the orchestrator contract without Hermes.
2. Integrate that backend into preflight, release, and operator docs.
3. Expand the Codex SSH/devbox and subagent surfaces so they can leverage the real Codex backend rather than only prompt/export bundles.

## Concrete Steps

1. Add a real Codex-local backend runner in `src/deep_gvr/orchestrator.py`.
2. Extend config, preflight, and release surfaces so `runtime.orchestrator_backend=codex_local` is supported.
3. Add targeted smoke and transcript tests for the Codex backend path.
4. Update Codex docs so Codex local is described as a real backend option, not only as a peer surface over Hermes.

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
uv run python scripts/codex_preflight.py --json
uv run python scripts/codex_preflight.py --operator
```

Acceptance evidence:

- A Codex-local backend can be selected in runtime config.
- The Codex-local backend can run without Hermes installed.
- Codex-local operator preflight does not require Hermes when the Codex backend is selected.
- Docs and architecture language describe Codex as a true backend option when configured.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/codex-local-backend` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions and Docs runs for the pushed head are green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- If the Codex-local backend cannot satisfy the orchestrator contract, fail explicitly instead of silently routing back through Hermes.
- Keep targeted smoke tests repeatable with local temp homes and isolated skill installs where possible.

## Interfaces and Dependencies

- Depends on the backend abstraction from `plans/55-codex-backend-abstraction.md`.
- Depends on Codex-local skill/plugin/operator surfaces already shipped in the repo.
- Must stay aligned with Tier 2/Tier 3 runtime contracts, evidence artifacts, and release/preflight checks.
