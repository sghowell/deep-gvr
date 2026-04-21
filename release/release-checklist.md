# Release Checklist

Use this checklist when cutting a public `deep-gvr` release.

## Version and Notes

- Confirm the version in `pyproject.toml` is final for the release.
- Update `CHANGELOG.md` so the current version has a complete dated section.
- Leave `## [Unreleased]` in place for follow-on work.
- Confirm `release/agentskills.publication.json` still matches the current project metadata.

## Validation

- Run `uv run python scripts/check_repo.py`
- Run `uv run python scripts/run_capability_probes.py`
- Run `uv run python -m unittest discover -s tests -v`
- Run `bash scripts/install_codex.sh`
- Run `uv run python scripts/codex_preflight.py --json`
- Run `uv run python scripts/codex_preflight.py --operator`
- Run `uv run python scripts/release_preflight.py --json`
- Run `uv run python scripts/release_preflight.py --operator --config ~/.hermes/deep-gvr/config.yaml`
- Run `uv run python scripts/check_release_version.py --tag v<version>`
- Run `uv run mkdocs build --strict`
- If you intend to enable `auto_improve`, run `uv run python scripts/evaluate_auto_improve.py --output /tmp/deep-gvr-auto-improve/report.json` first and review the report before editing `release/agentskills.publication.json`

## Publication

- Push the release branch or merge result to `main`.
- Create and push the signed or reviewed tag `v<version>`.
- Confirm the GitHub release workflow succeeds for the tag.
- Verify the release notes match the `CHANGELOG.md` section for that version.
- Confirm the `release/agentskills.publication.json` asset is attached to the GitHub release.

## Hosted Docs

- Confirm the Docs workflow builds successfully from the same repo state.
- If GitHub Pages is enabled for the repository, run the manual docs deployment workflow and verify the published site.

## Post-Release

- Open the next `## [Unreleased]` section for future work if needed.
- Verify the release links and docs references still point to the latest public surfaces.
