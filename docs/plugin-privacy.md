# deep-gvr Plugin Privacy

The `deep-gvr` Codex plugin is a local workflow bundle over the repository’s existing runtime.

## What It Stores Locally

When you use the plugin through the supported local runtime, `deep-gvr` writes local state under the same runtime home used by the Hermes, Codex-local, and direct CLI surfaces. That home is selected through `DEEP_GVR_HOME` when set and otherwise falls back to the compatibility path under `${HERMES_HOME:-~/.hermes}/deep-gvr`:

- `${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/config.yaml`
- `${DEEP_GVR_HOME:-${HERMES_HOME:-~/.hermes}/deep-gvr}/sessions/<session_id>/`
- evidence, checkpoints, and analysis/formal artifacts under the session directory

## What It Sends Externally

`deep-gvr` may send prompts or verification requests to external services that you configure explicitly, including:

- the model provider selected by your runtime config and orchestrator backend
- optional Tier 2 remote backends such as Modal or SSH
- optional Tier 3 formal backends such as Aristotle, MathCode, or OpenGauss, if you enable them

The plugin itself does not introduce an additional cloud service or telemetry layer beyond those configured runtime dependencies.

## Operator Responsibility

You are responsible for:

- selecting and configuring model providers
- enabling only the backends you actually intend to use
- reviewing the evidence and artifacts written by the runtime

If you need stricter data-handling guarantees, keep the runtime on the local-only path and avoid enabling remote backends.
