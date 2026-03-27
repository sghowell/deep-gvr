# Aristotle Transport Activation

## Purpose / Big Picture

Turn the newly implemented Tier 3 transport from a repo-local capability into a real activated environment by making Aristotle MCP setup repeatable, flipping the local transport probe to `ready`, and exercising at least one live formal case through the actual Hermes configuration.

## Branch Strategy

Start from `main` and implement this slice on `codex/transport-activation`. Merge back locally into `main` only after validation passes.

## Commit Plan

- `add transport activation plan`
- `automate aristotle mcp activation`
- `document transport activation workflow`

## Progress

- [x] The new transport-activation plan has been added.
- [ ] The setup helper can install the Aristotle MCP stanza into a Hermes config idempotently.
- [ ] The local Hermes config is activated for Aristotle transport and the transport probe reports `ready`.
- [ ] A bounded live formal run produces transport artifacts from the real configured environment.
- [ ] Docs, tests, and the plan index match the activation workflow.

## Surprises & Discoveries

- The current Hermes config already has the right model/tool defaults for local work, but it does not yet define `mcp_servers`, so Tier 3 still falls back even with `ARISTOTLE_API_KEY` present.
- The existing repo-local setup guidance is accurate, but it still relies on a manual config edit; that is the last avoidable operator step in the Tier 3 path.

## Decision Log

- Decision: treat activation as a tracked implementation slice instead of a one-off local tweak.
  Rationale: the repo guidance explicitly prefers encoded repeatable rules over undocumented operator folklore.
  Date/Author: 2026-03-26 / Codex
- Decision: acceptance requires a real live transport attempt, not just a static config check.
  Rationale: the goal is to prove the harness can dispatch through Hermes MCP in this environment, not merely render a plausible config file.
  Date/Author: 2026-03-26 / Codex

## Outcomes & Retrospective

This slice should leave the repo with a repeatable Aristotle activation helper, updated operator guidance, a locally verified `aristotle_transport` probe, and at least one live formal artifact set that reflects the real configured environment.

## Context and Orientation

The repo already has:

- A real Tier 3 transport path in `src/deep_gvr/formal.py`
- Tier 3 artifact persistence in `src/deep_gvr/tier1.py`
- Capability reporting in `src/deep_gvr/probes.py`
- Tier 3 setup guidance in `scripts/setup_mcp.sh`, `README.md`, `SKILL.md`, and docs
- Live execution paths in `src/deep_gvr/cli.py` and `eval/run_eval.py`

What is still missing is a repeatable activation workflow and a real environment run that proves the transport is functioning from the local Hermes installation.

## Plan of Work

Add an idempotent Aristotle MCP installer path to the setup helper, activate the real local Hermes config through that helper, rerun the transport probes, and execute a bounded live formal benchmark to capture real Tier 3 transport artifacts.

## Concrete Steps

1. Add the new plan to `plans/` and index it from `plans/README.md`.
2. Extend `scripts/setup_mcp.sh` so it can install the expected `mcp_servers.aristotle` stanza into a target Hermes config without duplicating existing config.
3. Add release-script coverage for install, idempotent re-install, and existing check behavior.
4. Update `README.md`, `SKILL.md`, `docs/capability-probes.md`, and `eval/README.md` so the operator path is `--install`, then `--check`, then live run verification.
5. Use the setup helper against the real `~/.hermes/config.yaml`, rerun `scripts/run_capability_probes.py`, and verify that `aristotle_transport` moves to `ready`.
6. Run a bounded live formal evaluation case and inspect the resulting `formal_transport` and `formal_results` artifacts.
7. Record the activation outcome in this plan and leave the repo docs aligned with the observed behavior.

## Validation and Acceptance

- `python scripts/check_repo.py`
- `python scripts/run_capability_probes.py`
- `python -m unittest discover -s tests -v`
- `bash scripts/setup_mcp.sh --install --check`
- `python eval/run_eval.py --mode live --routing-probe fallback --case-id formal-proved-repetition-majority --command-timeout-seconds 10`

Acceptance:

- `scripts/setup_mcp.sh --install` is idempotent and can create the expected Aristotle MCP entry in a target config.
- The real local Hermes environment reports `aristotle_transport: ready`.
- A live formal run produces Tier 3 transport artifacts from an attempted configured transport path, not the `missing_mcp_server` fallback.
- Docs and tests describe the actual activation workflow.

## Merge, Push, and Cleanup

Merge locally only after validation passes. Validate the merged result again, push the integrated branch, confirm CI, and delete `codex/transport-activation` when it is no longer needed.

## Idempotence and Recovery

Repeated setup runs must not duplicate the Aristotle config entry. If the live formal run times out or the remote proof backend errors, the session must still persist a transport artifact that shows the attempted configured path so the operator can distinguish transport activation from proof success.

## Interfaces and Dependencies

Primary paths: `scripts/setup_mcp.sh`, `tests/test_release_scripts.py`, `src/deep_gvr/probes.py`, `src/deep_gvr/formal.py`, `eval/run_eval.py`, `README.md`, `SKILL.md`, `docs/capability-probes.md`, `eval/README.md`, and the real local Hermes config at `~/.hermes/config.yaml`.
