# Known Results

- Surface-code threshold under standard depolarizing assumptions is commonly reported around the sub-1% regime, not multiple percent under realistic circuit-level assumptions.
- Do not conflate threshold regimes: code-capacity depolarizing thresholds are around 10%, phenomenological noisy-syndrome thresholds are in the low single-digit percent range, and realistic circuit-level thresholds are commonly around the sub-1% regime.
- Be explicit about code-capacity semantics: the familiar ~10.3% number is tied to independent X/Z decoding under code-capacity depolarizing assumptions, not a generic full-depolarizing maximum-likelihood threshold claim.
- Be explicit about the Nishimori-point mapping: reserve it for the higher ~10.9% maximum-likelihood bit-flip threshold, not the lower ~10.3% independent-X/Z decoding figure.
- Match the threshold regime to the actual question. For standard depolarizing surface-code threshold questions, prefer the sub-1% circuit-level regime as the main claim and treat code-capacity thresholds as separately scoped context instead of collapsing them into one sentence.
- When citing a threshold number, pair it with the noise model and decoder instead of giving a free-floating percentage.
- Do not attribute the surface-code threshold directly to the generic concatenated-code threshold theorem; ground it in surface-code-specific statistical-mechanical mappings, topological fault-tolerance constructions, or the cited numerical threshold studies.
- Wang, Fowler, and Hollenberg, "Surface code quantum computing with error rates over 1%", is Physical Review A 83(2) from 2011; do not cite it as a 2003 paper.
- Prefer Fowler et al. (2012) or Stephens (2014) for the familiar sub-1% circuit-level MWPM threshold range unless you explicitly explain Wang et al.'s parameter convention and why it matches your quoted number.
- Physical-qubit cost for distance-`d` planar or rotated surface-code constructions scales on the order of `d^2`.
- Union-Find decoding is generally treated as near-linear in practice and in its core analysis.
- For generic Union-Find scaling questions, prefer the total decode complexity `O(n alpha(n))` or near-linear wording; do not add threshold comparisons or claim a worst-case single-operation cost of `O(alpha(n))` unless the prompt explicitly asks for those details.
- Avoid toric-specific homology language when a claim is about surface codes generically; use planar or rotated wording unless the topology is explicit.
- Do not use Raussendorf-Harrington 2007 as the canonical citation for the standard 2D planar or rotated surface-code circuit-level threshold without qualifying that it is a different topological construction.
- If a work is named in the body, list it in `references`; if you do not want it in `references`, do not cite it in the body.
- These items are benchmark anchors, not exhaustive truth tables. Any concrete evaluation case should still cite the source it relies on.
