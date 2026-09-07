# ADR-003: Proposed specialist rewards and three-stream Multi-Catfish

## Status

Proposed. This record defines a review target; it has no runtime, reward,
preregistration, manuscript, or training authority. In particular, it does not
lift G-6, resolve the primary antenna gain, source `E_HO`, or establish that any
Catfish improves held-out energy efficiency.

ADR-004 subsequently accepts C2's payload-only system boundary and time-only
algebra. It removes `E_HO` from C2's proposed primary endpoint without claiming
that physical procedure energy is zero. Numeric event times and every training
gate remain unresolved.

## Date

2026-08-27

## Decision question

Can R1, R2, and R3 each own a physically distinct training-time Catfish while
one unchanged Main MODQN remains the only policy at evaluation and deployment?

The proposed answer is **conditional yes**, with two constraints:

1. R2 and R3 need new candidate reward semantics tied by exact identities to
   the numerator or denominator of energy efficiency; and
2. the three Catfish actions are never fused by an auction or coordinator.
   They generate separate, complete transition streams that Main learns from.

This separates the mechanism question from the effectiveness question. The
identities below establish a possible EE pathway, not a positive empirical
effect.

If accepted, this reward redesign supersedes the reciprocal exchange as the
proposed C3 **training** mechanism in the v0.1 design. Reciprocal exchange may
remain a read-only support/interaction diagnostic, but it grants no C3 role or
training authority.

## Shared architecture

There are four learner states during treatment training:

- Main MODQN, with its existing three-head action selection contract;
- C1, the R1 Energy-Frontier Catfish;
- C2, the R2 Temporal-Damage Catfish; and
- C3, the R3 Spatial-Power Catfish.

Each Catfish has independent online/target parameters, optimizer, replay view,
RNG, checkpoint, and resume metadata. A Catfish rollout executes one
pre-outcome action on its own exact environment fork or dedicated trajectory.
The resulting complete transition is retained regardless of reward sign.

Main receives the executed transition's canonical, unshaped full reward vector
and its actual successor, next mask, terminal flag, joint-action lineage, and
behavior probability. Catfish-only shaping never enters Main replay. The replay
mixer combines **data**, not proposed actions.

That receipt is necessary but not sufficient. Before a specialist source is
mixed, the actual Main Bellman consumer must demonstrate that its local
observation/action rows can represent the source's intervention. Source policy
version, frozen collection block, trigger probability, replay quota/age,
pre-state cluster, and behavior probability are part of every row's provenance;
an evolving specialist may not silently overwrite an older source identity.

At evaluation and deployment:

```text
C1 dose = C2 dose = C3 dose = 0
executed action = existing Main MODQN masked-greedy/scalarized action
```

There is no post-training Catfish, vote, auction, coordinator, or action
override. Separate treatment arms and a factorial decide whether each
experience source helps Main; the full trio is not assumed to be best.

## C1: unchanged R1 Energy-Frontier Catfish

C1 is governed by ADR-001. Environment and evaluation truth remain

```text
r1_u = R_u / P_system,
sum_u r1_u = system EE.
```

Its mechanisms are the named RIS-inspired executed-experience stratification
(EXP) and Catfish-only ACRM contrast. This ADR neither changes that formula nor
copies EXP/ACRM automatically into C2 or C3.

## C2: Temporal-Damage Catfish

### Candidate reward identity

For accounting interval `Delta`, let

```text
B0       = Delta * sum_u R_u
E0       = Delta * P_system
eta0     = B0 / E0 = sum_u R_u / P_system
L        = sum_u R_u * T_u
eta_time = (B0 - L) / E0
```

where `T_u = T_HO(c_u)` for the realised successful-handover class. The
per-user candidate reward is

```text
r2_time,u = -R_u*T_u/E0.
```

It has the exact additive certificate

```text
sum_u r2_time,u = eta_time - eta0 = -L/E0 <= 0.
```

The certificate's domain is

```text
E0 > 0, R_u >= 0, and 0 <= T_u <= Delta.
```

ADR-004 declares UE, gateway, random-access, and other procedure energy outside
the canonical partial satellite-payload denominator. Their exclusion is not a
claim that physical handover energy is zero. Any future component-level
`(E0+H)` boundary expansion is a separately named sensitivity. An
all-zero-service step with `E0=0` has no `eta0` certificate and is handled by
the service/outage gate.

Thus C2 would train on payload-boundary EE damage caused by useful-time loss
rather than merely counting handovers. A no-event transition contributes zero.
The reward is in bit/J and remains in natural units in receipts; any learner
calibration is frozen from a reference corpus and may not change the reported
physical value.

