# 35 MathCode Formal Backend

## Purpose / Big Picture

Integrate MathCode as an additional local Lean formalization backend for Tier 3.
Unlike OpenGauss, MathCode is already reachable on this machine as a repo-local
CLI with a bundled AUTOLEAN pipeline, so this slice gives deep-gvr a pragmatic
local proof/fomalization path while the OpenGauss installer remains blocked.

## Branch Strategy

Start from `main` and implement this slice on `codex/mathcode-formal-backend`.
Merge back into `main` locally with a fast-forward only after branch validation
passes, then validate the merged result, push `main`, confirm CI, and delete
the feature branch.

## Commit Plan

- `add mathcode backend contracts`
- `wire mathcode formal transport`
- `document mathcode backend workflow`

## Progress

- [x] Add the new plan and index it from `plans/README.md`.
- [x] Add formal backend selection and contracts for MathCode.
- [x] Implement the MathCode transport and operator workflow.
- [x] Extend docs, tests, and benchmarks for the MathCode backend.

## Surprises & Discoveries

- The local MathCode checkout in `~/dev/mathcode` already has the repo-local
  `mathcode` binary, `AUTOLEAN/`, and `lean-workspace/`, so the immediate
  problem is integration work, not initial bootstrap.
- `./run --help` shows a stable non-interactive CLI surface with `-p/--print`,
  JSON output support, JSON schema support, and normal command-timeout control,
  which makes MathCode a better fit for a deep-gvr transport boundary than a
  fully interactive TUI-first tool.
- MathCode defaults to Codex auth and writes formal outputs to
  `LeanFormalizations/`, which means the deep-gvr transport should treat it as a
  local CLI backend with explicit artifact capture instead of assuming MCP or
  delegated subagent semantics.
- The local CLI returns a stable JSON envelope with top-level metadata and a
  `structured_output` payload, so the transport can depend on schema-shaped
  output instead of scraping prose.
- MathCode is built for mathematical formalization specifically, so benchmark
  coverage should initially focus on theorem-style or proof-obligation cases
  rather than trying to force every formalizable claim through it.

## Decision Log

- Aristotle remains the default Tier 3 backend unless the config or case
  explicitly selects MathCode.
- MathCode integration should use the existing Tier 3 result contracts where
  possible rather than inventing a second proof artifact vocabulary.
- The initial MathCode transport should be local and non-interactive:
  `mathcode -p` or `./run -p` with structured output capture, bounded timeout,
  and explicit artifact persistence.
- MathCode does not retire the OpenGauss target; it is an additional local
  formal backend, not a replacement for plan 31.

## Outcomes & Retrospective

- MathCode is now selectable as a real Tier 3 backend through the shipped config
  surface, probe set, release preflight, deterministic benchmark suite, and
  formal transport code.
- The integration reuses the existing Tier 3 artifact family instead of adding
  MathCode-only artifacts, which keeps session evidence coherent across formal
  backends.
- OpenGauss remained out of scope and unchanged by this slice; plan 71 later
  reclassified it from `blocked_external` to planned repo-owned backend work.

## Context and Orientation

- Formal runtime: `src/deep_gvr/formal.py`
- Tier 3 contracts: `src/deep_gvr/contracts.py`
- Architecture ledger item: `mathcode-formal-backend`
- Local reference checkout: `~/dev/mathcode`

## Plan of Work

1. Add formal backend selection and contracts for MathCode.
2. Implement a local MathCode CLI transport boundary.
3. Extend benchmarks, docs, and evidence artifacts for MathCode-backed Tier 3
   work.

## Concrete Steps

1. Extend formal backend configuration and contracts to include `mathcode`.
2. Add a MathCode transport in `src/deep_gvr/formal.py` that can invoke either
   the configured `mathcode` binary or the repo-local `./run` wrapper in
   non-interactive print mode.
3. Map MathCode stdout/stderr, generated Lean files, and timeout/error outcomes
   into the existing `FormalVerificationRequest`, `formal_transport`, and
   `formal_results` artifact model.
4. Add readiness/preflight checks that detect the MathCode binary, bundled Lean
   workspace, and required auth/config state without pretending the backend is
   usable when the local checkout is incomplete.
5. Add tests and benchmark cases for at least one MathCode-backed formalizable
   case, plus failure coverage for missing binary, timeout, and malformed output.
6. Update docs and operator guidance so MathCode setup and usage are explicit
   and separate from Aristotle MCP and OpenGauss.

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
cd ~/dev/mathcode && ./run --help
```

Acceptance evidence:

- MathCode is selectable as a real Tier 3 backend.
- Evidence and benchmark artifacts identify when MathCode ran.
- Operator docs cover the MathCode flow accurately.
- At least one formal benchmark case completes through a MathCode-backed path or
  records a structured backend-specific failure artifact.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/mathcode-formal-backend` into `main` locally only
  after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if
  one was created.

## Idempotence and Recovery

- Keep Aristotle as the stable default while MathCode integration is being
  added.
- Reuse existing Tier 3 artifact shapes where possible so session evidence
  remains coherent across backends.
- If MathCode proves too interactive for a clean CLI transport in some paths,
  keep the slice open rather than weakening the acceptance criteria or hiding
  backend-specific failures.

## Interfaces and Dependencies

- Depends on the completed formal lifecycle work from plan 27.
- Touches formal backend contracts, local CLI transport code, readiness probes,
  docs, and benchmark cases.
- Depends on a working local MathCode checkout or install, including the
  repo-local binary, AUTOLEAN bundle, and Lean workspace.
