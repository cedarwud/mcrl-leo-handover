**On 93 development anchors a perfect oracle C2 (the exact declared label, no learning, added to exact C1 in the stage-C additive selector) moves realised pooled EE from 35.2347 to 35.4734 Mbit/J (+0.2387 Mbit/J, +0.68% relative to exact-C1-only, step-cluster 95% interval −3.60% to +5.73%; worse at 20 of the 30 anchors where it changes the choice, −2.10% on the 22-anchor subset), and by exactly zero under the sealed tie-break reading; exact C1 and exact C2 per-user argmax agree on 29.56% of 9,300 decisions; a test that separates real horizon value from residual fitting does exist (time-indexed endpoint attribution plus input-provenance ablation), but it needs a multi-step realised continuation endpoint that no current panel has, so the residual redefinition cannot be adopted yet.**

`DIAGNOSTIC_NOT_CLAIM` · C2TARGET · 2026-09-10/11 (UTC)

## Answer in four lines

1. **Route 2 has no demonstrable EE value at this operating point.** With perfect declared labels, including C2 changes pooled EE by an amount the anchor bootstrap cannot tell from zero. Its sign flips between the 22-anchor and 93-anchor sets. Where it changes the decision it is harmful twice as often as it helps. Under the sealed tie-break reading it cannot change a single decision.
2. **C2 is not redundant with C1 at the label level.** Their argmax agrees on only 29.56% of per-user decisions, and adding C2 changes 34.20% of per-user choices. The sealed catalogue then collapses those disagreements into one binary choice between two whole-network proposals, and that choice is where C2's leverage is lost.
3. **The project's EE endpoint cannot see what C2 declares.** The endpoint is open-loop and covers one step (step *t*, 48 boundaries). C2 is declared as value at steps *t*+1..*t*+3. Any C2 marginal measured on this endpoint, including the published learned **+27.947%**, is a step-*t* effect and cannot be horizon value.
4. **The objection to the residual target stands, but it can be answered with an instrument that does not exist yet.** A time-held-out split is necessary but not sufficient. The distinguishing test is to attribute the realised marginal to the step *t* versus steps *t*+1..*t*+3, and to check which inputs it flows through. Until that endpoint exists, the redefinition is **not adoptable**.

## Evidence classes and the four fields

- `[RUN]` verified by running code on `sat` in this work; `[DERIVED]` arithmetic or a direct consequence of quoted code/definitions; `[INFERRED]` interpretation.
- Every EE figure below carries field block **[E]** unless another block is named:
  - **Reference:** the arm named in the row. Every marginal is taken against `C1_ONLY` (exact C1, C2 excluded), which is the oracle `DROP_C2`.
  - **Information class:** development, learner-free exact-label oracle. The set is 93 development anchors: world 1 steps 0–29 and world 2 step 0, each with carriers nearest-eligible / stay-if-possible / random-masked. The corpus is `/home/sat/mcrl-v025-exact93-ws/artifacts/exact-label-corpus-93-20260910`, corpus digest `db2b4007…c94b` per its builder, and all 93 shard sidecars were re-verified. There are no seeds and no learner. The catalogue definition is the sealed `bounded-union-v2`. Labels are selection-time nominal boundary-0 values. The 93-anchor corpus was still being trained on by another agent. Its **corpus** is complete and verified, and it was read only.
  - **Estimand:** the pooled EE of the configuration each score selects, open loop, at the anchor step only.
  - **Numerator:** Σ full-buffer bits ÷ Σ joules, from ONE fresh realised dense full-48 `StepEvaluator` batch per anchor.
- Label statistics carry block **[L]**:
  - **Reference:** as named.
  - **Information class:** development exact labels, 93 anchors, 9,300 (anchor, user) groups, 90,938 rows. No physics was run.
  - **Estimand:** per-user argmax agreement, or Pearson/Spearman correlation.
  - **Numerator:** agreeing groups, or rows.
- **Which set, and why.** The 93-anchor build is the largest verified set, so it is primary. Its first 22 world-1 shards are **byte-identical** (SHA-256) to the 22-anchor corpus `/home/sat/mcrl-v025-exacttrain-ws/artifacts/exact-label-corpus-20260910`, digest `3dd10c17…08e9`. That subset is reported separately as the digest-anchored cross-check. `[RUN]`

## 1. What C2's declared target is

### Sealed declaration

