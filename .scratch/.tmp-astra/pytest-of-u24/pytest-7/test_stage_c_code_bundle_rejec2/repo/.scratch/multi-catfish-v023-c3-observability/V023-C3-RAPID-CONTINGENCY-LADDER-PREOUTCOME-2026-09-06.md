# V0.23 C3 rapid contingency ladder

Date: 2026-09-06 (written before the R4 world-2026121706 replay outcome)

Status: `FROZEN_PREOUTCOME_CONTINGENCY_DESIGN / NO_LAUNCH / NOT_CURRENT_AUTHORITY`

This document reduces the delay after a possible scientific failure of the
sealed V0.23 LC-SRS gate.  It does not modify, rescue, reinterpret, or compete
with the running R4 execution.  The V0.23 result must be adjudicated under its
existing frozen contract.

## 1. What may and may not run in parallel

Parallel versions of a floating-point tolerance, sign, multiplier, horizon,
threshold, world list, or seed list are forbidden.  Selecting the version that
looks best after opening outcomes would be outcome tuning.

Parallel *causal mechanism families* are allowed when their formulas, order,
inputs, worlds, and kill rules are fixed before their outcomes.  A shared
physical tape should be evaluated once and used to compute all declared target
families so that adding a candidate does not multiply the expensive simulator
work.

## 2. Locked candidate order

1. `L`: the current LC-SRS mechanism.  It remains the only candidate in the
   running V0.23 gate.
2. `D`: cost-shared externality (CSE), the first contingency candidate.
3. `F`: energy-share correction (EC), a deliberately simpler diagnostic and
   second contingency candidate.

For a frozen Q1+Q2 reference joint action `b`, focal user `u`, unilateral
candidate configuration `c`, current-slot duration `dt`, network energy `E`,
and correctly frozen reference price `lambda`, define

```
share_u(x) = beam_energy(x, beam(u)) / beam_occupancy(x, beam(u))
           + satellite_baseband_energy(x, sat(u))
             / served_satellite_occupancy(x, sat(u))
```

with zero share for an unserved user.  Candidate `D` is

```
z_D(u,a) = dt * sum_{v != u} [R_v(c) - R_v(b)]
           - lambda * ( [share_u(c) - share_u(b)]
                        - [E(c) - E(b)] )
```

and candidate `F` is its energy-only correction:

```
z_F(u,a) = -lambda * ( [share_u(c) - share_u(b)]
                       - [E(c) - E(b)] )
```

No compatibility gate, clipping, sign filtering, rescaling, or post-outcome
formula variant is allowed.  `D` has priority over `F`; this is not a
best-observed-score contest.  If `D` passes its fixed screen it is selected.
`F` is considered only if `D` fails and `F` independently passes.

## 3. Rapid funnel

### F0: formula and tape feasibility (local, non-heavy)

Implement both targets as pure functions over one immutable unilateral
evaluation tape.  Require exact cost-share conservation, reference centring,
finite outputs, mask preservation, and deterministic replay.  No simulation
outcome may change the formulas.

### F1: shared two-step kill screen (Ubuntu server, heavy)

Use fresh TRAIN world `2026121721`, frozen lineage `2026092101`, the first two
canonical decision steps, and one common keyed field.  Generate the physical
unilateral tape once; evaluate `BASE=Q1+Q2`, `D`, and `F` from the same tape.
This screen can stop spending but cannot establish efficacy.

A candidate survives only if all integrity checks pass, it changes at least
one legal action, service is not lower than BASE by more than 0.001, and its
pooled ratio-of-sums EE is strictly above BASE.  Failure is
`FAST_SCREEN_NO_SUPPORT`, not a structural impossibility claim.

### F2: shared four-world oracle screen (Ubuntu server, heavy)

Survivors use fresh TRAIN worlds `2026121721`--`2026121724`, frozen lineages
`2026092101`--`2026092103`, ten canonical steps, and matched keyed fields.
The same physical tape is shared by `D` and `F`.  A candidate passes only with
positive pooled ratio-of-sums EE versus BASE, positive directions in at least
3/4 worlds and 2/3 lineages, service non-inferiority margin 0.001, and complete
mechanics/provenance receipts.

### F3: source-to-learner screen

Only the first candidate in the locked order that passed F2 receives an
INFORMED-versus-equal-budget-NEUTRAL learner screen.  Source-update checkpoints
are `0,100,200,300,400,500,600,700,800,900,1000,1100,1200,1300,1400,1500,1600,1700,1800,1900,2000`
for each of three fixed learner seeds.  This is source-update training, not
episode training.

### F4: fixed-policy physical evaluation

Only after F3 passes may a separately frozen physical evaluation run at 100,
500, 1500, and 3000 episodes, with a checkpoint every 100 episodes.  The
9000-episode run remains a later user-notified decision.  True Catfish
ablations use equal-budget neutral-source replacement and retraining; dropping
a score head is secondary diagnosis only.

## 4. Branching after the sealed V0.23 result

- `GO_FIXED_LEARNER_SCREEN_CONTRACT`: keep `L`; do not open F1/F2.
- `STOP_PHYSICS`: open F0/F1 for `D` and `F` in parallel on the shared tape.
- `STOP_OBSERVABILITY`: do not change the LC-SRS target.  A new, pre-outcome
  interface/learner contract is required; `D`/`F` are not an automatic rescue.
- `REDESIGN_INTERFACE`: keep the physical teacher and design a new interface
  under a separate frozen contract; do not select an interface against the
  opened V0.23 worlds.
- `INVALID_RUN`: repair only the demonstrated execution defect and replay the
  smallest failing unit before rerunning the sealed gate.

## 5. Claim ceiling

This is a latency-reduction and contingency-design receipt.  It authorizes no
new run and provides no evidence that LC-SRS, CSE, EC, C1, C2, C3, FULL, or any
ablation improves EE.
