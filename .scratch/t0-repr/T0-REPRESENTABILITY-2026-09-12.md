**T0 = LP-prev(c=1, m=0) is ADMITTED by the representability screen (Amendment 3 §3: R_repr ≥ 0.5 for at least one clone on both sets): closed-loop R_repr of the declared clones — the learner's DQNNetwork(113→100→50→50→28, tanh) on the ratio learner's own observation, trained on 180 training-like episodes held out by episode — is 0.930 (one-hot BC) and 0.976 (soft distillation, τ = 3 chosen on VAL) on the 24 evaluation episodes, and 0.952 (BC) and 1.052 (soft) on the 24 calibration episodes (pooled Σbits/ΣJ, reference `A m=2dB`, greedy, fresh env per episode, pinned archive 427e6a91, sat; both episode sets reported separately, never compared), so both clones pass on both sets.**

# T0 representability screen — LP-prev(c=1, m=0) cloned onto the ratio learner's observation

Date 2026-09-12 (Taipei) / 2026-09-11 17:32–18:35 UTC. Measurement only: **no learner training, no `update()`, no gradient
step on any MODQN network, no optimizer on the learner, no trained checkpoint loaded.** The two clones are measurement
instruments in the sense of CFSCREEN §1b–1c, not the learner. Task: Amendment 3 §2–§3 (what T0 is, `R_repr`) and
Amendment 5 Part I §I.4 (this lane). Evidence tags: **[V]** = I ran it this session; **[D]** = arithmetic on [V] numbers.

```
PROVENANCE [A] (every number in this report unless tagged otherwise)
- physics / harness (C):   MODQN-harness ; MDP modifiers: cap UNKNOWN (not stated for this pilot), segment anchor
                           UNKNOWN (not stated), interruption UNKNOWN (not stated), users 100 — the same env
                           construction as the LP probe and the CF3 pilot (`cf_ratio.make_env_on`, 10 steps/episode)
- estimand (C):            pooled ratio-of-sums (Σbits/ΣJ, divided once), full-buffer
                           + numerator: full-buffer Shannon, no demand cap
                           + scoring horizon: n.a. (not a V0.25 a-r0 panel quantity)
                           + R_repr = (EE(clone) − EE(A m=2dB)) / (EE(T0) − EE(A m=2dB)), all three pooled EEs on the
                           SAME episode set, from rollouts run by this report's own code
                           + accumulation: plain left-to-right float sums, divided once (lp_common's loop, copied
                           statement for statement; NOT Python's compensated `sum`)
- power accounting (C):    consumed, per-beam max over served users (MODQN default)
- host + TLE archive (C):  sat ; archive = pinned 427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9
                           (asserted in EVERY process before it runs) ;
                           placebo arms + their values on this run: T0 = LP-prev(1,0) = 114,129,570.58605178 bit/J
                           (evaluation) and 117,528,214.54845703 (calibration); `A m=2dB` = C1_A_m2dB =
                           107,000,983.53410847 and 112,195,917.53568056 — all four bit-identical, on all 15 compared
                           fields, to the LP probe's result JSONs (`.scratch/h4-probe/results-lp/`)
- evaluation construction (C): fresh env per episode (per-episode reseeding) ; two episode sets, never compared with
                           each other: EVALUATION env 9,111,000+i / mobility 9,112,000+i, i = 0..23 ; CALIBRATION
                           env 9,121,000+i / mobility 9,122,000+i, i = 0..23 ; greedy ε = 0, masked argmax, first
                           index on ties, no generator consumed by any policy ;
                           clone training data: 3 training triples (42,1337,7), (43,1338,8), (44,1339,9) × 100
                           episodes on the pilot trainer's own episode schedule (§3)
- tree / commit / flags:   mcrl-leo-handover-cf3, commit 102b2d4d (staged `src scripts tests` +
                           `artifacts/PREREG-FROZEN-2026-08-25-R2.json` sha256 8bf13e28…4543) ; the ratio learner's
                           TrainerConfig (`cf3_common.pilot_config(record, "A1", 1000)`) is used ONLY for the
                           observation encoding (log1p SNR, raw-radian θ, loads ÷ users) and the network shape
                           (100, 50, 50) tanh ; bootstrap / D-2 / D-3 / cap flags are training-time settings and are
                           not exercised here (nothing is trained on the learner side)
- policy / checkpoint:     teacher T0 = LP-prev(c = 1, m = 0): score(a) = log2(1 + max(γ_a, 0)) − 1·[N_a == 0] on the
                           RAW user state (γ = `channel_quality`, N = previous-step `beam_loads`), masked argmax ;
                           reference = `A m=2dB` = `cf_sources.cf3_policies()["C1_A_m2dB"]` ; clones = DQNNetwork
                           (113 → 100 → 50 → 50 → 28, tanh) fitted by this report (model sha256 in §8) ; NO trained
                           MODQN checkpoint is loaded anywhere ; selection rule: the declared clones are the
                           100-epoch fits, epoch and τ chosen on VAL only (§4)
- n:                       24 episodes per set per arm (7 arms per set: T0, `A m=2dB`, decoder control, 4 clones) ;
                           training-like collection 300 episodes / 300,000 decisions ; 0 training seeds (nothing is
                           trained on the learner side) ; sem type: paired per-episode (n = 24; the two sets are
                           paired arm-to-arm by construction — same start epoch, population and t = 0 observation)
                           plus a 10,000-resample episode-cluster bootstrap for R_repr
- in-sample?:              no — the clones' TRAIN / VAL / TEST episodes are disjoint from the evaluation and the
                           calibration sets (0 shared start epochs, 0 shared (epoch, t=0 observation) keys) and from
                           the Amendment 3 source-pool seeds ; epoch and τ were selected on VAL only, never on TEST,
                           never on either closed-loop set
- status of this report:   SCREEN (Amendment 3 §3 representability screen; a diagnostic instrument, not a success
                           gate — the success gate is beating baseline MODQN) ; supersedes: the VERDICT-ONLY version
                           of this same file written 2026-09-11 18:09 UTC
```

