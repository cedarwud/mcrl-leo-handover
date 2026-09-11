**Held-out top-1 of a Q-network-architecture probe, predicting each source's action from the learner's own observation: C1 0.812 (`MAX_NOMINAL_GAIN`) / 0.838 (`A m=2dB`), C2 0.920 (`A m=9dB`) / 0.935 (`A m=12dB`), C3 0.714 (`B1_NO_NEW_BEAM`) / 0.683 (`B2_PREFER_SHARED`). For scale: the learner's own greedy policy, as a positive control, scores 0.877, and all six rules are exact functions of that observation. C1 and C2 are distinct by actions: they disagree on 35–55% of the same states, against 9–12% within each pair, and that gap is exactly the probability mass of one hysteresis-margin band. They are not distinct by states: C2's states lie inside C1's distribution, and only C1 reaches states C2 does not.**

Date: 2026-09-11. CFSCREEN. **No MODQN training. No `update()`, no gradient step on any Q-network, no optimizer on the learner.** The only fitted model is a behaviour-cloning probe, used as a measurement instrument. It is trained on logged rule actions and never touches the learner. Run locally with `.venv/bin/python`, at most 2 processes, `nice -n 16`, 1 BLAS thread. Peak RSS was 1.1 GB. Every number is a **diagnostic, not a gate.**

Evidence tags: **[V]** means I ran it or opened the source this session. **[D]** means arithmetic on [V] numbers. **[I]** means inferred.

**TLE archive provenance: every figure here comes from the UNPINNED local TLE archive.**
- [V] `MCRL_TLE_ROOT` was unset for every process in this run, so `resolve_tle_root()` fell back to `TLE_ROOT_DEFAULT` (`training_pipeline.py:773-787`). The docstring there says the local copy is the frozen 373 files plus 19 later days.
- [V] Every cell is bit-identical to FEASFRONT's `frontier.out`, so this run used the same archive FEASFRONT did.
- [coordinator-reported, not recomputed by me] That archive is file_set `e07f3e1e…`. A pinned archive, `427e6a91…`, now exists and gives different numbers. For example, RANDOM_MASKED is 52,420,510.10 bit/J on the pinned archive against 53,060,175.56 here.

**What stays valid.** Every screen compares rule vs rule vs learner inside one harness, and screens 2 and 4 use literally the same states, so those comparisons hold as such.

**What does not transfer.** No EE figure in this report (§1c, and the rule EE values quoted from FEASFRONT) is comparable to any pinned-archive result.

---

## 0. Harness, and the placebo that ties this run to FEASFRONT

- **I reused the rules and harness; I did not reimplement them.** `scripts/collect.py` `exec`s `.scratch/feasible-frontier/scripts/frontier.py` verbatim up to its main loop (sha256 `74e03c30…32fc6`). It then calls frontier's own `run()` unchanged, with the checkpoint loaded read-only. Logging is a wrapper around the arm function, and the wrapper also queries every other rule and the learner on the same state. [V]
- **Setup.** Same 24 episodes, seeds 42/1337/7, fresh env per cell. The checkpoint is `final-checkpoint.pt`, sha256 `e6b063ef…1b09c28b`, re-hashed this session. `c3s_physics_override.py` was copied into `scripts/` with identical bytes (`a5342447…`). [V]
- **Placebo: every cell's pooled bits, joules, EE, handover, φ1, φ2, served and active beams are bit-identical to `frontier.out`, for all 7 cells.** For example, `A m=12dB` is 101,467,361.953937 and TRAINED is 93,110,907.973748. [V]
  - The calibrated training scalar is lower than FEASFRONT's in every arm, by 0.005–0.016. The cause is src commit `c00aca3e` (16:23, "D-2 per-step floor"), which landed after `frontier.out` was written (15:58) [V: timestamps]. That commit changes only the outage-reward floor, so it cannot move EE [I]. The scalar is not used in any screen.
- **Instrument self-checks [V]:**
  - Each source's logged action equals its own query column on 24,000/24,000 rows.
  - The learner's greedy action, recomputed as masked argmax of the scalarized Q without touching `_train_rng`, equals `select_actions` on 24,000/24,000.
  - Per-head Q recomputed from the checkpoint reproduces the logged scalarized Q to 1.8e-7.
  - Reconstructing the B rules from the logged raw fields gives 0 mismatches, and so does reconstructing the A rules as `argmax(gain_dB + m·1[incumbent legal])`.
  - Empty-mask rows: 0 in every cell. The mean legal-set size is 26.3.

