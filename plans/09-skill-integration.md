# Skill Command Integration

## Purpose / Big Picture

Turn the current `SKILL.md` scaffold into a runnable command boundary by adding a repo-local `deep-gvr` entrypoint that can start and resume sessions with the existing Tier 1/2/3 harness, load config from the documented Hermes path, and emit operator-friendly summaries that line up with the skill contract.

## Branch Strategy

Start from `main` and implement this slice on `codex/skill-integration`. Merge back locally into `main` only after validation passes.

## Commit Plan

- `add skill integration plan`
- `add deep gvr command runner`
- `document skill command workflow`

## Progress

- [x] The plan for skill integration has been added.
- [x] The repo now has a runnable `deep-gvr` command surface for starting or resuming sessions.
- [x] Config at `~/.hermes/deep-gvr/config.yaml` is loaded by the repo-local command helper, with default creation when missing.
- [x] The skill procedure and install flow now point to a concrete command runner.

## Surprises & Discoveries

- The repo already has a complete Python orchestration loop in `src/deep_gvr/tier1.py`, so the missing work is the operator-facing command boundary rather than the loop internals.
- `hermes chat` is already used safely by the live evaluation harness, which provides the natural role-execution boundary for the skill command surface.
- The documented config path is YAML, but the repo currently only has JSON templates and no YAML loader.
- Re-exporting the CLI module from `deep_gvr.__init__` causes noisy `runpy` warnings for `python -m deep_gvr.cli`, so the command module should stay separate from the package convenience exports.

## Decision Log

- Decision: implement a repo-local Python command surface instead of trying to patch Hermes itself.
  Rationale: the repo rules explicitly require the skill to work without modifying Hermes internals.
  Date/Author: 2026-03-26 / Codex
- Decision: keep the command surface thin by reusing the existing Tier 1 loop, routing plan, evidence store, and Hermes prompt runner machinery.
  Rationale: skill integration should expose the existing harness, not fork a second orchestration stack.
  Date/Author: 2026-03-26 / Codex
- Decision: load the documented YAML config path directly and create a default config file during install when it does not yet exist.
  Rationale: the public surface already promises `~/.hermes/deep-gvr/config.yaml`, so the runnable command should honor that contract.
  Date/Author: 2026-03-26 / Codex

## Outcomes & Retrospective

The repo now has a real session command boundary instead of a skill-only promise: `uv run deep-gvr run ...` and `uv run deep-gvr resume ...` load the documented config path, reuse the existing harness, and persist role transcripts as session artifacts. Install now creates a usable default config without overwriting an existing one, and the docs/tests/checks all point at the same command surface.

## Context and Orientation

The repo now has a functioning loop runner, routing logic, Stim mediation, Aristotle fallback handling, and deterministic/live evaluation support. What it still lacks is the user-facing command path that makes `/deep-gvr` more than a documentation promise.

This plan covers the first runnable skill command surface: config loading, domain context loading, session start/resume commands, install-time defaults, and the repo-local docs/tests that make the boundary maintainable.

## Plan of Work

Add a Python CLI entrypoint for `deep-gvr`, backed by the existing harness, then update install/docs/tests so the skill scaffold, config path, and command usage all describe the same concrete workflow.

## Concrete Steps

1. Add a new runtime module for command handling, config loading, and domain-context loading.
2. Expose a runnable CLI entrypoint for `deep-gvr` with new-session and resume commands.
3. Reuse the existing Hermes prompt runner for generator, verifier, and reviser execution so the command path matches live evaluation behavior.
4. Ensure the command surface writes evidence to the configured session directory and prints session/result summaries plus artifact paths.
5. Update `scripts/install.sh` to create the documented config directory and a default `config.yaml` when missing.
6. Add tests for config loading, command execution with injected role executors, install defaults, and resume behavior.
7. Update `SKILL.md`, `README.md`, and local docs so the skill contract and operator workflow match the implemented command surface.

## Validation and Acceptance

- `python scripts/check_repo.py`
- `python scripts/run_capability_probes.py`
- `python -m unittest discover -s tests -v`
- `python -m deep_gvr.cli --help`
- `python -m deep_gvr.cli run "Explain why the surface code has a threshold." --command-timeout-seconds 5`

Acceptance:
- The repo exposes a runnable `deep-gvr` command surface for session start and resume.
- The command surface loads the documented config path and domain context without hidden setup.
- Install flow creates a usable default config when one does not already exist.
- Docs and tests describe the same command, config, and artifact behavior that the runtime implements.

## Merge, Push, and Cleanup

Merge locally only after validation passes. Validate the merged result again, push the integrated branch, confirm CI, and delete `codex/skill-integration` when it is no longer needed.

## Idempotence and Recovery

Repeated installs must not clobber an existing config unless explicitly forced. Re-running a start command should create a new session unless a specific session ID is provided. Resume must continue from the last complete checkpoint and preserve prior evidence artifacts.

## Interfaces and Dependencies

Primary paths: `SKILL.md`, `README.md`, `scripts/install.sh`, `src/deep_gvr/`, `domain/`, `tests/`, and the existing prompts plus Tier 1 loop helpers.