The certificate is conditional on the timing model. `Delta` stays the live
30.08-s agent decision interval; the 0.640-s D2 measurement clock is only a
labelled scale sensitivity. If an interruption spans intervals, a
remaining-interruption state and multi-step bits/energy ledger replace the
one-interval expression. `B0` and `L` use the identical
non-interruption-discounted rate array; applying `R_u*T_u` when `R_u` already
includes the same outage is forbidden. The expression assumes `P_system` is
paid across `Delta`; a model with different control/data power states must
integrate those states explicitly.

One-step `r2_time` values must not be summed and reported as cross-time EE.
The held-out C2 endpoint is the preregistered ratio of total useful bits after
interruption to total consumed energy over the evaluation horizon. The
unchanged steady-state `eta0=sum R/P_system` remains a separately reported
companion. Improving temporal ledger EE does not by itself prove an improvement
in steady-state R1, and an R1 improvement alone does not prove the temporal
pathway.

### New training-time mechanism: boundary-persistence replay

C2 operates only at pre-outcome temporal boundary states where the previous
association and current candidate table expose at least one valid persistence
choice and one valid handover choice. The trigger and candidate event classes
use the association ledger, physical IDs, masks, dwell/TTT state, and a
dedicated RNG; they cannot read the realised reward or successor. Candidate
admission also requires a pre-outcome deterministic recurrence-feasibility
certificate. If that certificate is not representable from an authorised state
or exact training-only mask, C2 remains shadow-only. Any unexpected realised
outage is retained and fails the service gate rather than becoming a zero-cost
temporal sample.

At an intervention:

1. freeze Main's reference joint action;
2. sample one focal user from the eligible set before outcomes;
3. let C2 choose among that user's persistence/handover candidates using its
   temporal head while all other users keep the reference action;
4. execute and retain the complete branch even if it is worse; and
5. train C2 on `r2_time` while transferring only the unshaped canonical
   full vector to Main.

C2 replay is balanced by **pre-action boundary/event eligibility**, not by
realised success. No high-reward-only filter is allowed. A matched random
boundary alternative uses the same focal frames and dose.

### Current closure

ADR-004 closes the C2 **system-boundary and algebra** question: the primary
candidate is payload-boundary time-only temporal EE, and out-of-boundary
procedure energy is not imported. `R2_PHYS = NOT_CLOSED` for numeric timing.
ETSI TS 38.133 supplies conditional timing proxies for specific FR2-NTN
procedures, but the SAN/PCell/electronic-VSAT, PRACH/SMTC, and
interruption-versus-full-delay mappings remain unresolved. Re-entry and episode
start are fixed at `T=0` in this successful-handover ledger and may not inherit
an inter-satellite time. The direct timing signal is also small on the current
30.08-s decision interval, so no penalty coefficient may be enlarged merely to
make C2 appear effective.

The state-observable v2 diagnostic nevertheless closes the support question at
legacy sensitivity level. Across ten seeds, an exact-incumbent-stay challenger
was eligible in 758/1,000 sampled focal rows, reduced the focal handover class
in all 758, and was both immediate-EE-positive and service-safe in 393
(51.85%), with at least one such row in every seed. Its frozen decision remains
`ADVANCE_TO_PHYSICAL_HANDOVER_PARAMETER_GATE_ONLY`: it establishes a credible
boundary-persistence hypothesis, not C2 learning or temporal-EE effectiveness.
One of 758 alternatives was service-unsafe, so deterministic feasibility
admission remains mandatory.

C2 advances only if it improves the frozen ledger-based temporal EE endpoint
and meets service safeguards; steady-state `eta0` must be non-inferior and is
reported beside it. Until that ledger and its physical parameters receive
authority, C2 is a temporal/QoS hypothesis, not an established EE Catfish.

## C3: Spatial-Power Catfish

### Why the current R3 cannot train this role

The live `r3_u = -U_{b_u}` rewards count spreading. It can encourage additional
active beams, which may increase circuit and baseband power, and it does not
identify which user sets a beam's maximum transmit-power requirement. A new
candidate R3 is required if C3 is to own a direct canonical-EE denominator
pathway.

### Candidate reward identity

An equal allocation such as `-C_b/U_b` exactly accounts for system power when
summed over users, but it is not an incentive-safe local reward. A focal user
can improve its allocated share while total system power worsens. It therefore
must not become the proposed Main R3 reward.

Instead, for each served user `u`, hold every other executed action fixed and
define the exact removal counterfactual

```text
P_minus_u      = system power with u removed from the realised joint action
d_power,u      = P_system - P_minus_u
r3_marginal,u  = -d_power,u                                      [W].
```

