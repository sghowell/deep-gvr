# Contracts and Artifacts

This document defines the repo-level contract vocabulary shared across prompts, code, schemas, fixtures, and tests.

## Core Contracts

- `DeepGvrConfig`: loop settings, verification tiers, explicit orchestrator plus per-role model routing, evidence storage, and domain defaults
- `BenchmarkCase`: one deterministic release-benchmark case with its expected verdict and expected tier path
- `BenchmarkReport`: recorded benchmark results plus release-readiness metrics
- `CandidateSolution`: generator or reviser output
- `VerificationReport`: verifier output with tiered results
- `SimSpec`: normalized simulation request
- `SimResults`: normalized simulation output
- `FormalVerificationRequest`: orchestrator-mediated Tier 3 request to the formal backend
- `EvidenceRecord`: append-only record for one GVR phase transition, including the effective provider/model path, routing mode, and any fallback temperature
- `SessionCheckpoint`: resume-safe loop state for the last complete phase
- `SessionIndex`: summary view of known sessions
- `CapabilityProbeResult`: result of a readiness probe for a platform assumption

## Artifact Paths

- `schemas/*.json`: canonical JSON Schemas
- `templates/*.json`: sample artifacts used in tests
- `prompts/*.md`: role prompts aligned to the contract names
- `domain/*.md`: concise domain context cards
- `eval/known_problems.json`: deterministic release benchmark corpus
- `eval/results/baseline_results.json`: committed benchmark evidence for the current repo baseline
- `sessions/<session_id>/checkpoint.json`: persisted Tier 1 loop state for resume
- `sessions/<session_id>/artifacts/iteration_<n>_simulation_*.json`: persisted Tier 2 specs and normalized results
- `sessions/<session_id>/artifacts/iteration_<n>_formal_*.json`: persisted Tier 3 requests and returned formal results

## Alignment Rules

- Field names must match across prompts, Python models, schemas, and fixtures.
- Config changes that affect effective model routing must update the routing helper, fixtures, and evidence examples in the same branch.
- Sample artifacts should be realistic enough to support smoke tests and contract review.
- Prompt changes that affect artifacts must update schemas and fixtures in the same branch.
- New public artifacts, including resume state, must have schema, template, and tests in the same branch.
