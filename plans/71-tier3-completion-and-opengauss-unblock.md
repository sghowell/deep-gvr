# 71 Tier 3 Completion and OpenGauss Unblock

## Purpose / Big Picture

Close the remaining Tier 3 completion gap by combining shipped-backend
hardening with a current, evidence-backed OpenGauss unblock attempt.

Plan 69 was necessary but not sufficient for the stronger completion bar. It
hardened Aristotle and MathCode, but Tier 3 was not fully addressed until the
OpenGauss architecture target was revisited with current evidence and either:

- integrated honestly into the runtime, or
- reduced to a precise external blocker with no remaining repo-owned ambiguity

The user-visible outcome of this slice is that Tier 3 is no longer in the
ambiguous state where the shipped backends are improving while the OpenGauss
target remains only loosely separated in chat history.

## Branch Strategy

Start from `main` on `codex/tier3-completion-and-opengauss-unblock`. Merge back
into `main` locally with a fast-forward only after branch validation passes,
then validate the merged result again, push `main`, confirm CI and Docs, and
delete the feature branch when it is no longer needed.

## Commit Plan

- `plan tier3 completion and opengauss unblock`
- `harden tier3 shipped backends`
- `recheck opengauss unblock state`

## Progress

- [x] Add this plan and index it from `plans/README.md`.
- [x] Execute the shipped-backend hardening from
  `plans/69-tier3-shipped-backends-hardening.md`.
- [x] Re-run a current OpenGauss unblock attempt and record the exact failure
  mode or integration outcome.
- [x] Decide whether OpenGauss can advance repo-side and record the shipped
  bounded local CLI outcome.
- [x] Align Tier 3 docs, probes, and architecture status with the resulting
  full Tier 3 state.

## Surprises & Discoveries

- Tier 3 was not fully addressed while Aristotle and MathCode were the only
  shipped backends. The architecture target also included OpenGauss, and plan
  31 has now realized it as a shipped bounded local CLI backend.
- Aristotle, MathCode, and OpenGauss differ structurally: Aristotle has a real
  submission/poll/resume lifecycle while MathCode and OpenGauss are bounded
  local CLI paths.
- The current OpenGauss ambiguity was narrower than the older docs claimed:
  the installed runtime and published Morph targets are healthy again, while
  the raw checkout launcher can still fail separately because its checkout-local
  Python dependencies are not bootstrapped.

## Decision Log

- Decision: treat full Tier 3 completion as a two-part program:
  shipped-backend hardening plus an explicit OpenGauss unblock decision.
- Decision: include OpenGauss in the shipped Tier 3 path only as the bounded
  local CLI backend implemented by plan 31, with readiness gated on an installed
  `gauss` runtime and `~/.gauss/config.yaml`.
- Decision: now that plan 31 is complete, treat OpenGauss as a realized Tier 3
  baseline while keeping raw-checkout diagnostics separate from installed
  runtime readiness.

## Outcomes & Retrospective

- This plan exists so Tier 3 completion is owned as a concrete repo program
  instead of being split between a hardening plan and an older blocked plan
  with no explicit reconnecting step.
- The reconnecting step is now complete. OpenGauss advanced repo-side through
  plan 31: the installed runtime is healthy, the published Morph targets
  resolve, and deep-gvr now ships bounded local OpenGauss CLI transport with
  diagnostics and tier3-support benchmark coverage.

## Context and Orientation

- Tier 3 runtime:
  - `src/deep_gvr/formal.py`
  - `src/deep_gvr/tier1.py`
- Tier 3 probes and release surfaces:
  - `src/deep_gvr/probes.py`
  - `src/deep_gvr/release_surface.py`
  - `scripts/run_capability_probes.py`
  - `scripts/diagnose_opengauss.py`
- Current docs and matrix:
  - `docs/tier2-tier3-support-matrix.md`
  - `docs/system-overview.md`
  - `docs/deep-gvr-architecture.md`
  - `docs/architecture-status.md`
- Existing plans:
  - `plans/69-tier3-shipped-backends-hardening.md`
  - `plans/31-opengauss-formal-backend.md`
  - `plans/37-opengauss-unblock-diagnostics.md`

## Plan of Work

1. Harden Aristotle, MathCode, and OpenGauss until the shipped Tier 3 path is
   repeatedly validated and operator-solid.
2. Re-run the OpenGauss unblock sequence with current upstream state and local
   diagnostics.
3. Decide whether OpenGauss can advance into repo-owned integration work.
4. Make the full Tier 3 state explicit in docs, probes, and the architecture
   ledger.

## Concrete Steps

1. Execute `plans/69-tier3-shipped-backends-hardening.md`:
   - strengthen Aristotle submission/poll/resume and CLI-fallback validation
   - strengthen MathCode local CLI, timeout, output-parsing, and artifact truth
   - make the lifecycle difference between Aristotle and local CLI backends
     explicit
2. Re-run OpenGauss diagnostics and unblock checks:
   - run `uv run python scripts/diagnose_opengauss.py --json`
   - recheck the current upstream installer target and local `gauss` runtime
   - capture exact failure output and whether the blocker is still upstream
     packaging, local prerequisites, or repo-owned code
3. When OpenGauss became runnable:
   - complete the backend-selection, transport, docs, and benchmark work from
     `plans/31-opengauss-formal-backend.md`
4. After OpenGauss advanced repo-side:
   - update `plans/31-opengauss-formal-backend.md` and
     `docs/architecture-status.md` to place OpenGauss in the realized baseline
   - ensure Tier 3 docs describe Aristotle, MathCode, and OpenGauss as shipped
     backends with distinct lifecycle contracts
5. Align parity and support claims:
   - make the final Tier 3 state usable by the later Codex-versus-Hermes
     backend parity slice

## Validation and Acceptance

This slice is complete when:

- Aristotle, MathCode, and OpenGauss have stronger repeated validation and
  clearer operator guidance
- the lifecycle and transport difference between Aristotle, MathCode, and
  OpenGauss is explicit everywhere the repo claims Tier 3 support
- OpenGauss is shipped as a bounded local CLI backend, with environment
  readiness separated from raw-checkout setup failures
- the architecture ledger and Tier 3 docs match that result exactly

Required validation:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py --json
uv run python -m unittest discover -s tests -v
uv run python -m unittest tests.test_formal tests.test_probes tests.test_release_scripts -v
uv run python scripts/diagnose_opengauss.py --json
```

Add live Aristotle, MathCode, or OpenGauss validation commands as needed in the
branch when the environment allows them honestly.

## Merge, Push, and Cleanup

- Stage and commit the Tier 3 completion work in coherent chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/tier3-completion-and-opengauss-unblock` into
  `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm CI and Docs are green.
- Delete the feature branch when it is no longer needed.

## Idempotence and Recovery

- Keep the Tier 3 support boundary truthful. Do not imply OpenGauss has
  Aristotle-style submission/poll/resume semantics.
- If OpenGauss is unavailable in a specific operator environment, record an
  environment readiness or raw-checkout setup issue rather than calling the
  backend unshipped.
- Keep Aristotle, MathCode, and OpenGauss lifecycle claims exact. Do not blur
  them into one generic Tier 3 story.

## Interfaces and Dependencies

- Depends on the shipped Tier 3 runtime surfaces already present in
  `src/deep_gvr/formal.py`.
- Depends on the diagnostics work from `plans/37-opengauss-unblock-diagnostics.md`.
- Connects the shipped-backend hardening work in
  `plans/69-tier3-shipped-backends-hardening.md` with the realized OpenGauss
  backend work in `plans/31-opengauss-formal-backend.md`.
