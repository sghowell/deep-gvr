# Examples

These examples show the kinds of workflows `deep-gvr` is designed to support.

## 1. Symbolic / Math Example

Question:

```text
/deep-gvr "Show that d/dx (x^x) = x^x (ln x + 1), and explain the domain assumptions."
```

Typical path:

- Tier 1 checks the derivation structure and the handling of assumptions
- Tier 2 may use the symbolic-math adapter to confirm the derivative and simplify the resulting expression

Expected artifacts:

- evidence and checkpoint files
- symbolic analysis artifacts if Tier 2 is requested

## 2. Optimization Example

Question:

```text
/deep-gvr "Determine the minimum-weight assignment for a small cost matrix and justify why it is optimal."
```

Typical path:

- Tier 1 checks the reasoning and optimality claim
- Tier 2 uses the optimization adapter to solve the instance directly and verify the bound or optimum

Expected artifacts:

- optimization request and result artifacts
- a verifier report tied to the computed optimum

## 3. Quantum Analysis Example

Question:

```text
/deep-gvr "Explain why increasing surface-code distance can reduce logical error below threshold, and state the regime where that claim holds."
```

Typical path:

- Tier 1 checks literature grounding, scope, and threshold-regime discipline
- Tier 2 may invoke QEC benchmarking if the answer makes concrete quantitative claims

Expected artifacts:

- citation-aware Tier 1 reasoning
- QEC analysis artifacts when empirical claims are introduced

## 4. Formal Verification Example

Question:

```text
/deep-gvr "Sketch a proof that majority decoding for odd repetition codes corrects up to (d-1)/2 bit flips."
```

Typical path:

- Tier 1 checks the proof sketch for coherence
- Tier 3 is triggered because the core claim is formalizable
- Aristotle or MathCode handles the proof-oriented backend work

Expected artifacts:

- formal request artifact
- formal transport artifact
- formal lifecycle and result artifacts

## Reading the Output

In all of these cases, the final answer is only part of what you should inspect.

The most valuable outputs are often:

- the verifier report
- the explicit caveats
- the Tier 2 or Tier 3 artifacts
- the checkpointed session state if the run needs to be resumed
