# V0.23 DROP_C3 100-episode development-evaluation receipt

Date: 2026-09-06

Status: `PASS_LOCAL_DROPC3_100_REOPEN`

## Bound execution

- Arm: `DROP_C3` only (`Q1+Q2`; Q3 not evaluated)
- Episodes: 100, ten canonical decision steps each
- Split: `EVALUATION_DEVELOPMENT`
- Episode training: false
- Learner update: false
- TEST opened: false
- Evaluation contract SHA-256:
  `7ff5d639cef0310bdbf66a54b6a8513aff0ff9460554543cf33e8c39e5673885`
- Frozen Q1/Q2 checkpoint SHA-256:
  `d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc`

## Reopened result

- Total bits: `987222835333251.4`
- Total energy: `8262138.508048408 J`
- Ratio-of-sums EE: `119487567.82176511 bit/J`
  (`119.48756782176511 Mbit/J`)
- Served user-steps: `99875 / 100000`
- Service fraction: `0.99875`
- Wall time: `1293.9823903681245 s`

The local reopen used the production checkpoint reader, recovered exactly 100
receipts at completed episode 100, and independently recomputed total bits /
total energy to the serialized EE value.

## File hashes

- `result.json`:
  `f58fcaebdd5e955fcb894ad5597ed6f975764e5e33efb851efd62c334a563fd1`
- `timing.json`:
  `33767ffa120cb824878629ab16b7744ec62291b73ef53c4dc53cd30cd8860b92`
- `checkpoint-000100.json`:
  `b0b2c0d8419c12d8f3dcf6ba767fb7f1fcd6e11ecda4b2f2212e8c5f4453c5f7`

## Claim ceiling

This is one provisional pre-Gate, no-C3 physical evaluation arm.  It provides
runtime and comparator-scale evidence only.  It performs no between-arm
comparison and establishes no Catfish efficacy, no FULL ordering, and no
baseline superiority.
