# deep-gvr

deep-gvr is a Hermes skill scaffold for agentic scientific research with a generator-verifier-reviser loop.

## Current State

This skill file is intentionally a readiness scaffold. It defines the intended operating contract, artifact locations, and validation boundaries before the full orchestrator procedure is implemented.

## Intended Commands

- `/deep-gvr <question>` starts a new session
- `/deep-gvr resume <session_id>` resumes a prior session

## Required Inputs

- research question
- active config at `~/.hermes/deep-gvr/config.yaml`
- prompt files in `prompts/`
- domain context from `domain/`

## Artifacts

- evidence log: `~/.hermes/deep-gvr/sessions/<session_id>.jsonl`
- session metadata: `~/.hermes/deep-gvr/sessions/index.json`
- artifacts: `~/.hermes/deep-gvr/sessions/<session_id>/artifacts/`

## Implementation Notes

- Tier 1 analytical verification is always required.
- Tier 2 empirical verification is claim-driven through the simulator adapter boundary.
- Tier 3 formal verification is claim-driven and degrades gracefully when unavailable.
- Cross-model verification is preferred. If Hermes cannot route models per subagent, fall back to prompt and temperature decorrelation.

See [docs/system-overview.md](docs/system-overview.md), [docs/contracts-and-artifacts.md](docs/contracts-and-artifacts.md), and the plans in `plans/` before implementing the full orchestrator.
