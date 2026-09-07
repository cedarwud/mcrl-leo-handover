# ADR-001: Proposed RIS-lineage R1 Catfish boundary

## Status

Proposed. This record has no runtime, training, preregistration, or manuscript
authority. It requires independent cross-model review and an explicit
controller ruling before implementation.

## Date

2026-08-26

## Context

The canonical MCRL environment reward is

```text
r1_u(t) = R_u(t) / P_system(t),
sum_u r1_u(t) = system EE(t).
```

That formula is executable system truth and is not being redesigned. The user
wants the R1 Catfish mechanism to inherit the original RIS Catfish EXP and
ACRM ideas while R2 and R3 are redesigned for LEO-specific temporal and
spatial roles.

Three distinctions are load-bearing:

1. An environment/evaluation reward is not the same object as a Catfish-only
   training reward.
2. Original RIS experience stratification uses pre-generated communication
   configurations labelled by realised EE. The proposed LEO version adds full
   transition lineage and a frozen master corpus; it is therefore a named
   RIS-inspired adaptation, not a literal reproduction.
3. Main replay must preserve the exact original MCRL reward vector even when
   the transition originated from a Catfish rollout.

The current MCRL baseline has one MODQN learner, one replay buffer, three
objective heads, and no live Catfish path. Its G-6 gate forbids integrating a
Catfish path without a new controller decision. The current one-step
`evaluate_actions` seam returns exact current-slot physics but no
branch-specific next observation or next mask, so it cannot produce a valid
EXP replay transition.

## Proposed decision

### 1. Preserve environment and evaluation truth

Keep `r1_u = R_u/P_system` unchanged in the environment, Main replay, Main
evaluation, checkpoint selection, and headline EE. No Catfish shaping term is
allowed in any of those surfaces.

### 2. Treat RIS-inspired EXP as a training-data mechanism

The proposed LEO interpretation of RIS EXP is:

- freeze one behavior/data-generating policy and its action probabilities;
- commit exactly one outcome-blind joint action at every encountered state;
- archive every resulting complete step bundle in a master corpus before
  treatment training;
- attach a step-level system-EE label with exact joint lineage;
- use the step bundle as the stratification unit, then unfold it into per-user
  transitions while preserving the bundle ID;
- freeze the quantile algorithm, tie rule, strata, and dataset membership
  before treatment training;
- train the R1 Catfish on the high-EE stratum and Main on its declared base
  stratum;
- during preregistered intervention windows, inject a fixed fraction of
  Catfish-origin transitions into Main updates.

The original RIS top-20% / top-50% thresholds and 70:30 mixed batch are source
defaults, not automatically calibrated LEO optima. They may be used as a named
RIS-lineage fidelity arm only if the pre-generation distribution, sample
support, and equal-budget controls are frozen first. For that arm, equality at
the upper quantile enters Catfish, equality at the lower quantile enters Main,
and all bottom-stratum bundles remain in the audit corpus even if excluded from
training. No coefficient or quantile may be selected on final validation data.

The following is forbidden: generate several current-state alternatives,
observe their outcomes, and let the favourable alternatives enter the EXP
master corpus. Counterfactual atlas rows can never become replay. EE
stratification is applied afterward to a corpus containing one committed joint
action per encountered state. It remains an intentionally optimistic replay
sampling heuristic, not an unbiased Bellman sample or a causal estimator.

This differs from the RIS source in several ways: complete Markov transition
bundles are required; Main/Catfish comparison is matched by state and common
random numbers; asymmetric discounting is not inherited by default; and the
source's independently evolving Main/Catfish trajectories are not called a
matched counterfactual.

### 3. Keep ACRM Catfish-only

The candidate per-user R1 Catfish training reward is

```text
r1_cat_acrm,u = r1_cat,u + eta_A * (r1_cat,u - r1_main_cf,u),
```

where both terms use the unchanged MCRL R1 definition. Freeze one Main
comparator checkpoint and policy for an ACRM collection block. At each Catfish
trajectory state, evaluate the comparator joint action with a copied RNG, then
commit the Catfish joint action with the original RNG. The Catfish branch owns
the stored successor, next mask, and terminal flag. The system value is
recovered only by summing the per-user contributions; a global EE difference
is not broadcast to every user.

