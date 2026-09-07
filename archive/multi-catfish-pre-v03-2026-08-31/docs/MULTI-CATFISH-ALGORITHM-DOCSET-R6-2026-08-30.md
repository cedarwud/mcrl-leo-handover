# Multi-Catfish MCRL algorithm document set R6

Date: 2026-08-30  
Status: **superseded for new authoring by the 2026-08-31 V0.3 EE-axis contract;
retained as R6 run/history authority; not a result**

> **2026-08-31 stop notice.** Do not use the R6 `unchanged r2/r3` role text for
> new figures, slides, or Chapter 4 prose. The current proposed mechanism is
> `MULTI-CATFISH-EE-AXIS-REDESIGN-CONTRACT-V0.3-2026-08-31.md`. R6 remains
> necessary only to interpret its already frozen/running experiment artifacts.

## 1. Purpose and precedence

This manifest was the entry point for figures, slides, algorithm explanation,
and non-result manuscript updates at the R6 synchronization. It implements
[ADR-005](decisions/ADR-005-separate-r5-run-authority-from-r6-authoring.md).

The R5 documents named in the R2 1500-episode authorities remain immutable
run-reproduction inputs. The following R6 files supersede their author-facing
wording without changing the running experiment:

| Purpose | R6 authority |
|---|---|
| complete technical algorithm | `MULTI-CATFISH-PAPER-ALGORITHM-V0.5-2026-08-30.md` |
| concise concept and figure explanation | `MULTI-CATFISH-CONCEPT-ALGORITHM-FREEZE-V0.2-2026-08-30.md` |
| non-result paper and figure rules | `MULTI-CATFISH-NONRESULTS-PAPER-AUTHORING-CONTRACT-V0.2-2026-08-30.md` |
| detailed C2 mechanism | `C2-TEMPORAL-FORK-CANDIDATE-V0.3A-R6-2026-08-30.md` |
| EE-positive falsification and acceptance | `THREE-CATFISH-EE-POSITIVE-ACCEPTANCE-CONTRACT-V0.2-2026-08-30.md` |

If an R5 and R6 statement disagree about current authoring, use R6. If the
question is whether a currently running arm matches its frozen authority, use
the R2 JSON authority and its R5 hashes.

## 2. Mechanism core retained unchanged

R6 does not redesign the three Catfish roles:

1. C1 Energy-Frontier uses the RIS-lineage EXP/ACRM adaptation, learns unchanged
   canonical `r1`, and may route specialist-origin TD influence only to
   `Q_1^M` after its consumer gate.
2. C2 Policy-Aligned Forecast-Certified Temporal Fork uses fixed `H=3`
   focal-action holds plus the first complete candidate-local Main release,
   learns unchanged canonical `r2`, and may route only to `Q_2^M`.
3. C3 Spatial Load-Balancing uses the strict canonical-`r3` load certificate
   with separate power/service safeguards and may route only to `Q_3^M`; its
   Main-consumer route remains developmental/shadow-only until its gate passes.
4. Every executed bundle retains the full canonical reward vector for audit.
   Specialists do not fuse actions, private rewards, policies, replay memories,
   optimizers, or RNGs.
5. Evaluation and deployment discard C1/C2/C3 and execute Main only.

These statements are sufficient for the structural system, overview, learner,
role-detail, routing, and training/deployment figures. No core redraw is
required merely because R6 updates operational evidence.

## 3. R6 executable-contract synchronization

R6 adds the following implementation facts:

- Each R2 1500-episode authority pins exactly 95 files.
- The local C2 V0.3A suite contains 234 tests and passes all 234 on the R6
  synchronization checkout.
- A declared support rejection remains a recorded candidate rejection. Any
  other C2 candidate/runtime contract error raises `C2BackendError`, aborts the
  affected arm, and may not be relabelled as K0 or zero dose.
- Bounded exact-path B000 and F111 checkpoint gates write periodic checkpoints,
  load them back, and validate the round trip. This is engineering evidence,
  not proof that an entire matrix or formal long-run resume chain completed.
- Formal trend arms checkpoint every 100 episodes. Matrix verification requires
  the planned episode boundary, the correct segment-aware checkpoint count,
  zero C2 contract errors, a loadable final checkpoint, and identical
  `mechanism_environment_source_sha256` across arms.
