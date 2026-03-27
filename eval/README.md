# Evaluation Harness

The evaluation directory contains the deterministic readiness benchmark and the recorded baseline results for the current repo implementation.

## Goals

- Catch false-positive verification behavior early
- Exercise tier-routing logic across analytical, empirical, and formalizable claims
- Provide small, stable fixtures for iterative prompt and harness improvement

## Files

- `known_problems.json`: benchmark corpus with expected verdicts and expected tiers
- `run_eval.py`: deterministic benchmark runner for the current repo baseline
- `results/baseline_results.json`: committed release baseline generated from the runner

## Usage

```bash
uv run python eval/run_eval.py --routing-probe fallback --output eval/results/local_results.json
```

The current runner uses fixture agents instead of live Hermes subagents. That keeps the benchmark repeatable while still exercising the Tier 1 loop, Tier 2 mediation, Tier 3 mediation, checkpointing, and routing evidence behavior.

The next implementation slice is tracked in [plans/08-live-eval.md](../plans/08-live-eval.md). That plan covers adding a live prompt-driven evaluation mode while preserving the deterministic baseline as the CI-safe release floor.

## Initial Categories

- known-correct claims that should verify
- known-incorrect claims that should fail verification
- simulation-triggering claims that should request Tier 2
- formalizable claims that should request Tier 3 when enabled
