# 68 Tier 2 Support Completion

## Purpose / Big Picture

Move Tier 2 from "broadly implemented" to "explicitly supportable" across the
shipped analysis families.

The runtime already supports nine Tier 2 adapter families and the benchmark
suite already includes deterministic known-problem cases across that portfolio.
What is still missing is a stronger operator-ready support story: clear backend
support statements per family, sharper install and preflight guidance, and
runtime-level validation that goes beyond isolated adapter unit tests.

## Branch Strategy

Start from `main` on `codex/tier2-support-completion`. Keep this slice separate
from Tier 3 hardening so the changes remain reviewable and the acceptance bar
for Tier 2 stays clear.

## Commit Plan

- `tighten tier2 support contracts`
- `harden tier2 preflight and validation`
- `document tier2 support boundary`

## Progress

- [x] Define an explicit support statement for every shipped Tier 2 family.
- [x] Improve preflight and operator guidance for missing optional dependencies.
- [x] Add stronger runtime-level validation for shipped Tier 2 families.
- [x] Align docs, contracts, and release surfaces with the Tier 2 support
  boundary.

## Surprises & Discoveries

- The repo already has deterministic benchmark coverage across the full Tier 2
  family list, so the biggest gap is not "missing examples." It is the support
  boundary between structural implementation and operator-ready installability.
- Only `qec_decoder_benchmark` currently has explicit non-local execution
  backend support. The other families should be treated as local-only until the
  repo says otherwise.

## Decision Log

- Decision: define completion in terms of explicit support statements and
  runtime-facing validation, not just adapter unit tests.
- Decision: keep local-only families honestly documented as local-only unless
  the repo actually adds broader backend support.

## Outcomes & Retrospective

- This plan exists so the remaining Tier 2 support work is owned by a concrete
  repo slice instead of being left as an implied follow-up from the support
  matrix.
- Tier 2 support statements now live in one code-owned support matrix instead of
  being duplicated loosely across probes, release preflight, evaluation
  subsets, and docs.
- Release preflight now distinguishes unsupported backend selection for the
  configured default family from missing package readiness for that family.
- The evaluation harness now exposes a dedicated `tier2-support` subset so
  runtime-facing Tier 2 coverage is explicit rather than implicit inside the
  larger benchmark suite.

## Non-Goals

- Do not require every Tier 2 family to support every execution backend.
- Do not reopen Codex or Hermes delegated-subagent work here.
- Do not treat OpenGauss or other Tier 3 concerns as part of this slice.

## Context and Orientation

- Tier 2 runtime:
  - `src/deep_gvr/tier1.py`
  - `adapters/registry.py`
- Tier 2 readiness and release gating:
  - `src/deep_gvr/probes.py`
  - `src/deep_gvr/release_surface.py`
  - `scripts/run_capability_probes.py`
  - `scripts/release_preflight.py`
- Deterministic coverage:
  - `tests/test_analysis_adapters.py`
  - `eval/known_problems.json`

## Plan of Work

1. Record a precise support statement for each shipped Tier 2 family, including
   whether it is local-only or also supports remote execution backends.
2. Tighten operator install and preflight guidance so missing optional
   dependencies are surfaced clearly and early.
3. Add runtime-level validation coverage that proves the shipped Tier 2 surface
   works through the actual loop and evaluation harness, not only through
   isolated adapter tests.
4. Update the public and operator docs so the Tier 2 support boundary is clear.

## Concrete Steps

1. Make the backend-support statement explicit for each family:
   - `qec_decoder_benchmark`: `local`, `modal`, `ssh`
   - every other shipped family: `local` unless expanded deliberately
2. Improve readiness and release gating:
   - ensure capability probes and release preflight explain exactly which
     packages are missing
   - ensure the default configured Tier 2 family is treated more strictly than
     optional families
3. Extend validation:
   - add or tighten runtime-facing tests and benchmark subsets that execute the
     shipped Tier 2 families through the loop or evaluation harness
   - make the claimed backend support visible in those tests
4. Update docs:
   - keep the support matrix, quickstart, and release workflow aligned with the
     actual shipped Tier 2 support boundary

## Validation and Acceptance

This slice is complete when:

- every shipped Tier 2 family has an explicit support statement
- preflight and release surfaces report missing optional dependencies precisely
- runtime-level validation exists for the shipped Tier 2 families
- the docs describe the Tier 2 support boundary honestly and clearly

Required validation:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Add narrower Tier 2-specific validation as needed in the branch.

## Merge, Push, and Cleanup

- Stage and commit the Tier 2 work in coherent chunks.
- Validate before merge.
- Merge locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm CI and Docs are green.
- Delete the feature branch when it is no longer needed.

## Idempotence and Recovery

- Keep the Tier 2 support statement truthful to the runtime. Do not broaden the
  claimed support surface in docs without matching validation and operator
  guidance.
- If a family remains local-only after this slice, keep that limitation explicit
  rather than implying broader backend parity.

## Interfaces and Dependencies

- Depends on the existing adapter registry, known-problem cases, and release
  preflight surfaces.
- Depends on keeping the support boundary honest: local-only families should
  stay documented as local-only unless the repo actually adds broader execution
  support.