- `V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md` line 15 (SHA-256 `ba867d0d…7f49`, equal to the sealed sidecar in `/home/sat/mcrl-records/decisions/`):
  > "C2 = declared continuation value excluding the immediate term (three offsets, −κ per absorbing lost offset). κ per stage-4 item 24; all in bits / κ."
- `V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.1-AMENDMENT-2026-09-08.md` line 9:
  > "C2 = future required-power / cap / service-survival forecasts (astra round 3 §2 items 26–28)"

### Code that computes it

The code is `c2_persistence_forecast` in `/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/targets.py`, lines 251–310 (file SHA-256 `e951aa2a…b4ab`). The imported corpus builder uses this tree. Its load-bearing lines are:

```python
# targets.py:298-310
        if alive:
            core += (selected.outcome.bits - baseline.outcome.bits) - eta * (
                selected.outcome.joules - baseline.outcome.joules
            )
            retained.append(selected)
            if not selected.valid or not selected.survives:
                alive = False
                lost += 1
        else:
            lost += 1
            retained.append(selected)
    penalty = kappa * lost
    return C2Label(core, lost, penalty, (core - penalty) / kappa, tuple(retained))
```

In words: over offsets 1, 2 and 3, it accumulates the candidate-minus-default bits − η_ref·joules while the candidate is alive. The first offset at which the candidate is invalid or not served is still counted, then every later offset is lost. Each lost offset is charged −κ. The normalized label is `(forecast_surplus_bits − κ·lost)/κ`.

- The exact pilot branch calls it at `scripts/run_v025_pilot_c3.py:601` and serializes `c2_label_bits = forecast_surplus_bits − persistence_penalty_bits` at line 676. The pilot SHA-256 is `95103bb9…435d`, unchanged.
- The projections come from `_batched_stage2_forecasts`. The pilot overrides the forecast boundaries to `(0,)` at line 108, so each offset is a **nominal, boundary-0** snapshot, not a realised 48-boundary outcome. `[DERIVED]`

### Surrogate actually shipped in the older corpus

The surrogate lives in `scripts/run_v025_pilot_c3.py`, lines 402–427 and 462. It is not a bits/joules quantity at all:

```python
# :424  per alive offset      c2_normalized += tanh(log(future_gain_ratio)) if survives else -1.0
# :427  after first loss      c2_normalized -= 1.0
# :462  c2_label_bits = kappa * c2_normalized
```

So the surrogate is κ·Σ tanh(log of the provider-primitive link-gain ratio versus the future default), with the same absorbing −1 per lost offset. The declared target uses whole-network bits and energy of the full 100-user configuration. The surrogate uses a per-link gain ratio squashed by tanh.

Argmax disagreement between exact and surrogate C2 over the 10 declared options per user, reproduced here as an instrument check `[RUN]`:

- 22-anchor corpus: 1,216 of 2,200, **55.2727%**
- 93-anchor corpus: 4,598 of 9,300, **49.4409%**
- C1: 51.6818% (22 anchors) and 57.9570% (93 anchors)

All four equal the published figures exactly.

### Two sealed readings of how C2 enters selection, and they disagree

- **Tie-break reading.** Priority declaration v1.6 §2 (line 8, "C2 enters the set-level selector as a tie-break only", with a 1e-9 relative tolerance). v1.9 §5 (line 9): "C2's oracle effect is expected to be zero by construction … FULL and DROP_C2 coincide."
- **Additive reading.** Stage-C contract line 20: "deployed S3 optimises the **complete** score C1 + C2 + Ψ̂ over 𝒞". The scorer that produced the five-arm numbers sums the two routes: `score_stagec_checkpoints.py:490-499`, `for route in ("C1", "C2"): total += model[route].score(selected) − model[route].score(reference)`.

I report both. The additive one is what a perfectly learned stage-C head would do. I do not adjudicate between them. The disagreement between two sealed documents is itself a finding for the owner.

## 2. Does the declared target carry EE value? A perfect oracle C2

### Construction `[RUN]`

For each anchor I rebuilt the sealed catalogue with the engine's own `_catalogue_with_census`: 91,547 configurations over 93 anchors, every one covered by exact corpus rows, 0 uncovered. Each configuration is scored in exactly the shape the deployed selector uses:

> Σ over users of [label(u, a) − label(u, a⁰)], argmax over the catalogue, tie-break on the lowest configuration id.

This is the same rule as the engine's `_set_score_select`. The arms are:

