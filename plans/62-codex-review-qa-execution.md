# 62 Codex Review and QA Execution

## Purpose / Big Picture

Upgrade the current Codex review/QA surface from a prompt/export pack into a
stronger evidence-backed execution path where repo-owned boundaries allow it.
The target is not live Codex app-state control. It is a better repo-owned path
for browser-driven docs QA, review workflows, and visible evidence capture.

## Branch Strategy

Start from `main` and implement this slice on
`codex/codex-review-qa-execution`. Merge back into `main` locally with a
fast-forward only after branch validation passes, then validate the merged
result again, push `main`, confirm CI and Docs, and delete the feature branch
when it is no longer needed.

## Commit Plan

- `add codex review qa execution contracts`
- `wire codex review qa execution surface`
- `document codex review qa execution`

## Progress

- [x] Evaluate which current review/QA flows can be made repo-owned and
      evidence-backed.
- [x] Add execution helpers or artifact paths for those flows.
- [x] Update docs and release checks accordingly.
- [x] Run full validation on the feature branch.
- [ ] Merge, push, and close out the slice.

## Surprises & Discoveries

- The cleanest repo-owned boundary is a typed evidence-bundle helper, not an
  attempt to drive live Codex review or browser state from the repository.
- The most useful first workflows are the ones already represented in the
  prompt pack: pull-request review and public-docs visual QA.
- Public-docs visual QA should stay `attention` even when the helper succeeds,
  because the bundle prepares inspection; it does not replace live visual
  judgment.

## Decision Log

- Decision: keep this slice focused on repo-owned execution/evidence, not live
  Codex app settings or GitHub review configuration.
- Decision: materialize one typed execution report plus workflow-specific
  artifacts rather than adding separate ad hoc helpers for each review flow.
- Decision: anchor the shipped prompts to the new helper so Codex starts from
  the repo-owned evidence bundle before wider review or browser work.

## Outcomes & Retrospective

- Added `scripts/codex_review_qa_execute.py` plus a typed
  `CodexReviewQaExecutionReport` surface for repo-owned review/QA evidence.
- Added workflow-specific evidence bundles for:
  - `pull_request_review`
  - `public_docs_visual_qa`
- Updated the shipped prompts, release metadata, schema/template checks, and
  docs so the review/QA surface is no longer described as prompt-only.

## Context and Orientation

- `codex_review_qa/`
- `docs/codex-review-qa.md`
- `scripts/export_codex_review_qa.py`
- `docs/README.md`

## Plan of Work

1. Identify the parts of review/QA that should move from prompt-only to
   evidence-backed execution.
2. Add repo-owned helpers or artifact conventions for those flows.
3. Update docs and checks so the surface remains explicit and enforceable.

## Concrete Steps

1. Add helpers for one or more of:
   - docs visual smoke capture
   - release-surface review evidence capture
   - structured review result export
2. Ensure the resulting evidence lands in repo-owned artifacts rather than only
   in ephemeral Codex product state.
3. Update docs and preflight/release checks if the surface changes.

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
uv run mkdocs build --strict
```

Acceptance evidence:

- At least one current review/QA workflow gains a stronger repo-owned execution
  and evidence path.
- The repo still stays honest about product-managed Codex review/browser state.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/codex-review-qa-execution` into `main` locally only
  after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm CI and Docs are green.
- Delete the feature branch when it is no longer needed.

## Idempotence and Recovery

- Any execution helpers should be rerunnable and should not depend on hidden app
  state.
- Do not reframe product-managed review features as repo-owned automation.

## Interfaces and Dependencies

- Depends on the current Codex review/QA prompt pack and public docs surface.
- Likely depends on current Codex browser/computer-use capabilities when run by
  the operator.
