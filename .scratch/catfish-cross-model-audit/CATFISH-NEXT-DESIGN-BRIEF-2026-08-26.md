# Multi-Catfish next-design review brief

## Material Passport

- Origin Skill: `academic-research-suite` experiment-agent
- Origin Mode: `design-review`
- Origin Date: 2026-08-26
- Verification Status: `REVIEW_INPUT_NOT_A_DESIGN_FREEZE`
- Version Label: `cross_model_input_v1`

## Decision to make

Decide whether the evidence still supports pursuing three genuinely distinct,
training-time Catfish roles, and if so specify the single most defensible next
R2/R3 design direction. The review must not force a three-role story. A ruling
of `KEEP_R1_ONLY`, `KEEP_R1_R2_AND_DROP_R3`, `COUPLE_R3_TO_R1`, or
`CONDITIONAL_THREE` is permitted.

The desired outcome is effectiveness, not role-count symmetry or a convenient
paper story.

## Fixed architecture constraints

1. Catfish is a training-time exploration / experience-distribution mechanism.
   At evaluation and deployment only the Main MODQN chooses the masked greedy
   per-user actions.
2. No post-training auction, coordinator, inter-agent negotiation, action
   override, or acceptance gate is allowed.
3. No transition may be admitted or discarded because its realised reward or
   EE sign was favourable. Branch selection is pre-outcome and every valid
   selected branch is retained. Outcome-filtered replay is closed as biased.
4. Catfish transitions must preserve the exact environment reward vector and
   use the existing single Bellman-update implementation. No Catfish-only
   reward label may leak into Main replay and no second TD target is allowed.
5. Every informed role needs a dose-matched random challenger with the same
   trigger frames, branch count, environment evaluations, replay rows, and
   update count.
6. Three roles are kept only if each has a distinct causal axis, is learnable
   from its authorised pre-action information, changes physical actions, and
   adds held-out value alone or by a preregistered interaction. Naming one
   Catfish after each existing reward is not a contribution.
7. The formal v4 evaluation seeds `2026082601`--`2026082610` may not be reused
   for retuning or a replacement R3 candidate.

## Verified current implementation facts

### R1 and power

- `r1_u = R_u / P_system`; summing over users exactly recovers system EE.
- The live `P_system` already charges realised PA supply power, per-active-beam
  circuit power, and once-per-active-satellite baseband power. A separate
  abstract beam-activation penalty must not be added to R1 and double counted.
- The action-aware power model depends on off-axis angle, association history,
  active physical beams, and the realised joint action.

### R2

- Current R2 is only `0`, `-phi1`, or `-phi2` from association identity.
- Handover currently removes no useful transmission time and adds no
  signalling/access energy in the physical EE numerator or denominator.
- A defensible temporal-EE role therefore requires sourced and frozen
  `T_HO(class)` and/or `E_HO(class)` terms in system truth, plus state/horizon
  sufficiency for future link quality and persistence.

### R3

- Current `r3_u = -U_b`; its population sum is `-sum_b U_b^2`.
- Per-beam bandwidth sharing cancels the direct user-count factor in aggregate
  beam rate when spectral efficiencies are held fixed. R3 affects EE only
  through composition/channel quality, interference, active beams/satellites,
  max-beam power, or service feasibility.
- Previous-step demand is the only load field in the 112-dimensional focal
  observation. It is stale relative to simultaneous current actions.

## Verified action-level evidence

### Existing Q2/Q3 heads

On ten fixed checkpoint seeds:

- Q2 physical-action pivotality: `60.25%`; including Q2 reduced inter-satellite
  handovers but had mean immediate `DeltaEE = -2.156 Mbit/J`, t95
  `[-5.415,+1.103]`, while adding `39.921 W` and `7.52` active beams.
- Q3 physical-action pivotality: `7.72%`; including Q3 reduced
  `sum(load^2)` in every seed but had mean `DeltaEE = -0.765 Mbit/J`, t95
  `[-1.265,-0.265]`, while adding `10.028 W` and `1.70` active beams.

