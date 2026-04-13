# Release Workflow

This guide is for operators who want to install, validate, version, and publish the human-facing `deep-gvr` release surface.

`deep-gvr` is published through two primary public channels:

- GitHub Releases for tagged source snapshots and release notes
- `agentskills.io` using the checked-in publication manifest

The same public docs set is also buildable as a hosted site through MkDocs Material and GitHub Pages.

## 1. Prepare the Release Metadata

Before cutting a public tag:

- update `CHANGELOG.md`
- confirm the repo version in `pyproject.toml`
- confirm the checked-in publication bundle still matches the repo metadata

Use the machine checks directly:

```bash
uv run python scripts/check_release_version.py --tag v0.1.0
uv run python scripts/render_release_notes.py --version 0.1.0
```

The release checklist lives at [release/release-checklist.md](https://github.com/sghowell/deep-gvr/blob/main/release/release-checklist.md).

## 2. Install the Skill Bundle

```bash
bash scripts/install.sh
```

If you want an isolated install tree for packaging or smoke testing, set `HERMES_HOME` first. The install and preflight helpers will use that tree instead of `~/.hermes`.

## 3. Run Structural Preflight

```bash
uv run python scripts/release_preflight.py --json
```

This checks the release bundle, config presence, and checked-in publication assets without assuming a live operator environment.

## 4. Run Operator Preflight

```bash
uv run python scripts/release_preflight.py --operator --config ~/.hermes/deep-gvr/config.yaml
```

This verifies the installed skill bundle plus the live runtime path:

- Hermes availability
- config validity
- provider readiness
- selected Tier 2 backend readiness
- selected Tier 3 backend readiness

## 5. Enable Tier 3 if Needed

For Aristotle:

```bash
bash scripts/setup_mcp.sh --install --check
```

For MathCode, point the config at the local checkout and executable run wrapper, then re-run operator preflight.

## 6. Build the Hosted Docs

```bash
uv run mkdocs build --strict
```

The hosted docs are built directly from the human-facing repo docs. There is no separate public docs tree.

The repo includes a `Docs` workflow that builds and deploys automatically on every push to `main`. `workflow_dispatch` remains available for manual reruns when needed.

## 7. Publish the Release

Create and push the release tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The tagged `Release` workflow will:

- validate the repo, release surface, and hosted docs build
- verify that the tag matches the repo version
- render release notes from `CHANGELOG.md`
- publish a GitHub Release
- attach the checked-in publication manifest

The publication bundle that should ship with the release is:

- `release/agentskills.publication.json`

That same manifest is the source of truth for `agentskills.io` publication.

## Auto Improve Policy

The release bundle ships with `auto_improve: false`.

That is intentional. Enabling automatic self-modification is an explicit operator choice, not the default behavior of the public release surface.
