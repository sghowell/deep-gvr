# 69 Tier 3 Shipped Backends Hardening

## Purpose / Big Picture

Harden the shipped Tier 3 backends, Aristotle and MathCode, so their operator
flows, evidence surfaces, and backend boundaries are clearer and more
repeatedly validated.

This was not an OpenGauss slice. At plan creation time, OpenGauss was still
treated as blocked external. The goal here was to strengthen the Tier 3
backends the repo already ships.

## Branch Strategy

Start from `main` on `codex/tier3-shipped-backends-hardening`. Keep this slice
separate from Tier 2 work so the Aristotle and MathCode acceptance bar stays
focused.

## Commit Plan

- `harden tier3 shipped backends`
- `tighten tier3 validation and preflight`
- `document tier3 support boundary`

## Progress

- [x] Strengthen Aristotle operator and lifecycle validation.
- [x] Strengthen MathCode operator validation and artifact truth.
- [x] Make the Aristotle vs MathCode lifecycle and transport boundary clearer in
  docs and preflight.
- [x] Keep OpenGauss explicitly out of the shipped Tier 3 path.

## Surprises & Discoveries

- Aristotle and MathCode are both shipped Tier 3 backends, but they are not
  equivalent surfaces: Aristotle has a real submission/poll/resume lifecycle,
  while MathCode is currently a bounded local CLI path.
- The biggest Tier 3 risk is not missing runtime code. It is overstating the
  parity of the shipped backends or blurring the separate OpenGauss target into
  the standard support story.

## Decision Log

- Decision: harden Aristotle and MathCode first, and keep OpenGauss out of the
  shipped Tier 3 completion bar until a later slice resolves its exact status.
- Decision: preserve the explicit Aristotle transport boundary until it is
  actually no longer Hermes-shaped.

## Outcomes & Retrospective

- Aristotle and MathCode now have a dedicated shipped-backend validation subset
  (`tier3-support`) that runs in CI and release instead of relying on indirect
  coverage inside broader benchmark groups.
- MathCode artifact truth is tighter: the formal transport now attributes a
  generated Lean file only when the current run created or modified it.
- Probes, preflight, and operator docs now expose the Aristotle versus
  MathCode lifecycle boundary explicitly while leaving OpenGauss on its
  separate non-shipped path. Plan 71 later reclassified OpenGauss from
  `blocked_external` to planned repo-owned backend work.

## Non-Goals

- Do not attempt to implement OpenGauss here.
- Do not add another orchestrator backend here.
- Do not claim that `codex_local` has retired the Hermes-shaped Aristotle
  transport boundary unless the code really does so.

## Context and Orientation

- Tier 3 runtime:
  - `src/deep_gvr/formal.py`
  - `src/deep_gvr/tier1.py`
- Current Tier 3 readiness and docs:
  - `src/deep_gvr/probes.py`
  - `scripts/run_capability_probes.py`
  - `docs/system-overview.md`
  - `docs/deep-gvr-architecture.md`
  - `docs/tier2-tier3-support-matrix.md`
- Deterministic coverage:
  - `tests/test_formal.py`
  - `eval/known_problems.json`

## Plan of Work

1. Strengthen Aristotle validation around submission, polling, resume, CLI
   fallback, and operator-preflight truth.
2. Strengthen MathCode validation around bounded local CLI execution, output
   parsing, timeout handling, and generated-artifact truth.
3. Make the lifecycle difference between Aristotle and MathCode explicit
   everywhere the operator will see it.
4. Leave OpenGauss on its separate non-shipped path.

## Concrete Steps

1. Aristotle:
   - add or tighten tests for submission/poll/resume and CLI fallback behavior
   - ensure docs and preflight surfaces describe the Hermes MCP primary path and
     direct CLI fallback accurately
2. MathCode:
   - tighten validation around the local run script, bounded execution,
     structured output, and generated Lean-file capture
   - make the absence of a shipped long-running lifecycle explicit
3. Backend boundary:
   - verify that the shared Tier 3 surface behaves honestly under both shipped
     orchestrator backends where applicable
   - keep the Hermes-shaped Aristotle transport dependency visible until it is
     actually retired
4. Documentation:
   - keep the support matrix, architecture doc, and operator workflow aligned
     with the real Tier 3 state

## Validation and Acceptance

This slice is complete when:

- Aristotle and MathCode both have stronger validation and clearer operator
  guidance
- the lifecycle difference between Aristotle and MathCode is explicit
- Tier 3 docs and preflight surfaces are aligned with the real shipped boundary
- OpenGauss remains explicitly outside the shipped support story rather than
  being blurred into it

Required validation:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Add narrower Tier 3-specific validation as needed in the branch.

## Merge, Push, and Cleanup

- Stage and commit the Tier 3 hardening work in coherent chunks.
- Validate before merge.
- Merge locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm CI and Docs are green.
- Delete the feature branch when it is no longer needed.

## Idempotence and Recovery

- Keep the Tier 3 support boundary truthful. Do not imply Aristotle and
  MathCode have the same lifecycle or transport semantics when they do not.
- Keep OpenGauss explicitly outside the shipped Tier 3 path until the repo can
  honestly ship a working operator path.

## Interfaces and Dependencies

- Depends on the existing Aristotle lifecycle, MathCode transport, and formal
  result contracts already shipped in the repo.
- Depends on OpenGauss remaining a separate non-shipped item until its backend
  integration slice lands.