## 1. Verdict

`R_repr ≥ 0.5` for **both** declared clones on **both** episode sets, so T0 is admitted under Amendment 3 §3. [V/D]

| episode set | arm | pooled EE (bit/J) | served | **R_repr** | R_repr bootstrap 95 % | share of resamples ≥ 0.5 |
|---|---|---:|---:|---:|---|---:|
| EVALUATION | BC (one-hot) | 113,632,227.01 | 0.99862 | **0.9302** | 0.839 – 1.031 | 100 % |
| EVALUATION | SOFT τ = 3 | 113,960,161.83 | 0.99858 | **0.9762** | 0.896 – 1.063 | 100 % |
| CALIBRATION | BC (one-hot) | 117,272,460.05 | 0.99792 | **0.9520** | 0.835 – 1.074 | 100 % |
| CALIBRATION | SOFT τ = 3 | 117,807,343.84 | 0.99817 | **1.0523** | 0.972 – 1.138 | 100 % |

The two sets are separate measurements and are never compared with each other. The bootstrap (10,000 resamples of the
24 episodes, same indices for clone, teacher and reference, seed 20260912) is supplementary; the declared metric is the
pooled point estimate. `R_repr` > 1 on the calibration set means the soft clone's pooled EE there is above T0's own
(+0.216 ± 0.200 % paired, 16/24 episodes) — a small overshoot inside episode noise, not a claim that a clone beats its
teacher.

**Sensitivity (400 epochs) does not change the verdict.** Declared at 18:00 UTC — after seeing that the declared fits'
VAL-selected epoch sat at 93–98 of the 100-epoch budget (possible under-training, which biases `R_repr` low), and
**before any closed-loop run** — the same two clones were refit with 400 epochs (τ kept at 3, not re-selected). Their
`R_repr` is 0.890 / 0.946 (evaluation, BC / soft) and 0.947 / 0.984 (calibration): every value is far above 0.5, so the
admission is the same. Longer training raised open-loop fidelity (BC TEST top-1 0.8929 → 0.9063; soft 0.9448 → 0.9697)
but did **not** raise closed-loop EE — the four `R_repr` values moved by −0.040, −0.030, −0.005 and −0.068. The verdict
stays read on the declared 100-epoch clones (§1 table).

