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
| fanout-and-escalation | realized | The orchestrator can keep a checkpoint-safe active branch plus queued alternative/decomposition branches, and repeated failures trigger explicit escalation evidence instead of silent retries. | `src/deep_gvr/tier1.py`, `src/deep_gvr/contracts.py`, `eval/known_problems.json`, `plans/32-fanout-and-escalation.md` |
| domain-adapter-expansion | realized | Tier 2 is a generalized OSS analysis boundary with scientific and quantum adapter families, not a Stim-only simulator hook. | `adapters/registry.py`, `src/deep_gvr/tier1.py`, `src/deep_gvr/probes.py`, `eval/known_problems.json`, `plans/33-domain-adapter-expansion.md` |
| mathcode-formal-backend | realized | MathCode is supported as an additional local Lean formalization backend alongside Aristotle. | `src/deep_gvr/formal.py`, `src/deep_gvr/probes.py`, `eval/known_problems.json`, `plans/35-mathcode-formal-backend.md` |
| release-surface-completion | realized | The repo ships a complete Hermes skill release surface, including checked-in publication assets, install/preflight helpers, and operator validation docs. | `scripts/install.sh`, `scripts/release_preflight.py`, `release/agentskills.publication.json`, `docs/release-workflow.md`, `plans/30-release-surface-completion.md` |
| codex-local-surface | realized | Codex local is supported as a first-class operator surface over the same typed runtime, with a dedicated skill, install helper, and preflight path. | `codex_skill/SKILL.md`, `scripts/install_codex.sh`, `scripts/codex_preflight.py`, `plans/46-codex-local-surface.md` |
| codex-plugin-surface | realized | The repo ships a packaged Codex plugin bundle and local marketplace metadata over the same Codex-local workflow. | `plugins/deep-gvr/.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`, `plans/48-codex-plugin-surface.md` |
| codex-automations | realized | The repo ships a checked-in Codex automation pack plus export helpers for recurring benchmark, CI triage, release, and docs-smoke workflows. | `codex_automations/catalog.json`, `scripts/export_codex_automations.py`, `plans/49-codex-automations.md` |
| codex-review-and-visual-qa | realized | The repo ships an exportable Codex review/QA prompt kit for pull-request review and browser-driven public-docs QA, including SSH/devbox-friendly operator guidance. | `codex_review_qa/catalog.json`, `scripts/export_codex_review_qa.py`, `plans/52-codex-review-and-visual-qa.md` |
| codex-subagent-integration | realized | The repo ships an exportable Codex subagent prompt kit for branch-safe multi-agent fanout and parallel surface review over the existing runtime and git/worktree discipline. | `codex_subagents/catalog.json`, `scripts/export_codex_subagents.py`, `plans/54-codex-subagent-integration.md` |
| codex-ssh-devbox-surface | realized | The repo ships an explicit Codex SSH/devbox remote-operator bundle plus a dedicated Codex preflight mode for remote validator readiness. | `codex_ssh_devbox/catalog.json`, `scripts/export_codex_ssh_devbox.py`, `scripts/codex_preflight.py`, `plans/53-codex-ssh-devbox-surface.md` |
| codex-backend-abstraction | realized | The runtime now selects an explicit orchestrator backend through a typed backend abstraction instead of instantiating Hermes directly in the CLI path. | `src/deep_gvr/orchestrator.py`, `src/deep_gvr/cli.py`, `src/deep_gvr/runtime_paths.py`, `plans/55-codex-backend-abstraction.md` |
| codex-local-backend | realized | Codex local is supported as a real orchestrator backend so the Codex path no longer requires Hermes underneath when `runtime.orchestrator_backend=codex_local` is selected. | `src/deep_gvr/orchestrator.py`, `src/deep_gvr/cli.py`, `src/deep_gvr/release_surface.py`, `plans/56-codex-local-backend.md` |
| codex-native-subagent-backend | realized | The native `codex_local` backend now executes Generator, Verifier, and Reviser as separate Codex role calls over `Tier1LoopRunner` instead of routing the whole run through one opaque backend-summary prompt. | `src/deep_gvr/orchestrator.py`, `src/deep_gvr/cli.py`, `src/deep_gvr/tier1.py`, `plans/58-codex-native-subagent-backend.md` |
| codex-ssh-devbox-execution | realized | A remote Codex SSH/devbox session can gate and execute the native `codex_local` backend from the stronger machine instead of stopping at a prompt/export surface. | `src/deep_gvr/codex_ssh_devbox_runtime.py`, `scripts/codex_ssh_devbox_run.py`, `src/deep_gvr/release_surface.py`, `plans/57-codex-ssh-devbox-execution.md` |
| benchmark-harness | realized | Deterministic and live benchmark runners exist with recorded artifacts and repeatable subset runs. | `eval/run_eval.py`, `src/deep_gvr/evaluation.py`, `plans/07-eval-release.md` through `plans/23-analytical-breadth-stability.md` |

## Open Architecture Items

| Item ID | Status | Target Behavior | Current Substitution / Workaround | Blocking Dependency | Owning Slice | Retirement Criteria |
|---|---|---|---|---|---|---|
| subagent-capability-closure | blocked_external | Generator and Verifier use distinct per-subagent routes, and the Verifier can call Aristotle MCP directly. | The repo now threads requested per-role routes plus delegated `capability_evidence` through the wrapper contract and artifacts, but real delegated runs still fail to produce observed route/MCP closure evidence and Tier 3 normally stays orchestrator-mediated. The dedicated Hermes v0.9 reassessment and the follow-up Hermes v0.10 recheck both timed out on the route-focused and verifier-MCP-focused delegated runs and returned no observed `capability_evidence`. | Hermes model-override and delegated MCP inheritance behavior still need to be proven or enabled. | [26-subagent-capability-closure.md](../plans/26-subagent-capability-closure.md) | The probe reports `ready` for per-subagent routing and delegated MCP access, the verifier can call Aristotle directly, and prompt/temperature decorrelation is no longer a supported steady-state strategy. |
| opengauss-formal-backend | blocked_external | OpenGauss is supported as the interactive Lean backend alongside Aristotle. | The runtime still has no selector or transport for OpenGauss, and the current local install path is still unhealthy: the raw checkout fails `./gauss doctor` before real Gauss validation because required Python dependencies are missing (latest local run: `prompt_toolkit`), while the default and README-pinned Morph targets still end in `404` after redirects. The repo now exposes a blocked-state `opengauss_transport` probe plus `scripts/diagnose_opengauss.py`, but that diagnostics surface does not retire the backend gap. | A valid upstream OpenGauss install/distribution path plus backend contracts, transport code, and operator workflow. | [31-opengauss-formal-backend.md](../plans/31-opengauss-formal-backend.md) | Formal backend selection supports OpenGauss, docs describe the operator flow, benchmark coverage includes an OpenGauss-backed case, and the local installer produces a working `gauss` runtime again. |
