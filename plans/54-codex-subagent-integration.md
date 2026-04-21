# 54 Codex Subagent Integration

## Purpose / Big Picture

Add a first-class Codex subagent surface for `deep-gvr`. This slice should make the repo's preferred multi-agent operating pattern explicit and reusable without pretending that `deep-gvr` owns Codex's internal delegation runtime.

The repo-owned outcome is:

- a checked-in Codex subagent prompt bundle tailored to branch-safe multi-agent work
- export and install helpers for that bundle
- release and preflight checks that enforce the bundle as part of the shipped Codex surface
- public/operator docs that explain how to use Codex subagents against the existing `deep-gvr` runtime and git/worktree discipline

## Branch Strategy

Start from `main` and implement this slice on `codex/codex-subagent-integration`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result again, push `main`, confirm CI and Docs, and delete the feature branch when it is no longer needed.

## Commit Plan

- `add codex subagent bundle`
- `wire codex subagent release checks`
- `document codex subagent surface`

## Progress

- [x] Draft the plan and index it from `plans/README.md`.
- [x] Add the checked-in Codex subagent bundle, export helper, schema, and tests.
- [x] Wire the subagent surface into install, release metadata, preflight, and repo checks.
- [x] Update public/operator docs and the architecture ledger.
- [x] Run validation, merge locally, revalidate on `main`, push, confirm CI and Docs, and delete the feature branch.

## Surprises & Discoveries

- The repo already ships Codex-local, plugin, automation, review/QA, and SSH/devbox surfaces, so the cleanest path is another checked-in prompt/export bundle rather than a new runtime abstraction.
- The strongest operator boundary is a versioned multi-agent playbook over the existing runtime and git/worktree rules. The repo should not claim to register live Codex subagent state or manage Codex's internal delegation APIs.
- The valuable part of this slice is not "parallelism" in the abstract. It is explicit safe usage: main agent owns integration, subagents stay on disjoint scopes or worktrees, and nothing pushes independently.

## Decision Log

- Decision: ship the Codex subagent surface as a checked-in prompt bundle plus export helper, following the same repo-owned pattern as the review/QA and SSH/devbox surfaces.
- Decision: keep the prompts explicit about worktree separation, disjoint write ownership, and main-agent integration responsibility.
- Decision: enforce the surface in publication metadata, release/preflight checks, and public docs so it is a real shipped operator path rather than an undocumented convention.

## Outcomes & Retrospective

- Added a checked-in Codex subagent bundle at `codex_subagents/` plus an export helper at `scripts/export_codex_subagents.py`.
- Wired the subagent surface into the enforced Codex/release surface through publication metadata, preflight, repo checks, install helpers, schemas, and tests.
- Added a dedicated human-facing `docs/codex-subagents.md` page plus docs-map and architecture updates so the new surface is explicit and discoverable.
- Branch validation passed with:
  - `uv run python scripts/check_repo.py`
  - `uv run python scripts/run_capability_probes.py`
  - `uv run python -m unittest discover -s tests -v`
  - `uv run mkdocs build --strict`
  - `uv run python scripts/export_codex_subagents.py --output-root /tmp/deep-gvr-codex-subagents --force --json`

## Context and Orientation

- Existing Codex local surface: `codex_skill/SKILL.md`, `scripts/install_codex.sh`, `scripts/codex_preflight.py`
- Existing Codex review/QA pack: `codex_review_qa/catalog.json`, `docs/codex-review-qa.md`
- Existing Codex SSH/devbox pack: `codex_ssh_devbox/catalog.json`, `docs/codex-ssh-devbox.md`
- Existing release surface enforcement: `src/deep_gvr/release_surface.py`, `src/deep_gvr/repo_checks.py`
- Existing public docs map: `README.md`, `docs/index.md`, `docs/start-here.md`, `mkdocs.yml`

## Plan of Work

1. Add a checked-in Codex subagent prompt bundle for safe multi-agent implementation and review workflows.
2. Wire the bundle into install/export/publication/preflight/repo-check surfaces.
3. Update public/operator docs so the Codex subagent path is explicit, bounded, and discoverable.

## Concrete Steps

1. Add:
   - `codex_subagents/catalog.json`
   - `codex_subagents/templates/parallel_validator_fanout.prompt.md`
   - `codex_subagents/templates/parallel_surface_review.prompt.md`
   - `src/deep_gvr/codex_subagents.py`
   - `scripts/export_codex_subagents.py`
   - matching schema/template/test coverage
2. Extend `scripts/install_codex.sh` with `--subagents-root <dir>`.
3. Extend `src/deep_gvr/release_surface.py`, `src/deep_gvr/repo_checks.py`, and `release/agentskills.publication.json` to enforce the new surface.
4. Update public/operator docs with a dedicated `docs/codex-subagents.md` page plus docs-map and architecture references.

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
uv run python scripts/export_codex_subagents.py --output-root /tmp/deep-gvr-codex-subagents --force --json
uv run python scripts/codex_preflight.py --json
uv run python scripts/release_preflight.py --json
```

Acceptance evidence:

- The repo contains a checked-in Codex subagent bundle and export helper.
- `install_codex.sh` can export the subagent bundle with `--subagents-root`.
- Release/preflight/repo checks fail if the new surface drifts or disappears.
- Public/operator docs explain the Codex subagent surface and keep the runtime boundary honest.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/codex-subagent-integration` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions runs for the pushed head are green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- The export helper should be rerunnable and refuse to overwrite existing exports without `--force`.
- The shipped prompts should keep the repo-owned boundary explicit: they guide Codex subagent usage, but they do not imply the repo controls Codex app state or delegation internals.
- If a multi-agent workflow needs concurrent writes, the prompts should direct the operator toward separate worktrees or clearly disjoint ownership rather than unsafely sharing one write scope.

## Interfaces and Dependencies

- Depends on the existing Codex-local surface and installer.
- Depends on the existing release/publication/preflight/check framework for Codex bundles.
- Depends on Codex product support for subagents/multi-agent workflows, but the repo should stay honest that it is shipping a versioned operator playbook over those capabilities rather than the capabilities themselves.
