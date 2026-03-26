# Evaluation Harness

The evaluation directory seeds the benchmark set for readiness and early implementation.

## Goals

- Catch false-positive verification behavior early
- Exercise tier-routing logic across analytical, empirical, and formalizable claims
- Provide small, stable fixtures for iterative prompt and harness improvement

## Initial Categories

- known-correct claims that should verify
- known-incorrect claims that should fail verification
- simulation-triggering claims that should request Tier 2
- formalizable claims that should request Tier 3 when enabled
