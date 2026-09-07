# C1 Source Gate A and immutable EXP corpus specification

Date: 2026-08-27  
Status: frozen design before gate-seed reveal; no PASS is implied

## Purpose and boundary

This non-training gate tests only whether the named LEO-native
`local_snr_greedy` source is better than the dose-matched `masked_uniform`
control as a source of executed C1 experience. It cannot authorize C1 bundles
to enter Main. A separate Main-consumer gate is mandatory after this gate.

The gate uses the unchanged corrected checkpoint only to advance common
pre-outcome anchors with Main's masked-greedy scalarized policy. C1 and its
control are evaluated from the same anchor with `evaluate_actions`, which
copies the environment RNG and does not commit either alternative. Neither
realised outcome can change the next anchor.

## Frozen design

- population: 100 users;
- five new, unique gate seeds supplied in a hash-bound manifest;
- ten common-anchor intervals per seed;
- treatment: deterministic `local_snr_greedy`, with action-index tie-break;
- control: `masked_uniform` from the same post-mask support and a domain-
  separated RNG;
- paired physics: identical anchor and common random numbers;
- primary per-seed endpoint: ratio-of-sums system EE in bits/J;
- safeguards: served-user fraction, zero-power consistency, finite rewards,
  valid masks/actions, and non-mutation of the common anchor;
- the corrected checkpoint, method, this spec, runner, seed manifest, TLE
  input, and dependency versions are retained by SHA-256.

Gate A passes only if all conditions hold:

1. mean paired seed difference
   `EE_local_snr_greedy - EE_masked_uniform > 0`;
2. the difference is positive in at least four of five seeds;
3. pooled served-user fraction for the named source is no more than `0.005`
   below the control;
4. every validity, finiteness, zero-power, common-anchor, and artifact guard
   passes.

There is no p-value and no threshold tuning. Any failed condition freezes a
FAIL for this source version.

## EXP corpus construction after a Gate-A PASS

A PASS permits a separate, executed, disjoint-seed source-build job. It does
not turn the counterfactual gate rows into replay transitions. The source-build
job executes one local-SNR trajectory and one masked-uniform trajectory from
matched initial conditions and retains complete atomic transitions.

Within each executed corpus, bundles are sorted by descending canonical
step-level system EE, then seed and step. The first ceiling one-third is
`high`, the next ceiling one-third is `mid`, and the remainder is `low`.
Only immutable high/mid bundles may prefill `D_1^F`; the same high/mid counts,
replay capacity, sampling schedule, residency, and FIFO eviction rule apply to
the neutral corpus. Prefill never enters Main or evaluation.

Gate seeds, source-build seeds, preview-training seeds, preview-evaluation
seeds, formal Stage-0 seeds, and thesis seeds are pairwise disjoint.

## Claim ceiling

A PASS means only that this fixed source rule outperformed this fixed neutral
source on the frozen non-training gate. It does not show that C1 learns, that
ACRM helps, that Main can consume C1 experience, or that held-out EE improves.
