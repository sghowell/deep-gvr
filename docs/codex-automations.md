# Codex Automations

This page covers the shipped Codex automation pack for `deep-gvr`.

The automation surface is intentionally narrow. The repo ships a reviewable set of recurring-work templates and export helpers for Codex; it does not claim to register live automations inside Codex's app-managed runtime state.

## What the Repo Ships

The checked-in automation pack lives at:

- `codex_automations/catalog.json`
- `codex_automations/templates/benchmark_subset_sweep.automation.toml`
- `codex_automations/templates/ci_failure_triage.automation.toml`
- `codex_automations/templates/release_candidate_sweep.automation.toml`
- `codex_automations/templates/docs_surface_smoke.automation.toml`

These templates cover four recurring workflows:

- deterministic benchmark subset sweeps
- GitHub Actions failure triage
- release-candidate readiness sweeps
- public-docs smoke checks

The repo also ships two export paths:

- `python scripts/export_codex_automations.py --output-root <dir>`
- `bash scripts/install_codex.sh --automation-root <dir>`

## Current Boundary

The shipped automation pack is:

- versioned in the repo
- validated by repo checks and release preflight
- exportable with the current checkout path substituted into the automation working-directory fields

It is not:

- a second runtime backend
- a replacement for Hermes as the shipped delegated execution backend
- a claim that the repo can directly create active Codex jobs in the app for you

Codex keeps live automation state inside the product. The repo therefore ships templates and an export helper, not direct registration into `~/.codex/automations`.

## Export the Automation Pack

Minimal export:

```bash
python scripts/export_codex_automations.py --output-root /tmp/deep-gvr-codex-automations
```

If you are already installing the Codex-local surface, you can export the automation pack at the same time:

```bash
bash scripts/install_codex.sh --automation-root /tmp/deep-gvr-codex-automations
```

Both commands produce an export bundle containing:

- `catalog.json`
- `automations/<id>/automation.toml`

Those exported TOML files have the current checkout path materialized into their `cwds` field so the bundle is ready for operator review.

## Included Templates

### Benchmark Sweep

- Purpose: run deterministic benchmark subsets and report only regressions or new failures
- Schedule template: weekdays at 9:00 AM
- Model profile: `gpt-5.3-codex` with `high` reasoning effort

### CI Failure Triage

- Purpose: inspect the newest CI or Docs run and summarize only actionable failures
- Schedule template: every 6 hours on weekdays
- Model profile: `gpt-5.3-codex` with `medium` reasoning effort

### Release Sweep

- Purpose: run the release-critical validation path and summarize blockers for cutting the next tag
- Schedule template: Fridays at 10:00 AM
- Model profile: `gpt-5.3-codex` with `high` reasoning effort

### Docs Smoke

- Purpose: run the hosted-docs safety path and summarize public-doc regressions
- Schedule template: daily
- Model profile: `gpt-5.3-codex` with `medium` reasoning effort

## Operator Guidance

- The checked-in templates ship with `status = "PAUSED"` on purpose.
- Review the exported prompts, schedules, and working directories before activating anything in Codex.
- Treat the templates as a starting point for your workspace, not as immutable universal schedules.

If you only want the interactive Codex surface, see [Codex Local](codex-local.md) and [Codex Plugin](codex-plugin.md). If you want a non-scheduled Codex review and visual-QA prompt pack, see [Codex Review and Visual QA](codex-review-qa.md).
