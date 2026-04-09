# Domain Portfolio

`deep-gvr` is domain-agnostic at the architectural level, but it ships with a concrete OSS-first analysis portfolio.

## Core Scientific Families

| Family | Primary OSS tools | Best for |
|---|---|---|
| Symbolic math | SymPy | identities, derivatives, integrals, algebraic checks, asymptotics |
| Optimization | OR-Tools, SciPy, HiGHS | discrete optimization, linear-style programs, constraint solving |
| Dynamics | SciPy, QuTiP | ODE systems, observables, open-system and Hamiltonian evolution |

These families make `deep-gvr` broader than a quantum-only research tool.

## OSS Quantum Families

| Family | Primary OSS tools | Best for |
|---|---|---|
| QEC decoder benchmark | Stim, PyMatching | threshold-style studies, decoder comparisons, logical error trends |
| MBQC graph state | Graphix | graph-state reasoning, MBQC command-sequence analysis |
| Photonic linear optics | Perceval | photonic circuits, linear-optical components, detector/noise analysis |
| Neutral-atom control | Pulser | pulse schedules, programmable neutral-atom array control |
| Topological QEC design | tqec | topological layouts, logical-computation design automation |
| ZX rewrite verification | PyZX | circuit simplification, equivalence checking, ZX-based rewrites |

## How These Families Fit Tier 2

Tier 2 is a general analysis boundary, not a single simulator hook.

That means the same verification layer can request:

- symbolic checks for algebraic claims
- numerical optimization for objective or bound claims
- ODE or open-system evolution for dynamics claims
- domain-specific quantum analysis where the claim actually needs it

The adapter layer keeps these backends interchangeable without rewriting the core GVR loop.

## Interop, Not Primary Families

These ecosystems matter, but they are not the primary family names on the shipped analysis surface:

- Qiskit
- Cirq
- PennyLane

They are better understood as interoperability targets and future ecosystem bridges than as the first public abstraction layer.

## Future Candidates

These are meaningful OSS projects, but they are not required to understand the current release surface:

- Bloqade
- Qiskit QEC
- Mitiq
- pyGSTi
- Qualtran

## What This Means for Users

If you ask `deep-gvr` a question in one of these supported domains, the verifier can escalate into a domain-appropriate analysis backend instead of pretending prose alone is enough.

If your question falls outside them, Tier 1 still works, but deeper computational verification may be narrower or unavailable.
