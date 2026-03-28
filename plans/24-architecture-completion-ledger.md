# 24 Architecture Completion Ledger

## Purpose / Big Picture

Turn the original architecture document into an executable completion backlog. This slice creates a single ledger of non-realized architecture items, maps each current workaround to a retirement plan, and updates repo-local docs and checks so runtime fallbacks are tracked as temporary gaps rather than treated as the product surface.

## Branch Strategy

Start from `main` and implement this slice on `codex/architecture-completion-ledger`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result, push `main`, confirm CI, and delete the feature branch.

## Commit Plan

- `add architecture completion plans`
- `track architecture gaps in docs`
- `enforce retirement slice ownership`

## Progress

- [x] Add the architecture completion ledger in `docs/architecture-status.md`.
- [x] Add and index numbered execution plans `24` through `33`.
- [x] Update repo-local docs so current temporary gaps point to owning retirement slices.
- [x] Extend repo checks so the ledger and retirement-slice references are required.

## Surprises & Discoveries

- The repo already has good slice-by-slice history through plan 23, so the main missing piece was not planning volume but a single place that distinguishes realized architecture from temporary substitutions.
- The most consequential current substitution is architectural, not just operational: the supported runtime still issues separate top-level `hermes chat` calls instead of running the role loop as Hermes-native delegated execution.
- `persist_to_memory` already exists in the config contract, but there is no runtime memory integration behind it, which makes evidence persistence a real architecture gap rather than just a documentation omission.

## Decision Log

- Keep the original architecture document as the target-state spec and add a separate ledger for current implementation status.
- Track non-realized architecture items by owning slice, not by informal prose scattered across docs.
- Treat runtime fallbacks as temporary gaps and make the repo checks enforce ownership of those gaps.

## Outcomes & Retrospective

- The repo now has a dedicated architecture ledger that separates realized architecture from temporary gaps and planned work.
- The roadmap is extended through plans `24` to `33`, with one owning slice per remaining architecture item.
- Repo checks now enforce the presence of the architecture ledger and retirement-slice references in the main operator docs.

## Context and Orientation

- Target-state design: `docs/deep-gvr-architecture.md`
- Architecture ledger: `docs/architecture-status.md`
- Indexed plans: `plans/README.md`
- Repo checks: `src/deep_gvr/repo_checks.py`
- Main operator docs: `README.md`, `SKILL.md`, `docs/capability-probes.md`

## Plan of Work

1. Add the architecture ledger and define the canonical open item IDs.
2. Create the next numbered plans that own each non-realized architecture item.
3. Update the architecture doc and operator docs so temporary gaps link to retirement slices.
4. Enforce the new planning discipline in the repo checks.

## Concrete Steps

1. Add `docs/architecture-status.md` with realized baseline items plus the open architecture table.
2. Add `plans/24-architecture-completion-ledger.md` through `plans/33-domain-adapter-expansion.md`.
3. Update `plans/README.md`, `docs/README.md`, and `docs/deep-gvr-architecture.md` to point to the new ledger.
4. Update `README.md`, `SKILL.md`, and `docs/capability-probes.md` so temporary-gap notes include retirement-slice ownership.
5. Extend `src/deep_gvr/repo_checks.py` to require the ledger and the retirement-slice references.

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Acceptance evidence:

- `docs/architecture-status.md` exists and lists every non-realized architecture item exactly once.
- Plans `24` through `33` exist and are indexed from `plans/README.md`.
- `README.md`, `SKILL.md`, and `docs/capability-probes.md` each reference the owning retirement slices for the current temporary gaps they describe.
- `scripts/check_repo.py` fails if the ledger or required retirement-slice references are removed.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/architecture-completion-ledger` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Keep the ledger additive and keyed by stable item IDs so future slices can update status without rewriting the document structure.
- If a future slice proves an external blocker cannot be closed in-repo, keep the item open as `blocked_external` instead of weakening the target behavior.
- Do not collapse multiple architecture gaps into one generic item; each open target needs one owner.

## Interfaces and Dependencies

- `docs/architecture-status.md` is the canonical status ledger for target-state alignment.
- `plans/24-architecture-completion-ledger.md` through `plans/33-domain-adapter-expansion.md` own the remaining architecture work.
- `src/deep_gvr/repo_checks.py` enforces the new ledger and retirement-slice rules.
