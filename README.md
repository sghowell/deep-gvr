# deep-gvr

`deep-gvr` is an agent-first research harness for Hermes Agent that implements a generator-verifier-reviser loop with tiered verification.

The repository is intentionally bootstrapped for Codex-driven implementation. The current state is readiness scaffolding: contracts, prompts, schemas, capability probes, execution plans, and repository guardrails needed to begin product implementation without re-deciding project structure.

## What Exists Now

- Agent operating rules in [AGENTS.md](AGENTS.md)
- Execution plan standard in [PLANS.md](PLANS.md)
- Contributor workflow in [CONTRIBUTING.md](CONTRIBUTING.md)
- Indexed design docs in [docs/README.md](docs/README.md)
- Typed Python contracts in `src/deep_gvr/`
- JSON schemas in `schemas/`
- Prompt and skill scaffolding in `prompts/` and `SKILL.md`
- Capability probes and validation scripts in `scripts/`
- Initial implementation backlog in `plans/`

## Intended Public Surface

- `/deep-gvr <question>` starts a research run
- `/deep-gvr resume <session_id>` resumes a prior run
- Config lives at `~/.hermes/deep-gvr/config.yaml`
- Evidence lives under `~/.hermes/deep-gvr/sessions/<session_id>/`

## Working Style

This repo follows harness-engineering principles:

- humans provide intent, priorities, and review
- Codex produces code, tests, docs, CI, and repo maintenance artifacts
- repository-local docs and execution plans are the source of truth
- quality rules are enforced in scripts and tests where possible

## Quickstart

The repo is pinned to Python 3.12 and `uv`.

```bash
uv sync
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

If `uv` is not available yet, the local checks can also be run with a Python 3.12 interpreter and `PYTHONPATH=src`.

## Reference Docs

- [docs/README.md](docs/README.md)
- [docs/deep-gvr-architecture.md](docs/deep-gvr-architecture.md)
- [plans/README.md](plans/README.md)
