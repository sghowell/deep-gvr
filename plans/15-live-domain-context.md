# Live Domain Context

## Purpose / Big Picture

Align live benchmark execution with the `deep-gvr` CLI by injecting the same repo-local domain context into live eval runs. The immediate goal is to stop live benchmark prompts from running with an empty `literature_context`, tighten the QEC anchors around noise-model distinctions that the latest live smoke exposed, and make prompt-quality improvements flow through one shared context path instead of diverging between CLI and eval.

## Branch Strategy

Start from `main` and implement this slice on `codex/live-domain-context`. Merge back locally into `main` only after validation passes.

## Commit Plan

- `add live domain context plan`
- `share live domain context loader`
- `document live domain context`

## Progress

- [x] Added the new plan and indexed it from `plans/README.md`.
- [ ] Moved the domain-context loader to a shared module that both CLI and live eval can use.
- [ ] Wired live eval to pass domain and literature context into Tier 1 runs.
- [ ] Tightened the QEC anchors so the shared context explicitly distinguishes code-capacity, phenomenological, and circuit-level threshold regimes.
- [ ] Added tests and docs for the shared live domain-context behavior.
- [ ] Re-ran a narrow live smoke to confirm live transcripts no longer show an empty `literature_context`.

## Surprises & Discoveries

- The CLI already injects `domain/qec_context.md` and `domain/known_results.md`, but live eval calls `Tier1LoopRunner.run(...)` without passing either `domain` or `literature_context`, so the benchmark generator sees an empty context list.
- The latest live smoke at `/tmp/deep-gvr-live-runtime-policy-2` completed generator and verifier successfully, and the generator’s revision notes explicitly admitted that `literature_context` was empty.
- The same smoke’s verifier identified a real content failure: the candidate conflated code-capacity, phenomenological, and circuit-level threshold regimes. That is exactly the kind of stable benchmark anchor that belongs in repo-local domain context rather than in ad hoc chat guidance.

## Decision Log

- Decision: move domain-context loading into a shared module instead of reimplementing it inside evaluation.
  Rationale: CLI and live eval should load the same domain files and apply the same parsing rules, or they will continue to drift.
  Date/Author: 2026-03-27 / Codex
- Decision: encode the threshold-regime distinctions in `domain/known_results.md` rather than inventing benchmark-case-specific prompt hacks.
  Rationale: this is stable scientific guidance for the repo’s current QEC focus area, and future live runs should benefit from it automatically.
  Date/Author: 2026-03-27 / Codex

## Outcomes & Retrospective

This slice should leave the repo with one domain-context path for both the CLI and live eval. Live benchmark runs should carry the same QEC context that the CLI already injects, and the shared anchor notes should reduce avoidable content errors around surface-code threshold regimes and toric-vs-planar scoping.

## Context and Orientation

The repo already has:

- CLI domain-context loading in `src/deep_gvr/cli.py`
- Live benchmark execution in `src/deep_gvr/evaluation.py`
- Repo-local QEC notes in `domain/qec_context.md` and `domain/known_results.md`
- Recent live artifacts showing that the runtime path is working but the benchmark generator still starts from an empty `literature_context`

What is missing is shared context injection between CLI and live eval.

## Plan of Work

Move the domain-context loader into a shared module, use it from both CLI and evaluation, strengthen the QEC benchmark anchors in `domain/known_results.md`, add tests that prove live eval now carries literature context, update docs, and rerun a narrow live smoke.

## Concrete Steps

1. Add this plan to `plans/` and index it from `plans/README.md`.
2. Move the existing domain-context helper out of `src/deep_gvr/cli.py` into a shared module.
3. Update `src/deep_gvr/cli.py` to use the shared helper without changing the public command surface.
4. Update `src/deep_gvr/evaluation.py` so live eval loads the selected domain context from the runtime config and passes both `domain` and `literature_context` into `Tier1LoopRunner.run(...)`.
5. Tighten `domain/known_results.md` so the QEC anchors explicitly distinguish code-capacity, phenomenological, and circuit-level threshold regimes, and warn against toric-specific language when the claim is about surface codes generally.
6. Add tests proving that live eval injects non-empty domain context and that a configured custom context file is reflected in the live generator query.
7. Update `README.md`, `SKILL.md`, `eval/README.md`, `docs/system-overview.md`, and this plan with the shared context behavior.
8. Re-run a narrow live eval smoke and inspect the transcripts for non-empty `literature_context`.

## Validation and Acceptance

- `python scripts/check_repo.py`
- `python scripts/run_capability_probes.py`
- `python -m unittest discover -s tests -v`
- `python eval/run_eval.py --mode live --routing-probe fallback --case-id known-correct-surface-threshold --prompt-profile compact --command-timeout-seconds 60 --output-root /tmp/deep-gvr-live-domain-context`

Acceptance:

- Live eval injects the same domain context path that the CLI uses.
- Live generator queries no longer show an empty `literature_context`.
- Shared QEC anchors encode the threshold-regime distinctions exposed by the latest live smoke.
- Docs describe live eval and CLI as sharing the same domain-context loader.

## Merge, Push, and Cleanup

Merge locally only after validation passes. Validate the merged result again, push the integrated branch, confirm CI, and delete `codex/live-domain-context` when it is no longer needed.

## Idempotence and Recovery

The shared loader should remain safe to rerun because it only changes prompt inputs, not artifact schemas. If live quality still falls short after the shared context is injected, the next lever remains prompt wording or route choice rather than another context-plumbing change.

## Interfaces and Dependencies

Primary paths: `src/deep_gvr/cli.py`, `src/deep_gvr/evaluation.py`, the new shared context module under `src/deep_gvr/`, `domain/qec_context.md`, `domain/known_results.md`, `tests/test_evaluation.py`, `README.md`, `SKILL.md`, `eval/README.md`, `docs/system-overview.md`, and `plans/README.md`.
