# Evaluation Harness

The evaluation directory contains both the deterministic readiness benchmark and the live prompt-driven benchmark runner for the current repo implementation.

## Goals

- Catch false-positive verification behavior early
- Exercise tier-routing logic across analytical, empirical, and formalizable claims
- Provide small, stable fixtures for iterative prompt and harness improvement
- Record prompt-driven benchmark evidence separately from the deterministic release floor

## Files

- `known_problems.json`: benchmark corpus with expected verdicts and expected tiers
- `run_eval.py`: deterministic and live benchmark runner
- `results/baseline_results.json`: committed release baseline generated from the runner
- `results/live/<run_id>/report.json`: live benchmark report for one prompt-driven run
- `results/live/<run_id>/cases/<case_id>/`: live per-case artifacts such as candidate output, verification report, transcripts, and case result summary
- `results/live/<run_id>/sessions/`: Tier 1 loop evidence, checkpoint, and mediated Tier 2/Tier 3 artifacts for the live run
- `results/live/<run_id>-repeat/consistency_report.json`: aggregate repeated-run stability report with per-run reports under `runs/run-###/`

## Usage

```bash
uv run python eval/run_eval.py --routing-probe fallback --output eval/results/local_results.json
```

That deterministic mode uses fixture agents instead of live Hermes subagents. It keeps the benchmark repeatable while still exercising the Tier 1 loop, Tier 2 mediation, Tier 3 mediation, checkpointing, and routing evidence behavior.

For live prompt execution, use:

```bash
uv run python eval/run_eval.py --list-subsets
uv run python eval/run_eval.py --mode live --routing-probe fallback --case-id known-correct-surface-threshold
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --case-id known-correct-surface-threshold
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --subset live-expansion --prompt-profile compact
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --subset live-expansion --prompt-profile compact --repeat 3
```

When `--output` is omitted in live mode, the runner writes `report.json` into the timestamped live output directory automatically. Live runs never overwrite `results/baseline_results.json` unless `--allow-baseline-overwrite` is passed explicitly.
When `--repeat` is greater than `1`, the runner writes `consistency_report.json` at the chosen output root and stores each individual run under `runs/run-###/report.json`.

## Live Mode Notes

- Live mode drives the real Tier 1 loop plus Tier 2 and Tier 3 mediation paths.
- Role prompts are loaded from `prompts/` and executed through `hermes chat`.
- Live mode uses the `compact` prompt profile by default to reduce query size; use `--prompt-profile full` when you want the more verbose scaffolding in transcripts for debugging.
- In compact mode, the verifier uses `prompts/verifier_compact.md` plus a tighter payload/contract shape so the live adversarial pass stays smaller than the generic compact prompt path.
- Live mode accepts `--config` and uses the same `models.*` routing settings as `uv run deep-gvr`, while still writing benchmark artifacts to the selected live output root instead of the config's evidence directory.
- When a live config pins concrete role models, the live runner prefers those top-level role routes and falls back to the shared route only when Hermes returns a provider/model route error; the transcript artifact records both attempts.
- Live mode also injects the same domain context loader as `uv run deep-gvr`, so the generator receives the repo-local QEC anchor notes instead of an empty `literature_context`.
- When `--toolsets` is omitted, live generator/verifier/reviser calls use a constrained default Hermes tool surface so they do not inherit the full interactive CLI tool policy by default.
- Live Tier 2 mediation normalizes common verifier aliases such as `uniform_depolarizing` and `iid_depolarizing` to the canonical Stim noise-model string `depolarizing`.
- Live Tier 2 requests are clamped to the repo-local safe budget of `shots_per_point <= 100000` and `max_parallel <= 4`.
- For simulation-testable claims that name concrete distances, error rates, decoders, or threshold behavior and do not already include `simulation_results`, the live verifier guidance now defaults to requesting Tier 2 instead of treating Tier 1 plausibility as enough.
- Before expecting live Tier 3 cases to run through Aristotle, use `bash scripts/setup_mcp.sh --install --check` to activate and verify the local Hermes MCP config.
- When `~/.hermes/config.yaml` defines `mcp_servers.aristotle`, live Tier 3 requests are also dispatched through `hermes chat` plus the configured Aristotle MCP tools.
- `--command-timeout-seconds` sets the base live role timeout. The verifier gets a higher repo-local floor, while Tier 3 formal transport keeps using the configured proof timeout instead of inheriting the shorter live role bound.
- The verifier now gets a larger follow-up timeout floor when Tier 2 or Tier 3 evidence is attached, so the evidence-bearing recheck is not forced through the same shorter budget as the initial audit.
- If compact mode still times out on the generator or verifier, the next operator levers are a higher timeout or a faster configured model route; prompt compaction does not change underlying provider latency.
- Per-case artifacts include `candidate_solution.json`, `verification_report.json`, `role_transcripts.json`, `case_result.json`, and the session evidence/checkpoint files.
- `case_result.json` now records `strict_verdict_match`, `verdict_accepted`, `tiers_matched_expected`, `accepted_refutation`, and an explicit `outcome` classification so operators can separate honest refutations from true verdict/tier failures.
- A failed formalizable live case does not necessarily mean Tier 3 transport failed; generator or verifier timeouts are recorded separately in `live_error.json` and `role_transcripts.json`, while real Tier 3 attempts leave `formal_transport` and `formal_results` artifacts under the session directory.
- When routing is in fallback mode, the harness records prompt separation plus the intended temperature values, but Hermes CLI does not expose a temperature flag. The live report records that limitation in case notes instead of pretending the override was applied.
- The repo-local QEC anchors now explicitly separate the `~10.3%` independent-X/Z code-capacity figure from the `~10.9%` Nishimori-point bit-flip result and steer generic depolarizing-threshold answers toward the circuit-level Fowler/Stephens literature instead of overloaded mixed-regime summaries.
- For known-incorrect live benchmark cases, a verified direct refutation now counts as success. The live runner no longer forces the generator to role-play a false claim just to preserve the deterministic benchmark verdict label.

## Initial Categories

- known-correct claims that should verify
- known-incorrect claims that should fail verification
- simulation-triggering claims that should request Tier 2
- formalizable claims that should request Tier 3 when enabled
