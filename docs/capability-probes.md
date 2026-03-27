# Capability Probes

The architecture document identifies several implementation unknowns that are important enough to probe before deeper feature work.

## Probe Matrix

### Per-subagent model routing

- Question: can Hermes route different models to delegated subagents?
- Default until proven otherwise: assume no per-subagent override support.
- Current baseline: the generic routing helper resolves direct per-role routes when the probe is `ready`; otherwise it records the shared orchestrator route plus role-specific temperature decorrelation in evidence. The live CLI/eval path is narrower: it makes separate top-level `hermes chat` calls, so concrete role-model pins can still be attempted there with shared-route fallback when Hermes rejects the explicit provider/model path.
- Preferred outcome: explicit generator and verifier model overrides.
- Fallback: use prompt separation plus temperature decorrelation and document the limitation.

### Subagent MCP inheritance

- Question: do delegated subagents inherit MCP tool access?
- Default until proven otherwise: assume verifier-side MCP access is not guaranteed.
- Current baseline: Tier 3 is mediated through the orchestrator, which persists formal request/results artifacts and passes returned results back into verification.
- Preferred outcome: verifier can call Aristotle directly.
- Fallback: orchestrator mediates formal verification requests and passes results back into verification.

### Aristotle transport

- Question: can the orchestrator dispatch Aristotle proof attempts through the locally configured Hermes MCP transport?
- Default until proven otherwise: assume Tier 3 falls back unless Hermes, `ARISTOTLE_API_KEY`, and `mcp_servers.aristotle` are all present.
- Current baseline: the formal verifier checks the Hermes config, then dispatches Tier 3 through `hermes chat` plus the configured Aristotle MCP tools when available.
- Operator path: use `scripts/setup_mcp.sh --install --check` to install the Aristotle MCP stanza into `~/.hermes/config.yaml` and confirm the transport preflight before live Tier 3 runs.
- Preferred outcome: the orchestrator records a real Tier 3 transport trace and returned proof results.
- Fallback: persist the formal request, record why transport was unavailable, and pass structured `unavailable` results back into verification.

### Session checkpoint and resume

- Question: what minimal state is required to resume a run safely?
- Implemented baseline: persist loop state, verdict history, and artifact references in `sessions/<session_id>/checkpoint.json`.
- Current command surface: `uv run deep-gvr resume <session_id>` loads the same configured evidence directory and resumes from that checkpoint.
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
- `src/deep_gvr/formal.py` contains the Hermes-MCP Tier 3 transport boundary and config preflight helpers.
- `scripts/setup_mcp.sh` can install and verify the Aristotle MCP stanza for the local Hermes config.
- `src/deep_gvr/tier1.py` implements the checkpoint artifact and resume-safe control flow.
- `plans/01-capability-probes.md` is the execution plan for deepening these probes during implementation.
