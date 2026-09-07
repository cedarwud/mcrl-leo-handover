# Multi-Catfish design-data plan v0.2

## Material Passport

- Origin Skills: `academic-research-suite` experiment-agent;
  `documentation-and-adrs`
- Origin Mode: `plan`
- Origin Date: 2026-08-26
- Verification Status: `SOL_ULTRA_PASS_TO_FABLE_REVIEW_FABLE_V0_2_PENDING`
- Version Label: `catfish_design_data_v0.2`
- Runtime Authority: none
- Training Authority: none

## Experiment overview

- **Title**: Data-blind counterfactual atlas for RIS-inspired R1 and LEO-native
  R2/R3 Catfish design
- **Objective**: collect only the missing evidence needed to decide whether
  R1 EXP/ACRM, temporal R2, and spatial C3 merit implementation pilots.
- **Type**: evaluation-only simulation plus parameter provenance audit
- **Primary hypothesis**: the audited legacy-geometry episode-8999 checkpoint contains
  pre-action-identifiable, service-safe alternatives on at least the R1 and R2
  causal axes; a third spatial axis is retained only if it adds information
  beyond direct R1 and survives unilateral-transfer checks.

This plan is not a reward freeze and does not claim that three Catfish roles
exist. It intentionally permits the terminal ruling `R1_ONLY`, `R1_R2`, or
`CONDITIONAL_THREE`.

## Why existing data are insufficient

Existing evidence is enough to reject several old directions:

- the episode-8999 checkpoint has finite deterministic evaluation replay under
  the audited legacy geometry; this is narrower than a new corrected-baseline
  or end-to-end reproducibility claim;
- Q2 and Q3 are action-pivotal, so inactivity is not the failure;
- current Q3 improves load spreading but reduces immediate EE;
- previous-inactive and ARLP spatial proposals failed their frozen gates;
- the exact-stay R2 screen found immediate opportunities, but the simulator
  has no physical handover interruption time or access energy.

It is not enough to train the new mechanisms:

1. Existing long runs used the old reward and policy.
2. Episode logs do not retain complete joint transition bundles.
3. The persisted per-user replay cannot reliably reconstruct step-level system
   EE and joint lineage for RIS experience stratification.
4. `evaluate_actions` has exact current-slot physics but no counterfactual
   `next_state` or `next_mask`; those rows are oracle labels, not replay.
5. No existing treatment isolates R1 EXP, R1 ACRM, sourced handover energy/time,
   or a joint-context spatial scout.

More training under the old contract would not close these identification
gaps.

## Decisions carried into the data plan

### R1: fixed scientific truth, proposed RIS-inspired carrier

- Environment and evaluation reward remains `r1_u = R_u/P_system`.
- R1 Catfish candidate uses offline executed experience stratification (EXP)
  and Catfish-only matched ACRM.
- Main receives unshaped full reward vectors from Catfish-origin transitions.
- Same-state outcome-positive branch filtering remains forbidden.
- Full architecture consequences are recorded in
  `docs/decisions/ADR-001-proposed-ris-lineage-r1-catfish.md`.

### R2: temporal continuity, not yet a frozen reward

The minimum one-slot physical candidate is

```text
d_u(t) = max(0, Delta - T_HO(c_u(t)))
B(t)   = sum_u R_u(t) * d_u(t)
E(t)   = P_system(t) * Delta + sum_u E_HO(c_u(t))
eta_HO = B(t) / E(t).
```

`T_HO(class)` and `E_HO(class)` must come from named sources or measurements.
They must cover no handover, intra-satellite beam switch, inter-satellite
handover, re-entry after outage, and episode start. If interruption can exceed
one slot, this algebra is invalid and a remaining-interruption state plus a
multi-step/full-fork evaluation is mandatory.

The current `0/-phi1/-phi2` reward is retained as baseline/diagnostic only
until this gate closes.

### C3: spatial role hypothesis, no independent reward

The old `-U_b`, previous-inactive, ARLP, and leave-one-out A/B reward candidates
are not reopened. C3 is tested only as a training-time joint-context spatial
proposal whose outcome is scored by unchanged system EE.

The single remaining intervention hypothesis is a reciprocal composition
exchange between two already-active physical beams that preserves:

- the complete beam-load vector;
- active-beam and active-satellite sets;
- both users' handover classes; and
- all other users' physical actions.

