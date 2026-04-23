# Backend Parity Matrix

This matrix records the shipped repo-owned backend contract for `hermes` and
`codex_local`.

It is intentionally narrower than every product capability around Hermes or
Codex. It covers what `deep-gvr` actually owns in-repo today: Tier 1 loop
behavior, routing, evidence, checkpoints, Tier 2, Tier 3, release/preflight,
remote execution, and benchmark visibility.

Excluded from the parity floor:

- blocked delegated-capability closure that neither backend ships today
- product-managed Codex live delegation state

## Status Meanings

- `parity`: both backends ship the capability at the same repo-owned level
- `codex_stronger`: both support the shared contract, and `codex_local` also
  ships an extra repo-owned advantage
- `shared_open_item`: not a Codex-behind-Hermes gap because the capability is
  not shipped on either backend or remains a shared runtime limitation

## Matrix

| Surface | Hermes backend today | Codex backend today | Status | Notes |
|---|---|---|---|---|
| Tier 1 run/resume loop | Delegated orchestrator path over the typed loop with checkpointed resume | Native role-separated loop over the same typed runtime with checkpointed resume | `parity` | Both ship the same Generator/Verifier/Reviser semantics and resume behavior. |
| Role routing and backend selection | Explicit routing plan plus live-route fallback on invalid configured role routes | Explicit routing plan plus live-route fallback on invalid configured role routes | `parity` | Codex fallback now matches the shipped Hermes route-recovery behavior. |
| Transcript and evidence artifacts | Standard session evidence plus delegated orchestrator transcript artifact | Standard session evidence plus native per-role transcript artifact and Codex-specific capability evidence | `codex_stronger` | Codex records finer per-role response objects while preserving the same artifact ownership model. |
| Live benchmark harness | Live benchmark runner executes through the Hermes role harness | Live benchmark runner executes through the Codex-native role harness when `runtime.orchestrator_backend=codex_local` | `parity` | The benchmark harness now follows the selected runtime backend instead of forcing Hermes. |
| Tier 2 family coverage | Full shipped Tier 2 family set through the shared runtime | Full shipped Tier 2 family set through the shared runtime | `parity` | Family availability and backend dispatch remain adapter-owned, not orchestrator-owned. |
| Tier 2 backend dispatch | `local`, `modal`, and `ssh` where the selected family supports them | `local`, `modal`, and `ssh` where the selected family supports them | `parity` | The current shipped broad backend dispatch remains QEC-only by design for both backends. |
| Tier 3 Aristotle path | Shared formal layer with Hermes MCP primary transport and CLI fallback | Same shared formal layer with Hermes MCP primary transport and CLI fallback | `parity` | Aristotle transport is still Hermes-shaped, but it does not leave Codex behind Hermes. |
| Tier 3 MathCode path | Shared bounded local CLI path | Same shared bounded local CLI path | `parity` | No backend-specific gap. |
| Tier 3 OpenGauss path | Shared bounded local `gauss chat -Q` CLI path with session-id/transcript capture when available | Same shared bounded local `gauss chat -Q` CLI path with session-id/transcript capture when available | `parity` | No backend-specific gap; both backends use the same shipped local OpenGauss transport. |
| Release install and preflight | Hermes install and release preflight remain supported | Codex install and preflight remain supported, and Hermes can still be installed alongside it | `parity` | Each backend keeps its operator path without removing the other. |
| Remote stronger-machine execution | No repo-owned Hermes-specific remote orchestrator path | Repo-owned Codex SSH/devbox bootstrap plus runtime-backed remote execution | `codex_stronger` | Codex has the stronger remote operator surface today. |
| Review/QA and exported operator packs | Not part of the Hermes backend contract | Supported Codex-local operator extensions over the same runtime | `codex_stronger` | These are additive Codex surfaces, not parity requirements for Hermes. |
| Delegated subagent closure | Intended but still blocked externally | Intentionally outside the runtime contract and left product-managed/operator-pack only | `shared_open_item` | Neither backend ships repo-owned live delegated subagent closure today. |

## Practical Result

For the shipped repo-owned backend contract, `codex_local` is now at least as
capable as `hermes`:

- no current repo-owned Hermes capability leaves Codex behind
- Codex is stronger on transcript granularity and remote stronger-machine
  execution
- Hermes remains fully supported as the default slash-command backend

The remaining open architecture work is shared rather than parity-specific:

- delegated-capability closure on the Hermes side
- the separate future `openai_native` backend
