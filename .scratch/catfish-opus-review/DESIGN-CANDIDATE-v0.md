# Three-role Catfish design candidate v0

Status: review input only; not approved, implemented, or scientifically validated.
Date: 2026-08-26

## Goal

Design three independently testable, training-time Catfish roles aligned with
the three existing MODQN objectives.  The design must add a mechanism beyond
the current exploration and ACRM carriers, while excluding post-training
auction, coordination, deployment-time action override, and reward rewriting.

"Independent" means separate responsibility, trigger, intervention state,
Q-head update path, ablation, and direct endpoint.  It does not mean the three
physical outcomes are causally non-interacting.

## Host facts that constrain the design

- The host has three parallel Q networks and three per-objective optimizers.
- The current trainer stores one three-reward transition in one uniform replay
  buffer, samples one batch, and uses that batch to update all three heads.
- Action selection scalarises the three Q surfaces with weights
  `(0.5, 0.3, 0.2)`; the weights do not enter the individual TD targets.
- R1 is each user's additive contribution to system EE.
- R2 is exactly `0`, `-phi1`, or `-phi2`, using realised physical association
  identity.  It is numerically active, but the completed run does not establish
  superior handover control.
- R3 is negative realised eligible load on the user's physical beam.  Load
  spreading may also affect R1 through rate and therefore is not causally
  orthogonal to R1.
- Repaired checkpoint diagnostics show Q-only sharpening with action and
  physical-beam dispersion, not joint collapse.  Collapse is therefore not an
  admissible design authority for this candidate.
- `active_action_slot_count` is not a physical beam count.  Physical R3 evidence
  must preserve `(satellite_id, local_beam_index)` identity.

## Proposed seam

Keep the existing uniform replay/update path as the baseline path.  Add one
training-only module at the replay/update seam:

```text
observe DecisionFrame
  -> three isolated Specialist proposals
  -> validate provenance and fixed safety limits
  -> admit to B1, B2, or B3

base batch -> unchanged full-vector MODQN update
B1 batch   -> auxiliary Q1-only update
B2 batch   -> auxiliary Q2-only update
B3 batch   -> auxiliary Q3-only update
```

The external interface should remain small:

```text
observe(frame: DecisionFrame) -> tuple[Admission, ...]
sample(role: R1 | R2 | R3, n: int, rng) -> SpecialistBatch
```

`DecisionFrame` contains immutable state/action masks, executed joint action,
raw and calibrated reward vectors, the three detached Q surfaces, physical
association/load metadata, source transition ID, and environment/RNG
provenance.  An `Admission` records role, source transition ID, own-objective
gain, two cross-objective costs, trigger reason, and provenance.  Invalid or
unknown provenance fails closed.

The baseline batch continues to update all three heads exactly once.  A
specialist batch contributes an auxiliary loss only to its matching head:

```text
L_i = L_i_base + lambda_i * L_i_specialist
```

The three banks use precommitted fixed quotas.  They do not share rankings,
messages, auctions, or dynamic quota negotiation.  No Catfish code executes in
deployment evaluation.

## Candidate regret and admission rule

For valid actions `A(s)`, candidate objective regret is:

```text
g_i(s, a_exec) =
  (max_{a in A(s)} Q_i(s,a) - Q_i(s,a_exec)) /
  max(max(Q_i(valid)) - min(Q_i(valid)), epsilon)
```

If a verified alternative transition is available, its realised own-objective
gain is:

```text
Delta_i = r_i(counterfactual) - r_i(executed)
```

Admission to `B_i` requires a role-specific trigger, positive own-objective
evidence, and precommitted cross-objective harm limits:

```text
Delta_i > tau_i
Delta_j >= -B[i,j] for each j != i
```

The formula, normalisation, thresholds, budgets, and whether one-step immediate
gain is scientifically sufficient are deliberately unresolved review targets.
Unknown cross-objective cost is not treated as zero.

## Three proposed roles

### R1 Energy-Frontier Scout

- Responsibility: expose under-sampled valid actions with higher R1/system EE.
- Primary trigger: positive R1 regret or verified positive `Delta_1`.
- Proposal: the valid R1-favoured action, subject to service and cross-objective
  harm limits.