It is not granted third-role status unless the simultaneous proposal beats
both reference and matched random and its two unilateral component moves pass
a frozen transfer/non-inferiority gate. A pair-only benefit that requires
deployment coordination fails this architecture.

## Research questions and estimands

| ID | Question | Primary estimand | Claim ceiling |
|---|---|---|---|
| RQ1 | Is there locally predictable EE headroom for an optional focal R1 proposal, and is the separate EXP/ACRM transition carrier executable? | proposal-minus-Q1/random `DeltaEE`; corpus/ACRM transition parity | local proposal support and carrier feasibility only; not EXP/ACRM benefit |
| RQ2 | Under sourced handover time/energy, do stay/same-satellite alternatives improve useful bits per joule? | paired `Delta eta_HO` over eligible events | temporal reward plausibility only |
| RQ3 | Does load/activation-preserving spatial composition add EE value beyond R1? | reciprocal-minus-Q1, reciprocal-minus-random, and two unilateral effects | spatial-role plausibility only; not an independent reward |

For every same-state candidate/reference pair with positive power:

```text
eta0    = R0 / P0
g_eta   = (Rc - R0) - eta0 * (Pc - P0)
DeltaEE = g_eta / Pc.
```

This identity is a diagnostic/oracle label. It may not accept or discard a
live branch after its outcome is observed.

## Data reuse and partition policy

### Reuse without new simulation

- Reuse the 758 exact-stay R2 rows for symbolic break-even and parameter-overlay
  development only.
- Reuse baseline and head-pivotality receipts as negative evidence and
  reference operating conditions.
- Do not retune any R3 candidate on formal v4 seeds `2026082601`--`2026082610`.

### New partitions

| Partition | Seeds | Purpose | May influence design? |
|---|---|---|---|
| engineering pilot | `2026082401` | schema, parity, resource estimate only | no scientific decision |
| development | `2026082701`--`2026082710` | fit/freeze pre-action proposal and R2 parameter overlay | yes |
| untouched validation pool | `2026082801`--`2026082830` | first `N` seeds selected by a frozen precision rule before any are opened | no |

Validation seeds are sealed now and must not be evaluated until the proposal,
parameters, feature set, comparisons, and pass rules are hashed. Development
and validation both wait for the geometry contract; only the engineering pilot
may run on the current legacy geometry, with no scientific decision.

## Collection design

### Common reference and sampling

- Checkpoint: episode 8999, SHA-256
  `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`.
- Reference: masked-greedy Q1-only joint action.
- Users/episode: 100; steps/seed: 10.
- Pilot: two focal users per step.
- Development: ten focal users per step without replacement using a dedicated
  frozen sampling RNG. Validation uses the frozen proposal dose and never
  enumerates all actions.
- Every alternative uses the same pre-state and a copied environment RNG.
- Only the Q1 reference commits and advances the episode.
- Every sampled/ineligible row is retained with a reason code.

### Track A: compact focal-action atlas for R1

For each sampled focal state, evaluate one representative of every unique valid
physical `(norad_id, cell_id)` action while all other users retain the Q1
reference action. Enumeration is development-data collection, not a deployable
oracle.

For the first optional R1 proposal, the fit-eligible pre-action surface is
restricted to what the current learner actually receives:

- the focal 112-D encoded state and action mask; and
- the stable relative candidate index needed to address an action.

The physical action key is stored for execution and lineage but is not a model
covariate in this first proposal. A detached Q1 surface/value or any new feature
block is a separate observation-ablation treatment that must be frozen and
exposed equally to its controls before it can enter proposal fitting.

Store receipt-only audit fields separately and forbid them from first-proposal
fitting:

- raw physical action keys, precise association ledger values, D2/TTT, dwell,
  radial-rate, and unencoded candidate metadata;
- reference joint physical intents and expanded pre-action active/load context;
- seed, step, focal-user, candidate, and RNG lineage.

Some audit quantities have an encoded counterpart inside the 112-D state. Only
that encoded counterpart is fit-eligible; the raw or expanded value remains
receipt-only. This prevents the offline atlas from silently granting the
proposal a richer observation than the live learner.

Store compact current-slot outcomes:

- system EE, throughput, consumed power, fixed/PA/beam components available in
  diagnostics;
- service and focal service;
- active beams/satellites, beam load, interference, SINR, and handover class;
- `DeltaR`, `DeltaP`, `g_eta`, `DeltaEE`, and identity residual versus Q1.

