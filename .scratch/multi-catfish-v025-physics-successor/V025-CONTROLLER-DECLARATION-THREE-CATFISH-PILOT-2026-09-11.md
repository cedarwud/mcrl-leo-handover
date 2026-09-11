# Declaration — the three-catfish design, frozen for today's short-episode pilot

Date: 2026-09-11. **Owner instruction: finalise the three catfish today and start short-episode
training.** Everything below is fixed **before** any pilot result exists and is not changed after.
Stage 1 (catfish-off reference) is folded into this batch as an arm rather than run first.

## The learner (all new-design arms)

- **Three Q-heads on one trunk-free MODQN-style network set, one per physical quantity**, reward
  vector per user-step `(B_u, E_u, H_u)`:
  - `B_u` = user u's decoded bits in the step (`R_u * dt`);
  - `E_u` = system joules in the step divided equally over the U users (`P_sys * dt / U`), so
    `sum_u E_u` = the evaluator's denominator exactly;
  - `H_u` = 1 if u's step is an inter-satellite handover, else 0 (the C-H quantity).
- **Shared continuation bootstrap** (D-1 flag ON): every head's target uses
  `a' = argmax_a [Q_B − eta*Q_E − lambda*Q_H](s', a)` over legal actions.
- **Action rule**: `argmax_a [Q_B − eta*Q_E − lambda*Q_H]`, masked. Deployed alone.
- **`eta` (Dinkelbach)**: `eta_0` = pooled EE of `MAX_NOMINAL_GAIN` on a calibration seed set
  (never the evaluation seeds); updated every quarter of the pilot to the greedy policy's pooled
  `sum B / sum E` on the calibration seeds. Replay stores **raw** `(B, E, H)`; targets are
  recomputed at sample time with the current `eta`, `lambda` (ASK-1 option C; declared as our
  adaptation).
- **`lambda` (constraint C-H, dual ascent)**: `lambda_0 = 0`; at each quarter,
  `lambda <- max(0, lambda + alpha * (H_inter_measured − 0.6016))`, with `alpha` fixed below.
- D-2 (per-step outage floor, adapted to these heads: an unserved user gets `B_u = 0` and its share
  of `E`), D-3 logging. Undiscounted is not used: `gamma` as in the baseline trainer, unchanged.
- **Exploration**: the baseline ε schedule's shape, compressed to the pilot length, identical for
  every arm.

## The three catfish — one per Q-head

| catfish | source rule | information | feeds head |
|---|---|---|---|
| **C1** (C-gain) | `A m=2dB` | gain | `Q_B` |
| **C2** (C-hold) | `A m=12dB` | gain + incumbent memory | `Q_H` |
| **C3** (C-consolidate) | `B1_NO_NEW_BEAM` | previous-step loads + gain | `Q_E` |

Each catfish runs in **its own environment copy** (same seeds schedule as the main), and pushes its
transitions — carrying the **unshaped** `(B, E, H)` (containment; no competitive term in this
pilot) — into its own buffer. **Head k's minibatch is `(1 − rho)` main replay + `rho` from catfish k's
buffer**, `rho = 1/9 ≈ 0.111` (Nair et al. 2018's demo fraction; not tuned). Every head also keeps
learning from the main replay. No imitation / margin loss in this pilot. Only the main agent is
evaluated.

## Arms

| arm | what | answers |
|---|---|---|
| **A0 BASELINE** | MODQN eq. (16) per-head max, `r1/r2/r3`, `0.5/0.3/0.2`, D-2, D-3 | the owner's success gate reference |
| **A1 OFF** | new learner, no catfish | does the learner change alone beat A0 |
| **A2 CF3** | A1 + C1/C2/C3 | the three-catfish effect |
| **A3 NULL3** | A1 + three **random-legal-action** catfish, identical schedule, buffers, `rho`, routing | is it the demonstrations or just extra experience |

**3 training seeds per arm, same seeds across arms. Episodes: 1000.** Final checkpoint only.

## Evaluation (identical for every arm)

Greedy, **pinned TLE archive** (hash recorded), 24 evaluation episodes on seeds disjoint from
training and calibration, same stream positions. Report: **pooled EE** (ratio of sums; bits and
joules separately), **`H_inter`** vs C-H 0.6016, `H_intra`, **served fraction** vs C-S, mean active
beams, plus `eta` and `lambda` trajectories. Per-arm mean over seeds and every seed individually.

## Declared reading (pilot = direction only; nothing here is a claim)

- **A2 > A3 and A2 > A1**, C-H met, C-S non-inferior → directional three-catfish signal → proceed to
  full-length runs and drop-one ablations.
- **A2 ≈ A3 > A1** → the gain is extra experience, not the demonstrators; report as such.
- **A1 ≥ A2** → no catfish effect at pilot scale; report, and check whether the pilot length was
  the limit before any redesign.
- **A1 vs A0** is read separately: whether the objective/learner change alone beats baseline MODQN.
  A win of A2 over A0 is the owner's success gate; A2 vs A1/A3 is what attributes it to catfish.

## Fixed constants

`rho = 1/9`; `alpha = 1.0` per unit of handover-rate violation (λ in the units of `Q_H`); quarter
length = 250 episodes; `eta_0` computed once and recorded before training; C-H 0.6016, C-S −0.5 pp.
