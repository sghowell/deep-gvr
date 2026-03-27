# Aristotle Transport Integration

## Purpose / Big Picture

Turn Tier 3 from a structured fallback boundary into a real orchestrator-mediated Aristotle transport path by wiring formal verification through the current Hermes CLI and MCP configuration, while preserving explicit unavailability and timeout behavior when the environment is not ready.

## Branch Strategy

Start from `main` and implement this slice on `codex/aristotle-transport`. Merge back locally into `main` only after validation passes.

## Commit Plan

- `add aristotle transport plan`
- `wire hermes mcp formal transport`
- `document aristotle transport workflow`

## Progress

- [x] The new Aristotle transport plan has been added.
- [ ] A real repo-local Tier 3 transport path is wired through Hermes CLI and the configured Aristotle MCP server.
- [ ] Capability probes distinguish subagent MCP inheritance from orchestrator-mediated Aristotle transport readiness.
- [ ] Tier 3 docs, setup guidance, tests, and live evaluation notes match the implemented transport behavior.

## Surprises & Discoveries

- The current Hermes CLI in this environment does not expose `hermes mcp ...`; MCP configuration is driven through `~/.hermes/config.yaml` plus native tool discovery.
- `ARISTOTLE_API_KEY` is present in the environment here, but Hermes currently has no configured Aristotle MCP server, so the existing Tier 3 path still degrades to `unavailable`.
- The repo already has a stable orchestrator-mediated Tier 3 seam in `src/deep_gvr/formal.py` and `src/deep_gvr/tier1.py`, which means this slice is an integration upgrade rather than a control-flow redesign.

## Decision Log

- Decision: keep Tier 3 orchestrator-mediated even after transport is real.
  Rationale: the current probe still treats subagent MCP inheritance as unverified, so direct verifier-side tool use remains a separate capability question.
  Date/Author: 2026-03-26 / Codex
- Decision: target Hermes native MCP configuration in `~/.hermes/config.yaml` rather than the stale `hermes mcp add` workflow.
  Rationale: the local Hermes installation already uses `mcp_servers` configuration and auto-discovered `mcp_<server>_<tool>` tools.
  Date/Author: 2026-03-26 / Codex
- Decision: keep graceful structured fallback when the Aristotle server is not configured or the formal command fails.
  Rationale: Tier 3 remains optional and must degrade into artifacts, not hangs or invented proof success.
  Date/Author: 2026-03-26 / Codex

## Outcomes & Retrospective

This slice should leave the repo with a real formal transport path for configured Aristotle environments, clearer capability reporting for transport readiness versus subagent inheritance, and operator docs/scripts that describe the current Hermes MCP setup model accurately.

## Context and Orientation

The repo already has:

- Tier 1 loop orchestration and artifact persistence in `src/deep_gvr/tier1.py`
- A formal-verification seam in `src/deep_gvr/formal.py`
- Live prompt execution utilities in `src/deep_gvr/evaluation.py`
- A skill/CLI surface in `src/deep_gvr/cli.py`
- Probe reporting in `src/deep_gvr/probes.py`
- Tier 3 setup guidance in `scripts/setup_mcp.sh`, `SKILL.md`, and docs

What is still missing is a real default transport for Aristotle. Today the default formal verifier still returns `unavailable` when credentials exist but no repo-local transport is wired.

## Plan of Work

Add a Hermes-CLI-backed Aristotle transport implementation, expose transport readiness through capability probes, persist transport artifacts in Tier 3 mediation, and update setup/docs/tests to match the actual Hermes MCP configuration model.

## Concrete Steps

1. Add the new plan to `plans/` and index it from `plans/README.md`.
2. Implement a real default Aristotle transport path in `src/deep_gvr/formal.py` using the current Hermes CLI plus a formal-verification prompt.
3. Persist transport transcript artifacts alongside the existing Tier 3 request/results artifacts in `src/deep_gvr/tier1.py`.
4. Add a distinct Aristotle transport readiness probe in `src/deep_gvr/probes.py` without changing the existing subagent-inheritance fallback semantics.
5. Update `scripts/setup_mcp.sh` to check and describe the actual `mcp_servers`-based Hermes configuration shape.
6. Add tests for configured transport, missing transport, timeout mapping, transcript artifact persistence, and probe readiness/fallback behavior.
7. Update `README.md`, `SKILL.md`, `docs/system-overview.md`, `docs/capability-probes.md`, `docs/contracts-and-artifacts.md`, and `plans/README.md`.

## Validation and Acceptance

- `python scripts/check_repo.py`
- `python scripts/run_capability_probes.py`
- `python -m unittest discover -s tests -v`
- `python scripts/setup_mcp.sh --check`
- `python eval/run_eval.py --mode live --routing-probe fallback --case-id formal-unavailable-repetition-scaling --command-timeout-seconds 5`

Acceptance:

- Tier 3 has a real default transport path instead of unconditional structured unavailability.
- The harness persists Tier 3 transport artifacts that explain what was attempted.
- Capability probes distinguish Aristotle transport readiness from subagent MCP inheritance.
- Setup/docs describe the actual Hermes MCP configuration path and current limitations.

## Merge, Push, and Cleanup

Merge locally only after validation passes. Validate the merged result again, push the integrated branch, confirm CI, and delete `codex/aristotle-transport` when it is no longer needed.

## Idempotence and Recovery

Repeated Tier 3 attempts must preserve append-only evidence and write new transport artifacts instead of overwriting prior runs. Missing or misconfigured Aristotle transport must fail into structured `unavailable` results that can be retried after the Hermes MCP config is corrected.

## Interfaces and Dependencies

Primary paths: `src/deep_gvr/formal.py`, `src/deep_gvr/tier1.py`, `src/deep_gvr/probes.py`, `src/deep_gvr/cli.py`, `src/deep_gvr/evaluation.py`, `scripts/setup_mcp.sh`, `prompts/`, `tests/`, and the operator docs in `README.md`, `SKILL.md`, and `docs/`.
