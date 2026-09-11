**Pooled over 352 seed x anchor cells per run, this project's deployed `Q1+Q2` user rows have mean |off-diagonal Pearson| `0.4110` (Q1-v1 non-z), `0.4818` (Q1-v2 non-z) and `0.3604` (v2z), with penultimate effective rank `0.636`/`0.459`, `0.636`/`0.454` and `0.815`/`0.903` of hidden width for C1/C2 respectively — so the sibling's `~0.998` collinear-Q-row pathology is ABSENT here: these values stand only `0.087`-`0.208` above the `0.2735` mutual-independence floor that a 10-slot action row mechanically imposes, whereas the sibling's `0.998` stands `0.84` above its own `0.155` floor and its repaired `0.17`-`0.22` band stands `0.015`-`0.065` above it, putting this project on the repaired side of that scale rather than the pathological one.**

# Q-row collinearity and penultimate effective rank — 2026-09-10

Design-phase representation diagnostic. **No EE was computed and no loss value was read.** No evaluation-only claim date, evaluation shard or evaluation split was opened; every input is a `TRAIN` row of `V025_PROBE/world/1`. No sealed artefact was modified and nothing was written into any training output directory.

## Verdict

| question | answer |
|---|---|
| Does this project have the sibling's collinear-Q-row pathology? | **No.** Not one of the 1,056 measured seed x anchor cells reaches `0.78` on the deployed `Q1+Q2` sum (maximum `0.769968`); none reaches `0.9`; the largest value seen anywhere, for a single head in isolation, is `0.824482`. |
| Is its representation rank-collapsed? | **Not collapsed, but materially rank-deficient in the non-z runs.** C2's penultimate effective rank is `22.7`-`22.9` of a 50-wide hidden layer (`0.454`-`0.459`) against a `50/50` i.i.d. reference at the identical matrix shape. The z view lifts it to `45.2` (`0.903`). |
| Does the built-in z control move in the predicted direction? | **Yes, on both axes.** Correlation `0.4818 -> 0.3604`; C2 effective rank `0.454 -> 0.903` of hidden width. But see the width confound in §7 — this project has no width-matched non-z control, so the z view's advantage is not cleanly attributable to the z transform. |
| Would the sibling's `shared_q_isolation` penalties have something to repair here? | The decorrelation penalty has very little headroom: at most `0.21` of the `0`-`1` range separates the worst run from the floor, and its own docstring records that the penalty is weakest far from `rho = 1`. The `srank` penalty has more visible headroom on C2 in the non-z runs, but the z view already occupies it. |

## 1. What was measured, and on what

Instrument: the sibling module itself, byte-identical, imported and called verbatim.

- source `/home/sat/mcrl-v025-qcollinear-ws/ref/penalties.py`, SHA-256 `d1ca8dc89ffc71762369b361498e80b91dffe719916ef52556ac77243b486411`
- confirmed identical to `/home/u24/papers/modqn-paper-reproduction/src/modqn_paper_reproduction/shared_q_isolation/penalties.py` on the local machine (same SHA-256, 206 lines)
- functions used unmodified: `q_row_decorrelation_penalty`, `mean_offdiag_row_pearson_torch(absolute=False)`, `_row_pearson_offdiag`, `srank_diagnostic(delta=0.01)` (mean-centered), `srank_penalty` (NOT mean-centered). The penalty and the diagnostic are kept as the distinct objects the module declares them to be and are never reported as one another.

Scored surface: for every checkpoint and every anchor, both deployed heads were forwarded over every `(user, action)` row and the scores summed. This reproduces the reference proposal's own arithmetic exactly — `independent_two_head_profile` builds each user's score as `model.score("C1", q1) + model.score("C2", q2)` and takes a masked argmax over it ([deployment.py:110-117](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/deployment.py:110)). No gauge, centering or normalisation is applied at deployment; `gauge_beta` appears only inside the training objective ([learner.py:786](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/learner.py:786)). Arm = `FULL`.

