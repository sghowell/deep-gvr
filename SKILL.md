# deep-gvr

deep-gvr is a Hermes skill procedure for agentic scientific research with a generator-verifier-reviser loop.

## Current State

The repo now includes a runnable `deep-gvr` command surface in `src/deep_gvr/cli.py`, backed by the Python orchestration helper, append-only evidence logging, checkpoint-based resume, the same Hermes prompt execution path used by live evaluation, and a Hermes-MCP-backed Tier 3 transport path when Aristotle is configured.
Live Hermes prompt execution now defaults to a `compact` prompt profile so benchmark and CLI runs carry less scaffolding by default.

## Intended Commands

- `/deep-gvr <question>` starts a new session
- `/deep-gvr resume <session_id>` resumes a prior session
- `python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml ...` runs the prompt stack against the benchmark corpus and records live artifacts under `eval/results/live/`
- `python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --subset live-expansion ...` runs the representative multi-case live subset used for ongoing harness tuning
- `python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --subset live-expansion --repeat 3 ...` measures whether that representative live subset is stable across repeated sweeps

## Procedure

When the user invokes `/deep-gvr`:

1. Ensure `~/.hermes/deep-gvr/config.yaml` exists. If it does not, create it from the repo defaults.
2. For a new question, run `uv run deep-gvr run "<question>"`.
3. For resume, run `uv run deep-gvr resume <session_id>`.
4. If Tier 3 is expected, run `bash scripts/setup_mcp.sh --install --check` so `~/.hermes/config.yaml` has `mcp_servers.aristotle` and the local environment confirms `ARISTOTLE_API_KEY` plus Hermes MCP readiness.
5. Report the returned session summary, including the session ID, verdict, and evidence/checkpoint paths.
6. If a live run needs debugging rather than throughput, rerun with `--prompt-profile full`.
7. If the command fails because a Hermes role call times out or a backend is unavailable, surface the structured failure clearly instead of inventing a result.

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
- `scripts/setup_mcp.sh --install` is the idempotent operator path for adding `mcp_servers.aristotle` before Tier 3 live runs.
- Cross-model verification is preferred. The effective route is derived from `models.orchestrator`, `models.generator`, `models.verifier`, and `models.reviser` plus the routing probe.
- Live eval now reads the same repo-local runtime config as the CLI when `--config` is provided, so route tuning should happen in one config file instead of through benchmark-only overrides.
- Live eval now also injects the same repo-local domain context files as the CLI, so benchmark runs no longer start from an empty `literature_context`.
- Live Tier 2 mediation now normalizes common verifier noise-model aliases to the canonical Stim value `depolarizing` and clamps live requests to the repo-local safe budget of `shots_per_point <= 100000` and `max_parallel <= 4`.
- The shared QEC domain context now explicitly separates code-capacity, bit-flip, and circuit-level threshold regimes so live depolarizing-threshold answers stay scoped to the right literature.
- Compact live verification now uses a dedicated verifier prompt/path so the adversarial verifier request is materially smaller than the generic compact prompt shape.
- Live CLI/eval now treat concrete role-model pins as explicit top-level route intent and will fall back to the shared live route when Hermes rejects that provider/model path as a route-configuration error.
- If Hermes cannot route models per subagent, fall back to the orchestrator route with prompt and temperature decorrelation, and record that limitation in evidence.
- Hermes CLI does not currently expose a temperature flag, so live evaluation records the intended fallback temperature values while relying on prompt separation only at execution time.
- Hermes-backed live execution supports `compact` and `full` prompt profiles. `compact` is the default runtime path; `full` is the debugging path when prompt scaffolding needs inspection.
- Live generator/verifier/reviser calls now default to a constrained Hermes tool surface when `--toolsets` is omitted, so prompt execution does not inherit the full interactive CLI tool policy by default.
- Live evaluation treats `--command-timeout-seconds` as the base role timeout, applies a higher repo-local floor to the verifier, applies a larger follow-up floor once Tier 2 or Tier 3 evidence is attached, and leaves Tier 3 formal transport on the configured proof timeout.
- Tier 3 transport readiness is separate from subagent MCP inheritance. The verifier still does not assume direct MCP access; the orchestrator checks for `mcp_servers.aristotle` and mediates the proof attempt.
- For live known-incorrect benchmark cases, the evaluation runner now accepts a verified direct refutation as success instead of forcing the generator to produce a false candidate.
- Live case results now expose `strict_verdict_match`, `verdict_accepted`, `tiers_matched_expected`, `accepted_refutation`, and an explicit `outcome`, and repeated eval runs write a `consistency_report.json` so stability is measured structurally instead of from free-form notes.
- For simulation-testable quantitative claims that name concrete distances, error rates, decoders, or threshold behavior without attached `simulation_results`, the live verifier guidance now defaults to requesting Tier 2.

See [docs/system-overview.md](docs/system-overview.md), [docs/contracts-and-artifacts.md](docs/contracts-and-artifacts.md), and the plans in `plans/` before implementing the full orchestrator.
