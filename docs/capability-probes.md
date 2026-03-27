# Capability Probes

The architecture document identifies several implementation unknowns that are important enough to probe before deeper feature work.

## Probe Matrix

### Per-subagent model routing

- Question: can Hermes route different models to delegated subagents?
- Default until proven otherwise: assume no per-subagent override support.
- Preferred outcome: explicit generator and verifier model overrides.
- Fallback: use prompt separation plus temperature decorrelation and document the limitation.

### Subagent MCP inheritance

- Question: do delegated subagents inherit MCP tool access?
- Default until proven otherwise: assume verifier-side MCP access is not guaranteed.
- Preferred outcome: verifier can call Aristotle directly.
- Fallback: orchestrator mediates formal verification requests and passes results back into verification.

### Session checkpoint and resume

- Question: what minimal state is required to resume a run safely?
- Implemented baseline: persist loop state, verdict history, and artifact references in `sessions/<session_id>/checkpoint.json`.
- Preferred outcome: `/deep-gvr resume <session_id>` can reconstruct the next orchestrator step without hidden memory.
- Fallback: resume from the last complete checkpoint and require a fresh verification pass for any incomplete step.

### Backend dispatch

- Question: how should `local`, `modal`, and `ssh` be selected and validated?
- Default until proven otherwise: all adapters expose the same CLI and return structured errors when a backend is unavailable.
- Current baseline: the Stim adapter runs real local simulations and returns structured unavailability for Modal and SSH.
- Preferred outcome: local smoke tests plus environment-sensitive Modal and SSH probes.
- Fallback: mark unsupported backends unavailable without blocking local development.

## Repository Support

- `scripts/run_capability_probes.py` runs the readiness probes.
- `src/deep_gvr/probes.py` contains the probe logic and default/fallback metadata.
- `src/deep_gvr/tier1.py` implements the checkpoint artifact and resume-safe control flow.
- `plans/01-capability-probes.md` is the execution plan for deepening these probes during implementation.
