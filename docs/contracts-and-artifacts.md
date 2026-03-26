# Contracts and Artifacts

This document defines the repo-level contract vocabulary shared across prompts, code, schemas, fixtures, and tests.

## Core Contracts

- `DeepGvrConfig`: loop settings, verification tiers, model routing, evidence storage, and domain defaults
- `CandidateSolution`: generator or reviser output
- `VerificationReport`: verifier output with tiered results
- `SimSpec`: normalized simulation request
- `SimResults`: normalized simulation output
- `EvidenceRecord`: append-only record for one GVR phase transition
- `SessionIndex`: summary view of known sessions
- `CapabilityProbeResult`: result of a readiness probe for a platform assumption

## Artifact Paths

- `schemas/*.json`: canonical JSON Schemas
- `templates/*.json`: sample artifacts used in tests
- `prompts/*.md`: role prompts aligned to the contract names
- `domain/*.md`: concise domain context cards

## Alignment Rules

- Field names must match across prompts, Python models, schemas, and fixtures.
- Sample artifacts should be realistic enough to support smoke tests and contract review.
- Prompt changes that affect artifacts must update schemas and fixtures in the same branch.
