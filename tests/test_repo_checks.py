from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests import _path_setup  # noqa: F401

from deep_gvr.repo_checks import (
    REQUIRED_TIER3_SOURCE_OF_TRUTH_SNIPPETS,
    check_hosted_docs_nav,
    check_markdown_links,
    check_tier3_source_of_truth,
    run_all_checks,
)


class RepoChecksTests(unittest.TestCase):
    def test_repo_checks_pass(self) -> None:
        self.assertEqual(run_all_checks(), [])

    def test_markdown_link_check_ignores_dot_venv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            venv_readme = root / ".venv" / "README.md"
            venv_readme.parent.mkdir(parents=True, exist_ok=True)
            venv_readme.write_text("[broken](doc/missing.md)\n", encoding="utf-8")
            self.assertEqual(check_markdown_links(root), [])

    def test_hosted_docs_nav_check_requires_non_excluded_pages_in_nav(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            docs_dir = root / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)
            (docs_dir / "index.md").write_text("# Home\n", encoding="utf-8")
            (docs_dir / "plugin-privacy.md").write_text("# Privacy\n", encoding="utf-8")
            (docs_dir / "plugin-terms.md").write_text("# Terms\n", encoding="utf-8")
            (root / "mkdocs.yml").write_text(
                "docs_dir: docs\nnav:\n  - Home: index.md\n",
                encoding="utf-8",
            )

            errors = check_hosted_docs_nav(root)

            self.assertIn(
                "mkdocs.yml: docs page 'plugin-privacy.md' is not included in nav or exclude_docs",
                errors,
            )
            self.assertIn(
                "mkdocs.yml: docs page 'plugin-terms.md' is not included in nav or exclude_docs",
                errors,
            )

    def test_hosted_docs_nav_check_accepts_nested_nav_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            docs_dir = root / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)
            (docs_dir / "codex-plugin.md").write_text("# Plugin\n", encoding="utf-8")
            (docs_dir / "plugin-privacy.md").write_text("# Privacy\n", encoding="utf-8")
            (docs_dir / "plugin-terms.md").write_text("# Terms\n", encoding="utf-8")
            (root / "mkdocs.yml").write_text(
                "\n".join(
                    [
                        "docs_dir: docs",
                        "nav:",
                        "  - Codex Plugin:",
                        "      - Overview: codex-plugin.md",
                        "      - Privacy: plugin-privacy.md",
                        "      - Terms: plugin-terms.md",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            self.assertEqual(check_hosted_docs_nav(root), [])

    def test_tier3_source_of_truth_check_rejects_stale_backend_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for relative, snippets in REQUIRED_TIER3_SOURCE_OF_TRUTH_SNIPPETS.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("\n".join(snippets) + "\n", encoding="utf-8")

            self.assertEqual(check_tier3_source_of_truth(root), [])

            stale_skill = root / "SKILL.md"
            stale_skill.write_text(
                "\n".join(REQUIRED_TIER3_SOURCE_OF_TRUTH_SNIPPETS["SKILL.md"])
                + "\nactual backend remains blocked externally until plan 31 can resume\n",
                encoding="utf-8",
            )

            errors = check_tier3_source_of_truth(root)

            self.assertIn(
                "SKILL.md: stale Tier 3 source-of-truth phrase "
                "'actual backend remains blocked externally until plan 31 can resume'",
                errors,
            )


if __name__ == "__main__":
    unittest.main()
