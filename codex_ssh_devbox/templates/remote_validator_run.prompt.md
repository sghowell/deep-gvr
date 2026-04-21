# deep-gvr remote validator run

Operate `deep-gvr` from a Codex session that is already connected to a remote devbox or SSH-accessible validator machine for `__DEEP_GVR_REPO_ROOT__`.

Instructions:

1. Confirm you are working inside the intended checkout and that the remote machine can access the required validator or simulation dependencies.
2. Run `uv run python scripts/codex_preflight.py --ssh-devbox --operator` from the repo root before attempting a live run.
3. If remote preflight is blocked, report the exact failing check and stop unless the operator explicitly asks you to remediate it.
4. If remote preflight passes, use the installed `deep-gvr` skill or `codex exec` workflow to run the requested investigation from the same checkout.
5. Prefer the remote machine for simulation-heavy validation, backend dispatch checks, or artifact inspection that would be weak or slow on a laptop.
6. Summarize:
   - what question or claim you ran
   - which backend path was used
   - where the session artifacts were written
   - any remote-only limitations or missing dependencies
7. Do not edit repo files, change release metadata, or push anything unless explicitly asked.

Repository-specific priorities:

- Treat `scripts/codex_preflight.py --ssh-devbox --operator` as the gate for remote-validator readiness.
- Reuse the existing typed runtime and SSH Tier 2 backend; do not invent a second remote execution path.
- Call out missing SSH backend config, missing remote workspace settings, or missing provider credentials explicitly.
