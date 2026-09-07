# Three-role Catfish design v0.1

## Material Passport

- Origin Skill: `academic-research-suite` experiment-agent
- Origin Mode: `design`
- Origin Date: 2026-08-26
- Verification Status: `DESIGN_DRAFT_NOT_IMPLEMENTED`
- Version Label: `catfish_three_role_v0.1`

## Decision

The design target remains **conditional three**, but three roles are not
frozen and no effectiveness claim is allowed.

| Scout | Causal axis | Current status |
|---|---|---|
| C1 Energy Frontier | immediate radio/link choice and realised system EE | physical endpoint complete; Catfish learning benefit untested |
| C2 Temporal Continuity | handover interruption, access energy, and future persistence | provisional; physics and state incomplete |
| C3 Spatial Composition | user-to-beam composition at fixed load/activation/handover class | one final shadow hypothesis; not yet an R3 role |

The old R3 previous-inactive split and activation-regularised load-potential
(ARLP) directions are permanently closed under their frozen contracts. C3 may
continue only through the materially different reciprocal-composition gate
below. A failure there reduces the architecture to R1 plus provisional R2; it
does not trigger another R3 retune.

## Claim ceiling

This document specifies a falsifiable design and gate sequence. It does not
show that:

- any Catfish training improves held-out EE;
- three roles are necessary or jointly best;
- R2 has a physical EE effect;
- the new C3 proposal is learnable or reproducible by Main;
- current narrow-geometry effect sizes transfer to HOBS-faithful geometry;
- the post-run checkpoint audits are byte-identical launched-source replays.

## Shared carrier

Catfish is a training-time exploration carrier, not a deployment component.

1. A scout and its intervention budget are selected from pre-outcome state,
   masks, detached policy surfaces, physical IDs, and an independent RNG.
2. The selected valid intervention is executed on the real training trajectory
   and retained regardless of realised reward sign.
3. The environment supplies the exact branch-specific full reward vector and
   next state. The existing single MODQN Bellman implementation consumes it.
4. No Catfish-only label enters Main replay. No second TD target, outcome-based
   acceptance, auction, coordinator, or post-training action override exists.
5. Every informed scout is compared with a dose-matched random challenger at
   the same trigger frames, action-change count, environment steps, replay
   rows, and update count.
6. At evaluation/deployment, scout dose is exactly zero and only Main MODQN
   performs the existing masked greedy action selection.

The current `evaluate_actions` seam remains a one-step oracle only. It returns
current-slot physics/reward but no branch-specific next observation or next
mask, so it must not be presented as a replay carrier. Shadow gates may use
that seam; training, if later authorised, uses executed interventions or first
passes an exact full-fork transition-equivalence gate.

## Common EE certificate

For a candidate-independent reference `(R0,P0)` and a candidate `(Rc,Pc)` on
the same pre-decision state and common random numbers, with positive power,

```text
eta0  = R0 / P0
g_eta = (Rc - R0) - eta0 * (Pc - P0)
DeltaEE = g_eta / Pc
```

This is an exact identity. The realised `g_eta` is an oracle label for analysis
and preregistered gate adjudication only. It may not select or filter a replay
transition after its outcome is observed. Service, outage, throughput, and
power remain mandatory companion endpoints.

## C1 — Energy-Frontier Scout

### Role

Perturb near an EE action boundary so Main observes alternatives on the direct
system-EE frontier. The endpoint is system `sum_u r1_u`, never only the moved
user's `r1_u`.

### Proposal information

Current masks, candidate SINR/off-axis angle, association state, detached Q1,
and a precommitted uncertainty/near-boundary trigger. No realised outcome may
enter proposal selection.

### Falsifier

Against a dose-matched random valid alternative, C1 must change physical action
support and later improve held-out Main EE without violating service. A shadow
oracle opportunity by itself is insufficient.

## C2 — Temporal-Continuity Scout

### Required physical truth

For slot length `Delta`, handover class `c_u(t)`, and class-specific sourced
parameters, the minimum single-slot form is

```text
d_u(t) = max(0, Delta - T_HO(c_u(t)))
B(t)   = sum_u R_u(t) * d_u(t)
E(t)   = P_system(t) * Delta + sum_u E_HO(c_u(t))
eta_HO = B(t) / E(t)
```

`T_HO(none)=E_HO(none)=0`. If any interruption can exceed one slot, or power
continues under a different regime during interruption, this approximation is
invalid: the environment needs a remaining-interruption timer and a multi-step
bits/energy horizon.

The class mapping must explicitly cover intra-satellite beam switch,
inter-satellite handover, re-entry after outage, and episode start. Parameter
sources, network boundary, overlap with existing power terms, uncertainty, and
slot timing must be frozen before looking at outcome-bearing runs. No value is
invented in this design.

### Required state

At minimum, Main must be able to distinguish current association, previous
served/unserved state, remaining interruption time, and enough persistence
information to value stay versus switch. Candidate additions include segment
age/current recurrence power plus the already available dwell/radial/TTT
contract fields, but the exact minimal block requires a state-sufficiency gate.

