# B2 / T_SEQ representability lane — PROGRESS

Agent: B2 representability lane. Brief: `.scratch/b2-representability/BRIEF-DRAFT.md` (dispatched 2026-09-11 ~20:07 UTC).
Task: Amendment 4 §2 **condition 3** — is the extra value of the sequential oracle (`T_SEQ` = B-real-floor R1) representable
from the B2 student's observation? Metric `R_repr` (Amendment 3 §3). **Measurement only: no learner training.**

Start 2026-09-11 20:15 UTC. Host `sat`. Workspace `/home/sat/mcrl-v025-b2-repr-ws/` (mine alone). Other lanes'
workspaces (`mcrl-v025-h4-probe-ws`, `mcrl-v025-dev-e0-ws`, `mcrl-v025-ceiling-ws`) are **read-only or untouched**:
I read the oracle lane's `results-oracle/` and `results-lp/` and write nothing there.
`.scratch/validity-audit/` and `.scratch/reviews/` are not read.

Constraints held throughout: ≤ 3 processes, `nice -n 16`, `OMP/MKL/OPENBLAS_NUM_THREADS=1` + `torch.set_num_threads(1)`,
`systemd-run --user --scope -p MemoryMax=5G`, `MCRL_TLE_ROOT=/home/sat/mcrl-v025-cf3-pilot-ws/tle-pinned-427e6a91`
asserted in every process (file-set sha256 `427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9`),
detached for anything long, exact-PID kills only, nothing in `/tmp`.

---

## S0. Inputs read (20:07–20:20 UTC)

- `BRIEF-DRAFT.md` (in full), Amendment 4 §2, Amendment 3 §3, `.scratch/h4-probe/BRANCH-NUMBERS-FLOOR-R1-EVAL.md`,
  `.scratch/t0-repr/T0-REPRESENTABILITY-2026-09-12.md` + all eight T0 scripts (method template),
  `.scratch/h4-probe/scripts/oracle_cells.py` and `oracle_replay.py`, and the tree's
  `action_contract.py` / `state_encoding.py` / `step.py` / `service.py` / `cf3_common.py`.
- **Precondition check (verified by me on sat, 20:12 UTC):** `results-oracle/` holds **24/24**
  `B-real-floor-R1-calibration-fwd-ep*.json` and **24/24** matching `-obs-actions.npz`, plus the assembled
  `B-real-floor-R1-calibration-obs-actions.npz` (7,463,628 B). One cell inspected: `obs (1000,113) float32`,
  `mask (1000,28) bool`, `action`, `ref_action`, `adv (1000,28) float32`, `adv_disallowed`, `adv_disallowed_floor`,
  `episode`, `step`, `user`; JSON carries `order` = `fwd`, `joint_ref`, `joint_chosen` (10 × 100), and per-step
  `ref_bits`, `ref_joules`, `eta_bits_per_j`, `n_moved`, `n_disallowed`, `n_disallowed_floor_only`.
- **Controller addition (20:20 UTC, before any fit):** after the declared closed-loop runs, roll each clone a second
  time on the same 24 evaluation episodes with the user order **reversed (99..0)** and report `R_repr` for both
  orders, as a scope limit on "sequential information" vs "this particular order". The **forward-order** result is
  the one the admission verdict reads.

## S1. Staged tree (20:16 UTC)

`git -C /home/u24/papers/mcrl-leo-handover-cf3 archive 102b2d4d src scripts tests artifacts/PREREG-FROZEN-2026-08-25-R2.json`
→ tarball sha256 `12c341e5d19031d4377455121914a8857a6c9ce6619975700f2c82ffe3045cba` (5,969,920 B, 437 `.py`),
copied with `cat … | ssh sat 'cat > …'` and **sha256 verified identical on both ends**; unpacked to
`/home/sat/mcrl-v025-b2-repr-ws/tree/`, `tree/COMMIT` = `102b2d4d`. (Byte-identical to the tree the T0 lane staged.)

---

## S2. DECLARATIONS — fixed before any fit, any closed-loop run and any result

### D1. The B2 student observation (141 dims) — declared exactly, never changed afterwards

```
obs_B2[u] = concat( enc113[u] , ctx28[u] )                                       (float32, 141)

enc113[u]  = cf_ratio.encode_with_time(states, t, users, cfg, steps)[u]          (unchanged, the ratio
             = [access(28), log1p(SNR)(28), theta_rad(28), loads/U(28), (T-t)/T]  learner's own observation)

ctx28[u,a] = ( # of users v that decided BEFORE u in this step's sweep order, whose chosen action a_v is not
               NO_OP and whose realised beam (norad_id, cell_id) under v's slot table equals u's slot-a beam )
             / num_users
           = 0 for any slot a with norad_id < 0 or cell_id < 0 (no beam identity).
```