The live per-beam formula gives an analytic implementation. Let `p_b` be the
served beam maximum, `p_b_minus_u` the maximum after removing `u`, `U_b` its
served load, and `N_active,s(b)` the satellite's active-beam count:

```text
if U_b > 1:
    d_power,u = P_supply(p_b) - P_supply(p_b_minus_u)
if U_b = 1:
    d_power,u = P_supply(p_b) + P_cir
                + I{N_active,s(b)=1} P_BB.
```

Thus a non-pivotal served user has zero R3 marginal cost, while the user that
sets a beam maximum or keeps a beam/satellite active receives the corresponding
negative physical cost. `sum_u r3_marginal,u` is generally **not**
`-P_system`; no additive accounting identity is claimed. The separately
reported team endpoint remains `R3_team=-P_system`.

The reward has the local incentive identity that the allocation lacked. For
two service-preserving actions of one focal user with all other actions fixed,

```text
r3_marginal,u(a_u_prime, a_minus_u)
  - r3_marginal,u(a_u, a_minus_u)
= P_system(a_u, a_minus_u)
  - P_system(a_u_prime, a_minus_u).
```

Therefore its sign exactly matches the system-power direction of a unilateral
change. At the current gate this is **C3-private credit** in natural watts; it
is not broadcast as a team scalar and it does not enter Main's TD target. Main
continues to receive only the separately authorised canonical reward vector.
The marginal signal cannot become Main R3 unless an observational-aliasing and
focal-versus-full-bundle replay audit proves that the unchanged Bellman
consumer can use it without reversing credit on non-focal unchanged actions.
Raw watts, the removal counterfactual, and any frozen learner calibration are
separate receipt fields. This identity aligns the denominator only; it does
not prove a throughput, temporal-ledger, or canonical-EE improvement.

A user that selected a valid action but was execution-time infeasible receives

```text
r3_marginal,u = -C_out,
C_out = max_{0 <= p <= P_beam,max} P_supply(p) + P_cir + P_BB.
```

This is a model-derived accounting barrier, not an incentive-safety proof. It
can tie the most expensive legal one-user service, and an outage may reset a
power segment and change future discounted return. A structural no-op with no
valid decision-time action receives zero and is reported separately. C3
interventions are therefore restricted ex ante to certified service-preserving
actions. Any Main reward-only arm also needs a hard or lexicographic service
constraint, or a proof of strict discounted-horizon dominance including
segment-reset effects. `C_out` alone cannot authorize it.

### New training-time mechanism: intra-satellite power-bottleneck challenge

The same-handover-class version is rejected as the primary mechanism. It
cannot challenge a continuing incumbent bottleneck: that reference has class
`NONE`, while every different-beam relocation is a handover. A prior draft also
claimed a general zero-support proof by assuming all continuing powers are at
least `p0`; the live recurrence can fall below `p0` when transmit gain improves,
so that proof is retracted. Exceptional same-class support is not equivalent to
the intended pathway, and matching an event class would not hold R2 fixed
because rate, `eta0`, `E0`, and system power can still change. Episode-start
warm histories are excluded from causal support.

The corrected C3 mechanism exposes the conflict instead of hiding it. It
changes exactly one focal user's action while every other user's Main reference
action remains fixed. The reference must persist on a continuing incumbent;
the candidate relocates to a different beam on the **same satellite**, paying
exactly one `INTRA_SATELLITE` event. Let those beams be `b_src != b_dst`.
A relocation is eligible only when all of the following are certified before
outcome:

1. the reference is the focal continuing incumbent and is deterministically
   service-feasible;
2. `U_bsrc >= 2`, so removing the focal user does not deactivate the source;
3. `b_dst` is already active under the frozen Main-reference joint action;
4. the focal user is the unique maximum-power user on `b_src`, and the
   remaining source maximum `p_bsrc_prime` is strictly smaller;
5. the valid same-satellite candidate is deterministically service-feasible
   and its new-link power does not exceed the existing destination maximum, so
   `p_bdst_prime = p_bdst`;
6. reference class is `NONE`, candidate class is `INTRA_SATELLITE`, and the
   complete vector retains that R2 temporal cost; and
7. physical IDs are unique, every non-focal action and link power is unchanged,
   and served users plus active beam/satellite sets are identical.

`p_bsrc` and `p_bdst` come from one frozen Main-reference fork;
`p_bsrc_prime` and the candidate power come from the candidate fork at the
same pre-state. The certificate uses masks, physical mappings,
association/segment state, and deterministic recurrence/service calculations.
It may not use realised fading, rate, EE, reward, or successor. Under the live
PA model, supply power is strictly increasing in positive beam output power.
Fixed power and the destination beam power are unchanged, so eligibility gives
the exact pre-outcome certificate