## 2. Placebo (the gate: nothing below counts until this passes) [V]

Run before anything else, on each episode set, with the same instrumented loop the clones use.

| check | evaluation | calibration |
|---|---|---|
| my T0 rollout vs LP probe `LP-prev-<set>-c1-m0.json` — 15 fields (ee, bits, joules, served, h_inter, h_intra, beams, ee_ep[24], rate mean/p10/min, served_user_steps, user_steps, n_episodes, ho/user-min) | **all 15 bit-identical**, ee 114,129,570.58605178 | **all 15 bit-identical**, ee 117,528,214.54845703 |
| `A m=2dB` re-rolled through the same loop vs `REF-C1_A_m2dB-<set>.json` (the R_repr reference) | **all 15 bit-identical**, ee 107,000,983.53410847 | **all 15 bit-identical**, ee 112,195,917.53568056 |
| my T0 action vs `lp_common.lp_prev_rule_factory(1, 0)` on every decision | 24,000 / 24,000 equal | 24,000 / 24,000 equal |
| T0 recomputed from the student's observation alone (decoder, §6) vs T0's action | 24,000 / 24,000 equal | 24,000 / 24,000 equal |
| decoder-from-observation POLICY rolled through the clone code path vs my T0 rollout | identical on the 15 fields **and** on every episode's bits, joules, start epoch and t = 0 hash | identical, same scope |
| observation decode: loads exact; remaining-steps feature exact; max relative SINR decode error | exact; exact; 2.427e-7 | exact; exact; 2.425e-7 |
| empty legal masks | 0 | 0 |

Walls: 45.3 / 41.3 / 37.4 s (evaluation: T0, reference, decoder) and 48.1 / 43.4 / 38.3 s (calibration).

**One finding from the first placebo round, fixed before the counted run.** The first run reported 14 of 15 fields
identical for `A m=2dB` on the evaluation set; the mismatch was `ho_per_user_min` in the last ulp (mine
1.2184175531914891 vs 1.2184175531914894). Cause [V]: that field is a derived display quantity, and `lp_grid.py`
derives it with the literal `DT_S = 30.08` while my first version used `cf_ratio.DT_S = DECISION_STEP_S =
30.080000000000002` (substeps × measurement step). Recomputing the target's `h_inter`/`h_intra` with 30.08 reproduces
the target exactly. Bits and joules use `cfr.DT_S` in both codes and were identical throughout, so no measured
quantity was affected. The derivation was aligned with `lp_grid` and both sets were re-run from scratch; the first
round is kept as evidence (`results/PLACEBO-evaluation.v1-hoderiv.json`, `results/PLACEBO-calibration.v1.json`).

## 3. The training-like episodes and the seed rule [V]

**Seed rule (recorded before collection).** For each training triple j ∈ {(42,1337,7), (43,1338,8), (44,1339,9)} the
episodes are drawn exactly as the pilot trainer draws them: one carried generator pair `env_rng = default_rng(env_seed)`,
`mobility_rng = default_rng(mobility_seed)` (`modqn.py:132-133`), `env.reset(env_rng, mobility_rng)` at every episode and
`env.step(actions, env_rng)` at every step (`cf_ratio.py:720,732`), with **T0 as the behaviour policy**. Each episode runs
on a **fresh env object**, and the env's only cross-episode state — the warm-start age stream `_age_rng` — is carried from
the previous episode's env through the env's own resume seam (`training_state_dict` / `load_training_state_dict`), the
path the trainer's own resume uses. The `train` seed (42/43/44) seeds only the learner's generators (ε-greedy, replay,
init) and is not consumed by T0: recorded, unused.

