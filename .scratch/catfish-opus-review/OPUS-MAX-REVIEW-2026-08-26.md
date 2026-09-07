# Opus Max review of three-role Catfish candidate v0

Status: completed read-only external-model review; controller-adjudicated.
Date: 2026-08-26

## Verified receipt

- Requested route: Claude `opus`, effort `max`.
- Canonical model returned: `claude-opus-5`.
- Runtime: 506,832 ms (about 8 min 27 s), 29 turns.
- Output: 36,215 tokens, including 23,965 thinking tokens.
- Subagents: 0.  Permission denials: 0.  Web requests: 0.
- The model had only `Read`, `Glob`, and `Grep` tools.
- Frozen design SHA-256:
  `f01dd357b941c442032c546fc6a8148c3bce6bedb7780845af6eed28fd6cb926`.
- Frozen prompt SHA-256:
  `2c742f1611cf8f17e96722416662a59b2af36d6ccc4d539b8613081d6b77d2c4`.

The structured receipt is in `OPUS-MAX-RECEIPT-2026-08-26.json`.

## Opus verdict

`REVISE_DIRECTION`

Opus accepted a narrowed core: bounded counterfactual transitions generated at
a decision-time seam and routed into objective-specific training paths can be
falsifiable on this host.  It rejected candidate v0 as written because the
outcome-based admission rule selects favourable reward realisations, filters
disconfirming samples, and therefore creates a self-confirming auxiliary TD
target.  It also ruled that three roles may be specified as conditional
hypotheses, but cannot yet be presented as an authorised or validated role set.

## Blocking findings

### 1. Outcome-filtered admission is biased

Candidate v0 proposed admitting a branch only when
`Delta_i = r_i(counterfactual) - r_i(executed) > tau_i`.  The environment has
live per-step fading, so this conditions the auxiliary replay bank on a
favourable reward realisation.  A Q-optimistic proposal whose realised outcome
is unfavourable is discarded instead of correcting the optimism.

Controller check: confirmed against the single TD target in
`src/mcrl/algorithms/modqn.py:511-552` and per-user/satellite random fading in
`src/mcrl/env/step.py:1093-1144`.

Required correction: decide whether to branch before observing the branch
outcome, then admit every valid branched transition regardless of its reward
sign.  Record `Delta_1/2/3` as diagnostics, not admission filters.

### 2. Per-user R1 gain is not the system-EE endpoint

Every `r1_u` uses the same system-power denominator.  A user's positive
`Delta_1(u)` can coexist with a decrease in `sum_u r1_u` when the alternative
changes the set of active beams and total power.

Controller check: confirmed by the additive identity and shared denominator in
`src/mcrl/runtime/energy_efficiency.py:167-175,251-262`, plus per-beam power
calculation in `src/mcrl/env/step.py:766-805`.

Required correction: the R1 proposal diagnostic must use the induced change in
system `sum_u r1_u`, not only the moved user's contribution.

### 3. A second update path violates a frozen structural test

The current host deliberately contains one `update()` method and one Bellman
target expression.  A separate auxiliary update method would immediately
violate W-08/B1.

Controller check: confirmed by `tests/test_w08_vanilla_td_target.py:59-74` and
the deletion rationale in `src/mcrl/algorithms/modqn.py:496-509`.

Required correction: any auxiliary rows and per-objective weights must flow
through the existing single `update()` implementation.  There must not be a
second Bellman equation.

### 4. Replay is not the only required seam

The seven-field `ReplayBuffer` has no raw reward, transition ID, physical beam
identity, or Q surface.  Those diagnostics are available from the full
`StepOutcome` through `TrainerEnvironment.last_outcome`, not from the compact
`StepResult` or replay tuple.

Controller check: confirmed by
`src/mcrl/runtime/replay_buffer.py:30-56,114-156` and
`src/mcrl/runtime/trainer_env.py:189-223`.

Required correction: specify two seams:

1. a decision-time frame producer that captures detached Q, association/load,
   raw/calibrated reward, masks, IDs, and RNG provenance;
2. the existing replay/update consumer.

Do not widen the frozen seven-field base replay schema solely for audit IDs;
keep specialist metadata in a parallel structure.

### 5. The old design record explicitly excluded a thin per-objective clone

The independent mechanism repository previously excluded "one Catfish per
objective" because three objective networks already existed and role naming
alone was too thin to be a contribution.  Its current `objective_banks_acrm`
already ranks candidates per objective by realised calibrated reward.

