# 40 Docs Deploy and Visuals

## Purpose / Big Picture

Finish the public docs publication path now that GitHub Pages is enabled, and raise the quality of the most visible human-facing diagrams and visuals. The user-visible outcome is that public docs deploy automatically on every push to `main`, and the core documentation pages no longer rely on ASCII-first presentation where polished publication-quality visuals should exist.

This slice should improve the visual surface without changing the underlying architecture, workflow, or system model.

## Branch Strategy

Start from `main` and implement this slice on `codex/docs-deploy-and-visuals`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result again, push `main`, confirm CI, and delete the feature branch when it is no longer needed.

## Commit Plan

- `add docs auto deploy workflow`
- `upgrade public documentation visuals`
- `document docs publication defaults`

## Progress

- [x] Review the current docs workflow and the public docs pages that still rely on low-legibility visuals.
- [x] Confirm GitHub Pages is now enabled for the repository, so manual-only deployment is no longer necessary.
- [x] Add automatic docs deployment on every push to `main`.
- [x] Replace the remaining ASCII-first public visual surface with publication-quality assets.
- [x] Align public docs copy and site styling with the upgraded visual surface.
- [x] Run full validation.
- [ ] Merge locally, revalidate on `main`, push, confirm CI, and delete the feature branch.

## Surprises & Discoveries

- The public docs already include Mermaid source blocks in a few places, but the site currently treats them as plain code rather than polished visuals.
- The most obvious public-facing ASCII artifact is the top-level README banner, which is exactly the wrong place to look improvised.
- Static SVG figures are the safest route for publication-quality visuals here because they render well on GitHub and on the hosted docs site without adding fragile client-side rendering dependencies.
- MkDocs Material still emits its upstream MkDocs 2.0 warning during local builds, but it is only stderr noise and does not affect strict build success for the current site.

## Decision Log

- Decision: switch the `Docs` workflow from manual deployment to automatic deployment on every push to `main`, while keeping `workflow_dispatch` available for manual reruns.
- Decision: use checked-in SVG figures for the upgraded visual surface rather than relying on runtime Mermaid rendering.
- Decision: improve the hosted docs theme modestly through MkDocs Material configuration and lightweight CSS, but do not change the documentation structure or navigation.
- Decision: limit the visual changes to the public docs and README surface; do not touch agent-facing or harness-facing docs in this slice.

## Outcomes & Retrospective

- The `Docs` workflow now uploads and deploys Pages artifacts automatically on every push to `main`, with `workflow_dispatch` retained only for manual reruns.
- The README, docs home, concepts page, system overview, and architecture doc now use checked-in SVG figures instead of ASCII-first presentation.
- The hosted docs theme now has a modest brand layer through a custom mark, tuned palette, and figure styling, without altering the information architecture.

## Context and Orientation

- Docs workflow: `.github/workflows/docs.yml`
- Public site config: `mkdocs.yml`
- Public landing pages: `README.md`, `docs/index.md`, `docs/concepts.md`, `docs/system-overview.md`, `docs/deep-gvr-architecture.md`, `docs/release-workflow.md`
- Repo doc checks: `src/deep_gvr/repo_checks.py`

## Plan of Work

1. Update the docs workflow so Pages deploys automatically on pushes to `main`.
2. Introduce a small visual asset set for the public docs surface.
3. Replace the most visible ASCII-first or low-legibility public diagrams with those assets.
4. Align site styling and docs copy with the new publication default.

## Concrete Steps

1. Update `.github/workflows/docs.yml` so build and deploy both run on pushes to `main`, with `workflow_dispatch` retained for manual reruns.
2. Add a small public docs asset family under `docs/assets/` for:
   - a README/docs hero
   - the GVR loop
   - the system architecture
   - the verification tiers
3. Update `README.md`, `docs/index.md`, `docs/concepts.md`, `docs/system-overview.md`, and `docs/deep-gvr-architecture.md` to use those visuals.
4. Add light MkDocs theme and CSS refinements so the hosted site presents the new visuals well.
5. Update `docs/release-workflow.md` to reflect automatic deployment on pushes to `main`.
6. Extend repo checks only if needed to keep the docs publication defaults coherent.

## Validation and Acceptance

Required validation:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Additional acceptance validation:

```bash
uv run mkdocs build --strict
```

Acceptance evidence:

- The `Docs` workflow deploys automatically on pushes to `main`.
- The README no longer opens with ASCII banner art.
- The core public docs pages use publication-quality visuals without changing the documented architecture or flow.
- The hosted docs build remains strict and warning-free.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/docs-deploy-and-visuals` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions runs for the pushed head are green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Re-running the docs workflow from the same repo state should rebuild and redeploy the same site content.
- The visual assets should be checked-in source artifacts, not generated outputs that require manual reconstruction.
- If a visual needs revision later, it should be replaceable without changing the underlying docs structure.

## Interfaces and Dependencies

- Depends on the existing Pages-ready docs workflow from plan 39.
- Reuses the human-facing docs set created in plan 38 and the release/documentation surface from plan 39.
- Does not change runtime behavior, verification logic, or the architecture itself.