**Harness fact found in passing: only episode 0 is paired across cells. [V]** At step 0 of episode 0, all 2,400 rows are identical across every cell. At step 0 of episodes 1–23, `access` and `loads` are identical (all zero at reset), but `snr` and `theta` differ in 100% of rows. The cells are therefore **different episodes after the first**.
- Mechanism [I]:
  - `env_rng` draws each episode's start epoch (`trainer_env.py:178`).
  - The fading draws come from that same stream, and there is one draw per satellite in the step's set (`step.py:1352-1383`). I infer that set depends on the associations, so the draw count depends on the actions.
- Consequences:
  - FEASFRONT's "every arm uses the same 24 episodes" holds for the seeds, not for episodes 1–23.
  - Its JSRL audit attributed "theta identical in only 1–8% of paired rows" to candidate-table reordering. Different episodes is the larger cause [I].
  - All cross-cell EE comparisons here are **unpaired** (unpaired sems). Screen 2 is unaffected, because it queries rules on the *same* states. Screen 3 compares distributions drawn from different episodes. §3 shows that this exogenous difference alone gives R ≈ 1.

---

## 1. Representability

### 1a. Is the action a function of the observation at all? Yes, exactly, for all six. [V]

`scripts/obs_reconstruct.py` decodes the learner's own 112-dim float32 encoding back into rule inputs:
- `snr = expm1(block 2)`: the encoding is `log1p(snr)`. Maximum relative decode error is 2.4e-7.
- `loads = 100 · block 4`: exact.
- incumbent = the one-hot in block 1: exact.

It then applies each rule with the legal mask. **The decoded rule reproduces the logged action on 24,000/24,000 decisions for A0, A2, A9, A12, B1 and B2.** The information ceiling is therefore 100%. Every shortfall below is a limit of the function class or of the data, not missing information.

### 1b. BC probe, held out by episode

**Probe setup:**
- **Architecture:** the Q-network architecture itself, `mcrl.runtime.q_network.DQNNetwork(112 → 100 → 50 → 50 → 28, tanh)`, the same class and `TrainerConfig` defaults as each learner head. It is trained as a classifier with a **masked softmax** (illegal logits set to −1e9) and cross-entropy.
- **Split:** 3 folds **by episode**. Fold k holds out episodes with `ep % 3 == k` (8 episodes, 8,000 decisions). It trains on 14 episodes and uses the 2 highest-index training episodes as inner validation, only to pick the epoch.
- **Recipe:** Adam 1e-3, batch 256, 100 epochs, same for every source.
- **Input variants:** `raw` is the learner's own encoding and is the primary. `z` is z-scored on the training fold, as a diagnostic.
- **Controls** (declared before the run):
  - NULL: random legal labels; top-1 must sit at chance.
  - TR: the learner's own greedy actions; this is the positive control.
- **Regret** is the rule's own score gap:
  - A rules: `(gain_dB + m·1[inc legal])` of the rule's action minus that of the prediction, in dB.
  - B rules: the fraction of predictions outside the rule's allowed set (**viol**, i.e. lights a new or unshared beam when the rule would not), plus the gain-dB gap on the rest.
  - TR: the scalarized-Q gap.
- "Contested" means decisions where the incumbent is legal and is not the max-gain option. These are the only decisions on which the two trivial baselines disagree, about 70% of rows.

