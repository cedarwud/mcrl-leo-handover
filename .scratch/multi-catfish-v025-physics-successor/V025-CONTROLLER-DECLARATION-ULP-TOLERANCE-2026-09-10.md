# Declared change — the replay parity gate is relaxed from bit-exact to 2 ULP

**2026-09-10. Written BEFORE any demand-capped result exists. No sealed constant,
threshold, sign, seed, horizon, price, guard, acceptance rule, artefact or manifest is
changed. This changes a gate in a controller-authored diagnostic prompt, not in the science.**

## What happened

`MSCAP` was asked to replay 128 recorded multi-start endpoints and confirm the pooled
capacity efficiency reproduced the receipts **at binary64**, stopping if it did not. That
gate was written by the controller.

It failed on 5 of 128 endpoints, 9 field values in all. The worker stopped as instructed and
reported no capped result. **It followed the instruction correctly.**

## Why the gate was wrong

Every one of the nine mismatches is **exactly one unit in the last place**:

| field | relative difference | ULP of the value | mismatch / ULP |
|---|---:|---:|---:|
| bits (w3/s1) | 1.710e-16 | 1.526e-05 | **1.00** |
| ee_bit_per_j (w3/s1) | 1.880e-16 | 7.451e-09 | **1.00** |
| bits (w4/s0) | 1.917e-16 | 1.526e-05 | **1.00** |
| joules (w4/s0) | 1.847e-16 | 4.547e-13 | **1.00** |
| joules (w1/s0) | 1.314e-16 | 4.547e-13 | **1.00** |
| joules (w1/s1) | 1.325e-16 | 4.547e-13 | **1.00** |
| ee_bit_per_j (w1/s1) | 1.602e-16 | 7.451e-09 | **1.00** |
| joules (w3/s1) | 1.352e-16 | 4.547e-13 | **1.00** |
| ee_bit_per_j (w3/s1) | 1.590e-16 | 7.451e-09 | **1.00** |

Double precision epsilon is 2.220e-16. Nine out of nine at exactly 1 ULP is the signature of
**summation order**, not of a physical or accounting discrepancy. Floating-point addition is
not associative; a replay that pools in a different order than the recording cannot be
bit-identical, and demanding that it be is a defect in the gate.

This is corroborated independently: `EVALPATH-2026-09-10.md` reports that with both
evaluation paths on all 48 boundaries, realised-field parity is "numerical but never fully
binary64-identical in this sample."

## The declared change

**The replay parity gate becomes: every replayed field must agree with its receipt to within
2 ULP of the receipt value, and the count of fields exceeding 1 ULP must be reported.**
Any mismatch above 2 ULP still stops the job.

## Why this is not tuning against an observed result

- The quantity being gated is **instrument reproducibility**, not any scientific outcome.
  No route's sign, no EE figure, and no acceptance rule depends on it.
- **No demand-capped number has been computed.** The job stopped before producing one, so
  there is no observed result to tune toward. The relaxation is declared while the outcome
  is still unknown.
- The new tolerance is fixed by IEEE 754, not chosen to admit the observed mismatches: 1 ULP
  is the smallest representable disagreement, and the bound is set at 2 ULP before rerunning.
- The rerun is **not outcome-selected**. It is a rerun of a job that produced **no** result,
  for a reason established to be an artefact of the gate.

## What is still owed

The `EVALPATH` finding that global path authority is `UNDETERMINED` is **not** resolved by
this declaration and is not affected by it. It remains on the owed-repair register.
