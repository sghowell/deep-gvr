# deep-gvr public docs visual QA

Run a visual QA pass for the public docs in `__DEEP_GVR_REPO_ROOT__`.

Instructions:

1. Build the docs first with `uv run mkdocs build --strict` from the repo root.
2. Prefer visual inspection in the Codex app using the in-app browser or computer-use surface when available.
3. If a local HTTP preview is needed, serve `site/` from a temporary local server and inspect it there.
4. Inspect at least these pages:
   - landing page
   - Concepts
   - Architecture and Design
   - Codex Local
   - Codex Plugin
   - Codex Automations
   - Codex Review and Visual QA
5. Look for:
   - broken or missing images
   - clipped or overflowing text in diagrams
   - unreadable figure typography
   - layout breakage on wide or narrow viewports
   - obviously broken links or missing sections
   - visual drift between the public docs entrypoints
6. Summarize only actionable issues. For each issue include:
   - page or URL
   - visible symptom
   - likely source file or asset path
7. If browser or computer-use inspection is unavailable, say that clearly and fall back to the strongest static check you can perform.
8. Do not edit files or push changes unless explicitly asked.

Repository-specific priorities:

- Treat the checked-in SVG figures and MkDocs pages as the source of truth.
- Focus on public-reader defects, not internal docs.
- Call out any regression that would make the hosted site feel broken or unprofessional.
