# Contributing

`deep-gvr` uses an agent-first workflow. Human contributors define priorities, architecture constraints, and acceptance criteria. Codex is expected to produce the implementation artifacts in the repository.

## Standard Workflow

1. Start from the current integration branch and create a feature branch such as `codex/tier1-loop`.
2. Choose or create an execution plan in `plans/` before making substantial changes.
3. Make changes in reviewable slices and stage them deliberately.
4. Commit in sensible chunks with concise descriptive messages.
5. Run the required validation commands locally.
6. Merge locally only after the feature branch is validated.
7. Validate the merged result again.
8. Push the integrated branch.
9. Delete the feature branch locally and remotely if it is no longer needed.

## Branch Naming

- Default prefix: `codex/`
- Examples:
  - `codex/repo-bootstrap`
  - `codex/capability-probes`
  - `codex/tier2-stim`

## Commit Hygiene

- Keep commits topical and easy to review.
- Avoid mixing policy docs, code, and unrelated refactors in the same commit unless they are inseparable.
- Prefer short imperative subjects without trailing punctuation.
- If a change introduces a new rule, include the enforcement mechanism in the same series when possible.

## Required Checks

```bash
python scripts/check_repo.py
python scripts/run_capability_probes.py
python -m unittest discover -s tests -v
```

If the project environment is synced with `uv`, use:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

## Plans Are Mandatory for Non-Trivial Work

Read [PLANS.md](PLANS.md) before creating or modifying any implementation plan. Each plan must declare:

- branch strategy
- intended commit boundaries
- validation and acceptance steps
- merge, push, and branch cleanup steps