- **Seed-rule check** (first 3 episodes of triple 0, both ways): single carried env ≡ fresh env + carried age state on
  start epoch, t = 0 observation hash, per-step action hash, bits, joules, served, h_inter, h_intra — identical for all
  3 episodes. Negative control (fresh env **without** the carried age state) differs from episode 1 on, so the carry is
  load-bearing and the fresh-env construction is not silently a different schedule.
- **Scope limit [D]:** episode 0 of each triple is the pilot's own training episode 0; from episode 1 on the stream
  position depends on the actions taken (the fading draw count is action-dependent), so these are *training-like*
  episodes drawn from the same generator with the same seeds under T0's behaviour — not the learner's own episodes.
- **Collected:** 300 episodes (100 per triple), **300,000 decisions**, 0 empty masks, mean legal-set size 26.3, T0's
  action legal on every row; 300 distinct start epochs. Walls 192 / 169 / 167 s.
- **Disjointness [V]:** 0 episodes share a start epoch with the evaluation set and 0 with the calibration set (and
  therefore 0 share (epoch, t = 0 observation)); the seed values are disjoint from the evaluation (9,111,000+i /
  9,112,000+i), calibration (9,121,000+i / 9,122,000+i) and Amendment 3 pool (9,141,000+1000k+i / 9,161,000+1000k+i)
  seeds.
- Per decision the collection stores the **113-dim observation** (the 112-dim MODQN encoding + `(T − t)/T`, exactly
  `cf_ratio.encode_with_time`), the legal mask, T0's action, **T0's 28-slot score vector** (float64, every slot) and
  `MAX_NOMINAL_GAIN`'s action (to mark price-active decisions).
- Descriptive only, on its own episode set (never compared with the evaluation or calibration sets): T0's pooled EE on
  the collected episodes is 117,812,417.08 / 116,655,602.82 / 117,084,038.97 bit/J for triples 0 / 1 / 2.

## 4. The two clones (measurement instruments) [V]

Architecture and recipe, identical for every clone and fixed before any fit: `DQNNetwork(113 → 100 → 50 → 50 → 28,
tanh)` — the learner's own Q-network class with the pilot config's hidden layers and activation — on the raw 113-dim
observation (no z-scoring), illegal logits set to −1e9 (masked softmax), Adam lr 1e-3, batch 256, 100 epochs, torch
seed 1000 for init and shuffling. Split **by episode**: episode k of each triple is TEST if k % 5 == 4, VAL if
k % 5 == 3, TRAIN otherwise → 180 / 60 / 60 episodes = 180,000 / 60,000 / 60,000 decisions.