`Phi` is the penultimate activation, i.e. the input to the final linear layer, matching `AdamMLPHead._forward`'s `activations[-2]` ([learner.py:718-737](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/learner.py:718)). C1 is `relu`, hidden `[8]`, so `Phi_C1` is `(rows, 8)`. C2 is `tanh`, hidden `[100, 50, 50]`, so `Phi_C2` is `(rows, 50)`. Widths are read from each run's `head_literals` (SHA-256 `201f6243cd7bb17f99a33aa299d6feab8c666b4a0d9651c3abdd1637276eebf0`, identical across all three runs). The batch is one anchor's full row set, `947`-`995` rows.

Scope, identical for all three runs: 22 `TRAIN` development anchors named by the run's own launch receipt, 100 users, 16 of 16 seeds at epoch 500, `= 352` seed x anchor cells per run and `1,056` in total. Every source shard was checked against its launch-receipt SHA-256 before use, and every checkpoint against its `.sha256` sidecar, its declared `learner_seed`, its `completed_source_epochs = 500` and the five-arm inventory.

### The score matrix, and one structural difference from the sibling that must be stated

The sibling's `Q` is `(num_users, num_actions)` over a **shared** action table. **This project has no shared action table.** At each anchor every user carries its own 9- or 10-row candidate list; on the three step-0 anchors inspected directly, 100 users' lists together contain 227, 227 and 230 *distinct* physical `(NORAD ID, beam-chain ID)` identities, and the most widely shared beam appears in only 11 users' lists. Two users therefore share essentially no physical action, and a physically-aligned `(users x actions)` matrix cannot be built.

The matrix used is consequently the one the deployed argmax actually operates on: **rows = users, columns = that user's own local `action_index` slots**, which is exactly the layout of the score vector `masked_argmax` consumes. Column `k` is the same *slot* for every user but not the same *beam*. The last slot of every user's table is that user's null action (`468` users at index 8, `1,732` at index 9 across the 22 anchors x 100 users; verified). Every present action is legal at every anchor — `action_mask` sums equal table lengths in all 1,056 cells.

Two estimators were run, and they agree:

- **Primary (sibling-verbatim):** the complete `(U x 10)` block, i.e. the users whose table has all 10 slots. `U` ranges `47`-`95`, median `77.5`, giving `1,105,600` user pairs per run. `q_row_decorrelation_penalty` is called on this block unchanged.
- **Robustness (all 100 users):** pairwise-complete Pearson over each pair's common slots. `4,950` pairs per cell, `0` pairs dropped in all 1,056 cells. Verified to agree with the sibling function to `0.0` on a complete matrix and to `1.7e-18` on the signed variant.

Degenerate rows are dropped exactly as the sibling does; the NaN path was exercised and returns NaN (an all-constant matrix gives `nan`, not `0` or `1`). **No cell returned NaN in the live measurement** — `nan = 0` for all runs, heads and estimators.

## 2. Verified by running code — mean |off-diagonal Pearson| between user rows

Estimand: the arithmetic mean, over the 352 seed x anchor cells of a run, of that cell's mean `|off-diagonal Pearson|` between the user rows of the score matrix. Numerator within a cell: the sum of `|rho|` over the `U(U-1)/2` user pairs, divided by that pair count. Cells are weighted equally. Reference point: the sibling's `0.998` pathology and `0.17`-`0.22` repaired band. Information class: replay of frozen checkpoints on frozen development anchors; no physics, no reward, no EE.

| run | checkpoint set | `Q1 + Q2` (deployed) | `Q1` alone | `Q2` alone |
|---|---|---:|---:|---:|
| Q1-v1 non-z | `firstrun-500ep-20260910T1355Z` | **0.411019** [0.276387, 0.703599] | 0.377607 [0.264383, 0.745755] | 0.427089 [0.271602, 0.749475] |
| Q1-v2 non-z | `firstrun-v2-500ep-20260910T1425Z` | **0.481769** [0.296202, 0.769968] | 0.591860 [0.294301, 0.824482] | 0.427892 [0.269491, 0.742660] |
| Q1-v2z (z view) | `firstrun-v2z-500ep-20260910T1512Z` | **0.360429** [0.267398, 0.544504] | 0.334835 [0.266716, 0.465603] | 0.359434 [0.264752, 0.548297] |

