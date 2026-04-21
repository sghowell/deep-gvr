# deep-gvr: Architecture and Design

**Project:** deep-gvr  
**Repository:** `sghowell/deep-gvr`  
**License:** MIT  
**Status:** Target design with an implemented 0.1 release surface  
**Version:** 0.1.0  
**Date:** April 9, 2026  
**Author:** Sean

## 1. Overview

`deep-gvr` is a verification-oriented research system with Hermes, Codex-local, a packaged Codex plugin, Codex automation operator surfaces, a repo-owned Codex subagent prompt kit, a repo-owned Codex review/QA surface, and an explicit Codex `ssh/devbox` operator and execution path. The Codex-local backend is now a real role-separated runtime path, not only a top-level wrapper over the same session summary prompt, the remote Codex path now includes a repo-owned bootstrap helper instead of only manual setup guidance, and the review/QA surface now includes a typed evidence-preparation helper instead of only prompt exports.

It answers technical questions by running a generator-verifier-reviser loop and escalating into deeper computational or formal checks only when the claim warrants them. The system is designed for readers and operators who care about evidence, traceability, and explicit uncertainty more than raw conversational smoothness.

The architecture is domain-agnostic. Domain specialization lives in prompts, domain cards, and Tier 2 analysis adapters rather than in one narrow hard-coded workflow.

## 2. Design Goals

The design is organized around a few non-negotiable ideas:

1. **Verification is the core feature.** The generator is allowed to be wrong; the system becomes useful when the verifier can expose that.
2. **Tiered checking is better than one generic pass.** Some claims are analytical, some computational, and some formal.
3. **Failure must be explicit.** A structured inability to verify is better than a polished bluff.
4. **Evidence is part of the product.** A result without an inspectable trail is not enough for research-grade work.
5. **The system should stay open and composable.** Analysis families should plug in through adapters rather than through prompt-specific hacks.

## 3. System Model

At a high level, `deep-gvr` is a typed Python runtime with an explicit orchestrator-backend boundary plus Hermes, Codex-local, a packaged Codex plugin, Codex automation surfaces, a Codex subagent surface, and an explicit Codex `ssh/devbox` surface. A separate OpenAI-native backend is now planned as a future expansion, but it is not implemented today:

<figure class="doc-figure">
  <img src="../assets/system-model.svg" alt="deep-gvr system model diagram" />
<figcaption>Hermes, Codex local, the packaged Codex plugin, the checked-in Codex automation pack, the Codex subagent surface, and the explicit Codex `ssh/devbox` surface share the same typed runtime. The repo also ships a separate Codex review/QA surface for high-signal review workflows, including repo-owned evidence-bundle preparation before live review or browser inspection. The runtime owns evidence, adapters, formal transport, resume semantics, backend selection, and remote bootstrap, with Hermes as the default backend in the checked-in config and Codex local as a native backend option that now executes Generator, Verifier, and Reviser through separate Codex role calls and can also run from a remote Codex SSH/devbox machine.</figcaption>
</figure>

### Main Components

| Component | Role |
|---|---|
| Orchestrator | manages session state, evidence, resume, escalation, and user communication |
| Generator | produces candidate answers or proof sketches |
| Verifier | attacks those candidates and requests deeper checks when necessary |
| Reviser | repairs specific flaws without losing already-correct structure |
| Tier 2 analysis layer | runs OSS-backed computational checks through adapters |
| Tier 3 formal layer | runs proof-oriented backends and records transport state |

## 4. Verification Model

`deep-gvr` uses three verification tiers.

### Tier 1: Analytical Verification

Tier 1 always runs. It checks:

- logical consistency
- citation discipline
- scope and completeness
- plausibility
- overclaiming

Tier 1 is the universal floor. Every answer must survive it.

### Tier 2: Computational Analysis

Tier 2 is triggered when the claim requires executable checking rather than prose judgment alone.

Examples:

- symbolic identities
- optimization claims
- numerical dynamics
- decoder or threshold claims
- graph-state, photonic, neutral-atom, or ZX-based analyses

The important architectural point is that Tier 2 is an **analysis boundary**, not a single simulator hook.

### Tier 3: Formal Verification

Tier 3 is used when the answer contains formalizable theorem-like content.

The release surface supports:

- Aristotle
- MathCode

OpenGauss remains part of the intended backend family, but it is not yet on the standard shipped path.

## 5. Analysis Adapter Portfolio

The Tier 2 layer is deliberately broader than one research niche.

### Core Scientific Families

- symbolic math via SymPy
- optimization via OR-Tools plus SciPy/HiGHS
- dynamics via SciPy and QuTiP

### Quantum and Quantum-Adjacent Families

- QEC decoder benchmarking via Stim and PyMatching
- MBQC graph-state analysis via Graphix
- photonic linear optics via Perceval
- neutral-atom control via Pulser
- topological-QEC design via tqec
- ZX rewrite and equivalence checking via PyZX

