# Frozen pilot: local opportunity gate for EE-aligned R2/R3 Catfish roles

Status: frozen before numerical results. Evaluation-only prototype; not a
reward freeze, training authorization, or scientific completion claim.

Date: 2026-08-26

## Decision question

Does the final full-policy checkpoint contain reproducible, pre-outcome,
single-user R2/R3 proposal opportunities that improve a role-specific endpoint
and immediate system EE relative to the checkpoint's Q1-only greedy
**projection**?

This is an opportunity screen. It does not establish that a reward can learn
the oracle label, that separately useful proposals compose into a good joint
action, or that a separately trained R1-only policy would behave like this
projection.

## Fixed boundary

- Evaluation only. No optimizer, replay, reward, checkpoint, or training-state
  update.
- The reference action is the checkpoint's per-user masked greedy Q1 surface,
  evaluated with objective weights `(1, 0, 0)`.
- A counterfactual changes exactly one focal user's **physical** action. All
  other users retain their reference action.
- Proposal generation sees only pre-decision state: masks, slot tables,
  candidate SINR, prior realised association, prior demand encoded in
  `beam_loads`, detached Q1 values, the reference physical intent set, and an
  independent frozen focal-sampling RNG.
- Proposal generation cannot inspect current-slot counterfactual physics.
- `StepEnvironment.evaluate_actions` supplies same-state/common-RNG immediate
  physics. Only the Q1 projection advances the episode.
- This is not a joint optimizer, auction, coordination layer, message-passing
  scheme, or deployment-time outcome search.

## Provenance and frozen populations

- Main final checkpoint episode 8999, expected SHA-256
  `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`.
- Frozen evaluation seeds `2026082401` through `2026082410`.
- 100 users and 10 steps per seed.
- Physical action identity is `(norad_id, cell_id)`, never a relative action
  index.
- Before checking role eligibility, draw focal user IDs without replacement
  from `range(100)` with the evaluation seed's independent `action_rng`.
  Never replace an ineligible focal user with another draw.

Two stages are kept separate:

1. Local engineering pilot: first frozen seed, 10 steps, `K=2` focal users per
   step. It can falsify code/parity/proposal viability but cannot retain a
   role.
2. Confirmation: all ten frozen seeds, 10 steps, `K=10` focal users per step.
   It is a long matched evaluation and is routed to the Ubuntu server after
   the local pilot passes.

## Q1-only projection reference

For each state, obtain reference actions by masked argmax of the existing Q1
surface. Evaluate this joint action once without mutation:

```text
R0   = reference system throughput
P0   = reference system consumed power
eta0 = R0 / P0
```

The same action is then committed to advance the sole trajectory. Preview and
committed reward, rate, SINR, link/beam power, interference, handovers, active
beams, and EE must match exactly at every step.

## Canonical R2 proposals

R2 is undefined at episode start and after a realised `UNSERVED` state. Such
focal rows are `NA`, not zero-cost incumbents. For a physical incumbent:

1. `r2_exact_stay`: eligible only when the incumbent `(NORAD, cell)` is a
   valid current candidate and the Q1 reference selects a different physical
   key. The incumbent action is unique.
2. `r2_same_satellite`: eligible only when the Q1 reference changes NORAD and
   at least one valid non-incumbent action retains the incumbent NORAD. Select
   the candidate with greatest pre-decision candidate SINR; break ties by
   physical `(NORAD, cell)` and then action index.

Neither family uses a counterfactual result to select a candidate. Duplicate
relative actions mapping to one physical key are de-duplicated before the
tie-break. The realised role endpoint is positive only when the focal user's
realised handover class has lower cost than under the Q1 reference. Outage,
re-entry, and execution infeasibility remain in the receipt.

The simulator has no physical handover interruption duration or access energy.
Consequently R2's immediate EE is `DIAGNOSTIC_ONLY / UNIDENTIFIED` as a full
handover benefit. Report the no-cost local certificate and symbolic burden:

```text
g0 = Delta R - eta0 * Delta P
required_avoided_handover_equivalent_bps = max(0, -g0)
required_avoided_handover_power_w = max(0, -g0 / eta0)
```

