**lighting-price credit oracle-first: FAIL — the credit's own one-step greedy rule (closed loop, others held at `A m=2dB`) gains +24.6 % / +24.9 % pooled EE at η = eta_0 / 1.0e8 when its own bits come from the realised evaluator, but keeps only 0.867 / 0.920 of the rule's bits against a ≥ 0.95 gate (6 evaluation episodes), and with observation-level own bits it *loses* 7.1–7.4 % on all 24 evaluation and 24 calibration episodes (bits 0.55, p10 0.38); the engineering core is green — 9 tests green, 13 named mutants red, `equal_share` bit-identical to CF3 at 102b2d4d — and under the difference credit the one-step argmax of `B^D − η·E^D` differs from the argmax of `B^D` alone in 866 of 2000 decisions (43.3 %) against 3 of 2000 (0.15 %) for the equal-share credit on the same decisions (the CF3 review's 0-of-240 probe), at a projected ≈ 6.2 h per 1000-episode run, ≈ 11× CF3 A1's ~0.56 h.**

# B1-CREDIT — the difference-reward credit and the analytic lighting price for the ratio learner

Date: 2026-09-12. Engineering lane (Ruling 2 §5): **no optimizer step, no training run, no learner update** was
performed anywhere in this task. Brief: `.scratch/b1-credit/PROMPT.md`. Governing: ruling 2 §3 stage B1
(`V025-CONTROLLER-RULING-CEILING-PARITY-B-CHAIN-AND-CATFISH-COUNT-2026-09-11.md`), Amendment 1 (oracle-first screen),
Amendment 2 (scenario-A branch), Amendment 5 Part II item 2 and the controller's 18:00 UTC addition (the
lighting-price credit's own greedy rule must be screened).

```
PROVENANCE [A] (this task's own measurements)
- physics / harness (C):   MODQN-harness, users 100, 10-step episodes, fresh env per episode; no MDP modifier added
                           (cap / segment anchor / interruption exactly as the CF3 pilot ran them)
- estimand (C):            diagnostics = fractions over decisions (a user-step with a non-empty mask) and
                           distributions of per-user credits; screen = pooled ratio-of-sums EE (Sigma bits /
                           Sigma joules, divided once), full-buffer numerator; benchmark = wall seconds
- power accounting (C):    consumed, per-beam (F-2): supply(p_beam) + P_cir per lit beam + P_BB per lit satellite
- host + TLE archive (C):  LOCAL laptop (LAPTOP-O8M86FNI, WSL2), nice -n 16, OMP_NUM_THREADS=1, torch 1 thread,
                           <= 2 concurrent processes; archive = pinned 427e6a91...8fe9, asserted in every process
- evaluation construction (C): calibration episodes env 9,121,000+i / mobility 9,122,000+i; evaluation episodes
                           env 9,111,000+i / mobility 9,112,000+i; rules from `cf_sources.py`; no rule consumes RNG
- units (C):               CF3's declared units, measured on sat before the pilot: s_B = 13,329,082,278.45065
                           bits/user-step, s_E = 120.61728174105066 J/user-step, eta_0 = 110,507,234.83444457 bit/J,
                           so eta~ = eta s_E / s_B = 1 at eta_0
- code:                    worktree /home/u24/papers/mcrl-leo-handover-b1, branch b1/difference-reward-20260912,
                           engineering-core commit 63b02dc030180b83889387b031bd1c7dff4754f5 (base 102b2d4d)
- status:                  ENGINEERING + DIAGNOSTIC. No learner was trained; nothing here says whether either
                           credit helps a learner. The lighting-price screen below is a no-training rollout.
```

## 1. What was built

| file | what |
|---|---|
| `src/mcrl/algorithms/cf_credit.py` (new) | the credit module: difference reward from the environment's counterfactual evaluator, analytic lighting price, the outage charge, the documented "without u" semantics, a scoped memo of the step-0 warm-start geometry |
| `src/mcrl/algorithms/cf_ratio.py` | `CFRatioSettings.credit_mode ∈ {equal_share (default), difference, lighting_price}`; trainer dispatch; `generate_pool(credit_mode=…)` + a pool credit marker; the trainer refuses a pool credited differently from its own replay; pre-B1 resume states load as `equal_share` |
| `tests/test_cf_credit.py` (new) | 9 tests, 13 named mutants |
| `scripts/b1_credit_diag.py` (new) | the no-training diagnostics and the cost benchmark |
| `scripts/b1_lp_credit_rule.py` (new) | the lighting-price credit's own one-step greedy rule, rolled out closed loop (the controller's 18:00 UTC addition) |

