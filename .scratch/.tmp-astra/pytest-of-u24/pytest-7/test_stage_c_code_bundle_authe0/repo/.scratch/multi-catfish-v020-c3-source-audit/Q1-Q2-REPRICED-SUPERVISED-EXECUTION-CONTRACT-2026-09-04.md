# Repriced Q1/Q2 supervised execution contract

Date: 2026-09-04 (Asia/Taipei)

Status: **FROZEN BEFORE REPRICED LEARNER OUTPUTS**

## Purpose and claim ceiling

This contract authorizes one source-only supervised refit of Q1 and Q2 after
the shared development multiplier was corrected to

\[
\lambda'=118{,}424{,}222.8550065\ \mathrm{bit/J}
\]

(`0x1.c3c0a7b6b86d3p+26`).  It does not authorize a simulator rollout, a C3
selection, TEST access, an episode learner, or an EE-efficacy claim.

The input repricing contract is
`Q1-Q2-LAMBDA-REPRICING-PREOUTCOME-CONTRACT-2026-09-04.md`, SHA-256
`34732dd3f65ffebf760313c2ffd235e0ecbd406ba6065dbce5635778550ef4a9`.
The multiplier is not iterated or tuned after learner outcomes are opened.

## Frozen Q1 fit

- Source: admitted C1 rows only from opening worlds `2026092001`--`2026092007`.
- TRAIN worlds: `2026092001`--`2026092004` (968 rows at contract freeze).
- Internal-validation worlds: `2026092005`--`2026092007` (712 rows at contract freeze).
- Targets: exact repriced `z1` values from the frozen repricing contract.
- Architecture, normalization scale, optimizer, learning rate, beta, and
  initializations remain those of the sealed V0.3 masked-mean/max Q1.
- Initializations: `2026092101`, `2026092102`, `2026092103`.
- Update rule: ten full-batch C1 updates; deploy rung is fixed at 10 and is not
  reselected from the new outcomes.
- Before using new labels, the implementation must reproduce the old rung-10
  Q1 parameters within maximum absolute error `1e-6` for every tensor and
  every initialization.
- The new Q1 source-only gate passes only if validation skill versus the
  strongest TRAIN-fitted state-independent null is strictly positive for at
  least two of three initializations and the mean skill is strictly positive.

## Frozen Q2 fit

- Source state/mask panel: the authenticated 21 V0.14 shards, worlds
  `2026108001`--`2026108007`, one shard per world and source lineage.
- TRAIN worlds: `2026108001`--`2026108004`; internal-validation worlds:
  `2026108005`--`2026108007`.
- Source-lineage to learner-initialization mapping:
  `2026092101 -> 2026108101`, `2026092102 -> 2026108102`,
  `2026092103 -> 2026108103`.
- Targets: the authenticated offline-repriced Q2 surfaces under `lambda'`.
- Architecture: 16 action-local inputs, hidden widths `100/50/50`, `tanh`.
- Adam learning rate `0.001`, beta `0.1`, batch size `512`, deterministic
  cyclic batches, CPU execution with one Torch intra-op thread.
- Diagnostic checkpoint rungs: `3, 10, 30, 100, 300, 1000, 3000`.
- Deployment rung: fixed at 3000; diagnostic rungs may not select a different
  deploy checkpoint.
- The Q2 source-only gate reuses the V0.14 head rule at rung 3000: validation
  skill versus the strongest TRAIN-fitted state-independent null must be
  strictly positive for at least two of three initializations and in the
  initialization mean.

## Reconstructed Q1 state on the V0.14 panel

The 228-dimensional Q1 state may be reconstructed from the stored V0.14 Q3
state only after authenticating the source shard.  Reuse passes only if the
old sealed Q1 surface is recovered over all 21,000 rows with:

- maximum absolute legal-cell error at most `1e-6` Q units; and
- legal masked argmax agreement exactly `1.0`.

Failure requires explicit source regeneration; this threshold may not be
relaxed after output.

## Outputs and stop rule

Each lineage output must bind its source hashes, target hashes, implementation
hash, configuration, validation report, and serialized Q1/Q2 parameters.
The merge may authorize exactly one next action:

- `GO_MATCHED_C3_GATE` if Q1 and Q2 both pass their frozen source-only gates;
- `STOP_REPRICED_Q1_Q2` otherwise.

No alternate multiplier, architecture, learning rate, update rung, seed,
threshold, source split, or target may be introduced after these outcomes.
No paper/deck/symbol-table update and no 500/9000-episode run is authorized by
this contract.