Brackets are the minimum and maximum over the 352 cells. Cell standard deviations are `0.1257`, `0.1339` and `0.0775` for the three `Q1+Q2` columns.

Signed mean off-diagonal Pearson — the sibling's NumPy readout rather than its penalty — on the same cells:

| run | `Q1 + Q2` | `Q1` alone | `Q2` alone |
|---|---:|---:|---:|
| Q1-v1 non-z | 0.312363 [0.011696, 0.703599] | 0.263922 [-0.008895, 0.745755] | 0.341771 [-0.000356, 0.749475] |
| Q1-v2 non-z | 0.425050 [0.033456, 0.769968] | 0.547321 [0.032126, 0.824393] | 0.344304 [0.005342, 0.742660] |
| Q1-v2z | 0.256588 [0.007746, 0.535966] | 0.194280 [0.005495, 0.431471] | 0.248055 [-0.007121, 0.544270] |

All-100-user pairwise-complete robustness estimator, `Q1 + Q2`: `0.389350`, `0.436671`, `0.348642` for v1, v2 and v2z. Slightly lower than the primary in every case and identically ordered.

Tail counts over the 352 cells of each run, `Q1 + Q2`:

| run | cells `> 0.7` | cells `> 0.9` | cells `> 0.99` | cells `< 0.30` | median |
|---|---:|---:|---:|---:|---:|
| Q1-v1 non-z | 2 | 0 | 0 | 75 | 0.345229 |
| Q1-v2 non-z | 21 | 0 | 0 | 3 | 0.473273 |
| Q1-v2z | 0 | 0 | 0 | 136 | 0.363074 |

Per-seed pooled means are tight: v1 `0.3928`-`0.4282`, v2 `0.4686`-`0.5075`, v2z `0.3484`-`0.3671`. **No seed is anomalous; this is not a one-checkpoint artefact.**

## 3. The number that decides how §2 should be read: the independence floor

Mean `|off-diagonal Pearson|` does **not** approach 0 for independent rows — it approaches `sqrt(2 / (pi (c-1)))` for `c` columns. This project's rows have 10 columns; the sibling's have 28. The two projects' raw numbers are therefore **not** on the same scale, and comparing `0.41` to `0.20` without this correction overstates the gap.

Measured (200 draws of a `92 x c` standard-Gaussian matrix through the same sibling function):

| columns | context | measured floor | analytic `sqrt(2/(pi(c-1)))` |
|---:|---|---:|---:|
| 10 | this project, 10-slot users | **0.273525** [0.266998, 0.283980] | 0.265962 |
| 9 | this project, 9-slot users | 0.291000 [0.284080, 0.302698] | 0.282095 |
| 28 | the sibling's action count | **0.155060** [0.150612, 0.160248] | 0.153553 |

A permutation null on the **real** score matrices — independently shuffling the entries within each user row, which destroys cross-user shape agreement while preserving each user's own score multiset, 64 repetitions per anchor at representative seed `6407676579069309528` — reproduces the floor almost exactly: `0.273643`, `0.273526`, `0.273218` for v1, v2, v2z. The floor is real and it is not a Gaussian artefact.

Excess over that permutation null, same representative seed, 22 anchors:

| run | observed | permutation null | **excess** |
|---|---:|---:|---:|
| Q1-v1 non-z | 0.396681 | 0.273643 | **+0.123038** [+0.010748, +0.389687] |
| Q1-v2 non-z | 0.473490 | 0.273526 | **+0.199964** [+0.033866, +0.423203] |
| Q1-v2z | 0.365805 | 0.273218 | **+0.092587** [+0.003964, +0.252151] |

Placed on this corrected scale:

Raw values below are the pooled means of §2; excess is that pooled mean minus the measured floor for that row's action count.

