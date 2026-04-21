# System Overview

`deep-gvr` is a Hermes skill bundle plus a typed Python runtime with supported Codex-local, packaged Codex plugin, Codex automation, Codex subagent, Codex review/QA, and Codex `ssh/devbox` peer surfaces. The runtime manages verification, evidence, and optional deeper analysis.

## Public Surface

- `/deep-gvr <question>`
- `/deep-gvr resume <session_id>`
- `codex exec -C /path/to/deep-gvr "Use the deep-gvr skill to answer: <question>"`
- `uv run python scripts/export_codex_automations.py --output-root /tmp/deep-gvr-codex-automations`
- `uv run python scripts/export_codex_subagents.py --output-root /tmp/deep-gvr-codex-subagents`
- `uv run python scripts/export_codex_review_qa.py --output-root /tmp/deep-gvr-codex-review-qa`
- `uv run deep-gvr run "<question>"`
- `uv run deep-gvr resume <session_id>`
- `uv run python scripts/codex_preflight.py --json`
- `uv run python scripts/codex_preflight.py --operator`
- `uv run python scripts/release_preflight.py --json`
- `uv run python scripts/release_preflight.py --operator --config ~/.hermes/deep-gvr/config.yaml`

Core runtime locations:

- Config: `~/.hermes/deep-gvr/config.yaml`
- Sessions: `~/.hermes/deep-gvr/sessions/<session_id>/`
- Checkpoint: `~/.hermes/deep-gvr/sessions/<session_id>/checkpoint.json`
- Artifacts: `~/.hermes/deep-gvr/sessions/<session_id>/artifacts/`
- Hermes memory target: `~/.hermes/memories/MEMORY.md`

## Core Components

- Orchestrator: coordinates the run, evidence, resume behavior, and user-facing flow
- Generator: proposes a candidate answer
- Verifier: challenges the candidate and decides whether deeper tiers are necessary
- Reviser: fixes concrete flaws rather than freewheeling into a fresh answer
- Tier 2 analysis layer: adapter-driven computational checks
- Tier 3 formal layer: proof-oriented verification through Aristotle or MathCode

## Verification Model

- Tier 1 analytical verification always runs
- Tier 2 is used for executable scientific or mathematical checks
- Tier 3 is used for formalizable claims
- repeated failure can escalate into bounded branching or halt explicitly
- evidence and checkpoints are persisted throughout the run

<figure class="doc-figure">
  <img src="../assets/verification-tiers.svg" alt="Verification tiers diagram" />
  <figcaption>The stack is intentionally selective: every run gets Tier 1, while Tier 2 and Tier 3 are claim-driven escalations.</figcaption>
</figure>

## Tier 2 Analysis Families

The current public analysis surface includes:

- symbolic math
- optimization
- dynamics
- QEC decoder benchmarking
- MBQC graph-state analysis
- photonic linear optics
- neutral-atom control
- topological-QEC design
- ZX rewrite and equivalence checking

## Tier 3 Formal Backends

- Aristotle: MCP-backed proof transport
- MathCode: local CLI-backed proof transport
- OpenGauss: intended backend, not part of the standard release path today

## Operational Defaults

- Hermes delegated orchestration is the shipped execution backend
- Codex local, the packaged Codex plugin, the checked-in Codex automation pack, the Codex subagent pack, and the explicit Codex `ssh/devbox` surface are supported operator surfaces over that same runtime
- the repo also ships a Codex review/QA prompt pack for pull-request review and public-docs visual QA
- file-backed artifacts are the ground truth
- deterministic benchmarks provide a stable regression floor
- live runs expose real provider, backend, and proof-transport behavior
