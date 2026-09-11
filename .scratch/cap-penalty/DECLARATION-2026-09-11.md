# CAPPENALTY — declarations fixed before any run

Written 2026-09-11, before the cap was implemented and before any CAP3 arm was
launched. No CAP3 number exists at the time of writing. Nothing below may be
revised after a number is seen; any later deviation is added as a dated
addendum, never as an edit.

## 1. The mechanism being added is a physics change

A per-satellite cap on simultaneously active beams, k = 3, **defines a
different MDP**. It is not a training trick and not a regulariser: it changes
which users are served, the load `U_{s,v}`, the radiating set, interference,
system power and every reward. Any number from a capped cell answers a question
about a different system from the one this project's rulings define.

This project removed the cap by ruling (`RULING-2026-08-22-no-beam-count-cap.md`
in the sibling repo's `docs/`; enforced here by
`tests/test_ruling_no_beam_count_cap.py`; recorded at
`src/mcrl/env/action_contract.py:60-64`). The ruling's reasons, from
`tests/test_ruling_no_beam_count_cap.py:1-22` and
`docs/R3-AND-EXECUTION-MASK-NOTES.md` §6:
1. Sun-2024's `V = 7` is the size of a non-spatial load-channel set; the paper's
   `Σ_v z_{s,v} = V` is an identity, not a bound. The cap was the old repo's invention.
2. With pointing and footprints, beams must cover ground; 7 cells reach a third
   of the service area at 550 km and a fifth at 485 km.
3. A ceiling must darken beams; darkening by demand rank was measured to starve
   68/100 users and invert the congestion incentive.
4. It fights `r3 = −U_{b_u}`: the reward pushes users to quiet beams, demand-ranked
   darkening extinguishes quiet beams first.
5. Enforcing it in the decision mask would make the mask depend on the joint
   action and break the per-user independent argmax that defines the B1 baseline.

## 2. Implementation choices, declared

- **Where.** Ruling §7.1–7.2 forbids the cap *and any socket for it* in the live
  tree, and `test_no_module_defines_a_beam_count_ceiling` scans `src/mcrl` for
  it. Adding the flag inside `src/` would violate a standing ruling and break a
  gate test. **So the flag lives outside `src/`**, in
  `.scratch/cap-penalty/beam_cap.py`: a `StepEnvironment` subclass whose only
  change is to post-process the service resolution when a cap is set. It is
  still the environment layer (it wraps `resolve_service` at
  `src/mcrl/env/step.py:822`), it touches nothing in
  `src/mcrl/algorithms/modqn.py`, and the live tree stays ruling-compliant.
  This is a deviation from the brief's "in the environment/action-mask layer"
  only in file location, declared here.
- **Off by default.** `beam_cap=None` calls the unmodified parent method. A test
  proves bit-identity with the plain environment (outcomes and trained weights).
- **Rule: post-execution darkening, copied from the sibling.** Per satellite
  (`norad_id`), rank that satellite's beams by eligible (post-feasibility) load,
  descending, ties by lower `cell_id`, keep the top k = 3, darken the rest.
  Source: sibling `src/modqn_paper_reproduction/env/family_b_step.py:834-844`
  (`order = sorted(..., key=lambda c: (-eligible_demand[l, c], c));
  active[l, order[:k_cap]] = True`) and `:1039` (only users on an active beam
  are served). **Not in the mask**, for reason 5 above, and because the sibling
  did not put it there either.
- **Darkened users** are unserved for that step: no load, no power, no rate, not
  in the radiating set, `r3 = 0`, the handover ledger records UNSERVED. Their
  pre-admission demand stays in `demand_by_beam`, so observation block 4 still
  shows the darkened beam's true demand, exactly as the sibling's M-05 comment
  requires (`family_b_step.py:851-853`). They are flagged in a separate
  `cap_darkened` field, **not** folded into `outage_infeasible`, so the physical
  outage rate stays readable.
- **Per satellite, not per window slot.** The sibling ranked per window-slot `l`
  (its four window satellites are shared by all users). Here each user's four
  slots can be different satellites, so the physical unit is the `norad_id`.

