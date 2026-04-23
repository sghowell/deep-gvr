# Changelog

This project follows a Keep a Changelog style release history. Public releases are cut from tagged repo states, and the tagged version must match the checked-in project metadata.

## [Unreleased]

No unreleased changes are queued yet.

## [0.1.0] - 2026-04-22

### Added

- The public `deep-gvr` release surface, including install, preflight, release publication metadata, and a GitHub Releases plus agentskills.io distribution model.
- A hosted public documentation surface built from the repo’s human-facing docs set.
- Structured release automation for changelog-derived release notes and tagged GitHub releases.
- Tiered verification support across analytical review, OSS-backed analysis adapters, and formal backends including Aristotle, MathCode, and OpenGauss.
- A full Tier 2 OSS analysis portfolio with nine shipped adapter families and a validated `uv sync --all-extras` operator path.
- A full Codex surface, including Codex local, plugin, automations, review/QA, subagent, and SSH/devbox operator bundles plus the native `codex_local` backend.
- Backend parity across the shipped `hermes` and `codex_local` orchestrator backends for the full repo-owned contract.
- An isolated `auto_improve` evaluation harness and explicit public release policy for keeping `auto_improve: false` by default.

### Notes

- `deep-gvr` ships as a Hermes skill bundle plus Codex-local surfaces, with `auto_improve: false` by default.
- Aristotle remains the long-running submission/poll/resume Tier 3 path; MathCode and OpenGauss ship as bounded local CLI formal backends.
