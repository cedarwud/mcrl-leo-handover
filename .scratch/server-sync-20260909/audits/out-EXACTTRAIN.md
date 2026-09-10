Completed corpus assembly and preflight. The required report is at [EXACT-CORPUS-TRAINING-2026-09-10.md](/home/sat/mcrl-v025-exacttrain-ws/EXACT-CORPUS-TRAINING-2026-09-10.md).

Key outcome:

- Intersection: 22 development anchors.
- Corpus: 21,532 exact C1/C2 rows and 4,552 exact C3 rows.
- Sampled surrogate match: 359/6,000 = 5.9833%.
- Argmax disagreement: C1 51.6818%, C2 55.2727%, C3 81.8182%.
- Reader/five-arm dry run: PASS.
- Production checkpoint C3 width: 240 for every arm, with loader readback PASS.
- Peak RSS: 614,244,352 bytes.
- Declared run: not launched.

The immutable runner rejects 4,000 updates and implements a constant-rate 2,000-update budget with no early stopping or held-out convergence calculation. Launching it would violate the declared schedule, so the production output path remains absent.
