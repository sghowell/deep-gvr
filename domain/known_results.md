# Known Results

- Surface-code threshold under standard depolarizing assumptions is commonly reported around the sub-1% regime, not multiple percent under realistic circuit-level assumptions.
- Do not conflate threshold regimes: code-capacity depolarizing thresholds are around 10%, phenomenological noisy-syndrome thresholds are in the low single-digit percent range, and realistic circuit-level thresholds are commonly around the sub-1% regime.
- Be explicit about code-capacity semantics: the familiar ~10.3% number is tied to independent X/Z decoding assumptions, not a generic full-depolarizing maximum-likelihood threshold claim.
- When citing a threshold number, pair it with the noise model and decoder instead of giving a free-floating percentage.
- Physical-qubit cost for distance-`d` planar or rotated surface-code constructions scales on the order of `d^2`.
- Union-Find decoding is generally treated as near-linear in practice and in its core analysis.
- Avoid toric-specific homology language when a claim is about surface codes generically; use planar or rotated wording unless the topology is explicit.
- Do not use Raussendorf-Harrington 2007 as the canonical citation for the standard 2D planar or rotated surface-code circuit-level threshold without qualifying that it is a different topological construction.
- These items are benchmark anchors, not exhaustive truth tables. Any concrete evaluation case should still cite the source it relies on.
