# Controller finding — three independent learner defects, and the pilot's positive result was an early-training artefact
Recorded 2026-09-09. All numbers verified by reading the training corpus and by evaluating checkpoints that already existed. `PILOT_NOT_CLAIM` throughout.

## 1. The training corpus contains only two-user coalitions
| coalition size | rows | share |
|---:|---:|---:|
| 2 | 180 | 100 % |
| 3, 4, 5, 6 | **0** | 0 % |

This is not an artefact of uniform mask sampling. The pilot's source path builds the bounded catalogue, **discards every configuration that does not change exactly two users**, and takes the lexicographically smallest remaining configuration ID. The corpus is 180 rows: 90 anchors in each of two worlds, **one coalition per anchor**.

Two consequences, both fatal on their own:
* The learner has **never seen a three-user coalition**. The occupancy-activation mechanism this project verified requires exactly three, since a beam at occupancy 1 or 2 selects no mode and occupancy 3 activates one.
* With one coalition per anchor there is **no within-anchor variation at all**, so the interaction coefficients are not identifiable from this design regardless of the model. More anchors cannot substitute for varied coalitions at the same anchor.

At size 2 the exact targets are informative: mean 10.84 in normalised units, 108 of 180 positive, 72 negative, no exact zeros. So the labels are real; the design is what is impoverished.

## 2. The pilot's headline result does not survive training
Evaluating the checkpoints that already existed, at the same five anchors and two seeds:

| epoch | FULL vs DROP_C3 | FULL availability | FULL mean coalition size |
|---:|---:|---:|---:|
| 200 | **+45.64 %** | 74.38 % | 100.0 |
| 600 | +2.91 % | 76.44 % | 61.1 |
| 1000 | **−25.56 %** | 76.72 % | 3.1 |
| 2000 | **−25.24 %** | 76.82 % | 3.0 |

The `+45.6 %` I reported this morning **decays to about −25 % and stays there**. It was an early-training artefact. A second catalogue anchor reproduces the same shape, so it is not a fluke of one evaluation.

The three quantities move together in exactly the pattern that indicts the early number: at epoch 200 the FULL arm selects the all-users coalition, carries the **lowest** availability of any arm, and posts the highest efficiency. As training proceeds the coalition size falls to three, availability recovers above BASELINE, and **the efficiency advantage disappears and reverses**. The early gain was bought by serving fewer users, which is precisely the failure mode the sealed QoS non-inferiority condition exists to catch.

## 3. A symptom I misdiagnosed
I treated "FULL always selects the hundred-user coalition" as a defect requiring explanation. It is **not stable behaviour**. From epoch 1000 onward no decision selects size 100; sizes are 2 to 5 with a mean of 3.0. It is a warm-up artefact.

The corrected reading is more interesting than the symptom I was chasing: **at convergence the learner selects coalitions of exactly the size where the verified mechanism lives**, while having been trained only on size two and while its features had the pairwise cross-gains summed away. It is reaching for the right thing with the wrong information.

## 4. Three independent defects, each separately sufficient to explain the failure
1. **Feature collapse.** The pairwise cross-gain terms are summed into a scalar the contract explicitly forbids, so the head cannot represent which aggressors matter. Repair in progress.
2. **Coverage collapse.** The corpus holds only size-two coalitions, one per anchor, so the verified three-user mechanism was never in the training data and the coefficients are unidentifiable.
3. **A tautological acceptance test.** The test named to enforce the first requirement contains zero mentions of its subject.

None of these was visible in any experimental result. All three were found by reading code and data.

## 5. What this does and does not license
Every previous learned C3 result, including this morning's, was measured under at least two of these defects. **No prior null or positive is evidence about whether coordination has value.** Equally, nothing here shows that repairing them will produce a positive result; it only shows the previous experiments could not have detected one.

## 6. Standing
No threshold, sign, seed, horizon, price, service guard, acceptance rule or claim condition changes. No run is authorised. Nothing here may enter the paper.
