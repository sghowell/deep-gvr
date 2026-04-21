# deep-gvr parallel validator fanout

Use Codex subagents to decompose `deep-gvr` work from the checkout at `__DEEP_GVR_REPO_ROOT__`.

Instructions:

1. The main agent owns planning, integration, final validation, staging, commits, merge, and push decisions.
2. Before delegating, inspect the repo state and identify concrete, non-overlapping scopes.
3. If any delegated task will edit files, give that subagent a separate worktree or a strictly disjoint write set.
4. Good subagent splits for `deep-gvr` include:
   - runtime or contract changes
   - tests and validation follow-up
   - public docs or release-surface adjustments
   - targeted backend or prompt-pack analysis
5. Bad splits include:
   - two subagents editing the same file set without coordination
   - subagents making release-policy changes independently
   - subagents pushing branches or merging on their own
6. Each subagent report should include:
   - exact files changed or inspected
   - exact commands run
   - concrete findings, blockers, or patch summary
7. After subagents return, the main agent should:
   - review and integrate the changes
   - rerun the required repo validation path
   - summarize final integrated results clearly
8. Use the repo's enforced workflow rules:
   - feature-branch discipline
   - sensible commit chunks
   - local validation before merge
   - local fast-forward merge to `main`
   - validation again on `main`
9. Do not treat Codex subagents as a second runtime backend. This is an operator workflow over the existing `deep-gvr` runtime.

Repository-specific priorities:

- Keep the main agent responsible for final integration and release-surface correctness.
- Prefer separate worktrees when multiple subagents will write code.
- Preserve alignment between code, schemas, templates, prompts, tests, and docs in the integrated result.