- **BC**: cross-entropy on T0's action. **SOFT**: cross-entropy toward `softmax(T0 score / τ)` over the legal actions.
- **Epoch selection (VAL only)**: min mean T0-score regret (`score_T0[a_T0] − score_T0[a_clone]`, T0's own score units);
  tie → max VAL top-1 → earliest epoch. Action accuracy alone is not the criterion (Amendment 3 §3).
- **τ selection (VAL only, written into PROGRESS.md before any closed-loop run)**: same criterion at each τ's selected
  epoch. Declared grid {0.01, 0.03, 0.1, 0.3, 1, 3}:

| τ | selected epoch | VAL mean T0-score regret | VAL top-1 | VAL top-3 |
|---|---:|---:|---:|---:|
| 0.01 | 96 | 0.017706 | 0.8970 | 0.9933 |
| 0.03 | 93 | 0.015245 | 0.9046 | 0.9952 |
| 0.1 | 93 | 0.010250 | 0.9188 | 0.9969 |
| 0.3 | 98 | 0.006252 | 0.9375 | 0.9985 |
| 1 | 96 | 0.006671 | 0.9293 | 0.9984 |
| **3 (selected)** | 93 | **0.004101** | 0.9458 | 0.9991 |

τ = 3 is the **upper edge of the declared grid**; the grid was not extended after seeing this (the declared rule was
applied as written). The trend 0.01 → 3 is monotone apart from τ = 1, so the soft target's usefulness here is mostly
that it carries T0's ranking of *all* legal actions, not only its argmax. BC's own fit: epoch 96, VAL regret 0.019689,
VAL top-1 0.8917. Each 100-epoch fit took ~55 s (peak RSS ~1.4 GB); each 400-epoch fit 213–220 s.

## 5. Held-out accuracy (TEST split: 60 episodes, 60,000 decisions, never used for any selection) [V]

| clone | top-1 | top-3 | mean T0-score regret | regret p95 | decisions with regret > 0 | top-1 on price-active decisions (19.8 % of rows) | top-1 elsewhere | CE at T0's action (bits) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BC (declared) | 0.8929 | 0.9932 | 0.019935 | 0.1431 | 10.71 % | 0.7678 | 0.9237 | 0.4122 |
| SOFT τ=3 (declared) | 0.9448 | 0.9993 | 0.004220 | 0.008279 | 5.52 % | 0.8947 | 0.9572 | 3.2846 |
| BC 400 ep (sensitivity) | 0.9063 | 0.9938 | 0.017138 | 0.1034 | 9.38 % | 0.8145 | 0.9289 | 0.4030 |
| SOFT τ=3, 400 ep (sensitivity) | 0.9697 | 0.9999 | 0.001153 | 0.0 | 3.03 % | 0.9512 | 0.9743 | 3.2869 |

Chance top-1 on this data is 0.0385 (mean 1/|legal|). "Price-active" = decisions where T0's action differs from
`MAX_NOMINAL_GAIN`'s, i.e. where the lighting price actually moves the choice; that is where every clone's errors
concentrate [D]. The soft clone's CE is large because its masked softmax is deliberately τ-tempered (flat), not
because it predicts worse — its top-1 and regret are better than BC's; only BC's CE is a useful entropy bound (§6).

## 6. T0's conditional action entropy given the student's observation [V]

**H(a_T0 | observation, mask) = 0.** T0's action was recomputed from the 113-dim observation alone —
`score_hat(a) = obs_snr_block[a] / ln 2 − 1·[obs_load_block[a] == 0]` (the encoding stores `log1p(max(γ,0))` and
`loads / users`), masked argmax — and equals T0's logged action on **300,000 / 300,000** collected decisions (0
mismatches), and on 24,000 / 24,000 decisions on each closed-loop set (§2). A deterministic decoder therefore exists on
the whole sample, which pins the conditional entropy at exactly 0 and puts the *information* ceiling for the clones at
100 %: every shortfall below is a limit of the function class, the fitting recipe or the data, never missing
information. This is the same structure CFSCREEN §1a found for the six rules there.