| arm | score |
|---|---|
| `C1_ONLY` | ΔC1 (the oracle DROP_C2) |
| `FULL` | ΔC1 + ΔC2 |
| `C2_ONLY` | ΔC2 |
| `BASE` | the carrier reference, no move |
| `EE_B0_BEST` | the catalogue member with the highest realised boundary-0 EE; a within-catalogue ceiling, not a policy |

The incumbent-row C1 label is asserted to be exactly 0 for every user, and it is.

### Pooled result

Block [E]. Served and rate-target attainment are fractions of user slots, from the same endpoint batch.

| arm | pooled EE (Mbit/J) | vs `C1_ONLY` | served | rate-target attainment |
|---|---:|---:|---:|---:|
| `BASE` | 10.1469 | −71.20% | 0.7992 | 0.1201 |
| `C1_ONLY` | **35.2347** | reference | 0.9858 | 0.2678 |
| `FULL` | **35.4734** | **+0.68%** (+0.2387 Mbit/J) | 0.9871 | 0.2648 |
| `C2_ONLY` | 27.6826 | −21.43% | 0.9401 | 0.2537 |
| `EE_B0_BEST` | 38.9767 | +10.62% | 1.0000 | 0.2768 |

### Uncertainty and robustness `[RUN]`

The bootstrap resamples 31 clusters with 2,000 replicates. A cluster is one (world, step) decision instant, holding its three carrier anchors.

| contrast | point | 95% interval |
|---|---:|---:|
| `FULL` vs `C1_ONLY` | +0.68% | **[−3.60%, +5.73%]** |
| `C2_ONLY` vs `C1_ONLY` | −21.43% | [−31.04%, −9.57%] |

The 22-anchor digest-anchored subset (world 1, steps 0–7):

| arm | pooled EE (Mbit/J) | served | attainment |
|---|---:|---:|---:|
| `C1_ONLY` | 42.4592 | 0.9873 | 0.2723 |
| `FULL` | 41.5656 | 0.9900 | 0.2627 |

That is **−0.8937 Mbit/J, −2.10%**, with 7 of 22 choices changed. The sign of the C2 marginal is not stable across the two verified sets. `[RUN]`

By world: world 1 (90 anchors) goes from 34.6174 to 34.8800, +0.76%. World 2 (3 anchors) goes from 68.3505 to 66.0149, −3.42%. `[RUN]`

The unweighted per-anchor geometric-mean ratio `FULL/C1_ONLY` is **−1.39%** over all 93 anchors and −4.35% over the 30 changed anchors. The pooled +0.68% is a ratio of sums, so energy-heavy, low-EE anchors weigh more in it. `[RUN]`

### Where the choice changes: 30 of 93 anchors `[RUN]`

- `FULL` beats `C1_ONLY` at the endpoint at 10 anchors and loses at 20. At realised boundary 0 it is better at only 8 of the 30.
- The pooled gain is carried by the **4 low-EE anchors** (C1_ONLY below 40 Mbit/J: 006, 055, 056, 067). `FULL` wins all four, by +42% to +97%. In two of them (006, 067) C1 had picked a small move (a beam evacuation, a pair) and C2 pushed the choice to an all-user proposal.
- In the other 26 anchors `FULL` wins 6 and loses 20.
- **`FULL` equals `C2_ONLY` at all 30 changed anchors.** In the additive sum C2 dominates C1. The median C2 score gained is 154.0 κ against a median C1 score given up of 16.7 κ. That fits C2's three-offset range and its absorbing −κ penalties. `[RUN]`, `[DERIVED]`

### Structure of the decision `[RUN]`

- The selected configuration is an `s0-top-two` all-user proposal for 83 of 93 `C1_ONLY` picks, 85 of 93 `FULL` picks, and **all 93** `EE_B0_BEST` picks. These are the two whole-network profiles in which every user takes its first or second option.
- The set-level decision is therefore close to a binary choice between two proposals. `C1_ONLY` lands on the realised boundary-0 best catalogue member at 64 of 93 anchors, `FULL` at 49 of 93.
- Both arms sit about 9–10% below the within-catalogue ceiling (`EE_B0_BEST`).

### Tie-break reading, sealed v1.6 §2 and v1.9 §5 `[RUN]`

- The exact-C1 maximiser is **unique at 93 of 93 anchors**. The tie set size is 1 everywhere, and the smallest relative gap to the runner-up is 1.3e-4, far above 1e-9.
- The C2 tie-break therefore changes **0 of 93** decisions, and the oracle C2 marginal is **exactly zero**, as v1.9 §5 predicted.
- The same pass rebuilt the identical `C1_ONLY` pick at 93 of 93 anchors, a determinism check across processes.