`ctx28` is the current step's **partial, ungated per-beam demand** mapped onto user *u*'s 28 candidate slots and
normalised by `num_users` — the same quantity and the same normalisation as encoded block 4
(`beam_loads`, the *previous* step's demand, `load_normalization = divide_by_num_users`), only accumulated over the
users that have already decided **this** step. It is exactly the brief's "one extra block of 28 counts, normalised
like the previous-step loads"; "already lit this step by an earlier-deciding user" is `ctx28 > 0`, recoverable from
the counts, so no separate binary block is added. Beam identity is taken from the environment's own slot tables
(`sim._candidates.slot_tables[v].norad_ids/cell_ids`), because the 28 action indices are **per-user** slots — the
same index means different physical beams for different users, so counting raw action indices would be wrong.

Nothing else is added: no realised rates, no other user's SINR, no later user's action, no counterfactual value.
A sequential protocol can deliver `ctx28` by broadcasting the running per-beam count.

### D2. Data

- **Training corpus** = the floored **B-real R1 CALIBRATION** cells: 24 episodes × 10 steps × 100 users = **24,000
  decisions**, out of the evaluation set by construction. Teacher label = `action` (the committed oracle action);
  teacher value = `adv` (28-slot advantage in F-units, NaN on illegal, 0 at the base = the reference action).
- **Split by episode** (same rule as the T0 screen): episode `i` is TEST if `i % 5 == 4` (4 episodes), VAL if
  `i % 5 == 3` (5 episodes), TRAIN otherwise (15 episodes) → 15,000 / 5,000 / 4,000 decisions. Empty-mask rows
  excluded and counted (expected 0).
- The 24 **evaluation** episodes are used for nothing but the final closed-loop measurement.
- **Declared in-sample caveat**: the brief's data source *is* the calibration set, so the calibration-set closed-loop
  `R_repr` is **in-sample** (its TRAIN/VAL episodes trained and selected the clone). The evaluation-set `R_repr` is
  fully out-of-sample. Both are reported; the two sets are never compared with each other.

### D3. Advantage normalisation and the τ grid

- `adv_norm[u,a] = adv[u,a] / ref_bits(step)` — `ref_bits` is that step's bits under the reference joint action
  (`steps_detail[t]["ref_bits"]`), so `adv_norm` is a dimensionless fraction of the step's reference throughput.
- `adv_std[u,a] = adv_norm[u,a] / s`, where **s = the RMS of `adv_norm` over the TRAIN split's legal, non-base
  slots** (formula declared here, value computed from TRAIN only and written into this file before any fit).
- **τ grid (declared): {0.01, 0.03, 0.1, 0.3, 1, 3}** applied to `adv_std` — the same grid the T0 screen declared.

### D4. The clones (measurement instruments — not the learner, no `update()`, no MODQN checkpoint)

`DQNNetwork(input → 100 → 50 → 50 → 28, tanh)` — the learner's own Q-network class with the pilot config's hidden
layers and activation; raw inputs (no z-scoring); illegal logits → −1e9 (masked softmax); Adam lr 1e-3, batch 256,
torch seed 1000 (init + shuffling); **400 epochs**, the epoch selected on VAL.

*Deviation from the T0 recipe, declared with its reason:* T0 used 100 epochs on 180,000 TRAIN rows (70,400 gradient
steps). Here TRAIN is 15,000 rows, so 100 epochs would be 5,900 steps; 400 epochs gives 23,600. The epoch is
selected on VAL from the whole curve, so a larger budget only widens the search and cannot force over-training.

| clone | input | target |
|---|---|---|
| **BC** (declared) | 141-dim B2 observation | cross-entropy on the teacher's action (one-hot) |
| **SOFT τ*** (declared) | 141-dim B2 observation | cross-entropy toward `softmax(adv_std / τ)` over **legal-and-allowed** actions |
| **BC-noctx** (ablation) | 113-dim observation only | as BC — isolates the marginal value of `ctx28` |
| **SOFT-noctx** (ablation) | 113-dim observation only | as SOFT at the selected τ |

**Soft-target support, declared:** the softmax is taken over legal actions that the teacher's own decision rule was
allowed to choose, i.e. excluding slots flagged `adv_disallowed` (service floor or rate floor). Reason: the teacher's
rule is `argmax` over legal-and-allowed with ties kept at the base, so a target with mass on disallowed slots would
teach the student to break the rate floor the floored cell exists to enforce. The base (reference) action is never
disallowed, so the support is never empty. The share of decisions whose max-advantage legal slot is disallowed is
reported as a diagnostic.

**Selection (VAL only, both epoch and τ, written here before any closed-loop run):** minimise the mean
**teacher-advantage regret** `adv_std[a_teacher] − adv_std[a_clone]` with `a_clone` = masked argmax over **legal**
slots (what the closed loop actually does); tie → max VAL top-1 → earliest epoch. Action accuracy alone is not the
criterion (Amendment 3 §3, and the T0 screen's lesson: the closed-loop metric decides). The clone's rate of picking
a `adv_disallowed` slot is reported next to it, not optimised.

### D5. Closed loop

Each clone is rolled **sequentially**: at every step the users decide in the declared order, user *u* seeing
`ctx28` built from the choices the clone has already made this step; greedy masked argmax over legal slots (first
index on ties, no generator consumed); fresh env per episode, per-episode reseeding; pinned archive.
Episode sets: EVALUATION (env `9_111_000+i` / mobility `9_112_000+i`, i = 0..23) and CALIBRATION
(`9_121_000+i` / `9_122_000+i`). Declared order **fwd = 0..99** (the order the teacher was built with); the
controller's added **rev = 99..0** run is a secondary reading on the evaluation set only.
Reported per arm: pooled Σbits/ΣJ (divided once, plain left-to-right sums — `lp_common.pooled_rollout_rates`
statement for statement), bits, joules, served, lit beams/step, H_inter, H_intra, handovers per user-minute,
per-served-user rate mean / p10 / min.

### D6. The metric and the reading (declared, from the brief)

`R_repr(T_SEQ) = (EE(clone) − EE(A m=2dB)) / (EE(B-real-floor) − EE(A m=2dB))`, all three pooled EEs on the SAME
episode set. Reported on both sets, plus held-out top-1 / top-3 and the teacher's conditional action entropy given
the B2 observation.

**Condition 3 is met iff at least one clone reaches `R_repr ≥ 0.5` on BOTH episode sets AND is not
throughput-degenerate: served ≥ 0.995, bits ratio ≥ 0.95, p10 ≥ 0.5 × the rule's p10 on the same set.**

---

## S3. Log

(appended after every step; detached jobs recorded with PID, cwd, cmdline, output path and expected finish)

### S3.1 Placebo — PASSED (20:24–20:33 UTC) [V]

Scripts `scripts/b2_common.py`, `scripts/b2_placebo.py`; launcher `run.sh` (nice 16, `MemoryMax=5G`, 1 thread,
pinned TLE asserted in-process). Detached: `setsid nohup ./run.sh b2_placebo.py --only ref > logs/placebo-ref.log`
(PID 3569629 wrapper) and `--only teacher > logs/placebo-teacher.log` (PID 3569798); both exited by themselves.

| check | evaluation | calibration |
|---|---|---|
| `A m=2dB` re-rolled through my loop vs LP probe `REF-C1_A_m2dB-<set>.json`, 15 fields | **all 15 bit-identical**, ee 107,000,983.53410847 | **all 15 bit-identical**, ee 112,195,917.53568056 |
| `T_SEQ` = B-real-floor R1 pooled Σbits/ΣJ re-derived by me from the 24 cell JSONs | **134,129,417.19** (matches BRANCH-NUMBERS-FLOOR-R1-EVAL) | **137,497,201.09** (matches h4-probe PROGRESS T2-23) |
| teacher replay: reference rule reproduces stored `joint_ref` | 20/20 steps (ep 0–1) | **240/240 steps (all 24 ep)** |
| teacher replay: re-encoded 113-dim observation vs saved npz | 20/20 steps bit-identical | **240/240 bit-identical** |
| teacher replay: committed bits / joules vs stored | max abs Δ **0.0 / 0.0** | max abs Δ **0.0 / 0.0** |
| empty masks / NO_OP actions | 0 / 0 | 0 / 0 |

Walls 37.4 s + 37.8 s (reference), ~7 min (teacher replay + corpus).

### S3.2 Training corpus built (20:33 UTC) [V]

`data/B2-train-calibration.npz` sha256 `ab8c9694c1253e02fd9526d142ae0fbfe4be7521eed0b852f60ac24bdba87cf3`,
**24,000 rows**, 0 empty masks, 0 NO_OP, mean legal-set 26.21, teacher action == reference action on 45.13 %
of decisions (the teacher **moves 54.87 %** of users). ctx block: 17.92 % of the 28-slot entries are non-zero,
max 0.09 (= 9 earlier users already on that beam), mean row sum 0.0671.

### S3.3 Advantage scale — computed from TRAIN only, before any fit [V]

`s = RMS(adv/ref_bits)` over the TRAIN split's legal non-base slots (377,665 slots, 15,000 rows) =
**0.014954477965824223**; mean |adv_norm| 0.011043 → mean |adv_std| 0.7384. Split: TRAIN episodes
{0,1,2,5,6,7,10,11,12,15,16,17,20,21,22} = 15,000 rows, VAL {3,8,13,18,23} = 5,000, TEST {4,9,14,19} = 4,000.

### S3.4 τ selected on VAL — written BEFORE any closed-loop run (20:41 UTC) [V]

Criterion as declared (min VAL mean teacher-advantage regret at each τ's VAL-selected epoch; tie → max VAL
top-1 → smallest τ). All fits 400 epochs, ~18 s each.

| τ | selected epoch | VAL regret (adv_std) | VAL top-1 | VAL top-3 |
|---|---:|---:|---:|---:|
| 0.01 | 34 | 0.184764 | 0.3922 | 0.6864 |
| 0.03 | 34 | 0.181491 | 0.3926 | 0.6874 |
| 0.1 | 32 | 0.175837 | 0.3996 | 0.6940 |
| **0.3 (selected)** | 20 | **0.173581** | 0.3978 | 0.6854 |
| 1 | 28 | 0.189575 | 0.3954 | 0.6580 |
| 3 | 17 | 0.207160 | 0.3840 | 0.6454 |

**τ = 0.3 is interior to the declared grid** (unlike the T0 screen, where τ sat at the upper edge).
Declared clones: `BC` (VAL-selected epoch 36, TEST top-1 0.3665) and `SOFT-tau0.3` (epoch 20, TEST top-1 0.3807).
Ablation `BC-noctx` (epoch 29, TEST top-1 0.3650); `SOFT-tau0.3-noctx` is fitted at the same τ (not re-selected).
Every VAL-selected epoch is far inside the 400-epoch budget (17–36), i.e. the fits are **not** budget-limited.

### S3.5 Closed loop — 10 sequential rollouts (20:33–20:48 UTC) [V]

Each `./run.sh b2_closed.py --clone <name> --set <set> [--order rev]`, detached, ≤ 3 at a time, 38–43 s each,
exit codes 0, no process left behind. Reference and teacher rows from §S3.1.

| set | arm | pooled EE (bit/J) | % vs rule | **R_repr** | served | bits/rule | p10 × rule | degenerate? |
|---|---|---:|---:|---:|---:|---:|---:|---|
| EVAL | rule `A m=2dB` | 107,000,983.53 | 0 | — | 0.99862 | 1.000 | 1.000 | — |
| EVAL | **teacher T_SEQ** | 134,129,417.19 | +25.353 | 1 (def.) | 0.99887 | 1.321 | 1.632 | no |
| EVAL | **BC** (declared) | 111,077,952.80 | +3.810 | **0.1503** | 0.99771 | 0.9793 | 1.149 | no |
| EVAL | **SOFT τ=0.3** (declared) | 110,503,257.07 | +3.273 | **0.1291** | 0.99754 | 0.9609 | 1.105 | no |
| EVAL | BC-noctx (ablation) | 110,004,595.90 | +2.807 | 0.1107 | 0.99775 | 0.9884 | 1.199 | no |
| EVAL | SOFT-noctx (ablation) | 110,796,247.46 | +3.547 | 0.1399 | 0.99771 | 0.9836 | 1.171 | no |
| EVAL | BC, order **rev** | 110,424,052.19 | +3.199 | 0.1262 | 0.99767 | 0.9757 | 1.166 | no |
| EVAL | SOFT, order **rev** | 110,216,791.34 | +3.005 | 0.1185 | 0.99750 | 0.9599 | 1.108 | no |
| CAL | rule `A m=2dB` | 112,195,917.54 | 0 | — | 0.99775 | 1.000 | 1.000 | — |
| CAL | **teacher T_SEQ** | 137,497,201.09 | +22.551 | 1 (def.) | 0.99871 | 1.317 | 1.590 | no |
| CAL | **BC** (declared) | 114,512,356.16 | +2.065 | **0.0916** | 0.99679 | 0.9620 | 1.037 | no |
| CAL | **SOFT τ=0.3** (declared) | 113,481,082.33 | +1.145 | **0.0508** | 0.99658 | 0.9509 | 1.042 | no |
| CAL | BC-noctx (ablation) | 114,275,583.71 | +1.854 | 0.0822 | 0.99662 | 0.9761 | 1.098 | no |
| CAL | SOFT-noctx (ablation) | 114,437,553.38 | +1.998 | 0.0886 | 0.99642 | 0.9664 | 1.078 | no |

Bootstrap (10,000 episode-cluster resamples, same indices for clone / teacher / reference, seed 20260912):
every arm's 95 % interval sits below 0.19, and the share of resamples with `R_repr ≥ 0.5` is **0 %** everywhere.
**No arm is throughput-degenerate**, so the shortfall is not a collapsed-rate artefact.

### S3.6 Conditional entropy (20:48 UTC) [V]

`results/ENTROPY.json` on the 24,000 calibration decisions: marginal `H(a_T)` = **3.6764 bits**
(Miller–Madow 3.6773; uniform-over-legal would be 4.7013); `H(a_T | a_ref)` = 3.0678 (MM 3.0874);
variational upper bound on `H(a_T | obs_B2)` from BC's held-out CE = **2.9627 bits**, and from BC-noctx
(no ctx block) = **2.9706 bits** → the declared ctx block buys **0.0079 bits per decision**. Fine binning is
degenerate as expected (24,000 distinct bins at float32 and at 0.05-rounding, 0 % of decisions share a bin,
0 ambiguous bins). Unlike T0 no exact decoder exists or is claimed: `T_SEQ` is an argmax over counterfactual
joint evaluations, not a function of the student's observation.

### S3.7 Sensitivity and diagnostics added after the declared reading (20:44–20:56 UTC) [V]

All declared before their own runs; **none of them changes the verdict**, and the verdict is read on the declared
forward-order clones of §S3.5.

- **`ctxfull` diagnostic (non-deployable)**: `b2_ctxfull.py` rebuilt the 24 calibration episodes and recorded, per
  decision, the per-beam demand of the **teacher's own** context (earlier users' chosen + later users' reference
  actions) — `data/B2-ctxfull-calibration.npz` sha256 `524ca5dd…7eff`, 39 s. A 169-dim clone on
  `[obs113 | ctx28 | ctxfull28]` reaches TEST top-1 **0.3573**, i.e. *no better* than 0.3665 (141-dim) or 0.3650
  (113-dim). Never rolled in closed loop, by declaration.
- **Fit noise**: the declared BC refit with torch seeds 2000 and 3000 → evaluation `R_repr` **0.1087** and
  **0.0627** against seed 1000's 0.1503 (spread 0.087).
- **Data learning curve** (BC, seed 1000, evaluation): 4 / 8 / 12 / 15 TRAIN episodes → `R_repr`
  **−0.0156 / 0.0018 / 0.0925 / 0.1503**, while TEST top-1 goes 0.3322 / 0.3545 / 0.3675 / 0.3665 (flat from 12 on).
  Two of these sensitivity arms (seed 3000, 8 episodes) are throughput-degenerate on the bits ratio (0.933, 0.937);
  **no declared clone is.**

### S3.8 Aggregation, copy-back and close-out (20:55–21:00 UTC) [V]

- `b2_aggregate.py` → `results/AGGREGATE.json` sha256 `6530d86f…`; 15 arms across the two sets, bootstrap
  10,000 episode-cluster resamples (seed 20260912, same indices for clone / teacher / reference).
  **`CONDITION 3 MET: False`.**
- The whole workspace (`scripts results models logs data run.sh`, 99 files) was tarred, streamed back with
  `ssh sat 'cat …' > …` and unpacked into `.scratch/b2-representability/`; **sha256 verified equal on both ends for
  all 99 files** (`tar` sha256 `61fac8eb…d8dc`).
- **No process of this lane remains on sat** (verified 21:00 UTC); nothing had to be killed. Other lanes'
  workspaces were never written to; `results-oracle/` and `results-lp/` were read only.
- Report written: `.scratch/b2-representability/T-SEQ-REPRESENTABILITY-2026-09-12.md`.
- **Wall time 45 min** (20:15 → 21:00 UTC), ≤ 3 processes throughout, peak RSS ~0.9 GB.
