from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import _path_setup  # noqa: F401

from deep_gvr.codex_review_qa import CodexReviewQaExecutionOptions, execute_codex_review_qa
from deep_gvr.contracts import ReleasePreflightReport

ROOT = Path(__file__).resolve().parents[1]


def _completed(command: list[str], *, stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr=stderr)


class CodexReviewQaExecutionTests(unittest.TestCase):
    def test_pull_request_review_execution_writes_review_bundle(self) -> None:
        template_payload = json.loads((ROOT / "templates" / "release_preflight.template.json").read_text(encoding="utf-8"))
        template_payload["overall_status"] = "ready"
        template_payload["release_surface_ready"] = True
        template_payload["operator_ready"] = True
        release_preflight = ReleasePreflightReport.from_dict(template_payload)

        def fake_run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
            mapping: dict[tuple[str, ...], subprocess.CompletedProcess[str]] = {
                ("git", "rev-parse", "--abbrev-ref", "HEAD"): _completed(command, stdout="codex/codex-review-qa-execution\n"),
                ("git", "rev-parse", "HEAD"): _completed(command, stdout="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef\n"),
                ("git", "rev-parse", "main"): _completed(command, stdout="feedfacefeedfacefeedfacefeedfacefeedface\n"),
                ("git", "merge-base", "main", "HEAD"): _completed(command, stdout="abc123abc123abc123abc123abc123abc123abcd\n"),
                ("git", "status", "--short"): _completed(command, stdout=""),
                ("git", "diff", "--name-only", "abc123abc123abc123abc123abc123abc123abcd"): _completed(
                    command,
                    stdout="src/deep_gvr/codex_review_qa.py\ndocs/codex-review-qa.md\n",
                ),
                ("git", "diff", "--name-status", "abc123abc123abc123abc123abc123abc123abcd"): _completed(
                    command,
                    stdout="M\tsrc/deep_gvr/codex_review_qa.py\nM\tdocs/codex-review-qa.md\n",
                ),
                ("git", "diff", "--stat", "abc123abc123abc123abc123abc123abc123abcd"): _completed(
                    command,
                    stdout=" src/deep_gvr/codex_review_qa.py | 42 +++++++++++++++++++++++++++++\n 1 file changed, 42 insertions(+)\n",
                ),
                ("git", "diff", "abc123abc123abc123abc123abc123abc123abcd"): _completed(
                    command,
                    stdout="diff --git a/src/deep_gvr/codex_review_qa.py b/src/deep_gvr/codex_review_qa.py\n",
                ),
            }
            result = mapping.get(tuple(command))
            if result is None:
                raise AssertionError(f"Unexpected command: {command!r}")
            return result

        with tempfile.TemporaryDirectory() as tmpdir:
            output_root = Path(tmpdir) / "review-bundle"
            with (
                patch("deep_gvr.codex_review_qa._run_command", side_effect=fake_run),
                patch("deep_gvr.release_surface.collect_release_preflight", return_value=release_preflight),
            ):
                report = execute_codex_review_qa(
                    CodexReviewQaExecutionOptions(
                        workflow_id="pull_request_review",
                        output_root=output_root,
                        force=True,
                    ),
                    root=ROOT,
                )

            self.assertEqual(report.workflow_id, "pull_request_review")
            self.assertEqual(report.overall_status.value, "ready")
            self.assertTrue((output_root / "report.json").exists())
            self.assertTrue((output_root / "review_target.json").exists())
            self.assertTrue((output_root / "diff.patch").exists())
            self.assertTrue((output_root / "release_preflight.json").exists())
            payload = json.loads((output_root / "review_target.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["changed_file_count"], 2)

    def test_public_docs_visual_qa_execution_writes_visual_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "repo"
            site_dir = root / "site"
            (site_dir / "assets").mkdir(parents=True, exist_ok=True)
            (site_dir / "assets" / "sample.svg").write_text("<svg></svg>\n", encoding="utf-8")

            page_paths = {
                "site/index.html": '<html><body><img src="assets/sample.svg" /></body></html>\n',
                "site/concepts/index.html": '<html><body><img src="../assets/sample.svg" /></body></html>\n',
                "site/deep-gvr-architecture/index.html": '<html><body><img src="../assets/sample.svg" /></body></html>\n',
                "site/codex-local/index.html": "<html><body>No images here.</body></html>\n",
                "site/codex-plugin/index.html": "<html><body>No images here.</body></html>\n",
                "site/codex-automations/index.html": "<html><body>No images here.</body></html>\n",
                "site/codex-review-qa/index.html": "<html><body>No images here.</body></html>\n",
            }
            for relative, content in page_paths.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            output_root = Path(tmpdir) / "docs-bundle"
            with patch(
                "deep_gvr.codex_review_qa._run_command",
                return_value=_completed(["uv", "run", "mkdocs", "build", "--strict"], stdout="build ok\n"),
            ):
                report = execute_codex_review_qa(
                    CodexReviewQaExecutionOptions(
                        workflow_id="public_docs_visual_qa",
                        output_root=output_root,
                        force=True,
                    ),
                    root=root,
                )

            self.assertEqual(report.workflow_id, "public_docs_visual_qa")
            self.assertEqual(report.overall_status.value, "attention")
            self.assertTrue((output_root / "build.log").exists())
            self.assertTrue((output_root / "visual_targets.json").exists())
            self.assertTrue((output_root / "preview_targets.json").exists())
            manifest = json.loads((output_root / "visual_targets.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["pages"]), 7)
            self.assertTrue(all(page["exists"] for page in manifest["pages"]))