The requested fine-binning estimate is reported for completeness and is **degenerate here, as expected** [V/D]: with
bins = identical float32 observation + mask, the 300,000 decisions fall in 300,000 distinct bins (0 % of decisions share
a bin), so the plug-in and Miller–Madow estimates are both 0 bits with no effective sample; a coarse binning (every
observation dimension rounded to 0.05 encoded units) also gives 300,000 bins and 0 bits. A continuous 113-dim
observation cannot be binned informatively at this sample size, which is why the exact decoder above is the operative
statement. Two scales for reading the zero: T0's marginal action entropy is 3.3168 bits and a uniform draw over the
legal set would be 4.7090 bits; a variational upper bound from a fitted model (BC's held-out cross-entropy) is 0.4122
bits.

## 7. Closed loop, all quantities, one table per episode set [V/D]

Greedy masked argmax (first index on ties), fresh env per episode, per-episode reseeding; every clone episode has the
same start epoch and t = 0 observation as T0's and the reference's on that set (checked per arm). `ho` = handovers per
user-minute; H_inter / H_intra are per user-step; rates are per served user.

### EVALUATION set (env 9,111,000+i / mobility 9,112,000+i, i = 0..23)

| arm | pooled EE (bit/J) | % vs `A m=2dB` | served | lit beams/step | bits / ref | joules / ref | H_inter | H_intra | ho /user-min | rate mean / p10 / min (Mbit/s) | p10 / ref | **R_repr** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| `A m=2dB` (reference) | 107,000,983.53 | 0.000 % | 0.99862 | 63.288 | 1.000 | 1.000 | 0.56163 | 0.04921 | 1.2184 | 431.12 / 101.40 / 4.763 | 1.000 | — |
| **T0** = LP-prev(1,0) (teacher) | 114,129,570.59 | +6.662 % | 0.99854 | 56.408 | 0.9540 | 0.8944 | 0.59054 | 0.05483 | 1.2873 | 411.32 / 102.98 / 5.054 | 1.016 | 1 (by definition) |
| **BC** (declared) | 113,632,227.01 | +6.197 % | 0.99862 | 57.279 | 0.9637 | 0.9075 | 0.59104 | 0.05454 | 1.2877 | 415.49 / 105.32 / 5.782 | 1.039 | **0.9302** |
| **SOFT τ=3** (declared) | 113,960,161.83 | +6.504 % | 0.99858 | 56.958 | 0.9612 | 0.9025 | 0.59454 | 0.05225 | 1.2901 | 414.43 / 103.72 / 6.677 | 1.023 | **0.9762** |
| BC 400 ep (sensitivity) | 113,347,194.44 | +5.931 % | 0.99862 | 57.171 | 0.9598 | 0.9061 | 0.59042 | 0.05408 | 1.2856 | 413.79 / 103.33 / 4.771 | 1.019 | 0.8902 |
| SOFT τ=3, 400 ep (sensitivity) | 113,745,213.60 | +6.303 % | 0.99854 | 56.508 | 0.9523 | 0.8958 | 0.58929 | 0.05404 | 1.2832 | 410.59 / 102.35 / 5.167 | 1.009 | 0.9461 |

Paired per-episode (n = 24, same episode starts): T0 vs reference +6.850 ± 0.649 % (24/24 episodes positive); BC vs T0
−0.392 ± 0.311 % (10/24), BC vs reference +6.423 ± 0.673 % (24/24); SOFT vs T0 −0.163 ± 0.281 % (10/24), SOFT vs
reference +6.666 ± 0.639 % (24/24); BC-400 vs T0 −0.695 ± 0.321 % (6/24); SOFT-400 vs T0 −0.347 ± 0.199 % (9/24).
On-policy agreement with T0 (T0 queried on the clone's own states): BC 0.8868 (0.7755 on price-active decisions,
mean on-policy T0-score regret 0.02156), SOFT 0.9421 (0.8851, 0.00460), BC-400 0.8968 (0.8030, 0.01929), SOFT-400
0.9691 (0.9460, 0.00131).

### CALIBRATION set (env 9,121,000+i / mobility 9,122,000+i, i = 0..23) — a separate measurement, never compared with the evaluation set

| arm | pooled EE (bit/J) | % vs `A m=2dB` | served | lit beams/step | bits / ref | joules / ref | H_inter | H_intra | ho /user-min | rate mean / p10 / min (Mbit/s) | p10 / ref | **R_repr** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| `A m=2dB` (reference) | 112,195,917.54 | 0.000 % | 0.99775 | 62.975 | 1.000 | 1.000 | 0.55138 | 0.03538 | 1.1704 | 450.57 / 111.39 / 2.168 | 1.000 | — |
| **T0** = LP-prev(1,0) (teacher) | 117,528,214.55 | +4.753 % | 0.99813 | 57.046 | 0.9524 | 0.9092 | 0.58950 | 0.04625 | 1.2681 | 428.96 / 107.85 / 6.980 | 0.968 | 1 (by definition) |
| **BC** (declared) | 117,272,460.05 | +4.525 % | 0.99792 | 57.846 | 0.9629 | 0.9213 | 0.58604 | 0.04492 | 1.2586 | 433.80 / 112.06 / 3.870 | 1.006 | **0.9520** |
| **SOFT τ=3** (declared) | 117,807,343.84 | +5.001 % | 0.99817 | 57.125 | 0.9559 | 0.9104 | 0.58596 | 0.04638 | 1.2613 | 430.53 / 107.92 / 10.806 | 0.969 | **1.0523** |
| BC 400 ep (sensitivity) | 117,244,392.45 | +4.500 % | 0.99767 | 57.592 | 0.9585 | 0.9172 | 0.58713 | 0.04658 | 1.2640 | 431.91 / 110.18 / 8.687 | 0.989 | 0.9468 |
| SOFT τ=3, 400 ep (sensitivity) | 117,442,888.08 | +4.677 % | 0.99796 | 56.917 | 0.9497 | 0.9073 | 0.58642 | 0.04529 | 1.2601 | 427.82 / 109.25 / 12.645 | 0.981 | 0.9840 |

Paired per-episode (n = 24): T0 vs reference +4.822 ± 0.406 % (24/24); BC vs T0 −0.240 ± 0.288 % (11/24), BC vs
reference +4.564 ± 0.442 % (23/24); SOFT vs T0 +0.216 ± 0.200 % (16/24), SOFT vs reference +5.042 ± 0.396 % (24/24);
BC-400 vs T0 −0.234 ± 0.248 % (9/24); SOFT-400 vs T0 −0.075 ± 0.187 % (12/24). On-policy agreement with T0: BC 0.8933
(price-active 0.7664, regret 0.01945), SOFT 0.9476 (0.9094, 0.00373), BC-400 0.9072 (0.8101, 0.01625), SOFT-400 0.9721
(0.9568, 0.00099).

**What the operating points say [D].** Both clones reproduce T0's lever — lit beams fall from the reference's 63.3 to
56.5–57.8 per step, joules to 0.90–0.92 ×, bits only to 0.95–0.96 × — and they do it without a service or rate tail:
served stays at 0.9977–0.9986 (reference 0.9977 / 0.9986) and the per-served-user p10 is 0.98–1.04 × the reference's
on both sets, so no clone is throughput-degenerate under the LP report's flag (p10 < 50 % of the reference's). The
handover rate tracks T0's (1.26–1.29 per user-minute against T0's 1.287 / 1.268). This matters for the reading:
an 89 % accurate clone keeps ~93 % of the teacher's EE gain because its errors sit on low-stakes decisions — its mean
on-policy T0-score regret is 0.02 in T0's own score units, about 2 % of one lighting price (c = 1).

