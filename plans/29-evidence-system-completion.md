# 29 Evidence System Completion

## Purpose / Big Picture

Complete the evidence system described in the architecture by adding Hermes memory persistence and Parallax-compatible exports or manifests on top of the existing file-backed session artifacts. The current file path is useful but incomplete relative to the intended architecture.

## Branch Strategy

Start from `main` and implement this slice on `codex/evidence-system-completion`. Merge back into `main` locally with a fast-forward only after branch validation passes, then validate the merged result, push `main`, confirm CI, and delete the feature branch.

## Commit Plan

- `add evidence memory integration`
- `add parallax export surface`
- `document evidence completion`

## Progress

- [x] Add the new plan and index it from `plans/README.md`.
- [x] Implement Hermes memory persistence behind `persist_to_memory`.
- [x] Add Parallax-compatible evidence export or manifest generation.
- [x] Update docs, tests, and repo checks for the completed evidence system.

## Surprises & Discoveries

- The current file-backed evidence model is already structured enough to serve as the source for memory summaries and Parallax exports.
- The main architecture gap is integration and export, not a lack of session artifacts.
- Hermes already uses `~/.hermes/memories/MEMORY.md` as a real memory document, so the repo can persist searchable session summaries there without patching Hermes or inventing a second memory location.

## Decision Log

- File-backed session artifacts remain the primary ground truth.
- Hermes memory persistence is derived from those artifacts, not a separate hidden state.
- Parallax compatibility should be expressed as an export or manifest layer, not a second independent evidence schema.

## Outcomes & Retrospective

- Completed.
- `SessionStore` now derives `session_memory_summary.json` plus `parallax_manifest.json` from the checkpoint/evidence log on every saved checkpoint.
- When `persist_to_memory` is enabled, the derived session summary is upserted into Hermes memory at `~/.hermes/memories/MEMORY.md` with a stable `[deep-gvr:<session_id>]` marker so reruns remain idempotent.
- The architecture ledger and repo checks now treat evidence-system completion as realized rather than an open retirement slice.

## Context and Orientation

- Evidence contracts: `src/deep_gvr/contracts.py`
- Session storage: `src/deep_gvr/tier1.py`
- Current config flag: `persist_to_memory`
- Architecture ledger item: `evidence-system-completion`

## Plan of Work

1. Define the Hermes memory summary contract and write path.
2. Add Parallax-compatible export or manifest generation.
3. Update session summaries, docs, and repo checks to require the completed evidence system.
4. Add tests for memory persistence, export generation, and resume compatibility.

## Concrete Steps

1. Extend evidence/session contracts with memory-summary and export metadata.
2. Update the session runner to emit Hermes memory entries when configured.
3. Add Parallax export or manifest generation under the existing session artifact layout.
4. Update docs and checks so `persist_to_memory` is no longer a placeholder flag.
5. Add tests for summary content, export creation, and artifact consistency.

## Validation and Acceptance

Required repo checks:

```bash
uv run python scripts/check_repo.py
uv run python scripts/run_capability_probes.py
uv run python -m unittest discover -s tests -v
```

Targeted validation:

```bash
uv run python -m unittest tests.test_contracts tests.test_tier1_loop -v
```

Acceptance evidence:

- `persist_to_memory` drives real Hermes memory persistence.
- Session evidence can be exported or surfaced in a Parallax-compatible form.
- Repo checks and docs describe the completed evidence system accurately.

## Merge, Push, and Cleanup

- Stage and commit in the planned chunks.
- Validate the feature branch before merge.
- Fast-forward merge `codex/evidence-system-completion` into `main` locally only after validation passes.
- Re-run the required validation commands on `main`.
- Push `main`.
- Confirm the GitHub Actions run for the pushed head is green.
- Delete the local feature branch, and delete the remote feature branch too if one was created.

## Idempotence and Recovery

- Memory summaries must be reproducible from file-backed artifacts.
- Export generation should be safe to rerun without corrupting session history.
- Keep evidence append-only even as derived summary/export layers are added.

## Interfaces and Dependencies

- Depends on session storage, contracts, and any Hermes memory boundary available in the runtime.
- Touches session artifacts, evidence summaries, and release/operator docs.
- Must preserve checkpoint/resume semantics while adding summary/export layers.
