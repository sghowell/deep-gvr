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
- Implemented baseline: the `qec_decoder_benchmark` analysis family now executes real Stim/PyMatching runs through local, Modal, and SSH backends while preserving the same normalized result contract.
- Current probe behavior: `scripts/run_capability_probes.py` reports per-environment readiness for all three backends, including local dependency checks, Modal CLI plus stub availability, and SSH/`scp` plus runtime-config readiness.
- Operator path: use `scripts/run_capability_probes.py --config ~/.hermes/deep-gvr/config.yaml` after configuring any remote backend so the probe details reflect the actual Modal and SSH settings you intend to use.
- Preferred outcome: local smoke tests plus environment-sensitive Modal and SSH readiness details.

### Analysis adapter families

- Question: are the OSS analysis families installed locally and ready for operator use?
- Implemented baseline: `scripts/run_capability_probes.py` now reports `analysis_adapter_families` across symbolic math, optimization, dynamics, QEC benchmarking, MBQC/Graphix, Perceval photonic, Pulser neutral-atom, tqec, and PyZX families.
- Current probe behavior: the probe reports `ready` only when every supported family has its expected local Python dependency set. Missing packages produce a structured family-by-family readiness map instead of silent non-support.
- Operator path: `scripts/release_preflight.py --operator` now surfaces the same readiness as an `analysis_adapter_families` check, blocking only when the configured default adapter family itself is unavailable and otherwise returning attention-level guidance for the missing optional families.
- Preferred outcome: operators can see exactly which OSS analysis families are usable before requesting those analyses live.

## Repository Support

- `scripts/run_capability_probes.py` runs the readiness probes.
- `src/deep_gvr/probes.py` contains the probe logic and default/fallback metadata.
- `src/deep_gvr/formal.py` contains the Hermes-MCP Tier 3 transport boundary and config preflight helpers.
- `scripts/setup_mcp.sh` can install and verify the Aristotle MCP stanza for the local Hermes config.
- `scripts/release_preflight.py` turns the probe results plus config/install checks into a release-grade operator readiness report.
- `src/deep_gvr/release_surface.py` lifts analysis-adapter readiness into the release preflight report so missing dependencies are visible at install/operator time.
- `src/deep_gvr/tier1.py` implements the checkpoint artifact and resume-safe control flow.
- `src/deep_gvr/evidence.py` derives Hermes memory summaries and Parallax-compatible manifests from the file-backed session artifacts.
- `plans/01-capability-probes.md` is the execution plan for deepening these probes during implementation.