## 8. Files, code and cost

All produced this session, on sat, in `/home/sat/mcrl-v025-t0-repr-ws/` (mine alone; the other agents' workspaces
`mcrl-v025-h4-probe-ws` and `mcrl-v025-ceiling-ws` were never touched). Everything below was copied back to
`.scratch/t0-repr/` with `tar` over ssh and **sha256 verified equal on both ends (55 files)**; `.scratch/validity-audit/`
and `.scratch/reviews/` were not read.

- **Scripts** (`.scratch/t0-repr/scripts/`, each does `sys.path.insert(0, "<tree>/src")` first): `t0_common.py`
  35c42ae6…8176 (T0, the 113-dim encoder, the rollout loop, the clone policy), `t0_placebo.py` e5f26602…4e72,
  `t0_collect.py` 6f2067ad…266e, `t0_clone.py` e0a18106…d432, `t0_select_tau.py` 1735e275…c192, `t0_closed.py`
  020ec384…d77f, `t0_entropy.py` bd9466cd…4092, `t0_aggregate.py` f6a05cdc…0350; launchers `run.sh` 20e91cf9…6d40
  (nice 16) and `run19.sh` 8c84876d…cf03 (nice 19).
- **Staged tree**: `git -C mcrl-leo-handover-cf3 archive 102b2d4d src scripts tests artifacts/PREREG-FROZEN-2026-08-25-R2.json`,
  tarball sha256 12c341e5…5cba (5,969,920 B, 437 .py), identical on both ends. The LP and BC-probe scripts were staged
  verbatim for reference and for the placebo's rule comparison: `lp_common.py` fc8d4f0b…4a27, `lp_grid.py` b3a011f5…ecc5,
  `bc_probe.py` cb80c4d7…e310f, `bc_rollout.py` 838c84bf…d4be.
