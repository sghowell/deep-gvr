# System Overview

`deep-gvr` is a Hermes skill bundle plus supporting Python utilities.

## Public Surface

- `/deep-gvr <question>` starts a session
- `/deep-gvr resume <session_id>` resumes a session
- `uv run deep-gvr run "<question>"` is the repo-local command boundary that backs the skill procedure
- `uv run deep-gvr resume <session_id>` resumes a prior session through the same runtime
- Config path: `~/.hermes/deep-gvr/config.yaml`
- Evidence path: `~/.hermes/deep-gvr/sessions/<session_id>/`
- Checkpoint path: `~/.hermes/deep-gvr/sessions/<session_id>/checkpoint.json`

## Core Components

- Orchestrator procedure in `SKILL.md`
- Command runtime in `src/deep_gvr/cli.py`
- Role prompts in `prompts/`
- Typed contracts and helper code in `src/deep_gvr/`
- Tier 1 session runner and persistence helpers in `src/deep_gvr/tier1.py`
- Adapters in `adapters/`
- Schemas in `schemas/`
- Fixtures in `templates/`
- Deterministic and live benchmark runner in `eval/run_eval.py`
- Capability probes and repo checks in `scripts/`

## Verification Model

- Tier 1 analytical verification always runs
- Tier 2 empirical verification is triggered by quantitative claims
- Tier 3 formal verification is triggered by formalizable claims
- Any failed applicable tier is a failed candidate
- Unavailable optional tiers must produce explicit caveats or `CANNOT_VERIFY`
- The local Tier 2 baseline uses the Stim adapter with PyMatching decoding
- The Tier 3 baseline is orchestrator-mediated Aristotle routing through Hermes MCP when `mcp_servers.aristotle` is configured, with structured unavailable/timeout results otherwise

## Early Defaults

- No Hermes fork
- Python 3.12 and `uv`
- Sequential GVR loop first
- Resume from the last complete checkpoint instead of replaying partial phases
- Cross-model verification preferred, with prompt/temperature decorrelation as the fallback
- Effective routing is derived deterministically from config plus probe state and recorded in evidence artifacts
- Release readiness is tracked with a deterministic benchmark suite and a committed baseline report
- Prompt quality and mediation behavior can be exercised with a separate live benchmark mode that records timestamped run artifacts
- Live benchmark runs share the same repo-local domain-context loader as the CLI
- Live Hermes prompt execution defaults to a compact prompt profile, with a full profile reserved for debugging prompt behavior
- Compact live verification uses a dedicated verifier prompt and tighter payload shape to reduce verifier-request bulk on the real Hermes route
- Live generator/verifier/reviser calls default to a constrained Hermes tool surface instead of inheriting the full interactive CLI tool policy
- The live role timeout is role-aware: verifier gets a higher floor, while Tier 3 transport keeps its own proof timeout
- Local, Modal, and SSH backends represented from the start through the adapter interface
