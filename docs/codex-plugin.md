# Codex Plugin

This page covers the packaged Codex plugin surface for `deep-gvr`.

The plugin surface is intentionally thin. It packages the existing Codex-local `deep-gvr` workflow as a reusable bundle; it does not introduce a separate runtime, a separate evidence model, or a non-Hermes backend.

## What the Plugin Contains

The checked-in plugin bundle lives at:

- `plugins/deep-gvr/.codex-plugin/plugin.json`
- `plugins/deep-gvr/skills/deep-gvr/SKILL.md`
- `plugins/deep-gvr/assets/`

The repository also ships a local marketplace manifest at:

- `.agents/plugins/marketplace.json`

Together, those files let the repository act as a local Codex plugin source instead of relying only on the standalone `codex_skill/` tree.

## Current Boundary

The plugin surface packages the existing Codex-local workflow:

- it operates the same typed `deep-gvr` runtime
- it writes the same Hermes config, checkpoints, and evidence artifacts
- it still depends on the underlying Hermes runtime and provider environment

It does not:

- replace Hermes as the shipped delegated execution backend
- add a Codex Cloud runtime path
- add new app or MCP integrations beyond the existing `deep-gvr` workflow

## Export a Standalone Local Marketplace Root

If you want a standalone local marketplace root for Codex, export the checked-in bundle from the repository:

```bash
bash scripts/install_codex.sh --plugin-root /tmp/deep-gvr-codex-plugin
```

That produces:

- `/tmp/deep-gvr-codex-plugin/plugins/deep-gvr`
- `/tmp/deep-gvr-codex-plugin/.agents/plugins/marketplace.json`

The repo remains the source of truth. The exported root is only a convenience copy or symlink tree for local plugin testing and distribution.

## Availability and Controls

Codex plugin availability inside the product depends on current Codex client and workspace support. OpenAI’s [March 26, 2026 plugin launch notes](https://help.openai.com/en/articles/11391654) describe plugins as curated bundles for reusable Codex workflows and note that plugin availability follows workspace app controls.

## Relationship to Codex Local

If you just want to run `deep-gvr` from Codex local today, the direct operator path is still:

```bash
bash scripts/install_codex.sh
uv run python scripts/codex_preflight.py --operator
```

Then use Codex from the local checkout:

```bash
codex exec -C /path/to/deep-gvr "Use the deep-gvr skill to answer: <question>"
```

The plugin surface exists so the same workflow can also be distributed as a packaged Codex bundle.