- **Results** (`.scratch/t0-repr/results/`): `AGGREGATE.json` 8e9f58de…bb52 (the verdict's record, declared clones),
  `AGGREGATE-WITH-SENSITIVITY.json` 80f7c394…94a4 (adds the two 400-epoch clones; admission read on the declared ones),
  `PLACEBO-{evaluation,calibration}.json` 351c97a3…04cb / 6bef5a6c…dfa0 (+ the v1 round kept as evidence),
  `CLONE-{BC,SOFT-tau0.01,…,SOFT-tau3,BC-e400,SOFT-tau3-e400}.json`, `CLOSED-<clone>-<set>.json` ×8, `TAU-SELECTION.json`
  876930f5…0a32, `ENTROPY.json` 1e116ce6…d645. **Models** (`models/`, 84 KB each): `BC.pt` 3f4e4d69…58bb, `SOFT-tau3.pt`
  e7487196…b4f2, `BC-e400.pt` 1bb3cbcc…9173, `SOFT-tau3-e400.pt` d7b83ae7…2b88, plus the five other τ fits. **Logs**
  (`logs/`) and the collection metadata (`data/T0-collect-triple{0,1,2}.json`) are included.
- **Not copied back (over 20 MB, kept on sat with their hashes recorded here and in the metadata JSONs)**: the raw
  decision dumps `data/T0-collect-triple0.npz` 23cd918a…cee5, `triple1.npz` 515bc53e…f991, `triple2.npz` f419be02…4cc1
  (70 MB each: 300,000 × (113-dim observation, 28 mask, action, 28-slot score, max-gain action, indices)).
- **Cost**: 37 min wall to the verdict, ~60 min in total; at most 3 processes (2 after the resume), `nice -n 16` then
  `nice -n 19`, 1 BLAS thread and `torch.set_num_threads(1)` in every process, `systemd-run --user --scope -p
  MemoryMax=5G`, peak RSS ~2.2 GB (collection; the shared TleArchive parse cache grows ~14 MB per episode), all
  intermediates inside the workspace, never `/tmp`. Python 3.13.3, torch 2.13.0+cu130, numpy 2.5.2.

## 9. What this does and does not establish

1. **Establishes**: T0's policy is representable, in closed loop, by the learner's own function class on the learner's
   own observation — 93–98 % of T0's EE gain over `A m=2dB` on the evaluation set and 95–105 % on the calibration set,
   with service and rate tails intact. Under Amendment 3 §3 T0 is admitted as a teacher, and `R_repr` ≈ 0.93–1.05 is
   the number the later learner readings are measured against (`ρ / R_repr`, Amendment 3 §4).
2. **Establishes**: T0 carries no information the student lacks — the conditional entropy is exactly 0, so a teacher
   arm using T0 cannot be justified by information the student cannot see. Its value, if any, must come from the
   optimisation (what the learner does with the labels), not from privilege.
3. **Does not establish** anything about whether a learner will *reach* this ceiling, nor anything about the privileged
   teachers T_DR / T_SEQ / T_JOINT, whose own screens need the oracle cells. `R_repr` is a ceiling for the teacher's
   representability, not a claim about training.
4. **Does not compare** the two episode sets with each other, and carries no number from another host or archive: every
   figure here is sat, pinned archive 427e6a91, MODQN-harness, with the placebo rows above as the tie to the LP probe.
5. **Selection caveat**: τ = 3 sits at the upper edge of the declared grid, so a larger τ might clone T0 slightly
   better; the grid was declared before fitting and was not extended. The 400-epoch sensitivity shows open-loop fidelity
   keeps improving with training while closed-loop `R_repr` does not, so the remaining 2–7 % gap to T0 is not obviously
   a fitting-budget artefact.