Thus Q2 and Q3 are active, but their current directions are not established as
EE-helpful.

### R2 opportunity

The state-only exact-stay screen found 758 eligible rows; 393 were immediate
EE-positive and service-safe (`51.847%`), with opportunities in all ten seeds.
This is only a local association opportunity under the incomplete physics; it
does not identify the missing handover-time/energy effect.

### Two R3 directions already closed

1. Previous-inactive split: the opportunity label existed in 211/1,000
   held-out rows, but a frozen state-only scorer achieved AUROC `0.549769` and
   AP `0.249874`; accepted `DeltaEE` t95 crossed zero. Action identity explained
   most of the apparent signal.
2. Activation-regularised load potential (ARLP): 917 eligible rows on ten new
   seeds. It was safer and better than matched random by `+0.387609 Mbit/J`,
   but lost to Q1 in every seed by `-0.190279 Mbit/J` with t95
   `[-0.276338,-0.104871]`, and failed to improve its own realised C3.

The narrow falsification is those focal, myopic, previous-demand proposal
contracts. It is not proof that every spatial mechanism is impossible. Any new
R3 must be materially different in observation, credit, horizon, or
intervention unit; it may not retune the rejected formulas.

## Common EE comparison identity

For a candidate and a candidate-independent reference evaluated on the same
pre-decision state and common random numbers, with positive powers,

```text
eta0  = R0 / P0
g_eta = (Rc - R0) - eta0 * (Pc - P0)
DeltaEE = g_eta / Pc
```

The sign identity is exact. It may be logged as an oracle/diagnostic label but
must not become a realised-outcome admission filter. Over a temporal horizon,
replace rate and power with useful bits and energy.

## Geometry issue that must remain independent of treatment success

- Current implementation stores `theta_3dB = 3.32 deg` as full HPBW and uses a
  one-sided half-power angle of `1.66 deg`.
- HOBS Eq. (3) and the cited radius definition imply that its tabulated
  `0.058 rad = 3.323 deg` is one-sided, hence full HPBW is `6.646 deg`.
- Holding physical user/beam offsets fixed, smaller theta makes angle-aware
  gain/power/EE more sensitive. If footprint, pitch, and user geometry are
  rescaled together, much of the relative-angle effect can cancel while
  candidate overlap, load, and handover opportunity change.
- The source-faithful main geometry and the legacy narrow sensitivity arm must
  be declared before outcomes. Geometry may not be selected because it makes a
  Catfish treatment look stronger.
- Changing theta also breaks the current 39-pointing-cell freeze under the
  existing guard-ring rule, and the independent `G0` consistency decision
  remains open. No long training is authorised before that geometry contract
  is re-frozen.

## Questions requiring one primary recommendation

1. Given the negative R3 evidence and missing R2 physics, what is the honest
   role-count ruling now? Distinguish design plausibility from demonstrated
   effectiveness.
2. If `CONDITIONAL_THREE` is still defensible, give exactly one materially new
   R3 mechanism. State its pre-outcome observables, intervention unit, reward
   versus proposal semantics, causal path to system EE, why it is not merely
   R1 duplicated, why it requires no deployment-time coordination, and the
   smallest data-blind falsifier. If none meets those constraints, say so.
3. Give the minimum physically coherent R2 change: system useful-bit/energy
   equations, required state or horizon, parameter provenance gate, and the
   smallest matched falsifier. Do not invent `T_HO` or `E_HO` values.
4. Is a three-scout, outcome-blind branch carrier scientifically coherent when
   all valid branch transitions retain the same full reward vector and share
   one Bellman implementation? Identify any remaining selection, support, or
   credit-assignment bias.
5. Choose the correct theta strategy for mechanism development: HOBS-faithful
   primary plus legacy-narrow sensitivity, legacy-narrow primary, or defer all
   mechanism work until geometry is corrected. Explain which conclusions can
   and cannot transfer across geometries.
6. Specify the single next non-heavy gate and its pre-result pass/fail logic.
   Do not recommend long RL training yet.

Keep repository facts, mathematical inference, reviewer proposal, and future
empirical claims visibly separate.
