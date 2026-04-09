```text
       __                                      
  ____/ /__  ___  ____        ____ __   _______
 / __  / _ \/ _ \/ __ \______/ __ `/ | / / ___/
/ /_/ /  __/  __/ /_/ /_____/ /_/ /| |/ / /    
\__,_/\___/\___/ .___/      \__, / |___/_/     
              /_/          /____/              
```

`deep-gvr` is an agent-first research harness for Hermes Agent that implements a generator-verifier-reviser loop with tiered verification and an OSS-backed analysis-adapter portfolio.

The repository is intentionally structured for Codex-driven implementation. The current state is a working baseline: contracts, prompts, schemas, capability probes, execution plans, repository guardrails, a delegated Hermes skill-orchestrator command surface with checkpointed resume semantics, a checkpoint-safe bounded fan-out and escalation loop, a generalized Tier 2 analysis path with OSS scientific and quantum adapters, and Tier 3 formal verification with persisted proof handles, polling, and resume-aware completion on the shipped harness path.
Target-state alignment is tracked in [docs/architecture-status.md](docs/architecture-status.md); current substitutions are temporary gaps with owning retirement slices, not the intended long-term surface.

## What Exists Now

- Agent operating rules in [AGENTS.md](AGENTS.md)
- Execution plan standard in [PLANS.md](PLANS.md)
- Contributor workflow in [CONTRIBUTING.md](CONTRIBUTING.md)
- Indexed design docs in [docs/README.md](docs/README.md)
- Typed Python contracts in `src/deep_gvr/`
- Tier 1 loop helpers and session persistence in `src/deep_gvr/tier1.py`
- Checkpoint-safe branch fan-out and escalation state in `src/deep_gvr/tier1.py` and `src/deep_gvr/contracts.py`
- Delegated Hermes command boundary in `src/deep_gvr/orchestrator.py`
- OSS analysis adapters in `adapters/`, including symbolic math, optimization, dynamics, QEC benchmarking, MBQC, photonic, neutral-atom, topological-QEC, and ZX rewrite families
- Orchestrator-mediated Aristotle Tier 3 transport and fallback logic in `src/deep_gvr/formal.py`
- JSON schemas in `schemas/`
- Prompt and skill procedure in `prompts/` and `SKILL.md`
- Capability probes and validation scripts in `scripts/`
- Runnable CLI surface in `src/deep_gvr/cli.py`
- Initial implementation backlog in `plans/`
- Deterministic benchmark runner and recorded release baseline in `eval/`

## Temporary Architecture Gaps

- `subagent-capability-closure`: per-subagent routing and verifier-side MCP access are still not real supported runtime capabilities. Retirement slice: [plans/26-subagent-capability-closure.md](plans/26-subagent-capability-closure.md)

## Intended Public Surface

- `/deep-gvr <question>` starts a research run
- `/deep-gvr resume <session_id>` resumes a prior run
- Config lives at `~/.hermes/deep-gvr/config.yaml`
- Evidence lives under `~/.hermes/deep-gvr/sessions/<session_id>/`
- Resume checkpoints live at `~/.hermes/deep-gvr/sessions/<session_id>/checkpoint.json`
- Hermes memory summaries append into `~/.hermes/memories/MEMORY.md` when `persist_to_memory: true`
- A Parallax-compatible export manifest lives at `~/.hermes/deep-gvr/sessions/<session_id>/artifacts/parallax_manifest.json`

## Working Style

This repo follows harness-engineering principles:

- humans provide intent, priorities, and review
- Codex produces code, tests, docs, CI, and repo maintenance artifacts
- repository-local docs and execution plans are the source of truth
- quality rules are enforced in scripts and tests where possible

## Quickstart

The repo is pinned to Python 3.12 and `uv`.

```bash
uv sync
uv sync --extra analysis --extra quantum_oss
uv run deep-gvr init-config
bash scripts/install.sh
uv run python scripts/release_preflight.py --json
uv run deep-gvr run "Explain why the surface code is understood to have a threshold."
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
uv run python eval/run_eval.py --routing-probe fallback --output eval/results/local_results.json
```

If `uv` is not available yet, the local checks can also be run with a Python 3.12 interpreter and `PYTHONPATH=src`.

## Installation

For a local Hermes skill install, use the repo helper:

```bash
scripts/install.sh
uv run python scripts/release_preflight.py --operator --config ~/.hermes/deep-gvr/config.yaml
```

`scripts/install.sh` creates a Hermes-indexable install under `~/.hermes/skills/deep-gvr` by default. If `HERMES_HOME` is set, the helper uses `$HERMES_HOME/skills` plus `$HERMES_HOME/deep-gvr/config.yaml` instead of the default `~/.hermes` paths. In the default `symlink` mode it creates a real skill directory whose contents are symlinked back to the repo, because Hermes does not index a top-level skill directory that is itself a symlink. Use `--copy` if you need a fully copied install or `--target` to choose a different skills directory.

The install helper now also creates `~/.hermes/deep-gvr/config.yaml` from the repo defaults when that file does not already exist.
`scripts/release_preflight.py` is the release-grade operator check for the installed bundle. In default mode it verifies the structural release surface without requiring live provider credentials or Hermes itself, so it is safe for CI and packaging checks. `--operator` raises the bar to actual runtime readiness for the configured path: installed skill bundle, valid config, Hermes CLI presence, explicit provider credentials, selected Tier 2 backend readiness, Tier 3 transport readiness when enabled, checked-in publication manifest, and the shipped `auto_improve: false` policy.
For Tier 3, `scripts/setup_mcp.sh --install` adds the expected `mcp_servers.aristotle` block to `~/.hermes/config.yaml` without duplicating an existing entry, `scripts/setup_mcp.sh --check` verifies the key plus the Hermes MCP config entry, and `scripts/setup_mcp.sh --print-snippet` prints the same block without modifying the config.
If you plan to enable Tier 3 in `~/.hermes/deep-gvr/config.yaml`, run `scripts/setup_mcp.sh --install --check` before the operator preflight.
For Tier 2 remote backends, the runtime config now also carries `verification.tier2.modal.cli_bin`, `verification.tier2.modal.stub_path`, and the SSH fields `host`, `user`, `key_path`, `remote_workspace`, and `python_bin`. Modal readiness depends on the configured CLI plus stub path; SSH readiness depends on `ssh` and `scp` plus a populated remote workspace config.
The optional extras `analysis` and `quantum_oss` install the broader OSS adapter-family dependencies. `scripts/release_preflight.py --operator` now reports `analysis_adapter_families` explicitly so missing local libraries are surfaced as operator-state instead of silent non-support.

## Release Surface

The checked-in publication bundle lives at `release/agentskills.publication.json`. It is validated against `SKILL.md`, `pyproject.toml`, the install/preflight helpers, and the committed deterministic baseline, so it can act as the repo-local source bundle for GitHub and agentskills.io release work.

The release bundle ships with `auto_improve: false`. To opt in, edit `release/agentskills.publication.json` after human review and republish that same validated bundle; do not change the repo default casually.

See [docs/release-workflow.md](docs/release-workflow.md) for the end-to-end install, preflight, and publication flow.

## Command Surface

The repo now exposes a console command through `uv run deep-gvr`:

```bash
uv run deep-gvr --help
uv run deep-gvr run "Explain why the surface code has a threshold."
uv run deep-gvr run "Explain why the surface code has a threshold." --prompt-profile full
uv run deep-gvr resume <session_id>
```

The command now launches one Hermes session preloaded with the installed `deep-gvr` skill, passes the repo-local config/runtime request into that delegated orchestrator, and returns the structured session summary produced by the skill. The wrapper still records a local orchestrator transcript artifact alongside the skill-managed evidence directory, derives `session_memory_summary.json` plus `parallax_manifest.json` under the session artifacts directory, and appends the session summary into `~/.hermes/memories/MEMORY.md` when `persist_to_memory` is enabled.
Because the wrapper preloads `--skills deep-gvr`, the skill must be installed first with `scripts/install.sh`. `uv run deep-gvr init-config` still creates `~/.hermes/deep-gvr/config.yaml`, but it does not install the skill bundle.
`--command-timeout-seconds` is now the delegated orchestrator timeout for the top-level Hermes session. The separate live benchmark harness keeps its own prompt-harness timeout policy.
If Aristotle transport is configured in `~/.hermes/config.yaml`, delegated skill runs can mediate Tier 3 requests through the shipped proof lifecycle and leave `formal_request`, `formal_lifecycle`, `formal_transport`, and `formal_results` artifacts in the session directory.

## Evaluation Baseline

The release baseline uses the deterministic fixture-backed benchmark suite in `eval/known_problems.json`. That corpus now includes core-science analysis cases, OSS quantum analysis cases, and an orchestration-required case that exercises bounded fan-out after repeated primary-branch failure. The committed CI-safe baseline result is `eval/results/baseline_results.json`, generated with `--routing-probe fallback` to match the documented current routing baseline.

The same runner now also supports live prompt-driven execution through the explicit prompt harness in `src/deep_gvr/evaluation.py`. A live smoke run writes a timestamped artifact directory under `eval/results/live/` and leaves the committed deterministic baseline untouched:

```bash
uv run python eval/run_eval.py --list-subsets
uv run python eval/run_eval.py --mode live --routing-probe fallback --case-id known-correct-surface-threshold
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --case-id known-correct-surface-threshold
uv run python eval/run_eval.py --routing-probe fallback --subset core-science --output eval/results/core-science.json
uv run python eval/run_eval.py --routing-probe fallback --subset quantum-oss --output eval/results/quantum-oss.json
uv run python eval/run_eval.py --mode live --routing-probe fallback --case-id known-correct-surface-threshold --prompt-profile full
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --subset live-expansion --prompt-profile compact
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --subset live-expansion --prompt-profile compact --repeat 2
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --subset live-analytical-breadth --prompt-profile compact
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --subset live-escalation-breadth --prompt-profile compact --command-timeout-seconds 120
```

Live runs record `report.json`, per-case candidate and verification artifacts, role transcripts, and the session evidence/checkpoint files used by the Tier 1 loop. The live eval path now accepts `--config`, uses the same repo-local route settings as `uv run deep-gvr`, and injects the same domain context files that the delegated CLI path uses. Compact live verification also uses a dedicated compact verifier prompt/path to keep the verifier request smaller on the real Hermes route, and literature-grounded threshold explanations plus pure asymptotic-counting claims now stay on the Tier 1 path unless the candidate adds a genuinely new empirical or formal obligation. See [eval/README.md](eval/README.md) for the full workflow and artifact layout.
When `--repeat` is greater than `1`, the runner writes per-run reports under `<output-root>/runs/run-###/report.json` and an aggregate `consistency_report.json` at the root so stability can be measured directly instead of inferred from ad hoc reruns.
Live eval also uses the constrained default live runtime policy when `--toolsets` is omitted, so generator/verifier/reviser runs do not inherit the full Hermes CLI tool surface by default.
When a live config sets a non-default provider or a concrete model for `models.generator`, `models.verifier`, or `models.reviser`, live CLI/eval runs now treat that as explicit top-level route intent and fall back to the shared live route if Hermes returns a route-configuration error for the explicit provider/model path.
The shared QEC domain anchors and generator prompt now also push live depolarizing-threshold answers to keep the main claim on the circuit-level surface-code regime, reserve `~10.9%` for the Nishimori-point bit-flip result, and prefer Fowler/Stephens for the sub-1% MWPM range.
Live Tier 2 mediation now normalizes analysis requests into `analysis_spec` and `analysis_results`, records the selected adapter family in evidence, normalizes common verifier noise-model aliases such as `uniform_depolarizing` or `iid_depolarizing` to the canonical Stim value `depolarizing` for QEC tasks, caps live requests at `shots_per_point <= 100000` and `max_parallel <= 4`, and gives the verifier a longer follow-up timeout floor once Tier 2 or Tier 3 evidence is attached.
Live benchmark case results now record whether the strict verdict matched, whether an accepted refutation counted as success, whether the expected tiers were exercised, and an explicit `outcome` such as `direct_match`, `accepted_refutation`, `tier_mismatch`, `verdict_mismatch`, or `execution_error`.
For analysis-testable claims that do not yet carry `analysis_results`, the live verifier guidance now defaults to requesting Tier 2 instead of letting Tier 1 plausibility settle the case.
For live known-incorrect benchmark cases, the runner now also treats a verified direct refutation as success instead of requiring the generator to role-play a false claim.
Simulation-backed rejected benchmark claims can now also pass as accepted refutations when the live run clearly disproves the target claim.
For compact theorem claims, the live verifier now keeps proof-oriented cases on Tier 3 and returns `CANNOT_VERIFY` when the core theorem claim only has failed Tier 3 results.
The current representative stability gate is still `--subset live-expansion --repeat 2`; plan 21 recorded a clean `2/2` repeated sweep at `/tmp/deep-gvr-live-suite-hardening-final/consistency_report.json`. The new `live-analytical-breadth`, `live-escalation-breadth`, and `live-full` subsets are broader coverage sweeps rather than the fast repeated gate. Plan 23 removed the prior analytical tier-mismatch and timeout mix, but the repeated `live-analytical-breadth` sweep is currently blocked on this machine by a Hermes provider-auth failure (`nous/claude-opus-4-6` returning HTTP 401), not by repo-local prompt or routing logic. Retirement slice for the remaining delegated-capability closure: [plans/26-subagent-capability-closure.md](plans/26-subagent-capability-closure.md)

## Reference Docs

- [docs/README.md](docs/README.md)
- [docs/deep-gvr-architecture.md](docs/deep-gvr-architecture.md)
- [eval/README.md](eval/README.md)
- [plans/README.md](plans/README.md)
