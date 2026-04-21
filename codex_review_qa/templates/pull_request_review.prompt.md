# deep-gvr pull request review

Review the changes for `__DEEP_GVR_REPO_ROOT__` with a code-review mindset. Prioritize bugs, regressions, behavior changes, release-surface drift, missing tests, and public-doc/operator regressions over style commentary.

Instructions:

1. Identify the exact review target before you judge it.
   - If the operator gives a PR number, inspect that PR.
   - Otherwise review the current local branch against `main`.
2. Read the changed files directly. Do not guess from commit messages.
3. Report findings first, ordered by severity.
4. For each finding, include:
   - a short severity label
   - the concrete problem
   - the file path
   - the specific behavioral or release risk
5. If there are no findings, say that explicitly and then note residual risks or testing gaps.
6. Keep the review output concise and technical. Avoid praise or generic commentary.
7. Do not edit files, push changes, or open a PR unless explicitly asked.

Repository-specific priorities:

- Treat `docs/deep-gvr-architecture.md` and `docs/architecture-status.md` as source-of-truth surfaces.
- Check that public docs, release metadata, schemas, templates, and tests moved with any contract or public-surface changes.
- Watch for drift across Codex, Hermes, release, and docs surfaces.
- Prefer findings about correctness, readiness, and enforcement over style-only notes.
