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

## Usage

```bash
uv run python eval/run_eval.py --routing-probe fallback --output eval/results/local_results.json
```

That deterministic mode uses fixture agents instead of live Hermes subagents. It keeps the benchmark repeatable while still exercising the Tier 1 loop, Tier 2 mediation, Tier 3 mediation, checkpointing, and routing evidence behavior.

For live prompt execution, use:

```bash
uv run python eval/run_eval.py --mode live --routing-probe fallback --case-id known-correct-surface-threshold
```

When `--output` is omitted in live mode, the runner writes `report.json` into the timestamped live output directory automatically. Live runs never overwrite `results/baseline_results.json` unless `--allow-baseline-overwrite` is passed explicitly.

## Live Mode Notes

- Live mode drives the real Tier 1 loop plus Tier 2 and Tier 3 mediation paths.
- Role prompts are loaded from `prompts/` and executed through `hermes chat`.
- Live mode uses the `compact` prompt profile by default to reduce query size; use `--prompt-profile full` when you want the more verbose scaffolding in transcripts for debugging.
- Before expecting live Tier 3 cases to run through Aristotle, use `bash scripts/setup_mcp.sh --install --check` to activate and verify the local Hermes MCP config.
- When `~/.hermes/config.yaml` defines `mcp_servers.aristotle`, live Tier 3 requests are also dispatched through `hermes chat` plus the configured Aristotle MCP tools.
- Each live role call uses a bounded subprocess timeout, configurable with `--command-timeout-seconds`, so stalled model calls fail into recorded error artifacts instead of hanging the whole run.
- If compact mode still times out on the generator or verifier, the next operator levers are a higher timeout or a faster configured model route; prompt compaction does not change underlying provider latency.
- Per-case artifacts include `candidate_solution.json`, `verification_report.json`, `role_transcripts.json`, `case_result.json`, and the session evidence/checkpoint files.
- A failed formalizable live case does not necessarily mean Tier 3 transport failed; generator or verifier timeouts are recorded separately in `live_error.json` and `role_transcripts.json`, while real Tier 3 attempts leave `formal_transport` and `formal_results` artifacts under the session directory.
- When routing is in fallback mode, the harness records prompt separation plus the intended temperature values, but Hermes CLI does not expose a temperature flag. The live report records that limitation in case notes instead of pretending the override was applied.

## Initial Categories

- known-correct claims that should verify
- known-incorrect claims that should fail verification
- simulation-triggering claims that should request Tier 2
- formalizable claims that should request Tier 3 when enabled
