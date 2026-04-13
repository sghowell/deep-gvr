# 39 Public Release and Distribution

## Purpose / Big Picture

Move `deep-gvr` from a repo-validated release surface to a real public release process. The user-visible outcome is a project that can be versioned, packaged, documented, and published in a way that feels intentional and trustworthy to external users, not just to operators working from the repository checkout.

This slice should formalize:

- how releases are versioned and cut
- where releases are published
- how release notes and changelog history are maintained
- how the public docs are hosted
- how the existing agentskills publication bundle fits into the actual release flow

## Branch Strategy

Start from `main` and implement this slice on `codex/public-release-and-distribution`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result again, push `main`, confirm CI, and delete the feature branch when it is no longer needed.

## Commit Plan

- `add release planning and changelog surface`
- `add hosted docs and release workflows`
- `document public release process`

## Progress

- [x] Review the current release/publication surface and public docs set.
- [x] Confirm the repo currently has no git tags, no changelog, no dedicated release workflow, and no hosted docs configuration.
- [x] Add this plan and index it from `plans/README.md`.
- [ ] Add versioned release metadata and changelog policy.
- [ ] Add hosted public docs configuration and deployment.
- [ ] Add GitHub release automation and release checklist artifacts.
- [ ] Align docs and validation with the new public release process.
- [ ] Run full validation.
- [ ] Merge locally, revalidate on `main`, push, confirm CI, and delete the feature branch.

## Surprises & Discoveries

- The repo already has a credible operator/release surface: install script, preflight, publication manifest, and polished public docs.
- The missing work is not “can it be installed?” but “can it be released and consumed like a real public product?”
- There is currently no tag history, no `CHANGELOG.md`, no GitHub release workflow, and no hosted docs configuration. Those are now the highest-leverage productization gaps.
- Because the public docs sweep already separated human-facing docs from agent/harness docs, a hosted docs site can now publish the public set cleanly without dragging internal docs into the nav.

## Decision Log

- Primary public release channels for this slice are **GitHub Releases** and **agentskills.io**. These are the required channels for completion.
- Hosted docs are in scope and should be published via **GitHub Pages** using a lightweight docs-site generator. Default choice: **MkDocs Material**.
- `README.md` remains the repository landing page, while the hosted docs site becomes the canonical browsable public docs surface.
- `CHANGELOG.md` is required and should use a human-readable release format such as Keep a Changelog plus semantic version sections.
- Versioning source of truth should be explicit and unified across `pyproject.toml`, `release/agentskills.publication.json`, release notes, and the Git tag.
- **PyPI publication is explicitly deferred** in this slice. The project is a Hermes skill bundle plus Python runtime, and the primary supported install surface remains repo/GitHub plus agentskills publication rather than `pip install deep-gvr`.
- Public release automation should validate and publish the existing checked-in release bundle, not invent a second parallel packaging surface.

## Outcomes & Retrospective

- Intended outcome: a new user can discover `deep-gvr`, browse hosted docs, inspect a real release history, and install the supported public release without reading the repo like a development workspace.
- Intended outcome: maintainers can cut a release through a documented and validated process instead of ad hoc manual steps.

## Context and Orientation

- Existing release assets: `release/agentskills.publication.json`, `scripts/install.sh`, `scripts/release_preflight.py`, `docs/release-workflow.md`
- Existing public docs surface: `README.md`, `docs/start-here.md`, `docs/quickstart.md`, `docs/concepts.md`, `docs/domain-portfolio.md`, `docs/examples.md`, `docs/faq.md`, `docs/system-overview.md`, `docs/deep-gvr-architecture.md`
- Current workflow automation: `.github/workflows/ci.yml`
- Current package metadata: `pyproject.toml`

## Plan of Work

1. Add a real release-history and versioning surface.
2. Publish the public docs set as a hosted site.
3. Add GitHub release automation that validates the shipped release bundle before publication.
4. Align the public docs, release docs, and repo checks with the resulting process.

## Concrete Steps

1. Add `CHANGELOG.md` with an initial `0.1.0` release entry and clear policy for future entries.
2. Add a small release metadata helper or repo check so `pyproject.toml`, `release/agentskills.publication.json`, and tagged release versions cannot drift.
3. Add hosted docs configuration using MkDocs Material:
   - `mkdocs.yml`
   - site nav limited to the human-facing docs set
   - explicit exclusion of agent-facing and harness-facing docs from the public nav
4. Add a GitHub Pages workflow that builds and publishes the hosted docs.
5. Add a GitHub release workflow that:
   - runs repo checks
   - runs release preflight
   - validates version consistency
   - attaches or references the checked-in publication bundle
   - creates GitHub release notes from the changelog section for the tag
6. Update `docs/release-workflow.md`, `README.md`, and the hosted docs entry pages so the release/install path points at the real public release channels.
7. Add a release checklist artifact or script for maintainers, covering:
   - version bump
   - changelog update
   - tag creation
   - GitHub release
   - agentskills publication
8. Extend repo checks so the public release surface stays coherent:
   - hosted docs config exists
   - changelog exists
   - version fields stay aligned
   - release workflow files exist

## Validation and Acceptance

Required validation:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Additional acceptance validation:

```bash
uv run python scripts/release_preflight.py --json
mkdocs build --strict
```

Acceptance evidence:

- The repo has a checked-in `CHANGELOG.md` and a documented semantic release policy.
- A hosted docs site can be built from the current public docs set without pulling in internal docs.
- GitHub Pages deployment is configured for the hosted docs site.
- GitHub release automation exists and validates the release bundle before publication.
- Release-version drift between `pyproject.toml`, the publication manifest, and the tagged version is mechanically checked.
- The public release process is documented end to end in the repo.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/public-release-and-distribution` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions runs for the pushed head are green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Re-running the docs build and release validation should be safe and deterministic for the same repo state.
- Release automation should fail before publication when version or changelog state is incomplete, rather than partially publishing.
- The hosted docs build should remain a pure derived surface from repo content, not a manually edited parallel docs tree.

## Interfaces and Dependencies

- Depends on the existing release surface in `release/`, `scripts/install.sh`, and `scripts/release_preflight.py`.
- Adds a hosted docs toolchain and GitHub workflows, but does not change the supported runtime architecture.
- Defers PyPI publication and any new binary/package-manager distribution surface to a later slice.
- Should reuse the human-facing docs set already created in plan 38 rather than inventing a second public documentation corpus.
