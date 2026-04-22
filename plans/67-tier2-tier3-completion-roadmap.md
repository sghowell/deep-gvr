# 67 Tier 2 / Tier 3 Completion Roadmap

## Purpose / Big Picture

Record the remaining shared-runtime work needed before more orchestrator-backend
expansion should take priority again.

`deep-gvr` already ships broad Tier 2 adapter coverage, Aristotle transport and
lifecycle support, and MathCode as a real local Tier 3 backend. The remaining
gap is no longer "implement the surface at all." It is to make the shipped Tier
2 and Tier 3 surfaces explicitly supportable, operator-ready, and honest about
where support is broad, where it is local-only, and where it is still blocked
externally.

This roadmap also pauses `openai_native` as the next execution priority until
the shared Tier 2 and Tier 3 completion work is materially further along.

## Branch Strategy

This roadmap is being added on `codex/tier2-tier3-completion-roadmap`. Future
follow-on slices should each use their own feature branch from `main`, merge
back locally only after validation passes, validate the merged result again,
push `main`, confirm CI and Docs, and then delete the feature branch when it is
no longer needed.

## Commit Plan

- `add tier2 tier3 completion roadmap`
- `add tier2 tier3 support matrix`
- `document tier2 tier3 priority shift`

## Progress

- [x] Materialize the Tier 2 / Tier 3 completion roadmap in-repo.
- [x] Add a factual support-matrix reference page that separates runtime
  implementation, deterministic coverage, execution-backend support, and
  reference-environment readiness.
- [x] Queue the next completion slices in repo-local plan files.
- [x] Execute `plans/68-tier2-support-completion.md`.
- [x] Execute `plans/70-tier2-coverage-expansion.md`.
- [ ] Execute `plans/69-tier3-shipped-backends-hardening.md`.
- [ ] Execute `plans/71-tier3-completion-and-opengauss-unblock.md`.
- [ ] Execute `plans/72-codex-hermes-backend-parity.md`.
- [ ] Reassess `plans/66-openai-native-backend.md` only after the shared Tier 2
  and Tier 3 completion bar and the Codex-versus-Hermes parity bar are
  clearer.

## Surprises & Discoveries

- Tier 2 is broader in the runtime than it is in current operator readiness.
  The repo ships nine adapter families with deterministic benchmark cases, but
  only one family is fully ready in the current reference environment.
- Tier 2 backend dispatch is not the same thing as orchestrator backend support.
  Today only `qec_decoder_benchmark` has explicit `local` / `modal` / `ssh`
  execution-backend support.
- Aristotle and MathCode are both shipped Tier 3 backends, but they are not
  symmetric:
  - Aristotle has a true submission/poll/resume lifecycle and still uses a
    Hermes-shaped transport boundary.
  - MathCode is a bounded local CLI path and does not ship the same lifecycle
    semantics.
- OpenGauss remains honestly blocked external. It should stay out of the
  completion bar for shipped Tier 3 support until upstream installability
  recovers.
- The stronger completion bar is now broader than this roadmap originally
  assumed: Tier 2 needs real coverage expansion beyond plan 68, Tier 3 needs an
  explicit reconnect between shipped-backend hardening and the OpenGauss target,
  and Codex backend completion now depends on proving parity against the
  shipped Hermes backend rather than only finishing surface-level Codex slices.

## Decision Log

- Decision: prioritize shared Tier 2 and Tier 3 completion over another
  orchestrator-backend expansion slice.
- Decision: define "complete support" in terms of explicit support statements,
  deterministic coverage, operator guidance, preflight truth, and repeated live
  validation where support is claimed.
- Decision: do not require every Tier 2 family to run on every execution
  backend. Completion means every shipped family has an explicit support
  statement and a validated operator path that matches that statement.
- Decision: treat Aristotle and MathCode as the shipped Tier 3 completion scope,
  while keeping OpenGauss separately blocked external.
- Decision: the overall backend-completion bar now also includes Codex-versus-
  Hermes parity after the shared Tier 2 and Tier 3 work is materially further
  along.

## Outcomes & Retrospective

- The repo now has an explicit roadmap for the shared Tier 2 and Tier 3 work
  that still remains before another backend expansion should be the default next
  step.
- The public technical-reference surface now has a support matrix page that
  makes the shipped boundary explicit instead of leaving it implied across
  architecture docs, probes, and plans.
