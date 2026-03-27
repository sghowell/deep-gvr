# deep-gvr

`deep-gvr` is an agent-first research harness for Hermes Agent that implements a generator-verifier-reviser loop with tiered verification.

The repository is intentionally structured for Codex-driven implementation. The current state is an early working baseline: contracts, prompts, schemas, capability probes, execution plans, repository guardrails, a repo-local loop helper with checkpointed resume semantics, a working local Stim/PyMatching Tier 2 path, and orchestrator-mediated Tier 3 formal verification with structured fallback behavior.

## What Exists Now

- Agent operating rules in [AGENTS.md](AGENTS.md)
- Execution plan standard in [PLANS.md](PLANS.md)
- Contributor workflow in [CONTRIBUTING.md](CONTRIBUTING.md)
- Indexed design docs in [docs/README.md](docs/README.md)
- Typed Python contracts in `src/deep_gvr/`
- Tier 1 loop helpers and session persistence in `src/deep_gvr/tier1.py`
- Local Stim/PyMatching empirical verification in `adapters/stim_adapter.py`
- Orchestrator-mediated Aristotle Tier 3 fallback/client logic in `src/deep_gvr/formal.py`
- JSON schemas in `schemas/`
- Prompt and skill scaffolding in `prompts/` and `SKILL.md`
- Capability probes and validation scripts in `scripts/`
- Initial implementation backlog in `plans/`
- Deterministic benchmark runner and recorded release baseline in `eval/`

## Intended Public Surface

- `/deep-gvr <question>` starts a research run
- `/deep-gvr resume <session_id>` resumes a prior run
- Config lives at `~/.hermes/deep-gvr/config.yaml`
- Evidence lives under `~/.hermes/deep-gvr/sessions/<session_id>/`
- Resume checkpoints live at `~/.hermes/deep-gvr/sessions/<session_id>/checkpoint.json`

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
uv run python eval/run_eval.py --routing-probe fallback --output eval/results/local_results.json
```

If `uv` is not available yet, the local checks can also be run with a Python 3.12 interpreter and `PYTHONPATH=src`.

## Installation

For a local Hermes skill install, use the repo helper:

```bash
scripts/install.sh
scripts/setup_mcp.sh --check
```

`scripts/install.sh` creates a symlink install under `~/.hermes/skills/deep-gvr` by default. Use `--copy` if you need a copied install or `--target` to choose a different skills directory.

## Evaluation Baseline

The release baseline uses the deterministic fixture-backed benchmark suite in `eval/known_problems.json`. The current committed baseline result is `eval/results/baseline_results.json`, generated with `--routing-probe fallback` to match the documented current routing baseline.

The next planned implementation step is live prompt-driven benchmark execution, tracked in [plans/08-live-eval.md](plans/08-live-eval.md).

## Reference Docs

- [docs/README.md](docs/README.md)
- [docs/deep-gvr-architecture.md](docs/deep-gvr-architecture.md)
- [eval/README.md](eval/README.md)
- [plans/README.md](plans/README.md)
