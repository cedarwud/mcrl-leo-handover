# B1-CREDIT — implement the difference-reward credit for the ratio learner (engineering lane; NO training)

Keep `/home/u24/papers/mcrl-leo-handover/.scratch/b1-credit/PROGRESS.md` updated after every step (files touched, tests
run, benchmarks, what is next) so an interruption resumes at the first incomplete step. Never pre-fill a result.

## Why

`.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-RULING-CEILING-PARITY-B-CHAIN-AND-CATFISH-COUNT-2026-09-11.md`
§3 stage **B1** replaces the pilot's equal-share energy label `E_u = P_sys·dt/U` with a **difference reward** computed by
the environment's own counterfactual evaluator. Its Amendment 1 (oracle-first screen) says B1 may only **train** after the
realised oracle cell A-real beats the rule; another agent is measuring A-real now. This task prepares the code so B1 can
start the moment A-real passes. If A-real fails, this code is shelved — that is accepted. Read the ruling and both
amendments (`…-AMENDMENT-1-ORACLE-FIRST-SCREEN-…`, `…-AMENDMENT-2-SCENARIO-A-BRANCH-…`) first.

## Hard boundary (Ruling 2 §5)

**No optimizer step, no training run, no "smoke training", no learner update of any kind.** Allowed: code, unit tests on
fixed data, rollouts of non-learned rules, counterfactual evaluations, benchmarks. Local compute only: ≤ 2 processes,
`nice -n 16`, `OMP_NUM_THREADS=1`, python `/home/u24/papers/mcrl-leo-handover/.venv/bin/python`,
`MCRL_TLE_ROOT=/home/u24/mcrl-runtime/tle-pinned-427e6a91` (assert file_set sha256 `427e6a91…8fe9`). Do not touch `sat`.
Do not read `.scratch/validity-audit/`, `.scratch/ee-ceiling/` results, `.scratch/reviews/`.

## Setup

Create a new worktree: `git -C /home/u24/papers/mcrl-leo-handover worktree add /home/u24/papers/mcrl-leo-handover-b1 -b b1/difference-reward-20260912 102b2d4d`
(`102b2d4d` = tip of `cf3/pilot-20260911`, which carries `cf_ratio.py`, `cf_sources.py`, the pilot scripts and tests). Do not
modify the shared tree `/home/u24/papers/mcrl-leo-handover` (except `.scratch/b1-credit/`) or the cf3 worktree (other agents
read it). Commit only on the new branch, named paths only.

## Read first (the code is the ground truth)

`src/mcrl/algorithms/cf_ratio.py` (reward matrix `cf_reward_matrix`, B/E/H heads, units `s_B`/`s_E`, shared-continuation
targets, settings/fingerprint), `src/mcrl/env/step.py` (`evaluate_actions`, `evaluate_actions_without_user`,
`_evaluate_selected_actions`, `_resolve_physics`, served/outage, handover classes), `src/mcrl/env/link_budget.py`
(`beam_power_w`, `supply_power_w`, `fixed_power_w`, `system_power_w`, `link_rate_bps`; the per-beam `max` aggregation;
bandwidth `B_w/U_b` sharing), `scripts/cf3_de_diag.py` (the counterfactual pattern already used once),
`tests/test_cf_ratio.py` (test style and the named-mutant convention), `.scratch/cf3-pilot/DECLARATION-ADDENDUM.md`
(§Learner: units, targets).

## Build

A new module `src/mcrl/algorithms/cf_credit.py` and a settings flag `credit_mode ∈ {equal_share (default), difference,
lighting_price}` on the ratio learner. **`equal_share` must stay bit-identical to CF3** (same rewards, same fingerprint
fields apart from the new flag's default).

1. **`difference`**: per user-step, `B_u^D = bits(a) − bits(a without u)` and `E_u^D = joules(a) − joules(a without u)`,
   both from the environment's counterfactual evaluator with common random numbers (no state committed), `H` unchanged.
   Establish by reading and by test what "without u" does to the others (bandwidth share `U_b`, co-channel interference if
   u's beam goes dark, per-beam `max` power if u was the beam's max-power user, satellite baseband if u was alone on its
   satellite) and document it. **Explicit outage charge**: establish what an unserved user contributes (does its beam
   radiate? does it count in `U_b`?) and define the charge so that, in every tested state, an outage is never scored above
   the worst served legal action (the "outage free ride" the pilot's Amendment 1 item 7 warned about). Document the choice.
2. **`lighting_price`** (cheap, no counterfactual): `B_u` = own bits (as CF3); `E_u` = u's marginal joules computed
   analytically from the power model (beam supply power change if u is the beam's max-power user, circuit power if u is
   alone on the beam, baseband if u is alone on the satellite). Establish whether joules depend on interference at all
   (if not, `E^D` from mode 1 must equal this analytic value — test it). Note: the LP(c, m) rule family measured by the
   LP probe is the greedy version of this credit.

## Tests (fail-then-pass; each property with a named mutant that turns it red, as in `test_cf_ratio.py`)

- `equal_share` rewards and fingerprint bit-identical to CF3 on a fixed rollout.
- Counterfactual calls do not advance RNG or state: a trajectory with and without the calls is bit-identical.
- For a user alone on its beam, `E^D` equals that beam's joules (plus baseband if alone on its satellite) within 1e-9
  relative; for a user that is not its shared beam's max-power user, `E^D = 0`.
- `lighting_price` `E` equals `difference` `E^D` on every user-step of a fixed rollout (if joules are interference-free).
- Outage is never preferred over the worst served legal action in any tested state.
- Non-additivity documented: `Σ_u B_u^D ≠ system bits` in general (test asserts the documented relation, not equality).

## Diagnostics (no learner; rollouts of `A m=2dB` only)

On 2 calibration episodes (env `9_121_000+i`, mobility `9_122_000+i`, fresh env per episode; rules from `cf_sources.py`),
for every decision: the distributions of `B^D/s_B`, `E^D/s_E`, `η̃·E^D/s_E` (η̃ = 1 at `eta_0`), and **the fraction of
decisions whose one-step argmax of `B^D − η·E^D` differs from the argmax of `B^D` alone** — the analogue, under the new
credit, of the CF3 review's 0-of-240 probe of the equal-share credit (compute the per-action contrasts by evaluating each
legal action for the user with the others fixed). Also: the correlation between `B^D − η·E^D` and the user's unilateral
system contrast `F(a_{−u}, a) − F(a_{−u}, a_u)`. **Cost benchmark**: ms per step for `difference` mode (≈ one extra
counterfactual per user per step), projected wall per episode and per 1000-episode run (CF3 A1 ran ~2 s/episode alone).

## Report

`.scratch/b1-credit/B1-CREDIT-IMPLEMENTATION-2026-09-12.md`: first line one bold sentence — tests green / mutants red, the
argmax-change fraction under the difference credit vs 0/240 under equal share, and the projected training cost per run;
then what "without u" means in this physics, the outage-charge choice, the diagnostics, the benchmark, and the commit.
Return the first line.