Controller check: confirmed by
`catfish-mechanisms/docs/00-INHERITED-STATE.md:39-54`,
`docs/06-INTEGRATION-MANUAL.md:140-152`, and
`src/catfish/mechanisms/_common.py:125-168`.

Required correction: the contribution cannot be "three roles."  It must be the
new outcome-blind branch generator plus isolated gradient routing, with a new
mechanism/control/falsifier/prereg pair.  Repository-relative novelty remains
the maximum current claim.

## Major engineering and scientific risks

- Cross-objective budgets are insufficient by themselves; one user's branch
  can change system EE and the R3 reward of other users sharing the destination
  beam.  Cross-user effects must be logged.
- A full deep copy is unlikely to be the right carrier because ephemeris objects
  can be shared while mutable episode state and all RNG states must be copied.
  Feasibility remains a prototype question rather than a confirmed fact.
- Branch and main execution must never share the same mutable RNG object because
  action-dependent radiating sets can change random-number consumption.
- Head-local auxiliary banks fit Q1/Q2/Q3 under different sampling
  distributions.  This does not automatically invalidate the design, but it
  requires a head-consistency diagnostic and matched random-admission control.
- R2 is presently adverse relative to `stay-if-possible` on handover incidence;
  the design must first measure whether `w2*Q2` is ever pivotal in the final
  scalarised argmax.
- Branch frequency needs a fixed per-episode budget `K`; candidate and random
  control must use the same branch and update budget.
- Specialist banks require independent RNG streams and resume-state coverage.
  Reusing the trainer RNG would perturb epsilon-greedy and base replay draws.
- `lambda_i=0` can require numeric equality but not identical fingerprints,
  because adding configuration fields necessarily changes the manifest hash.

## Opus carrier decision

Reject both candidate-v0 variants and adopt a third candidate:

**trigger-gated, outcome-blind, budgeted branch**

1. Decide branch eligibility from pre-outcome state, masks, detached Q surfaces,
   physical-load metadata, and a fixed per-episode budget.
2. Once a branch is executed and passes the same no-op/next-mask validity rules
   as base replay, admit it unconditionally to the selected role bank.
3. Record all realised objective and cross-user effects; do not use their signs
   as admission filters.
4. Copy only mutable environment/driver episode state and independent RNG
   states; share immutable geometry/ephemeris references.
5. Route specialist rows through the single existing Bellman implementation.
6. Compare with a matched random-branch control at the same dose.

## Controller adjudication

Adopt now:

- outcome-blind admission;
- system-level R1 accounting;
- two-seam design;
- single-update compatibility;
- independent bank RNG and resume state;
- fixed branch budget and matched random control;
- explicit answer to the earlier per-objective-role exclusion.

Retain as conditional hypotheses, not frozen claims:

- R1 Energy-Frontier Scout;
- R2 Handover-Persistence Scout;
- R3 Physical-Load-Relief Scout.

Do not adopt without prototype evidence:

- that a partial environment branch can be restored exactly;
- that head-local auxiliary sampling is stable;
- that the three proposal sets are non-redundant;
- that R2/R3 are policy-pivotal;
- any learning or endpoint benefit.

The external review therefore changes the recommended direction materially:
the three roles remain the design target, but candidate v0 is closed and must
not be implemented.  A revised v1 must use the outcome-blind carrier and pass
the prototype gate below before any heavy training.

## Minimal local prototype gate

No full training is needed for this gate.

1. **Zero-dose equivalence:** module connected with specialist dose zero versus
   module absent; logs, Q/target weights, and RNG states must be bit-identical.
2. **Branch parity:** after branch/discard, main mutable state and every RNG state
   must match a no-branch control; proposing the executed action must reproduce
   the executed reward vector.
3. **R1 alignment:** compare per-user `Delta_1(u)` with induced system
   `Delta sum_u r1_u`; precommit the sign-agreement threshold before running.
4. **Role overlap:** measure pairwise Jaccard overlap of proposed
   `(decision, action)` sets on identical checkpoint frames.
5. **Head pivotality:** over the ten fixed evaluation seeds, measure how often
   dropping `w2*Q2` or `w3*Q3` changes the greedy action.
6. **Branch cost:** measure overhead at fixed `K`; stop if projected full-run
   overhead exceeds the precommitted ceiling.

Passing this gate proves only feasibility, parity, proposal non-redundancy, and
checkpoint-level pivotality.  It does not prove learning benefit, causal role
independence, R2/R3 usefulness, held-out generalisation, literature novelty, or
collapse remediation.
