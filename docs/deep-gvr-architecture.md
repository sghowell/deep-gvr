# deep-gvr: Architecture and Design Document

**Project:** deep-gvr
**Organization:** Zetetic Works Research Corporation
**Repository:** `zetetic-works/deep-gvr`
**License:** MIT
**Status:** Design, pre-implementation
**Version:** 0.1.0 (initial release target)
**Date:** March 26, 2026
**Authors:** Sean, with Claude

---

## 1. Overview

### 1.1 What deep-gvr Is

deep-gvr is an autonomous scientific research skill for Hermes Agent that implements a Generator-Verifier-Reviser (GVR) loop with tiered verification. It is architecturally inspired by DeepMind's Aletheia agent but designed to be lightweight, model-agnostic, open-source, and immediately usable on existing infrastructure.

Given a research question, deep-gvr:

1. **Generates** candidate solutions, hypotheses, or proof sketches grounded in literature and prior results
2. **Verifies** those candidates through a decoupled adversarial process using up to three verification tiers: analytical (natural language reasoning), empirical (simulation), and formal (Lean 4 theorem proving)
3. **Revises** candidates based on specific flaws identified by the Verifier, iterating until the result passes verification, the system admits failure, or the iteration budget is exhausted

The first target domain is fault-tolerant quantum computing research, specifically photonic fusion-based quantum computing (FBQC) and quantum error correction (QEC). The architecture is domain-agnostic; the domain specialization lives entirely in the prompts and simulator adapters.

### 1.2 What deep-gvr Is Not