### Falsifier

On new seeds, compare a pre-outcome temporal proposal with a dose-matched
random eligible alternative using common random numbers and a frozen
short-horizon useful-bits/energy endpoint. Failure to source non-negligible
`T_HO/E_HO`, failure of state sufficiency, or failure of paired EE/service
safeguards closes R2 as an EE role while retaining it only as a QoS objective.

## C3 — Reciprocal Spatial-Composition Scout

### Purpose and non-claim

This is the only remaining R3 hypothesis. It is not yet an R3 reward and may
not be called the third effective Catfish. It tests spatial composition while
removing the load-spreading and activation changes that defeated the previous
R3 candidates.

### Reference and eligibility

Let `a0` be a frozen Q1-only masked-greedy joint action and `b_u` the physical
beam chosen for user `u`. A pair `(u,v)` is eligible only if:

1. `b_u != b_v`;
2. `u` can validly choose `b_v` and `v` can validly choose `b_u`;
3. the reciprocal exchange preserves both users' handover classes;
4. feasibility is determined from authorised pre-outcome information; and
5. physical IDs are unique, with a deterministic tie-break.

The branch exchanges the two physical beams and leaves every other user
unchanged. The complete physical load vector, active-beam set,
active-satellite set, and handover-class vector must be identical to reference.

### Informed proposal

The proposal may read current masks and physical mappings, Q1 reference action,
candidate SINR/off-axis angle, association ledger, and deterministic power
feasibility. It may not read realised rate, reward, power, EE, or `g_eta`.

Among eligible pairs, the first shadow hypothesis requires both users'
candidate SINR to be non-decreasing and at least one to improve, ranked by a
frozen sum-log-SINR score and physical-ID tie-break. This rule is frozen before
new outcome seeds and receives no coefficient sweep.

### Distinct causal question

At fixed load, activation, and handover class, composition can still change
off-axis gain, useful rate, recurrence/max beam power, PA supply, and
interference. The scout alters joint action support; it does not define another
EE reward. Whether that is sufficiently distinct from C1 is an empirical gate,
not an accepted claim.

### Mandatory shadow arms

Evaluate from identical pre-states and common random numbers:

- Q1 reference;
- informed reciprocal swap;
- uniform matched eligible reciprocal swap;
- `u`-only move;
- `v`-only move.

The unilateral arms are mandatory. If only the simultaneous swap is helpful
while either unilateral move is harmful, the effect depends on coordinated
deployment and C3 fails this architecture.

### Pass/fail boundary

The gate uses wholly new seeds and a pre-frozen eligibility census. It passes
only if:

1. the sealed minimum eligible support is met;
2. all load/activation/satellite/handover invariants hold exactly;
3. service/outage safeguards are non-inferior;
4. informed-minus-reference and informed-minus-random seed-level paired EE
   intervals exclude zero in the positive direction; and
5. both unilateral arms pass a pre-frozen non-inferiority rule.

Failure closes this C3 direction without retuning. Passing only grants a later
training-preregistration gate; it does not establish an R3 reward, Main
learnability, or three-role effectiveness.

## Geometry contract

Mechanism success may not decide antenna geometry.

- Primary scientific geometry: HOBS-faithful one-sided half-power angle
  `0.058 rad = 3.323155 deg`, represented by this codebase as full HPBW
  `6.646310 deg` and halved once inside the antenna/cell API.
- Sensitivity arm: legacy narrow full HPBW `3.32 deg`, one-sided `1.66 deg`.
- Before any outcome-bearing new mechanism gate, refreeze `G0`, aperture
  interpretation, cell radius, pitch, lattice crop/guard, pointing-cell IDs
  and count, coverage, seeds, and primary/sensitivity analysis rules.
- Do not force the old 39 pointing cells if the source-faithful lattice cannot
  supply them. Do not carry `G0=2000` silently into the wider beam.

Holding physical offsets fixed, the narrow beam makes angle-aware gain/power
more sensitive. Rescaling the cell geometry with the beam can cancel much of
that relative-angle effect while changing candidate overlap, load, and
handover opportunity. Therefore current narrow-geometry effect sizes do not
transfer to the source-faithful primary.

## Gate order

1. **Geometry-contract refreeze** — non-heavy, no treatment outcomes.
2. **R2 physical-parameter and state-sufficiency gate** — non-heavy design and
   evaluation-only falsifier; no invented values.
3. **C3 reciprocal-composition shadow gate** — non-heavy, new seeds, no
   training, no retuning.
4. **Executed-intervention carrier parity** — zero-dose equivalence, RNG/state
   parity, exact reward/next-state provenance, fixed budget and random control.
5. **Only if all role gates survive:** preregister a heavy `2^3` role factorial
   with dose-matched controls on the Ubuntu server. Report main effects,
   interactions, and exact three-player attribution. The full trio must beat
   every leave-one-out pair within the frozen inference rule.

No heavy training is authorised by v0.1.