- The Tier 2 follow-on is now executed as `plans/68-tier2-support-completion.md`.
- The broader Tier 2 coverage slice is now executed as
  `plans/70-tier2-coverage-expansion.md`.
- The next follow-on slices now exist as repo-local plan files:
  `plans/69-tier3-shipped-backends-hardening.md`,
  `plans/71-tier3-completion-and-opengauss-unblock.md`, and
  `plans/72-codex-hermes-backend-parity.md`.

## Context and Orientation

- Shared runtime and probes:
  - `src/deep_gvr/tier1.py`
  - `src/deep_gvr/formal.py`
  - `src/deep_gvr/probes.py`
  - `scripts/run_capability_probes.py`
- Tier 2 and benchmark surfaces:
  - `adapters/registry.py`
  - `tests/test_analysis_adapters.py`
  - `eval/known_problems.json`
- Existing backend expansion queue:
  - `plans/65-openai-native-backend-evaluation.md`
  - `plans/66-openai-native-backend.md`

## Plan of Work

1. Make Tier 2 not only explicit but materially broader in real operator
   coverage.
2. Harden the shipped Tier 3 backends, Aristotle and MathCode, around live
   validation, operator guidance, and backend-boundary honesty.
3. Reconnect Tier 3 hardening to the OpenGauss architecture target with a
   current unblock decision.
4. Prove Codex-versus-Hermes backend parity on the full repo-owned backend
   contract, not only on Tier 2 and Tier 3.
5. Return to backend expansion only after the shared Tier 2 / Tier 3 support
   picture and the Codex parity bar are stronger.

## Concrete Steps

1. Execute `plans/68-tier2-support-completion.md`:
   - document explicit backend-support statements for every shipped Tier 2
     family
   - improve operator installability and release-preflight truth
   - validate the shipped Tier 2 families through the runtime, not only unit
     adapter tests
2. Execute `plans/70-tier2-coverage-expansion.md`:
   - materially raise real Tier 2 operator coverage beyond the current `1/9`
     ready-family reference baseline
   - decide deliberately whether any families beyond QEC should gain non-local
     backend support
   - add stronger backend-matrix validation where shared support claims apply
3. Execute `plans/69-tier3-shipped-backends-hardening.md`:
   - harden Aristotle and MathCode operator flows
   - strengthen repeated live validation and artifact truth
   - make the Aristotle vs MathCode lifecycle difference explicit in docs and
     preflight
4. Execute `plans/71-tier3-completion-and-opengauss-unblock.md`:
   - reconnect shipped Tier 3 hardening with the still-open OpenGauss target
   - capture a current, evidence-backed integration or blocked-external answer
5. Execute `plans/72-codex-hermes-backend-parity.md`:
   - prove that `codex_local` is at least as capable as the shipped `hermes`
     backend across repo-owned functionality
   - retain full Hermes support while closing any remaining Codex-behind-Hermes
     gaps
6. Reassess `plans/66-openai-native-backend.md` only after the support matrix,
   Tier 3 completion work, and Codex parity slice give a better answer to what
   "fully supported" actually means.

## Validation and Acceptance

This roadmap is accepted when:

- the remaining Tier 2 and Tier 3 completion work is captured in-repo with
  explicit owning plans
- the public technical-reference surface records the shipped support boundary
  clearly
- the next execution slice is unambiguous

Repo checks that should continue to pass when the roadmap is materialized:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

## Merge, Push, and Cleanup

- Stage and commit the roadmap and support-matrix updates in coherent chunks.
- Validate the branch before merge.
- Merge locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions and Docs runs for the pushed head are green.
- Delete the feature branch when it is no longer needed.

## Idempotence and Recovery

- Keep this roadmap truthful to the shipped runtime and current probe surface;
  do not use it to promise backend work that has not happened yet.
- If the Tier 2 or Tier 3 follow-on ordering changes, update this roadmap in
  the same branch as the new change rather than leaving stale queue state
  behind.

## Interfaces and Dependencies

- Depends on the current Tier 2 adapter registry, benchmark cases, and probe
  surfaces already shipped in the repo.
- Depends on the existing Aristotle lifecycle and MathCode local transport
  surfaces.
- Depends on OpenGauss continuing to be treated as blocked external until the
  upstream install story is healthy again.
