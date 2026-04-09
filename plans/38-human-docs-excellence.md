# 38 Human-Facing Documentation Excellence Sweep

## Purpose / Big Picture

Upgrade the public documentation into a polished, high-trust docs surface for external researchers and hands-on operators without rewriting the internal agent-facing or harness-facing docs. The user-visible outcome is a cleaner public entry path, better onboarding, sharper positioning, and a more readable architecture document.

## Branch Strategy

Start from `main` and implement this slice on `codex/human-docs-excellence`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result again, push `main`, confirm CI, and delete the feature branch when it is no longer needed.

## Commit Plan

- `rebuild public docs surface`
- `add public docs guardrails`

## Progress

- [x] Review the current public and internal docs surface.
- [x] Confirm the out-of-scope internal docs that should remain untouched.
- [x] Add this plan for the docs sweep.
- [x] Rewrite `README.md` as the public landing page.
- [x] Add the new public docs pages and rewrite the architecture, system-overview, and release-workflow docs.
- [x] Add narrow repo checks for public-doc coherence.
- [x] Run full validation.
- [ ] Merge locally, revalidate on `main`, push, confirm CI, and delete the feature branch.

## Surprises & Discoveries

- The existing public docs surface was heavily mixed with implementation-backlog and harness-operator language, especially in `README.md` and `docs/deep-gvr-architecture.md`.
- `docs/system-overview.md` contained useful facts, but it had drifted into an internal runtime checklist rather than a concise human-facing technical reference.
- The repo checks were already narrow enough that adding a small public-docs consistency rule could be done without touching the agent/harness docs.

## Decision Log

- Keep `docs/README.md`, `docs/capability-probes.md`, `docs/contracts-and-artifacts.md`, `AGENTS.md`, `PLANS.md`, `CONTRIBUTING.md`, `SKILL.md`, and `eval/README.md` out of the public docs sweep.
- Use `README.md` plus `docs/start-here.md` as the public entrypoints instead of reusing `docs/README.md`.
- Rewrite the architecture document as a real design document rather than a dump of prompts, schemas, and phased implementation history.
- Add new public docs pages instead of forcing every audience into the existing file set.

## Outcomes & Retrospective

- The public docs surface is now split cleanly between landing, onboarding, concepts, domains, examples, FAQ, operator workflow, and architecture.
- `README.md` and `docs/start-here.md` now act as the public entrypoints instead of routing readers through internal doc indices.
- The architecture document now reads as a design document instead of a prompt/schema dump.
- Repo validation passed after the docs sweep and the new public-docs guardrails.

## Context and Orientation

- Public entrypoints: `README.md`, `docs/start-here.md`
- Public docs set: `docs/quickstart.md`, `docs/concepts.md`, `docs/domain-portfolio.md`, `docs/examples.md`, `docs/faq.md`, `docs/system-overview.md`, `docs/release-workflow.md`, `docs/deep-gvr-architecture.md`
- Repo guardrails: `src/deep_gvr/repo_checks.py`

## Plan of Work

1. Rebuild the public docs information architecture.
2. Rewrite the core public narrative to remove internal backlog framing and operator-first clutter.
3. Add missing public docs pages for onboarding, concepts, domains, examples, and FAQ.
4. Add narrow repo checks that keep the public docs map coherent.

## Concrete Steps

1. Rewrite `README.md` as the public landing page.
2. Add `docs/start-here.md`, `docs/quickstart.md`, `docs/concepts.md`, `docs/domain-portfolio.md`, `docs/examples.md`, and `docs/faq.md`.
3. Rewrite `docs/system-overview.md`, `docs/release-workflow.md`, and `docs/deep-gvr-architecture.md` to match the new public docs voice and role split.
4. Update `plans/README.md` to index this plan.
5. Add public-docs consistency checks to `src/deep_gvr/repo_checks.py`.

## Validation and Acceptance

Required validation:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Acceptance evidence:

- `README.md` works as a standalone evaluation and entry page.
- `docs/start-here.md` routes readers cleanly by goal.
- The new public docs exist and are reachable from `README.md` and `docs/start-here.md`.
- `docs/deep-gvr-architecture.md` reads like a polished design document instead of an internal implementation dump.
- Repo checks enforce the public docs map without spilling into the internal docs surface.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/human-docs-excellence` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Re-running the repo checks should keep the public docs surface deterministic.
- If a public docs page is removed or renamed later, the repo check should fail loudly instead of letting the docs map drift silently.
- If the public narrative needs refinement later, the doc-role split in this slice should make that localized instead of requiring another full sweep.

## Interfaces and Dependencies

- Depends on the existing repo check entrypoint in `scripts/check_repo.py`.
- Does not change the agent-facing or harness-facing docs surface except for adding this implementation plan.
- Adds only public-docs coherence checks; it does not impose a style regime on internal docs.
