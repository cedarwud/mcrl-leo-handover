# Frozen state-observable gate for deployable R2/R3 Catfish proposals

Status: frozen before this gate's numerical results. Evaluation only; no reward
freeze, training, joint optimizer, auction, or deployment-time coordinator.

Date: 2026-08-26

## Question

Do canonical proposals built only from one user's live observation contain
reproducible role-positive and immediate-EE-positive opportunities relative to
the full checkpoint's Q1-only projection?

This gate follows the v1 physics-opportunity screen. It removes the v1 R3
proposal's access to other users' simultaneous Q1 reference actions (`B0` and
`B_minus_u`). Passing is necessary for a deployable per-user Catfish hypothesis
but is not evidence that a Q head can learn the opportunity or that proposals
compose.

## Frozen inputs and common reference

- Same episode-8999 checkpoint and SHA-256 as v1:
  `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`.
- Same ten evaluation seeds `2026082401` through `2026082410`, 100 users, 10
  steps, and data-blind `K=10` focal draws per step.
- Same masked Q1-only projection `(1, 0, 0)`, one-focal-user counterfactual,
  common-start-RNG `evaluate_actions`, and baseline-only trajectory.
- Same EE identity and tolerance:
  `Delta EE = (Delta R - eta0 Delta P) / Palt`.
- Proposal lists are fully built before any current-slot action evaluation.

## Allowed proposal inputs

For focal user `u`, proposal generation may read only:

- that user's current `access_vector`, `beam_loads`, candidate SINR, action
  mask, and slot table;
- that user's detached Q1 row only to obtain its Q1 reference action;
- deterministic action-index tie-breaking; and
- the independent frozen focal-sampling RNG.

It may not read any other user's state, action, Q value, current intent, or a
current-slot `ActionEvaluation`. Physical keys are used only to de-duplicate
relative actions and verify the counterfactual; they do not rank proposals.

## State-observable proposal families

### R2: `r2_access_exact_stay`

The current `access_vector` must contain exactly one incumbent action and that
action must remain valid. If the focal Q1 reference chooses a different
physical key, propose the observed incumbent action. Otherwise the family is
ineligible/no-op.

The all-zero access-vector case cannot identify an incumbent satellite. A
same-satellite/different-cell persistence proposal is therefore deliberately
excluded from this state-only gate. The v1 physical opportunity for that case
requires a separate state-extension decision, such as a minimal incumbent-slot
indicator; it cannot be credited to the current state.

R2 remains `DIAGNOSTIC_ONLY / UNIDENTIFIED` without physical `T_HO/E_HO`.

### R3: `r3_prev_inactive_split`

Among valid physical candidates different from the focal Q1 reference, keep
only actions whose observed previous demand is exactly zero. Choose greatest
candidate SINR, then lowest action index.

This is a state-observable split/open hypothesis, not a guarantee that the beam
is absent from other users' simultaneous actions. Its topology endpoint is
positive only if the realised alternative both activates the proposed key and
increases effective beam count by exactly one relative to the Q1 reference.

### R3: `r3_prev_active_lower_load`

Let `N_ref` be the observed previous demand at the focal Q1 reference action.
Among valid physical candidates different from the reference, keep only those
with `0 < N_candidate < N_ref`. Choose smallest previous demand, then greatest
candidate SINR, then lowest action index.

This is a state-observable reuse hypothesis. Its topology endpoint is positive
only if the alternative adds no realised active beam relative to the Q1
reference.

For both R3 families the load endpoint remains

```text
Delta_load_relief = sum_b U0_b^2 - sum_b Ualt_b^2 > 0.
```

## Joint opportunity labels

- `r2_access_exact_stay`: lower realised handover cost, positive `g_eta`,
  focal user served, and total served count not lower.
- `r3_prev_inactive_split`: positive topology endpoint, positive load relief,
  positive `g_eta`, focal user served, and total served count not lower.
- `r3_prev_active_lower_load`: positive topology endpoint, positive load
  relief, positive `g_eta`, focal user served, and total served count not lower.

These are discarded post-action labels for evaluation. Proposal generation
cannot observe them.

## Frozen opportunity rule

Use evaluation seed as the independent unit. A family advances only if it has
at least 30 eligible proposals, joint opportunities in at least 8 of 10 seeds,
and a joint-opportunity fraction of at least 10% of eligible proposals.

- R2 passing advances only to physical handover parameterisation and a minimal
  state-sufficiency decision.
- R3 passing advances only to a held-out learnability test using live state
  features. It does not authorize RL training.
- Failure means drop or redesign before training. A result within one
  percentage point of 10% is reported as borderline but does not pass.

## Required receipt fields

In addition to v1 provenance/parity fields, every evaluated row records the
allowed focal observation values used for selection, absolute reference and
alternative focal rates, other-user aggregate rate change, absolute and delta
system throughput/power/EE, intended and realised active-set changes for
diagnosis only, role/topology/service labels, and the exact EE certificate.

## Claim ceiling

Passing supports only: "a deterministic proposal using the current focal-user
observation produced non-trivial, cross-seed local opportunities under exact
immediate physics." It does not prove prediction accuracy, long-horizon gain,
joint composability, trained policy improvement, or a completed multi-Catfish
mechanism.
