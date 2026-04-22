# 71 Tier 3 Completion and OpenGauss Unblock

## Purpose / Big Picture

Close the remaining Tier 3 completion gap by combining shipped-backend
hardening with a current, evidence-backed OpenGauss unblock attempt.

Plan 69 is necessary but not sufficient for the stronger completion bar. It
hardens Aristotle and MathCode, but Tier 3 is not fully addressed until the
OpenGauss architecture target is revisited with current evidence and either:

- integrated honestly into the runtime, or
- reduced to a precise external blocker with no remaining repo-owned ambiguity

The user-visible outcome of this slice is that Tier 3 should no longer be in
the ambiguous state where the shipped backends are improving while the
OpenGauss target remains only loosely separated in chat history.

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
- [x] Decide whether OpenGauss can advance repo-side or remains honestly
  repo-owned follow-on work.
- [x] Align Tier 3 docs, probes, and architecture status with the resulting
  full Tier 3 state.

## Surprises & Discoveries

- Tier 3 is not fully addressed just because Aristotle and MathCode are the
  shipped backends today. The architecture target still includes OpenGauss.
- Aristotle and MathCode differ structurally: Aristotle has a real
  submission/poll/resume lifecycle while MathCode is currently a bounded local
  CLI path.
- The current OpenGauss ambiguity was narrower than the older docs claimed:
  the installed runtime and published Morph targets are healthy again, while
  the raw checkout launcher can still fail separately because its checkout-local
  Python dependencies are not bootstrapped.

## Decision Log

- Decision: treat full Tier 3 completion as a two-part program:
  shipped-backend hardening plus an explicit OpenGauss unblock decision.
- Decision: do not imply OpenGauss is part of the shipped path unless a working
  `gauss` runtime and repo-owned integration actually exist.
- Decision: now that the installed `gauss` runtime is healthy again, reclassify
  OpenGauss from `blocked_external` to planned repo-owned backend work under
  plan 31.

## Outcomes & Retrospective

- This plan exists so Tier 3 completion is owned as a concrete repo program
  instead of being split between a hardening plan and an older blocked plan
  with no explicit reconnecting step.
- The reconnecting step is now complete. OpenGauss can advance repo-side: the
  installed runtime is healthy, the published Morph targets resolve, and the
  remaining gap is the unimplemented deep-gvr backend-selection, transport,
  operator-flow, and benchmark work in plan 31.

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

1. Harden Aristotle and MathCode until the shipped Tier 3 path is repeatedly
   validated and operator-solid.
2. Re-run the OpenGauss unblock sequence with current upstream state and local
   diagnostics.
3. Decide whether OpenGauss can advance into repo-owned integration work.
4. Make the full Tier 3 state explicit in docs, probes, and the architecture
   ledger.

## Concrete Steps

1. Execute `plans/69-tier3-shipped-backends-hardening.md`:
   - strengthen Aristotle submission/poll/resume and CLI-fallback validation
   - strengthen MathCode local CLI, timeout, output-parsing, and artifact truth
   - make the lifecycle difference between Aristotle and MathCode explicit
2. Re-run OpenGauss diagnostics and unblock checks:
   - run `uv run python scripts/diagnose_opengauss.py --json`
   - recheck the current upstream installer target and local `gauss` runtime
   - capture exact failure output and whether the blocker is still upstream
     packaging, local prerequisites, or repo-owned code
3. If OpenGauss becomes runnable:
   - continue with the backend-selection, transport, docs, and benchmark work
     from `plans/31-opengauss-formal-backend.md`
4. If OpenGauss can advance repo-side without being shipped yet:
   - update `plans/31-opengauss-formal-backend.md` and
     `docs/architecture-status.md` to make the remaining repo-owned gap exact
   - ensure Tier 3 docs describe Aristotle and MathCode as the shipped path and
     OpenGauss as an explicit planned integration target, not an implied
     near-term shipped option
5. Align parity and support claims:
   - make the final Tier 3 state usable by the later Codex-versus-Hermes
     backend parity slice

## Validation and Acceptance

This slice is complete when:

- Aristotle and MathCode have stronger repeated validation and clearer operator
  guidance
- the lifecycle and transport difference between Aristotle and MathCode is
  explicit everywhere the repo claims Tier 3 support
- OpenGauss is reduced to a precise current repo-owned integration gap with no
  stale external-blocker ambiguity
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

- Keep the Tier 3 support boundary truthful. Do not imply OpenGauss is part of
  the shipped path until a working runtime and repo-owned integration exist.
- If the current OpenGauss unblock attempt succeeds locally but the backend is
  still unimplemented, preserve that distinction explicitly rather than
  collapsing it back into a fake external blocker.
- Keep Aristotle and MathCode lifecycle claims exact. Do not blur them into one
  generic Tier 3 story.

## Interfaces and Dependencies

- Depends on the shipped Tier 3 runtime surfaces already present in
  `src/deep_gvr/formal.py`.
- Depends on the diagnostics work from `plans/37-opengauss-unblock-diagnostics.md`.
- Connects the shipped-backend hardening work in
  `plans/69-tier3-shipped-backends-hardening.md` with the still-open
  architecture target in `plans/31-opengauss-formal-backend.md`.