| regime | raw value | its own floor | excess over floor |
|---|---:|---:|---:|
| sibling pathology (transcribed) | 0.998 | 0.155 | +0.843 |
| **this project, Q1-v2 non-z (worst)** | **0.482** | **0.274** | **+0.208** |
| **this project, Q1-v1 non-z** | **0.411** | **0.274** | **+0.137** |
| **this project, Q1-v2z** | **0.360** | **0.274** | **+0.087** |
| sibling repaired band (transcribed) | 0.17-0.22 | 0.155 | +0.015 to +0.065 |

**This project sits between the sibling's repaired band and its pathology, and much nearer the repaired end.** There is a real, reproducible cross-user agreement in action-preference shape — it is not zero and should not be described as zero — but it is a fifth of the sibling's excess at worst, and the sibling's `~0.998` regime does not occur here at any anchor, any seed or any head.

## 4. Which head carries the collinearity

- In the **current design run (Q1-v2 non-z)**, C1 dominates: `Q1` alone is `0.5919` against `Q2` alone at `0.4279`, and the deployed sum at `0.4818` is *less* collinear than its more collinear part. C1 is the 15-input, single-8-wide-hidden-layer head; C2 is the 22-input `100-50-50` head.
- In the **older run (Q1-v1 non-z)** the ordering reverses: `Q1` `0.3776` against `Q2` `0.4271`. The Q1-v1 -> Q1-v2 schema change therefore *raised* C1's cross-user row agreement by `+0.2143` while leaving C2 unchanged to `+0.0008`. (What that schema change consisted of — 16 slots to 15, two duplicate activation bits removed, focal elevation added — is read from `BASE-COLLAPSE-DIAGNOSIS-2026-09-10.md`, not verified by me.)
- In the **z view** the two heads converge to `0.3348` and `0.3594`, both near the floor, and neither dominates.

So the answer to "does one head dominate" is run-dependent, and in the run this project is currently building on, **yes — C1 does.** That is a specific, actionable finding: the head with the collinearity problem is the small one.

## 5. Effective rank of the penultimate features

`srank_diagnostic(Phi, delta = 0.01)` on the **mean-centered** `Phi`, one anchor's full row batch (`947`-`995` rows), pooled over 352 cells. The raw `sigma_max^2 - sigma_min^2` is `srank_penalty` on the **un-centered** `Phi`, reported alongside as the module requires and never conflated with the diagnostic.

| run | C1 srank (hidden 8) | as fraction | C2 srank (hidden 50) | as fraction |
|---|---:|---:|---:|---:|
| Q1-v1 non-z | 5.085227 [2, 8] | **0.635653** | 22.948864 [9, 35] | **0.458977** |
| Q1-v2 non-z | 5.090909 [2, 7] | **0.636364** | 22.718750 [9, 35] | **0.454375** |
| Q1-v2z | 6.522727 [3, 8] | **0.815341** | 45.170455 [34, 48] | **0.903409** |

Reference at the identical matrix shapes: an i.i.d. standard-Gaussian `Phi` scores `8/8` and `50/50` at every one of the 22 anchors, i.e. fraction `1.000`. So the fractions above are genuine deficits, not an artefact of the batch or the threshold.

Raw Kumar Eq. (6) penalty values on the un-centered `Phi`:

| run | C1 `sigma_max^2 - sigma_min^2` | C2 `sigma_max^2 - sigma_min^2` |
|---|---:|---:|
| Q1-v1 non-z | 8464.73 [92.84, 38810.63] | 18913.45 [8280.57, 34197.45] |
| Q1-v2 non-z | 5088.72 [132.77, 35011.11] | 20241.01 [8312.16, 37572.19] |
| Q1-v2z | 12113.69 [553.21, 55093.55] | 20170.16 [8137.76, 36230.09] |

**Read that table with care.** The penalty is unnormalised and scale-carrying: the z view has the *highest* C1 penalty value while also having the *highest* C1 effective rank, and its C2 penalty is indistinguishable from the non-z runs while its C2 effective rank is double theirs. On this substrate the penalty value does not track the diagnostic, and a training curve of the penalty alone would be uninterpretable as rank evidence.

## 6. Per-anchor structure (mean over the 16 seeds)

