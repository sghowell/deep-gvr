# System Overview

`deep-gvr` is a Hermes skill bundle plus supporting Python utilities.

## Public Surface

- `/deep-gvr <question>` starts a session
- `/deep-gvr resume <session_id>` resumes a session
- Config path: `~/.hermes/deep-gvr/config.yaml`
- Evidence path: `~/.hermes/deep-gvr/sessions/<session_id>/`
- Checkpoint path: `~/.hermes/deep-gvr/sessions/<session_id>/checkpoint.json`

## Core Components

- Orchestrator procedure in `SKILL.md`
- Role prompts in `prompts/`
- Typed contracts and helper code in `src/deep_gvr/`
- Tier 1 session runner and persistence helpers in `src/deep_gvr/tier1.py`
- Adapters in `adapters/`
- Schemas in `schemas/`
- Fixtures in `templates/`
- Capability probes and repo checks in `scripts/`

## Verification Model

- Tier 1 analytical verification always runs
- Tier 2 empirical verification is triggered by quantitative claims
- Tier 3 formal verification is triggered by formalizable claims
- Any failed applicable tier is a failed candidate
- Unavailable optional tiers must produce explicit caveats or `CANNOT_VERIFY`
- The local Tier 2 baseline uses the Stim adapter with PyMatching decoding
- The Tier 3 baseline is orchestrator-mediated Aristotle routing with structured unavailable/timeout results

## Early Defaults

- No Hermes fork
- Python 3.12 and `uv`
- Sequential GVR loop first
- Resume from the last complete checkpoint instead of replaying partial phases
- Cross-model verification preferred, with prompt/temperature decorrelation as the fallback
- Local, Modal, and SSH backends represented from the start through the adapter interface
