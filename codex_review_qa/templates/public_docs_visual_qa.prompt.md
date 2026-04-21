# deep-gvr public docs visual QA

Run a visual QA pass for the public docs in `__DEEP_GVR_REPO_ROOT__`.

Instructions:

1. Prepare the repo-owned visual-QA evidence bundle first:
   - `uv run python scripts/codex_review_qa_execute.py public_docs_visual_qa --output-root /tmp/deep-gvr-codex-review-qa-evidence/docs --force --json`
2. Read the generated `visual_targets.json`, `preview_targets.json`, and `build.log` artifacts before starting live inspection.
3. Prefer visual inspection in the Codex app using the in-app browser or computer-use surface when available.
4. If a local HTTP preview is needed, serve `site/` from a temporary local server and inspect it there.
5. Inspect at least these pages:
   - landing page
   - Concepts
   - Architecture and Design
   - Codex Local
   - Codex Plugin
   - Codex Automations
   - Codex Review and Visual QA
6. Look for:
   - broken or missing images
   - clipped or overflowing text in diagrams
   - unreadable figure typography
   - layout breakage on wide or narrow viewports
   - obviously broken links or missing sections
   - visual drift between the public docs entrypoints
7. Summarize only actionable issues. For each issue include:
   - page or URL
   - visible symptom
   - likely source file or asset path
8. If browser or computer-use inspection is unavailable, say that clearly and fall back to the strongest static check you can perform.
9. Do not edit files or push changes unless explicitly asked.

Repository-specific priorities:

- Treat the checked-in SVG figures and MkDocs pages as the source of truth.
- Use the repo-owned evidence bundle to anchor page selection, built-asset checks, and preview targets before live browser inspection.
- Focus on public-reader defects, not internal docs.
- Call out any regression that would make the hosted site feel broken or unprofessional.
