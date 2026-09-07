# Fresh-context review: EE, handover, and load balancing

Date: 2026-08-26

## Question and completion criterion

This review deliberately starts outside the current manuscript and implementation. It asks how three objectives are related in primary LEO/wireless research:

- R1: energy efficiency (EE), normally useful bits or rate divided by system energy or power;
- R2: handover stability/cost;
- R3: load balancing/congestion.

Completion criterion: at least six primary sources, including at least two LEO-specific sources; every directional relationship must name its mediator and boundary condition; the result must end in a KEEP_THREE, CONDITIONAL_THREE, or MERGE_DROP verdict.

## Result in one sentence

The causal channels are well established, but their signs are not universal: handover and load are state-dependent regularizers or constraints on an association decision, not monotone proxies for EE. The defensible verdict is **CONDITIONAL_THREE**.

## What the literature clearly defines

All three objectives share one control variable: the user-to-satellite/beam association. The association changes temporal stability, channel quality, resource sharing, interference, active infrastructure, throughput, and power. EE is downstream of those mediators.

```text
association a(t)
  |-- temporal branch: stay/switch -> HO overhead and interruption
  |                                  -> future channel and visibility
  |-- spatial branch:  user placement -> resource sharing/blocking
  |                                   -> interference and active nodes
  `-- physical outcome: system bits B, system energy E -> EE = B/E
```

LEO research does not generally claim “fewer handovers always improve EE” or “more even load always improves EE.” It instead formulates combinations such as rate minus a handover penalty, minimum handovers subject to satellite-load constraints, or joint association/power optimization. Examples include:

- Afif et al. jointly optimize rate, power, association, and a handoff penalty; their model states that handoffs add signaling, interruption, and power costs, while excessive persistence can sacrifice rate ([primary paper](https://arxiv.org/html/2511.19745)).
- He et al. minimize average LEO handovers subject to a per-satellite channel/load constraint. When resources are scarce, users may accept a satellite with shorter remaining visibility to avoid overload; when resources are sufficient, this sacrifice is unnecessary ([primary paper](https://mint.nju.edu.cn/_upload/tpl/07/92/1938/template1938/pdf/gc20hsx.pdf)).
- Taksande et al. show directly that independently choosing the longest continuous connection minimizes handovers but can overload a satellite; some users must deviate from their individually handover-optimal paths to control overload ([primary preprint](https://arxiv.org/html/2607.04829)).
- Jiang et al. optimize LEO coverage duration, allocated capacity utility, and load balance jointly and report that improved balancing can weaken capacity utility, while longer association duration reduces handovers ([primary article DOI](https://doi.org/10.1109/TVT.2022.3174575)).
- The HOBS work places training/association overhead inside effective data time and jointly controls association and beam power for EE; stale association information and infrequent power adjustment lower EE in a fast-moving LEO setting ([primary paper](https://ieeevtc.org/vtc2024spring/DATA/PID2024002205.pdf)).

## Signed causal relationships

| Relationship | Helpful EE path | Harmful EE path | Sign-setting moderators |
|---|---|---|---|
| R2 higher = fewer handovers -> R1 | less signaling energy, less interruption, less retraining/reallocation | remaining on a degrading link lowers useful bits and can require more RF power; delayed switching can cause outage | explicit HO energy/time, channel slope, remaining visibility, dwell/hysteresis, evaluation horizon |
| R3 higher = more balanced load -> R1 | less blocking and resource contention; improved per-user bandwidth/rate; sometimes less hotspot interference or peak transmit power | offloading can choose a weaker channel; spreading can activate more beams/satellites and add fixed/circuit/fronthaul power or interference | traffic regime, capacity constraint, resource-sharing law, active-node power, channel heterogeneity, reuse/interference model |
| R2 higher -> R3 | persistence may avoid transient synchronized moves | persistence preserves or creates hotspots because users do not relocate | user density, common visibility windows, capacity slack |
| R3 higher -> R2 | a target with both low load and long remaining visibility can prevent future moves | immediate rebalancing normally requires association changes and therefore handovers | prediction horizon, target visibility, overload severity |

The two-sided R3 result is independently visible in terrestrial primary work and transfers when the satellite model has the same resource and fixed-power couplings. Zhou et al. show that joint load-aware association and power control can improve both load balance and EE ([primary paper](https://arxiv.org/abs/1607.00853)), while a related uplink study reports that a more load-balanced/fair association can reduce achievable rate and yield lower EE than rate- or EE-oriented association ([primary paper](https://arxiv.org/abs/1511.08342)). Kuang and Utschick explicitly find that association biases for energy saving differ from those for load balancing because cell activation and interference must be optimized jointly ([primary paper](https://arxiv.org/abs/1602.03508)). Zhuang et al. show the opposite low-load pressure: energy saving may require concentrating traffic so that the smallest feasible set of access nodes remains active ([primary paper](https://arxiv.org/abs/1509.04805)).

These terrestrial mechanisms are not proof for a particular LEO simulator. They are transferable hypotheses only when its power model charges active satellites/beams and its rate model includes shared resources or interference.

## One common EE certificate

Let the current system have rate/throughput `R`, power `P`, and `eta = R/P`. For a candidate association change with deltas `DeltaR` and `DeltaP`, assuming positive denominators:

```text
(R + DeltaR) / (P + DeltaP) > R / P
    iff
