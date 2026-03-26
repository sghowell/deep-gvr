# PLANS.md

Every implementation plan in this repository is a living, executable specification. A plan must be complete enough that another engineer or agent can continue from the file alone.

## Non-Negotiable Requirements

- Keep the plan self-contained. Do not require side knowledge from chat history.
- State the user-visible outcome and the repo paths involved.
- Record decisions, discoveries, and progress as the work evolves.
- Include exact validation commands and expected acceptance evidence.
- Include git workflow details for the work: branch name or naming rule, expected commit boundaries, local merge steps, post-merge validation, push, and cleanup.

## Required Sections

Each file in `plans/` must include these sections in this order:

1. `# <Title>`
2. `## Purpose / Big Picture`
3. `## Branch Strategy`
4. `## Commit Plan`
5. `## Progress`
6. `## Surprises & Discoveries`
7. `## Decision Log`
8. `## Outcomes & Retrospective`
9. `## Context and Orientation`
10. `## Plan of Work`
11. `## Concrete Steps`
12. `## Validation and Acceptance`
13. `## Merge, Push, and Cleanup`
14. `## Idempotence and Recovery`
15. `## Interfaces and Dependencies`

## Branch Strategy Rules

- Use one feature branch per plan slice.
- Default naming: `codex/<plan-topic>`.
- The branch strategy section must say which branch the work starts from and where it merges back.

## Commit Plan Rules

- List the intended commit groupings before implementation starts.
- Keep each commit focused on one coherent unit of change.
- Use concise descriptive commit messages.

## Validation Rules

Every plan must list the commands needed to validate the work. At minimum, plans should include the repo-level checks unless the plan explains why a subset is sufficient:

```bash
python scripts/check_repo.py
python scripts/run_capability_probes.py
python -m unittest discover -s tests -v
```

## Merge, Push, and Cleanup Rules

Every plan must explicitly state:

- merge locally only after validation passes
- validate the merge result
- push the integrated branch
- remove the feature branch when it is no longer needed
