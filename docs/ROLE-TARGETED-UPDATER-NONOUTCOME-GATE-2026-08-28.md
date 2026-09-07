# Role-targeted updater non-outcome gate

Date: 2026-08-28  
Status: scratch prototype/unit gate PASS; runner integration and efficacy NO-GO

## Implemented candidate

The rejected all-head `update_main_with_source_quota()` remains a historical
carrier and is not authorized for the new design. A separate scratch function
implements the diagonal consumer:

```text
.scratch/smc-er-short-ep/smc_er_core.py
update_main_with_role_targeted_donors(...)
```

It implements the proposed diagonal consumer:

```text
C1 -> Main objective 0 only
C2 -> Main objective 1 only
C3 -> Main objective 2 only
L_j = 0.75 L_MainReplay,j + 0.25 L_Cj,j
```

The actual canonical Main replay sample is used in all three objective losses.
A missing or unusable role has effective donor fraction zero and cannot lend
its dose to another role. No routed source delegates directly to the canonical
`main.update()` path. Private specialist rewards/provenance are excluded from
Main; off-target canonical donor losses are receipt-only under `no_grad`.
Both routed functions now defer durable bundle-ledger admission until canonical
Main replay has reached its batch threshold. Warm-up therefore performs no
optimizer step, consumes no replay RNG sample, and does not burn a donor bundle
that can be learned later. Ledger validation is also two-phase: duplicate IDs
are rejected before sampling, while durable commit occurs only after all three
optimizer steps and finite-parameter checks succeed. An injected optimizer
failure leaves the ledger uncommitted.

## Verification

Command:

```text
.venv/bin/python -m pytest -q \
  .scratch/smc-er-short-ep/test_smc_er_core.py \
  .scratch/smc-er-short-ep/test_sweep_evaluation.py
```

Result: `43 passed`.

The focused tests cover:

- exact zero-source delegation;
- actual canonical replay sample use;
- C1, C2, and C3 donor-reward perturbations changing only their matching Main
  objective DQN;
- exact canonical equivalence when a scheduled role is missing;
- equality of the missing-role path's optimizer states, replay-sample count,
  replay RNG object use, and final RNG state with the canonical update;
- fixed C1/C2/C3 mapping and off-target `no_grad` audit receipts;
- private C1 field exclusion;
- missing/unusable zero-dose behavior and no dose borrowing;
- source/bundle uniqueness, durable duplicate rejection, and donor-fraction
  validation;
- warm-up deferral with an unchanged ledger followed by successful admission
  of the exact same donor once an update is possible;
- nonmutating ledger preflight and no durable commit after an injected optimizer
  failure; and
- ratio-of-sums rather than mean-of-ratios evaluation, equal training-seed
  weighting, and impossible zero-energy rejection.

Bound SHA-256 at this receipt:

| File | SHA-256 |
|---|---|
| `.scratch/smc-er-short-ep/smc_er_core.py` | `3d7e488deda216f34e24a4ad587d78b52f652a36e195119092948be158c0b6b3` |
| `.scratch/smc-er-short-ep/test_smc_er_core.py` | `44665da9e527cc374ce09fdda7ce344cd290e0608402b4e5d75ffabecdf9b04f` |
| `.scratch/smc-er-short-ep/sweep_evaluation.py` | `a4dcae189073d0c1ad90c532d0d78dae7dc8f0130dd1e0b7a7bb635347b17f45` |
| `.scratch/smc-er-short-ep/test_sweep_evaluation.py` | `9879f6a34e4cdb152b4302c535bf5e91f4d504680579b76b4e8879b4b87adc04` |

## What this does not prove

- No existing short-episode runner has been switched to the new function.
- No reference updater outside the scratch module has yet replayed a complete
  multi-role optimizer-state trajectory.
- No production resume/checkpoint receipt is bound to the new carrier.
- An exception can still leave in-memory optimizer parameters partially
  updated even though the donor ledger is uncommitted; a production runner must
  restore an exact pre-update snapshot or abort from the last atomic checkpoint
  before any outcome-bearing route is authorized.
- No C1/C2/C3 donor has passed its observational-alias, off-support,
  scalarized-pivotality, or fresh-seed EE gate.
- No outcome-bearing screen or training was run.

The next safe carrier step is a deterministic reference-equivalence and resume
fixture using the new function, followed by a frozen three-arm C1 developmental
screen. Formal training remains NO-GO.
