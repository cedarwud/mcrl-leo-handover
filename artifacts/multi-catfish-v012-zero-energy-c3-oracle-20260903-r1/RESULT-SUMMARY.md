# Multi-Catfish V0.12 zero-energy C3 oracle result

Date: 2026-09-03 UTC  
Split: TRAIN development worlds only  
Episode training: none  
Learned Q3: none; both FULL arms use oracle C3 surfaces

## Binding result

The frozen V0.12 decision is:

`STOP_C3_ORACLE_REDESIGN_REVIEW_SEAM`

Neither candidate passed the preregistered gate. Both `FULL_ZR` and `FULL_HR`
failed exactly the pooled and per-world active-satellite-step nonincrease
conditions. This STOP is not changed retrospectively.

## Verified development evidence

The clean second attempt completed all 18 preregistered episodes: two worlds,
three frozen Q1 lineages, and three arms (`DROP_C3`, `FULL_ZR`, `FULL_HR`).
All users were served in all arms.

| Quantity | `DROP_C3` | `FULL_ZR` | Difference |
|---|---:|---:|---:|
| total bits | 60,209,118,725,490.875 | 57,545,137,525,591.17 | -4.42455% |
| total energy (J) | 502,418.7521106105 | 477,173.4704532916 | -5.02475% |
| ratio-of-sums EE (bit/J) | 119,838,518.11374167 | 120,595,844.25539435 | +0.631956% |
| served user-steps | 6,000 | 6,000 | 0 |
| active-beam steps | 2,597 | 2,468 | -129 |
| active-satellite steps | 304 | 310 | +6 |

`FULL_HR` produced the same selected actions and aggregate outcomes as
`FULL_ZR`, although the two oracle surfaces differed at every one of the 60
recorded decision steps.

For both ZR and HR:

- EE was positive in both individual worlds: +0.148808% and +1.085793%.
- Exactly two of three lineage contrasts were EE-positive in each world.
- Service was noninferior for all three lineages in both worlds.
- Formula identity, mechanics, support, exposure, current-slot joint support,
  and the active-beam guard passed.
- The active-satellite total increased by six steps; this alone triggered the
  two frozen hard stops.

The independent verifier reauthenticated the contract, runner, sealed source
set, base preregistration, TLE corpus, and Q1 checkpoint bytes, then recomputed
the frozen verdict as STOP. Both the server-side and local verifier passed.

## Inference after the frozen decision

The active-satellite count is a proxy for energy, whereas total trajectory
energy is measured directly and fell by 5.02475%. The six-step increase is
therefore evidence of downstream state drift, but it is not by itself evidence
that ZR harms the canonical EE objective or expands modeled energy.

This inference does not convert V0.12 into a pass and is not an efficacy claim.
The panel contains only two TRAIN worlds and an oracle Q3, not a learned Q3 or
held-out evaluation.

## Independently converged next-step proposal

Fresh-context Fable 5.1 Max and Sol Ultra independently selected the same next
step:

1. preserve the V0.12 STOP;
2. do not redesign the ZR formula;
3. retire HR from active candidate selection;
4. preregister a fresh-world `FULL_ZR` versus `DROP_C3` confirmation;
5. replace both beam-step and satellite-step proxy hard stops symmetrically
   with exact pooled and per-world trajectory-energy nonincrease, retaining the
   two proxy counts as diagnostics;
6. authorize only a separately preregistered Q3 learnability gate if that
   confirmation passes.

The proposal above is prospective. It is not part of the V0.12 frozen gate.

## Claim ceiling

This package supports only a verified TRAIN-world oracle-development result and
a prospective next-step design. It does not establish learned-policy efficacy,
held-out generalization, short-EP readiness, or permission for long training.
