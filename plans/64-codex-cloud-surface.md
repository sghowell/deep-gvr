# 64 Codex Cloud Surface

## Purpose / Big Picture

Evaluate and, if justified, implement a first-class Codex Cloud surface for
`deep-gvr`. This is intentionally later than the local and SSH/devbox Codex
work because the current repo runtime is strongly local/operator-shaped and the
highest-value Codex work still sits on the local and remote-native paths.

## Branch Strategy

Start from `main` and implement this slice on `codex/codex-cloud-surface`.
Merge back into `main` locally with a fast-forward only after branch validation
passes, then validate the merged result again, push `main`, confirm CI and
Docs, and delete the feature branch when it is no longer needed.

## Commit Plan

- `plan codex cloud surface`
- `add codex cloud surface`
- `document codex cloud boundary`

## Progress

- [ ] Decide whether Codex Cloud belongs in the supported product surface.
- [ ] If yes, define a narrow honest first surface.
- [ ] Implement only that narrow surface.

## Surprises & Discoveries

- Pending.

## Decision Log

- Decision: treat Codex Cloud as optional and later than local/remote-native
  Codex support.

## Outcomes & Retrospective

- Pending implementation.

## Context and Orientation

- `docs/codex-local.md`
- `docs/deep-gvr-architecture.md`
- `release/agentskills.publication.json`
- current Codex Cloud docs and product constraints

## Plan of Work

1. Decide whether a Codex Cloud path should exist at all for `deep-gvr`.
2. If yes, define the narrowest honest supported surface.
3. Implement only the surface the repo can actually own.

## Concrete Steps

1. Evaluate likely Codex Cloud use cases such as:
   - background repo review
   - issue triage
   - release/report generation
   - narrow code-mode tasks against the repo
2. Decide whether any of those fit the `deep-gvr` runtime and evidence model
   cleanly.
3. If they do, add the necessary docs, checks, and thin integration surface.

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
uv run mkdocs build --strict
```

Acceptance evidence:

- The repo either has a truthful narrow Codex Cloud surface or a documented
  decision not to support one yet.
- The resulting boundary is explicit about cloud-local differences.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/codex-cloud-surface` into `main` locally only after
  validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm CI and Docs are green.
- Delete the feature branch when it is no longer needed.

## Idempotence and Recovery

- Keep the slice narrow and truthful. Do not imply that the repo can own more of
  Codex Cloud than it actually can.

## Interfaces and Dependencies

- Depends on current Codex product support for cloud tasks and background
  execution.
- Depends on a clear boundary between cloud-only work and the local/runtime
  evidence model already shipped by `deep-gvr`.
