# System Overview

`deep-gvr` is a typed Python runtime with an explicit orchestrator-backend boundary plus Hermes and Codex-facing operator surfaces. Today the runtime supports both `hermes` and `codex_local` backends; Codex local, the packaged Codex plugin, Codex automation, Codex subagent, Codex review/QA, and Codex `ssh/devbox` remain supported surfaces over that same runtime. The native `codex_local` backend now executes Generator, Verifier, and Reviser as separate Codex role calls over the typed loop, and the SSH/devbox path can execute that same backend from a remote machine. A separate `openai_native` backend is now planned, but it is not part of the shipped runtime surface yet.

## Public Surface

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
- `uv run python scripts/codex_preflight.py --json`
- `uv run python scripts/codex_preflight.py --operator`
- `uv run python scripts/codex_preflight.py --ssh-devbox --operator`
- `uv run python scripts/release_preflight.py --json`
- `uv run python scripts/release_preflight.py --operator --config ${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/config.yaml`

Core runtime locations:

- Config: `${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/config.yaml`
- Sessions: `${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/sessions/<session_id>/`
- Checkpoint: `${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/sessions/<session_id>/checkpoint.json`
- Artifacts: `${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/sessions/<session_id>/artifacts/`
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

See [Tier 2 and Tier 3 Support Matrix](tier2-tier3-support-matrix.md) for the
current shipped support boundary, execution-backend support statements, and the
reference probe baseline.

## Tier 3 Formal Backends

- Aristotle: submission/poll/resume lifecycle over Hermes MCP primary transport
  with direct CLI fallback
- MathCode: bounded local CLI-backed proof transport with no shipped
  submission/poll/resume lifecycle
- OpenGauss: intended backend, not part of the standard release path today

See [Tier 2 and Tier 3 Support Matrix](tier2-tier3-support-matrix.md) for the
current Tier 3 transport boundary, lifecycle differences, and reference probe
baseline.

## Operational Defaults

- The runtime selects an explicit orchestrator backend, with Hermes still the default backend in the checked-in config template
- Codex local, the packaged Codex plugin, the checked-in Codex automation pack, the Codex subagent pack, and the explicit Codex `ssh/devbox` surface are supported operator surfaces over that same runtime
- the native `codex_local` backend now drives Generator, Verifier, and Reviser through separate Codex role executions instead of one opaque backend-summary call
- the Codex `ssh/devbox` path now uses the same native `codex_local` backend instead of acting only as a prompt/export bundle
- the repo now ships a rerunnable remote-bootstrap helper that materializes the remote config and Codex surface before the SSH/devbox preflight gate
- the repo also ships a Codex review/QA prompt pack plus a repo-owned evidence helper for pull-request review and public-docs visual QA
- file-backed artifacts are the ground truth
- deterministic benchmarks provide a stable regression floor
- live runs expose real provider, backend, and proof-transport behavior

## Current Backend Gaps

| Area | Hermes backend today | Codex backend today | Current gap |
|---|---|---|---|
| Core orchestrator execution | Delegated Hermes skill wrapper | Native role-separated `codex exec` loop | Hermes does not yet expose the same repo-owned per-role transcript and parsed-response surface |
| Live delegated subagent closure | Intended target, but still blocked in the delegated-capability closure slice | Intentionally stays outside the runtime contract and remains product-managed/operator-pack territory | No backend currently ships repo-owned live delegated subagent closure |
| Aristotle Tier 3 transport | Primary shipped path via Hermes MCP with CLI fallback | Uses the same shared formal layer | `codex_local` still depends on Hermes-shaped Aristotle transport when Aristotle is selected |
| Remote stronger-machine execution | No backend-specific orchestrator remote bootstrap path | Repo-owned SSH/devbox bootstrap and runtime-backed execution helper | Codex has a stronger repo-owned remote execution surface today |
