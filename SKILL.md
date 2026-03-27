# deep-gvr

deep-gvr is a Hermes skill scaffold for agentic scientific research with a generator-verifier-reviser loop.

## Current State

The repo now includes a Python Tier 1 orchestration helper with append-only evidence logging and checkpoint-based resume, plus a live evaluation path that executes the real generator, verifier, and reviser prompts through `hermes chat`. The top-level `/deep-gvr` slash command wiring is still scaffolded; this file remains the operating contract for the future parent-agent procedure.

## Intended Commands

- `/deep-gvr <question>` starts a new session
- `/deep-gvr resume <session_id>` resumes a prior session
- `python eval/run_eval.py --mode live ...` runs the prompt stack against the benchmark corpus and records live artifacts under `eval/results/live/`

## Required Inputs

- research question
- active config at `~/.hermes/deep-gvr/config.yaml`
- prompt files in `prompts/`
- domain context from `domain/`

## Artifacts

- evidence log: `~/.hermes/deep-gvr/sessions/<session_id>.jsonl`
- session metadata: `~/.hermes/deep-gvr/sessions/index.json`
- session checkpoint: `~/.hermes/deep-gvr/sessions/<session_id>/checkpoint.json`
- artifacts: `~/.hermes/deep-gvr/sessions/<session_id>/artifacts/`

## Implementation Notes

- Tier 1 analytical verification is always required.
- The verifier input must remain isolated to the candidate artifact plus iteration metadata.
- Resume continues from the last complete phase recorded in `checkpoint.json`.
- Tier 2 empirical verification is claim-driven through the simulator adapter boundary.
- The orchestrator mediates Tier 2 as verifier -> simulator adapter -> verifier, persisting both the spec and normalized results under the session artifacts directory.
- Tier 3 formal verification is claim-driven and degrades gracefully when unavailable.
- The orchestrator mediates Tier 3 as verifier -> formal backend -> verifier, persisting both the formal request and returned results under the session artifacts directory.
- Cross-model verification is preferred. The effective route is derived from `models.orchestrator`, `models.generator`, `models.verifier`, and `models.reviser` plus the routing probe.
- If Hermes cannot route models per subagent, fall back to the orchestrator route with prompt and temperature decorrelation, and record that limitation in evidence.
- Hermes CLI does not currently expose a temperature flag, so live evaluation records the intended fallback temperature values while relying on prompt separation only at execution time.
- Live evaluation bounds each `hermes chat` role call with a repo-local timeout so stalled model calls degrade into structured benchmark errors instead of hanging the run.

See [docs/system-overview.md](docs/system-overview.md), [docs/contracts-and-artifacts.md](docs/contracts-and-artifacts.md), and the plans in `plans/` before implementing the full orchestrator.