Development may fit exactly one pre-action R1 proposal. Its feature list,
model/rule, training seed, and digest are frozen before validation. The oracle
best action is an upper-bound label only and may never select validation
actions directly. The matched random comparator is drawn uniformly from unique
valid physical alternatives that differ from the Q1 reference, using a
dedicated frozen RNG and the same eligible rows.

The untouched validation runner does **not** enumerate or save the complete
action atlas. It evaluates only Q1 reference, the frozen proposal, and the
matched random action. This prevents validation outcomes from becoming a new
mechanism-design dataset.

The atlas is not an EXP/ACRM gate. A shared Catfish policy acting for many users
changes joint interference, load, activation, and successor distributions in a
way a one-focal contrast cannot identify. The first optional proposal pilot is
therefore restricted to exactly one outcome-blind sampled focal user per step.
A multi-user Catfish dose is a later, separately frozen joint-action treatment.

### Track B: R2 parameter overlay and horizon decision

Do not recollect the already-measured immediate exact-stay contrast. First:

1. source and freeze `Delta`, `T_HO(class)`, `E_HO(class)`, network boundary,
   double-count exclusions, the slot-boundary convention, power during
   interruption, and whether steady-state post-interruption rate is valid;
2. apply the one-slot useful-bits/energy equation to existing development rows;
3. decide before validation whether the one-slot model is valid;
4. if not valid, stop and specify a full-fork/remaining-interruption state seam
   before collecting another outcome.

The eventual validation proposal uses only pre-action state and cannot read the
parameter-overlay outcome.

### Track C: reciprocal spatial-composition falsifier

At each pre-state, construct eligible `(u,v)` pairs without current-slot
outcomes. For the frozen informed pair and a uniform matched eligible pair,
evaluate six arms with copied RNG states:

1. Q1 reference;
2. informed reciprocal swap;
3. uniform matched reciprocal swap;
4. `u`-only component move;
5. `v`-only component move; and
6. a dose-matched frozen-R1 arm that simultaneously applies the already-frozen
   112-D-state R1 proposal to both `u` and `v` while all other users retain the
   Q1 reference.

The direct C3-versus-R1 distinctness comparison is eligible only when both
users' frozen R1 proposals independently select a valid action different from
Q1 before any arm outcome is evaluated. Ineligible rows are retained with a
reason code and count against the frozen support denominator. This sixth arm is
an evaluation-only two-user comparator; it does not relax Track A's initial
one-focal deployment dose.

Also record the interaction contrast

```text
I_uv = EE_uv - EE_u - EE_v + EE_reference.
```

The pair ranking may use only masks, physical IDs, Q1 reference actions,
candidate SINR/off-axis state, association/handover class, and deterministic
feasibility. Development is allowed to select and freeze one ranking rule;
validation gets no retuning.

The frozen report must compare reciprocal C3 directly with the sixth,
dose-matched frozen-R1 arm on the same eligible pair/state/RNG lineage. Until a
downstream local-policy transfer test passes, C3 is described only as a
centralized offline data proposal, not a deployable or coordination-free
Catfish.

All declared load, activation, satellite, and handover-class invariants must be
checked against realised physics. An invariant failure is an engineering fail,
not an unfavourable scientific row to discard.

## Expected output schema

| Output | Proposed path | Format | Success criterion |
|---|---|---|---|
| pilot receipt | `.scratch/catfish-design-data/atlas-pilot-v1.json` | JSON | finite, no overwrite, exact preview/commit and CRN identities |
| development receipt | `.scratch/catfish-design-data/atlas-development-v1.json` | JSON | 10 unique seeds; all sampled/ineligible rows accounted |
| frozen proposal bundle | `.scratch/catfish-design-data/proposal-freeze-v1.json` | JSON | self-hash; features/rules/parameters/pass gates complete |
| validation receipts | `.scratch/catfish-design-data/validation-{r1,r2,c3}-v1.json` | JSON | exact frozen track digest and selected `N`; only preregistered track-specific arms; no validation all-action atlas; one-shot decision |
| report | `.scratch/catfish-design-data/DESIGN-DATA-REPORT-v1.md` | Markdown | evidence/inference/recommendation and claim ceiling separated |

Large arrays must not be duplicated per candidate. Store focal state once and
candidate rows by stable ID so the receipt remains auditable without repeating
112-D vectors for every action.

