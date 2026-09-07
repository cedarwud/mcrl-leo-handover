# Multi-Catfish MCRL V0.11 joint-C3 ordered oracle result

Status: **COMPLETE — FAIL CLOSED**  
Decision: **`JOINT_C3_STRUCTURAL_REDESIGN_REQUIRED`**  
Scope: one frozen TRAIN world, three frozen Q1 lineages, oracle surfaces only;
no learner, no optimizer update, no TEST access, and no efficacy claim.

## Verified facts

- All 15 preregistered arm-lineage shards completed.
- The binding merge and the standalone verifier agree exactly.
- Result file SHA-256:
  `c03262af4c99166667e49995f943e309e23f4c799a56bd04825b6f63363f7e7e`.
- Canonical in-result SHA-256:
  `f7a28a6d7c14227103a8b6c39947438fe92f8c298becef247b71b2ef0d2a9f25`.
- All arms retained 3,000/3,000 served user-steps and passed the common
  physical/mechanics assertions.

| Gate | Comparator | Pooled EE direction | Lineages positive | Method passed | Decision |
|---|---|---:|---:|---|---|
| AP-MONE | `FULL_AP` vs `DROP_C3` | -4.443940% | 0/3 | yes | fail |
| M1-D | `FULL_M1D` vs `DROP_C3` | -1.489437% | 0/3 | no | fail |
| exact-O1 diagnostic | `DIAG_O_FULL` vs `DIAG_O_DROP` | -1.196711% | 1/3 | no | fail |

The pooled ratio-of-sums inputs were:

| Arm | Total bits | Total energy (J) | EE (bit/J) |
|---|---:|---:|---:|
| `DROP_C3` | 29,654,551,114,139.89 | 233,573.3423 | 126,960,340.68 |
| `FULL_AP` | 39,824,994,004,360.27 | 328,268.6488 | 121,318,298.74 |
| `FULL_M1D` | 42,480,520,419,659.40 | 339,655.7335 | 125,069,345.91 |
| `DIAG_O_DROP` | 39,510,434,527,027.73 | 283,526.3841 | 139,353,643.07 |
| `DIAG_O_FULL` | 51,248,427,531,138.34 | 372,212.3799 | 137,685,983.30 |

Relative to their matched comparator, AP-MONE increased bits by 34.2964%
but energy by 40.5420%; M1-D increased bits by 43.2513% but energy by
45.4172%; the exact-O1 diagnostic increased bits by 29.7086% but energy by
31.2796%.

M1-D had at least one five-sweep nonconvergence in every lineage.  The
exact-O1 family also had at least one five-sweep nonconvergence in every
lineage.  Fail-closed steps executed the shared C3-free background only, as
preregistered; they cannot rescue either gate.

## Inference bounded by this evidence

The V0.10 failure was not repaired by anticipating joint response through
either antithetic coalition credit or bounded self-consistency.  Frozen-Q1
misalignment is not a sufficient explanation because the exact-O1 diagnostic
also failed in pooled EE and method convergence.  Across all three views, C3
raised delivered bits but expanded network energy more strongly.  The next C3
proposal therefore needs a principled joint-energy or activation-control role,
not another rescaling or sign search of the same opening non-focal-rate target.

This is a development diagnosis, not proof that no three-head method exists.

## Authorized next action

Do not launch a C3 learner or episode training from this result.  First freeze
a structural-redesign contract that keeps the three-head, common-mask,
unweighted-sum, one-argmax deployment invariant and tests at most two
theory-derived C3 candidates on new TRAIN worlds.  Do not change scale, seed,
user order, sweep cap, or acceptance rules against this outcome.

## Verification receipts

- Pre-outcome manifest SHA-256:
  `c46dceaba1c7e4f42c677ff2971501a2cead14ee6a71b879352f7f7f60eeaeb0`.
- Standalone verifier SHA-256:
  `a393d6cf27cbe514adc3fb0dfdfac0a9c13e5add92bcd0b93bdc3eba01845585`.
- Standalone verifier test SHA-256:
  `67eaf3a3d53a5260dd60748e2f345d8e6fdc3697d374b96e85424a03907563e9`.
- Standalone verification status: `PASS`, 15 rows, matching frozen decision.
