<p align="center">
  <img src="docs/assets/deep-gvr-hero.svg" alt="deep-gvr hero banner" width="100%" />
</p>

# deep-gvr

[![CI](https://img.shields.io/github/actions/workflow/status/sghowell/deep-gvr/ci.yml?branch=main&label=CI)](https://github.com/sghowell/deep-gvr/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/github/license/sghowell/deep-gvr)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/downloads/release/python-3120/)

`deep-gvr` is a verification-oriented research system for Hermes Agent, Codex local, packaged Codex plugin workflows, Codex automation templates, Codex subagent workflows, Codex SSH/devbox execution, and direct CLI use. It uses a generator-verifier-reviser loop to answer difficult technical questions with explicit analytical, computational, and formal verification.

It is built for people who want more than a polished answer. `deep-gvr` is designed to show its work: what it claimed, how it checked the claim, what evidence it produced, and where it could not verify enough to be confident.

## Why It Exists

Most agent systems optimize for fluency. `deep-gvr` optimizes for adversarial checking.

Its core idea is simple:

- generate a candidate answer
- try to break it with an isolated verifier
- escalate into analysis or formal proof when the claim requires it
- revise, branch, or stop with an explicit failure mode

That makes it useful for research-style questions where correctness matters more than style.

<p align="center">
  <img src="docs/assets/gvr-loop.svg" alt="Generator verifier reviser loop diagram" width="100%" />
</p>

## What You Get

- A structured generator-verifier-reviser workflow
- Three verification tiers:
  - Tier 1 analytical review
  - Tier 2 OSS-backed computational analysis
  - Tier 3 formal verification
- Explicit artifacts: checkpoints, evidence logs, analysis outputs, and proof transport records
- A domain-agnostic adapter architecture with strong support for math, optimization, dynamics, and open-source quantum tooling
- Supported local operator surfaces through Hermes, Codex local, the packaged Codex plugin bundle, a checked-in Codex automation pack, and `uv run deep-gvr`
- An explicit orchestrator-backend boundary in the runtime, with both `hermes` and `codex_local` supported today
- A native Codex backend path that runs Generator, Verifier, and Reviser as separate Codex role calls over the same typed loop

## A Typical Question

```text
/deep-gvr "Explain why the surface code is understood to have a threshold."
```

Codex local can drive the same runtime from a local checkout:

```bash
codex exec -C /path/to/deep-gvr "Use the deep-gvr skill to answer: Explain why the surface code is understood to have a threshold."
```

A successful run typically:

1. grounds itself in known literature and domain context
2. produces a candidate explanation
3. checks the explanation adversarially at Tier 1
4. requests Tier 2 or Tier 3 only if the claim actually needs them
5. writes evidence and artifacts under `${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/sessions/<session_id>/`

## Quick Start

`deep-gvr` is built for Python 3.12 and [`uv`](https://github.com/astral-sh/uv).

```bash
uv sync
uv sync --all-extras
bash scripts/install.sh
uv run python scripts/release_preflight.py --operator --config ${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/config.yaml
uv run deep-gvr run "Explain why the surface code is understood to have a threshold."
```

`uv sync` is the minimal local path. `uv sync --all-extras` is the validated full-portfolio path for the shipped Tier 2 families plus docs/dev tooling. If you only want a narrower Tier 2 subset, you can still use targeted extras such as `uv sync --extra analysis` or `uv sync --extra quantum_oss`.

If you want the Codex-local surface as well:

```bash
bash scripts/install_codex.sh
uv run python scripts/codex_preflight.py --operator
```

If you want the Codex-native backend path without installing the Hermes surface as well:

```bash
bash scripts/install_codex.sh --skip-hermes-install
```

If you want a standalone exported local Codex plugin marketplace root as well:

```bash
bash scripts/install_codex.sh --plugin-root /tmp/deep-gvr-codex-plugin
```

If you want the checked-in Codex automation pack exported for review as well:

```bash
bash scripts/install_codex.sh --automation-root /tmp/deep-gvr-codex-automations
```

If you want the Codex review and visual-QA prompt pack exported for review as well:

```bash
bash scripts/install_codex.sh --review-qa-root /tmp/deep-gvr-codex-review-qa
```

If you want a repo-owned review-evidence bundle for Codex before live review or browser inspection:

```bash
uv run python scripts/codex_review_qa_execute.py pull_request_review --output-root /tmp/deep-gvr-codex-review-qa-evidence/review --force
uv run python scripts/codex_review_qa_execute.py public_docs_visual_qa --output-root /tmp/deep-gvr-codex-review-qa-evidence/docs --force
```

If you want the Codex subagent prompt pack exported for review as well:

```bash
bash scripts/install_codex.sh --subagents-root /tmp/deep-gvr-codex-subagents
```

If you want the Codex `ssh/devbox` remote-operator prompt pack exported for review as well:

```bash
bash scripts/install_codex.sh --ssh-devbox-root /tmp/deep-gvr-codex-ssh-devbox
```

If you want to run the native Codex backend from a remote Codex SSH/devbox session:

```bash
uv run python scripts/codex_remote_bootstrap.py --json
uv run python scripts/codex_preflight.py --ssh-devbox --operator
uv run python scripts/codex_ssh_devbox_run.py run "Explain why the surface code is understood to have a threshold."
```

Once installed into Hermes, the same system is available as:

```text
/deep-gvr <question>
/deep-gvr resume <session_id>
```

For the full operator path, see [Quickstart](docs/quickstart.md) and [Release Workflow](docs/release-workflow.md).

## Docs Map

Start here:

- [Docs Home](docs/index.md)
- [Start Here](docs/start-here.md)
- [Codex Local](docs/codex-local.md)
- [Codex Plugin](docs/codex-plugin.md)
- [Codex Automations](docs/codex-automations.md)
- [Codex Review and Visual QA](docs/codex-review-qa.md)
- [Codex Subagents](docs/codex-subagents.md)
- [Codex SSH Devbox](docs/codex-ssh-devbox.md)
- [Quickstart](docs/quickstart.md)
- [Concepts](docs/concepts.md)
- [Domain Portfolio](docs/domain-portfolio.md)
- [Examples](docs/examples.md)
- [FAQ](docs/faq.md)

Technical reference:

- [System Overview](docs/system-overview.md)
- [Backend Parity Matrix](docs/backend-parity-matrix.md)
- [Tier 2 and Tier 3 Support Matrix](docs/tier2-tier3-support-matrix.md)
- [Architecture and Design](docs/deep-gvr-architecture.md)
- [Release Workflow](docs/release-workflow.md)

Release history:

- [Changelog](CHANGELOG.md)
- [GitHub Releases](https://github.com/sghowell/deep-gvr/releases)

## Current Scope and Limits

- `deep-gvr` is a verification-oriented research system, not a general-purpose chatbot.
- Tier 2 and Tier 3 are selective. They are used when the claim warrants them, not on every run.
- Local operation is the default path. Some optional backends depend on external tools or remote infrastructure.
- The shipped Tier 3 backends are Aristotle and MathCode. OpenGauss remains an intended backend, but it is not part of the standard release path today.
- The current shipped support boundary for Tier 2 families and Tier 3 backends is summarized in [Tier 2 and Tier 3 Support Matrix](docs/tier2-tier3-support-matrix.md).
- Codex local can now act as a real orchestrator backend when `runtime.orchestrator_backend=codex_local` is selected, and that backend now runs Generator, Verifier, and Reviser as separate native Codex role calls over the typed loop.
- Hermes remains the default backend in the checked-in config template, and the Hermes `/deep-gvr` surface still requires Hermes to be installed.
- The repo ships Codex automation templates and export helpers, not direct registration into Codex's live automation runtime state.
- The repo also ships an exportable Codex review/QA prompt pack plus a repo-owned evidence helper for pull-request review and browser-driven docs QA, including from SSH/devbox sessions when the Codex product supports them.
- The repo also ships an exportable Codex subagent prompt pack for safe multi-agent fanout and parallel surface review over the same runtime and git/worktree discipline; that pack complements the native Codex backend and is not the backend itself.
- The repo also ships an explicit Codex `ssh/devbox` bundle, readiness path, and runtime-backed remote execution helper over the native `codex_local` backend.
- The repo also ships a rerunnable `scripts/codex_remote_bootstrap.py` helper that syncs remote config, installs the Codex surface, ensures the evidence directory exists, and then reports the remaining SSH/devbox readiness deltas.
- Some advanced Hermes-native capabilities, especially true per-subagent routing and delegated MCP inheritance, still depend on upstream Hermes support.

## What It Is Not

- Not a fine-tuned model
- Not a single proprietary stack
- Not limited to quantum computing
- Not a system that always claims success

When `deep-gvr` cannot verify something to the required standard, it is expected to say so.