`equal_share` is CF3 exactly: same rewards, same replay rows, same RNG streams, same logs, same settings fingerprint
except the new flag at its default (test 1, against `git show 102b2d4d:src/mcrl/algorithms/cf_ratio.py` executed as a
module in the same process).

Per user-step the reward vector stays `(B, E, H)` with `H` unchanged in every mode (1 iff the step is an
inter-satellite handover):

* **`equal_share`** (CF3): `B_u = R_u dt` (0 unserved), `E_u = P_sys dt / U`.
* **`difference`**: `B_u^D = bits(a) − bits(a without u)`, `E_u^D = joules(a) − joules(a without u)`, both from
  `StepEnvironment.evaluate_actions` / `evaluate_actions_without_user` on the pre-step state, with common random
  numbers, nothing committed. The evaluator's base vector is asserted equal to the committed step every step
  (ruling 2 §1 parity); a mismatch raises `MCRLContractError`.
* **`lighting_price`**: `B_u = R_u dt` (own bits, as CF3); `E_u` = the analytic marginal joules of the power model.

## 2. What "without u" does in this physics

Established by reading (`env/step.py::_resolve_physics`, `env/service.py`, `env/link_budget.py`,
`env/interference.py`) and then by test (`test_without_u_changes_only_bandwidth_share_and_interference_from_its_beam`,
which predicts the evaluator's without-u rate vector from the committed step's own physics and matches it to 1e-9
relative on every user, every removal):

1. **u's own bits disappear.**
2. **Bandwidth share.** A beam is time-shared, `R_v = (B_w / U_b)·log2(1 + γ_v)`; u's beam-mates go from `U_b` to
   `U_b − 1` sharers and their SINR is unchanged — a beam does not interfere with its own users, and a user's wanted
   term uses its **own** link power, not the beam power.
3. **Per-beam max power.** The beam radiates `p_b = max` over its served users' link powers. If u is the **unique**
   max, `p_b` drops to the next highest; if u ties at the max, or is below it, nothing changes (ties are common: a
   fresh segment starts at exactly `p⁰ = 0.825 W`). If u is alone, the beam goes dark.
