# V0.10 MONE-C3 oracle result

Status: **FAIL_MONE_C3_ORACLE**  
Evidence class: TRAIN-development, no learner, no TEST, no efficacy claim

## Verified outcome

The six preregistered episode shards completed on the Ubuntu server and the
frozen merge runner returned `FAIL_MONE_C3_ORACLE`.

| Quantity | FULL (`Q1 + O2 + O3`) | DROP-C3 (`Q1 + O2`) | FULL relative to DROP-C3 |
|---|---:|---:|---:|
| ratio-of-sums EE (bit/J) | 116,681,925.68734552 | 119,842,129.76925364 | -2.6369725638161135% |
| delivered bits | 32,509,667,450,130.043 | 30,851,908,210,562.863 | +5.373279436244425% |
| network energy (J) | 278,617.85155347164 | 257,437.91661551513 | +8.227201034099749% |
| served user-steps | 3,000 | 3,000 | 0 |

All three initialization contrasts were negative:

- `2026092101`: -2.9370721773622398%
- `2026092102`: -1.4455142044113245%
- `2026092103`: -3.548178471346655%

Binding mechanics passed, legal-action spread was nonzero, and FULL changed
3,110 of 6,000 user-step actions relative to DROP-C3. The hard stops were the
negative pooled EE direction and zero of three positive lineages.

## Verified diagnostics

- Mean active beams per step increased from 44.2667 to 48.3667.
- Mean hold rate after the opening step fell from 0.4248 to 0.1989.
- The sum of exact unilateral opening surpluses was positive at all 60
  diagnosed state-steps, but the realized joint surplus was negative at 28.
- Across the 60 diagnostics, the summed unilateral surplus was
  `1.859489670518412e13` bit-equivalent, while the joint-interaction residual
  was `-1.811656867987044e13`; the residual cancelled about 97% of the
  additive prediction.
- Frozen Q1 versus exact matched O1 had mean pairwise agreement 0.7684, mean
  Spearman correlation 0.6558, and mean top-action agreement 0.2275.

## Interpretation boundary

Verified fact: exact unilateral MONE does not pass as C3 on the frozen Q1+O2
background. The failure is not learner approximation because no Q3 learner
was used.

Inference: the dominant failure mode is simultaneous multi-user
non-additivity/credit assignment; frozen-Q1 versus matched-O1 mismatch and
the missing realized energy response amplify the problem. This inference is
under clean-room cross-model review and is not a new accepted method.

Decision: do not start MONE Q3 learner or episode training. Any replacement
C3 requires a new formula, new preregistration, and fresh TRAIN seed before
outcome access.

Primary receipt: `server-merged/result.json` (SHA-256
`b43aead4ababd674070cf49857eefc4e59a1e5842eb694c411daf1ded35bed59`).
