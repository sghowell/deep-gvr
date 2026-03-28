# deep-gvr

deep-gvr is a Hermes skill procedure for agentic scientific research with a generator-verifier-reviser loop.

## Current State

The repo now includes a runnable `deep-gvr` command surface in `src/deep_gvr/cli.py`, backed by the delegated Hermes orchestrator wrapper in `src/deep_gvr/orchestrator.py`, append-only evidence logging, checkpoint-based resume, and a Hermes-MCP-backed Tier 3 transport path when Aristotle is configured.
Live Hermes prompt execution now defaults to a `compact` prompt profile so benchmark and CLI runs carry less scaffolding by default.
Current target-state gaps are tracked in [docs/architecture-status.md](docs/architecture-status.md); the temporary runtime substitutions below each point to a retirement slice.

## Temporary Architecture Gaps

- `subagent-capability-closure`: per-subagent routing and verifier-direct MCP are still not supported runtime capabilities. Retirement slice: [plans/26-subagent-capability-closure.md](plans/26-subagent-capability-closure.md)
- `formal-proof-lifecycle`: Tier 3 still ends at one bounded proof attempt instead of a full submission and polling lifecycle. Retirement slice: [plans/27-formal-proof-lifecycle.md](plans/27-formal-proof-lifecycle.md)
- `remote-backend-completion`: Modal and SSH are still incomplete Tier 2 execution paths. Retirement slice: [plans/28-remote-backend-completion.md](plans/28-remote-backend-completion.md)
- `evidence-system-completion`: Hermes memory persistence and Parallax-compatible evidence outputs are still missing. Retirement slice: [plans/29-evidence-system-completion.md](plans/29-evidence-system-completion.md)

## Intended Commands

- `/deep-gvr <question>` starts a new session
- `/deep-gvr resume <session_id>` resumes a prior session
- `python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml ...` runs the prompt stack against the benchmark corpus and records live artifacts under `eval/results/live/`
- `python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --subset live-expansion ...` runs the representative multi-case live subset used for ongoing harness tuning
- `python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --subset live-expansion --repeat 2 ...` is the current representative stability gate for the live benchmark subset
- `python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --subset live-analytical-breadth ...` runs the broader Tier 1 coverage sweep
- `python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --subset live-escalation-breadth --command-timeout-seconds 120 ...` runs the broader Tier 2 and Tier 3 coverage sweep

## Procedure

When the user invokes `/deep-gvr`:

1. Ensure `~/.hermes/deep-gvr/config.yaml` exists. If it does not, create it from the repo defaults.
2. Read the runtime request from the parent message. The external wrapper passes a JSON payload with `command`, `session_id`, `question` or resume target, `config_path`, `prompt_root`, `prompt_profile`, and `routing_probe`.
3. Execute Generator, Verifier, Reviser, and any Simulator work through Hermes `delegate_task`. Do not answer the research question directly from the parent context when a delegated role should handle it.
4. Do not call `uv run deep-gvr run` or `uv run deep-gvr resume` from inside this skill. Those commands are the external wrapper that invokes this delegated orchestrator.
5. If Tier 3 is expected, run `bash scripts/setup_mcp.sh --install --check` so `~/.hermes/config.yaml` has `mcp_servers.aristotle` and the local environment confirms `ARISTOTLE_API_KEY` plus Hermes MCP readiness.
6. Persist or update the session evidence, checkpoint, and artifacts under the configured evidence directory.
7. Return only the structured JSON session summary requested by the wrapper, including the session ID, verdict, and evidence/checkpoint paths.
8. If a run needs debugging rather than throughput, prefer the `full` prompt profile from the runtime request.
9. If the delegated run cannot complete because a role call times out, a backend is unavailable, or a provider route fails, surface the structured failure clearly instead of inventing a result.

## Required Inputs

- research question
- active config at `~/.hermes/deep-gvr/config.yaml`
- prompt files in `prompts/`
- domain context from `domain/`

## Artifacts

- evidence log: `~/.hermes/deep-gvr/sessions/<session_id>.jsonl`
- session metadata: `~/.hermes/deep-gvr/sessions/index.json`
- session checkpoint: `~/.hermes/deep-gvr/sessions/<session_id>/checkpoint.json`
- artifacts: `~/.hermes/deep-gvr/sessions/<session_id>/artifacts/`

## Implementation Notes