4. **Co-channel interference.** Beam b's radiated power reaches every co-colour victim (same satellite, other cell —
   3.12a; other satellite, any cell — 3.12b) **linearly in `p_b`**, so a power drop or a dark beam lowers each
   victim's interference by exactly `(1 − p_b'/p_b)·T[v, b]` and raises its rate. Nothing else moves: link powers are
   per-user angle recurrences, feasibility is per link, and the fading/shadowing draw is common (it is drawn per
   satellite over the union of the candidate windows, which does not depend on the action vector).
5. **Satellite baseband.** `P_BB` is charged once per satellite with at least one lit beam, so removing u removes it
   only when u was the **only served user of its satellite**.

Two consequences, both tested:

* Removing a user can only **raise** the others' rates, so `Σ_u B_u^D ≤ system bits`, and the gap is exactly the sum
  of the externalities `Σ_u Σ_{v≠u} (R_v(a_{−u}) − R_v(a))·dt` (asserted to 1e-6 relative, every step of two
  rollouts). `B_u^D` is **negative** whenever u's beam costs the co-colour victims more than u itself decodes.
* **Joules do not depend on interference or SINR at all** (the recurrence depends only on the off-axis angle): the
  same action vector evaluated under three different fading draws gives three different bit totals and *one* joule
  total, bit-for-bit. Hence `E_u^D` equals the analytic lighting price exactly.

## 3. The lighting price, and why it equals `E^D`

`E^LP_u = [supply(p_b) − supply(p_b without u) + P_cir·1{u alone on its beam} + P_BB·1{u alone on its satellite}]·dt`,
with `supply(p) = p/ξ(p)` and `supply(0) = 0`. Measured on every user-step of three rollouts (`A m=2dB`,
`A m=12dB`, random-legal, 24 users), `|E^LP − E^D| ≤ 6.3e-12 J` — against a step total of ~1.3e4 J, i.e. the
floating-point difference between "difference of two sums" and "one term". Structural zeros agree exactly: a user
below its beam's max power, or tied at it, has `E^LP = E^D = 0.0`.

So in this physics the exact difference reward's **energy** half is free: no counterfactual is needed for it. The
expensive half is `B^D`, which needs the evaluator because bits depend on interference and on the bandwidth share.

## 4. Outage: what an unserved user contributes, and the charge

An outage user (its chosen link needs more than `p_max`; `service.py`) is counted in the **pre-admission demand**
only — the next step's observation block 4 — and **not** in `U_b`, not in the beam's max power, not in activation.
Its beam radiates only if other users are on it; it decodes nothing and consumes nothing. Therefore
`bits(a) = bits(a without u)` and `joules(a) = joules(a without u)` **exactly**, and the pure difference reward
scores an outage exactly **0** — while a served action can score below 0 (a lone lit beam costs
`(supply(p⁰) + P_cir)·dt ≈ 188 J ≈ 1.56 s_E` against own bits that are often smaller). That is the "outage free
ride" CF3's Amendment 1 item 7 warned about, and it is not hypothetical here: in the tested states **52.2 %** of the
rule's own served decisions have `D = B^D − η E^D < 0` at `η = eta_0`.

**The charge (declared, in `cf_credit.outage_charge`).** For a user in outage:

* `E_out = E_max = (supply(p_max) + P_cir + P_BB)·dt = 268.353 J = 2.2248 s_E` — an upper bound on the E credit of
  **any** served action in either mode: a served link has `p ≤ p_max`, `supply` is increasing with `supply(0) = 0`,
  and one user can light at most one circuit and one baseband;
* `B_out = min(0, min over u's served legal alternatives a' (others fixed) of the mode's B credit)` — for the
  lighting price own bits are `≥ 0`, so `B_out = 0` with no evaluation at all; for the difference credit it costs one
  evaluation per legal alternative **of an outage user only**.

Then for every served legal `a'` and **every `η ≥ 0`**
`B_out − η E_out ≤ B(a') − η E(a')`, so the ordering cannot be broken by the Dinkelbach price the learner happens to
be using. Tested on 20 states that have both an outage and a served legal alternative, at
`η̃ ∈ {0, 0.5, 1, 2, 10}`, in both modes; the mutant `no_outage_charge` (charge = 0) turns that test red, i.e. the
free ride is real in those states, not a theoretical worry.

Why outages exist at all is worth recording, because it sets the cost of the charge: a **fresh** segment starts at
`p⁰ = p_max/2`, so it is always feasible; only a **continuing incumbent** whose angle has drifted more than 3 dB, or
a **step-0 warm-started** link (the segment is aged `Uniform{0..9}` steps at reset), can be infeasible. Under
`A m=2dB` outages are rare (2 of 100 users at step 0, 0–3 later); under uniform-random legal actions **75–78 of 100
users are in outage at step 0** and essentially none afterwards.

## 5. Tests and mutants

`tests/test_cf_credit.py`: 9 tests, all green on the committed tree; 13 named mutants, each turning its own test red.
Verified twice: once on the pre-commit tree (`.scratch/b1-credit/mutants.log`) and once against the engineering-core
commit itself with `git status --porcelain -- src tests` empty, recording each run's pytest **exit code**
(`mutants-63b02dc0.log`: baseline GREEN exit 0, all 13 mutants RED exit 1, 04:11–04:26 local). Trainer-level checks run `train_cf` with a batch size no
episode can fill, so `update()` returns before touching a network; every such test asserts `updates == 0` and
bit-identical weights before/after. The no-update subset of the CF3 suite (`tests/test_cf_ratio.py`, 10 tests) is
green as well; the CF3 tests that perform optimizer steps were **deliberately not run** (hard boundary).

| property (brief) | test | named mutants that turn it red |
|---|---|---|
| `equal_share` rewards and fingerprint bit-identical to CF3 on a fixed rollout | `test_equal_share_is_bit_identical_to_cf3` | `default_credit_difference`, `e_share_over_served` |
| counterfactual calls do not advance RNG or state | `test_counterfactual_calls_leave_the_trajectory_bit_identical` | `cf_live_rng`, `cf_commits_segments` |
| `E^D` = the beam's joules for a lone user (plus baseband if alone on its satellite); `E^D = 0` for a non-max user | `test_difference_energy_alone_on_beam_and_non_max_user` | `ed_supply_only`, `ed_per_link_power` |
| lighting-price `E` equals `E^D` on every user-step; joules ignore interference | `test_joules_ignore_interference_and_lighting_price_equals_difference` | `lp_no_baseband`, `lp_tie_as_max` |
| outage never scored above the worst served legal action | `test_outage_is_never_preferred_over_the_worst_served_legal_action` | `no_outage_charge` |
| non-additivity, with the documented relation | `test_difference_credit_is_not_additive_and_obeys_the_documented_relation` | `bd_own_bits` |
| the "without u" semantics themselves | `test_without_u_changes_only_bandwidth_share_and_interference_from_its_beam` | `physics_bandwidth_not_shared` |
| a pool carries its credit and the trainer checks it | `test_pool_credit_is_recorded_and_checked_by_the_trainer` | `trainer_ignores_pool_credit` |
| a pre-B1 resume state is an `equal_share` state | `test_pre_b1_resume_state_resumes_an_equal_share_learner_only` | `resume_requires_flag` |

## 6. Diagnostics (no learner): what the three credits do to a one-step argmax

Rollouts of `A m=2dB` on **2 calibration episodes** (env 9,121,000+i / mobility 9,122,000+i, i = 0,1; fresh env per
episode), **2,000 decisions** (every user-step with a non-empty mask; all had ≥ 2 legal actions), **52,815
(decision, action) pairs**. For every decision, every legal action of that user was evaluated with the other users'
rule actions fixed (common random numbers, nothing committed). `η = eta_0`, i.e. `η̃ = 1`.

| credit | argmax of `B − η̃E` differs from argmax of `B` | agrees with the unilateral system best response `argmax_a F(a_{−u}, a)` | corr(score, system contrast) pooled / within decision | median spread over the decision's served actions: `B/s_B` and `η̃E/s_E` |
|---|---|---|---|---|
| `equal_share` (CF3) | **3 / 2000 = 0.15 %** | 1048 / 2000 = 52.4 % | 0.447 / 0.434 | 1.759 and **0.0156** |
| `lighting_price` | **1787 / 2000 = 89.4 %** | 571 / 2000 = 28.6 % | 0.701 / 0.798 | 1.759 and 1.563 |
| `difference` | **866 / 2000 = 43.3 %** | **1982 / 2000 = 99.1 %** | 0.818 / **1.000** | 2.700 and 1.563 |

* The equal-share row **reproduces the CF3 review's 0-of-240 probe** under this task's own background (`A m=2dB`
  instead of `MAX_NOMINAL_GAIN`) and over 2,000 instead of 240 decisions: the energy term's action spread is
  0.0156 `s_B`-equivalents against an own-bits spread of 1.76, i.e. the energy head can move the argmax in 0.15 % of
  decisions. Under the difference credit the same term's spread is **100×** larger (1.563) and it moves 43.3 % of
  the argmaxes.
* The difference credit's within-decision correlation with the system contrast is exactly 1 (max residual
  8.9e-16): by construction `D_u(a') − D_u(a_u) = F(a_{−u}, a') − F(a_{−u}, a_u)` for served alternatives, and this
  is the numerical confirmation in this physics. The 18 decisions (0.9 %) where the difference credit's argmax
  differs from the system best response are **exactly** the 18 decisions whose system best response is an *outage*
  alternative (of 190 decisions that have one): the outage charge refuses them by design. Where the system best
  response is served, the two never differ (0 of 1982).