### Reading

- **At this operating point, a perfect declared C2 has no demonstrable EE value.** The additive gain is +0.68%, the interval spans −3.6% to +5.7%, the sign reverses on the 22-anchor subset, and the per-anchor record is 10 better against 20 worse. The tie-break gain is 0. No head can do better than the perfect label on this selector, so **the target is the constraint, not the head**, for this endpoint. `[DERIVED]` from the oracle bound.
- **The endpoint is structurally blind to horizon value.** Every panel anchor is open loop: `transition_from` is the carrier's step *t*−1 configuration, independent of the arm, and only step *t* is scored. C2 declares value at *t*+1..*t*+3, which this endpoint never scores. So what was measured is C2's usefulness as a step-*t* selection signal, and a C2 horizon benefit is unmeasurable here, not measured and found absent. `[DERIVED]` from the evaluator construction.
- **The published learned five-arm C2 marginal (+27.947%) used the same open-loop single-step endpoint, so it cannot be horizon value.** A perfect declared label buys +0.68% on this endpoint. So a learned C2 head's 28% on a comparable endpoint is not explained by the declared target's information. The candidates are a second current-slot scorer, surrogate-label effects (that run used surrogate labels), or panel contamination. `[INFERRED]`. The panels differ, and nothing was re-scored here.

### Per-anchor detail for the 30 changed anchors

Block [E]; EE in Mbit/J. All 93 anchors are in `.scratch/c2target/oracle-ee-93-merged.json` → `per_anchor`.

