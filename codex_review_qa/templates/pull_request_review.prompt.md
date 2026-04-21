# deep-gvr pull request review

Review the changes for `__DEEP_GVR_REPO_ROOT__` with a code-review mindset. Prioritize bugs, regressions, behavior changes, release-surface drift, missing tests, and public-doc/operator regressions over style commentary.

Instructions:

1. Identify the exact review target before you judge it.
   - If the operator gives a PR number, inspect that PR.
   - Otherwise review the current local branch against `main`.
2. Prepare the repo-owned review evidence bundle first:
   - `uv run python scripts/codex_review_qa_execute.py pull_request_review --output-root /tmp/deep-gvr-codex-review-qa-evidence/review --force --json`
3. Use the generated `review_target.json`, `diff.patch`, and `release_preflight.json` artifacts as primary review context before you read more files.
4. Read the changed files directly. Do not guess from commit messages.
5. Report findings first, ordered by severity.
6. For each finding, include:
   - a short severity label
   - the concrete problem
   - the file path
   - the specific behavioral or release risk
7. If there are no findings, say that explicitly and then note residual risks or testing gaps.
8. Keep the review output concise and technical. Avoid praise or generic commentary.
9. Do not edit files, push changes, or open a PR unless explicitly asked.

Repository-specific priorities:

- Treat `docs/deep-gvr-architecture.md` and `docs/architecture-status.md` as source-of-truth surfaces.
- Check that public docs, release metadata, schemas, templates, and tests moved with any contract or public-surface changes.
- Use the repo-owned evidence bundle to call out release-surface drift and review-target ambiguity before falling back to wider exploratory review.
- Watch for drift across Codex, Hermes, release, and docs surfaces.
- Prefer findings about correctness, readiness, and enforcement over style-only notes.
