# V0.25 engine stage-4b report — 2026-09-08

## Disposition

**IMPLEMENTED / HOLD FOR FORMAL EXECUTION / CONTROLLER_DECIDE.** Stage 4b is
implemented and its synthetic/contract suite passes. No formal provider
manifest, allocation manifest, calibration outcome, real-world rehearsal,
matrix outcome, or admission outcome was opened. The stage-4 compute HOLD
therefore remains in force; no missing formal value is fabricated.

## Delivered contracts

- QoS uncertainty pools useful-user-seconds/full-roster-user-seconds, handover
  events/opportunities, and Phi-cost numerator/denominator additively inside
  every resample. Every EE and QoS ratio is recomputed per draw. The EE contrast
  is relative (`EE_FULL/EE_DROP - 1`), uses a central 95% percentile interval,
  and passes only when its lower bound exceeds `0.005`. A zero-bit cluster stays
  eligible for the pooled primary interval; the paired-log supplement is
  explicitly `UNDEFINED_ZERO_BIT_CLUSTER`.
- The report contract names `a-r0` as the only primary setting and labels all
  others `EXPLORATORY_SENSITIVITY`; it is TRAIN-only. The executable admission
  function reads `a-r0` only, emits `ADMIT`/`NOT_ADMITTED`, and exposes every
  certificate's value, rule and Boolean result.
- Default units prepare 33 steps: 30 executed plus offsets 1/2/3. Production
  converts any interior, D2-aligned event-ledger timestamp to explicit
  duplicate-time left/right limits and passes them to the integrator; unknown
  interior times fail closed. The independent KAT proves that the integrated
  bits and joules change. Present provider ledger transitions occur at the
  decision boundary, so formal calls correctly produce no interior pairs.
- The executable v1.5 decomposition evaluates the complete coalition powerset,
  computes each unilateral `d_i`, `Psi_A`, and exact Shapley interaction credit,
  and fails closed if credits do not conserve `Psi_A`. Its KAT proves the exact
  physical core identity `C1 + C3 = (F(a_A)-F(a0))/kappa`. The selector arms are
  exactly FULL=`C1+C2+C3`, DROP_C1=`C2+C3`, DROP_C2=`C1+C3`, and
  DROP_C3=`C1+C2`, all over the same complete setting catalogue. `UNI` alone
  restricts the catalogue to unilateral moves.
- Learner experiments dispatch to the two-way TLE-date x learner-seed
  pigeonhole bootstrap as primary, with paired-arm product weights and pooled
  ratios recomputed in every draw. The learner-free physics matrix dispatches
  to a one-way TLE-date bootstrap. A crossed synthetic fixture proves the two
  interval laws differ.
- Merge always reports Level B (`FULL` versus `DROP_C3`) and Level A (`FULL`
  versus `S_UNI`) with the selected FULL matched-anchor nonadditivity fraction.
- The launcher runs all four `a-r0` units first and creates `AR0-DONE` only if
  all four exit successfully. It then queues R1, R2, R3, R4, R5=`a′-r0`,
  R6=`a-γ0`, C2-H1, C2-H2, and remaining treatments. Concurrency is capped at
  20. R1–R4 implement respectively 100 Mbit/s, 150 users through the provider
  parameter, and 1.0/0.1 W per active chain. Every receipt binds its run-setting
  digest, classification and regime. R1–R6 receive the full admission
  certificate evaluation and separate “in regime R_k” decisions; none changes
  the primary `a-r0` result.
- The provider/tape protocol makes split, exact start UTC, TLE filenames and
  SHA-256 values, split-rule digest, and provider-source digest mandatory. Tape
  construction takes split from that protocol rather than hardcoding TRAIN.
  The immutable manifest re-verifies these outputs before STARTED is journaled
  or any unit opens. The allocation-manifest builder records the full domain,
  role, UTC, TLE, layout, stream, world-seed, learner-seed and provider identity
  and fails closed on role-wise successor-date overlap. `--allocation` consumes
  explicit identities and refuses to freeze a manifest unless CLAIM_PANEL and
  every declared successor-development role are present.
- The nearest-epoch TLE rule is documented as the per-NORAD date-1/date/date+1,
  absolute-age-at-most-24-hours, future-epoch-permitted, non-causal
  accuracy-first benchmark convention.
- Coupled-solve decisions 1–3 were already implemented before this stage-4b
  pass: 65,536 iterations, absolute-or-relative update convergence,
  `CONVERGED_SLOW`, physical cap-bound infeasibility, and analytic/cap/NaN KATs.
- J1 admission evidence now records its objective margin over U_all, all three
  registered matched-QoS checks against BASE and U_all, and the exact U_all
  configuration. A zero solver update certifies zero numerical F error;
  nonzero residuals are explicitly `UNAVAILABLE_FAIL_CLOSED` rather than being
  misrepresented as objective-error bounds. The gate consumes this conjunction.

## Sealed a-r0 off-axis KAT and figure

- KAT: `probe/figures/a-r0-off-axis-kat.json`, file SHA-256
  `87e8bb4598c1212c823469f33775dc8650dbc7667c2e2623c3ef44d4ad8e7d03`.
- Figure: `probe/figures/a-r0-off-axis-power-ee.svg`, SHA-256
  `cdcd912cdc0ab6b4cff78c3c7847b68a8ee57b5c42e3172647497b23e826cf17`.
- The controlled fixture varies only transmit off-axis angle. Required RF power
  increases strictly and realised pooled EE decreases strictly at angles
  0, 0.5, 1.0, 1.5 and 2.0 degrees. SVG structure/render technical checks pass;
  human visual acceptance remains explicitly pending in the KAT receipt.

## Verification

```text
PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest -q tests/physics_v025
159 passed
```

Additional checks: stage-4b contract `8 passed`; deterministic `--dry-run`
PASS with all 14 arms; v1.5 set-score KAT receipt
`d1abddb27d90996cc7057865a2f078472012db734e4b7cf6800ecd0ee5c8da16`;
`python -m py_compile` PASS; launcher `bash -n` PASS; `git diff --check` PASS;
`git diff -- src/mcrl/env` empty. The off-axis SVG was rasterised at 900x500
and visually inspected after regeneration.

## CONTROLLER_DECIDE

1. The formal real-world rehearsal remains disallowed by the stage-4 measured
   compute gate (>450 s/anchor lower bound versus the binding 10-s Level-B
   coordinator). The
   exact v1.5 powerset counterfactuals add work; shared batched nominal/C2 and
   coalition evaluation must be completed and remeasured before any formal
   manifest, calibration or outcome opens.
2. The bounded-catalogue top-10 rank remains the stage-4 deterministic
   legal-option proxy rather than exact nominal unilateral surplus. This is an
   inherited launch blocker outside the stage-4b additions.
3. After those two blockers close, generate/sign the formal default and R2
   provider-profile manifests, the role-wise allocation manifest, and all 37
   calibrations; then run the bounded rehearsal, seal stride, launch 148 units,
   and execute merge/admission. Until then this package remains HOLD.
4. Coupled-solve receipt item 4 still needs the bounded real-world certificate
   distribution, including the `CONVERGED_SLOW` share. It cannot be produced
   honestly before the compute gate allows the quarantined rehearsal.
5. For nonzero converged solver residuals, admission needs independently proved
   upper/lower F bounds (covering fixed-point power, nonlinear PA energy and ACM
   threshold stability). Until the solver exports those bounds, the J1
   numerical-error certificate deliberately fails closed.
