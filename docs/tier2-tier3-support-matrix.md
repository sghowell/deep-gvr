# Tier 2 and Tier 3 Support Matrix

This page records the shipped support boundary for `deep-gvr`'s Tier 2 analysis
families and Tier 3 formal backends.

The important distinction is that several different questions are easy to blur
together:

- Is there a real runtime implementation?
- Does the repo have deterministic coverage for it?
- Where is it designed to execute today?
- What does the current capability probe say about this machine?

Current machine readiness is dynamic. Use
`uv run python scripts/run_capability_probes.py --json` for the live answer on
the machine you plan to use.

## How to Read This Matrix

- Runtime support: a shipped code path exists in the runtime.
- Deterministic coverage: the repo already has unit tests or known-problem
  benchmark cases for that surface.
- Execution backend support: local-only unless a broader backend is stated
  explicitly.
- Reference probe baseline: the probe state observed in the reference repo
  environment on April 22, 2026 after syncing the validated full-portfolio
  environment with `uv sync --all-extras`.

## Tier 2 Analysis Families

Tier 2 completion does not mean every family must run on every execution
backend. It means every shipped family needs an explicit support statement and
an operator path that matches that statement.

| Family | Runtime support | Deterministic coverage | Execution backend support | Reference probe baseline | Remaining support gap |
|---|---|---|---|---|---|
| `symbolic_math` | Shipped adapter | `symbolic-verified-equivalence`, `symbolic-rejected-derivative` | `local` | ready in the reference environment | keep install guidance and shared-runtime signoff aligned |
| `optimization` | Shipped adapter | `optimization-verified-linear-program`, `optimization-rejected-assignment` | `local` | ready in the reference environment | keep install guidance and shared-runtime signoff aligned |
| `dynamics` | Shipped adapter | `dynamics-verified-decay` | `local` | ready in the reference environment | keep install guidance and shared-runtime signoff aligned |
| `qec_decoder_benchmark` | Shipped adapter | `simulation-verified-distance5`, `simulation-rejected-distance7` | `local`, `modal`, `ssh` | ready in the reference environment | repeated operator signoff across the claimed execution backends |
| `mbqc_graph_state` | Shipped adapter | `mbqc-verified-graphix-pattern` | `local` | ready in the reference environment | keep install guidance and local-runtime signoff aligned |
| `photonic_linear_optics` | Shipped adapter | `photonic-verified-basic-state` | `local` | ready in the reference environment | keep install guidance and local-runtime signoff aligned |
| `neutral_atom_control` | Shipped adapter | `neutral-atom-verified-register` | `local` | ready in the reference environment | keep install guidance and local-runtime signoff aligned |
| `topological_qec_design` | Shipped adapter | `tqec-verified-gallery-block-graph` | `local` | ready in the reference environment | keep install guidance and local-runtime signoff aligned |
| `zx_rewrite_verification` | Shipped adapter | `zx-verified-qasm-rewrite` | `local` | ready in the reference environment | keep install guidance and local-runtime signoff aligned |

Current Tier 2 facts:

- All nine Tier 2 families have real runtime adapters.
- All nine Tier 2 families have deterministic benchmark coverage in the repo.
- The validated full-portfolio install path is `uv sync --all-extras`.
- Only `qec_decoder_benchmark` currently ships explicit `local` / `modal` /
  `ssh` execution-backend support.
- The other eight Tier 2 families are local-only today.

## Tier 3 Formal Backends

Tier 3 completion is about the shipped backends, Aristotle and MathCode.
OpenGauss remains an intended backend family member, but it is not part of the
standard shipped path today.

| Backend | Runtime support | Transport shape | Lifecycle support | Deterministic coverage | Reference probe baseline | Remaining support gap |
|---|---|---|---|---|---|---|
| Aristotle | Shipped backend | Hermes MCP primary, direct Aristotle CLI fallback | submission, polling, and checkpointed resume | dedicated `tier3-support` subset plus `formal-proved-repetition-majority` and `formal-unavailable-repetition-scaling` | ready in the reference environment | stronger backend-parity signoff and continued honesty about the Hermes-shaped transport boundary |
| MathCode | Shipped backend | local CLI | bounded single-shot execution; no shipped submission/poll/resume lifecycle | dedicated `tier3-support` subset plus `formal-mathcode-nat-add-zero` | ready in the reference environment | backend-parity signoff and the separate OpenGauss completion decision in the remaining Tier 3 completion work |
| OpenGauss | not part of the shipped path | diagnostics only; no integrated transport | none | none | ready for local runtime diagnostics in the reference environment | repo-owned backend selection, transport, operator workflow, and benchmark coverage in the owning OpenGauss backend slice |

## Reference Readiness Baseline

The latest reference-environment capability probe on April 22, 2026, after
`uv sync --all-extras`, reported:

- `analysis_adapter_families`: `9/9` ready families
- `backend_dispatch`: `local_ready=true`, `modal_ready=false`,
  `ssh_ready=false`
- `aristotle_transport`: `ready`
- `mathcode_transport`: `ready`
- `opengauss_transport`: `ready`
- dedicated `tier3-support` evaluation subset: `3/3` passing on the shipped
  Aristotle and MathCode cases

That probe result is a machine snapshot, not a universal product claim. The
machine you plan to use should always be checked directly.

## What Complete Support Means

For Tier 2, complete support means:

- every shipped family has an explicit execution-backend support statement
- install and preflight surfaces report missing dependencies precisely
- the repo provides a single validated full-portfolio install path instead of
  leaving the broader families as ad hoc extras
- release preflight blocks unsupported backend selections for the configured
  default adapter family instead of pretending every family shares the QEC
  dispatch contract
- deterministic coverage is backed by runtime-facing validation, not only unit
  adapter tests
- the shared Tier 2 surface is validated under the shipped orchestrator
  backends where the claim is the same

For Tier 3, complete support means:

- Aristotle and MathCode both have explicit repeated shipped-backend validation
- the Aristotle lifecycle path and the MathCode bounded local path are both
  documented exactly as they behave in probes, preflight, and operator docs
- Aristotle remains honestly described as Hermes-shaped until that dependency is
  actually retired
- OpenGauss local runtime readiness is no longer the blocker; complete support now requires the repo-owned backend-selection, transport, operator-flow, and benchmark work in the owning OpenGauss backend slice