| world | anchor | step | carrier | C1_ONLY EE | served | attain | FULL EE | served | attain | FULL/C1_ONLY − 1 | C1_ONLY pick → FULL pick (changed users) |
|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 001 | 0 | stay-if-possible | 71.8385 | 1.00 | 0.34 | 62.3987 | 1.00 | 0.34 | −13.14% | s0-top-two (100) → s0-top-two (100) |
| 1 | 004 | 1 | stay-if-possible | 59.7366 | 1.00 | 0.33 | 65.7924 | 1.00 | 0.40 | +10.14% | s0-top-two (100) → s0-top-two (100) |
| 1 | 006 | 2 | nearest-eligible | 21.3258 | 0.94 | 0.14 | 30.2278 | 1.00 | 0.23 | +41.74% | beam-evacuation (5) → s0-top-two (100) |
| 1 | 013 | 4 | stay-if-possible | 80.3056 | 1.00 | 0.44 | 61.8389 | 1.00 | 0.36 | −23.00% | s0-top-two (100) → s0-top-two (100) |
| 1 | 015 | 5 | nearest-eligible | 78.8406 | 1.00 | 0.46 | 62.5973 | 1.00 | 0.35 | −20.60% | s0-top-two (100) → s0-top-two (100) |
| 1 | 016 | 5 | stay-if-possible | 78.8406 | 1.00 | 0.46 | 62.5973 | 1.00 | 0.35 | −20.60% | s0-top-two (100) → s0-top-two (100) |
| 1 | 018 | 6 | nearest-eligible | 64.9262 | 1.00 | 0.26 | 40.7024 | 1.00 | 0.19 | −37.31% | s0-top-two (100) → s0-top-two (100) |
| 1 | 025 | 8 | stay-if-possible | 81.2479 | 1.00 | 0.47 | 63.0349 | 1.00 | 0.42 | −22.42% | s0-top-two (100) → s0-top-two (100) |
| 1 | 026 | 8 | random-masked | 77.0220 | 1.00 | 0.47 | 60.9423 | 1.00 | 0.44 | −20.88% | s0-top-two (100) → s0-top-two (100) |
| 1 | 029 | 9 | random-masked | 67.6077 | 1.00 | 0.37 | 79.7512 | 1.00 | 0.52 | +17.96% | s0-top-two (100) → s0-top-two (100) |
| 1 | 037 | 12 | stay-if-possible | 62.6988 | 1.00 | 0.37 | 56.2452 | 1.00 | 0.40 | −10.29% | s0-top-two (100) → s0-top-two (100) |
| 1 | 048 | 16 | nearest-eligible | 81.1897 | 1.00 | 0.44 | 65.2002 | 1.00 | 0.39 | −19.69% | s0-top-two (100) → s0-top-two (100) |
| 1 | 049 | 16 | stay-if-possible | 81.1897 | 1.00 | 0.44 | 65.2002 | 1.00 | 0.39 | −19.69% | s0-top-two (100) → s0-top-two (100) |
| 1 | 051 | 17 | nearest-eligible | 49.1015 | 1.00 | 0.20 | 52.2664 | 1.00 | 0.24 | +6.45% | s0-top-two (100) → s0-top-two (100) |
| 1 | 052 | 17 | stay-if-possible | 49.1015 | 1.00 | 0.20 | 52.2664 | 1.00 | 0.24 | +6.45% | s0-top-two (100) → s0-top-two (100) |
| 1 | 055 | 18 | stay-if-possible | 14.8409 | 1.00 | 0.05 | 26.7142 | 1.00 | 0.03 | +80.00% | s0-top-two (100) → s0-top-two (100) |
| 1 | 056 | 18 | random-masked | 14.9258 | 1.00 | 0.04 | 27.5711 | 1.00 | 0.05 | +84.72% | s0-top-two (100) → s0-top-two (100) |
| 1 | 063 | 21 | nearest-eligible | 73.4026 | 1.00 | 0.39 | 54.5090 | 1.00 | 0.26 | −25.74% | s0-top-two (100) → s0-top-two (100) |
| 1 | 064 | 21 | stay-if-possible | 53.9349 | 1.00 | 0.26 | 73.4026 | 1.00 | 0.39 | +36.09% | s0-top-two (100) → s0-top-two (100) |
| 1 | 067 | 22 | stay-if-possible | 19.0094 | 0.94 | 0.10 | 37.4627 | 1.00 | 0.12 | +97.07% | pairwise-top10-top2 (2) → s0-top-two (100) |
| 1 | 072 | 24 | nearest-eligible | 61.8515 | 1.00 | 0.38 | 69.1228 | 1.00 | 0.43 | +11.76% | s0-top-two (100) → s0-top-two (100) |
| 1 | 075 | 25 | nearest-eligible | 73.1485 | 1.00 | 0.45 | 54.8557 | 1.00 | 0.30 | −25.01% | s0-top-two (100) → s0-top-two (100) |
| 1 | 078 | 26 | nearest-eligible | 59.0122 | 1.00 | 0.28 | 28.7229 | 1.00 | 0.11 | −51.33% | s0-top-two (100) → s0-top-two (100) |
| 1 | 084 | 28 | nearest-eligible | 74.2287 | 1.00 | 0.39 | 62.7011 | 1.00 | 0.35 | −15.53% | s0-top-two (100) → s0-top-two (100) |
| 1 | 085 | 28 | stay-if-possible | 74.2287 | 1.00 | 0.39 | 62.7011 | 1.00 | 0.35 | −15.53% | s0-top-two (100) → s0-top-two (100) |
| 1 | 086 | 28 | random-masked | 71.1958 | 1.00 | 0.34 | 59.5596 | 1.00 | 0.36 | −16.34% | s0-top-two (100) → s0-top-two (100) |
| 1 | 087 | 29 | nearest-eligible | 53.9065 | 1.00 | 0.26 | 52.5483 | 1.00 | 0.30 | −2.52% | s0-top-two (100) → s0-top-two (100) |
| 1 | 088 | 29 | stay-if-possible | 53.9065 | 1.00 | 0.26 | 52.5944 | 1.00 | 0.30 | −2.43% | s0-top-two (100) → s0-top-two (100) |
| 2 | 091 | 0 | stay-if-possible | 68.5658 | 1.00 | 0.38 | 67.2133 | 1.00 | 0.41 | −1.97% | s0-top-two (100) → s0-top-two (100) |
| 2 | 092 | 0 | random-masked | 67.9197 | 1.00 | 0.36 | 62.5596 | 1.00 | 0.42 | −7.89% | s0-top-two (100) → s0-top-two (100) |

## 3. What C2 adds on top of C1, and whether it is redundant

Block [L]; all `[RUN]`. The 22-anchor corpus value is in brackets.