These thresholds are not estimates of `T_HO` or `E_HO`. R2 cannot be frozen as
an EE Catfish until a separate physical-parameter and state-sufficiency gate is
passed.

## Canonical activation-aware R3 proposals

Let `B0` be the set of physical keys selected by all Q1 reference actions and
`B_minus_u` the keys selected by all reference users except focal user `u`.
These are **intended** beam sets, not realised radiating sets.

1. `r3_reuse_intended`: a valid focal candidate different from the reference
   key and contained in `B_minus_u`. It does not add an intended beam.
2. `r3_open_new_intent`: a valid focal candidate different from the reference
   key and absent from `B0`. It adds one intended beam.

Within either family, choose the smallest prior-demand value from the focal
state's `beam_loads`, then greatest pre-decision candidate SINR, then physical
`(NORAD, cell)`, then action index. Duplicate physical keys are de-duplicated
before this tie-break. No result-dependent maximisation is allowed in the gate;
an optional best-outcome envelope must be labelled oracle-only and cannot
support role retention.

For both families, record intended and realised active-set changes separately.
`r3_open_new_intent` counts as a realised opening only if the alternative's
eligible active-beam set contains the proposed key and the reference set does
not. The realised load endpoint is

```text
Delta_load_relief = sum_b U0_b^2 - sum_b Ualt_b^2
```

An R3 row is role-positive only when `Delta_load_relief > 0`. Across every
family, a jointly useful opportunity requires the role endpoint and EE
certificate to be positive, the focal user to remain served, and the total
served-user count not to decrease. This prevents an outage from looking like a
successful R2 persistence merely because an unserved action carries no
handover charge.

## Exact local EE certificate

For every eligible alternative:

```text
Delta R  = Ralt - R0
Delta P  = Palt - P0
g_eta    = Delta R - eta0 * Delta P
Delta EE = Ralt / Palt - R0 / P0
```

For positive `P0` and `Palt`:

```text
Delta EE = g_eta / Palt
```

The runner fails if the signs differ or the identity exceeds the frozen
floating-point tolerance `max(1e-9, 1e-10 * max(abs(Delta EE), 1))` in raw
`bit/J` units. `g_eta` is a current-slot oracle label, never a deployable
pre-outcome feature.

## Required row fields

Each eligible/no-op/NA row records seed, step, focal user, family, eligibility
reason, reference and proposed action indices and physical keys, Q1 values,
prior association, prior demand, candidate SINR, intended beam-set relation,
realised active-beam sets, service/outage, focal and other-user rate changes,
active satellites, effective beams, `sum U_b^2`, mean/max load, handover class,
`Delta R`, `Delta P`, `g_eta`, `Delta EE`, identity residual, and R2 symbolic
break-even quantities.

## Gates and claim ceiling

Engineering validity requires provenance checks, baseline preview/commit
parity at every step, exact common-RNG identity checks, and exactly one changed
physical focal action per eligible proposal.

The local pilot passes only engineering validity and produces descriptive
counts. It cannot retain or reject a scientific role.

Confirmation uses seed as the independent paired unit; focal users and steps
are clustered observations, not independent replicates. A family advances to
reward-design work only when it has at least 30 eligible proposals, jointly
positive opportunities in at least 8 of 10 seeds, and a jointly positive
fraction of at least 10% across eligible proposals. These are precommitted
engineering opportunity thresholds, not a causal-effect significance test.

For R2, passing those descriptive thresholds advances only to physical
handover parameterisation; it does not freeze an EE reward. For R3, passing
advances only to a learnability test. Any role that fails is dropped or
redesigned before training.

Even a passing family supports only: "pre-outcome canonical local proposals
with jointly role-positive and immediate-EE-positive opportunities exist in
the sampled Q1-projection states." It does not support composability, trained
policy gain, independent R1-only superiority, or multi-Catfish completion.

## Checkable completion criteria

- One local command produces the one-seed pilot receipt without training and
  passes every engineering trip-wire.
- After that pass, one server command produces the ten-seed confirmation
  receipt and applies the frozen opportunity rules without changing this
  specification.