| anchor | v1 `Q1+Q2` | v2 `Q1+Q2` | v2z `Q1+Q2` | C1 srank v1/v2/z | C2 srank v1/v2/z |
|---|---:|---:|---:|---|---|
| `0\|nearest-eligible` | 0.5159 | 0.6002 | 0.4065 | 4.81 / 5.12 / 6.56 | 24.00 / 23.62 / 46.12 |
| `0\|random-masked` | 0.3263 | 0.3792 | 0.3727 | 4.75 / 5.00 / 6.44 | 24.56 / 24.06 / 46.44 |
| `0\|stay-if-possible` | 0.4844 | 0.4936 | 0.4520 | 4.81 / 5.12 / 6.56 | 29.19 / 29.50 / 48.00 |
| `1\|nearest-eligible` | 0.6559 | **0.7210** | 0.4464 | 4.94 / 5.12 / 6.62 | 27.56 / 27.69 / 47.94 |
| `1\|random-masked` | 0.2942 | 0.4376 | 0.3579 | 5.12 / 5.25 / 6.69 | 20.25 / 19.38 / 47.12 |
| `1\|stay-if-possible` | 0.3512 | 0.3703 | 0.3723 | 4.81 / 5.12 / 6.69 | 25.56 / 25.75 / 48.00 |
| `2\|nearest-eligible` | 0.4960 | 0.5048 | 0.2889 | 5.38 / 5.25 / 6.88 | 24.00 / 23.69 / 46.75 |
| `2\|random-masked` | 0.3049 | 0.3925 | 0.3059 | 5.38 / 5.25 / 6.75 | 23.69 / 22.88 / 46.69 |
| `2\|stay-if-possible` | 0.3051 | 0.3198 | 0.2903 | 5.38 / 5.25 / 6.69 | 23.50 / 23.44 / 47.00 |
| `3\|nearest-eligible` | 0.3136 | 0.3383 | 0.2844 | 5.56 / 5.25 / 6.62 | **12.81 / 12.88** / 37.56 |
| `3\|random-masked` | 0.4733 | 0.6588 | 0.2891 | 5.06 / 5.06 / 6.56 | **11.44 / 11.25** / 37.12 |
| `3\|stay-if-possible` | 0.3009 | 0.3383 | 0.2801 | 5.56 / 5.19 / 6.69 | **11.75 / 11.69** / 36.94 |
| `4\|nearest-eligible` | 0.5390 | 0.6933 | 0.4888 | 4.62 / 4.44 / 5.94 | 26.38 / 26.19 / 45.69 |
| `4\|random-masked` | 0.2816 | 0.5516 | 0.3818 | 4.50 / 4.56 / 6.25 | 26.25 / 25.81 / 45.62 |
| `4\|stay-if-possible` | 0.5446 | 0.6002 | 0.4816 | 4.62 / 4.44 / 5.94 | 32.50 / 32.56 / 47.88 |
| `5\|nearest-eligible` | 0.6549 | 0.6705 | 0.5164 | 5.12 / 5.25 / 6.69 | 24.62 / 24.38 / 47.44 |
| `5\|random-masked` | 0.3015 | 0.5214 | 0.3819 | 5.19 / 5.12 / 6.38 | 25.88 / 25.56 / 46.81 |
| `5\|stay-if-possible` | 0.5112 | 0.5328 | 0.3948 | 5.06 / 5.06 / 6.12 | 27.31 / 27.50 / 47.94 |
| `6\|nearest-eligible` | 0.4791 | 0.4585 | 0.2970 | 5.12 / 5.19 / 6.56 | 21.06 / 20.25 / 46.12 |
| `6\|random-masked` | 0.2885 | 0.3911 | 0.2893 | 5.38 / 5.44 / 6.56 | 28.50 / 27.38 / 46.31 |
| `6\|stay-if-possible` | 0.3105 | 0.3176 | 0.2776 | 5.50 / 5.19 / 6.69 | 23.25 / 23.25 / 46.81 |
| `7\|nearest-eligible` | 0.3098 | 0.3075 | 0.2736 | 5.19 / 5.31 / 6.62 | **10.81 / 11.12** / 37.44 |

