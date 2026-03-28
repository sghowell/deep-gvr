# deep-gvr

`deep-gvr` is an agent-first research harness for Hermes Agent that implements a generator-verifier-reviser loop with tiered verification.

The repository is intentionally structured for Codex-driven implementation. The current state is a working baseline: contracts, prompts, schemas, capability probes, execution plans, repository guardrails, a runnable `deep-gvr` command surface with checkpointed resume semantics, a working local Stim/PyMatching Tier 2 path, and orchestrator-mediated Tier 3 formal verification through Hermes MCP when Aristotle is configured, with structured fallback when it is not.
Target-state alignment is tracked in [docs/architecture-status.md](docs/architecture-status.md); current substitutions are temporary gaps with owning retirement slices, not the intended long-term surface.

## What Exists Now

- Agent operating rules in [AGENTS.md](AGENTS.md)
- Execution plan standard in [PLANS.md](PLANS.md)
- Contributor workflow in [CONTRIBUTING.md](CONTRIBUTING.md)
- Indexed design docs in [docs/README.md](docs/README.md)
- Typed Python contracts in `src/deep_gvr/`
- Tier 1 loop helpers and session persistence in `src/deep_gvr/tier1.py`
- Local Stim/PyMatching empirical verification in `adapters/stim_adapter.py`
- Orchestrator-mediated Aristotle Tier 3 transport and fallback logic in `src/deep_gvr/formal.py`
- JSON schemas in `schemas/`
- Prompt and skill procedure in `prompts/` and `SKILL.md`
- Capability probes and validation scripts in `scripts/`
- Runnable CLI surface in `src/deep_gvr/cli.py`
- Initial implementation backlog in `plans/`
- Deterministic benchmark runner and recorded release baseline in `eval/`

## Temporary Architecture Gaps

- `hermes-native-orchestrator`: the supported runtime still executes role prompts through separate top-level `hermes chat` calls instead of Hermes-native delegated role execution. Retirement slice: [plans/25-hermes-native-orchestrator.md](plans/25-hermes-native-orchestrator.md)
- `subagent-capability-closure`: per-subagent routing and verifier-side MCP access are still not real supported runtime capabilities. Retirement slice: [plans/26-subagent-capability-closure.md](plans/26-subagent-capability-closure.md)
- `formal-proof-lifecycle`: Tier 3 is still a bounded proof attempt rather than a full submission, polling, and resume lifecycle. Retirement slice: [plans/27-formal-proof-lifecycle.md](plans/27-formal-proof-lifecycle.md)
- `remote-backend-completion`: Tier 2 is still local-first; Modal and SSH remain incomplete runtime paths. Retirement slice: [plans/28-remote-backend-completion.md](plans/28-remote-backend-completion.md)
- `evidence-system-completion`: evidence is still file-backed only; Hermes memory persistence and Parallax compatibility remain to be implemented. Retirement slice: [plans/29-evidence-system-completion.md](plans/29-evidence-system-completion.md)

## Intended Public Surface

