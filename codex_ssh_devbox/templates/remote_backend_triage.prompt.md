# deep-gvr remote backend triage

Debug a `deep-gvr` remote validator or Tier 2 SSH-backend issue from a Codex session that is already connected to a remote devbox or SSH-accessible machine for `__DEEP_GVR_REPO_ROOT__`.

Instructions:

1. Start by running:
   - `uv run python scripts/codex_preflight.py --ssh-devbox --json`
   - `uv run python scripts/run_capability_probes.py`
2. Identify whether the failure is in:
   - Codex remote-session prerequisites
   - `deep-gvr` runtime config
   - SSH backend config
   - remote workspace or Python path setup
   - optional analysis-family dependencies
3. Use the existing SSH Tier 2 backend settings and artifacts as the source of truth. Do not invent an alternate transport.
4. Summarize only concrete blockers and the smallest next fix. Include:
   - the failing surface
   - the exact evidence or command output
   - the likely offending file or config field
5. If everything required for the remote path is ready, say that explicitly and identify what the operator should run next.
6. Do not edit files or push changes unless explicitly asked.

Repository-specific priorities:

- Prefer exact readiness and configuration failures over broad advice.
- Keep the distinction between repo-owned support and Codex product-managed SSH/devbox state explicit.
- Treat `docs/codex-ssh-devbox.md` as the human-facing surface for this path.
