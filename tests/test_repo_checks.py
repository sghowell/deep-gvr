from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests import _path_setup  # noqa: F401

from deep_gvr.repo_checks import check_markdown_links, run_all_checks


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


if __name__ == "__main__":
    unittest.main()