| source | catfish | predictor | held-out top-1 | fold range | top-3 | top-1 on contested | regret (rule's own score) |
|---|---|---|---:|---|---:|---:|---|
| `A m=0` = `MAX_NOMINAL_GAIN` | C1 | **probe (raw)** | **0.8117** | 0.806–0.816 | 0.940 | 0.762 | mean 0.244 dB; 18.8% of decisions > 0; p95 1.69 dB |
| | | probe (z) | 0.7618 | 0.751–0.776 | 0.892 | 0.704 | mean 0.488 dB |
| | | always-max-gain | 1.0000 (definitional) | | 1.000 | 1.000 | 0 |
| | | always-incumbent | 0.3025 | | 1.000 | 0.000 | mean 5.35 dB |
| `A m=2dB` | C1 | **probe (raw)** | **0.8377** | 0.831–0.850 | 0.945 | 0.785 | mean 0.243 dB; 16.2% > 0; p95 1.71 dB |
| | | probe (z) | 0.7960 | 0.787–0.812 | 0.902 | 0.730 | mean 0.453 dB |
| | | **always-max-gain** | **0.8755** | | 0.976 | 0.822 | mean 0.127 dB |
| | | always-incumbent | 0.4263 | | 1.000 | 0.178 | mean 3.78 dB |
| `A m=9dB` | C2 | **probe (raw)** | **0.9199** | 0.919–0.921 | 0.971 | 0.905 | mean 0.156 dB; 8.0% > 0; p95 0.43 dB |
| | | probe (z) | 0.9136 | 0.910–0.918 | 0.965 | 0.899 | mean 0.139 dB |
| | | always-max-gain | 0.5387 | | 0.712 | 0.354 | mean 2.18 dB |
| | | always-incumbent | 0.7478 | | 1.000 | 0.647 | mean 1.32 dB |
| `A m=12dB` | C2 | **probe (raw)** | **0.9353** | 0.932–0.939 | 0.980 | 0.935 | mean 0.119 dB; 6.5% > 0; p95 0.18 dB |
| | | probe (z) | 0.9313 | 0.929–0.935 | 0.976 | 0.931 | mean 0.124 dB |
| | | always-max-gain | 0.4730 | | 0.635 | 0.260 | mean 3.48 dB |
| | | always-incumbent | 0.8144 | | 1.000 | 0.740 | mean 0.88 dB |
| `B1_NO_NEW_BEAM` | C3 | **probe (raw)** | **0.7141** | 0.708–0.720 | 0.918 | 0.680 | **viol 0.074**; gap mean 0.53 dB |
| | | probe (z) | 0.7279 | 0.722–0.736 | 0.914 | 0.685 | viol 0.042; gap mean 0.64 dB |
| | | always-max-gain | 0.3847 | | 0.535 | 0.157 | viol 0.615 |
| | | always-incumbent | 0.6558 | | 0.824 | 0.561 | viol 0.050; gap mean 1.29 dB |
| `B2_PREFER_SHARED` | C3 | **probe (raw)** | **0.6829** | 0.672–0.695 | 0.903 | 0.673 | **viol 0.105**; gap mean 0.56 dB |
| | | probe (z) | 0.6965 | 0.684–0.704 | 0.905 | 0.674 | viol 0.057; gap mean 0.78 dB |
| | | always-max-gain | 0.3607 | | 0.522 | 0.166 | viol 0.639 |
| | | always-incumbent | 0.5973 | | 0.798 | 0.512 | viol 0.170; gap mean 1.15 dB |
| TRAINED greedy (positive control) | — | probe (raw) | 0.8766 | 0.869–0.881 | 0.983 | 0.870 | Q gap mean 0.0053 (per-state Q sd ≈ 0.155) |
| random legal labels (NULL) | — | probe (raw) | 0.0382 | 0.037–0.041 | 0.112 | — | chance 0.0386 / top-3 0.1158 |

[V] for every row. **Sensitivity** (added after reading the declared run, because its best epochs sat at 54–93 of 100): 400 epochs changes no top-1 by more than 0.002. For example, A0 goes 0.8117 → 0.8104 and A12 0.9353 → 0.9345. The shortfall is a plateau, not undertraining. The NULL control sits at chance (0.0382 against 0.0386). The 400-epoch NULL fit gives 0.0413, which is +2.2 binomial se and within noise across three variants.

### 1c. Closed loop: does the held-out probe reproduce the rule's operating point?

Each episode is driven by the fold model that never saw it (`scripts/bc_rollout.py`), on the same harness with frontier's `run()` unchanged. **Four fields for every EE number in this table:**
- **reference:** the source rule's own cell. For the TR row, the reference is the trained checkpoint.
- **information:** nominal. The selector sees only the 112-dim observation and the mask, with no realised current-step fading.
- **estimand:** pooled EE = Σ bits / Σ joules over 24 episodes × 10 steps (seeds 42/1337/7, fresh env per cell). It is unpaired across cells after episode 0; sems are unpaired per-episode.
- **numerator:** the env's own `system_throughput_bps · dt`, which is Σ per-user rate from `step.py:1022`. This is the same object FEASFRONT reports. I did not re-cap it and did not re-verify its buffer model this session.

| source | rule pooled EE (bit/J) | probe pooled EE (bit/J) | ΔEE | rule ho | probe ho | Δho | rule beams | probe beams | on-policy agreement |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `A m=0` | 111,504,571.39 | 110,501,828.62 | −0.90% (−0.7 sem) | 0.7120 | 0.7024 | −0.010 (−1.2 sem) | 63.72 | 64.45 | 0.818 |
| `A m=2dB` | 112,459,003.43 | 110,990,292.29 | −1.31% (−1.0 sem) | 0.5860 | 0.5736 | −0.012 (−1.3 sem) | 63.51 | 64.56 | 0.840 |
| `A m=9dB` | 105,701,579.47 | 103,828,295.17 | −1.77% (−1.4 sem) | 0.2753 | 0.2577 | −0.018 (**−4.4 sem**) | 69.21 | 70.56 | 0.929 |
| `A m=12dB` | 101,467,361.95 | 101,780,163.24 | +0.31% (+0.2 sem) | 0.2258 | 0.2215 | −0.004 (−1.4 sem) | 72.47 | 72.53 | 0.943 |
| `B1_NO_NEW_BEAM` | 103,474,767.67 | 99,041,224.96 | **−4.28% (−7.5 sem)** | 0.4250 | 0.4366 | +0.012 (+1.1 sem) | **37.86** | **47.33** | 0.660 |
| `B2_PREFER_SHARED` | 103,756,292.71 | 98,636,930.91 | **−4.93% (−5.6 sem)** | 0.4849 | 0.4976 | +0.013 (+1.4 sem) | **37.87** | **45.50** | 0.630 |
| TRAINED (control) | 93,110,907.97 | 95,597,552.54 | +2.67% (+1.6 sem) | 0.2799 | 0.2662 | −0.014 (−2.3 sem) | 67.90 | 65.89 | 0.875 |

[V] for the measured columns, [D] for Δ and sem ratios.
- The A-family probes land within about 1.4 sem of their rule's EE. Their per-step errors are near-ties that cost 0.1–0.25 dB, so the operating point survives.
- The `A m=9dB` probe holds slightly more often than the rule: it hands over 0.018 less, a resolved difference.
- **The C3 probes reproduce only about 70% of the consolidation.**
  - B1: active beams fall from the learner's 67.90 to 47.33, not to 37.86, which closes 68% of the gap [D]. B2 closes 75% [D].
  - Their pooled EE is resolvably below the rule's. They land at 98.6–99.0M, between the learner (93.1M) and the rule (103.5–103.8M).
  - Each off-set prediction lights a beam, and the probe's viol rate is 7–10% of decisions.

---

## 2. Distinctness by actions

`D(row, column)` = the fraction of (user, step) decisions where the row source's own action differs from the column rule's action, **computed on the row source's states**. Each cell uses 24,000 decisions. Reading the matrix both ways gives both directions. [V]

| states ↓ \ rule → | A0 (C1) | A2 (C1) | A9 (C2) | A12 (C2) | B1 (C3) | B2 (C3) | always-inc | TRAINED |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **A0** | 0 | 0.123 | 0.469 | 0.547 | 0.452 | 0.523 | 0.698 | 0.746 |
| **A2** | 0.125 | 0 | 0.363 | 0.441 | 0.454 | 0.547 | 0.574 | 0.637 |
| **A9** | 0.461 | 0.350 | 0 | 0.092 | 0.567 | 0.688 | 0.252 | 0.360 |
| **A12** | 0.527 | 0.427 | 0.095 | 0 | 0.589 | 0.721 | 0.186 | 0.337 |
| **B1** | 0.615 | 0.588 | 0.508 | 0.441 | 0 | 0.053 | 0.344 | 0.776 |
| **B2** | 0.639 | 0.627 | 0.570 | 0.505 | 0.052 | 0 | 0.403 | 0.835 |
| **TRAINED** | 0.785 | 0.707 | 0.450 | 0.386 | 0.728 | 0.833 | 0.347 | 0 |

**Catfish level** (mean over the directed member pairs, with min–max) [D]:

| pair | D mean | range |
|---|---:|---|
| within C1 (A0↔A2) | **0.124** | 0.123–0.125 |
| within C2 (A9↔A12) | **0.093** | 0.092–0.095 |
| within C3 (B1↔B2) | **0.052** | 0.052–0.053 |
| **C1 ↔ C2** | **0.448** | 0.350–0.547 |
| C1 ↔ C3 | 0.556 | 0.452–0.639 |
| C2 ↔ C3 | 0.574 | 0.441–0.721 |
| C1 ↔ learner | 0.719 | 0.637–0.785 |
| C2 ↔ learner | 0.383 | 0.337–0.450 |
| C3 ↔ learner | 0.793 | 0.728–0.835 |

On contested decisions only, C1↔C2 disagreement rises to 0.49–0.78 (`raw/screens.out`).

**The C1–C2 disagreement is exactly a margin band.** [V] On each A-source's states, `D(A_m1, A_m2)` equals the fraction of decisions whose gain gap `gain_dB(best legal) − gain_dB(incumbent)` lies in `(m1, m2]`. This holds to the digit: on A2 states, `D(A2, A9)` = 0.3633 and the (2, 9] band = 0.3633. On A0 states, `D(A0, A2)` = 0.1228 and the (0, 2] band = 0.1228. On A9 states, `D(A9, A12)` = 0.0919 and the (9, 12] band = 0.0919. This follows from the rule's definition [D], and the counts confirm it. The band masses are:

| states | incumbent gone or illegal | g = 0 (incumbent is best) | 0 < g ≤ 2 | 2 < g ≤ 9 | 9 < g ≤ 12 | g > 12 |
|---|---:|---:|---:|---:|---:|---:|
| A0 | 0.114 | 0.188 | 0.123 | 0.346 | 0.078 | 0.151 |
| A2 | 0.112 | 0.190 | 0.125 | 0.363 | 0.078 | 0.132 |
| A9 | 0.123 | 0.163 | 0.112 | 0.350 | 0.092 | 0.160 |
| A12 | 0.140 | 0.147 | 0.100 | 0.332 | 0.095 | 0.186 |

---

## 3. Distinctness by states: the FEASFRONT JSRL measure, unchanged

**Method.**
- Query: X's 2,400 encoded observations at step index t. Pool: Y's 2,400 at the same t.
- Both are z-scored on Y's own per-dimension mean and sd over its 24,000 rows (constant dimensions get sd = 1).
- `R` = mean 1-NN distance from query to pool ÷ mean leave-one-out 1-NN distance within the pool.
- `out95` = the fraction of query 1-NN distances beyond the pool's LOO 95th percentile. It is 0.05 for a pool against itself by construction.
- Values are averaged over t = 1…9. At t = 0, the reset state, R is 0.84–1.01 for every pair. That is the level produced by drawing different episodes alone (§0), so R ≈ 1 means no policy difference.
- The measure is asymmetric by construction: the pool sets both the z-scoring and the yardstick. [V]

**R (1..9)**, row = query, column = pool:

| query ↓ \ pool → | A0 | A2 | A9 | A12 | B1 | B2 | TR |
|---|---:|---:|---:|---:|---:|---:|---:|
| **A0** | — | 1.165 | 1.323 | 1.369 | 1.423 | 1.404 | 1.717 |
| **A2** | 1.146 | — | 1.310 | 1.353 | 1.411 | 1.396 | 1.676 |
| **A9** | 1.160 | 1.167 | — | 1.204 | 1.352 | 1.340 | 1.481 |
| **A12** | 1.161 | 1.168 | 1.170 | — | 1.326 | 1.313 | 1.461 |
| **B1** | 1.436 | 1.436 | 1.573 | 1.622 | — | 1.067 | 2.194 |
| **B2** | 1.442 | 1.441 | 1.587 | 1.636 | 1.098 | — | 2.252 |
| **TR** | 1.239 | 1.253 | 1.323 | 1.385 | 1.492 | 1.460 | — |

**out95 (1..9)**:

| query ↓ \ pool → | A0 | A2 | A9 | A12 | B1 | B2 | TR |
|---|---:|---:|---:|---:|---:|---:|---:|
| **A0** | — | 0.093 | 0.230 | 0.306 | 0.288 | 0.276 | 0.475 |
| **A2** | 0.079 | — | 0.201 | 0.274 | 0.281 | 0.271 | 0.459 |
| **A9** | 0.054 | 0.054 | — | 0.132 | 0.231 | 0.231 | 0.347 |
| **A12** | 0.051 | 0.048 | 0.078 | — | 0.203 | 0.204 | 0.331 |
| **B1** | 0.350 | 0.348 | 0.472 | 0.509 | — | 0.078 | 0.657 |
| **B2** | 0.355 | 0.355 | 0.485 | 0.524 | 0.087 | — | 0.666 |
| **TR** | 0.186 | 0.193 | 0.267 | 0.311 | 0.314 | 0.299 | — |

**Which block carries the difference** (share of squared full-space 1-NN distance, and block-only R), for representative pairs [V]:

| query→pool | access | snr | theta | loads | block-only R snr | theta | loads |
|---|---:|---:|---:|---:|---:|---:|---:|
| A0→A2 (within C1) | 0.018 | 0.369 | 0.211 | 0.402 | 1.09 | 1.26 | 4.22 |
| A9→A12 (within C2) | 0.023 | 0.337 | 0.197 | 0.443 | 1.09 | 1.19 | 4.13 |
| B1→B2 (within C3) | 0.008 | 0.453 | 0.258 | 0.281 | 1.01 | 1.16 | 4.65 |
| A2→A9 (C1→C2) | 0.019 | 0.344 | 0.208 | 0.428 | 1.18 | 1.35 | 4.75 |
| A0→A12 (C1→C2) | 0.021 | 0.334 | 0.200 | 0.445 | 1.20 | 1.31 | 4.94 |
| A9→A2 (C2→C1) | 0.024 | 0.368 | 0.216 | 0.393 | 1.11 | 1.27 | 4.12 |
| B1→A2 (C3→C1) | 0.057 | 0.348 | 0.204 | 0.391 | 1.23 | 1.28 | 5.42 |
| A2→B1 (C1→C3) | 0.050 | 0.399 | 0.218 | 0.333 | 1.24 | 1.30 | **11.49** |
| B1→TR (C3→learner) | 0.113 | 0.272 | 0.178 | 0.437 | 1.31 | 1.32 | 8.75 |

Every pair of the 42 is in `raw/screens.out`.

**What the tables say:**
- **C3's states are distinct from everything, in both directions.** C3 queried into C1 or C2 pools gives R 1.44–1.64 and out95 0.35–0.52. C1 or C2 queried into C3 pools gives R 1.31–1.42 and out95 0.20–0.29. Into the learner's pool, C3 gives R 2.19–2.25 and out95 0.66–0.67. The within-C3 reference is R 1.07–1.10, out95 0.08–0.09.
  - When A-states are queried into B pools, the **loads** block alone has R 10–12. Consolidated populations have a tightly clustered loads block that A-policy states fall far outside.
- **C1 → C2 is out and C2 → C1 is in.** C1 states queried into C2 pools give R 1.31–1.37 and out95 0.20–0.31. C2 states queried into C1 pools give R 1.16–1.17 and out95 0.05. That is the same R as C1's own sibling (1.15–1.17), and out95 sits at the level a pool gets against itself.
  - Along the margin axis the pattern is monotone: states of the higher-margin rule lie inside the lower-margin rule's distribution.
  - No block isolates C1 from C2. The loads block-only R across the catfish (4.1–5.0) overlaps the within-catfish values (3.8–4.4).
- **The learner's states vs the sources.** Source states queried into the learner's pool give R 1.46–2.25 and out95 0.33–0.67. Learner states queried into source pools give R 1.24–1.49. Every source hands the learner states outside its own distribution, consistent with FEASFRONT's JSRL result.

---

## 4. Margin scale (input to a later large-margin loss)

**Quantities** [V], on each source's own states (24,000 each; every state has ≥ 2 legal actions):
- **sdQ:** the population sd, across legal actions, of the trained checkpoint's scalarized Q (`0.5·Q1 + 0.3·Q2 + 0.2·Q3`, the composition `select_actions` uses).
- **agree:** the learner's greedy action equals the source's action.
- **mE:** `Q(a_src) − max_{a≠a_src} Q(a)`.
- **"fires at l":** the fraction of states where a DQfD-style margin term `max_a[Q(a) + l·1(a≠a_src)] − Q(a_src)` is non-zero, with `l = c·sdQ(state)`.

| states | sdQ median | sdQ p10–p90 | **learner already picks source action** | mE median | mE / sd median | fires, c = 0 | c = 0.25 | c = 0.5 | c = 1 | per-head argmax agrees: Q1 | Q2 | Q3 | per-head sd median: Q1 | Q2 | Q3 |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A0 (C1) | 0.156 | 0.122–0.206 | **0.254** | −0.109 | −0.75 | 0.746 | 0.792 | 0.835 | 0.895 | 0.216 | 0.211 | 0.025 | 0.264 | 0.288 | 0.105 |
| A2 (C1) | 0.155 | 0.122–0.206 | **0.363** | −0.066 | −0.47 | 0.637 | 0.691 | 0.743 | 0.843 | 0.218 | 0.335 | 0.035 | 0.263 | 0.288 | 0.105 |
| A9 (C2) | 0.155 | 0.124–0.206 | **0.640** | +0.069 | +0.46 | 0.360 | 0.431 | 0.517 | 0.706 | 0.225 | 0.647 | 0.080 | 0.263 | 0.276 | 0.102 |
| A12 (C2) | 0.156 | 0.125–0.206 | **0.663** | +0.077 | +0.50 | 0.337 | 0.413 | 0.499 | 0.690 | 0.222 | 0.698 | 0.092 | 0.264 | 0.270 | 0.100 |
| B1 (C3) | 0.144 | 0.114–0.187 | **0.224** | −0.113 | −0.83 | 0.776 | 0.838 | 0.886 | 0.944 | 0.084 | 0.497 | **0.027** | 0.259 | 0.236 | 0.101 |
| B2 (C3) | 0.144 | 0.114–0.187 | **0.165** | −0.143 | −1.06 | 0.835 | 0.891 | 0.933 | 0.975 | 0.072 | 0.437 | **0.020** | 0.258 | 0.238 | 0.101 |
| TR (control) | 0.155 | 0.127–0.199 | 1.000 | +0.081 | +0.53 | 0.000 | 0.259 | 0.474 | 0.759 | 0.363 | 0.627 | 0.069 | 0.262 | 0.270 | 0.106 |

- **Scale.** The per-state scalarized-Q sd is about 0.14–0.16, with p10–p90 0.11–0.21. It is nearly the same on every source's states.
- **No source's agreement is near 1.** C2 is highest at 0.64–0.66. An agreement-gated margin loss would fire on 34–36% of C2 states at `l = 0` and on 50–52% at `l = 0.5·sd`. It would **not** "almost never fire" for any source. On C1 and C3 states it fires on 64–84% at `l = 0`.
- **The old heads versus the three catfish** [V numbers; I reading]:
  - The trained **Q3** (load-balance, `r3 = −U_b`) argmax agrees with C3's action on only **2.0–2.7%** of C3 states, below the ~3.8% chance level. The old load-balance head is anti-aligned with consolidation. A C3 catfish needs the plan's redefined energy head; it cannot sit on the trained Q3.
  - The trained **Q1** argmax agrees with `MAX_NOMINAL_GAIN` on only 21.6% of its states, so the old Q1 does not encode the gain argmax either.
  - The trained **Q2** (handover) agrees with C2 on 0.65–0.70.

---

## 5. Is the C1 / C2 split real?

**By actions, yes, but it is one rule at two thresholds.** [V, D]
- On the same states, C1 and C2 disagree on 35–55% of decisions (49–78% of contested ones). That is about 4× their within-pair disagreement (C1 0.12, C2 0.09).
- That disagreement is **exactly** the mass of the gain-gap band between their margins: roughly the (2, 9] dB band, 33–36% of decisions. Tables 1b and 4 add two more facts:
  - both are about equally easy for the learner's architecture to represent (0.81–0.84 vs 0.92–0.94);
  - they pull the learner in opposite directions: the learner already agrees with C2 on 64–66% but with C1 on only 25–36%.
- **On a contested state, a C1 target and a C2 target are usually different actions.** Attached to different heads (Q_B vs Q_H), they teach conflicting actions on a third or more of all states. The design would have to accept that by construction.

**By states, no. C2 adds no coverage that C1 lacks.** [V] C2's states sit inside C1's distribution (R 1.16–1.17, out95 0.05), no further out than C1's own sibling. C1's states are partly outside C2's (out95 0.20–0.31). With respect to coverage, C2 is nested in C1.

**By information set, the claimed split is weaker than HARVEST states.** [V, from `frontier.py:pick`] HARVEST assigns C-gain "block 2 only". But `A m=2dB` is a hysteresis rule: it reads the incumbent from block 1 exactly as `A m=9/12dB` do. Only `MAX_NOMINAL_GAIN` is memoryless. As listed, C1's own two members already differ by the incumbent-memory bit, and their disagreement (0.12) is that bit at a 2 dB threshold.

**Reading:** C1 and C2 are **two action targets from one hysteresis family** (threshold ≈ 0–2 dB vs 9–12 dB). They are not two state regions and, for `A m=2dB`, not two information sets.
- **If the plan needs two catfish there, the justification is the endpoint:** C1 is the EE-maximising end, C2 is the handover-cap end, and they disagree on the same states.
- **If it needs distinct experience coverage, there is one** (C1, whose states contain C2's).
- Which counts is the design's call. The numbers above are what it would read.

---

## Verdicts per catfish

| catfish | representable from the learner's observation | distinct from the other two (actions) | distinct (states) | what could make it useless as a catfish |
|---|---|---|---|---|
| **C1 (C-gain)**: `MAX_NOMINAL_GAIN`, `A m=2dB` | **Partly.** Information exact (24,000/24,000). Probe top-1 **0.812 / 0.838**, 4–6 points below the positive control (0.877). For `A m=2dB` it is **below the trivial always-max-gain baseline (0.876)**: the Q-architecture learns the 28-slot gain argmax poorly at this data scale. Errors are near-ties (mean 0.24 dB), so the closed-loop probe keeps the operating point (EE −0.9% / −1.3%, ≤ 1.0 sem; ho −0.01). | Yes. vs C2 0.35–0.55, vs C3 0.45–0.64 (within-pair 0.12) | Yes vs C3 (both directions). vs C2 only outward: C1 reaches states C2 does not (out95 0.20–0.31), and C2's states lie inside C1's. | The learner agrees with it on only 25–36% of states, so it has plenty to teach. As listed it is not "gain-only": `A m=2dB` uses the incumbent. `MAX_NOMINAL_GAIN` violates the declared cap C-H (φ2 0.6546 > 0.6016, FEASFRONT); `A m=2dB` is feasible (0.5497). Teaching an argmax over 28 continuous slots is where the learner's architecture is weakest. |
| **C2 (C-hold)**: `A m=9dB`, `A m=12dB` | **Yes.** Probe top-1 **0.920 / 0.935**, above the positive control and well above always-incumbent (0.748 / 0.814), including on contested decisions (0.905 / 0.935). Regret 0.12–0.16 dB. Closed loop: `A m=12dB` EE +0.3% (0.2 sem); `A m=9dB` EE −1.8% (−1.4 sem) and hands over 0.018 less (−4.4 sem). | Yes. vs C1 0.35–0.55, vs C3 0.44–0.72 (within-pair 0.09) | vs C3 yes. **vs C1 no**: its states lie inside C1's distribution (R 1.16–1.17, out95 0.05). | It is the source the learner already agrees with most (64–66%), so a margin loss fires on only about a third of its states at `l = 0`. It adds no coverage beyond C1. Its value is action targets on contested states, and those targets conflict with C1's. |
| **C3 (C-consolidate)**: `B1_NO_NEW_BEAM`, `B2_PREFER_SHARED` | **Partly.** Information exact (24,000/24,000). Probe top-1 **0.714 / 0.683**, the lowest, 16–19 points below the positive control and only 6–9 points above always-incumbent. 7–10% of predictions light a beam the rule would not. **Closed loop, the probe reproduces about 70% of the consolidation**: beams 47.3 / 45.5 vs the rule's 37.9 (learner 67.9); EE −4.3% / −4.9% vs the rule (−7.5 / −5.6 sem). | Yes, the most distinct: vs C1 0.45–0.64, vs C2 0.44–0.72, vs learner 0.73–0.84. The two members are nearly one rule (0.05). | **Yes, both directions and the most distinct**: R 1.31–1.64 vs A pools, 2.19–2.25 vs the learner's; the loads block carries it (block-only R 10–12). | The consolidation is the part the probe misses. The rule's benefit comes from the beam count, and each off-set error lights a beam. The trained Q3 head is anti-aligned with it (argmax agreement 2.0–2.7%, below chance), so it needs the redefined energy head. B1 and B2 are effectively one source. |

**The learner itself** (for reference): its states are distinct from every source's. Every source hands it states outside its own distribution (R 1.46–2.25). This is consistent with FEASFRONT's JSRL finding and extends it from `MAX_NOMINAL_GAIN` to all six rules.

---

## Verified vs inferred

**Verified by running code this session, read-only, no gradient step on any Q-network:**
- the 7 collection cells, bit-identical to `frontier.out` on every EE and handover column;
- all self-checks listed in §0;
- the information-ceiling reconstruction (6 × 24,000);
- the probe fits: 8 targets × 3 folds × {raw, z, raw-400};
- the 7 closed-loop probe rollouts;
- the D matrix and the exact band identity;
- the 42-pair coverage table with per-block breakdown;
- the margin table, with per-head Q recomputed and checked to 1.8e-7;
- the fact that only episode 0 is paired across cells.

**Inferred:**
- the mechanism behind the episode divergence (action-dependent `env_rng` consumption shifting the next start epoch);
- the attribution of the scalar drift to commit `c00aca3e`;
- that the FEASFRONT JSRL theta non-identity is mostly the episode divergence;
- that the probe shortfall on the argmax rules is a function-class/data limit, which the 400-epoch plateau and the 100% information ceiling support but do not prove;
- every design reading in §5 and in the verdicts.

**Not measured:**
- probes with more data than 24 episodes;
- any architecture other than the learner's;
- paired statistics (the cells are unpaired after episode 0);
- robustness to other seeds, user counts or physics;
- anything about training with these catfish.

## Files (all in `.scratch/catfish-screens/`)

- `scripts/collect.py`, `bc_probe.py`, `bc_rollout.py`, `screens.py`, `obs_reconstruct.py`, and `c3s_physics_override.py` (a byte-identical copy).
- `raw/{A0,A2,A9,A12,B1,B2,TR}.{npz,json}`: logged states, masks, actions, cross-queries and Q (about 12.5 MB each).
- `raw/bc_*`: probe predictions, logits and fold models.
- `raw/bcroll_*_raw.json`: closed-loop outputs.
- `raw/screens.out` / `screens.json`: every table, including all 42 coverage pairs.
- `raw/obs_reconstruct.out`.
- `raw/*.out`: raw logs.
- `PROGRESS.md`.
- Total `raw/` size is about 145 MB.
