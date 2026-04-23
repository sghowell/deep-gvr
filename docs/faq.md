# FAQ

## Is deep-gvr a chatbot?

No. It is a verification-oriented research system built around structured challenge, evidence, and explicit failure modes.

## Does every run use Tier 2 or Tier 3?

No. Tier 1 always runs. Tier 2 and Tier 3 are selective and claim-driven.

## When does Tier 2 trigger?

Tier 2 is used when a claim benefits from executable checking: symbolic verification, optimization, numerical dynamics, QEC benchmarking, or other adapter-backed analysis.

## When does Tier 3 trigger?

Tier 3 is used for proof-oriented or formalizable claims, not for every technical answer.

## What are the shipped Tier 3 backends?

The standard release surface supports Aristotle, MathCode, and OpenGauss. Aristotle is the submission/poll/resume path; MathCode and OpenGauss are bounded local CLI paths.

## Is Codex supported?

Yes. Codex local is a supported first-class operator surface for `deep-gvr`.

## Does the Codex surface replace Hermes?

It can. If you set `runtime.orchestrator_backend=codex_local`, the runtime executes through Codex natively. Hermes is still supported and remains the default backend in the checked-in config template.

## Is deep-gvr only for quantum computing?

No. Quantum work is an important part of the portfolio, but the current analysis surface also includes symbolic math, optimization, and dynamics.

## What is local and what can be remote?

The default path is local. Some Tier 2 backends can also use Modal or SSH-backed execution if the operator config enables them.

## Is live behavior deterministic?

No. Live runs depend on real model routes and external systems. The repo also ships a deterministic benchmark path for stable regression checking.

## What external dependencies matter most?

The main ones are:

- the selected orchestrator backend (`hermes` or `codex_local`)
- the configured model provider route
- optional Tier 2 backend tools and libraries
- optional Tier 3 backend setup such as Aristotle MCP, a local MathCode checkout, or a local configured OpenGauss runtime

## What happens when deep-gvr cannot verify something?

It should say so explicitly. A structured `CANNOT_VERIFY`, a caveated answer, or a failed deeper-tier artifact is a correct outcome when the evidence does not support a stronger claim.