`eta_A`, Catfish discount, comparison timing, calibration order, tie/zero
cases, RNG order, block length, and comparator refresh policy must be frozen
before treatment outcomes. A first pilot uses a comparator frozen for the
entire run; a lagged comparator is a separate nonstationary treatment.

The shaped scalar is formed in natural units, calibrated once through the
ordinary R1 scale, and may update only the R1 Catfish learner. When a
Catfish-origin transition is transferred to Main, Main receives the canonical
calibrated but ACRM-unshaped full environment reward vector `(r1, r2, r3)` and
the same executed Catfish successor.

That transfer is ordinary DQN off-policy replay only under the current
shared-policy/local-observation approximation. In the joint-action-coupled
multi-user system it is not claimed to be an exact stationary single-agent MDP
transition, unbiased transition sampling, or a causal estimate. Behavior-policy
probabilities and complete joint lineage are therefore mandatory receipts.

### 4. Admit the architecture consequence explicitly

The proposed ACRM adaptation requires at least one separate R1 Catfish learner state: online
and target parameters, optimizer, replay or dataset view, RNG, checkpoint, and
resume metadata. It may reuse the same tested Bellman-update implementation,
but it is not the current single-learner baseline.

This proposal therefore supersedes the earlier design assumption that no
second Catfish TD learner can exist. It does not supersede G-6 and does not
authorize code changes.

### 5. Do not infer R2/R3 reward semantics from R1 EXP/ACRM

R2 and R3 may eventually use the same training-time carrier and accounting
interface, but they do not inherit R1's EE stratification label or ACRM formula
by default. Their causal axes and credit contracts must pass separate gates.

## Alternatives considered

### Copy the original RIS scalar EE reward into MCRL

Rejected. MCRL already has an exact action-aware system-EE decomposition. A
second EE definition would break reward, replay, and evaluation consistency.

### Shape the Main R1 reward directly with ACRM

Rejected. It changes the scientific objective and makes treatment evaluation
incomparable with the canonical baseline.

### Use one learner and call high-reward Main samples a Catfish

Rejected. It removes the independent challenger whose differentiated policy
is the mechanism being claimed.

### Select only realised-positive counterfactual branches online

Rejected. This leaks outcome information into branch admission and creates an
unmatched support advantage.

### Freeze offline EE strata after executed pre-generation

Proposed. It is a RIS-inspired adaptation that preserves EXP's executed-data
stratification concept while adding full transition lineage and avoiding
same-state outcome cherry-picking; it is not a literal reproduction.

## Consequences

- A new controller gate is required before any Catfish code enters the live
  MCRL path.
- Training cost, checkpoint size, RNG surfaces, and resume tests increase.
- EXP needs step-bundled joint lineage; the existing per-user replay snapshot
  cannot reconstruct the required system-EE stratum reliably.
- The master corpus must log behavior-policy probabilities and joint action
  lineage so distribution shift can be audited.
- ACRM needs exact matched Main/Catfish evaluation and must not leak its shaped
  label into Main.
- One-step preview is insufficient for ACRM learning data: the Catfish branch
  needs an executed or exact full-fork next state and next mask.
- The fidelity arm needs equal-corpus-size and equal-injection-budget controls.
- Passing the optional action-level shadow gate supports only its bounded
  one-focal proposal; it neither authorizes nor vetoes EXP/ACRM learning.
- Carrier parity plus an explicit controller ruling may authorize only a short
  EXP/ACRM factorial; effectiveness remains unproven until that pilot runs.

## Required acceptance gates

1. Cross-model review finds no reward-truth or support violation.
2. If the optional one-focal R1 proposal is pursued, its separate design-data
   gate demonstrates pre-action-identifiable opportunity. That result neither
   authorizes nor vetoes the EXP/ACRM carrier.
3. A complete-transition pre-generation seam passes next-state, next-mask,
   reward-vector, RNG, and resume parity tests.
4. A data-blind short pilot compares EXP, ACRM, EXP+ACRM, and equal-budget
   controls before any long training.
5. Only an explicit controller ruling may lift G-6 for implementation.