- Tier 1 analytical verification is always required.
- The verifier input must remain isolated to the candidate artifact plus iteration metadata.
- Resume continues from the last complete phase recorded in `checkpoint.json`.
- Tier 2 empirical verification is claim-driven through the simulator adapter boundary.
- The orchestrator mediates Tier 2 as verifier -> simulator adapter -> verifier, persisting both the spec and normalized results under the session artifacts directory.
- Tier 3 formal verification is claim-driven and degrades gracefully when unavailable.
- The orchestrator mediates Tier 3 as verifier -> Hermes CLI -> configured Aristotle MCP tools -> verifier, persisting the formal request, transport trace, and returned results under the session artifacts directory.
- The repo-local `uv run deep-gvr ...` wrapper now opens one Hermes session preloaded with this skill; the live benchmark runner in `src/deep_gvr/evaluation.py` remains the explicit prompt-role harness.
- `scripts/setup_mcp.sh --install` is the idempotent operator path for adding `mcp_servers.aristotle` before Tier 3 live runs.
- Cross-model verification is preferred. The effective route is derived from `models.orchestrator`, `models.generator`, `models.verifier`, and `models.reviser` plus the routing probe.
- Live eval now reads the same repo-local runtime config as the delegated CLI wrapper when `--config` is provided, so route tuning should happen in one config file instead of through benchmark-only overrides.
- The live eval prompt harness still treats a non-default provider selection as explicit top-level route intent even when the model field is empty, so repo-local provider defaults such as `openrouter` are actually exercised there.
- Live eval now also injects the same repo-local domain context files as the CLI, so benchmark runs no longer start from an empty `literature_context`.
- Live Tier 2 mediation now normalizes common verifier noise-model aliases to the canonical Stim value `depolarizing` and clamps live requests to the repo-local safe budget of `shots_per_point <= 100000` and `max_parallel <= 4`.
- The shared QEC domain context now explicitly separates code-capacity, bit-flip, and circuit-level threshold regimes so live depolarizing-threshold answers stay scoped to the right literature.
- Compact live verification now uses a dedicated verifier prompt/path so the adversarial verifier request is materially smaller than the generic compact prompt shape.
- Literature-grounded threshold explanations and pure asymptotic-counting claims now stay on Tier 1 by default unless the candidate adds a genuinely new empirical or formal obligation.
- The live eval prompt harness now treats concrete role-model pins as explicit top-level route intent and will fall back to the shared live route when Hermes rejects that provider/model path as a route-configuration error.
- Plain-text provider auth/401 failures from Hermes are now treated as live route configuration errors instead of bubbling up as JSON parse failures.
- If Hermes cannot yet route models per subagent, treat the current route sharing as a temporary gap and record it in evidence. Retirement slice: [plans/26-subagent-capability-closure.md](plans/26-subagent-capability-closure.md)
- Hermes CLI does not currently expose a temperature flag, so live evaluation records the intended fallback temperature values while relying on prompt separation only at execution time.
- Hermes-backed live execution supports `compact` and `full` prompt profiles. `compact` is the default runtime path; `full` is the debugging path when prompt scaffolding needs inspection.
- Live generator/verifier/reviser calls now default to a constrained Hermes tool surface when `--toolsets` is omitted, so prompt execution does not inherit the full interactive CLI tool policy by default.
- Live evaluation treats `--command-timeout-seconds` as the base role timeout, applies a higher repo-local floor to the verifier, applies a larger follow-up floor once Tier 2 or Tier 3 evidence is attached, and leaves Tier 3 formal transport on the configured proof timeout.
- Tier 3 transport readiness is separate from subagent MCP inheritance. The current orchestrator-mediated proof path is a temporary gap rather than the end state. Retirement slices: [plans/26-subagent-capability-closure.md](plans/26-subagent-capability-closure.md) and [plans/27-formal-proof-lifecycle.md](plans/27-formal-proof-lifecycle.md)
- For live known-incorrect benchmark cases, the evaluation runner now accepts a verified direct refutation as success instead of forcing the generator to produce a false candidate.
- The same accepted-refutation scoring now also covers simulation-backed direct refutations when the live run clearly disproves the benchmark claim.
- The accepted-refutation scoring now also recognizes conservative explicit refutations of the 5% circuit-level threshold claim when they clearly reject the claim and ground it in a sub-1% or `~0.6-0.8%` literature range.
- Live case results now expose `strict_verdict_match`, `verdict_accepted`, `tiers_matched_expected`, `accepted_refutation`, and an explicit `outcome`, and repeated eval runs write a `consistency_report.json` so stability is measured structurally instead of from free-form notes.
- For simulation-testable quantitative claims that name concrete distances, error rates, decoders, or threshold behavior without attached `simulation_results`, the live verifier guidance now defaults to requesting Tier 2.
- For compact theorem or asymptotic proof claims, the live prompts now avoid unnecessary Tier 2 escalation and force `CANNOT_VERIFY` when the core theorem only has failed Tier 3 proof results.
- The current remaining blocker for repeated `live-analytical-breadth` on this machine is operational, not repo-local: Hermes is rejecting the active `nous/claude-opus-4-6` provider path with HTTP 401 during generator calls. Retirement slice for the remaining delegated-capability closure: [plans/26-subagent-capability-closure.md](plans/26-subagent-capability-closure.md)

See [docs/system-overview.md](docs/system-overview.md), [docs/contracts-and-artifacts.md](docs/contracts-and-artifacts.md), and the plans in `plans/` before implementing the full orchestrator.
