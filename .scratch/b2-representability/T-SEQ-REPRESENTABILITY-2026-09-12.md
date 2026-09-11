**`R_repr(T_SEQ)` = 0.150 (BC one-hot) and 0.129 (SOFT τ = 0.3) on the 24 evaluation episodes, and 0.092 (BC) and 0.051 (SOFT) on the 24 calibration episodes — every value far below the 0.5 admission line, with 0 of 10,000 bootstrap resamples reaching 0.5 on any arm; neither declared clone is throughput-degenerate (served 0.9966–0.9977 ≥ 0.995, bits ratio 0.951–0.979 ≥ 0.95, per-served-user p10 1.04–1.15 × the rule ≥ 0.5 ×), so the shortfall is a genuine representability shortfall and not a collapsed rate tail. Amendment 4 §2 condition 3 is therefore NOT met, and B2 is not entered.**

# T_SEQ representability screen — the rate-floored sequential oracle cloned onto the B2 student's observation

Date 2026-09-12 (Taipei) / 2026-09-11 20:15–21:00 UTC. Measurement only: **no learner training, no `update()`, no
gradient step on any MODQN network, no optimizer on the learner, no trained checkpoint loaded.** The clones are
measurement instruments in the sense of CFSCREEN §1b–1c and of the T0 screen, not the learner. Task: Amendment 4 §2
condition 3 (may B2 be entered?) with the `R_repr` metric of Amendment 3 §3. Evidence tags: **[V]** = I ran it this
session; **[D]** = arithmetic on [V] numbers; **[R]** = reported by another lane and re-derived by me here.

```
PROVENANCE [A] (every number in this report unless tagged otherwise)
- physics / harness (C):   MODQN-harness ; MDP modifiers: cap UNKNOWN (not stated for this pilot), segment anchor
                           UNKNOWN (not stated), interruption UNKNOWN (not stated), users 100 — the same env
                           construction as the oracle lane, the LP probe and the T0 screen
                           (`cf_ratio.make_env_on`, 10 steps/episode)
- estimand (C):            pooled ratio-of-sums (Σbits/ΣJ, divided once), full-buffer
                           + numerator: full-buffer Shannon, no demand cap
                           + scoring horizon: n.a. (not a V0.25 a-r0 panel quantity)
                           + R_repr = (EE(clone) − EE(A m=2dB)) / (EE(T_SEQ) − EE(A m=2dB)), all three pooled EEs
                             on the SAME episode set, the clone's from rollouts run by this report's own code
                           + accumulation: plain left-to-right float sums, divided once (lp_common's loop, copied
                             statement for statement; NOT Python's compensated `sum`)
- power accounting (C):    consumed, per-beam max over served users (MODQN default)
- host + TLE archive (C):  sat ; archive = pinned 427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9
                           (asserted in EVERY process before it runs) ;
                           placebo arms on this run: `A m=2dB` = 107,000,983.53410847 bit/J (evaluation) and
                           112,195,917.53568056 (calibration) — bit-identical on all 15 compared fields to the LP
                           probe's `REF-C1_A_m2dB-<set>.json`
- teacher (C):             T_SEQ = B-real-floor R1 = the rate-floored one-sequential-sweep realised-information
                           oracle of the h4-probe lane (`oracle_cells.py` kind "Bf", reference R1 = `A m=2dB`,
                           user order 0..99, rate floor: a move is disallowed if any user served under the
                           reference drops below 50 % of its reference rate at that step).  Its pooled EE was
                           RE-DERIVED here from the 24 per-episode cell JSONs of each set and its saved joint
                           actions were RE-COMMITTED through my own loop (§2)
- evaluation construction (C): fresh env per episode (per-episode reseeding) ; two episode sets, never compared
                           with each other: EVALUATION env 9,111,000+i / mobility 9,112,000+i, i = 0..23 ;
                           CALIBRATION env 9,121,000+i / mobility 9,122,000+i, i = 0..23 ; greedy ε = 0, masked
                           argmax, first index on ties, no generator consumed by any policy ;
                           clone training data: the 24 floored B-real R1 CALIBRATION cells (24,000 decisions),
                           split by episode into 15 TRAIN / 5 VAL / 4 TEST
- tree / commit / flags:   mcrl-leo-handover-cf3, commit 102b2d4d (staged `src scripts tests` +
                           `artifacts/PREREG-FROZEN-2026-08-25-R2.json`, tarball sha256 12c341e5…5cba, identical
                           on both ends and to the tree the T0 lane staged) ; the ratio learner's TrainerConfig
                           (`cf3_common.pilot_config(record, "A1", 1000)`) is used ONLY for the observation
                           encoding and the network shape (100, 50, 50) tanh ; nothing is trained on the learner side
- policy / checkpoint:     clones = DQNNetwork(141 → 100 → 50 → 50 → 28, tanh) fitted by this report (sha256 in §8) ;
                           NO trained MODQN checkpoint is loaded anywhere ; selection rule: the declared clones are
                           the 400-epoch fits, epoch and τ chosen on VAL only (§4)
- n:                       24 episodes per set per arm ; 24,000 teacher decisions (15,000 TRAIN / 5,000 VAL /
                           4,000 TEST) ; 0 training seeds (nothing is trained on the learner side) ; sem type:
                           paired per-episode (n = 24) plus a 10,000-resample episode-cluster bootstrap for R_repr
- in-sample?:              EVALUATION set — **no**: no evaluation episode contributed a single training row, a
                           single selection decision or a single hyper-parameter.  CALIBRATION set — **yes, by the
                           brief's construction**: the training corpus IS the calibration set, so its closed-loop
                           R_repr is in-sample (15 of its 24 episodes trained the clone, 5 selected the epoch and τ).
                           Both are reported; the two sets are never compared with each other.  The in-sample set
                           scores LOWER than the out-of-sample one, so this caveat cannot be rescuing the verdict.
- status of this report:   SCREEN (Amendment 4 §2 condition 3; a diagnostic instrument, not a success gate — the
                           success gate remains beating baseline MODQN) ; supersedes nothing
```