- Intervention: admit the verified transition to `B1`; auxiliary update is
  Q1-only.
- Forbidden overlap: R2 handover class and R3 physical load cannot be primary
  admission triggers and cannot change the Q2/Q3 targets.
- Direct endpoint: paired-seed episode-mean system EE in bits/J.

### R2 Handover-Persistence Scout

- Responsibility: teach the handover head to distinguish avoidable switching
  from stable physical-association continuation.
- Primary trigger: incumbent remains eligible while the executed/proposed action
  produces `phi1` or `phi2`, or a verified alternative reduces that penalty.
- Proposal: stay on the incumbent physical association when eligible, otherwise
  use an R2-favoured valid action.  Forced handover and re-entry remain separately
  labelled rather than being silently counted as optional switching.
- Intervention: admit balanced stable/phi1/phi2 contrast transitions to `B2`;
  auxiliary update is Q2-only.
- Forbidden overlap: beam load and EE cannot be primary admission triggers; the
  role cannot alter dwell rules or execute a deployment-time handover.
- Direct endpoint: `phi1 + phi2` incidence per user-decision, with optional,
  forced, served-to-served, and re-entry strata reported separately.

### R3 Physical-Load-Relief Scout

- Responsibility: expose valid associations that reduce realised physical-beam
  concentration.
- Primary trigger: high eligible load/max physical-beam share plus positive R3
  regret or verified positive `Delta_3`.
- Proposal: an eligible lower-load physical beam or R3-favoured valid action,
  with exact action-to-physical-beam provenance.
- Intervention: admit the verified transition to `B3`; auxiliary update is
  Q3-only.
- Forbidden overlap: action-slot diversity is diagnostic only; the role cannot
  use it as physical-load evidence or force a deployment-time top-k action.
- Direct endpoint: raw R3 and maximum physical-beam load share, supported by
  effective physical beams and service fraction.

## Two implementation variants requiring review

1. **Verified one-step branch:** clone the complete environment and RNG state,
   execute a role-proposed joint action in the clone, record the resulting
   transition, then prove the main trajectory is unchanged.  This provides
   realised counterfactual rewards but may be invalid or expensive in the
   coupled multi-user environment.
2. **Real-transition-only admission:** never create a branch.  Use only executed
   exploration transitions and role-specific TD surprise/metadata to admit
   samples.  This is safer but may reduce to ordinary multi-objective
   prioritised replay and may not justify a distinct Catfish contribution.

The review should recommend one, propose a defensible third variant, or reject
the carrier.

## Isolation and falsification requirements

- With all `lambda_i=0`, training must be checkpoint/log/RNG equivalent to the
  repaired MODQN baseline.
- A `B_i` sample may contribute gradients only to Q-head `i`.
- Reward labels, calibration, base replay contents, objective weights, masks,
  and TD-target equations remain unchanged.
- Environment branch restore, if used, must have exact state/RNG/main-trajectory
  parity and preserve physical action mapping.
- Each role is compared with a matched random-admission control having the same
  admission count and auxiliary update budget.
- A role fails if it does not improve its direct endpoint, violates service/EE
  safeguards, merely duplicates another role, or depends on post-training
  coordination.
- Current claim ceiling is "new relative to the two local EXP/ACRM carriers and
  current repository menu."  No literature-novelty claim is authorised.

## Evidence paths

Host repository `/home/u24/papers/mcrl-leo-handover`:

- `docs/POST-RUN-VALIDATION-CORRECTED-R2-2026-08-26.md`
- `docs/CATFISH-DESIGN-FREEZE-GATE-2026-08-26.md`
- `src/mcrl/algorithms/modqn.py`
- `src/mcrl/runtime/replay_buffer.py`
- `src/mcrl/runtime/trainer_spec.py`
- `src/mcrl/runtime/training_pipeline.py`
- `tests/test_w08_vanilla_td_target.py`
- `tests/test_w12_collapse_metrics.py`
- `tests/test_w17_step_environment.py`

Independent mechanism repository `/home/u24/papers/catfish-mechanisms`:

- `docs/04-MENU.md`
- `src/catfish/contract.py`
- `src/catfish/mechanisms.py`
- `tests/`

