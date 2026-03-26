from __future__ import annotations

import unittest

from tests import _path_setup  # noqa: F401

from deep_gvr.repo_checks import run_all_checks


class RepoChecksTests(unittest.TestCase):
    def test_repo_checks_pass(self) -> None:
        self.assertEqual(run_all_checks(), [])


if __name__ == "__main__":
    unittest.main()
