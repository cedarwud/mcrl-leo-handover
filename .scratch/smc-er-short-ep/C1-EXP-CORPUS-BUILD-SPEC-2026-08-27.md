# C1 immutable EXP corpus build specification

Date: 2026-08-27  
Status: frozen after Source Gate A PASS and before source-build seed reveal

Authority prerequisite: the independently verified Source Gate A receipt with
result SHA-256 `9eca695349a65694131c2d7ad4ec1318bc93aecbd7286c17d2e2ebaea3fba0cc`.

This job builds replay transitions; it is not another gate and cannot authorize
Main routing.

- Use five new source-build seeds, disjoint from Source Gate A and all other
  named namespaces.
- At each seed, create two fresh 100-user environments from identical initial
  RNG states. Execute ten intervals of `local_snr_greedy` in one branch and
  `masked_uniform` in the other.
- Retain every complete atomic transition: encoded canonical states, relative
  and physical actions, natural `U x 3` rewards, successor states, current and
  successor masks, done flag, behavior probabilities, seed/step lineage,
  throughput, power, service, and canonical step-level system EE.
- No counterfactual, reward-sign filter, Main replay, ACRM value, learned Q
  value, or later training outcome may enter the corpus.
- Within each branch, order bundles by descending system EE, then seed, step,
  and bundle ID. Let `n=50`; ranks 1--17 are `high`, 18--34 are `mid`, and
  35--50 are `low`. Only the immutable 34 high/mid bundles prefill `D_1^F`.
- The local and control branches therefore have identical total bundle count,
  high/mid capacity, replay residency, prefill update count, and FIFO rule.
- The `.npz` bytes and JSON manifest are hash-bound. Loading rejects a changed
  checkpoint, encoder configuration, array shape, duplicate bundle ID, or file
  hash.

The corpus has no held-out efficacy claim. A later C1 Main-consumer gate must
pass before any online C1 bundle can enter Main; the offline corpus itself can
never enter Main.
