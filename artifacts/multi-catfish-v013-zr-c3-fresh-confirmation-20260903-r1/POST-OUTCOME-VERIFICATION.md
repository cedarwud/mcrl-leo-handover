# Multi-Catfish MCRL V0.13 post-outcome verification

Date: 2026-09-03  
Scope: four fresh TRAIN worlds; exact ZR oracle versus `DROP_C3`; no learner,
no optimizer, no TEST split, and no episode-training efficacy claim

## Verified decision

The sealed producer and an independently implemented verifier agree exactly:

`GO_ZR_C3_LEARNABILITY_PREREG_ONLY`

For `FULL_ZR` relative to `DROP_C3`:

- pooled ratio-of-sums EE: `+0.9382853481196829%`;
- pooled delivered bits: `-5.69792088289125%`;
- pooled trajectory energy: `-6.574518487334846%`, or
  `-64526.7834608024 J`;
- served user-steps: unchanged (`12000` versus `12000`);
- active-beam steps: `-322`;
- active-satellite steps: `+2` (diagnostic only);
- production action exposure: `1816` user-decisions; and
- supported positive ZR targets: `13090`.

EE was strictly positive in every world. Positive Q1-lineage counts by world
were `2/3`, `3/3`, `3/3`, and `3/3`. Exact trajectory energy was nonincreasing
in every world and pooled. All formula, method, support, mechanics, service,
coverage, common-field, and frozen-authority checks passed.

## Independent verification

The independent verifier was written and tested against synthetic fixtures
before it was applied to the completed outcome bundle. It then reconstructed
all 24 shard rows and independently checked:

- strict canonical JSON and duplicate-key rejection;
- exact four-world, two-arm, three-lineage coverage;
- row and step bits, energy, service, count, and ratio arithmetic;
- formula, method, mechanics, and joint-support receipts;
- frozen Q1 and executable-authority receipts;
- common initial-world and keyed-field identity;
- cross-arm step-0 equality of Q1, O2, mask, Q1 reference, and background;
- pooled and per-world exact trajectory-energy gates; and
- the complete merged summaries, decision, and result digest.

The independent result had no discrepancy with the producer. W145 synthetic
tests passed `9/9` and the verifier compiled successfully.

## Hashes

- merged result file SHA-256:
  `cc9e610ce8d35b509689fd50e04aec5dabf2c61297811bf555f37b9d9c469a98`
- merged canonical result payload SHA-256:
  `e2309605c9ff4c62ceb5612c2251cb648fed5aa2e4479e5a504a39c2cacbe661`
- independent verifier SHA-256:
  `83fa55d41d10a8a6c80e1da0636d1cd658670c8011e97c76d0ad2cae56a902f4`
- W145 test SHA-256:
  `f4c10460ca6d4b57806aa120fb83907b00b8ec6db4bfd538c99b3c7d3182dcee`

## Claim ceiling and next authorized step

This is replicated TRAIN-development oracle evidence that the unchanged ZR
physical direction remains complementary to frozen Q1 plus exact OPS3 O2
under the V0.13 contract. It is not evidence that a Q3 network can learn ZR,
that a learned Q2 can reproduce OPS3, or that a learned three-head policy
improves held-out EE.

The only promotion authorized by this result is a separately frozen,
state-only ZR-Q3 learnability preregistration. Q2 learnability remains a
separate required gate before any true learned three-head episode ablation.
