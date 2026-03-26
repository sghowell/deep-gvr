# AGENTS.md

This repository is built for agent-first development. Humans define intent and acceptance criteria. Codex writes and maintains the implementation, tests, docs, CI, and repository guardrails.

## Core Rules

- Treat [docs/deep-gvr-architecture.md](docs/deep-gvr-architecture.md) as the top-level design source, then distill operational detail into smaller repo-local docs instead of relying on one large document.
- Keep behavior, contracts, prompts, and validation aligned. When one changes, update the others in the same change.
- Encode repeatable rules in code or scripts instead of leaving them as review folklore.
- Prefer additive changes that leave the repo in a runnable, testable state after each commit.

## Git Workflow and Hygiene

- Work on a feature branch. Do not implement directly on `main`.
- Name branches with the `codex/` prefix unless a plan explicitly requires something narrower.
- Stage and commit changes in sensible, reviewable chunks. A commit should tell one coherent story.
- Use concise descriptive commit messages. Prefer imperative summaries such as `bootstrap repo contracts` or `add schema validation checks`.
- Validate each chunk before moving on when practical, and always validate the full branch before merge.
- Merge locally into the integration branch only after required checks pass.
- Push after the merge result is validated.
- Clean up the feature branch locally and remotely after integration when it is no longer needed.

## Required Read-Before-Edit Files

- [AGENTS.md](AGENTS.md)
- [PLANS.md](PLANS.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [docs/golden-principles.md](docs/golden-principles.md)
- The relevant plan in `plans/`

## Required Validation Before Merge

- `python scripts/check_repo.py`
- `python scripts/run_capability_probes.py`
- `python -m unittest discover -s tests -v`

When `uv` is available and the project environment is synced, run the same commands through `uv run`.

## Repo Map

- `src/deep_gvr/`: typed contracts, probes, and repo validation helpers
- `schemas/`: JSON Schemas used by fixtures and tests
- `templates/`: canonical sample artifacts and fixtures
- `prompts/`: agent prompts for generator, verifier, reviser, and simulator roles
- `plans/`: living execution plans for implementation work
- `scripts/`: repository checks and readiness probes
- `tests/`: unit and smoke tests

## Documentation Expectations

- Keep docs short, explicit, and local to the code they govern.
- If a review comment identifies a stable rule, update the repo docs or checks in the same branch.
- If a prompt changes a field name or artifact shape, update the matching schema, templates, and tests immediately.
