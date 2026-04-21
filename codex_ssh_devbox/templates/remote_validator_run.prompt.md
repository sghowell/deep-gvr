# deep-gvr remote validator run

Operate `deep-gvr` from a Codex session that is already connected to a remote devbox or SSH-accessible validator machine for `__DEEP_GVR_REPO_ROOT__`.

Instructions:

1. Confirm you are working inside the intended checkout and that the remote machine can access the required validator or simulation dependencies.
2. Run `uv run python scripts/codex_preflight.py --ssh-devbox --operator` from the repo root before attempting a live run.
3. If remote preflight is blocked, report the exact failing check and stop unless the operator explicitly asks you to remediate it.
4. If remote preflight passes, prefer `uv run python scripts/codex_ssh_devbox_run.py run "<question>"` from the same checkout so the native `codex_local` backend is gated and executed directly from the remote machine.
5. Prefer the remote machine for simulation-heavy validation, backend dispatch checks, or artifact inspection that would be weak or slow on a laptop.
6. Summarize:
   - what question or claim you ran
   - which backend path was used
   - where the session artifacts were written
   - any remote-only limitations or missing dependencies
7. Do not edit repo files, change release metadata, or push anything unless explicitly asked.

Repository-specific priorities:

- Treat `scripts/codex_preflight.py --ssh-devbox --operator` as the gate for remote-validator readiness.
- Reuse the existing typed runtime and native `codex_local` backend; do not invent a second orchestrator backend for remote execution.
- Treat the selected Tier 2 backend as the source of truth: the remote machine may be the strong local host, or it may dispatch through the existing typed `ssh` or `modal` backend.
- Call out missing selected-backend config, missing provider credentials, or a non-`codex_local` orchestrator backend explicitly.
