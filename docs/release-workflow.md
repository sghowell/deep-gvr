# Release Workflow

This guide is for operators who want to install, validate, and publish the human-facing `deep-gvr` release surface.

## 1. Install the Skill Bundle

```bash
bash scripts/install.sh
```

If you want an isolated install tree for packaging or smoke testing, set `HERMES_HOME` first. The install and preflight helpers will use that tree instead of `~/.hermes`.

## 2. Run Structural Preflight

```bash
uv run python scripts/release_preflight.py --json
```

This checks the release bundle, config presence, and checked-in publication assets without assuming a live operator environment.

## 3. Run Operator Preflight

```bash
uv run python scripts/release_preflight.py --operator --config ~/.hermes/deep-gvr/config.yaml
```

This verifies the installed skill bundle plus the live runtime path:

- Hermes availability
- config validity
- provider readiness
- selected Tier 2 backend readiness
- selected Tier 3 backend readiness

## 4. Enable Tier 3 if Needed

For Aristotle:

```bash
bash scripts/setup_mcp.sh --install --check
```

For MathCode, point the config at the local checkout and executable run wrapper, then re-run operator preflight.

## 5. Publish the Bundle

The checked-in publication bundle is:

- `release/agentskills.publication.json`

The release surface is designed so that the publication manifest, install path, and preflight path stay aligned.

## Auto Improve Policy

The release bundle ships with `auto_improve: false`.

That is intentional. Enabling automatic self-modification is an explicit operator choice, not the default behavior of the public release surface.
