# Release Workflow

`deep-gvr` now ships a release-grade install, preflight, and publication bundle.

## Operator Path

1. Install the skill bundle into Hermes:

   ```bash
   bash scripts/install.sh
   ```

   If you need an isolated Hermes home for packaging or smoke tests, set `HERMES_HOME` first and the install plus preflight helpers will use that tree instead of `~/.hermes`.

2. Run structural preflight to confirm the installed bundle, runtime config, and publication assets are present:

   ```bash
   uv run python scripts/release_preflight.py --json
   ```

3. Run operator preflight before live use:

   ```bash
   uv run python scripts/release_preflight.py --operator --config ~/.hermes/deep-gvr/config.yaml
   ```

4. If Tier 3 is enabled, install and validate Aristotle MCP transport:

   ```bash
   bash scripts/setup_mcp.sh --install --check
   ```

`--operator` fails unless the selected runtime path is actually ready for Hermes use. The default preflight mode only enforces structural release-surface completeness so it stays CI-safe.

## Publication Bundle

- Checked-in publication manifest: `release/agentskills.publication.json`
- Source skill manifest: `SKILL.md`
- Operator docs: `README.md`
- Preflight helper: `scripts/release_preflight.py`

The publication manifest is validated against repo-local truth during repo checks. It is the checked-in source bundle for GitHub and agentskills.io release work.

## Auto Improve Policy

The release bundle ships with `auto_improve: false`.

To opt in:

1. review the release bundle and operator docs
2. set `auto_improve` to `true` in `release/agentskills.publication.json`
3. republish the same validated bundle with human sign-off

Do not enable `auto_improve` by default in the repository release surface.