Two structures are visible and both are anchor properties, not seed noise. First, five of the six highest v2 correlations are `nearest-eligible` carriers (steps 1, 4, 5, 0 and 4-stay; the exception is `3|random-masked` at `0.6588`), which suggests cross-user agreement is partly a property of the anchor's incumbent geometry rather than of the network — that reading is inferred, not established. Second, **C2's effective rank halves at all three step-3 anchors and at step 7** (`10.81`-`12.88` of 50, fraction `0.216`-`0.258`) in both non-z runs, while the z view lifts those same anchors to `36.94`-`37.56`. Step 3 and step 7 are the 0-indexed positions of the 4th and 8th steps that earlier V0.14 gate work identified as group-departure points where the whole population hands over together; that identification is carried over from prior work and is not re-verified here.

## 7. The z view, and the confound that stops it being a clean attribution

The z run is the built-in control, and it moved in the predicted direction on both axes:

| quantity | v2 non-z | v2z | change |
|---|---:|---:|---:|
| `Q1+Q2` mean \|off-diag Pearson\| | 0.481769 | 0.360429 | **-0.121340** |
| excess over permutation null | +0.199964 | +0.092587 | **-0.107377** |
| `Q1` alone | 0.591860 | 0.334835 | -0.257025 |
| `Q2` alone | 0.427892 | 0.359434 | -0.068458 |
| C1 effective rank / 8 | 0.636364 | 0.815341 | **+0.178977** |
| C2 effective rank / 50 | 0.454375 | 0.903409 | **+0.449034** |
| cells `> 0.7` (of 352) | 21 | 0 | -21 |

**The confound.** The z view is serialised as `[raw || live z]`, so its inputs are *twice as wide*: Q1 `15 -> 30`, Q2 `22 -> 44`. The corpus census in `ZSCORE-VIEW-AND-TRAINING-2026-09-10.md` records the concatenated Q1 block at matrix rank 24 and Q2 at 36 — materially more usable input directions than the raw blocks alone. More input directions make a higher feature rank easier to reach for reasons that have nothing to do with the z transform. The sibling ran exactly this negative control (`width448`: duplicate the raw features, no z) and its own notes report it did **not** repair (`analysis/family-b-collapse-diagnosis/PRIOR-ART-CARDS-2026-07-10.md:104`, `DISPATCH-LEDGER-2026-07-10.md:340`, both read on the local machine, not reproduced by me); **this project has no width-matched non-z control.** Until one exists, the z view's advantage here is *consistent with* the z transform being the active ingredient but does not establish it. That control is cheap: rebuild the corpus as `[raw || raw]` and retrain, using the same runner and seed list.

## 8. Robustness checks

**The null action.** Every user's table ends with its null action, at a shared column within the complete block. If its score were a common outlier it would manufacture cross-user correlation on its own. It is not constant (per-anchor null-score spreads run from `[-0.798, 0.952]` to `[-8.220, 11.670]`), and it is the row extreme for a minority of users at most anchors (`0`-`92` of 100, varying strongly by anchor). Recomputing with that column dropped, at representative seed `6407676579069309528` across all 22 anchors:

| run | with null slot (10 cols) | without null slot (9 cols) | 9-column floor |
|---|---:|---:|---:|
| Q1-v1 non-z | 0.396681 | 0.360159 | 0.291000 |
| Q1-v2 non-z | 0.473490 | 0.421220 | 0.291000 |
| Q1-v2z | 0.365805 | 0.336033 | 0.291000 |

The null column contributes `0.030`-`0.052`, and the excess over the 9-column floor survives at `+0.069`, `+0.130`, `+0.045`. The ordering and the conclusion are unchanged.

**Estimator agreement.** The all-100-user pairwise-complete estimator agrees with the sibling-verbatim complete-block estimator to `0.0` on complete matrices, drops `0` pairs in all 1,056 live cells, and gives the same run ordering with values `0.022`-`0.045` lower.

**Instrument self-test.** On synthetic input the sibling function returned `1.0` for an exactly rank-1 (collinear) matrix, `nan` for an all-constant matrix, and dropped constant rows without coercing them; `srank_diagnostic` returned `1` for a rank-1 `Phi`. The degenerate paths behave as the brief requires.