* The rule's own action is **not** the unilateral best response in 79.1 % of decisions — the credit is a different
  instrument from the rule it is measured on.

Distributions at the rule's own decisions (1,994 served, 6 outage; quantiles over served decisions):

| quantity | p10 | p50 | p90 | mean | notes |
|---|---|---|---|---|---|
| `B^D / s_B` | −0.185 | 0.103 | 1.997 | 0.571 | 33.2 % negative |
| `E^D / s_E` (= `η̃E^D/s_E`) | 0.0 | 0.0097 | 1.563 | 0.639 | **48.1 % exactly zero** (user not its beam's unique max-power user) |
| `D/s_B = B^D/s_B − η̃E^D/s_E` | −0.572 | −0.011 | 0.423 | — | 52.2 % negative |
| own bits `/s_B` (CF3's `B`) | 0.281 | 0.859 | 2.066 | — | |
| equal-share `E/s_E` | 0.716 | 1.020 | 1.145 | — | nearly constant across actions — that is the 0.15 % |
| outage decisions (6) | `B_out/s_B ∈ [−1.20, −0.11]`, `E_out/s_E = 2.2248` | | | | the declared charge |

Per step, `Σ_u B_u^D / system bits` = 0.21 / 0.55 / 0.70 (min / median / max over the 20 steps) and
`Σ_u E_u^D / system joules` = 0.45 / 0.64 / 0.75: the credit is **not** additive, and the documented direction
(`≤`, the gap being the externalities and the shared circuit/baseband/sub-max supply) holds at every step.

## 7. The lighting-price credit's own oracle-first screen

**Harness placebo first.** `A m=2dB`, re-rolled locally through this task's own instrumented loop on both episode
sets, reproduces the LP probe's reference rolls on `sat`: evaluation **107,000,983.53410847** bit/J (LP probe:
107,000,983.53), calibration **112,195,917.53568056** (112,195,917.54), served 0.99862 / 0.99775, lit beams
63.288 / 62.975, per-served-user rate mean / p10 / min 431.12 / 101.40 / 4.763 and 450.57 / 111.39 / 2.168 Mbit/s —
every published field identical. The local harness is the same machinery, so the cells below are comparable with the
LP grid.

**Construction** (the A-real precedent, `.scratch/h4-probe/scripts/oracle_cells.py`): at every step the reference
joint action `R` is `A m=2dB`'s action on the current state; every user simultaneously scores each legal `a` against
the others held at `R`, `score_u(a) = B_u(a | R_{−u})/s_B − η̃·E^LP_u(a | R_{−u})/s_E`, and moves iff it strictly
beats `score_u(R_u)`; all moves are committed together and the rollout is closed loop. `E^LP` is this module's
analytic marginal joules (u's own link power and feasibility per candidate come from one evaluation per candidate
index — they are per-link, so ≤ 28 evaluations give them for all users); an infeasible candidate carries the declared
outage charge `(B, E) = (0, E_max)`. Two variants of the own-bits term: **evaluator** (u's own bits in
`evaluate_actions(R with u → a)`, realised interference and bandwidth share) and **nominal**
(`(B_w/(load_a+1))·log2(1+γ_a)·dt` from u's observation). `η = eta_0` (η̃ = 1) and `η = 1.0e8` as a sensitivity.
The analytic `E^LP` was checked against the evaluator's own lighting price on every scored candidate: **max
deviation 0.0 J**.

**Cells.** Gates (controller, 18:00 UTC): pooled EE ≥ +3.3 % over `A m=2dB` on the same episodes, served ≥ 0.995,
bits ratio ≥ 0.95, p10 per-served-user rate ≥ 0.5 × the rule's.

| variant (own bits from) | η | set | n | pooled EE vs `A m=2dB` | paired per-episode (wins) | served | bits ratio | p10 ratio | lit beams | joules ratio | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **evaluator** (realised) | eta_0 | evaluation | 6 | **+24.614 %** | +25.12 ± 2.32 % (6/6) | 1.00000 | **0.867** | 0.797 | 42.7 (rule 61.8) | 0.695 | **FAIL** (bits ratio) |
| **evaluator** (realised) | 1.0e8 | evaluation | 6 | **+24.941 %** | +25.45 ± 2.45 % (6/6) | 1.00000 | **0.920** | 0.810 | 45.2 (rule 61.8) | 0.736 | **FAIL** (bits ratio) |
| nominal (observation) | eta_0 | evaluation | 24 | −7.443 % | −7.31 ± 0.48 % (0/24) | 1.00000 | 0.549 | 0.387 | 37.2 (rule 63.3) | 0.593 | **FAIL** (EE, bits, p10) |
| nominal (observation) | 1.0e8 | evaluation | 24 | −7.073 % | −6.95 ± 0.50 % (0/24) | 1.00000 | 0.551 | 0.389 | 37.3 (rule 63.3) | 0.593 | **FAIL** (EE, bits, p10) |
| nominal (observation) | eta_0 | calibration | 24 | −7.390 % | −7.28 ± 0.52 % (0/24) | 1.00000 | 0.545 | 0.377 | 36.7 (rule 63.0) | 0.588 | **FAIL** (EE, bits, p10) |
| nominal (observation) | 1.0e8 | calibration | 24 | −7.411 % | −7.35 ± 0.49 % (0/24) | 1.00000 | 0.548 | 0.380 | 36.9 (rule 63.0) | 0.592 | **FAIL** (EE, bits, p10) |

Coverage, as the controller's fallback allowed: the nominal variant on all 24 + 24 episodes, the evaluator variant on
the first 6 evaluation episodes (544–549 s and ≈ 25,400 evaluations per episode; the nominal variant costs 10–11 s
per episode). Per-served-user rate mean / p10 / min: evaluator eta_0 348.3 / 67.9 / 7.666 Mbit/s against the rule's
85.3 Mbit/s p10 on the same 6 episodes; nominal eta_0 (evaluation) 236.2 / 39.2 / 3.022 against 101.4.

**Agreement of the credit's one-step choice** (fraction of decisions; the two LP rules are computed from the same
observation, m = 0):

| cell | LP-prev(1, 0) | LP-prev(4.2, 0) | realised unilateral system-contrast argmax | nominal vs evaluator choice | moved off `A m=2dB` | picked an outage |
|---|---|---|---|---|---|---|
| evaluator, eta_0 | 0.216 | 0.190 | 0.303 | 0.282 | 0.791 | **0.0000** |
| evaluator, 1.0e8 | 0.233 | 0.200 | 0.281 | 0.248 | 0.788 | **0.0000** |
| nominal, eta_0 (eval) | 0.265 | 0.118 | — | — | 0.639 | **0.0000** |

**Readings.**

1. **The verdict is FAIL, on the bits-ratio gate for the realised variant and on everything for the deployable one.**
   With realised own bits the credit does pull the declared lever hard — 61.8 → 42.7 lit beams, joules × 0.695,
   EE +24.6 % with served 1.00000 — but it pays 13 % of the system's bits for it. It is *not* throughput-degenerate
   in the p10 sense (0.797 ≥ 0.5), so what rejects it is exactly the bits-ratio ≥ 0.95 condition (Ruling 2 §2
   scenario B / Amendment 4 §1.3) that also rejected LP-prev(2, 0) and LP-prev(3, 0).
2. **The controller's finding is confirmed directly:** LP-prev(1, 0) is not a stand-in for this credit. The credit's
   own choice agrees with LP-prev(1, 0) in only 21.6–26.5 % of decisions and with LP-prev(4.2, 0) in 11.8–20.0 %, and
   the two families land on opposite sides of the gate (LP-prev(1, 0): +6.66 %, bits 0.954, PASS; this credit:
   +24.6 %, bits 0.867, FAIL). "Lighting price passed oracle-first" cannot be inferred from the LP grid.
3. **η does not move the verdict.** Between η = eta_0 = 1.105e8 and η = 1.0e8 the gain moves +24.6 → +24.9 % and the
   bits ratio 0.867 → 0.920: still short of 0.95, and the direction says the credit would need a substantially
   *lower* price to clear the bits gate — at which point it stops consolidating beams, which is the only lever it has.
4. **The deployable version is far from the realised one.** With observation-level own bits (previous-step loads,
   pre-action γ) the same credit chooses differently in ~72–75 % of decisions and ends 7 % *below* the rule with
   0.55 of its bits: the information, not the credit, is what fails there. That is the same "credit right,
   information wrong" split Amendment 1 §3 rule 5 anticipates.
5. **The outage charge holds closed loop:** in every cell, across 48 + 12 episodes, the greedy rule picked an
   infeasible candidate **0** times, and served came out at 1.00000 against the rule's 0.99862 / 0.99775 — the
   charge (§4) is what keeps an outage from being the cheapest action once energy is priced per user.
6. **The analytic lighting price was exact everywhere it was scored:** across ≈ 1.5 M candidate scorings the analytic
   `E^LP` and the evaluator's own lighting price never differed (max deviation **0.0 J**).

Consequence for Amendment 5 Part II item 2: on this evidence the lighting-price credit has **not** passed
oracle-first, so the contingency has no admissible credit from this screen. (Per the owner's 20:10 UTC direction this
verdict does not block the development lane; the lighting-price arms there are development diagnostics.)

## 8. Cost benchmark and the projected training cost

Measured on the local host (nice 16, 1 thread, 2 concurrent processes), 100 users, `A m=2dB`:

| quantity | value |
|---|---|
| evaluations added per step by `difference` | 109 (1 base + 1 per acting user + the outage users' legal alternatives) |
| wall of one evaluation (steps ≥ 1) | **15.0 ms** |
| `difference_context` per step | **1,698 ms** mean (step 0: 2,959 ms; later steps 1,558 ms, p90 1,716 ms) |
| plain `env.step` | 310 ms |
| `lighting_price` credit per step | **3.0 ms** (no counterfactual) |
| extra wall per episode, rule-like behaviour | **17.0 s** |
| extra wall per episode, uniform-random legal actions (≈ ε = 1 exploration) | **43.7 s** (step 0 alone 25.8 s: 75–78 outage users × their legal alternatives) |

Projection for one 1000-episode CF3-scale run, with ε decaying linearly 1.0 → 0.01 over 222 episodes (the pilot's
schedule; `Σ_ep ε = 120.4`) and the per-episode cost interpolated linearly in ε between the two measured regimes:

* extra counterfactual wall ≈ **20,200 s ≈ 5.6 h per run** (local speed),
* total ≈ **6.2 h per run** against CF3 A1's ~0.56 h (2 s/episode on `sat`, alone) — **≈ 11× CF3 A1**.

Caveats, both in the conservative direction for `sat`: this host is slower than `sat` (a rule episode costs ~3.1 s of
`env.step` here against CF3 A1's 2 s/episode *including* its 10 updates), and the projection assumes the learner's
greedy behaviour has the rule's outage rate. `lighting_price` costs ~30 ms per episode — nothing.

**A cheap exact alternative exists and is already validated, but is not wired in.** Because joules are analytic and
bits change only through the bandwidth share and the co-colour interference of one beam (§2), `bits(a without u)` can
be computed for every u from the committed step's own `(U × B)` interference-term matrix in `O(U²)` arithmetic —
that is `cf_credit.without_user_rates`, which the semantics test matches against the evaluator to 1e-9 relative. The
ruling names the environment's evaluator, so the trainer uses the evaluator; if the cost above is the binding
constraint, switching the per-step path is a one-line change with a test that already compares the two.

## 9. Boundary and what was not done

* No optimizer step, no training run, no smoke training anywhere. Trainer-level tests ran with updates impossible
  and assert unchanged weights. Local only, ≤ 2 processes, `nice -n 16`, `OMP_NUM_THREADS=1`, pinned archive
  asserted in every process. `sat` untouched; the shared tree touched only under `.scratch/b1-credit/`; the cf3
  worktree untouched.
* The CF3 tests that perform optimizer steps were not run (that is why the no-update subset is reported separately).
* No pilot driver or launcher was changed: B1 training needs its own declaration, and `run_cf3_pilot.py` is CF3's.
  `generate_pool` accepts the credit and marks the pool, and the trainer refuses a mismatched pool, so a B1 pool
  generator is a thin script when it is wanted.
* Nothing here is evidence that either credit helps a learner. Amendment 1's oracle-first screen still gates B1
  training on the realised cell A-real, which another lane is measuring.
