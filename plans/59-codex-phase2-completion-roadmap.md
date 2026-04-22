# 59 Codex Phase 2 Completion Roadmap

## Purpose / Big Picture

Record the remaining Codex-focused work needed before `deep-gvr` should treat
the Codex side of the product as feature-complete instead of merely
well-supported. The current repo already ships the Codex local surface, plugin,
automations, review/QA pack, subagent pack, SSH/devbox surface, native
`codex_local` backend, native role-separated runtime, and remote SSH/devbox
execution path. This roadmap captures the remaining backend/runtime leverage
work that is still worth doing before shifting attention fully to release-only
concerns.

This plan is a roadmap and prioritization surface. It exists so the next Codex
slices live in the repo instead of only in chat history.

## Branch Strategy

This roadmap is being added alongside the first follow-on execution slice on
`codex/codex-runtime-hardening`. Future phase-2 slices should each use their own
feature branch starting from `main`, merge back locally with a fast-forward
only after validation passes, validate the merged result again, push `main`,
confirm CI/Docs, and delete the feature branch when it is no longer needed.

## Commit Plan

- `add codex phase2 roadmap`
- `harden codex runtime evidence`
- `document codex runtime hardening`

## Progress

- [x] Materialize the Codex phase-2 roadmap as a repo-local plan.
- [x] Define the immediate next slice as Codex runtime hardening.
- [x] Add concrete follow-on plan files for the remaining queued phase-2 slices.
- [ ] Execute the remaining queued phase-2 slices.
  Completed so far: `60`, `61`, `62`, `63`.

## Surprises & Discoveries

- The architecture ledger already treats the major Codex phase-1 surfaces as
  realized: local surface, plugin, automations, review/QA, subagent pack,
  SSH/devbox surface, backend abstraction, native local backend, native
  role-separated backend, and SSH/devbox execution.
- The remaining Codex work is not another “make Codex supported” step. It is
  phase-2 leverage and hardening work around observability, remote bootstrap,
  review/QA execution, native delegation evaluation, and possibly Codex Cloud.
- Some earlier Codex slices were intentionally narrow prompt/export surfaces.
  That was the right phase-1 boundary, but it means the remaining work should be
  explicit about what is runtime-owned versus product-owned.

## Decision Log

- Decision: treat the Codex phase-1 surface as complete enough to stop adding
  ad hoc slices without a roadmap.
- Decision: prioritize runtime hardening before more ambitious Codex-native
  product integration.
- Decision: keep Codex Cloud as a later optional surface, not the next runtime
  step.
- Decision: keep repo-owned boundaries honest around live Codex app state,
  plugin enablement, automations registration, and SSH/devbox provisioning.

## Outcomes & Retrospective

- The repo now has an explicit Codex phase-2 queue instead of relying on chat
  memory for remaining Codex work.
- The immediate next execution slice was materialized and executed as
  `plans/60-codex-runtime-hardening.md`.
- The remote-bootstrap follow-on is now also executed as
  `plans/61-codex-remote-bootstrap.md`.
- The review/QA execution follow-on is now also executed as
  `plans/62-codex-review-qa-execution.md`.
- The native delegation evaluation follow-on is now also executed as
  `plans/63-codex-native-delegation-evaluation.md`.
- Future queued slices now also exist as repo-local plan files:
  `plans/64-codex-cloud-surface.md`.
- A later repo-wide completion bar now also requires explicit Codex-versus-
  Hermes backend parity over the shared runtime surface. That work is tracked
  separately in `plans/72-codex-hermes-backend-parity.md` rather than being
  treated as part of the original phase-2 queue.

## Context and Orientation

- Current Codex runtime/docs surfaces:
  - `src/deep_gvr/orchestrator.py`
  - `src/deep_gvr/cli.py`
  - `docs/codex-local.md`
  - `docs/codex-subagents.md`
  - `docs/codex-ssh-devbox.md`
  - `docs/deep-gvr-architecture.md`
  - `docs/architecture-status.md`
- Recent execution slices:
  - `plans/55-codex-backend-abstraction.md`
  - `plans/56-codex-local-backend.md`
  - `plans/57-codex-ssh-devbox-execution.md`
  - `plans/58-codex-native-subagent-backend.md`

## Plan of Work

1. Harden the native `codex_local` backend around runtime evidence and failure
   observability.
2. Improve the remote Codex execution story so stronger machines are easier to
   treat as first-class validator hosts.
3. Upgrade the Codex review/QA surface from prompt pack only toward a stronger
   evidence-backed execution workflow.
4. Evaluate how much native Codex delegation/subagent state is realistically
   worth integrating at the runtime boundary.
5. Decide whether Codex Cloud belongs in the product surface after local and
   remote native Codex are fully hardened.

## Concrete Steps

1. Execute `plans/60-codex-runtime-hardening.md`:
   - preserve failed Codex role calls in transcript artifacts
   - record richer per-role runtime evidence in the existing artifact surface
   - expose Codex-specific capability evidence without conflating it with the
     Hermes-only plan-26 closure probes
2. Execute `plans/61-codex-remote-bootstrap.md`:
   - improve SSH/devbox remote environment bootstrap and operator readiness
   - make remote heavy-validation use less manual
3. Execute `plans/62-codex-review-qa-execution.md`:
   - turn the current review/QA prompt surface into a stronger execution and
     evidence path where repo-owned boundaries allow it
4. Execute `plans/63-codex-native-delegation-evaluation.md`:
   - measure whether deeper Codex-native delegation should be promoted beyond
     the current operator-pack boundary
5. Optionally execute `plans/64-codex-cloud-surface.md` if Cloud support is
   still desired after the local and remote Codex paths are fully hardened

## Validation and Acceptance

This roadmap file is accepted when:

- the remaining Codex work is captured in-repo with explicit owning plans
- the immediate next slice is clear
- the plan stays aligned with the current implemented Codex boundary

Repo checks that should continue to pass when the roadmap is materialized:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

## Merge, Push, and Cleanup

- Stage and commit the roadmap in a reviewable chunk.
- If it lands alongside the first follow-on Codex slice, validate the whole
  branch before merge.
- Merge locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions and Docs runs for the pushed head are green.
- Delete the feature branch when it is no longer needed.

## Idempotence and Recovery

- The roadmap must stay truthful to the repo’s current implemented Codex
  boundary; do not use it to promise unimplemented product integrations.
- If later slices change the ordering, update this roadmap in the same branch as
  the new slice rather than leaving stale queue state behind.

## Interfaces and Dependencies

- Depends on the current realized Codex phase-1 surfaces already recorded in
  `docs/architecture-status.md`.
- Depends on the repo continuing to distinguish runtime-owned behavior from
  product-owned Codex app state.
