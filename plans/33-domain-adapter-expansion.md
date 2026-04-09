# 33 Domain Adapter Expansion

## Purpose / Big Picture

Expand Tier 2 from a Stim-centric simulation hook into a broader OSS analysis boundary. This slice proves that `deep-gvr` can route analysis requests through a typed adapter registry across scientific and quantum domains while keeping prompts, schemas, benchmarks, and readiness probes aligned.

## Branch Strategy

Start from `main` and implement this slice on `codex/domain-adapter-expansion`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result, push `main`, confirm CI, and delete the feature branch.

## Commit Plan

- `generalize tier2 analysis contracts`
- `add oss analysis adapter families`
- `document oss analysis portfolio`

## Progress

- [x] Replace the Tier 2 public contract framing with `analysis_spec` and `analysis_results`.
- [x] Implement first-class OSS adapter families for symbolic math, optimization, dynamics, QEC benchmarking, MBQC/graph-state analysis, photonic linear optics, neutral-atom control, topological-QEC design, and ZX rewrite/verification.
- [x] Expand domain context, prompts, probes, and release-surface checks for the broader analysis portfolio.
- [x] Expand deterministic benchmarks and subsets beyond quantum-only cases.

## Surprises & Discoveries

- The main technical challenge was not adapter code but surface consistency: Tier 2 names were embedded across prompts, schemas, tests, release preflight, and benchmark reporting.
- The installed CLI path needed a repo-root-aware adapter loader. A direct top-level import of `adapters.registry` broke `eval/run_eval.py` and package imports until the loader moved behind `tier1.py`.
- Broad OSS family support is best treated as readiness-probed optional capability, not as an assumption that every local environment will have every library installed.

## Decision Log

- Tier 2 is now described as an `analysis` boundary, not a simulation-only boundary.
- Stim/PyMatching remains supported, but only as one `qec_decoder_benchmark` adapter family inside the generalized registry.
- `Graphix`, `Perceval`, `Pulser`, `tqec`, and `PyZX` are in-scope plan-33 adapter families.
- `Qiskit`, `Cirq`, and `PennyLane` remain future interoperability targets, not primary adapter-family names.
- Standalone `FBQC` and `resource_state` adapters are not required completion criteria for this slice; their future support should build on the concrete OSS families shipped here.

## Outcomes & Retrospective

- `src/deep_gvr/contracts.py` now exposes normalized `AnalysisSpec`, `AnalysisResults`, and `AnalysisMeasurement` contracts alongside the legacy QEC-specific Stim data model.
- `src/deep_gvr/tier1.py` now mediates Tier 2 through a generalized analysis request path and persists `iteration_<n>_analysis_spec.json` plus `iteration_<n>_analysis_results.json`.
- `adapters/registry.py` plus the new adapter modules now provide a concrete OSS analysis portfolio:
  - `symbolic_math`
  - `optimization`
  - `dynamics`
  - `qec_decoder_benchmark`
  - `mbqc_graph_state`
  - `photonic_linear_optics`
  - `neutral_atom_control`
  - `topological_qec_design`
  - `zx_rewrite_verification`
- `src/deep_gvr/probes.py` and `src/deep_gvr/release_surface.py` now surface adapter-family readiness explicitly instead of silently assuming those local dependencies exist.
- `eval/known_problems.json` and `src/deep_gvr/evaluation.py` now include a broader deterministic analysis suite with named subsets `core-science`, `photonic-mbqc`, `quantum-oss`, and `analysis-full`.

## Context and Orientation

- Core loop and mediation: `src/deep_gvr/tier1.py`
- Contracts: `src/deep_gvr/contracts.py`
- Adapter registry: `adapters/registry.py`
- Domain context cards: `domain/`
- Prompt surfaces: `prompts/`
- Benchmarks: `eval/known_problems.json`
- Architecture ledger item: `domain-adapter-expansion`

## Plan of Work

1. Generalize Tier 2 contracts and evidence from simulation-specific names to analysis-specific names.
2. Add the OSS scientific and quantum adapter families behind a shared registry.
3. Expand domain context, probes, release checks, and benchmark coverage for the broader portfolio.
4. Retire the architecture gap by updating the ledger and the main docs.

## Concrete Steps

1. Add `AnalysisSpec`, `AnalysisResults`, and `AnalysisMeasurement` contracts plus schemas/templates.
2. Refactor the Tier 1 runner, verifier prompt contracts, and benchmark runner to use `analysis_spec` / `analysis_results`.
3. Implement the adapter modules for SymPy, OR-Tools/SciPy, SciPy/QuTiP, Graphix, Perceval, Pulser, tqec, PyZX, and the generalized QEC benchmark path.
4. Add domain cards for `math`, `optimization`, `dynamics`, `mbqc`, `photonic`, and `neutral_atom`, and make domain loading registry-driven.
5. Add adapter-family readiness probes plus release-preflight reporting.
6. Expand the deterministic benchmark corpus and subsets, then regenerate the committed deterministic baseline.
7. Update docs and the architecture ledger so plan 33 is marked realized.

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Targeted validation:

```bash
uv run python -m unittest tests.test_analysis_adapters tests.test_contracts tests.test_tier1_loop tests.test_evaluation tests.test_probes -v
uv run python eval/run_eval.py --routing-probe fallback --output /tmp/deep-gvr-plan33-baseline.json
```

Acceptance evidence:

- Tier 2 runtime, prompts, artifacts, and evidence all use the generalized analysis contract.
- The new OSS adapter families execute through the shared registry with deterministic unit coverage.
- Domain context, probes, release preflight, and benchmark subsets all recognize the expanded portfolio.
- The architecture ledger no longer treats plan 33 as an open gap.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/domain-adapter-expansion` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Keep adapter additions isolated behind the registry so missing OSS libraries degrade into structured adapter errors instead of import-time crashes.
- Preserve the internal QEC Stim contract only as a backend detail of `qec_decoder_benchmark`, not as the Tier 2 public surface.
- Do not add a new adapter family without the matching schema, benchmark, and readiness-probe updates.

## Interfaces and Dependencies

- Depends on the completed backend-dispatch work from plan 28 and the release-surface work from plan 30.
- Touches adapter contracts, prompts, domain context, benchmarks, release preflight, and capability probes.
- Keeps broad ecosystems such as Qiskit, Cirq, and PennyLane out of the first-wave adapter-family list while leaving them as future interoperability surfaces.