## 3. Arms (500 episodes each, one process each, detached)

| arm | env | penalty |
|---|---|---|
| `CAP3_OFF` | cap k = 3 | `PenaltyConfig(diagnostics=True)`, kind none |
| `CAP3_PENALTY` | cap k = 3 | `TB-SRANK-kumar`, α = 1e-3, diagnostics on |

Seeds (train 42, env 1337, mobility 7), learning rate 1e-3, checkpoint every
100 episodes — identical to PENALTYARM. Tree: PENALTYARM's server snapshot
(`5219995a` + its penalty port), copied unchanged, plus the cap module and the
driver/eval scripts. PENALTYARM's `OFF` and `PENALTY` are the no-cap cells and
are **not rerun**.

## 4. Readouts

- **Primary representation readout:** `srank_δ` per head (δ = 0.01, mean-centred
  Φ over the 128-sample TD minibatch, read-only) — the estimator PENALTYARM
  logged, taken from the per-episode logs of all four arms.
- **Secondary representation readout (added here, declared now):** the same
  estimator on a **common probe set** — states from the no-cap OFF checkpoint's
  greedy rollouts — evaluated through every checkpoint's network. This separates
  "the network lost rank" from "the cap changed the input distribution".
- G-3 four (`active_beam_count` = distinct action slots, `argmax_agreement`,
  normalised `q_margin`, `q_entropy`) at greedy evaluation for all four cells;
  training-time G-3 for the two new arms.
- Greedy pooled EE as a ratio of sums, bits and joules separately, served
  fraction, handover rate, mean physically active beams, cap-darkened user
  fraction. Harness: PENALTYARM's `eval_pooled_ee.py`, extended; fresh env per
  cell; 24 episodes; capped cells evaluated in the capped env.
- Descriptive cross-cells (evaluation only, no training): OFF's checkpoint run
  in the capped env, and CAP3_OFF's checkpoint run in the uncapped env, to
  separate "the cap's physics" from "training under the cap".

## 5. Operational definitions and declared reading

Reference values from PENALTYARM (OFF, ep 401–500 `srank_δ`): 40.77 / 40.35 /
41.54; arm-to-arm spread in that study up to ~3 units.

- **Rank collapse in `CAP3_OFF`** := on at least one head, the ep 401–500 mean
  `srank_δ` is ≤ 30 (≥ ~25% below OFF's ~40, i.e. more than 3× the arm-to-arm
  spread seen in PENALTYARM). Between 30 and 36 is **ambiguous** and reported as
  such. ≥ 36 on all heads is **no collapse**.
- **Penalty holds rank** := on every head that collapsed in `CAP3_OFF`,
  `CAP3_PENALTY`'s ep 401–500 mean `srank_δ` is ≥ 36.

Branches:
- **`CAP3_OFF` no collapse** → the cap does not create the penalty's target in
  this physics; the owner's hypothesis is not the explanation here. Report, stop.
- **`CAP3_OFF` collapses, `CAP3_PENALTY` holds** → premise established here at the
  representation level. Report whether pooled EE follows, **without** claiming
  an EE effect from one seed at 500 episodes; state the seed count and
  CPU-hours a resolvable test needs; the owner decides.
- **`CAP3_OFF` collapses, penalty does not hold** → report that plainly.
- **Ambiguous** → report as ambiguous; the common-probe readout and G-3 are
  shown, but do not decide the branch.

Separately, `CAP3_OFF` vs `OFF` pooled EE is reported as an **observation** at one
seed, not a claim.

**500 episodes is not convergence.** The frozen reference is 9,000 episodes;
ε is still ~0.75 at episode 500. No number here is compared with a 9,000-episode
checkpoint.

## 6. Re-run rule

Only a surprise triggers a re-run, at larger n, reported as a re-run. An
inconvenient number, a missing separation or a wrong sign is not a surprise. No
coefficient sweep, no cap-value sweep, no extra training arm.
