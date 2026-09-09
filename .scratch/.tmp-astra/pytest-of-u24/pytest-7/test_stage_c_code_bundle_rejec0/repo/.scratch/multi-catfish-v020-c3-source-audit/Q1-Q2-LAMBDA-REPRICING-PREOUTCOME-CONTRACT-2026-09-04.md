# Q1/Q2 lambda-repricing pre-outcome contract

Date: 2026-09-04 (Asia/Taipei)

Status: **FROZEN BEFORE BATCH REPRICING OUTPUTS**

## Scope and claim ceiling

This is a development-only, zero-episode source-reuse gate. It may read only
already opened TRAIN and internal-validation sources. It may not open TEST,
run the simulator, propagate a TLE, update an episode policy, or establish an
EE efficacy claim.

The purpose is to remove one shared multiplier confound before comparing any
C3 target. It does not redesign the C1 or C2 source mechanisms.

## Frozen multiplier

The single development multiplier is

\[
\lambda'=118{,}424{,}222.8550065\ \mathrm{bit/J}
\]

with binary64 representation `0x1.c3c0a7b6b86d3p+26`.

It is the pooled ratio-of-sums EE of the `BASE = Q1 + learned Q2` arm in the
already opened V0.18 TRAIN analytic panel:

- result:
  `artifacts/multi-catfish-v018-relational-zr-20260904-r2/server-run-r2/analytic-panel-r2/merged/result.json`
- result SHA-256:
  `728049388c1e251aec131fc185309b22f068c2199af43bf6bddcf63d2dfe95eb`
- pooled total bits: `124797752231295.12`
- pooled total energy: `1053819.4739440435` J
- pooled BASE rows: `12`

The old multiplier is
`84994621.12635651` bit/J
(`0x1.443a8f481639ap+26`). The new multiplier is frozen once here. It must not
be iterated, rescaled, or replaced after observing repriced learner or C3
outcomes. Final decisions still use canonical ratio-of-sums EE.

## Frozen Q1 source

- root:
  `artifacts/multi-catfish-v03-e1-action-shared-supplement-20260901/source-data`
- source-manifest SHA-256:
  `9ec832c71b29ad84e37856db1f5d237f07d177c62cc93fbb66de06d808184a0a`
- TRAIN worlds: `2026092001`--`2026092004`
- internal-validation worlds: `2026092005`--`2026092007`
- admitted route: C1 only

For every admitted C1 comparison, reconstruct and then reprice

\[
z'_1=\Delta t\left[\Delta R_u-\lambda'\Delta P^N\right].
\]

The raw focal rates, full network powers, interval, actions, mask, and state
remain unchanged. C3 rows and audit-only C1 rows are excluded.

## Frozen Q2 source

- root:
  `artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/source-panel/shards`
- TRAIN worlds: `2026108001`--`2026108004`
- internal-validation worlds: `2026108005`--`2026108007`
- lineages: `2026092101`, `2026092102`, `2026092103`
- one shard for every world-lineage pair: 21 shards
- action count: 28; users: 100; physical steps: 10; OPS-3 horizon: 3

For every legal Q2 cell, decode the stored 448-dimensional feature-major
state and reprice

\[
z'_2=z_2-(\lambda'-\lambda_0)
\frac{1}{H_t}\sum_{h=1}^{H_t}
\chi_h\Delta t\,\Delta P_h.
\]

The rate, outage, state, action mask, world split, and policy provenance remain
unchanged. Float32 state precision is permitted; geometry or physics is not
recomputed.

## Frozen reconstruction gate

Offline reuse passes only if all conditions hold:

1. all seven Q1 files and all 21 Q2 NPZ receipts authenticate;
2. world-to-split membership exactly matches the declarations above;
3. old lambda and kappa metadata match their frozen hexadecimal values;
4. all reconstructed and repriced legal values are finite and all illegal Q2
   targets remain zero;
5. every Q1 old target reconstructs with maximum absolute error at most
   `1e-3` bit;
6. each Q2 shard reconstructs the old target with maximum absolute error at
   most `2500` bits and maximum error divided by that shard's maximum absolute
   target below `1e-6`;
7. direct and affine Q2 repricing agree within `1e-3` bit.

Failure means the affected source must be regenerated from frozen physics;
thresholds may not be relaxed after outputs are opened. Passing authorizes
only matched Q1/Q2 supervised retraining under a separately sealed execution
receipt. It does not authorize C3 selection or episode training.

## Next-stage invariants

- Retrain Q1 and Q2 together at the fixed multiplier; do not update only one.
- Preserve their existing architectures, optimizer, learning rate, beta,
  initialization mapping, complete-world split, and declared rung schedules.
- Rebuild Q1+Q2 reference actions before evaluating C3.
- C3 candidates must be compared on the same anchors and background. CSE is a
  heuristic unless a valid potential identity is supplied.
- No TEST access and no 9000-episode launch are authorized by this contract.