## 1. Verdict

**Condition 3 is NOT met.** No clone comes within a factor of three of the 0.5 line, on either episode set. [V/D]

| episode set | clone | pooled EE (bit/J) | % vs `A m=2dB` | **R_repr** | bootstrap 95 % | resamples ≥ 0.5 | degenerate? |
|---|---|---:|---:|---:|---|---:|---|
| EVALUATION | **BC (one-hot)** | 111,077,952.80 | +3.810 % | **0.1503** | 0.117 – 0.184 | **0 %** | no |
| EVALUATION | **SOFT τ = 0.3** | 110,503,257.07 | +3.273 % | **0.1291** | 0.104 – 0.155 | **0 %** | no |
| CALIBRATION | **BC (one-hot)** | 114,512,356.16 | +2.065 % | **0.0916** | 0.062 – 0.120 | **0 %** | no |
| CALIBRATION | **SOFT τ = 0.3** | 113,481,082.33 | +1.145 % | **0.0508** | 0.019 – 0.083 | **0 %** | no |

Read against the gap this screen exists to explain: the sequential oracle is +25.353 % over `A m=2dB` on the
evaluation set and the simultaneous one is +6.104 %, a **+19.25 pp** difference. A B2 student that could express
that difference would have to reach at least **+12.68 %** (half the sequential oracle's headroom). The best clone reaches
**+3.81 %** — less than the +6.66 % that the *simultaneous, observation-only* rule LP-prev(1,0) already gets under
the **unchanged** execution contract, and less than the T0 clones' +6.20 % / +6.50 % on the very same 24 episodes.
**Changing the execution contract to give the student earlier users' same-step choices buys nothing that the
existing contract does not already deliver.** [D]

Three further readings, each declared before it was run:

1. **The declared 28-slot context block is worth approximately zero.** Same teacher, same corpus, same recipe,
   with and without it: evaluation +0.0396 (BC) and −0.0108 (SOFT) in `R_repr`; calibration +0.0094 (BC) and
   −0.0378 (SOFT). Mean effect ≈ 0.0001, with both signs present. Open loop it moves held-out top-1 by +0.0015
   (BC) and −0.0035 (SOFT) and the held-out cross-entropy by 0.0079 bits per decision (§6).
2. **The reverse user order (controller addition) does not change the picture, because there is almost nothing to
   change.** Rolling the same clones on the same 24 evaluation episodes with order 99..0: `R_repr` 0.1262 (BC,
   from 0.1503) and 0.1185 (SOFT, from 0.1291). The clone keeps 84 % / 92 % of its (small) headroom, so what
   little value the current-step visibility has is **not** an artefact of the order the teacher was built with.
   Scope limit either way: the teacher itself was only ever measured in the forward order — the oracle lane left
   the reverse-order cell HELD — so this compares clone-vs-clone, not teacher-vs-teacher.
3. **The clones do not land in the teacher's operating regime at all** (§7). T_SEQ wins by lighting **more**
   beams (66.9 vs the rule's 63.3) and delivering **32 % more bits**; every clone instead lights **fewer** beams
   (58.8–60.9) and delivers **2–4 % fewer bits**, i.e. it reproduces the T0/LP lever (save joules) rather than
   the oracle's lever (buy bits). This is the physical form of the same finding.

## 2. Placebo (the gate: nothing below counts until this passes) [V]

| check | evaluation | calibration |
|---|---|---|
| `A m=2dB` re-rolled through my own loop vs the LP probe's `REF-C1_A_m2dB-<set>.json` — 15 fields (ee, bits, joules, served, h_inter, h_intra, beams, ee_ep[24], rate mean/p10/min, served_user_steps, user_steps, n_episodes, ho/user-min) | **all 15 bit-identical**, ee 107,000,983.53410847 | **all 15 bit-identical**, ee 112,195,917.53568056 |
| T_SEQ pooled Σbits/ΣJ re-derived by me from the 24 cell JSONs | **134,129,417.19** (= the oracle lane's number) | **137,497,201.09** (= the oracle lane's number) |
| teacher replay: the reference rule reproduces the stored `joint_ref` at every step | 20/20 steps (ep 0–1) | **240/240 steps (all 24 episodes)** |
| teacher replay: the re-encoded 113-dim observation vs the saved npz rows | 20/20 bit-identical | **240/240 bit-identical** |
| teacher replay: committed bits / joules vs the stored per-step values | max abs Δ **0.0 / 0.0** | max abs Δ **0.0 / 0.0** |
| empty legal masks / NO_OP actions in the corpus | 0 / 0 | 0 / 0 |

Walls: 37.4 s and 37.8 s for the two reference rollouts; ~7 min for the 26 teacher replays and the corpus build.
The replay is what everything below stands on: it proves that committing the oracle's saved joint actions in a
fresh env reproduces the oracle's own energy ledger bit for bit, so the context block I build from the env's slot
tables during that replay belongs to exactly the states the oracle decided in.

## 3. The B2 observation, declared before any fit (PROGRESS.md §S2/D1) [V]

```
obs_B2[u] = concat( enc113[u] , ctx28[u] )                                    141 dims, float32

enc113[u]  = cf_ratio.encode_with_time(...)[u]      the ratio learner's own observation, unchanged
ctx28[u,a] = ( # users v deciding BEFORE u in this step's order whose chosen action realises the SAME
               physical beam (norad_id, cell_id) as u's slot a ) / num_users ;  0 where u's slot a has
               no beam identity
```

`ctx28` is the current step's **partial, ungated per-beam demand** on user *u*'s 28 candidate slots, normalised
exactly as encoded block 4 normalises the *previous* step's demand — the brief's "one extra block of 28 counts,
normalised like the previous-step loads". "Already lit this step by an earlier-deciding user" is `ctx28 > 0` and
needs no separate block. Nothing else was added: no realised rates, no other user's SINR, no future information.

**One implementation point that a naïve encoding gets wrong.** The 28 action indices are **per-user slots**
(`a = 7·l + j` over *that user's* four satellite slots and seven cells), so the same index is a different physical
beam for different users; counting raw action indices across users would produce a meaningless block. Beam
identity is therefore taken from the environment's own slot tables (`_candidates.slot_tables[v].norad_ids/cell_ids`),
the same objects `step.py` uses to build `beam_loads`. A real sequential protocol delivers `ctx28` by broadcasting
the running per-beam count, which is exactly what this is.

Corpus statistics [V]: 17.92 % of the ctx entries are non-zero, max 0.09 (nine earlier users already on that beam),
mean row sum 0.0671.

## 4. Data, clones and selection (all fixed before any fit) [V]

- **Corpus**: the 24 floored B-real R1 **calibration** cells = **24,000 decisions**, out of the evaluation set by
  construction. `data/B2-train-calibration.npz` sha256 `ab8c9694…7cf3`. 0 empty masks, 0 NO_OP, mean legal-set
  26.21. The teacher **moves 54.87 %** of users off the reference action.
- **Split by episode** (the T0 rule): TEST if `i % 5 == 4` (episodes 4, 9, 14, 19), VAL if `i % 5 == 3`
  (3, 8, 13, 18, 23), TRAIN otherwise (15 episodes) → 15,000 / 5,000 / 4,000 decisions.
- **Architecture and recipe**, identical for every clone: `DQNNetwork(input → 100 → 50 → 50 → 28, tanh)` — the
  learner's own Q-network class with the pilot config's hidden layers and activation — raw inputs (no z-scoring),
  illegal logits → −1e9, Adam lr 1e-3, batch 256, **400 epochs**, torch seed 1000. *Declared deviation from T0's
  100 epochs*: TRAIN here is 15,000 rows, not 180,000, so 100 epochs would be 5,900 gradient steps against T0's
  70,400; 400 gives 23,600. Every VAL-selected epoch landed at 17–49, deep inside the budget, so **no fit is
  budget-limited** (the opposite of the T0 screen's situation).
- **Advantage normalisation**, declared as a formula and computed from TRAIN only:
  `adv_norm = adv / ref_bits(step)` (a dimensionless fraction of the step's reference throughput), then
  `adv_std = adv_norm / s` with `s` = the RMS of `adv_norm` over TRAIN's legal non-base slots = **0.014954477966**
  (377,665 slots). Mean |adv_std| = 0.7384. The declared τ grid {0.01, 0.03, 0.1, 0.3, 1, 3} then applies on the
  same scale the T0 screen used.
- **Soft-target support**: `softmax(adv_std/τ)` over legal **and allowed** slots (excluding those the oracle's own
  rate/service floor rejected). Declared reason: the teacher's rule is an argmax over legal-and-allowed with ties
  kept at the base, so a target with mass on disallowed slots would teach the student to break the rate floor the
  floored cell exists to enforce. The base slot is never disallowed, so the support is never empty.
- **τ selection (VAL only, written into PROGRESS.md before any closed-loop run)**: minimise mean teacher-advantage
  regret `adv_std[a_teacher] − adv_std[a_clone]` at each τ's VAL-selected epoch; tie → max VAL top-1 → smallest τ.

| τ | selected epoch | VAL mean advantage regret | VAL top-1 | VAL top-3 |
|---|---:|---:|---:|---:|
| 0.01 | 34 | 0.184764 | 0.3922 | 0.6864 |
| 0.03 | 34 | 0.181491 | 0.3926 | 0.6874 |
| 0.1 | 32 | 0.175837 | 0.3996 | 0.6940 |
| **0.3 (selected)** | 20 | **0.173581** | 0.3978 | 0.6854 |
| 1 | 28 | 0.189575 | 0.3954 | 0.6580 |
| 3 | 17 | 0.207160 | 0.3840 | 0.6454 |

τ = 0.3 is **interior** to the declared grid (the T0 screen's τ sat at the upper edge), so the grid did not bind.
BC's own fit: epoch 36, VAL regret 0.185040, VAL top-1 0.3940.

## 5. Held-out fidelity (TEST split: 4 episodes, 4,000 decisions, never used for any selection) [V]

| clone | input | top-1 | top-3 | mean adv regret | regret p95 | CE at the teacher's action (bits) | picks a floor-disallowed slot | top-1 where the teacher moved (55.9 %) | top-1 where it stayed |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **BC** (declared) | 141 | 0.3665 | 0.6615 | 0.2066 | 0.9354 | 2.9627 | 13.68 % | 0.0760 | 0.7347 |
| **SOFT τ=0.3** (declared) | 141 | 0.3807 | 0.6707 | 0.1974 | 0.8592 | 3.1532 | 10.95 % | 0.0747 | 0.7687 |
| BC-noctx (ablation) | 113 | 0.3650 | 0.6640 | 0.2180 | 0.9974 | 2.9706 | 12.90 % | 0.0742 | 0.7336 |
| SOFT-noctx (ablation) | 113 | 0.3842 | 0.6785 | 0.1955 | 0.8504 | 3.1389 | 10.47 % | 0.0693 | 0.7834 |
| **BC-ctxfull** (diagnostic, §6) | 169 | 0.3573 | 0.6570 | 0.2100 | 0.9463 | 3.0055 | 15.17 % | 0.0850 | 0.7024 |

Chance top-1 on this data is 0.0389. **The decisive line of the table is the second-to-last column**: on the
55.9 % of decisions where the teacher actually *moves* a user off the reference action — precisely the decisions
that produce its +25 % — every clone predicts the teacher's choice **7–9 % of the time**. All of the apparent
0.37 top-1 comes from the 44 % of decisions where the teacher stays put and the clone copies the reference.
A clone that cannot tell *where to move* cannot carry a gain that is made entirely of moves. This is the
open-loop shadow of the closed-loop result, and unlike the T0 screen the two agree.

For contrast, on the same architecture and the same reference the **T0** screen's clones scored top-1 0.8929 (BC)
and 0.9448 (SOFT) with mean regret 0.020 / 0.004 in the teacher's own score units. [R, `.scratch/t0-repr/`]

## 6. What the student is missing — and what it is not [V]

**Conditional entropy.** On the 24,000 corpus decisions the teacher's marginal action entropy is **3.6764 bits**
(Miller–Madow 3.6773); a uniform draw over the legal set would be 4.7013 bits; conditioning on the reference
action alone leaves 3.0678 bits. The tightest variational upper bound on `H(a_T | obs_B2)` available here is BC's
held-out cross-entropy, **2.9627 bits** — i.e. the B2 observation accounts for at most 0.71 of the teacher's
3.68 bits (19 %). The same bound **without** the context block is 2.9706 bits, so the declared block is worth
**0.0079 bits per decision**. Fine binning is degenerate exactly as in the T0 screen (24,000 distinct bins at
float32 and at 0.05-rounding, 0 % of decisions share a bin, 0 ambiguous bins), so no plug-in estimate is possible
and the exact-decoder route is unavailable: unlike T0, `T_SEQ` is an argmax over counterfactual joint evaluations
and is **not** a function of any student observation. No exact decoder exists and none is claimed.

**The missing information is not the rest of the joint action.** Declared and run as a non-deployable diagnostic:
a clone on `[obs113 | ctx28 | ctxfull28]`, where `ctxfull28` is the per-beam demand of the **teacher's own**
context at *u*'s turn (chosen actions of the earlier users **and reference actions of the later users**, i.e.
exactly the joint vector `V` the oracle best-responds against). Its held-out top-1 is **0.3573** — *no better* than
the 141-dim clone's 0.3665 and no better than the 113-dim clone's 0.3650. Handing the student the whole joint
action the teacher conditions on therefore does **not** make the teacher's decision predictable. What the student
lacks is not a feature of the joint action; it is the counterfactual evaluation itself — 2,500-odd calls to the
physics per step that decide, for this user at this instant, which of 26 legal beams raises `bits − η·joules`
without dropping anyone below half their rate.

## 7. Closed loop, all quantities, one table per episode set [V/D]

Greedy masked argmax (first index on ties), users deciding in the stated order within each step, fresh env per
episode, per-episode reseeding. `ho` = handovers per user-minute; H_inter / H_intra are per user-step; rates are
per served user. Declared clones in bold; ablation, order and sensitivity arms below the line.

### EVALUATION set (env 9,111,000+i / mobility 9,112,000+i, i = 0..23) — no clone saw any of these episodes

| arm | pooled EE (bit/J) | % vs rule | served | lit beams/step | bits / ref | joules / ref | H_inter | H_intra | ho /user-min | rate mean / p10 / min (Mbit/s) | p10 / ref | paired % vs rule | **R_repr** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|---:|
| `A m=2dB` (reference) | 107,000,983.53 | 0.000 | 0.99862 | 63.288 | 1.000 | 1.000 | 0.56163 | 0.04921 | 1.2184 | 431.12 / 101.40 / 4.763 | 1.000 | — | — |
| **T_SEQ** = B-real-floor R1 (teacher) | 134,129,417.19 | +25.353 | 0.99887 | 66.929 | 1.3208 | 1.0536 | 0.60729 | 0.07892 | 1.3688 | 569.27 / 165.46 / 16.048 | 1.632 | +25.71 ± 0.95 (24/24) [R] | 1 (by definition) |
| **BC** (declared) | 111,077,952.80 | +3.810 | 0.99771 | 59.683 | 0.9793 | 0.9433 | 0.51138 | 0.02779 | 1.0755 | 422.58 / 116.48 / 9.346 | 1.149 | +3.998 ± 0.546 (24/24) | **0.1503** |
| **SOFT τ=0.3** (declared) | 110,503,257.07 | +3.273 | 0.99754 | 58.829 | 0.9609 | 0.9304 | 0.46987 | 0.02750 | 0.9921 | 414.70 / 112.05 / 8.495 | 1.105 | +3.485 ± 0.454 (24/24) | **0.1291** |
| BC-noctx (ablation) | 110,004,595.90 | +2.807 | 0.99775 | 60.854 | 0.9884 | 0.9614 | 0.51154 | 0.02708 | 1.0744 | 426.50 / 121.55 / 6.375 | 1.199 | +3.007 ± 0.419 (24/24) | 0.1107 |
| SOFT-noctx (ablation) | 110,796,247.46 | +3.547 | 0.99771 | 60.058 | 0.9836 | 0.9499 | 0.47800 | 0.02612 | 1.0056 | 424.43 / 118.77 / 5.157 | 1.171 | +3.730 ± 0.470 (24/24) | 0.1399 |
| BC, order **rev** (99..0) | 110,424,052.19 | +3.199 | 0.99767 | 59.825 | 0.9757 | 0.9455 | 0.50954 | 0.02708 | 1.0704 | 421.06 / 118.28 / 14.070 | 1.166 | +3.414 ± 0.466 (22/24) | 0.1262 |
| SOFT, order **rev** (99..0) | 110,216,791.34 | +3.005 | 0.99750 | 58.938 | 0.9599 | 0.9319 | 0.47125 | 0.02883 | 0.9975 | 414.31 / 112.35 / 5.119 | 1.108 | +3.219 ± 0.480 (24/24) | 0.1185 |
| BC, torch seed 2000 (fit noise) | 109,950,995.42 | +2.757 | 0.99725 | 59.221 | 0.9627 | 0.9369 | 0.49379 | 0.02183 | 1.0285 | 415.63 / 114.37 / 8.931 | 1.128 | +2.961 ± 0.460 (21/24) | 0.1087 |
| BC, torch seed 3000 (fit noise) | 108,703,067.81 | +1.591 | 0.99679 | 58.054 | 0.9328 | 0.9182 | 0.50542 | 0.02488 | 1.0578 | 402.88 / 109.58 / 7.056 | 1.081 | +1.779 ± 0.399 (19/24) | 0.0627 † |
| BC, 12 TRAIN episodes (data curve) | 109,510,375.48 | +2.345 | 0.99787 | 60.117 | 0.9723 | 0.9500 | 0.50492 | 0.01829 | 1.0436 | 419.47 / 115.60 / 11.681 | 1.140 | +2.503 ± 0.456 (21/24) | 0.0925 |
| BC, 8 TRAIN episodes (data curve) | 107,050,281.11 | +0.046 | 0.99779 | 59.271 | 0.9369 | 0.9365 | 0.50817 | 0.01946 | 1.0524 | 404.27 / 110.84 / 10.256 | 1.093 | +0.208 ± 0.515 (14/24) | 0.0018 † |
| BC, 4 TRAIN episodes (data curve) | 106,578,617.73 | −0.395 | 0.99867 | 61.104 | 0.9615 | 0.9653 | 0.51096 | 0.02679 | 1.0726 | 414.50 / 111.30 / 7.163 | 1.098 | −0.267 ± 0.434 (11/24) | −0.0156 |

† throughput-degenerate on the declared bits-ratio condition (0.9328 and 0.9369 < 0.95). Both are sensitivity arms;
**neither declared clone is degenerate on any condition, on either set.**

### CALIBRATION set (env 9,121,000+i / mobility 9,122,000+i) — in-sample by construction; a separate measurement, never compared with the evaluation set

| arm | pooled EE (bit/J) | % vs rule | served | lit beams/step | bits / ref | joules / ref | H_inter | H_intra | ho /user-min | rate mean / p10 / min (Mbit/s) | p10 / ref | paired % vs rule | **R_repr** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|---:|
| `A m=2dB` (reference) | 112,195,917.54 | 0.000 | 0.99775 | 62.975 | 1.000 | 1.000 | 0.55138 | 0.03538 | 1.1704 | 450.57 / 111.39 / 2.168 | 1.000 | — | — |
| **T_SEQ** (teacher) | 137,497,201.09 | +22.551 | 0.99871 | 67.946 | 1.3172 | 1.0748 | 0.61300 | 0.07358 | 1.3695 | 592.91 / 177.07 / 22.151 | 1.590 | +22.64 ± 0.59 (24/24) [R] | 1 (by definition) |
| **BC** (declared) | 114,512,356.16 | +2.065 | 0.99679 | 59.246 | 0.9620 | 0.9425 | 0.50092 | 0.02283 | 1.0447 | 433.85 / 115.50 / 10.097 | 1.037 | +2.190 ± 0.346 (21/24) | **0.0916** |
| **SOFT τ=0.3** (declared) | 113,481,082.33 | +1.145 | 0.99658 | 59.083 | 0.9509 | 0.9401 | 0.46458 | 0.02192 | 0.9704 | 428.93 / 116.04 / 9.210 | 1.042 | +1.271 ± 0.384 (17/24) | **0.0508** |
| BC-noctx (ablation) | 114,275,583.71 | +1.854 | 0.99662 | 60.283 | 0.9761 | 0.9584 | 0.50404 | 0.02250 | 1.0503 | 440.31 / 122.36 / 13.276 | 1.098 | +1.976 ± 0.473 (19/24) | 0.0822 |
| SOFT-noctx (ablation) | 114,437,553.38 | +1.998 | 0.99642 | 59.596 | 0.9664 | 0.9475 | 0.47246 | 0.02025 | 0.9828 | 436.02 / 120.06 / 6.899 | 1.078 | +2.156 ± 0.503 (19/24) | 0.0886 |

**What the operating points say [D].** The teacher and the clones are not on the same lever. T_SEQ raises lit beams
from 63.3 to 66.9 and bits to 1.32 ×, paying 1.05 × the joules — it *buys* throughput with a little more power, and
its rate tail improves (p10 1.63 ×, min 16.0 Mbit/s against the rule's 4.8). Every clone does the opposite: lit
beams fall to 58.8–60.9, bits to 0.93–0.99 ×, joules to 0.92–0.96 ×. That is the LP/T0 lever — switch off marginal
beams — reached from a different teacher, and it lands where a simple rule already lands. The +19.25 pp that the
sequential oracle has over the simultaneous one lives entirely in the part of its behaviour the clones do not
reproduce.

## 8. Files, code and cost

All produced this session, on sat, in `/home/sat/mcrl-v025-b2-repr-ws/` (mine alone). The other lanes'
workspaces `mcrl-v025-h4-probe-ws`, `mcrl-v025-dev-e0-ws` and `mcrl-v025-ceiling-ws` were **never written to**;
`results-oracle/` and `results-lp/` were read only. `.scratch/validity-audit/` and `.scratch/reviews/` were not read.
Everything was copied back to `.scratch/b2-representability/` and **sha256-verified equal on both ends (99 files)**.

- **Scripts** (`.scratch/b2-representability/scripts/`, each inserts the staged tree's `src` first): `b2_common.py`
  a5464828…, `b2_placebo.py` 6441ab87…, `b2_clone.py` 790a5794…, `b2_select_tau.py` ff136299…, `b2_closed.py`
  8babc285…, `b2_entropy.py` 2bc1b9c8…, `b2_ctxfull.py` 1e503913…, `b2_aggregate.py` f8a2fdc1…; launcher `run.sh`
  ef3918bd… (nice 16, `MemoryMax=5G`, 1 BLAS thread, pinned TLE). *Provenance note:* the declared clones were
  fitted before `b2_clone.py` gained its three diagnostic switches (`--train-episodes`, `--ctxfull`, `--seed`);
  the switches are additive and leave the default path unchanged, but the `CLONE-BC.json` / `CLONE-SOFT-tau*.json`
  records carry the pre-patch script hashes, which is how it should read.
- **Staged tree**: `git -C mcrl-leo-handover-cf3 archive 102b2d4d src scripts tests artifacts/PREREG-FROZEN-2026-08-25-R2.json`,
  tarball sha256 `12c341e5d19031d4377455121914a8857a6c9ce6619975700f2c82ffe3045cba` (5,969,920 B, 437 `.py`),
  identical on both ends and identical to the tree the T0 lane staged.
- **Data**: `data/B2-train-calibration.npz` `ab8c9694…7cf3` (24,000 × [obs 113, ctx 28, mask 28, action, ref_action,
  adv 28, adv_disallowed, adv_disallowed_floor, ref_bits, indices]), `data/B2-ctxfull-calibration.npz`
  `524ca5dd…7eff` (the non-deployable diagnostic block), plus their meta JSONs.
- **Results** (41 files): `AGGREGATE.json` `6530d86f…` (the verdict's record), `PLACEBO-REF-{evaluation,calibration}.json`,
  `PLACEBO-TEACHER-{evaluation,calibration}.json`, `TEACHER-{evaluation,calibration}.json`, `TAU-SELECTION.json`
  `4db0bd94…`, `ADV-SCALE.json` `77168c71…`, `ENTROPY.json` `7d45ba10…`, 15 × `CLONE-*.json`, 16 × `CLOSED-*.json`.
  **Models** (15, ~85 KB each): `BC.pt` `49118e7b…`, `SOFT-tau0.3.pt` `638873ac…`, and the ablation / sensitivity fits.
  **Logs** (`logs/`) for every detached job.
- **Cost**: **45 min wall** from dispatch to the verdict (20:15 → 21:00 UTC), ~50 min including the write-up; at most
  **3 processes** at any moment, `nice -n 16`, 1 BLAS thread and `torch.set_num_threads(1)` in every process,
  `systemd-run --user --scope -p MemoryMax=5G`, peak RSS ~0.9 GB, nothing in `/tmp`, no process of this lane left
  running and none killed. 16 closed-loop rollouts at 38–43 s each; 15 clone fits at 7–20 s each.

## 9. What this does and does not establish

1. **Establishes** that the extra value of the sequential oracle over the simultaneous one is **not** representable
   from the declared B2 observation by the learner's own function class fitted on the available teacher data:
   `R_repr` = 0.05–0.15 against an admission line of 0.5, with a bootstrap that never touches 0.5, and with no
   throughput degeneracy to explain it away. Under Amendment 4 §2, **condition 3 fails and B2 is not entered.**
   B1 keeps priority and the execution contract is unchanged.
2. **Establishes** that the specific information B2 would add — earlier users' same-step choices — is worth
   ≈ 0 in this measurement: 0.008 bits per decision open loop, and a closed-loop effect of either sign whose mean
   over four comparisons is ~0.000 in `R_repr`. It also establishes that this is **not** because the block is too
   thin: giving the student the teacher's entire joint context (`ctxfull`, non-deployable) does not raise held-out
   fidelity either. The teacher's advantage lives in the counterfactual evaluation, not in a feature.
3. **Establishes** that the failure is not the user order: with the order reversed the clones keep 84 % / 92 % of
   their headroom. Scope limit: the *teacher* was only measured in the forward order (the oracle lane's
   reverse-order cell is HELD), so nothing here says the oracle's own +25 % survives reversal.
4. **Does not establish** that no B2 observation could ever work — only that the one declared in the brief, on this
   corpus, does not. A different construction (for example a per-slot *predicted* interference or a served-count
   forecast, rather than a demand count) is untested.
5. **The one real caveat, stated plainly: the closed-loop learning curve has not saturated.** BC's `R_repr` on the
   evaluation set is −0.016 / 0.002 / 0.093 / 0.150 at 4 / 8 / 12 / 15 TRAIN episodes. A linear extrapolation in
   rows would reach 0.5 at roughly 32 training episodes — about 17 more floored B-real calibration cells, ~17 min
   of oracle compute on four shards. Three things argue that the extrapolation is not to be trusted, and I record
   all three rather than picking one: (a) **held-out fidelity has already saturated** — top-1 0.3322 / 0.3545 /
   0.3675 / 0.3665 over the same four data sizes, i.e. flat from 12 episodes on, while EE keeps moving, which is
   the signature of noise rather than learning; (b) **fit noise alone spans the top of the curve** — refitting the
   same declared clone with torch seeds 2000 and 3000 gives `R_repr` 0.109 and 0.063 against seed 1000's 0.150, a
   spread of 0.087 that is larger than the 12 → 15 episode increment; (c) the `ctxfull` diagnostic shows the
   fidelity ceiling is not an information problem, so more of the same data buys a better fit to a target that
   remains only 19 % explained. **If the owner wants the negative reading overturned rather than accepted, the
   decisive and cheap experiment is more floored B-real calibration episodes plus a multi-seed closed-loop read —
   not a re-run of this one.** I did not run it because it is outside this brief and because B2 is a
   conditional branch that this screen was asked to gate, not to advocate for.
6. **Does not compare** the two episode sets with each other, and carries no number from another host or archive:
   every figure is sat, pinned archive 427e6a91, MODQN-harness, with §2 as the tie to the oracle and LP lanes.
7. **Independent of the verdict**: nothing here touches the development lane (Amendment 6, T0 anchor teacher),
   which uses a non-privileged teacher and is unaffected. Nothing here authorises any learner training.