Broad ecosystems such as Qiskit, Cirq, and PennyLane are better treated as interop surfaces than as the first public adapter abstraction.

## 6. Evidence, Checkpoints, and Resume

The system is designed to preserve a research trail, not merely a final answer.

Each session maintains:

- a checkpoint
- evidence records
- tier-specific artifacts
- derived memory and export summaries

That enables:

- explicit resume semantics
- post-run auditability
- portability of results into downstream systems

The evidence model is one of the main differences between `deep-gvr` and a generic answer-generation agent.

## 7. Escalation and Branching

Not every failed attempt should be answered by the same retry loop.

When repeated failure suggests the system is stuck, the orchestrator can:

- revise in place
- switch to a bounded alternative branch
- halt with an explicit failure outcome

This gives the system a structured way to explore alternative framings without degenerating into uncontrolled search.

## 8. Runtime Surface

The public command surface is:

- `/deep-gvr <question>`
- `/deep-gvr resume <session_id>`
- `codex exec -C /path/to/deep-gvr "Use the deep-gvr skill to answer: <question>"`
- `uv run python scripts/export_codex_automations.py --output-root /tmp/deep-gvr-codex-automations`
- `uv run python scripts/export_codex_subagents.py --output-root /tmp/deep-gvr-codex-subagents`
- `uv run python scripts/export_codex_review_qa.py --output-root /tmp/deep-gvr-codex-review-qa`
- `uv run python scripts/codex_review_qa_execute.py pull_request_review --output-root /tmp/deep-gvr-codex-review-qa-evidence/review --force`
- `uv run python scripts/codex_review_qa_execute.py public_docs_visual_qa --output-root /tmp/deep-gvr-codex-review-qa-evidence/docs --force`
- `uv run deep-gvr run "<question>"`
- `uv run deep-gvr resume <session_id>`
- `uv run python scripts/codex_remote_bootstrap.py --json`
- `uv run python scripts/codex_ssh_devbox_run.py run "<question>"`
- `uv run python scripts/codex_ssh_devbox_run.py resume <session_id>`

The runtime persists sessions under `${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/sessions/<session_id>/`, including evidence, artifacts, and checkpoint state.

## 9. Practical Boundaries

The current release surface is strong, but it is not magic.

- Codex local, the packaged Codex plugin, the checked-in Codex automation pack, the Codex subagent pack, and the explicit Codex `ssh/devbox` path are supported surfaces over the same runtime, and the runtime now supports both `hermes` and `codex_local` backends.
- The native `codex_local` backend now runs Generator, Verifier, and Reviser as separate Codex role executions over `Tier1LoopRunner` rather than using one opaque backend-summary prompt.
- Native Codex runs now preserve structured per-role response and failure data in the standard transcript artifact and emit a Codex-specific runtime evidence record without claiming Hermes delegated-capability closure.
- The repo ships reviewable Codex automation templates and export helpers, not direct registration into Codex's live automation runtime state.
- The repo ships a reviewable Codex subagent prompt pack for safe multi-agent coordination, not direct control of Codex's internal delegation state and not the runtime backend itself.
- The repo now also ships an explicit Codex-native delegation evaluation report path that records why deeper live Codex delegation stays operator-pack or product-managed rather than becoming a runtime contract today.
- The repo also ships an exportable Codex review/QA prompt kit plus a repo-owned evidence helper for pull-request review and browser-driven docs QA.
- The repo ships an explicit Codex `ssh/devbox` remote-operator bundle, readiness path, native remote execution helper, and a rerunnable remote-bootstrap helper that syncs config plus Codex surface state on the remote machine, but it still does not provision Codex remote sessions itself.
- A separate `openai_native` backend is now planned. If it lands, it should target OpenAI's official API or harness primitives rather than trying to turn deeper Codex product-managed state into a repo-owned backend contract.
- There are still real backend asymmetries:
  - Hermes remains the only backend with a blocked delegated-capability closure plan for real per-subagent route proof and delegated verifier-side Aristotle MCP access.
  - Codex local is stronger on native role execution, transcript granularity, and repo-owned SSH/devbox execution.
  - Aristotle transport is still Hermes-shaped even when `codex_local` is the selected backend.
- Some advanced Hermes-native capabilities still depend on upstream Hermes support.
- Some optional backends depend on local or remote operator setup.
- Live behavior depends on real provider routes and external systems.
- Formal verification is selective and should not be forced onto claims that are better handled analytically or computationally.

These are product boundaries, not reasons to weaken the underlying architecture.

## 10. Intended Use

`deep-gvr` is best suited to technical questions where one or more of the following matter:

- the answer should be challenged, not merely produced
- evidence should survive the run
- computational or formal escalation may be necessary
- honest failure is preferable to confident bluffing

That is the design center: a research-oriented, open, verification-first skill rather than a generic conversational interface.