## Analysis plan and pass rules

The evaluation seed is the independent unit. Nested users/actions/steps are not
treated as independent replicates. Report pooled descriptions plus seed-level
means and seed-clustered t95 intervals. No subgroup rescue is allowed after
validation outcomes.

### Precision and decision-rule freeze

The current `8/10`, `10%`, `1%`, and `+0.5 percentage point` values are not
treated as validated universal thresholds. Before opening any validation seed,
a controller-owned precision memo must freeze:

- a minimum important effect in physical EE units;
- the validation cluster count `N` selected from the first `N` seeds of the
  reserved pool using only development variance, with `10 <= N <= 30`;
- the exact seed-clustered comparison statistic and confidence interval;
- minimum eligible support and every denominator/tie rule;
- service-unsafety definition and an upper confidence bound;
- matched-random comparison statistic;
- R2 source-uncertainty grid and reversal rule; and
- C3 unilateral non-inferiority margin and interaction decision.

No validation runner is implementation-ready until this memo is self-hashed.

### R1 opportunity and carrier gates

An optional focal proposal passes only if the frozen pre-action rule:

1. has eligible support in every validation seed;
2. changes exactly one sampled focal physical action on its declared eligible
   rows;
3. exceeds the frozen minimum important `DeltaEE` versus Q1 and has a
   seed-clustered lower confidence endpoint above zero;
4. beats dose-matched random under the frozen paired statistic; and
5. keeps the frozen upper confidence bound on service unsafety within its
   operational limit.

This result neither passes nor fails RIS-inspired EXP/ACRM. That carrier
advances only when the master-corpus generator, one-action-per-state rule,
bundle stratification, frozen Main comparator, Catfish-authoritative successor,
calibration order, and resume/RNG parity are executable and tested. Its benefit
requires a separate short learning pilot with EXP, ACRM, EXP+ACRM, and
equal-budget controls.

### R2 physics and runtime gates

R2 passes to a short temporal-Catfish implementation pilot only if:

1. every `T_HO/E_HO` value and timing boundary has accepted provenance;
2. the state/horizon is sufficient for the largest sourced interruption;
3. the frozen proposal exceeds the minimum important `Delta eta_HO` and has a
   seed-clustered lower confidence endpoint above zero;
4. it beats matched random and meets the same service safety bound;
5. sensitivity over preregistered source uncertainty does not reverse the
   primary direction; and
6. before any temporal-Catfish learning, `B/E` is wired into a bounded
   evaluation/accounting seam whose units, slot timing, power boundary, reward
   calibration, no-double-count rule, successor, next mask, RNG, resume state,
   and—when needed—remaining-interruption state all pass parity tests.

Failure of provenance or state sufficiency closes the EE claim while permitting
the old handover penalty to remain a QoS diagnostic.

### C3-S shadow gate

C3-S may be proposed for a controller-authorized, centralized training-only
scout only if:

1. eligibility support and all invariants pass in every validation seed;
2. informed reciprocal EE exceeds the frozen minimum important effect versus
   Q1 and matched reciprocal random, with seed-clustered lower confidence
   endpoints above zero;
3. both unilateral component arms meet the frozen non-inferiority margin versus
   Q1 and do not violate service safety;
4. the interaction contrast and direct dose-matched R1 comparison satisfy the
   frozen distinctness rule;
5. no Catfish-only R3 reward is required to state the mechanism.

Passing C3-S does not establish a third role and does not authorize a
three-role factorial. It only permits a separate bounded scout proposal after
an explicit controller ruling lifts the relevant G-6 scope.

### C3-L post-learning local-transfer gate

Only after a C3-S scout exists may a separately preregistered C3-L test ask
whether the learned joint-context behavior transfers to independently executed
local policies without deployment-time coordination. The transfer must retain
the frozen EE/service margins, action dose, and held-out lineage. Only a C3-L
pass permits the label `conditional third role` and entry into a three-role
factorial. Failure closes C3 under the current architecture and does not trigger
another R3 reward retune.

## Proposed commands and worker routing

The runner does not exist yet. These commands are interface targets for the
implementation gate, not commands authorised by this plan.

```bash
.venv/bin/python scripts/run_catfish_design_atlas.py \
  --stage pilot \
  --output .scratch/catfish-design-data/atlas-pilot-v1.json

.venv/bin/python scripts/run_catfish_design_atlas.py \
  --stage development \
  --output .scratch/catfish-design-data/atlas-development-v1.json
```

