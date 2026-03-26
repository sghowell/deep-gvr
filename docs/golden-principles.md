# Golden Principles

These principles are the mechanically enforced or intentionally repeated rules for early `deep-gvr` development.

## Harness Engineering Principles

- Keep humans at the intent and review layer. Keep Codex at the implementation and maintenance layer.
- Prefer repository-local instructions over chat-only context.
- Promote stable review feedback into docs, checks, or tests.
- Accept agent-authored code so long as it is correct, maintainable, and legible to future agent runs.

## Architecture Rules

- The Verifier is adversarial and isolated from the original problem framing.
- Tier 1 analytical verification always runs.
- Tier 2 and Tier 3 are selective, claim-driven additions.
- Adapters own backend dispatch. Prompts should not encode backend-specific logic.
- Evidence is append-only and machine-readable.
- The skill must work without patching Hermes itself.

## Git and Delivery Rules

- Use feature branches for all substantive work.
- Commit in sensible chunks with concise descriptive messages.
- Validate before merge and validate again after local merge.
- Push only validated integration results.
- Clean up integrated feature branches.

## Documentation Rules

- A new public interface or artifact shape must be reflected in docs, schema, template, and tests in the same branch.
- Execution plans are mandatory for non-trivial work.
- Capability unknowns must be captured as probes with a default and a fallback.
