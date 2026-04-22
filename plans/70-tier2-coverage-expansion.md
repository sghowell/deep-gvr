# 70 Tier 2 Coverage Expansion

## Purpose / Big Picture

Expand Tier 2 from an honest support boundary into materially broader operator
coverage across the shipped analysis families.

Plan 68 made the support contract explicit. It did not make Tier 2 broadly
ready on real machines. The runtime already ships nine Tier 2 adapter
families, deterministic benchmark cases for all nine, and explicit backend
support statements. What is still missing is broader real execution coverage:
default installability for more than the current `1/9` reference-environment
ready count, stronger repeated runtime validation across the shipped families,
and explicit backend-support decisions for any family that should go beyond
`local`.

The user-visible outcome of this slice is that Tier 2 should move closer to
"actually usable across the shipped portfolio" instead of only "accurately
scoped and honestly documented."

## Branch Strategy

Start from `main` on `codex/tier2-coverage-expansion`. Merge back into `main`
locally with a fast-forward only after branch validation passes, then validate
the merged result again, push `main`, confirm CI and Docs, and delete the
feature branch when it is no longer needed.

## Commit Plan

- `plan tier2 coverage expansion`
- `broaden tier2 install and validation`
- `document tier2 expanded support`

## Progress

- [x] Add this plan and index it from `plans/README.md`.
- [ ] Increase Tier 2 operator-ready family coverage materially beyond the
  current `1/9` reference-environment baseline.
- [ ] Strengthen runtime-facing validation across the shipped Tier 2 families.
- [ ] Decide explicitly whether any families beyond
  `qec_decoder_benchmark` should gain non-local backend support.
- [ ] Align docs, probes, and release surfaces with the broader Tier 2 support
  reality.

## Surprises & Discoveries

- The repo is not short on Tier 2 runtime code. It already ships nine adapter
  families and deterministic benchmark cases across the whole portfolio.
- The current Tier 2 gap is operational rather than architectural: installable
  packages, repeated runtime proof, and explicit backend-support breadth.
- Only `qec_decoder_benchmark` currently ships `local` / `modal` / `ssh`
  execution-backend support. Broadening that support for other families should
  be a deliberate decision, not an accidental side effect.

## Decision Log

- Decision: define Tier 2 expansion in terms of real operator coverage, not
  just more support-matrix detail.
- Decision: do not assume every Tier 2 family should support every execution
  backend.
- Decision: if a support claim is shared across `hermes` and `codex_local`,
  backend-parity validation should be added rather than inferred.

## Outcomes & Retrospective

- This plan exists so the remaining "make Tier 2 actually broad and usable"
  work is owned explicitly in-repo instead of being left implied by the support
  matrix.

## Context and Orientation

- Tier 2 support contract and probes:
  - `src/deep_gvr/tier2_support.py`
  - `src/deep_gvr/probes.py`
  - `src/deep_gvr/release_surface.py`
- Tier 2 runtime and adapter registry:
  - `src/deep_gvr/tier1.py`
  - `adapters/registry.py`
- Deterministic and runtime-facing validation:
  - `src/deep_gvr/evaluation.py`
  - `eval/known_problems.json`
  - `tests/test_analysis_adapters.py`
  - `tests/test_evaluation.py`
  - `tests/test_release_scripts.py`
- Existing Tier 2 support-boundary slice:
  - `plans/68-tier2-support-completion.md`

## Plan of Work

1. Raise the practical Tier 2 ready-family count through better installability
   and operator guidance.
2. Add stronger repeated runtime validation across the shipped Tier 2 families.
3. Decide deliberately which families, if any, should gain non-local backend
   support beyond `qec_decoder_benchmark`.
4. Keep probes, release preflight, docs, and backend-parity claims aligned
   with the expanded support reality.

## Concrete Steps

1. Improve installability:
   - add repo-owned setup guidance or dependency surfaces that make more Tier 2
     families ready by default on a fresh operator machine
   - keep per-family missing-package reporting precise
2. Strengthen validation:
   - add repeated runtime-facing validation for all shipped Tier 2 families
   - ensure the `tier2-support` subset remains truthful to the broadened
     support surface
3. Revisit backend support breadth:
   - decide whether any families beyond `qec_decoder_benchmark` should support
     `modal` or `ssh`
   - if the answer is no, document and validate that explicitly
   - if the answer is yes, add the runtime, preflight, and benchmark coverage
     in the same slice
4. Align shared-backend truth:
   - where the same Tier 2 capability is claimed under both `hermes` and
     `codex_local`, add backend-matrix validation instead of assuming parity
5. Update docs:
   - keep `docs/tier2-tier3-support-matrix.md`, `docs/release-workflow.md`,
     `docs/quickstart.md`, and `docs/architecture-status.md` aligned with the
     actual expanded Tier 2 surface

## Validation and Acceptance

This slice is complete when:

- the reference-environment Tier 2 ready-family count is materially higher than
  `1/9`
- each shipped Tier 2 family has stronger runtime-facing validation, not only
  adapter unit tests
- backend-support breadth is explicit and validated for every family
- docs, probes, and release preflight all describe the broadened Tier 2
  support surface honestly

Required validation:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py --json
uv run python -m unittest discover -s tests -v
uv run python -m unittest tests.test_analysis_adapters tests.test_evaluation tests.test_release_scripts -v
uv run python eval/run_eval.py --subset tier2-support --output /tmp/deep-gvr-tier2-coverage-expansion.json
```

Add narrower backend-specific Tier 2 validation as needed in the branch.

## Merge, Push, and Cleanup

- Stage and commit the Tier 2 expansion work in coherent chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/tier2-coverage-expansion` into `main` locally only
  after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm CI and Docs are green.
- Delete the feature branch when it is no longer needed.

## Idempotence and Recovery

- Keep the Tier 2 support contract truthful. Do not broaden claims in docs or
  probes without matching runtime and validation support.
- If a family remains `local` only, keep that limitation explicit instead of
  implying broader backend parity.
- If installability remains difficult for a family, capture the exact blocker
  rather than silently weakening the completion bar.

## Interfaces and Dependencies

- Depends on the existing Tier 2 support matrix and release-preflight truth
  from `plans/68-tier2-support-completion.md`.
- Depends on the shipped adapter families and deterministic benchmark cases
  already recorded in the repo.
- Feeds into the later Codex-versus-Hermes backend parity work by making shared
  Tier 2 claims explicit and testable.
