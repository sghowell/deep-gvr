# Codex Automations

This directory is the checked-in source of truth for the `deep-gvr` Codex automation pack.

The repo intentionally ships automation templates, not live scheduled jobs. Codex keeps automation run state inside its own app-managed storage, so this directory exists to give operators a reviewable, versioned pack of recurring workflow definitions.

The current pack includes templates for:

- deterministic benchmark subset sweeps
- GitHub Actions failure triage
- release-candidate readiness sweeps
- public-docs smoke checks

Use `python scripts/export_codex_automations.py --output-root <dir>` or `bash scripts/install_codex.sh --automation-root <dir>` to materialize an export bundle with the current checkout path substituted into the automation working-directory fields.
