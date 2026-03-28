# System Overview

`deep-gvr` is a Hermes skill bundle plus supporting Python utilities.

## Public Surface

- `/deep-gvr <question>` starts a session
- `/deep-gvr resume <session_id>` resumes a session
- `uv run deep-gvr run "<question>"` launches one Hermes session preloaded with the installed `deep-gvr` skill
- `uv run deep-gvr resume <session_id>` resumes a prior session through the same delegated runtime wrapper
- Config path: `~/.hermes/deep-gvr/config.yaml`
- Evidence path: `~/.hermes/deep-gvr/sessions/<session_id>/`
- Checkpoint path: `~/.hermes/deep-gvr/sessions/<session_id>/checkpoint.json`

## Core Components

- Orchestrator procedure in `SKILL.md`
- Delegated command runtime in `src/deep_gvr/cli.py` and `src/deep_gvr/orchestrator.py`
- Role prompts in `prompts/`
- Typed contracts and helper code in `src/deep_gvr/`
- Tier 1 session runner and persistence helpers in `src/deep_gvr/tier1.py`
- Adapters in `adapters/`
- Schemas in `schemas/`
- Fixtures in `templates/`
- Deterministic and live prompt-harness benchmark runner in `eval/run_eval.py`
- Capability probes and repo checks in `scripts/`

## Verification Model

- Tier 1 analytical verification always runs
- Tier 2 empirical verification is triggered by quantitative claims
- Tier 3 formal verification is triggered by formalizable claims
- Any failed applicable tier is a failed candidate
- Unavailable optional tiers must produce explicit caveats or `CANNOT_VERIFY`
- The local Tier 2 baseline uses the Stim adapter with PyMatching decoding
- The Tier 3 baseline is orchestrator-mediated Aristotle routing through Hermes MCP when `mcp_servers.aristotle` is configured, with structured unavailable/timeout results otherwise

## Early Defaults

- No Hermes fork
- Python 3.12 and `uv`
- Sequential GVR loop first
- Resume from the last complete checkpoint instead of replaying partial phases
- Cross-model verification preferred, with prompt/temperature decorrelation as the fallback
- Effective routing is derived deterministically from config plus probe state and recorded in evidence artifacts
- Release readiness is tracked with a deterministic benchmark suite and a committed baseline report
- Prompt quality and mediation behavior can be exercised with a separate live benchmark mode that records timestamped run artifacts
- The shipped CLI/skill path now uses Hermes delegated orchestration, while the benchmark runner keeps the explicit prompt-role harness for isolated evaluation
- The live benchmark runner supports named subsets such as `live-expansion` for representative multi-case sweeps plus `live-analytical-breadth`, `live-escalation-breadth`, and `live-full` for broader coverage
- The live benchmark runner also supports repeated subset sweeps with a top-level `consistency_report.json` plus per-run reports under `runs/run-###/`
- The current representative stability gate is a repeated `live-expansion` sweep, and plan 21 recorded a clean `2/2` pass on that subset
- Live benchmark runs share the same repo-local domain-context loader as the CLI
- The shared QEC domain-context loader now encodes threshold-regime and citation-scope guardrails for live depolarizing-threshold answers
- Live Hermes prompt execution defaults to a compact prompt profile, with a full profile reserved for debugging prompt behavior
- Compact live verification uses a dedicated verifier prompt and tighter payload shape to reduce verifier-request bulk on the real Hermes route
- Literature-grounded threshold explanations and pure asymptotic-counting claims now stay on Tier 1 by default unless the candidate adds a genuinely new empirical or formal obligation
- The live benchmark harness can prefer explicit top-level role routes from config and fall back to the shared live route when a provider/model path is invalid
- A non-default provider with an empty model now also counts as explicit top-level live route intent, so repo-local provider defaults such as `openrouter` are exercised in live runs
- Live benchmark generator/verifier/reviser calls default to a constrained Hermes tool surface instead of inheriting the full interactive CLI tool policy
- The live role timeout is role-aware: verifier gets a higher floor, evidence-bearing verifier rechecks get a larger follow-up floor, and Tier 3 transport keeps its own proof timeout
- Live Tier 2 mediation normalizes common verifier aliases to the canonical Stim `depolarizing` noise-model string and clamps live requests to a safe execution budget
- Live benchmark case reports now separate `direct_match`, `accepted_refutation`, `tier_mismatch`, `verdict_mismatch`, and `execution_error` outcomes instead of burying those distinctions in notes
- For simulation-testable quantitative claims that name concrete distances, error rates, decoders, or threshold behavior without `simulation_results`, the live verifier guidance now defaults to Tier 2 rather than letting Tier 1 plausibility settle the case
- Live benchmark scoring accepts a verified direct refutation as success for known-incorrect cases
- Live benchmark scoring now also accepts simulation-backed direct refutations when they clearly reject the benchmark claim with the expected tiers
- Known-incorrect accepted-refutation scoring now recognizes conservative explicit 5% threshold refutations framed in sub-1% or `~0.6-0.8%` literature terms
- Compact theorem/asymptotic proof claims now stay on the Tier 3 path, and failed Tier 3 proof results force `CANNOT_VERIFY` on the core theorem claim
- Plain-text provider auth/401 failures from Hermes are now treated as live route configuration errors instead of JSON parse failures
- Plan 23 narrowed the remaining analytical-breadth instability to an external Hermes provider-auth failure on this machine, rather than a repo-local tier-routing or prompt-discipline bug
- Local, Modal, and SSH backends represented from the start through the adapter interface
