# Exploratory local-oracle gate for EE-aligned R2/R3 Catfish roles

Status: pre-result design input for independent review. Not approved, run, or
scientific evidence.

Date: 2026-08-26

## Question

Does the current final checkpoint and action space contain reproducible,
pre-outcome, per-user R2/R3 proposal opportunities that improve both the
role-specific endpoint and immediate system EE relative to an R1-only greedy
baseline?

This is an opportunity/upper-bound screen. It does not establish that a new
reward can learn the oracle, that independently good proposals compose into a
good joint action, or that three trained roles outperform R1-only.

## Fixed carrier and claim boundary

- Evaluation only; no optimizer, replay, reward, checkpoint, or training-state
  update.
- Main trajectory is the checkpoint's per-user masked greedy Q1-only policy,
  with objective weights `(1, 0, 0)`.
- A counterfactual changes exactly one focal user's action. Every other user's
  action remains the Q1-only baseline action.
- Proposal generation uses only the current pre-decision candidate table,
  physical incumbent/previous-demand/previous-radiating state already owned by
  the environment, detached Q1 values, and an independent frozen sampling RNG.
- The proposal is generated before any current-slot physics is evaluated.
- `StepEnvironment.evaluate_actions` supplies same-state/common-RNG immediate
  physics. Only Q1-only advances the episode.
- This is not a joint optimizer, auction, message-passing scheme, or
  deployment-time coordinator. A result can justify a learnable per-user
  mechanism hypothesis only.

## Frozen inputs

- Main final checkpoint episode 8999, SHA-256
  `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`.
- Frozen evaluation seeds `2026082401` through `2026082410`.
- 100 users and 10 steps per seed.
- Five focal user IDs per step, sampled without replacement from all 100 user
  IDs using that evaluation seed's independent `action_rng`, before inspecting
  eligibility or current-slot outcomes.
- Physical action identity is `(norad_id, cell_id)`, never the relative action
  index.

## Baseline

For each state, obtain Q1-only actions by masked argmax of the existing Q1
surface. Evaluate this joint action once without mutation. It defines

```text
R0   = baseline system throughput
P0   = baseline system consumed power
eta0 = R0 / P0
```

The same action is then committed on the main trajectory. Preview and committed
reward, rate, SINR, link/beam power, interference, handovers, active beams, and
EE must match exactly at every step.

## R2 local proposal

For a focal user with a physical incumbent, enumerate valid current actions and
classify their pre-outcome handover cost from physical identity:

```text
none = 0, same satellite / different cell = phi1,
different satellite = phi2
```

If the Q1-only action is not already in the minimum-cost class, propose the
valid action with minimum handover class; ties use highest detached Q1, then
lowest action index. Record whether the proposal is exact stay or
same-satellite persistence.

The realised R2 endpoint is positive only when the focal user's realised
handover cost is lower than under Q1-only. Forced outage/re-entry and execution
infeasibility remain explicit rather than being filtered out.

The current simulator has no physical handover interruption or access energy.
For every proposal, therefore report the no-cost EE result plus the symbolic
break-even burden required for persistence to become EE-positive:

```text
g0 = Delta R - eta0 * Delta P
required_avoided_handover_equivalent_bps = max(0, -g0)
required_avoided_handover_power_w = max(0, -g0 / eta0)
```

These are thresholds, not estimates of `T_HO` or `E_HO`; no physical R2 claim
is allowed without separately sourced parameters and state sufficiency.

## R3 local proposals

R3 uses two disjoint pre-outcome physical proposal families, derived from the
previous-step beam state visible to the live policy. Each family uses highest
detached Q1, then lowest action index as its within-family tie-break.

1. `reuse_active_lower_load`: a valid action on a previously radiating beam
   whose previous demand is strictly lower than the Q1-only action's candidate
   beam demand. This is the same-active-set/load-composition hypothesis.
2. `open_inactive`: a valid action on a beam absent from the previous radiating
   set, when the Q1-only candidate maps to a beam with positive previous
   demand. This measures whether opening a spatial alternative can ever pay its
   activation cost. It is kept separate from reuse rather than pooled.

The realised R3 endpoint is the reduction in system load concentration:

```text
Delta_load_relief = sum_b U0_b^2 - sum_b Ualt_b^2
```

The proposal is role-positive only when `Delta_load_relief > 0`; outcome-based
filtering is used only for analysis, never for proposal generation.

## Exact local EE certificate

For every alternative:

```text
Delta R  = Ralt - R0
Delta P  = Palt - P0
g_eta    = Delta R - eta0 * Delta P
Delta EE = Ralt / Palt - R0 / P0
```

With positive `P0` and `Palt`, the identity is

```text
Delta EE = g_eta / Palt
```

The probe fails if the signs differ or the numeric identity exceeds a frozen
floating-point tolerance. `g_eta` is an oracle label under exact current-slot
physics, not a deployable pre-outcome feature. A future reward/proposal model
must predict it from state; it cannot observe it before acting.

## Pre-result decision rules

Engineering validity requires all of the following:

- checkpoint, status, preregistration, dependency, and frozen-TLE provenance
  checks pass;
- main environment and RNG parity pass at every baseline step;
- `Delta EE = g_eta / Palt` passes for every alternative;
- each proposal changes exactly one physical user action.

Opportunity findings are descriptive at the sampled-state level and paired at
the seed level. A proposal family is retained for reward-design work only if:

- it yields at least 30 eligible realised proposals overall;
- role-positive proposals occur in at least 8 of 10 seeds; and
- role-positive plus EE-positive proposals are at least 10% of eligible
  proposals and occur in at least 8 of 10 seeds.

Failure means the family is dropped or redesigned before any training. Passing
means only that a non-trivial learnable target may exist. It does not authorize
reward freezing or training.

R2 has an additional ceiling: failure under the no-cost current physics does
not settle a physical R2-v2 role. It instead reports the paired distribution of
the required avoided-handover equivalent burden; a separate parameter/source
gate decides whether those thresholds are physically plausible.

## Outputs

- R1-only seed-level EE, throughput, power, service, active beams, and
  handovers.
- Per proposal: seed, step, focal user, proposal family, baseline/alternative
  physical action, Q1 values, previous load/active status, realised
  handover/load endpoint, `Delta R`, `Delta P`, `g_eta`, `Delta EE`, and R2
  break-even thresholds.
- Family-level eligibility, role-positive, EE-positive, jointly positive,
  sign-parity, and per-seed coverage.
- Explicit statement that individually beneficial local proposals have not
  been composed or trained.

## Checkable completion criterion

One command produces a receipt over all ten frozen seeds in which every
baseline parity and `g_eta` identity check passes, and either retains or rejects
each R2/R3 proposal family under the rules above without launching training.
