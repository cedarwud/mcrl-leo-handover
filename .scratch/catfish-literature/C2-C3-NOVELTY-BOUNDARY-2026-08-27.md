# C2/C3 novelty boundary: targeted primary-source audit

Status: read-only design evidence. This is a targeted prior-art boundary, not a
systematic review and not manuscript authority.

Date: 2026-08-27

## Question

Which parts of ADR-003 are established building blocks, and which narrower
combination could remain a project-specific contribution if the scientific
gates later pass?

## Primary sources checked

1. Tumer, Agogino, and Wolpert, *Learning Sequences of Actions in Collectives
   of Autonomous Agents*, AAMAS 2002,
   DOI: <https://doi.org/10.1145/544741.544832>. The paper frames multi-agent
   reward design around global alignment and individual learnability.
2. Foerster et al., *Counterfactual Multi-Agent Policy Gradients*, AAAI 2018,
   <https://arxiv.org/abs/1705.08926>. COMA explicitly uses a counterfactual
   baseline that varies one agent while holding the other agents' actions
   fixed, and identifies difference rewards as prior work.
3. Castellini et al., *Difference Rewards Policy Gradients*, 2020,
   <https://arxiv.org/abs/2012.11258>. This work directly combines difference
   rewards with policy gradients for multi-agent credit assignment.
4. Afif et al., *Joint Satellite Power Consumption and Handover Optimization
   for LEO Constellations*, IEEE WiSEE 2025,
   DOI: <https://doi.org/10.1109/WISEE57913.2025.11229869>, preprint:
   <https://arxiv.org/abs/2511.19745>. It jointly treats association,
   transmitted power, throughput, and a handover penalty.
5. Afif et al., *Multi-Agent Reinforcement Learning for Joint Handover
   Management and Power Allocation in Multi-Orbit Satellite Networks*, 2026
   preprint, <https://arxiv.org/abs/2608.14335>. It uses a MARL association
   policy followed by a power-allocation subproblem, with handover penalties in
   the association state/objective.
6. Lee et al., *Handover Protocol Learning for LEO Satellite Networks: Access
   Delay and Collision Minimization*, IEEE TWC 2024,
   <https://arxiv.org/abs/2310.20215>. It makes handover protocol delay and
   collision consequences explicit and learns a handover protocol.
7. He, Wang, and Wang, *Load-Aware Satellite Handover Strategy Based on
   Multi-Agent Reinforcement Learning*, IEEE GLOBECOM 2020,
   DOI: <https://doi.org/10.1109/GLOBECOM42002.2020.9322449>, author PDF:
   <https://mint.nju.edu.cn/_upload/tpl/07/92/1938/template1938/pdf/gc20hsx.pdf>.
   It jointly minimizes average satellite handovers subject to load constraints
   with multi-agent Q-learning.
8. Gupta et al., *Energy efficient LEO satellite communications:
   Traffic-aware payload switch-off techniques*, Computer Communications 236
   (2025) 108122,
   <https://orbilu.uni.lu/bitstream/10993/64490/1/Elsevier_CompComs_2025.pdf>.
   It jointly treats beam assignment, active-beam power allocation, and
   satellite switch-off to reduce payload power while satisfying demand.
9. Abels et al., *Dynamic Weights in Multi-Objective Deep Reinforcement
   Learning*, ICML 2019, <https://proceedings.mlr.press/v97/abels19a.html>.
   It identifies replay-distribution conflict across objective weights and
   proposes diverse experience replay.

## Established ideas that must not be claimed as novel

- Per-agent counterfactual or removal-based credit.
- Holding other agents/actions fixed to identify a focal contribution.
- Designing local rewards for alignment and learnability.
- Joint handover/association and power-allocation optimisation.
- Treating handovers as having time, signalling, power, collision, or service
  consequences.
- Using MARL specialists, centralised training, or training-only information in
  the generic sense.
- Jointly minimizing handovers while satisfying a satellite-load constraint.
- Using persistence, hysteresis, time-of-stay, or an option/commitment horizon
  to suppress ping-pong handovers.
- Joint beam assignment, active-beam power allocation, or payload switch-off
  for energy efficiency.
- Maintaining diverse or objective-relevant replay in multi-objective RL.

Consequently, the formula

```text
P_system(a) - P_system(a with focal user removed or changed)
```

is an application of established difference-reward reasoning. Its existence
alone cannot support a novelty claim.

## Narrow project-specific candidates

The following are only **candidate contribution surfaces**. They still need a
broader systematic audit and positive experimental evidence.

### C2

- An exact additive decomposition of the change from instantaneous canonical
  EE to a handover-time/energy ledger,
  `sum_u r2_u = eta_HO - eta_0`, with the full shared denominator retained.
- Boundary-persistence Catfish collection that deliberately samples the
  decision conflict between immediate EE and avoided temporal damage, while
  Main alone remains the deployed policy.

Neither “handover costs time/energy” nor “stay longer” is the contribution.

### C3

- The closed-form removal marginal induced by this simulator's
  max-over-users beam power recurrence, including the singleton beam overhead
  case.
- A pre-outcome, one-focal, active-destination bottleneck-relief certificate
  whose first-step `Delta P_system < 0` follows analytically from that exact
  recurrence.
- A state-sufficient guard that converts those power reductions into positive
  held-out time-accounted EE without reading realised fading, rate, reward, or
  successor data.

The third item is not yet established; it is precisely what the disjoint-seed
shadow and later aliasing audit must decide.

### Three-role carrier

- C1, C2, and C3 create independent, causally identified replay streams for
  energy-frontier, temporal-damage, and spatial power-bottleneck experience.
- The streams affect one Main learner through training data only; Catfish
  actions are never voted, auctioned, coordinated, or fused at execution.
- A matched factorial must show that informed C2/C3 slots outperform random
  slots and that all three together survive the interaction test.

This combination may be distinguishable from ordinary multi-objective MARL,
but it is not globally novel merely because it is called Multi-Catfish.

## v0.3 SMC-ER boundary after the formal falsifiers

The C2 time-only EE direction and the C3 outcome-blind median guard are now
closed. Their failure cannot itself be turned into a contribution claim.

For `MULTI-CATFISH-PAPER-ALGORITHM-V0.3-2026-08-27.md`, the narrowest remaining
candidate method contribution is the **carrier composition and exact local
contracts**, not the generic ingredients:

- a canonical-R2 persistence-option Catfish that changes the executed
  experience trajectory while keeping one-step TD and the Main reward vector
  unchanged;
- a max-over-users PA-recurrence certificate for a three-step persistent
  bottleneck-relief Catfish, with unilateral marginal power as Catfish-only
  credit; and
- fixed-quota routing of complete transitions from three independent
  specialists into one vector-reward Main learner, with matched random source
  controls and zero Catfish dose at deployment.

Even this compound claim remains only a project-specific candidate. A broader
systematic search could still find an equivalent auxiliary-experience or
option-based architecture, and positive experiments are required before the
word “effective” is admissible.

## Current claim ceiling

Allowed now: “ADR-003 proposes a project-specific three-stream mechanism built
from established counterfactual-credit and satellite optimisation ideas.”

Not allowed now: “C2/C3 are novel,” “the mechanism improves EE,” or “the three
Catfish are effective.” Those claims require, in order, systematic prior-art
search, all physics/state/service gates, isolated-role evidence, and the frozen
joint factorial.