- **Non-heavy pilot**: estimated 2--5 minutes and about 3 GB peak RSS; may run
  in the current environment after implementation/tests and a no-writer check.
- **Heavy development atlas**: estimated 20--40 minutes and about 3--5 GB peak
  RSS. Run on the Ubuntu server because all-action enumeration does not need a
  browser and competes with WSL2 resources.
- **Non-heavy frozen validation candidate**: expected to be much smaller because it
  evaluates only frozen proposal/control arms. Re-estimate from the pilot
  receipt before deciding its host.

Heavy worker setup, when authorised:

1. SSH to the Ubuntu server.
2. Sync a clean scoped copy of the repo, frozen checkpoint/prereg/TLE manifest,
   runner, tests, and spec digest without overwriting completed artifacts.
3. Confirm Python 3.13.3, Torch 2.13.0, NumPy 2.5.2, SGP4 2.27, available RAM,
   and an empty output path.
4. Open a fresh Codex worker session in the synced checkout.
5. Paste the separately generated bounded heavy-worker prompt only after the
   pilot and cross-model design review pass.

## Monitoring and stop rules

- Default pilot timeout: 15 minutes.
- Development/validation hard timeout: 60 minutes per partition.
- Monitor terminal receipt, output growth, elapsed time, and maximum RSS.
- Never overwrite an existing receipt and never auto-retry a failure.
- Abort on non-finite physics, preview/commit mismatch, CRN identity failure,
  proposal/spec digest mismatch, seed overlap, or incomplete row accounting.
- Do not run validation if development fails or if the proposal bundle is not
  frozen.
- Do not run any RL training from this document.

## Geometry and authority gates

Outcome-bearing development or validation cannot start until the HOBS-faithful primary versus
legacy-narrow sensitivity geometry, `G0`, aperture interpretation, lattice,
pointing-cell IDs/count, and coverage rules are independently frozen. An
engineering pilot on legacy geometry has no transferable scientific claim.

If that freeze changes the geometry used to train checkpoint episode 8999, the
checkpoint is sensitivity-only. A new matched reference checkpoint and source
receipt are required before primary-geometry development; running the old
checkpoint under new physics is not a matched baseline.

The proposal freeze must also bind scenario start epochs, geometry stratum,
checkpoint, TLE manifest, all seed-to-RNG stream mappings, and behavior-policy
lineage.

MCRL G-6 remains in force. Probe code may be evaluation-only and isolated, but
no Catfish learner, replay injection, ACRM, reward change, deployment selector,
auction, or coordinator is authorised by this plan.

## Terminal decisions

| Evidence outcome | Permitted next design |
|---|---|
| R1 carrier parity passes | RIS-inspired EXP/ACRM short pilot; atlas proposal is optional |
| R1 carrier plus R2 physics/runtime parity pass | two-role EE + temporal Catfish short factorial |
| R1 carrier, R2 physics/runtime parity, C3-S, and C3-L pass | conditional three-role short factorial |
| any role fails safety/identity | close that role before training |
| all proposal gates fail | retain the audited episode-8999 legacy-geometry reference; require a future matched reference for any new primary geometry; do not manufacture Catfish roles |

## Immediate next gate

The first Sol Ultra fresh-context review returned
`REVISE_BEFORE_IMPLEMENTATION`. A closure audit found cross-document R1 gating,
C3 staging/comparator, R2 runtime, and receipt-language inconsistencies; those
findings were incorporated. A final fresh-context clean read then returned
`PASS_TO_FABLE_REVIEW` with no blocker or major. The current Fable Max v0.2
review attempt returned no scientific result because the provider session limit
was reached; the earlier Fable review of v0.1 does not substitute for review of
this material. Therefore the cross-model gate remains open and no runner is
authorised.

On retry, the reviewers must decide:

1. whether offline EE stratification is a scientifically acceptable
   RIS-inspired adaptation that preserves EXP's core concept without reopening
   same-state outcome cherry-picking;
2. whether ACRM can remain Catfish-only while Main receives unshaped vectors;
3. whether the focal action atlas can identify an R1 proposal without becoming
   a deployment oracle;
4. whether the R2 parameter overlay and C3 unilateral-transfer gates are
   sufficient;
5. whether any pass threshold or reserved seed choice is underjustified.

No runner implementation begins until this review is adjudicated.