| statistic | value |
|---|---:|
| exact C1 vs exact C2 per-user argmax agreement (10 declared options) | **2,749 / 9,300 = 29.56%** [680 / 2,200 = 30.91%] |
| exact C1 vs exact (C1+C2) argmax agreement: adding C2 changes the per-user choice in 3,181 groups | 6,119 / 9,300 = 65.80% [65.27%] |
| exact C2 vs exact (C1+C2) argmax agreement | 5,560 / 9,300 = 59.78% |
| Pearson / Spearman, raw normalized labels (90,938 rows) | 0.3934 / 0.4580 [0.4792 / 0.4957] |
| Pearson / Spearman, deltas against the incumbent row (81,638 non-incumbent rows) | 0.4168 / 0.4905 [0.5104 / 0.5358] |
| ΔC2 exactly zero (C2 cannot discriminate the move at all) | 18,390 / 81,638 = 22.53% |
| argmax is the incumbent action: C1 / C2 / C1+C2 | 13.61% / 25.43% / 7.63% |

[DERIVED] **C2 is not a re-derivation of C1.** A correlation of about 0.4–0.5 and 30% argmax agreement mean it carries largely different per-user rankings, so redundancy is not why route 2 fails.

What happens instead is funnelling. About 34% of per-user choices change, but at set level only 30 of 93 anchors change, and those changes are almost all a swap between the two `s0-top-two` whole-network proposals. When C2 wins that swap, it picks the proposal with the lower step-*t* EE 20 times out of 30. `[RUN]`

## 4. The residual-target proposal and the objection

### (a) What the redefinition is, algebraically `[DERIVED]`

- **"Subtract" reading.** Take C2′ = C2 − β·C1. Under exact labels, argmax(C1 + C2′) = argmax((1−β)·C1 + C2). The redefinition is then a **re-weighting**, not new information. At oracle level it can only move the C1/C2 mixing weight. Any advantage in a learned system is a learnability effect.
- **"Condition" reading.** Take C2′ = C2 − E[C2 | current-slot state]. A head that sees only decision-time state learns E[C2′ | its inputs]. If its inputs equal the conditioning set, that expectation is 0 by construction. The only learnable part is whatever C2′'s inputs carry that the current-slot conditioning set does not.

  In Q2 those inputs are the 12 offset-indexed slots 10–21: `valid`, `survival`, `minimum_decoding_margin` and `mean_acm_spectral_efficiency` at offsets 1, 2 and 3 (`src/mcrl/stagec_v025/state.py:48-65`). Also relevant are the forward-looking current slots `forecast_se_trend`, `remaining_d2_time` and `remaining_visibility_time`.

### (b) The candidate test (held-out split over time): necessary, not sufficient `[DERIVED]`

A forward time split removes leakage between anchors that share a decision instant, which the three carriers and the overlapping 3-offset label windows both create. It also tests stationarity.

It does **not** separate the two hypotheses. C1's leftovers are systematic. Examples are the nominal-versus-realised fading gap, the boundary-0-versus-48-boundary gap, and the sealed C1 head's level-calibration deficit (LOAO −34.63 versus −1.84 for linear, as quoted in the brief). A C2′ fitting them would generalise over time exactly as well as one carrying horizon value. The split becomes informative only when it is taken over the **target's** time index. That is test T1.

### (c) A test that does distinguish them

This is proposed, not implemented. Its premise is `[DERIVED]`: C1 is by definition a step-*t* quantity, F(aᵢ, a⁰₋ᵢ) − F(a⁰) at the current step, so C1's leftovers pay out at step *t*. Any gain that appears only at *t*+1..*t*+3 cannot be a C1 leftover.

- **T1: time-indexed endpoint attribution.** Learner-free first, then with a learned C2′.
  - Setup: for each anchor, commit the `FULL′` pick and the `C1_ONLY` pick at step *t*, then roll each forward on the **realised** field through steps *t*+1..*t*+3. Use the same declared continuation C2 uses (persistence with absorbing loss). Each arm uses its own committed configuration as `transition_from`.
  - Score pooled EE separately on step *t* (full-48) and on steps *t*+1..*t*+3 (full-48 each), each with BASE in the same fresh `evaluate_many` batch.
  - Pre-declared readings:
    - **Horizon value**: the pooled marginal on *t*+1..*t*+3 is positive with a step-cluster interval excluding 0, **and** it is not smaller than the step-*t* marginal.
    - **Residual fitting**: the marginal is concentrated at step *t* and the *t*+1..*t*+3 marginal interval covers 0.
    - Anything else is **indeterminate**. The reading is not re-cut afterwards.
