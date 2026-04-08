# Architecture Status

`docs/deep-gvr-architecture.md` remains the target-state design for `deep-gvr`.
This ledger records where the repository already matches that target and where
the remaining architecture work is still owned by a numbered plan. Runtime
fallbacks are temporary gaps, not acceptable end states.

## How to Use This Ledger

- `realized`: implemented and aligned with the architecture target
- `temporary_gap`: implemented enough to function today, but still using a
  substitution or workaround that must be retired
- `planned`: explicitly deferred architecture work with an owning plan
- `blocked_external`: architecture work that still depends on Hermes or another
  external platform before the repo can complete it

## Realized Architecture Baseline

| Item ID | Status | Target Behavior | Evidence |
|---|---|---|---|
| tier1-loop | realized | The repo has a checkpointed Generator-Verifier-Reviser loop with explicit failure admission and append-only evidence. | `src/deep_gvr/tier1.py`, `plans/03-tier1-loop.md` |
| local-tier2-stim | realized | Tier 2 empirical verification can execute real local Stim and PyMatching runs. | `adapters/stim_adapter.py`, `plans/04-tier2-stim.md` |
| remote-backend-completion | realized | Tier 2 backend dispatch is complete across local, Modal, and SSH execution, with readiness reported per environment. | `adapters/stim_adapter.py`, `src/deep_gvr/probes.py`, `plans/28-remote-backend-completion.md` |
| tier3-aristotle-transport | realized | The orchestrator can dispatch Aristotle through Hermes MCP when the local environment is configured, with direct Aristotle CLI fallback when the Hermes->MCP transport fails at runtime. | `src/deep_gvr/formal.py`, `plans/10-aristotle-transport.md`, `plans/11-transport-activation.md`, `plans/34-aristotle-cli-fallback.md` |
| formal-proof-lifecycle | realized | Tier 3 proof attempts support submission, polling, checkpointed resume, and long-running completion on the shipped harness path. | `src/deep_gvr/formal.py`, `src/deep_gvr/tier1.py`, `plans/27-formal-proof-lifecycle.md` |
| checkpoint-resume | realized | `/deep-gvr resume <session_id>` can continue from the last complete checkpoint. | `src/deep_gvr/cli.py`, `src/deep_gvr/tier1.py`, `plans/09-skill-integration.md` |
| hermes-native-orchestrator | realized | `/deep-gvr` runs through a Hermes-native delegated skill-orchestrator path instead of the old top-level per-role prompt harness. | `src/deep_gvr/orchestrator.py`, `src/deep_gvr/cli.py`, `SKILL.md`, `plans/25-hermes-native-orchestrator.md` |
| evidence-system-completion | realized | Evidence is persisted as files, Hermes memory summaries, and Parallax-compatible exports. | `src/deep_gvr/tier1.py`, `src/deep_gvr/evidence.py`, `plans/29-evidence-system-completion.md` |
| benchmark-harness | realized | Deterministic and live benchmark runners exist with recorded artifacts and repeatable subset runs. | `eval/run_eval.py`, `src/deep_gvr/evaluation.py`, `plans/07-eval-release.md` through `plans/23-analytical-breadth-stability.md` |

## Open Architecture Items

| Item ID | Status | Target Behavior | Current Substitution / Workaround | Blocking Dependency | Owning Slice | Retirement Criteria |
|---|---|---|---|---|---|---|
| subagent-capability-closure | blocked_external | Generator and Verifier use distinct per-subagent routes, and the Verifier can call Aristotle MCP directly. | The repo now threads requested per-role routes plus delegated `capability_evidence` through the wrapper contract and artifacts, but real delegated runs still fail to produce observed route/MCP closure evidence and Tier 3 normally stays orchestrator-mediated. | Hermes model-override and delegated MCP inheritance behavior still need to be proven or enabled. | [26-subagent-capability-closure.md](../plans/26-subagent-capability-closure.md) | The probe reports `ready` for per-subagent routing and delegated MCP access, the verifier can call Aristotle directly, and prompt/temperature decorrelation is no longer a supported steady-state strategy. |
| release-surface-completion | planned | The repo ships a complete Hermes skill release surface, including agentskills.io-ready packaging, preflight, and operator validation. | The repo has install helpers and a CLI, but no end-to-end publication workflow or release gating for the intended public surface. | Packaging, publication assets, operator preflight, and release documentation. | [30-release-surface-completion.md](../plans/30-release-surface-completion.md) | Release artifacts, install steps, preflight checks, and publication instructions are exercised and documented end to end. |
| opengauss-formal-backend | planned | OpenGauss is supported as the interactive Lean backend alongside Aristotle. | The architecture documents OpenGauss only as a future backend and the runtime has no selector or transport for it. | OpenGauss environment, backend contracts, and operator workflow. | [31-opengauss-formal-backend.md](../plans/31-opengauss-formal-backend.md) | Formal backend selection supports OpenGauss, docs describe the operator flow, and benchmark coverage includes an OpenGauss-backed case. |
| fanout-and-escalation | planned | The orchestrator can optionally branch into multiple hypotheses and escalate failures through structured decomposition. | The current loop is strictly sequential and ends with structured failure reporting only. | Orchestrator state expansion, benchmark additions, and checkpoint-safe fan-out semantics. | [32-fanout-and-escalation.md](../plans/32-fanout-and-escalation.md) | Fan-out and escalation are configurable, checkpoint-safe, evidence-aware, and covered by tests and benchmarks. |
| domain-adapter-expansion | planned | The architecture supports non-Stim adapters for FBQC, decoder evaluation, and resource-state optimization. | The repo has FBQC domain context only; no non-Stim adapters or matching benchmark cases exist. | Adapter contracts, domain prompts, and domain-specific benchmark corpus expansion. | [33-domain-adapter-expansion.md](../plans/33-domain-adapter-expansion.md) | New adapters, prompts, schemas, and benchmarks ship together and are validated like the Stim path. |