- Final developmental sweeps use five frozen fresh evaluation seeds on the
  canonical held-out `TEST` partition, execute the Main-only masked-greedy
  policy, and compute system EE by ratio of pooled useful bits to pooled system
  energy. They do not evaluate on `TRAIN`.
- The post-run bundle revalidates both completed matrices. For the current fresh
  matrices it independently reads all 75 periodic and five final checkpoints
  per LR; checks the three training seeds, learning rate, trainer identity, and
  EP1500 periodic/final policy digest; rechecks direct `r1/r2/r3`, service, EE
  arithmetic, source dose, C2 forecast cost, all CSV projections, and the exact
  5-arm x 5-user x 5-seed sweep grid; and enforces the zero-power guard before
  applying the frozen LR selector. A legally resumed treatment is accepted for
  final-endpoint closure only after its source snapshot, absolute episode clock,
  segment telemetry, and continuation checkpoint schedule validate; it is
  explicitly ineligible for a full 100--1500EP trajectory. The two matrices
  must have identical normalized authority after removing only `learning_rate`.
  The bundle emits both five-line editable sweep figures and direct
  `F111-B000`/leave-one-out contrast tables.
- An optional every-100EP U=100 `TEST` trajectory evaluates 75 checkpoints and
  375 fresh-seed episodes per matrix. Before exposing those curves it freshly
  revalidates both complete LR matrices, their sweep receipts, and the selector
  inputs/decision against the sealed post-run receipt. It accepts only fresh
  complete histories, is retrospective and diagnostic only, and may not select
  an intermediate checkpoint or replace the final EE-vs-users endpoint.
- The public F111 label is exactly `Full Multi-Catfish MCRL`. `C2-V0.3` may be
  used as a mechanism-version note, not appended to the public treatment name.

## 4. Frozen 1500-to-3000 selection rule

The developmental matrices use arms `B000`, `F111`, `A011`, `A101`, and `A110`
at learning rates `0.001` and `0.01`. At the U=100 evaluation endpoint, a
learning rate is eligible only when mean Main-only EE for F111 is strictly
greater than B000 and each leave-one-out arm:

```text
F111 > B000, F111 > A011, F111 > A101, and F111 > A110.
```

If neither learning rate is eligible, stop before 3000 episodes. If exactly one
is eligible, select it. If both are eligible and their F111 endpoint EE differs
by at most 4.0% relative to the larger value, prefer `0.001`; otherwise select
the larger eligible endpoint. Any 3000-episode comparison must be a fresh run,
not an extension selected from a favourable intermediate checkpoint.

This rule is a developmental routing decision. It does not establish
statistical significance, robustness, generalization, or final efficacy.

## 5. Time-stamped run status and claim ceiling

At `2026-08-30T08:44:53Z`, both R2 matrices reported matrix status `running`,
with B000 as the active first arm. This is launch/running evidence only. It is
not a completed 1500-episode comparison and is intentionally not converted into
a moving episode count in author-facing diagrams.

Until complete arm statuses, final checkpoint/log hashes, evaluation receipts,
matrix exit receipts, and scientific adjudication exist, R6 permits only:

- proposed, defines, routes, aligns, is designed to, hypothesizes, and
  specifies a falsifiable evaluation plan.

R6 does not permit:

- improves, outperforms, effective, validated, best, robust, generalizes,
  Chapter 5 result, selected learning rate, or 9000-episode efficacy claim.

## 6. Required post-1500 update

After both matrices are complete, publish a new result-status revision that:

1. validates all five arms for both learning rates;
2. records final and periodic checkpoint receipts and cross-arm mechanism hashes;
3. evaluates the frozen U=100 rule without changing it;
4. separates direct `r1/r2/r3` endpoints from Main-only EE; and
5. either authorizes a fresh 3000-episode screen or records
   `STOP_BEFORE_3000`.

The executable adapters are
`.scratch/c2-v03a-trend/c2_v03a_postrun_bundle.py` and
`.scratch/c2-v03a-trend/c2_v03a_checkpoint_trajectory.py`. The first is a
non-training closure step; the second is a heavy optional diagnostic and must
run on the Ubuntu server after matrix completion.

Do not edit this R6 snapshot to retrofit the outcome.
