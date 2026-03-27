# Live Runtime Policy

## Purpose / Big Picture

Tune the live harness so generator, verifier, and reviser prompts run with a constrained Hermes runtime policy instead of inheriting the full interactive CLI behavior. The immediate goal is to stop live role calls from wasting time on repo exploration, preserve bounded role-specific timeouts, and let formal verification keep its own Tier 3 timeout budget.

## Branch Strategy

Start from `main` and implement this slice on `codex/live-runtime-policy`. Merge back locally into `main` only after validation passes.

## Commit Plan

- `add live runtime policy plan`
- `tune live role runtime policy`
- `document live runtime policy`

## Progress

- [x] Added the new plan and indexed it from `plans/README.md`.
- [x] Constrained live role calls to a narrow default Hermes toolset when operators do not explicitly request toolsets.
- [x] Stopped live formal transport from inheriting the shorter generator/verifier timeout budget.
- [x] Added tests for the runtime policy and updated repo docs.
- [x] Re-ran live smokes to confirm the changed runtime behavior.

## Surprises & Discoveries

- A 60-second live eval on the current default Hermes route still timed out in the generator when the role runner inherited the global CLI tool policy, and the transcript showed repo exploration attempts instead of direct answer generation.
- Forcing `--toolsets clarify` on the live role call removed the repo-reading behavior and let the generator finish within 60 seconds on the same route, which shows the inherited tool policy is a real latency contributor.
- The verifier still timed out at 60 seconds under the restricted toolset, which points to a second lever: role-specific timeout policy rather than a single flat bound for every live step.
- The formal verifier currently receives the same `command_timeout_seconds` override as the live role runner, which clips Tier 3 transport to the same shorter budget even though the formal request already carries its own timeout.
- Once generator and verifier started completing under the new runtime policy, the live path exposed a latent Tier 2 robustness bug: malformed verifier `simulation_spec` payloads crashed the orchestrator with `KeyError` instead of producing structured simulation errors. This slice now converts those malformed specs into normalized simulation-error artifacts.

## Decision Log

- Decision: keep the public surface small and implement the new behavior as a repo-local runtime policy, not a broad config-schema expansion.
  Rationale: the failure mode is in the live execution boundary, and the harness can fix it without introducing another config contract.
  Date/Author: 2026-03-27 / Codex
- Decision: apply the constrained default toolset only to generator, verifier, and reviser calls.
  Rationale: Tier 3 formal transport legitimately needs Aristotle/MCP access, so it should not inherit the same restriction.
  Date/Author: 2026-03-27 / Codex
- Decision: let formal transport fall back to the Tier 3 request timeout unless an explicit formal command timeout is added later.
  Rationale: the existing live role timeout flag is documented as a per-role Hermes timeout, not as a proof-budget override.
  Date/Author: 2026-03-27 / Codex

## Outcomes & Retrospective

This slice leaves the repo with a more realistic live runtime policy: role prompts default to a constrained Hermes tool surface, verifier/formal steps are no longer forced into the same short timeout budget as generation, and malformed Tier 2 specs now degrade into structured simulation errors instead of a crash. In the recorded live smoke at `/tmp/deep-gvr-live-runtime-policy-2`, generator and verifier both completed under the default policy, the transcript showed `--toolsets clarify` rather than repo exploration, and the run ended with a normal verifier verdict (`FLAWS_FOUND`) instead of a timeout/crash. That moves the remaining live-quality gap back to prompt/model quality rather than harness control flow.

## Context and Orientation

The repo already has:

- Live benchmark execution in `src/deep_gvr/evaluation.py` and `eval/run_eval.py`
- Live CLI session execution in `src/deep_gvr/cli.py`
- Aristotle transport in `src/deep_gvr/formal.py`
- Compact prompt scaffolding and route tuning from the previous slices

What is still missing is a runtime policy that keeps live role calls focused on JSON generation and verification instead of inheriting Hermes interactive-tool behavior.

## Plan of Work

Add a shared live runtime policy helper, use it to constrain live role toolsets and timeouts, stop overriding the formal verifier with the shorter live role timeout, update tests and docs, and re-run narrow live smokes to confirm the changed behavior.

## Concrete Steps

1. Add this plan to `plans/` and index it from `plans/README.md`.
2. Introduce a repo-local helper for default live role toolsets and role-specific timeout behavior.
3. Apply that policy in `src/deep_gvr/evaluation.py` for generator, verifier, and reviser Hermes calls.
4. Apply the same policy in `src/deep_gvr/cli.py` so live CLI runs and eval runs behave consistently.
5. Update formal-verifier construction so Tier 3 transport uses its own request timeout instead of inheriting the shorter live role timeout override.
6. Add tests that prove the restricted default toolset is applied when operators do not explicitly provide toolsets, that explicit toolsets still win, and that formal transport no longer inherits the live role timeout override.
7. Update `README.md`, `SKILL.md`, `eval/README.md`, and the plan with the new runtime policy.
8. Re-run a narrow live eval smoke and inspect transcripts to confirm the generator no longer attempts repo exploration under the default runtime policy.

## Validation and Acceptance

- `python scripts/check_repo.py`
- `python scripts/run_capability_probes.py`
- `python -m unittest discover -s tests -v`
- `python eval/run_eval.py --mode live --routing-probe fallback --case-id known-correct-surface-threshold --prompt-profile compact --command-timeout-seconds 60 --output-root /tmp/deep-gvr-live-runtime-policy`

Acceptance:

- Live generator/verifier/reviser calls default to the constrained runtime policy when no explicit toolsets are supplied.
- Explicit operator toolset choices still override the default runtime policy.
- Formal verification is no longer clipped to the shorter live role timeout override.
- Docs explain the constrained live runtime policy and the remaining timeout lever.

## Merge, Push, and Cleanup

Merge locally only after validation passes. Validate the merged result again, push the integrated branch, confirm CI, and delete `codex/live-runtime-policy` when it is no longer needed.

## Idempotence and Recovery

The runtime policy should be safe to rerun: operators can still override toolsets explicitly, and live evidence artifacts should remain structurally identical. If the constrained runtime policy still times out, the next lever remains route choice or longer role-specific timeout budgets rather than another harness rewrite.

## Interfaces and Dependencies

Primary paths: `src/deep_gvr/evaluation.py`, `src/deep_gvr/cli.py`, `src/deep_gvr/formal.py`, `tests/test_evaluation.py`, `tests/test_cli.py`, `README.md`, `SKILL.md`, `eval/README.md`, and `plans/README.md`.
