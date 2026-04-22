# 72 Codex-Hermes Backend Parity

## Purpose / Big Picture

Make the native `codex_local` backend at least as capable as the shipped
`hermes` backend across all repo-owned functionality, while retaining full
Hermes support.

The Codex phase-1 and phase-2 work made Codex a real first-class backend and
operator surface. That still does not prove completion against the stronger
standard the user set here: Codex should be equal or greater in functionality
than Hermes for every repo-owned capability, without dropping or weakening the
Hermes backend.

This plan is not about deeper Codex product-managed app state, and it is not
about Codex Cloud. It is about repo-owned backend parity across the full
backend contract: Tier 1 loop behavior, routing, checkpoints, evidence,
transcripts, Tier 2 support, Tier 3 support, release and install surfaces,
remote execution, benchmark validation, and any other backend-sensitive
behavior the repo claims to support.

## Branch Strategy

Start from `main` on `codex/codex-hermes-backend-parity`. Merge back into
`main` locally with a fast-forward only after branch validation passes, then
validate the merged result again, push `main`, confirm CI and Docs, and delete
the feature branch when it is no longer needed.

## Commit Plan

- `plan codex hermes backend parity`
- `add backend parity matrix`
- `close codex hermes parity gaps`

## Progress

- [x] Add this plan and index it from `plans/README.md`.
- [ ] Define the explicit Codex-versus-Hermes parity matrix for repo-owned
  backend capabilities.
- [ ] Close any remaining `codex_local` gaps behind the shipped Hermes backend
  where parity is supposed to hold.
- [ ] Keep Hermes support green and explicit while Codex parity improves.
- [ ] Align docs, probes, release surfaces, and architecture status with the
  final parity result.

## Surprises & Discoveries

- The remaining Codex work is no longer mostly about UI surfaces. It is about
  backend parity across the full repo-owned backend contract.
- Parity must be judged against the repo-owned Hermes support that actually
  ships today, not against blocked-external aspirations such as plan 26.
- Some current gaps are shared-runtime gaps first and Codex gaps second:
  Aristotle transport is still Hermes-shaped, Tier 2 breadth is still narrow in
  the reference environment, and Tier 3 full completion still depends on the
  OpenGauss question.

## Decision Log

- Decision: define backend parity against shipped, repo-owned Hermes behavior.
  Blocked-external Hermes capabilities do not set the parity floor until they
  actually ship.
- Decision: parity means Codex is at least as capable on every repo-owned
  backend surface where Hermes ships behavior today, while Hermes remains fully
  supported and validated.
- Decision: deeper Codex app-state ownership remains out of scope unless the
  product exposes a stable repo-owned contract later.

## Outcomes & Retrospective

- This plan exists so the new completion bar for Codex is tracked explicitly
  instead of being inferred from older phase-2 work.

## Context and Orientation

- Backend seam and runtime:
  - `src/deep_gvr/orchestrator.py`
  - `src/deep_gvr/cli.py`
  - `src/deep_gvr/tier1.py`
  - `src/deep_gvr/formal.py`
- Backend-sensitive probes and release surfaces:
  - `src/deep_gvr/probes.py`
  - `src/deep_gvr/release_surface.py`
  - `scripts/run_capability_probes.py`
- Current Codex and Hermes architecture state:
  - `docs/system-overview.md`
  - `docs/codex-local.md`
  - `docs/deep-gvr-architecture.md`
  - `docs/architecture-status.md`
- Dependencies for shared-runtime parity:
  - `plans/70-tier2-coverage-expansion.md`
  - `plans/69-tier3-shipped-backends-hardening.md`
  - `plans/71-tier3-completion-and-opengauss-unblock.md`
  - `plans/26-subagent-capability-closure.md`

## Plan of Work

1. Define the full backend-parity matrix for `hermes` and `codex_local`,
   including Tier 1 and every other backend-sensitive repo surface.
2. Prove parity for every shared repo-owned capability where the support claim
   is the same.
3. Close any remaining Codex-behind-Hermes gaps that are still repo-owned.
4. Keep Hermes fully supported and validated while that work lands.

## Concrete Steps

1. Build the parity matrix:
   - Tier 1 loop and resume behavior
   - routing and backend selection behavior
   - transcript and evidence surfaces
   - Tier 2 family coverage and backend dispatch
   - Tier 3 backend coverage and lifecycle behavior
   - release preflight and install surfaces
   - remote execution and stronger-machine flows
   - benchmark and probe visibility
   - any remaining backend-sensitive operator or artifact surfaces
2. Add backend-matrix validation:
   - add tests or live smokes that exercise both `hermes` and `codex_local`
     where the repo claims equivalent support
   - keep backend-specific differences explicit where the repo does not yet
     claim equivalence
3. Close remaining repo-owned gaps:
   - remove or narrow lingering Hermes-only assumptions from Codex-sensitive
     release and operator surfaces where they are no longer justified
   - implement missing Codex runtime support where parity should hold
4. Keep Hermes fully supported:
   - ensure parity work does not regress Hermes install, preflight, execution,
     or evidence behavior
5. Update docs:
   - make the final parity state explicit in `docs/architecture-status.md`,
     `docs/system-overview.md`, and the Codex-facing docs

## Validation and Acceptance

This slice is complete when:

- the repo has an explicit backend-parity matrix for `hermes` and
  `codex_local`
- every shared repo-owned capability is either:
  - equal or stronger on `codex_local`, or
  - explicitly documented as a still-open or blocked difference
- Hermes remains fully supported and validated
- the docs and release/preflight surfaces describe the final backend boundary
  honestly

Required validation:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py --json
uv run python -m unittest discover -s tests -v
uv run python -m unittest tests.test_cli tests.test_tier1_loop tests.test_formal tests.test_evaluation tests.test_release_scripts -v
```

Add narrower backend-matrix smokes as needed in the branch.

## Merge, Push, and Cleanup

- Stage and commit the backend-parity work in coherent chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/codex-hermes-backend-parity` into `main` locally
  only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm CI and Docs are green.
- Delete the feature branch when it is no longer needed.

## Idempotence and Recovery

- Keep parity claims exact. Do not declare Codex equal to Hermes where the repo
  still has a real backend-sensitive gap.
- Do not weaken Hermes support while improving Codex.
- Keep blocked-external Hermes items separate from the parity floor until they
  actually ship.

## Interfaces and Dependencies

- Depends on the current backend seam in `src/deep_gvr/`.
- Depends on Tier 2 and Tier 3 completion work making the shared runtime
  surfaces broad enough to compare honestly.
- Preserves Hermes as a supported backend rather than replacing it.