```text
P_system_prime - P_system
  = P_supply(p_bsrc_prime) - P_supply(p_bsrc) < 0.
```

The focal reward improves by the same amount:

```text
r3_marginal,u(candidate) - r3_marginal,u(reference)
  = P_system(reference) - P_system(candidate) > 0.
```

This proves only the immediate denominator direction. C3 deliberately adds one
intra-satellite temporal event; rates/interference can also change, so temporal
and canonical EE may still worsen. C2 supplies the opposing continuity
experience, while Main receives every branch's complete reward vector and must
learn the trade-off. Neither Catfish accepts or vetoes the other's action.

`C3_SUPPORT = NOT_CLOSED`. The 112-dimensional Main state does not contain
segment-start gain or exact current link/beam power. Until a sealed census
shows non-zero support and an authorised C3 state or exact training-only mask
can represent the certificate, C3 remains shadow-only. Even then, transfer to
Main needs a separate representability test because its deployed observation
does not receive the hidden certificate inputs.

`C3_RATE_SAFETY = NOT_CLOSED`. The first legacy-narrow shadow found 20 exact
power-relief candidates but only 5 immediate-EE-positive versus 15 negative;
18 also lost throughput. A parameter-free median-channel throughput guard
selected those five on the same development seed, but its original frozen
protocol still decided `REJECT_MEDIAN_RATE_RULE`; that result is permanent.
Following the independent Fable review, the unchanged rule is registered only
as a new disjoint-seed shadow hypothesis with multiplicity disclosed. Its
primary is conditional time-accounted EE; realised throughput is descriptive
and no post-hoc non-inferiority margin is permitted. Failure of that sealed
shadow closes C3 as an EE role.

C3 uses an independent one-focal value surface over the certified support and
the focal `r3_marginal`. Before any value ranking, the frozen pre-outcome
median-channel guard must hold; it is a non-inferiority filter in the model
branch, not an EE score. Deterministic ties are broken by larger certified
power reduction and then physical ID. The selected branch is executed and
retained regardless of realised EE sign. A uniform random action from the same
post-guard support is the dose-matched control. Because exactly one local
action changes, no paired-action coordination is required at deployment, but
the Main Bellman representability/transfer gate remains mandatory.

The previous reciprocal exchange remains a diagnostic for whether spatial
composition can matter at fixed load. It is not injected into Main: complete
joint lineage alone cannot make the unchanged local-action Bellman consumer
reproduce a two-user coordinated action.

The bottleneck certificate relies on the live beam rule

```text
p_b = max_{u served by b} p_link,u,b,
```

which is why this proposal is materially different from the failed ARLP
load/activation potential: it targets the actual PA denominator and forbids
activation changes.

## Why these are three coherent Catfish rather than three action voters

All three are specialist challengers to one Main policy:

| Catfish | Physical axis | Own learning signal | New experience support |
|---|---|---|---|
| C1 | immediate rate/power frontier | unchanged `r1` plus Catfish-only ACRM | executed high-EE-stratum and contrast transitions |
| C2 | temporal interruption/procedure damage | exact `eta_HO - eta0` decomposition | stay-versus-handover boundary transitions |
| C3 | spatial beam-power bottleneck | unilateral marginal-power difference reward | certified intra-satellite bottleneck-relief transitions |

Their experiences can influence the single deployed action only through Main's
ordinary off-policy updates on complete executed transitions. This is the
integration hypothesis to test. It is not guaranteed merely because each
specialist improves its own reward.

## Required causal separation

Reward redesign and Catfish benefit must not be bundled into one comparison.
For each proposed reward/mechanism, the minimum causal cells are:

```text
A = old reward      + Main only
B = proposed reward + Main only
C = proposed reward + dose/compute-matched random-action carrier
D = proposed reward + informed Catfish
```

`B-A` estimates reward-redesign effect, `C-B` carrier/data effect, and `D-C`
informed-mechanism effect. B is the zero-dose Main-only cell; C is the
matched-random carrier cell. This template applies to a Main reward only after
that reward has separate controller authority. The current R2/R3 specialist
signals are private and therefore do not yet authorise a Main-only reward
factorial; if later authorised, their Main semantics first receive a `2^2`
factorial so one reward cannot hide the other's failure.

The experiment sequence is:

1. **Reward-semantics and service-safety gate:** run the Main-only `2^2` design
   only after the outage constraint and physical parameters are closed.