- Not a replacement for Lem (Zetetic Works' planned native scientific agent). deep-gvr is Lem's cognitive loop running on borrowed infrastructure (Hermes Agent) as a proof of concept and standalone tool.
- Not a fine-tuned model. deep-gvr is a harness (in the sense of the Zetetic Works "Harness Engineering" framework). It orchestrates existing models through structured adversarial interaction.
- Not a formal methods tool. Formal verification (Tier 3) is available but not mandatory. Most use cases will rely primarily on analytical and empirical verification.

### 1.3 Design Principles

1. **Decoupled verification is the core insight.** The Generator and Verifier must be separate agents with isolated contexts. Ideally, they use different models. This is the single most important architectural decision, inherited from Aletheia.

2. **Tiered verification, not mandatory formalization.** Not every claim is amenable to formal proof. The Verifier selects the appropriate verification tier based on claim type. Analytical verification (Tier 1) always runs. Empirical (Tier 2) and formal (Tier 3) run when applicable.

3. **Lightweight means no code changes to Hermes.** deep-gvr is a skill bundle. It uses Hermes's existing primitives: `delegate_task` for the GVR roles, `terminal` for simulation, MCP for formal verification, memory for evidence persistence. Nothing is patched or forked.

4. **Simulator-agnostic from day one.** The Simulator subagent dispatches through an adapter layer. Swapping Stim for a custom FBQC simulator requires only a new adapter, not a prompt rewrite.

5. **Admit failure explicitly.** A system that always claims to have solved the problem is worse than useless. The Verifier can output CANNOT VERIFY, and the Orchestrator can halt with a structured failure report. This is a reliability feature, not a limitation.

6. **Evidence is a first-class artifact.** Every GVR iteration is recorded. The evidence trail is append-only, machine-parseable, and human-readable. Research is cumulative.

### 1.4 Relationship to Aletheia

| Aletheia (DeepMind) | deep-gvr (Zetetic Works) |
|---|---|
| Gemini Deep Think base model | Any model via OpenRouter / Nous Portal / OpenAI |
| Single model for all GVR roles | Cross-model verification (different providers for G vs V) |
| Natural language verification only | Tiered: analytical + empirical (Stim) + formal (Aristotle/OpenGauss) |
| Google Search for literature | Hermes web_search + web_fetch |
| Proprietary, closed | MIT, open source |
| Standalone system | Hermes Agent skill (agentskills.io compatible) |
| Math-focused | Science-focused (initial: quantum computing) |
| Inference-time scaling (proprietary) | Model-level reasoning (extended thinking modes where available) |

---

## 2. Architecture

### 2.1 System Context

```
┌──────────────────────────────────────────────────────────────────┐
│                         User                                      │
│  (CLI, Telegram, Discord, Slack, WhatsApp)                       │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Hermes Agent                                   │
│                                                                   │
│  ┌─────────────┐  ┌──────────┐  ┌────────┐  ┌───────────────┐  │
│  │ Memory      │  │ Skills   │  │ MCP    │  │ Terminal      │  │
│  │ (FTS5)      │  │ System   │  │ Client │  │ (local/ssh/   │  │
│  │             │  │          │  │        │  │  modal/sing.) │  │
│  └─────────────┘  └────┬─────┘  └────┬───┘  └──────┬────────┘  │
│                        │             │              │            │
│                   ┌────┴─────────────┴──────────────┴────┐      │
│                   │          deep-gvr skill               │      │
│                   │       (Orchestrator procedure)        │      │
│                   └──────────────────────────────────────┘      │
│                                                                   │
│  delegate_task ──► ┌───────────┐ ┌───────────┐ ┌───────────┐   │
│                    │ Generator │ │ Verifier  │ │ Reviser   │   │
│                    │ subagent  │ │ subagent  │ │ subagent  │   │
│                    └───────────┘ └─────┬─────┘ └───────────┘   │
│                                        │                         │
│  delegate_task ──► ┌───────────┐       │                         │
│                    │ Simulator │       │                         │
│                    │ subagent  │       │                         │
│                    └─────┬─────┘       │                         │
└──────────┬───────────────┼─────────────┼─────────────────────────┘
           │               │             │
           ▼               ▼             ▼
    ┌──────────┐    ┌──────────┐  ┌──────────────┐
    │ Hermes   │    │ Stim /   │  │ Aristotle    │
    │ Memory   │    │ Custom   │  │ MCP Server   │
    │ Store    │    │ Simulator│  │              │
    └──────────┘    └──────────┘  │ OpenGauss    │
                                  │ (lean4-skills)│
                                  └──────────────┘
```

### 2.2 Component Architecture

deep-gvr has six logical components. Four are implemented as Hermes subagents (spawned via `delegate_task`), one is the orchestration procedure itself (the SKILL.md), and one is the evidence system (file-based).

#### 2.2.1 Orchestrator (SKILL.md)

The Orchestrator is not a subagent. It is the SKILL.md procedure that the parent Hermes agent follows. It controls:

- Problem intake and decomposition
- Literature grounding (web search before generation)
- GVR loop control (dispatch, iteration, termination)
- Evidence recording
- Session checkpoint and resume
- User communication (progress updates, failure reports, results)

The Orchestrator runs in the parent agent's context. This means it has access to Hermes memory, user interaction, and the full tool registry. The GVR subagents do not.

#### 2.2.2 Generator (subagent)

Spawned via `delegate_task`. Receives:
- The research problem statement
- Literature context gathered by the Orchestrator
- Prior failed attempts and Verifier feedback (on revision cycles)
- The Generator system prompt (from `prompts/generator.md`)

Produces:
- A candidate solution in structured format (see Section 5.1)

Has access to: `web_search`, `web_fetch`, `terminal`, `read_file`, `write_file`
Does NOT have access to: `delegate_task`, `memory`, `execute_code`, `clarify`, `send_message`

#### 2.2.3 Verifier (subagent)

Spawned via `delegate_task`. Receives:
- The Generator's candidate solution (ONLY — no problem context bleed from the Orchestrator)
- The Verifier system prompt (from `prompts/verifier.md`)
- Instructions on which verification tiers are available and configured

Produces:
- A verification verdict: VERIFIED, FLAWS_FOUND, or CANNOT_VERIFY
- Tier-specific results (see Section 5.2)
- Specific flaw descriptions (if FLAWS_FOUND)

Has access to: `web_search`, `web_fetch`, `terminal`, `read_file`, `write_file`, MCP tools (Aristotle)
Does NOT have access to: `delegate_task`, `memory`, `execute_code`, `clarify`, `send_message`

**Critical isolation property:** The Verifier receives the Generator's *output* but NOT the original problem statement or the Orchestrator's reasoning about it. This forces the Verifier to evaluate the candidate on its own merits rather than being primed by the Orchestrator's framing. The candidate must be self-contained. If the Verifier cannot understand the candidate without additional context, that is itself a flaw (the solution is underspecified).

#### 2.2.4 Reviser (subagent)

Spawned via `delegate_task`. Receives:
- The Generator's candidate solution
- The Verifier's flaw report
- The Reviser system prompt (from `prompts/reviser.md`)
- Instruction to address each identified flaw specifically

Produces:
- A revised candidate solution in the same structured format as the Generator

Has access to: same as Generator

#### 2.2.5 Simulator (subagent)

Spawned via `delegate_task` when the Verifier (or Orchestrator) requests empirical verification. Receives:
- A simulation specification: what to simulate, what parameters, what to measure
- The Simulator system prompt (from `prompts/simulator.md`)

Produces:
- Simulation results in structured JSON
- Interpretation of results relative to the claim being verified

Has access to: `terminal`, `read_file`, `write_file`

The Simulator subagent does NOT invoke Stim directly. It invokes the **simulator adapter** (see Section 4), which handles backend dispatch and output normalization.

#### 2.2.6 Evidence System (file-based)

Not a subagent. A set of files managed by the Orchestrator:

- **Evidence log** (`~/.hermes/deep-gvr/sessions/<session_id>.jsonl`): Append-only JSON Lines file. One line per GVR iteration.
- **Session index** (`~/.hermes/deep-gvr/sessions/index.json`): Maps session IDs to metadata (problem statement, start time, status, result summary).
- **Artifacts directory** (`~/.hermes/deep-gvr/sessions/<session_id>/artifacts/`): Simulation outputs, Lean files, intermediate results.

### 2.3 GVR Loop Control Flow

```
START
  │
  ▼
┌─────────────────────────────────┐
│ 1. PROBLEM INTAKE               │
│    Parse research question       │
│    Identify domain, claim types  │
│    Initialize session            │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 2. LITERATURE GROUNDING          │
│    web_search for relevant       │
│    papers, known results,        │
│    existing bounds               │
│    Summarize context             │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 3. GENERATE                      │
│    delegate_task → Generator     │
│    Input: problem + lit context  │
│    Output: candidate solution    │◄─────────────────────┐
└──────────────┬──────────────────┘                       │
               │                                          │
               ▼                                          │
┌─────────────────────────────────┐                       │
│ 4. VERIFY                        │                      │
│    delegate_task → Verifier      │                      │
│    Input: candidate ONLY         │                      │
│    Tier selection:               │                      │
│      T1: analytical (always)     │                      │
│      T2: empirical (if numeric)  │                      │
│      T3: formal (if provable)    │                      │
│    Output: verdict + details     │                      │
└──────────────┬──────────────────┘                       │
               │                                          │
               ▼                                          │
         ┌─────────────┐                                  │
         │   Verdict?   │                                  │
         └──────┬──────┘                                  │
                │                                          │
     ┌──────────┼──────────────┐                          │
     │          │              │                           │
     ▼          ▼              ▼                           │
  VERIFIED   FLAWS_FOUND   CANNOT_VERIFY                  │
     │          │              │                           │
     │          ▼              ▼                           │
     │   ┌────────────┐  ┌────────────┐                   │
     │   │ iteration  │  │ Log and    │                   │
     │   │ < max?     │  │ report     │                   │
     │   └─────┬──────┘  │ inability  │                   │
     │         │         └────────────┘                   │
     │    yes  │  no                                      │
     │         │   │                                      │
     │         ▼   ▼                                      │
     │   ┌──────────────┐  ┌──────────────┐              │
     │   │ 5. REVISE     │  │ Try alt.     │              │
     │   │ delegate_task │  │ approach?    │              │
     │   │ → Reviser     │  │ (if config'd)│              │
     │   │ Input: cand.  │  └──────────────┘              │
     │   │   + flaws     │                                │
     │   │ Output: rev.  │                                │
     │   │   candidate   │────────────────────────────────┘
     │   └──────────────┘
     │         (loops back to VERIFY with revised candidate)
     │
     ▼
┌─────────────────────────────────┐
│ 6. OUTPUT                        │
│    Record final evidence         │
│    Persist to Hermes memory      │
│    Return result to user         │
│    Optional: formalize in Lean   │
└─────────────────────────────────┘
```

### 2.4 Cross-Model Verification Strategy

A key enhancement over Aletheia: the Generator and Verifier should use *different language models* from *different providers* when possible. This decorrelates their failure modes. If both roles use the same model, they share blind spots — the Verifier is likely to miss the same errors the Generator made, because they arise from the same training distribution.

**Default model routing (configurable):**

| Role | Primary | Fallback |
|---|---|---|
| Orchestrator | User's configured Hermes model | — |
| Generator | Claude Sonnet/Opus (OpenRouter) | DeepSeek-R1 (OpenRouter) |
| Verifier | DeepSeek-R1 (OpenRouter) | Claude Sonnet/Opus (OpenRouter) |
| Reviser | Same provider as Generator | — |
| Simulator | User's configured Hermes model | — |

The key constraint: **Generator and Verifier must not use the same model.** If only one provider is available, use different model variants (e.g., claude-sonnet vs claude-opus) or different temperature settings as a weaker form of decorrelation.

**Implementation approach:**

Hermes's `delegate_task` spawns subagents that inherit the parent's model configuration. Per-subagent model routing is not natively supported as of March 2026. Two implementation paths:

1. **Preferred: Hermes config override.** Investigate whether `delegate_task` accepts model configuration in its parameters. If so, pass model overrides per role. This may require an upstream PR.

2. **Fallback: PTC wrapper.** The Orchestrator uses `execute_code` to make direct API calls (via OpenRouter/OpenAI SDK) with explicit model selection, then passes the result to a subagent for structured post-processing. This is more complex but works without Hermes modifications.

3. **Minimal fallback: Temperature decorrelation.** If neither of the above works, run both roles on the same model but with different system prompts and temperatures (Generator: higher temperature for creative exploration; Verifier: lower temperature for precise analysis). This is the weakest decorrelation strategy.

**This is the highest-priority architectural question to resolve during implementation.**

---

## 3. Verification Tiers

### 3.1 Tier 1: Analytical Verification (Natural Language)

**Always runs.** The Verifier performs structured reasoning about the candidate:

- **Logical consistency:** Does the argument follow? Are there circular dependencies, unstated assumptions, or non-sequiturs?
- **Citation verification:** Are referenced papers real? Do they actually say what the candidate claims? (Uses `web_search` to check.)
- **Sanity checks:** Are claimed results physically plausible? Do numerical values fall within expected ranges?
- **Completeness:** Does the solution address all parts of the problem? Are there obvious gaps?
- **Overclaiming:** Does the conclusion follow from the evidence presented, or does it claim more than is justified?

**Output format (Tier 1):**
```json
{
  "tier": 1,
  "method": "analytical",
  "checks": [
    {
      "check": "logical_consistency",
      "status": "pass" | "fail" | "uncertain",
      "detail": "string"
    },
    ...
  ],
  "overall": "VERIFIED" | "FLAWS_FOUND" | "CANNOT_VERIFY",
  "flaws": ["string", ...],
  "caveats": ["string", ...]
}
```

### 3.2 Tier 2: Empirical Verification (Simulation)

**Triggered when** the candidate makes quantitative predictions about physical systems, performance metrics, or computational results that can be tested numerically.

Examples of claims that trigger Tier 2:
- "This architecture achieves a threshold of 0.7% under circuit-level noise"
- "The logical error rate scales as exp(-αd) with α > 0.5"
- "The decoder runs in O(n log n) time" (can be empirically profiled)
- "Fusion success probability exceeds 0.5 with this resource state"

The Verifier requests empirical verification from the Orchestrator, which delegates to the Simulator subagent. The Verifier then interprets the simulation results.

**Flow:**
```
Verifier identifies empirical claim
  → Verifier outputs NEEDS_SIMULATION with simulation spec
  → Orchestrator receives this, delegates to Simulator subagent
  → Simulator invokes adapter → Stim (or custom simulator)
  → Simulator returns structured results
  → Orchestrator passes results back to Verifier (or spawns new Verifier with results)
  → Verifier incorporates empirical evidence into verdict
```

Note: Because Hermes subagents can't delegate to other subagents, the Verifier cannot directly invoke the Simulator. The Orchestrator mediates. This adds one round-trip but preserves the depth-2 delegation limit.

**Output format (Tier 2):**
```json
{
  "tier": 2,
  "method": "empirical",
  "simulator": "stim" | "custom",
  "parameters": {
    "code": "surface_code",
    "distance": 7,
    "noise_model": "depolarizing",
    "error_rate": 0.01,
    "decoder": "pymatching",
    "shots": 100000
  },
  "results": {
    "logical_error_rate": 2.3e-4,
    "physical_error_rate": 0.01,
    "threshold_estimate": 0.0089,
    "confidence_interval": [0.0085, 0.0093]
  },
  "claim_supported": true | false,
  "interpretation": "string"
}
```

### 3.3 Tier 3: Formal Verification (Lean 4)

**Triggered when** the candidate contains precise mathematical statements that are amenable to formalization: theorem statements, bounds proofs, complexity arguments, code distance proofs, logical operator constructions.

**Not triggered for:**
- Empirical claims (use Tier 2)
- Heuristic arguments ("we expect this to work because...")
- Claims about experimental results
- Software architecture decisions

The Verifier identifies formalizable claims and, if Tier 3 is enabled and the ARISTOTLE_API_KEY is configured, attempts formalization via the Aristotle MCP server or OpenGauss.

**Two verification backends:**

| Backend | Invocation | Best For |
|---|---|---|
| Aristotle MCP | `prove` / `formalize` MCP tools | Single theorems, fire-and-forget, hard problems |
| OpenGauss | `/autoprove` / `/autoformalize` skill commands | Iterative proof development, project-scoped work |

For v0.1, Aristotle MCP is the primary Tier 3 backend (simpler integration, no local Lean toolchain required). OpenGauss integration is Phase 2.

**Output format (Tier 3):**
```json
{
  "tier": 3,
  "method": "formal",
  "backend": "aristotle" | "opengauss",
  "claim": "string (the mathematical statement)",
  "lean_code": "string (if generated)",
  "proof_status": "proved" | "disproved" | "timeout" | "error",
  "proof_time_seconds": 180,
  "details": "string"
}
```

### 3.4 Tier Selection Logic

The Verifier applies tiers based on claim type analysis. The selection logic is encoded in the Verifier prompt:

```
For each substantive claim in the candidate:

1. Is it a precise mathematical statement (theorem, lemma, bound)?
   → Mark for Tier 3 (if configured and available)
   → ALSO apply Tier 1

2. Is it a quantitative prediction about a physical or computational system?
   → Mark for Tier 2
   → ALSO apply Tier 1

3. Is it a qualitative argument, design rationale, or literature claim?
   → Tier 1 only

Apply all applicable tiers. A claim that fails ANY tier is a flaw.
A claim that passes Tier 1 but is marked for Tier 2/3 and those
tiers are unavailable gets a caveat, not a failure.
```

---

## 4. Simulator Adapter Layer

### 4.1 Design

The adapter layer sits between the Simulator subagent and the actual simulation infrastructure. It provides a stable interface so that:

- The Simulator subagent prompt doesn't need to change when simulators change
- New simulators plug in by adding a new adapter, not by modifying existing code
- Backend dispatch (local/Modal/SSH) is handled transparently

### 4.2 Adapter Interface

Every adapter implements the same CLI contract:

```bash
python adapters/<adapter_name>.py \
  --spec <spec_file.json> \
  --backend local|modal|ssh \
  --output <results_file.json>
```

**Spec file schema (input):**
```json
{
  "simulator": "stim",
  "task": {
    "code": "surface_code",
    "task_type": "rotated_memory_z",
    "distance": [3, 5, 7, 9, 11],
    "rounds_per_distance": "2d",
    "noise_model": "depolarizing",
    "error_rates": [0.001, 0.003, 0.005, 0.007, 0.009, 0.011],
    "decoder": "pymatching",
    "shots_per_point": 100000
  },
  "resources": {
    "timeout_seconds": 3600,
    "max_parallel": 4
  }
}
```

**Results file schema (output):**
```json
{
  "simulator": "stim",
  "adapter_version": "0.1.0",
  "timestamp": "2026-03-26T10:30:00Z",
  "runtime_seconds": 245.3,
  "backend": "local",
  "data": [
    {
      "distance": 7,
      "rounds": 14,
      "physical_error_rate": 0.005,
      "logical_error_rate": 1.2e-4,
      "shots": 100000,
      "errors_observed": 12,
      "decoder": "pymatching"
    },
    ...
  ],
  "analysis": {
    "threshold_estimate": 0.0089,
    "threshold_method": "crossing_point",
    "below_threshold_distances": [7, 9, 11],
    "scaling_exponent": null
  },
  "errors": []
}
```

### 4.3 Stim Adapter (v0.1)

The initial adapter wraps Stim's CLI tools and PyMatching:

```python
# adapters/stim_adapter.py (conceptual structure)

class StimAdapter:
    def run(self, spec: SimSpec, backend: str) -> SimResults:
        if backend == "local":
            return self._run_local(spec)
        elif backend == "modal":
            return self._run_modal(spec)
        elif backend == "ssh":
            return self._run_ssh(spec)

    def _run_local(self, spec: SimSpec) -> SimResults:
        results = []
        for distance in spec.task.distance:
            for error_rate in spec.task.error_rates:
                circuit = self._generate_circuit(spec, distance, error_rate)
                detections = self._sample(circuit, spec.task.shots_per_point)
                logical_errors = self._decode(detections, spec.task.decoder)
                results.append(DataPoint(...))
        return SimResults(data=results, analysis=self._analyze(results))

    def _generate_circuit(self, spec, distance, error_rate) -> str:
        # Invokes: stim gen --code ... --distance ... --after_clifford_depolarization ...
        ...

    def _sample(self, circuit, shots) -> bytes:
        # Invokes: stim detect --shots ... < circuit.stim
        ...

    def _decode(self, detections, decoder_type) -> int:
        # Invokes PyMatching or other decoder
        ...
```

### 4.4 Future Adapters

Custom FBQC simulators plug in through the same interface:

```
adapters/
  stim_adapter.py          # v0.1 — surface code, stabilizer circuits
  fbqc_adapter.py          # future — fusion network topology simulators
  decoder_adapter.py       # future — ML decoder training/evaluation
  resource_state_adapter.py # future — photonic resource state optimization
```

Each adapter is a standalone Python module. The Simulator subagent selects the adapter based on the simulation spec's `simulator` field.

### 4.5 Backend Dispatch

All adapters support three backends:

**Local:** Direct subprocess invocation. No additional infrastructure needed. Suitable for small simulations (< 10 minutes).

**Modal:** Wraps the simulation in a Modal function for serverless GPU execution. Requires `modal` CLI configured. The adapter generates a Modal stub, deploys, and polls for results.

```bash
# Conceptual Modal dispatch
modal run adapters/modal_stubs/stim_modal.py \
  --spec spec.json --output results.json
```

**SSH:** Forwards the simulation command to a remote host via the Hermes SSH terminal backend. The adapter constructs the remote command, ships the spec file, runs the simulation, and retrieves results.

```bash
# Conceptual SSH dispatch (via Hermes terminal)
scp spec.json user@gpu-node:/tmp/
ssh user@gpu-node "cd /path/to/sim && python run.py --spec /tmp/spec.json --output /tmp/results.json"
scp user@gpu-node:/tmp/results.json ./results.json
```

---

## 5. Data Schemas

### 5.1 Generator Output Schema

The Generator must produce output in this structured format. This is enforced by the Generator prompt.

```
## Candidate Solution

### Hypothesis
[Clear, falsifiable statement of what is being claimed]

### Approach
[High-level strategy: what method, what tools, what prior work it builds on]

### Technical Details
[Step-by-step argument, proof sketch, or analysis]
[Mathematical statements should be clearly delineated]
[Quantitative predictions should include expected values and conditions]

### Expected Results
[What the hypothesis predicts, in testable terms]

### Assumptions
[Explicit list of assumptions made]
[Physical parameters assumed (noise rates, loss rates, etc.)]
[Mathematical assumptions (smoothness, boundedness, etc.)]

### Limitations
[What this solution does NOT address]
[Known weaknesses or gaps]

### References
[Papers, results, or prior work cited]
[Each reference should be verifiable via web search]
```

### 5.2 Verifier Output Schema

```
## Verification Report

### Verdict: [VERIFIED | FLAWS_FOUND | CANNOT_VERIFY]

### Tier 1: Analytical Verification
[Always present]
- Logical consistency: [PASS/FAIL/UNCERTAIN — detail]
- Citation validity: [PASS/FAIL/UNCERTAIN — detail]
- Physical plausibility: [PASS/FAIL/UNCERTAIN — detail]
- Completeness: [PASS/FAIL/UNCERTAIN — detail]
- Overclaiming: [PASS/FAIL/UNCERTAIN — detail]

### Tier 2: Empirical Verification
[Present if triggered]
- Simulation requested: [yes/no — reason]
- If yes: NEEDS_SIMULATION with spec: [simulation specification]
- If results available: [interpretation]

### Tier 3: Formal Verification
[Present if triggered]
- Formalizable claims identified: [list]
- Formalization attempted: [yes/no — reason]
- Results: [per-claim status]

### Flaws (if FLAWS_FOUND)
1. [Specific flaw description — what is wrong and why]
2. [Specific flaw description]
...

### Caveats (if VERIFIED)
- [Things that are technically correct but should be noted]

### Cannot Verify Reason (if CANNOT_VERIFY)
[Specific explanation of what blocked verification]
```

### 5.3 Evidence Record Schema (JSON Lines)

Each line in the session's `.jsonl` file:

```json
{
  "iteration": 1,
  "timestamp": "2026-03-26T10:30:00Z",
  "phase": "generate" | "verify" | "revise" | "simulate",
  "input_summary": "string (truncated input description)",
  "output_summary": "string (truncated output description)",
  "verdict": null | "VERIFIED" | "FLAWS_FOUND" | "CANNOT_VERIFY",
  "tiers_applied": [1] | [1, 2] | [1, 3] | [1, 2, 3],
  "flaws": ["string", ...],
  "simulation_results": null | { ... },
  "formal_verification_results": null | { ... },
  "model_used": "claude-sonnet-4-20250514",
  "provider": "openrouter",
  "tokens_in": 4500,
  "tokens_out": 3200,
  "duration_seconds": 45.2,
  "artifacts": ["path/to/file", ...]
}
```

### 5.4 Session Index Schema

```json
{
  "sessions": {
    "session_abc123": {
      "problem": "Determine the threshold of surface code under biased noise...",
      "domain": "qec",
      "started": "2026-03-26T10:00:00Z",
      "last_updated": "2026-03-26T11:30:00Z",
      "status": "completed" | "in_progress" | "failed" | "paused",
      "iterations": 3,
      "final_verdict": "VERIFIED",
      "result_summary": "string",
      "evidence_file": "sessions/session_abc123.jsonl"
    }
  }
}
```

---

## 6. Prompt Architecture

The prompts are the most critical engineering artifact in deep-gvr. Each prompt is a separate markdown file in the `prompts/` directory, loaded by the Orchestrator and injected into the corresponding `delegate_task` call.

### 6.1 Generator Prompt (`prompts/generator.md`)

**Core directives:**

- You are a scientific research agent specializing in [domain context injected by Orchestrator].
- Your task is to produce a candidate solution to the research problem provided.
- Ground your reasoning in published results. Cite specific papers by author and year. Do not fabricate citations.
- Propose multiple approaches when the path is not obvious. Evaluate their tradeoffs before committing to one.
- Your output must follow the Candidate Solution format exactly (see Section 5.1).
- Be explicit about assumptions. Every assumption is a potential point of failure in verification.
- Include quantitative predictions where possible. "This should work" is not a prediction. "The logical error rate should be below 10^-4 at distance 7 with physical error rate 0.005" is.
- If you are not confident in your solution, say so. A clearly-flagged uncertain result is more valuable than an overconfident wrong one.

**Domain context injection point:**
```
[The Orchestrator inserts a brief domain context here, e.g.:]

Domain: Fault-tolerant quantum computing, specifically photonic
fusion-based quantum computing (FBQC) and quantum error correction (QEC).

Key concepts: surface codes, color codes, Floquet codes, fusion networks,
photon loss, detector efficiency, MWPM/Union-Find decoding, resource states,
GHZ states, linear optical Bell measurements, threshold theorems.

Current research frontier: [Orchestrator fills from literature search]
```

### 6.2 Verifier Prompt (`prompts/verifier.md`)

**Core directives:**

- You are an adversarial scientific reviewer. Your purpose is to find flaws in the candidate solution you have been given.
- **You are NOT the author of this solution. You have no investment in it being correct. Your job is to break it.**
- Assume the solution is wrong until you have convinced yourself otherwise through systematic checking.
- You must evaluate the candidate on its own merits. You have NOT been given the original problem statement. If the candidate is not self-contained enough to evaluate, that is itself a flaw (underspecification).
- Apply verification systematically using the tier framework:
  - **Tier 1 (Analytical):** Always apply. Check logical consistency, citation validity, physical plausibility, completeness, and overclaiming.
  - **Tier 2 (Empirical):** If the candidate makes quantitative predictions about physical or computational systems, request simulation by outputting NEEDS_SIMULATION with a precise simulation specification.
  - **Tier 3 (Formal):** If the candidate contains precise mathematical statements (theorems, bounds, proofs), and formal verification is available, attempt formalization via the Aristotle MCP tools (`prove`, `formalize`).
- **Output your verdict in exactly one of three forms:**
  - `VERIFIED` — you found no flaws after systematic checking. Include caveats for anything uncertain.
  - `FLAWS_FOUND` — you found specific, actionable flaws. List each one clearly.
  - `CANNOT_VERIFY` — you lack the ability or information to verify this candidate. Explain specifically what is blocking you.
- **Anti-sycophancy guardrails:**
  - Do not praise the solution. Analysis only.
  - "This is a reasonable approach" is not verification. Check the actual claims.
  - If you find yourself writing "this looks correct," stop and identify what specific checks you performed to reach that conclusion.
  - A VERIFIED verdict with no specific checks described is not acceptable. List what you checked.

### 6.3 Reviser Prompt (`prompts/reviser.md`)

**Core directives:**

- You have been given a candidate solution and a list of specific flaws identified by a reviewer.
- Your task is to produce a revised candidate that addresses each identified flaw.
- **Address flaws one by one.** For each flaw, explain what was wrong and what you changed.
- **Do not rewrite the entire solution.** Preserve what was correct. Modify only what is necessary to fix the identified flaws.
- If a flaw requires a fundamentally different approach, say so explicitly rather than patching a broken foundation.
- Your output must follow the same Candidate Solution format as the original.
- Include a "Revision Notes" section that maps each flaw to the change made:
  ```
  ### Revision Notes
  - Flaw 1: [original flaw] → Fixed by: [what changed]
  - Flaw 2: [original flaw] → Fixed by: [what changed]
  ```

### 6.4 Simulator Prompt (`prompts/simulator.md`)

**Core directives:**

- You have been given a simulation specification describing what to simulate and what to measure.
- Your task is to invoke the appropriate simulator adapter and interpret the results.
- Use the `terminal` tool to run the adapter:
  ```bash
  python adapters/<simulator>_adapter.py --spec spec.json --backend <backend> --output results.json
  ```
- After the simulation completes, read the results file and provide:
  1. A summary of the raw results
  2. Whether the results support or contradict the claim being tested
  3. Any unexpected findings or anomalies
  4. Confidence assessment: was the simulation run with sufficient statistics (shots), resolution (parameter sweep), and appropriate controls?
- If the simulation fails (timeout, error, resource limit), report the failure clearly. Do not fabricate results.
- If the simulation specification is ambiguous or insufficient, report what is missing.

---

## 7. File Structure

```
deep-gvr/
├── SKILL.md                    # Orchestrator procedure (main skill file)
├── README.md                   # Project overview, installation, usage
├── LICENSE                     # MIT
├── ARCHITECTURE.md             # This document
│
├── prompts/
│   ├── generator.md            # Generator subagent system prompt
│   ├── verifier.md             # Verifier subagent system prompt
│   ├── reviser.md              # Reviser subagent system prompt
│   └── simulator.md            # Simulator subagent system prompt
│
├── adapters/
│   ├── __init__.py
│   ├── base_adapter.py         # Abstract adapter interface
│   ├── stim_adapter.py         # Stim/PyMatching adapter (v0.1)
│   └── modal_stubs/
│       └── stim_modal.py       # Modal deployment stub for Stim
│
├── schemas/
│   ├── sim_spec.schema.json    # Simulation spec JSON schema
│   ├── sim_results.schema.json # Simulation results JSON schema
│   └── evidence.schema.json    # Evidence record JSON schema
│
├── templates/
│   ├── evidence_record.json    # Example evidence record
│   └── session_index.json      # Example session index
│
├── domain/
│   ├── qec_context.md          # QEC domain context for prompt injection
│   ├── fbqc_context.md         # FBQC domain context for prompt injection
│   └── known_results.md        # Reference: known thresholds, bounds, results
│
├── eval/
│   ├── README.md               # Evaluation methodology
│   ├── known_problems.json     # Benchmark problems with known answers
│   └── run_eval.py             # Evaluation harness
│
└── scripts/
    ├── install.sh              # Installs deep-gvr into ~/.hermes/skills/
    └── setup_mcp.sh            # Configures Aristotle MCP server
```

---

## 8. Installation and Configuration

### 8.1 Prerequisites

- Hermes Agent installed and configured (any model provider)
- Python 3.10+ (bundled with Hermes)
- Stim (`pip install stim`) and PyMatching (`pip install pymatching`) for Tier 2
- Aristotle API key for Tier 3 (optional, from aristotle.harmonic.fun)

### 8.2 Installation

```bash
# Clone into Hermes skills directory
cd ~/.hermes/skills/
git clone https://github.com/zetetic-works/deep-gvr.git

# Install Python dependencies for adapters
pip install stim pymatching --break-system-packages

# (Optional) Configure Aristotle MCP for Tier 3 formal verification
export ARISTOTLE_API_KEY="your-key-here"
hermes mcp add aristotle -e ARISTOTLE_API_KEY=$ARISTOTLE_API_KEY -- \
  uvx --from git+https://github.com/septract/lean-aristotle-mcp aristotle-mcp

# (Optional) Install OpenGauss for interactive proof engineering
cd ~/.hermes/skills/
git clone https://github.com/math-inc/OpenGauss.git opengauss
```

### 8.3 Configuration

deep-gvr is configured through a YAML file at `~/.hermes/deep-gvr/config.yaml`:

```yaml
# deep-gvr configuration

# GVR loop parameters
loop:
  max_iterations: 3            # Max GVR cycles before admitting failure
  alternative_approach: true   # Try different approach on repeated failure
  max_alternatives: 2          # Max alternative approaches before halting

# Verification tiers
verification:
  tier1:
    enabled: true              # Always true (analytical verification)
  tier2:
    enabled: true              # Empirical verification via simulation
    default_simulator: stim
    default_backend: local     # local | modal | ssh
    timeout_seconds: 3600      # Per-simulation timeout
    ssh:
      host: ""                 # For SSH backend
      user: ""
      key_path: ""
  tier3:
    enabled: false             # Formal verification (requires ARISTOTLE_API_KEY)
    backend: aristotle         # aristotle | opengauss
    timeout_seconds: 300       # Per-proof timeout

# Model routing (cross-model verification)
models:
  generator:
    provider: openrouter       # openrouter | nous | openai | default
    model: ""                  # Empty = use provider's default strong model
  verifier:
    provider: openrouter
    model: ""
  reviser:
    provider: default          # "default" = use Hermes's configured model
    model: ""

# Evidence storage
evidence:
  directory: ~/.hermes/deep-gvr/sessions
  persist_to_memory: true      # Save session summaries to Hermes memory

# Domain context
domain:
  default: qec                 # qec | fbqc | custom
  context_file: ""             # Path to custom domain context (overrides default)
```

---

## 9. Evaluation Strategy

### 9.1 Validation Benchmark

Before using deep-gvr on open research questions, we need confidence that the GVR loop actually works — that the Verifier catches real errors and doesn't rubber-stamp the Generator's output. This requires a small benchmark of problems with known answers.

**Benchmark categories:**

1. **Known-correct claims** (should VERIFY):
   - "The surface code has a threshold under independent depolarizing noise" (well-established, ~1%)
   - "The planar surface code requires O(d²) physical qubits for distance d" (elementary)
   - "Union-Find decoding has near-linear time complexity" (proved)

2. **Known-incorrect claims** (should find FLAWS):
   - "The surface code threshold under circuit-level noise is 5%" (too high; actual ~0.6-1%)
   - "Color codes have higher thresholds than surface codes for all noise models" (false)
   - A proof sketch with a subtle logical error (hand-crafted)

3. **Verifiable-by-simulation claims** (should trigger Tier 2):
   - "At physical error rate 0.001, the logical error rate for distance-7 surface code is below 10^-6" (checkable via Stim)

4. **Formalizable claims** (should trigger Tier 3 if enabled):
   - "For the repetition code of distance d, the logical error rate is O(p^((d+1)/2))" (formalizable in Lean)

### 9.2 Metrics

| Metric | Description |
|---|---|
| True Positive Rate | Fraction of correct solutions verified as VERIFIED |
| True Negative Rate | Fraction of incorrect solutions flagged as FLAWS_FOUND |
| False Positive Rate | Fraction of incorrect solutions rubber-stamped as VERIFIED (critical failure) |
| Tier Accuracy | Fraction of claims routed to the correct verification tier |
| Iteration Efficiency | Average GVR iterations to reach final verdict |
| Failure Admission Rate | Fraction of genuinely hard problems where the system correctly outputs CANNOT_VERIFY |

**Target for v0.1 release:** False positive rate < 20% on the benchmark. This is a bar, not a ceiling — we expect to improve it through prompt iteration.

---

## 10. Phased Implementation Plan

### Phase 1: Core GVR Loop (Week 1–2)

**Goal:** Working `/deep-gvr` command in Hermes with Tier 1 verification only.

**Deliverables:**
- [ ] SKILL.md with full orchestrator procedure
- [ ] prompts/generator.md
- [ ] prompts/verifier.md (Tier 1 only)
- [ ] prompts/reviser.md
- [ ] Evidence recording (JSON Lines)
- [ ] Session management (init, checkpoint, resume)
- [ ] config.yaml with defaults
- [ ] Validation on 3+ known-correct and 3+ known-incorrect problems

**Build approach:** Use Hermes Agent itself (or Claude Code) to generate the skill bundle, then iterate on prompts manually based on benchmark results.

### Phase 2: Tier 2 — Simulation (Week 2–3)

**Goal:** Stim adapter operational, Verifier triggers empirical verification.

**Deliverables:**
- [ ] adapters/stim_adapter.py with local backend
- [ ] prompts/simulator.md
- [ ] Verifier prompt update for Tier 2 triggering
- [ ] Orchestrator mediation flow (Verifier → Orchestrator → Simulator → Orchestrator → Verifier)
- [ ] Modal backend support in adapter
- [ ] SSH backend support in adapter
- [ ] Validation on simulation-verifiable benchmark problems

### Phase 3: Tier 3 — Formal Verification (Week 3–4)

**Goal:** Aristotle MCP integration, Verifier triggers formal verification selectively.

**Deliverables:**
- [ ] Aristotle MCP server configured and tested
- [ ] Verifier prompt update for Tier 3 triggering
- [ ] Async proof polling (proofs can take minutes to hours)
- [ ] Graceful degradation when Aristotle is unavailable
- [ ] Validation on formalizable benchmark problems

### Phase 4: Cross-Model Verification (Week 4–5)

**Goal:** Generator and Verifier use different models.

**Deliverables:**
- [ ] Investigation: does Hermes delegate_task support model overrides?
- [ ] If yes: implement per-role model routing via config
- [ ] If no: implement PTC wrapper or upstream PR
- [ ] A/B testing: same-model vs cross-model verification on benchmark
- [ ] Document findings on decorrelation effectiveness

### Phase 5: Polish and Release (Week 5–6)

**Goal:** Public release on GitHub and agentskills.io.

**Deliverables:**
- [ ] README.md with installation, quickstart, examples
- [ ] ARCHITECTURE.md (this document, finalized)
- [ ] eval/ benchmark suite and results
- [ ] QEC and FBQC domain context files
- [ ] install.sh and setup_mcp.sh scripts
- [ ] Publish to agentskills.io
- [ ] Announcement via Zetetic Works channels

---

## 11. Open Questions Tracker

### Resolved

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | Simulator target | Stim first, custom FBQC later | Widely used, well-documented, handles primary use case |
| 2 | Model providers | OpenRouter + Nous Portal + OpenAI | All available, enables cross-model verification |
| 3 | Compute backends | Local + Modal + SSH | Covers dev, bursty, and large-scale workloads |
| 4 | Formalization requirement | Tiered, not mandatory | Most early use cases are analytical/empirical |
| 5 | Release model | Zetetic Works open source, MIT | First public release, establishes brand |
| 6 | Name | deep-gvr | Descriptive, echoes deep research, says what it does |

### Open

| # | Question | Priority | Notes |
|---|----------|----------|-------|
| 7 | Per-subagent model routing in Hermes | **P0** | Blocking for cross-model verification. Investigate delegate_task internals. |
| 8 | Subagent MCP access | **P0** | Do delegated subagents inherit MCP tool access? Must verify. |
| 9 | Evidence format Parallax compatibility | P1 | JSON Lines works for v0.1. Parallax schema alignment is Phase 2+. |
| 10 | Session checkpoint/resume mechanics | P1 | Serialize loop state to session directory. Orchestrator reloads on `/deep-gvr resume <session_id>`. |
| 11 | Lean 4 environment location | P2 | Aristotle API avoids local Lean for v0.1. OpenGauss needs local or Morph Cloud. |
| 12 | Multi-hypothesis fan-out vs sequential | P2 | Start sequential. Fan-out is a v0.2 feature. |
| 13 | Failure escalation policy | P1 | v0.1: log + structured report to user. v0.2: auto-decomposition. |
| 14 | Domain knowledge static vs dynamic | P1 | Minimal static context + dynamic retrieval. domain/ files are brief reference cards, not textbooks. |
| 15 | Skill auto-improvement policy | P2 | Ship with auto_improve: false. Document how to enable. |
| 16 | Contribution model | P2 | Accept adapter contributions freely. Prompt changes require review. |
| 17 | Evaluation benchmark size | P1 | Target 10–15 problems across all categories for v0.1. |

---

## 12. Appendix: Hermes Agent Constraints

Reference: constraints imposed by Hermes's architecture that deep-gvr must work within.

| Constraint | Value | Impact |
|---|---|---|
| Subagent delegation depth | Max 2 (parent → child) | GVR roles cannot sub-delegate. Verifier cannot directly invoke Simulator. |
| Concurrent subagents | Max 3 | Limits parallel hypothesis exploration. |
| Subagent blocked tools | delegate_task, memory, execute_code, clarify, send_message | Subagents can't persist to memory, delegate further, or interact with user. |
| Skill SKILL.md size | Recommended < 60 chars description in system prompt index | Keep frontmatter description concise; full procedure in SKILL.md body. |
| Skill auto-creation threshold | ~5+ tool calls or tricky error fixes | deep-gvr should NOT be auto-created; it's an installed skill. |
| Memory system | FTS5 full-text search + LLM summarization | Evidence summaries are searchable across sessions via Hermes memory. |
| MCP tool access | Inherited by subagents (needs verification) | If true, Verifier can directly call Aristotle MCP. If false, Orchestrator must mediate. |
| Model switching | Global via `hermes model` | Per-subagent model routing requires investigation (see Open Question #7). |

---

*This document is the authoritative design reference for deep-gvr v0.1. Implementation should be driven by this spec and the phased plan in Section 10. Deviations should be documented as amendments to this document.*
