# deep-gvr Plugin Privacy

The `deep-gvr` Codex plugin is a local workflow bundle over the repository’s existing runtime.

## What It Stores Locally

When you use the plugin through the supported local runtime, `deep-gvr` writes local state under the same paths used by the Hermes and CLI surfaces:

- `~/.hermes/deep-gvr/config.yaml`
- `~/.hermes/deep-gvr/sessions/<session_id>/`
- evidence, checkpoints, and analysis/formal artifacts under the session directory

## What It Sends Externally

`deep-gvr` may send prompts or verification requests to external services that you configure explicitly, including:

- the model provider selected by your Hermes runtime
- optional Tier 2 remote backends such as Modal or SSH
- optional Tier 3 formal backends such as Aristotle or MathCode, if you enable them

The plugin itself does not introduce an additional cloud service or telemetry layer beyond those configured runtime dependencies.

## Operator Responsibility

You are responsible for:

- selecting and configuring model providers
- enabling only the backends you actually intend to use
- reviewing the evidence and artifacts written by the runtime

If you need stricter data-handling guarantees, keep the runtime on the local-only path and avoid enabling remote backends.