2. **Non-learning shadow gates:** establish C2 boundary support and C3 certified
   bottleneck support, identities, service safety, and proposal advantage versus
   matched random without training.
3. **Carrier parity and representability:** zero-dose/exact-fork tests cover
   successor, next mask, reward vector, RNG, resume, behavior probability, and
   actual fields consumed by Main for a one-focal transition. They also compare
   observationally aliased rows with different hidden bottleneck status and
   focal-only versus complete-bundle Main updates.
4. **Short isolated pilots:** compare each informed specialist against cells B
   and C. C2 must improve ledger temporal EE with steady-state `eta0`
   non-inferior; C3 must improve held-out canonical EE and reduce payload power,
   while the temporal ledger meets its frozen rule and service is preserved.
   Throughput is always reported but is not called non-inferior without an
   independently authorised margin.
5. **Fixed `2^3` informed-selection factorial:** only surviving roles enter a
   preregistered factorial. Every role owns a fixed intervention slot in every
   arm; an off role is replaced by a frozen uniform-random action from the same
   eligible support, never by no action or extra dose for another role. Its
   factor therefore estimates informed specialist selection versus matched
   random selection, not role presence versus zero dose. Report main effects,
   pair interactions, and three-way interaction. The full trio may be called
   jointly best only if the all-informed arm beats each arm with exactly one
   specialist slot randomised under the frozen rule. B remains the separate
   zero-dose Main-only comparison and C the carrier-effect comparison. Every
   informed/random draw uses the identical post-safety eligible support and
   focal trigger.

For every arm, environment steps, executed Catfish transitions, replay rows,
optimizer updates, wall-clock accounting, seeds, and selection opportunities
must be matched or explicitly decomposed. Validation seeds may not be used to
retune triggers, quantiles, calibration, mixture weights, or event parameters.
The preregistration also freezes per-source collection blocks, policy/checkpoint
versions, trigger probabilities, replay quotas and ages, pre-state clustering,
and the off-level matched-random schedule.

## Falsifiers

C2 is not an EE Catfish if sourced timing/energy or state sufficiency cannot be
closed, if its exact temporal endpoint is negligible under the frozen model, or
if it improves neither ledger temporal EE nor service. A temporal-EE gain with
steady-state `eta0` non-inferior is reported as such; it is not renamed an R1
gain.

C3 is not an EE Catfish if certified bottleneck support is too sparse, the
pre-outcome `Delta P_system<0` certificate or one-focal Main transfer fails, it
merely reproduces C1 under a dose-matched comparison, or lower payload power is
bought with throughput/service loss that removes the canonical-EE benefit.

The architecture is not an effective Multi-Catfish if individual roles pass but
their mixed replay causes negative interaction, or if the all-informed trio
does not beat the arms with one specialist slot randomised. In that case the
scientifically correct result is a smaller informed Catfish set, not a post-hoc
mixer or auction.

## Novelty and claim ceiling

C2's exact temporal EE-damage decomposition and boundary-persistence replay,
C3's unilateral marginal-power reward and certified intra-satellite bottleneck
challenge,
and their three-stream/no-action-fusion carrier are **new project proposals**.
They are not yet claimed as globally novel; a dedicated related-work and prior-
art audit is required before manuscript novelty language.

A recent LEO preprint already combines a handover time fraction with an
effective new-link power cost, and terrestrial LTE/NR work already constructs
handover signaling energy from component power and duration. The generic idea
"handover costs time and energy" is therefore not a novelty claim. Any later
claim must be narrower than those model structures and survive the prior-art
audit recorded in the R2 provenance matrix.

No identity in this ADR proves learnability, positive EE effect, or joint
synergy. No existing legacy-narrow checkpoint can answer those questions for
the unresolved primary geometry.

## Required gates before any heavy training

1. Independent review of the revised algebra, one-focal bottleneck certificate,
   incentive directions, outage handling, and separation from C1.
2. Controller closure of ADR-002 primary gain and geometry implementation.
3. Controller closure of the remaining R2 event-to-time mapping under ADR-004;
   out-of-boundary `E_HO` is not a primary prerequisite.
4. A service-constraint ruling that closes reward hacking and segment-reset
   effects; `C_out` alone is insufficient.
5. Absolute unit/identity tests for both proposed rewards and the strict C3
   `Delta P_system<0` certificate.
6. Exact full-transition fork/carrier parity, one-focal Main representability,
   and deterministic resume tests.
7. A self-hashed preregistration separating A/B/C/D causal cells, reward-only
   `2^2`, isolated-role, matched-random off-slot, and final factorial arms.

Heavy training belongs on the Ubuntu server and is not authorised by this
Proposed ADR.