- `/deep-gvr <question>` starts a research run
- `/deep-gvr resume <session_id>` resumes a prior run
- Config lives at `~/.hermes/deep-gvr/config.yaml`
- Evidence lives under `~/.hermes/deep-gvr/sessions/<session_id>/`
- Resume checkpoints live at `~/.hermes/deep-gvr/sessions/<session_id>/checkpoint.json`

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
uv run deep-gvr init-config
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
scripts/setup_mcp.sh --install --check
```

`scripts/install.sh` creates a symlink install under `~/.hermes/skills/deep-gvr` by default. Use `--copy` if you need a copied install or `--target` to choose a different skills directory.

The install helper now also creates `~/.hermes/deep-gvr/config.yaml` from the repo defaults when that file does not already exist.
For Tier 3, `scripts/setup_mcp.sh --install` adds the expected `mcp_servers.aristotle` block to `~/.hermes/config.yaml` without duplicating an existing entry, `scripts/setup_mcp.sh --check` verifies the key plus the Hermes MCP config entry, and `scripts/setup_mcp.sh --print-snippet` prints the same block without modifying the config.

## Command Surface

The repo now exposes a console command through `uv run deep-gvr`:

```bash
uv run deep-gvr --help
uv run deep-gvr run "Explain why the surface code has a threshold."
uv run deep-gvr run "Explain why the surface code has a threshold." --prompt-profile full
uv run deep-gvr resume <session_id>
```

The command loads `~/.hermes/deep-gvr/config.yaml`, injects domain context from `domain/`, runs the existing generator-verifier-reviser loop, and writes evidence to the configured session directory.
Live Hermes calls now use the `compact` prompt profile by default to reduce query size; use `--prompt-profile full` when you need the more verbose scaffolding for debugging prompt behavior.
When `--toolsets` is omitted, live generator/verifier/reviser calls now force a narrow Hermes tool surface instead of inheriting the full interactive CLI tool policy. This keeps role prompts focused on returning contract-shaped JSON rather than exploring the repo by default. Pass `--toolsets ...` when you explicitly want a broader live tool surface.
`--command-timeout-seconds` is now the base live role timeout. The verifier may receive a higher repo-local floor, while Tier 3 formal transport keeps using the configured proof timeout instead of inheriting the shorter live role bound.
If Aristotle transport is configured in `~/.hermes/config.yaml`, Tier 3 requests are dispatched through `hermes chat` plus the discovered `mcp_aristotle_*` tools and the session records a `formal_transport` artifact alongside the formal request/results artifacts.

## Evaluation Baseline

The release baseline uses the deterministic fixture-backed benchmark suite in `eval/known_problems.json`. The committed CI-safe baseline result is `eval/results/baseline_results.json`, generated with `--routing-probe fallback` to match the documented current routing baseline.

The same runner now also supports live prompt-driven execution through `hermes chat`. A live smoke run writes a timestamped artifact directory under `eval/results/live/` and leaves the committed deterministic baseline untouched:

```bash
uv run python eval/run_eval.py --list-subsets
uv run python eval/run_eval.py --mode live --routing-probe fallback --case-id known-correct-surface-threshold
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --case-id known-correct-surface-threshold
uv run python eval/run_eval.py --mode live --routing-probe fallback --case-id known-correct-surface-threshold --prompt-profile full
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --subset live-expansion --prompt-profile compact
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --subset live-expansion --prompt-profile compact --repeat 2
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --subset live-analytical-breadth --prompt-profile compact
uv run python eval/run_eval.py --mode live --config ~/.hermes/deep-gvr/config.yaml --routing-probe fallback --subset live-escalation-breadth --prompt-profile compact --command-timeout-seconds 120
```

Live runs record `report.json`, per-case candidate and verification artifacts, role transcripts, and the session evidence/checkpoint files used by the Tier 1 loop. The live eval path now accepts `--config`, uses the same repo-local route settings as `uv run deep-gvr`, and injects the same domain context files that the CLI uses. Compact live verification also uses a dedicated compact verifier prompt/path to keep the verifier request smaller on the real Hermes route, and literature-grounded threshold explanations plus pure asymptotic-counting claims now stay on the Tier 1 path unless the candidate adds a genuinely new empirical or formal obligation. See [eval/README.md](eval/README.md) for the full workflow and artifact layout.
When `--repeat` is greater than `1`, the runner writes per-run reports under `<output-root>/runs/run-###/report.json` and an aggregate `consistency_report.json` at the root so stability can be measured directly instead of inferred from ad hoc reruns.
Live eval also uses the constrained default live runtime policy when `--toolsets` is omitted, so generator/verifier/reviser runs do not inherit the full Hermes CLI tool surface by default.
When a live config sets a non-default provider or a concrete model for `models.generator`, `models.verifier`, or `models.reviser`, live CLI/eval runs now treat that as explicit top-level route intent and fall back to the shared live route if Hermes returns a route-configuration error for the explicit provider/model path.
The shared QEC domain anchors and generator prompt now also push live depolarizing-threshold answers to keep the main claim on the circuit-level surface-code regime, reserve `~10.9%` for the Nishimori-point bit-flip result, and prefer Fowler/Stephens for the sub-1% MWPM range.
Live Tier 2 mediation now normalizes common verifier noise-model aliases such as `uniform_depolarizing` or `iid_depolarizing` to the canonical Stim value `depolarizing`, caps live requests at `shots_per_point <= 100000` and `max_parallel <= 4`, and gives the verifier a longer follow-up timeout floor once Tier 2 or Tier 3 evidence is attached.
Live benchmark case results now record whether the strict verdict matched, whether an accepted refutation counted as success, whether the expected tiers were exercised, and an explicit `outcome` such as `direct_match`, `accepted_refutation`, `tier_mismatch`, `verdict_mismatch`, or `execution_error`.
For simulation-testable quantitative claims that name concrete distances, error rates, decoders, or threshold behavior and do not yet carry `simulation_results`, the live verifier guidance now defaults to requesting Tier 2 instead of letting Tier 1 plausibility settle the case.
For live known-incorrect benchmark cases, the runner now also treats a verified direct refutation as success instead of requiring the generator to role-play a false claim.
Simulation-backed rejected benchmark claims can now also pass as accepted refutations when the live run clearly disproves the target claim.
For compact theorem claims, the live verifier now keeps proof-oriented cases on Tier 3 and returns `CANNOT_VERIFY` when the core theorem claim only has failed Tier 3 results.
The current representative stability gate is still `--subset live-expansion --repeat 2`; plan 21 recorded a clean `2/2` repeated sweep at `/tmp/deep-gvr-live-suite-hardening-final/consistency_report.json`. The new `live-analytical-breadth`, `live-escalation-breadth`, and `live-full` subsets are broader coverage sweeps rather than the fast repeated gate. Plan 23 removed the prior analytical tier-mismatch and timeout mix, but the repeated `live-analytical-breadth` sweep is currently blocked on this machine by a Hermes provider-auth failure (`nous/claude-opus-4-6` returning HTTP 401), not by repo-local prompt or routing logic. Retirement slice for the runtime-side delegated and routing closure: [plans/25-hermes-native-orchestrator.md](plans/25-hermes-native-orchestrator.md) and [plans/26-subagent-capability-closure.md](plans/26-subagent-capability-closure.md)

## Reference Docs

- [docs/README.md](docs/README.md)
- [docs/deep-gvr-architecture.md](docs/deep-gvr-architecture.md)
- [eval/README.md](eval/README.md)
- [plans/README.md](plans/README.md)