## 9. Every number's four fields

- **Reference point.** For §2 and §5, the sibling's `0.998` / `0.17`-`0.22` / `init 60 -> final 3-46` figures. For §3, this project's own measured permutation and Gaussian independence floors. For §5, an i.i.d. Gaussian `Phi` at the identical shape.
- **Information class.** Frozen-checkpoint replay on frozen `TRAIN` development anchors. Exact source rows, exact float-hex weights, no sampling, no physics, no reward, no EE, no evaluation date.
- **Estimand.** §2: cell-equal-weighted mean over 352 seed x anchor cells of the within-cell mean `|off-diagonal Pearson|` between user rows. §5: cell-equal-weighted mean over the same 352 cells of `srank_delta=0.01` on the mean-centered per-anchor `Phi`.
- **Numerator.** §2: within a cell, the sum of `|rho|` over `U(U-1)/2` user pairs, `U in [47, 95]`, `1,105,600` pairs per run in total. §5: within a cell, the count of leading singular values of the centered `Phi` reaching `99%` of the singular-value sum.

## 10. Evidence classification

**Verified by running code (by me, on `sat`).** Every value in §2, §3, §4, §5, §6, §7 and §8, including the floors, the permutation null, the i.i.d. Gaussian rank references and the instrument self-test. Widths `8` and `50` were read from the runs' own `head_literals` and confirmed against the decoded weight shapes.

**Read from source, not reproduced by me.** The sibling's `~0.998` pathology, its `0.17`-`0.22` repaired band, its `srank init 60 -> final 3-46` and `75 -> 99-106`, its `raw-224` substrate and 28-action rows, and the disclosed vanishing-gradient hazard at `rho -> 1`. These are claims stated in `penalties.py`'s own docstring, which I read on the local machine. I did not rerun the sibling's experiments and I make no statement about whether those numbers are correct. The sibling's srank figures also have no denominator stated in that file, so **its rank fractions cannot be computed and are not compared here** — only this project's fractions are, against this project's own i.i.d. reference.

**Derived on paper.** The analytic floor `sqrt(2/(pi(c-1)))`, which matches the measured floors to `0.008` at `c=10`, `0.009` at `c=9`, `0.002` at `c=28`. The excess-over-floor columns are subtractions of two measured quantities. The `+0.2143` C1 shift between Q1-v1 and Q1-v2 is a difference of two measured pooled means.

**Inferred, not established.** That the elevated correlations at `nearest-eligible` step-1/4/5 anchors reflect geometric homogeneity of the incumbent profile rather than the network. That the C2 rank halving at steps 3 and 7 is the same group-departure structure identified in earlier gate work. That the z transform rather than the input-width doubling causes the z run's advantage — §7 states why this is not established. **That any of this bears on EE.** It does not: no EE was computed, and nothing here licenses an EE statement in either direction.

## 11. What this closes and what it opens

**Closes.** Porting the sibling's `q_row_decorrelation_penalty` to this project has almost nothing to repair. The worst run stands `0.208` above its floor on a scale where the sibling's pathology stands `0.843` above its own, and the penalty's own docstring records that it is weakest far from `rho = 1` — so the instrument would be applied where it is least effective, to an effect a fifth the size it was designed for. Recommend not pursuing that arm.

**Does not close.** C2's `0.454` effective rank of a 50-wide hidden layer in the current non-z design is a real deficit against a `1.000` i.i.d. reference at the identical shape, concentrated to `0.22`-`0.26` at the step-3 and step-7 group-departure anchors. The z view removes it. Whether that is the z transform or merely twice the input width is the open question, and the width-matched `[raw || raw]` control settles it for the cost of one retrain.

**Bears on the two findings that motivated this measurement, but does not explain them.** The learned `a0` being indistinguishable from a myopic rule in concentration terms, and the sealed head losing to linear regression on level calibration (both supplied in the brief; the second was not verified by me), are *not* explained by collinear Q rows here — the rows are not collinear. Whatever produces those two results, the sibling's pathology is not it, and that possibility can be struck from the candidate list.

