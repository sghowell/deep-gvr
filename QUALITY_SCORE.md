# Quality Score

This file defines the quality bar for readiness and early implementation work.

## Readiness Rubric

| Area | Ready When |
| --- | --- |
| Operating model | `AGENTS.md`, `CONTRIBUTING.md`, `PLANS.md`, and PR checklist agree on workflow and validation |
| Contracts | Python models, schemas, prompts, and templates use the same field names and concepts |
| Capability probes | P0 unknowns have scripts, documented defaults, and documented fallbacks |
| Validation | Repo checks and tests run locally and in CI |
| Plans | Each implementation slice has a self-contained execution plan with branch and commit guidance |
| Skill shape | `SKILL.md`, prompts, schemas, templates, adapters, and domain docs are scaffolded |

## Failure Conditions

- Workflow docs disagree with each other.
- A prompt refers to artifact fields not represented in schemas or templates.
- A plan omits branch strategy, commit boundaries, validation, or merge cleanup steps.
- Checks rely on undocumented manual review for rules that can be scripted.
- Capability spikes have no fallback path.