DeltaR - eta * DeltaP > 0.
```

Over a temporal window, replace rate/power with useful bits/energy. Handover interruption belongs in `DeltaB`, handover signaling energy in `DeltaE`, and future channel improvement in both. For a spatial move, all affected users, interference changes, and active-node power belong in the same deltas. This identity gives all three roles one common language without pretending the secondary objectives have fixed signs.

## Coherent three-Catfish design hypothesis

All roles use one training-only challenger interface: a pre-outcome trigger, a role-specific counterfactual proposal, a bounded intervention budget, unconditional storage of the full reward vector, and a mediator receipt. No role filters transitions by a favorable realized outcome, and no role survives into deployment.

1. **C1 Energy-Frontier Catfish**
   - Trigger: Main is uncertain or near an EE action boundary.
   - Proposal: an alternative predicted to improve direct long-horizon EE.
   - Mediators: total useful bits and total system energy.
   - Falsifier: it does not change executed actions or has no positive held-out EE marginal effect relative to a dose-matched random challenger.

2. **C2 Temporal-Externality Catfish**
   - Trigger: stay versus switch is near the boundary and the candidate differs in remaining visibility, channel trend, or handover class.
   - Proposal: the R2-favored alternative among EE-admissible candidates; use occasional bidirectional boundary probes so the learner sees both premature switching and harmful persistence.
   - Mediators: handover/interruption cost, future link quality, remaining service duration, and subsequent `DeltaB - eta*DeltaE`.
   - Falsifier: after controlling exploration dose, the intervention changes handover count but not these mediators or held-out EE.

3. **C3 Spatial-Externality Catfish**
   - Trigger: candidate associations differ in congestion or in the marginal active-beam/satellite/interference footprint.
   - Proposal: the R3-favored alternative among EE-admissible candidates; probe both spreading and consolidation rather than always selecting the least-loaded beam.
   - Mediators: blocking/resource share, other users' rates, interference, peak beam power, active-node count, and system `DeltaR - eta*DeltaP`.
   - Falsifier: it improves a raw balance index but has no measurable network externality or held-out EE contribution.

This is a unified **multi-Catfish externality discovery** mechanism: C1 explores the direct efficiency frontier, C2 exposes inter-temporal externalities, and C3 exposes inter-user/spatial externalities.

## What must be tested

Use a full `2^3` role factorial (`000` through `111`) plus a true no-Catfish baseline. In inactive role slots, use dose-matched random interventions so role direction is separated from extra exploration and updates.

Report:

- each role's main effect averaged over the other roles;
- pairwise and three-way interactions;
- exact three-player Shapley attribution from all eight cells;
- mediator changes for C2 and C3;
- held-out EE, throughput, power, service, handovers, and load/activation metrics.

The desired result is `Y111` above every leave-one-out pair (`Y110`, `Y101`, `Y011`) with uncertainty accounted for. A role may be conditionally useful even if its standalone EE effect is negative, but only if its interaction contribution is positive and the full trio is best. If the trio is indistinguishable from the best pair, the third role is not scientifically necessary.

## Mapping back to the current project (after the fresh review)

The current R2 is a dimensionless event penalty and is not itself consumed by the physical throughput or power model. It therefore lacks the direct handover-energy/interruption pathway assumed in much of the literature; any effect on R1 must arise indirectly through changed associations and future segment states.

The current R3 is `-U_b` per served user. It encodes a balancing preference, but not the sign of the EE externality. Under equal per-user time sharing, the user-count factor cancels in a beam's aggregate rate when spectral efficiencies are held fixed; R3 can affect R1 only through changed grouping/channel quality, active beams/satellites, interference, max-beam power, or service feasibility.

Therefore the literature supports three distinct roles, but it does not validate the current raw R2/R3 proxies as EE-improving mechanisms.

## Verdict

**CONDITIONAL_THREE.** Keep three roles for the next diagnostic design, but define C2 and C3 by temporal and spatial EE externalities rather than by blind maximization of raw handover count and raw load. Promote to KEEP_THREE only after the matched factorial and mediator evidence show that each role changes physical actions and contributes positively—possibly through interactions—to held-out EE or an explicitly preregistered non-inferior secondary objective.