## 12. Provenance

| run | directory | launch-receipt file SHA-256 | corpus digest | seeds x anchors |
|---|---|---|---|---|
| Q1-v1 non-z | `/home/sat/mcrl-v025-retrain-ws/artifacts/firstrun-500ep-20260910T1355Z` | `11920d3ae7d827438c31752daf43ac1004d65421b7f7534fc39ad86e55d9aff7` | `23814e63d9300fe049bd730897b7e07ef880e5fe21f7a5624c1fee4a9d5eb20c` | 16 x 22 |
| Q1-v2 non-z | `/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2-500ep-20260910T1425Z` | `19ac748748942b3cf81aa7f3a2375447295d7c228e4e9c9084a5e1f84da4d893` | `ab81d942993d005e6eab964e4e1011a8b85cfed49d47fac7448a39e729514016` | 16 x 22 |
| Q1-v2z | `/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2z-500ep-20260910T1512Z` | `1c3f37acfccdf44c1f45c332acf895975df656d96550ac5108547003d8ed24e9` | `ef3dc0c66b89b185b9395b1d9f2e063319de1e24014123594cb2ef902278af31` | 16 x 22 |

The file hash above is the SHA-256 of the receipt bytes; it differs by construction from the receipt's own embedded `launch_receipt_sha256` field, which is computed before that field is inserted. The v1 and v2 file hashes agree with the values quoted in `BASE-COLLAPSE-DIAGNOSIS-2026-09-10.md`.

Seed list, identical in all three runs and all at epoch 500: `389903013832883586`, `925030429265975792`, `1437152739566466432`, `2106858948530091040`, `2306713132836500212`, `2539879246662512149`, `2914121027624601215`, `2947922203589416513`, `3155344545377116990`, `5166716249291843642`, `5683607794651051129`, `6114226365011333154`, `6407676579069309528`, `7234013715671416945`, `7291913070596938501`, `9087876568043732533`. Every checkpoint's SHA-256 is recorded per cell in the machine receipt. Representative seed for §3's permutation null and §8's null-slot check: `6407676579069309528`.

Artifacts, all in `/home/sat/mcrl-v025-qcollinear-ws`:

- [`Q-ROW-COLLINEARITY-2026-09-10.json`](/home/sat/mcrl-v025-qcollinear-ws/Q-ROW-COLLINEARITY-2026-09-10.json) — every one of the 1,056 cells with its seed, anchor, checkpoint hash, per-head correlations under both estimators, and both spectral readouts.
- [`NULL-FLOOR-2026-09-10.json`](/home/sat/mcrl-v025-qcollinear-ws/NULL-FLOOR-2026-09-10.json) — permutation null and i.i.d. rank references.
- [`MECHANISM-2026-09-10.json`](/home/sat/mcrl-v025-qcollinear-ws/MECHANISM-2026-09-10.json) — Gaussian floors at 9, 10 and 28 columns; null-slot analysis.
- [`scripts/qcollinear_probe.py`](/home/sat/mcrl-v025-qcollinear-ws/scripts/qcollinear_probe.py), [`scripts/null_floor.py`](/home/sat/mcrl-v025-qcollinear-ws/scripts/null_floor.py), [`scripts/mechanism.py`](/home/sat/mcrl-v025-qcollinear-ws/scripts/mechanism.py), [`ref/penalties.py`](/home/sat/mcrl-v025-qcollinear-ws/ref/penalties.py).

Resource discipline: `/home/sat/mcrl-leo-handover/.venv/bin/python` only; that checkout and its `.venv` untouched. One Python process at a time, never more than two. `nice -n 16`. `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, `NUMEXPR_NUM_THREADS`, `BLIS_NUM_THREADS`, `VECLIB_MAXIMUM_THREADS` all `1`. Peak RSS by `/usr/bin/time -v`: **680,536 KiB** (main probe, 2:55.64 wall), **696,432 KiB** (null floor, 0:08.92), **679,840 KiB** (mechanism). All well under the 4 GB cap.
