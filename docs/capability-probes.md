# Capability Probes

The architecture document identifies several implementation unknowns that are important enough to probe before deeper feature work.
The remaining open probe defaults are temporary gaps, not accepted end states; each open item points to a retirement slice in the architecture-completion roadmap.

## Probe Matrix

### Per-subagent model routing

- Question: can Hermes route different models to delegated subagents?
- Default until proven otherwise: assume no per-subagent override support.
- Current baseline: the shipped command surface now runs through the delegated Hermes skill runtime, while the explicit live benchmark harness keeps the separate prompt-role calls for isolated testing. Probe `ready` status must now come from observed runtime evidence rather than environment hints; until that evidence exists, the generic routing helper records the shared orchestrator route plus role-specific temperature decorrelation in evidence, and the live benchmark harness can still attempt concrete top-level role pins with shared-route fallback when Hermes rejects the explicit provider/model path. The delegated runtime contract now requires `capability_evidence` to distinguish requested `role_routes` from actually observed route behavior.
- Preferred outcome: explicit generator and verifier model overrides.
- Temporary gap: the shared-route path remains in place only until the runtime can close this capability. Retirement slice: [26-subagent-capability-closure.md](../plans/26-subagent-capability-closure.md)

### Subagent MCP inheritance

- Question: do delegated subagents inherit MCP tool access?
- Default until proven otherwise: assume verifier-side MCP access is not guaranteed.
- Current baseline: Tier 3 is mediated through the orchestrator, which persists formal request/results artifacts and passes returned results back into verification. Probe `ready` status for delegated MCP inheritance must come from observed verifier-side runtime evidence rather than configuration hints alone, and the delegated runtime contract now requires `capability_evidence` to report verifier-direct MCP usage only when it was actually observed.
- Preferred outcome: verifier can call Aristotle directly.
- Temporary gap: orchestrator-mediated Tier 3 remains only until verifier-side MCP access is real. Retirement slice: [26-subagent-capability-closure.md](../plans/26-subagent-capability-closure.md)

### Aristotle transport

- Question: can the orchestrator dispatch Aristotle proof attempts through the locally configured Hermes MCP transport?
- Default until proven otherwise: assume Tier 3 falls back unless Hermes, `ARISTOTLE_API_KEY`, and `mcp_servers.aristotle` are all present.
- Current baseline: the formal verifier checks the Hermes config, uses persisted Aristotle proof handles for submission/polling on the shipped harness path, and still records Hermes MCP transport details when that boundary is used.
- Operator path: use `scripts/setup_mcp.sh --install --check` to install the Aristotle MCP stanza into `~/.hermes/config.yaml` and confirm the transport preflight before live Tier 3 runs.
- Preferred outcome: the orchestrator records a real Tier 3 transport trace and returned proof results.
- Implemented baseline: Tier 3 now persists `formal_request`, `formal_lifecycle`, `formal_transport`, and `formal_results` artifacts so proof polling can resume without starting over.

### Session checkpoint and resume

- Question: what minimal state is required to resume a run safely?
- Implemented baseline: persist loop state, verdict history, and artifact references in `sessions/<session_id>/checkpoint.json`.
- Current command surface: `uv run deep-gvr resume <session_id>` loads the same configured evidence directory and resumes from that checkpoint.
- Evidence integration baseline: each saved checkpoint now also derives `session_memory_summary.json`, a Parallax-compatible `parallax_manifest.json`, and an optional Hermes-memory summary entry in `~/.hermes/memories/MEMORY.md` when `persist_to_memory` is enabled.
- Preferred outcome: `/deep-gvr resume <session_id>` can reconstruct the next orchestrator step without hidden memory.

### Backend dispatch

- Question: how should `local`, `modal`, and `ssh` be selected and validated?
- Default until proven otherwise: all adapters expose the same CLI and return structured errors when a backend is unavailable.
- Current baseline: the Stim adapter runs real local simulations and returns structured unavailability for Modal and SSH.
- Preferred outcome: local smoke tests plus environment-sensitive Modal and SSH probes.
- Temporary gap: Modal and SSH unavailability is only the current interim state. Retirement slice: [28-remote-backend-completion.md](../plans/28-remote-backend-completion.md)

## Repository Support

- `scripts/run_capability_probes.py` runs the readiness probes.
- `src/deep_gvr/probes.py` contains the probe logic and default/fallback metadata.
- `src/deep_gvr/formal.py` contains the Hermes-MCP Tier 3 transport boundary and config preflight helpers.
- `scripts/setup_mcp.sh` can install and verify the Aristotle MCP stanza for the local Hermes config.
- `src/deep_gvr/tier1.py` implements the checkpoint artifact and resume-safe control flow.
- `src/deep_gvr/evidence.py` derives Hermes memory summaries and Parallax-compatible manifests from the file-backed session artifacts.
- `plans/01-capability-probes.md` is the execution plan for deepening these probes during implementation.