- **T2: input provenance, for the learned C2′ head only.**
  - Setup: re-score T1 twice. First with Q2 slots 10–21 replaced by their training means. Then, separately, with the current slots 0–9 replaced by their training means.
  - Readings:
    - **Horizon value**: the *t*+1..*t*+3 marginal collapses when the offset slots are neutralised.
    - **Residual fitting**: the marginal survives offset-slot neutralisation, meaning it is being made from current-slot inputs that C1 also sees.
- **Time split as a guard.** Run T1 on a forward split: world 1, train steps 0–19, test steps 23–29. The 3-step purge is needed because labels at step *s* read outcomes through *s*+3. That leaves 60 train and 21 test anchors. The 3 world-2 anchors cannot be split over time.

### (d) Is it measurable here?

- **Not on current data.** `[RUN]` / `[DERIVED]` The corpus forecast projections are nominal boundary-0 snapshots, not realised outcomes. Every scoring panel, and this harness, is open loop and scores step *t* only. No artefact holds realised *t*+1..*t*+3 outcomes of an arm's committed configuration.
- **The engine has the parts.** The tape has 33 steps, so *t*+3 ≤ 32 for every development step. `StepEvaluator` accepts any step, `field="realised"` and `transition_from=<arm's committed config>`. The endpoint batch here took seconds per anchor, so T1 is about 3 more such batches per arm per anchor, a small cost. `[DERIVED]` from the measured timings (the catalogue plus both evaluators took 7–10 s per anchor after a 215–250 s tape build).
- **T2 needs a learned C2′ head.** None exists, and building one is out of scope.

**Verdict on the objection.** It is correct for the current endpoint. On an open-loop single-step endpoint, any positive C2 or C2′ marginal is by construction a step-*t* effect, so it is at best current-slot information C1 missed. That is the residual-fitting branch. A distinguishing test exists (T1, strengthened by T2), but it needs one new instrument. **Until T1 exists, the residual redefinition is not adoptable.** Adopting it now would guarantee that a positive marginal cannot be read as horizon value. `[DERIVED]`

## 5. What a better target would be

Proposal only; nothing below was implemented or run.

1. **Make target and endpoint agree before changing either.**
   - If route 2 is to claim horizon value, the committed endpoint must score steps *t*+1..*t*+3 of each arm's own trajectory: the T1 instrument, or a closed-loop episode.
   - If the endpoint stays open-loop single-step, route 2 has **no legitimate EE channel**. Any redefinition would then be a step-*t* quantity, C1 split in two, and not identifiable as a separate route.
2. **Fix the mixing rule before measuring.** The sealed tie-break reading (v1.6/v1.9) gives exactly 0. The additive reading (the stage-C contract and scorer) lets C2 dominate the sum by about 9× in κ units, and it picks the lower-EE proposal in 20 of 30 changes. Neither is a neutral default. The C1/C2 weight is a design decision to seal, and under exact labels it is equivalent to the "subtract" form of the residual target (§4a).
3. **Give continuation somewhere to act.** In `bounded-union-v2` the decision reduces to two all-user proposals, so a per-user continuation signal has one binary lever. A continuation route would need catalogue members that differ in **persistence**, for example stay-versus-move variants of the same proposal. `[INFERRED]` from §2's structure, and not tested.
4. **Candidate target, if (1) is met.** Use a **realised continuation delta**: T1's *t*+1..*t*+3 realised F-difference of the committed profile against the declared continuation of C1's pick. It is defined on the same field and boundaries as the endpoint, and it is not a residual of C1 by construction, so the §4 objection does not arise. Its value would first have to be shown learner-free, with an oracle marginal on the T1 endpoint, before any head is trained.

## 6. Mandatory evaluator rule: compliance `[RUN]`

- **Selection comparison.** For each anchor there was ONE fresh `StepEvaluator(field="realised", boundary_indices=(0,))`. BASE and **every** covered catalogue member entered through a single `evaluate_many` call. Profiles were read from that evaluator's own `_evaluated` dict. BASE's presence was asserted.
- **Endpoints.** For each anchor there was ONE separate fresh realised dense full-48 `StepEvaluator` (`boundary_indices=tuple(range(48))`). BASE and all five arm configurations were in one `evaluate_many` call, and BASE's presence was asserted.
- **Stub.** On both evaluators `evaluate` was replaced by a raising stub immediately after `evaluate_many`, with a shared counter. **Result: selection 0 calls, endpoint 0 calls, over all 93 anchors, asserted at exit in each of the 3 workers and again in the merge.** No foreign cache was used; no row-builder evaluator was reused.
- **Disclosure.** The sealed catalogue builder `_catalogue_with_census` constructs its **own** internal nominal boundary-0 evaluator for ranking users, and uses scalar `evaluate` on its own freshly populated cache. That is sealed code, left unmodified. It is catalogue construction, not a selection comparison of mine, and it never touches the stubbed evaluators.

