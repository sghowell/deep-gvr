# deep-gvr parallel surface review

Use Codex subagents to perform a high-signal parallel review of the `deep-gvr` checkout at `__DEEP_GVR_REPO_ROOT__`.

Instructions:

1. Keep the main agent in charge of final synthesis and any resulting edits.
2. Split review work into clearly different surfaces. Recommended split:
   - subagent 1: runtime, contracts, adapters, and tests
   - subagent 2: public docs, diagrams, and hosted-docs surface
   - subagent 3: release/publication/install/preflight surface
3. Each subagent should review with a bug-risk-first mindset and focus on:
   - behavioral regressions
   - missing tests or schema drift
   - public-surface inconsistencies
   - release-surface breakage or stale commands
4. If a subagent is asked to edit, keep the write scope isolated and use a separate worktree when needed.
5. Require each subagent to return:
   - findings first, ordered by severity
   - exact file references
   - commands run or checks inspected
   - any residual uncertainty
6. The main agent should reconcile duplicate or conflicting findings, decide what is real, apply any integrated fixes, and rerun the top-level validation path.
7. Do not allow subagents to push, merge, or independently rewrite shared repo policy.

Repository-specific priorities:

- Treat public docs as part of the shipped product surface, not an afterthought.
- Treat release metadata, install helpers, and Codex/Hermes operator surfaces as part of the review scope when they are touched.
- Keep the distinction explicit between repo-owned prompt/export surfaces and Codex product-managed runtime features.
