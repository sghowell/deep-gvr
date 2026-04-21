# Contracts and Artifacts

This document defines the repo-level contract vocabulary shared across prompts, code, schemas, fixtures, and tests.

## Core Contracts

- `DeepGvrConfig`: loop settings, verification tiers, explicit orchestrator plus per-role model routing, evidence storage, domain defaults, backend runtime config for Tier 2 execution, and Tier 3 backend selection including local MathCode settings
- `SkillSessionSummary`: operator-facing result emitted by the `deep-gvr` command surface, including any observed delegated or Codex-native `capability_evidence`
- `BenchmarkCase`: one deterministic release-benchmark case with its expected verdict and expected tier path
- `BenchmarkReport`: recorded benchmark results plus release-readiness metrics
- `CandidateSolution`: generator or reviser output
- `VerificationReport`: verifier output with tiered results
- `AnalysisSpec`: normalized Tier 2 analysis request
- `AnalysisResults`: normalized Tier 2 analysis output
- `SimSpec`: internal Stim/PyMatching request used inside the `qec_decoder_benchmark` family
- `SimResults`: internal Stim/PyMatching output used inside the `qec_decoder_benchmark` family
- `FormalVerificationRequest`: orchestrator-mediated Tier 3 request to the selected formal backend
- `FormalProofLifecycle`: persisted Tier 3 proof-handle state for submission, polling, and resume
- `EvidenceRecord`: append-only record for one GVR phase transition, including branch identity, explicit escalation actions, the effective provider/model path, routing mode, and any fallback temperature
- `SessionCheckpoint`: resume-safe loop state for the last complete phase, including active and queued hypothesis branches
- `SessionIndex`: summary view of known sessions
- `HermesMemorySummary`: derived session summary persisted as a session artifact and mirrored into Hermes memory when enabled
- `ParallaxEvidenceManifest`: Parallax-compatible manifest derived from the checkpoint, evidence log, and artifact references
- `CapabilityProbeResult`: result of a readiness probe for a platform assumption
- `ReleasePreflightReport`: structural and operator-readiness report for the shipped Hermes release surface
- `CodexRemoteBootstrapReport`: rerunnable remote-machine bootstrap report for the Codex SSH/devbox path, including config-sync, install, and evidence-directory actions plus a nested remote preflight snapshot
- `CodexReviewQaExecutionReport`: repo-owned evidence bundle report for Codex pull-request review and public-docs visual QA workflows
- `CodexNativeDelegationEvaluationReport`: grounded evaluation of which deeper Codex-native delegation behaviors should stay runtime-owned, remain operator-pack surfaces, or remain explicitly product-managed
- `ReleasePublicationManifest`: checked-in publication bundle manifest for GitHub and agentskills.io release work
- `AutoImproveEvaluationReport`: isolated benchmark-and-policy comparison used to justify whether `auto_improve` should remain disabled by default

## Artifact Paths

- `schemas/*.json`: canonical JSON Schemas
- `templates/*.json`: sample artifacts used in tests
- `templates/config.template.yaml`: YAML form of the default runtime config written by install and CLI helpers
- `release/agentskills.publication.json`: checked-in publication bundle manifest validated against repo metadata
- `scripts/evaluate_auto_improve.py`: operator-facing evaluator for the `auto_improve` release policy
- `templates/auto_improve_evaluation.template.json`: canonical sample evaluation report
- `prompts/*.md`: role prompts aligned to the contract names
- `domain/*.md`: concise domain context cards
- `src/deep_gvr/cli.py`: repo-local command runtime for session start/resume
- `scripts/release_preflight.py`: operator-facing release preflight helper for install, config, provider, backend, and Tier 3 readiness
- `scripts/codex_remote_bootstrap.py`: operator-facing remote bootstrap helper for Codex SSH/devbox machines
- `scripts/codex_review_qa_execute.py`: operator-facing evidence-bundle helper for Codex review and visual-QA workflows
- `scripts/evaluate_codex_native_delegation.py`: operator-facing evaluator for the deeper Codex-native delegation boundary
- `templates/codex_remote_bootstrap.template.json`: canonical sample remote-bootstrap report
- `templates/codex_review_qa_execution.template.json`: canonical sample Codex review/QA execution report
- `templates/codex_native_delegation_evaluation.template.json`: canonical sample Codex-native delegation evaluation report
- `eval/known_problems.json`: deterministic release benchmark corpus, including core-science, OSS quantum analysis, and orchestration-required cases
- `eval/results/baseline_results.json`: committed benchmark evidence for the current repo baseline
- `eval/results/live/<run_id>/report.json`: live prompt-driven benchmark report
- `eval/results/live/<run_id>/cases/<case_id>/candidate_solution.json`: live generator or reviser output for one benchmark case
- `eval/results/live/<run_id>/cases/<case_id>/verification_report.json`: live verifier output for one benchmark case
- `eval/results/live/<run_id>/cases/<case_id>/role_transcripts.json`: Hermes prompt and response transcripts for one live benchmark case
- `eval/results/live/<run_id>/cases/<case_id>/case_result.json`: normalized per-case live benchmark summary
- `/tmp/deep-gvr-auto-improve-<run_id>/report.json`: default auto-improve evaluation report written outside the worktree
- `/tmp/deep-gvr-codex-native-delegation-<run_id>/report.json`: default Codex-native delegation evaluation report written outside the worktree
- `eval/results/live/<run_id>/sessions/<session_id>/checkpoint.json`: persisted Tier 1 state for a live benchmark session
- `sessions/<session_id>/artifacts/<timestamp>_run_orchestrator_transcript.json`: top-level CLI wrapper transcript artifact. Hermes runs record the delegated orchestrator exchange there; native Codex runs record one entry per role call, including selected routes, parsed response payloads, and any role-level errors
- `sessions/<session_id>/artifacts/<timestamp>_run_capability_evidence.json`: capability-evidence artifact emitted by the CLI wrapper when the runtime can report observed delegated or Codex-native execution evidence
- `sessions/<session_id>/checkpoint.json`: persisted Tier 1 loop state for resume
- `sessions/<session_id>/artifacts/session_memory_summary.json`: derived structured summary used for Hermes memory persistence
- `sessions/<session_id>/artifacts/parallax_manifest.json`: Parallax-compatible manifest for the session evidence set
- `sessions/<session_id>/artifacts/iteration_<n>_analysis_*.json`: persisted Tier 2 specs and normalized results
- `sessions/<session_id>/artifacts/iteration_<n>_formal_request.json`: persisted Tier 3 request routed to the formal backend
- `sessions/<session_id>/artifacts/iteration_<n>_formal_lifecycle.json`: persisted Tier 3 proof-handle state for pending or completed proof work
- `sessions/<session_id>/artifacts/iteration_<n>_formal_transport.json`: persisted Tier 3 transport transcript and backend-specific preflight details
- `sessions/<session_id>/artifacts/iteration_<n>_formal_results.json`: persisted Tier 3 returned formal results
- `~/.hermes/memories/MEMORY.md`: Hermes memory document that now receives namespaced deep-gvr session summaries when `persist_to_memory` is enabled

## Alignment Rules

- Field names must match across prompts, Python models, schemas, and fixtures.
- Config changes that affect effective model routing must update the routing helper, fixtures, and evidence examples in the same branch.
- Sample artifacts should be realistic enough to support smoke tests and contract review.
- Prompt changes that affect artifacts must update schemas and fixtures in the same branch.
- New public artifacts, including resume state, must have schema, template, and tests in the same branch.
- Tier 2 public contracts must use the generalized analysis vocabulary even when a specific adapter family internally wraps a narrower simulator contract.