## 7. Scope, resources, reproducibility `[RUN]`

- **Constraints.** Interpreter: `/home/sat/mcrl-leo-handover/.venv/bin/python` only, never modified. Every run used `nice -n 16` and all six BLAS/OMP thread variables = 1. At most 3 python processes of mine ran at once, and each process enforced a 4.9 GB `RLIMIT_AS`.
- **Peak RSS** (`/usr/bin/time -v` maximum resident set size):

  | run | peak RSS (KiB) |
  |---|---|
  | oracle workers | 1,787,936 / 1,789,444 / 1,752,348 |
  | tie-break workers | 1,781,068 / 1,724,144 / 1,780,888 |
  | label analysis | 73,876 |
  | merge | 14,732 |

  All are well under 5 GB.
- **Development anchors only.** Worlds come from `TRAIN_WORLDS = DEVELOPMENT_WORLD_DOMAINS[:2]`. No evaluation-only claim date was read. No sealed artefact was changed; the pilot, targets and contract digests are quoted above, and the pilot is unchanged. Nothing was written outside `/home/sat/mcrl-v025-c2target-ws`, which was `git init`'d and is not committed.
- **Interruption, disclosed.** A first 22-anchor run was killed together with the controlling session at about 19:00Z. It had produced no output and nothing was imported from it. Only its one-anchor smoke file (`smoke-1.json`) exists. The full runs above were started fresh at 23:4xZ.

### Evidence files in `/home/sat/mcrl-v025-c2target-ws/.scratch/c2target/` (SHA-256)

| file | SHA-256 |
|---|---|
| `oracle_ee.py` | `3a1ca6b40849ac0498fdb770ab8042c0447c743370a7838a74b76e7101a9bcdb` |
| `ties.py` | `9bb7979bb4d334ddcc2501a769bc191ef216675a6b06802db008f7a3cb3e249d` |
| `labels.py` | `8c562d77492250f1bfd575b263a98e05889729c726ef9aea3986a7e91d85fe91` |
| `merge.py` | `8779fea44d68e6d16bcd11814682ceb13f05fdd2f91f900d6c016c8099d3b95e` |
| `subset.py` | `083be35ccfef5142f7256276f6c6381bcc609a85aa6e7782b63b746f252dc746` |
| `oracle-ee-93-w0.json` | `8b3345e32d067ed1276f91bc6381ba986ae80747e9b52c849dc3154bcf3f6a7d` |
| `oracle-ee-93-w1.json` | `4aa384f0614e8644d271e39ffe2a05c9c5f0a03300ebfb1167bbf908afba96d5` |
| `oracle-ee-93-w2.json` | `b08e960fdeba6da01885a0ccac511002daa7a99a69465a2e52816d5acf4308d0` |
| `oracle-ee-93-merged.json` | `d5c579f7f7a96c8debf51dd8ea4516cd6d9b2e654bf66d986205ba4000151568` |
| `ties-93-w0.json` | `cb744fc0a8e3558f75e33d9e3f37e74d59d6661b7a39fbbdf71a994fa3e710c5` |
| `ties-93-w1.json` | `a3dfbca4e63cec4446bb4e948661a5423203f4d73c852db309b0d2fea088e034` |
| `ties-93-w2.json` | `03d41833314fbfee6fe5482138ac6e4b27fc9f8d26e9d90eb57a2ed7f85b92fc` |
| `labels-93.json` | `d3a29e4ea4fa85d2f3c569e20defa6dbb343050f8407ddb8cc3a3363e60040d2` |
| `labels.json` (22) | `474c57e78f42ab913f40633df6b54e80d60114bbf9567252fadffc239d60591d` |
| `subset-analysis.json` | `f92e53f90429585e43f46c0c9ff4c2071fd77d5a25c8ebacce13102400c20b7d` |

Reproduce with `oracle_ee.py <corpus> <worker> 3 oracle-ee-93-w<worker>.json` for workers 0–2, then `merge.py oracle-ee-93 3 93`, `ties.py <corpus> <worker> 3 ties-93-w<worker>.json`, and `subset.py`.
