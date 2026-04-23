# 31 OpenGauss Formal Backend

## Purpose / Big Picture

Implement OpenGauss as the additional shipped formal backend promised by the architecture, alongside Aristotle as the primary default backend and MathCode as the other bounded local CLI path. This slice adds a real OpenGauss backend selection, local quiet-query transport, operator flow, and benchmark coverage without pretending OpenGauss has Aristotle-style submission or resume semantics.

## Branch Strategy

Start from `main` and implement this slice on `codex/opengauss-formal-backend`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result, push `main`, confirm CI, and delete the feature branch.

## Commit Plan

- `add opengauss backend contracts`
- `wire opengauss transport`
- `document interactive formal backend`

## Progress

- [x] Add the new plan and index it from `plans/README.md`.
- [x] Diagnose the current local OpenGauss installer failure mode.
- [x] Add backend selection and contracts for OpenGauss.
- [x] Implement the OpenGauss transport and operator workflow.
- [x] Extend docs, tests, and benchmarks for the new formal backend.

## Surprises & Discoveries

- OpenGauss is a distinct operator flow from Aristotle, so this slice needs backend-specific setup and lifecycle docs, not just another enum value.
- The benchmark suite should include at least one case that benefits from interactive/project-scoped proof work.
- The upstream install path is no longer the blocker on this machine: the official installer now completes, the published Morph targets resolve, `gauss` is on `PATH`, and `~/.gauss/config.yaml` exists.
- The remaining ambiguity is narrower and repo-owned: the raw checkout launcher can still fail `./gauss doctor` if the checkout-local Python dependencies are not bootstrapped, but the installed runtime is healthy enough to support real backend integration work.
- The shipped repo-owned OpenGauss path is a bounded local `gauss chat -Q` CLI transport with optional session-id and transcript capture, not a full Aristotle-style submission/poll/resume lifecycle.

## Decision Log

- Aristotle remains the primary default formal backend unless a case or config selects OpenGauss explicitly.
- OpenGauss must reuse the same Tier 3 result contracts where possible.
- Backend choice must be explicit in evidence and benchmark artifacts.
- Keep the raw-checkout diagnostics separate from the installed-runtime contract. Once the installed runtime is healthy, the remaining gap is repo-owned backend work rather than an external blocker.
- A separate MathCode integration slice may proceed in parallel, but it does not retire the OpenGauss architecture target.

## Outcomes & Retrospective

- OpenGauss is now selectable as a shipped Tier 3 backend through the same Tier 3 contracts used by Aristotle and MathCode.
- The repo now ships a bounded local OpenGauss CLI transport over `gauss chat -Q`, including provider/setup error mapping plus session-id and transcript-path capture when the CLI emits them.
- Deterministic benchmark coverage now includes an OpenGauss-backed formal case, and the `tier3-support` subset includes OpenGauss alongside Aristotle and MathCode.
- Plan 37 remains useful as the diagnostics surface (`uv run python scripts/diagnose_opengauss.py --json`), but it is now operator support for the shipped backend rather than a stand-in for missing integration.

## Context and Orientation

- Formal runtime: `src/deep_gvr/formal.py`
- Tier 3 contracts: `src/deep_gvr/contracts.py`
- Architecture ledger item: `opengauss-formal-backend`

## Plan of Work

1. Add formal backend selection and contracts for OpenGauss.
2. Implement transport and operator setup for OpenGauss.
3. Extend benchmarks, docs, and evidence artifacts for multi-backend Tier 3 work.

## Concrete Steps

1. Extend formal backend configuration and contracts to include OpenGauss.
2. Add the OpenGauss transport boundary and honest bounded lifecycle integration.
3. Update prompts, docs, and operator setup for OpenGauss-backed proof work.
4. Add tests and benchmark cases that exercise the new backend.

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Targeted validation:

```bash
uv run python -m unittest tests.test_formal tests.test_contracts -v
uv run python scripts/diagnose_opengauss.py --json
uv run python eval/run_eval.py --subset tier3-support --output /tmp/deep-gvr-tier3-support-opengauss.json
```

Acceptance evidence:

- OpenGauss is selectable as a real Tier 3 backend.
- Evidence and benchmark artifacts identify which formal backend ran.
- Operator docs cover both Aristotle and OpenGauss flows accurately.
- The shipped lifecycle boundary stays honest: OpenGauss is a bounded local CLI path, not a submission/poll/resume transport.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/opengauss-formal-backend` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Keep Aristotle as the stable default while OpenGauss integration is being added.
- Reuse existing Tier 3 artifact shapes where possible.
- If the local installed OpenGauss environment is not ready, keep the slice open rather than weakening the target.

## Interfaces and Dependencies

- Depends on the completed formal lifecycle work from plan 27.
- Touches formal backend contracts, transport code, docs, and benchmark cases.
- Requires a working local `gauss` runtime, backend contracts, transport code, benchmark coverage, and operator setup.
