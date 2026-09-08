# V0.25 engine stage-4 report — 2026-09-08

## Disposition

**HOLD / CONTROLLER_DECIDE.** The stage-4 correctness and provider integration
work is materially advanced, but the real-world compute gate is not met. Formal
R2 manifests, calibration outcomes, the three-anchor rehearsal, and the
development smoke were not opened because development measurements already put
them beyond their binding budgets. No q, calibration value, world digest,
stride, or smoke outcome was fabricated.

## Implemented

- Each selected step is anchored under all three fixed carriers; the default
  30 steps produce 90 anchors/world and each carries offsets 1/2/3.
  `--anchor-stride` defaults to 1, is receipted, and merge rejects mixed values.
- The size-guarded catalogue uses complete Cartesian enumeration through 4,096
  configurations and otherwise includes every unilateral, two proposal sets,
  top-10/top-two pairs, and per-active-beam evacuations, with a 3,200 hard cap.
  Zero-option users receive explicit null actions. Receipts include the full
  catalogue digest and shortlist-miss/null counts.
- Pair C3 is interaction only. Larger-set Shapley interaction allocation and
  the matched-anchor additive/interaction identity are implemented and covered
  by independent KATs. The pair fixture with energies 10/10/10/8 produces
  Psi=2 and credits (1,1); C1+C3 counts the joint F change once.
- The merge QoS gate uses the availability lower interval > -0.5 pp and upper
  relative changes < +5% for both handover rate and Phi-priced handover cost.
  A synthetic one-margin-failure KAT is present.
- The final provider handoff is integrated with provenance. Dense arrays,
  physical `(NORAD, cell_id)` aggressor keys, same-satellite co-colour terms,
  live visibility/D2 legality, fail-closed primitives, moving step layouts,
  generating-input manifests, and the 30+3 prepared horizon are wired.
- H/SH receives interruptions from the common physical event ledger. The full
  roster remains in every denominator and partial, complete, decoding, and
  useful service are distinct fields.
- Factor arms score only the declared C1+C2+C3 targets. DROP removes one term
  in the same selector/catalogue, UNI is unilateral-only, and S_UNI is the
  iterated exact-unilateral comparator with iteration/wall fields.
- The whole proposal/evaluation/forecast/selection path is timed. A 30.08-s
  miss replaces every deployable set-level selection with BASE. The attempt
  registry is append-only/hash-chained; canonical step rows are reaggregated at
  merge; SMOKE receipts are rejected from merge.
- Kappa is `B_ref/(U*N_ref)` bits per user-step. C2 uses nominal fields, focal
  survival, absorbing invalid propagation, and no energy surrogate. The
  sensitivity standby census is 12 chains per represented satellite.
- The controller's coupled-solve decision is applied: 65,536 iterations,
  absolute-or-relative convergence, monotonicity/non-finite INVALID checks,
  valid cap-bound infeasibility, and `CONVERGED_SLOW` propagation.

## Provider provenance and tests

- Provider workspace marker: `PROVIDER-FIX-DONE` present.
- Provider handoff SHA-256:
  `7140f116cff04f3614b5bedb5145949804eaad43df8a1cf56339b9d8d6e266d1`.
- Integrated provider SHA-256:
  `3e6ad0b5c5c25b16b7f6c7cc4dca2b0f12487d4e400cd3d090002a24b491cb38`.
- Frozen TLE archive digest:
  `fe2d0ccc2148de73c7014be8af06efc20700f5cf3e8d1f58641222910da0e934`.
- Provider suite: `19 passed`.
- Engine suite excluding the provider module: `132 passed`, including the
  three coupled-solve KATs.
- Dry-run: PASS, 14 arms, KAT receipt
  `1384f24951e78c6c39b59e655a2b13b89f5ec6b9e265276d6ee38852350f6e08`.
- `git diff --check`: PASS. `git diff -- src/mcrl/env`: empty.

## Real-world compute measurements

All measurements below used quarantined development namespace
`V025_PROBE/world/1`; they are engineering timings, not claim-panel outcomes.

| Measurement | Result |
|---|---:|
| decision-instant legal candidates | 2,800 |
| bounded catalogue configurations | 2,912 |
| catalogue maximum same-beam occupancy | 9 |
| real-provider one-step construction | 9.9–12.5 s |
| exact a-r0 batch, 2 rows | 0.190 s |
| exact a-r0 batch, 128 rows | 4.292 s = .0335 s/row |
| exact a-r0 batch, 2,912 rows | >90 s; interrupted |

The 128-row and full-catalogue observations miss the <=.02 s/row target; the
provider misses <=1 s/anchor. More importantly, C2 forecasts have not yet been
moved onto a shared batch call, so a complete anchor remains far beyond the
30.08-s coordinator definition. A conservative lower bound for current,
nominal, and three offset passes is >450 s/anchor. Three rehearsal anchors
therefore exceed 10 core-minutes before orchestration, and even the first ten
smoke anchors cannot be certified below 60 core-minutes on the current path.

## Rehearsal and smoke receipts

- Formal rehearsal q: `NOT_RUN_COMPUTE_GATE`.
- Projected 31 x 4 x 90 cost: `NOT_RUN_NO_VALID_Q`.
- Smallest sealed stride: `NOT_RUN_NO_VALID_Q` (rough lower-bound estimate is
  approximately 10, explicitly not sealed).
- Smoke receipt location: none; `.scratch/multi-catfish-v025-physics-successor/smoke/`
  was not populated.
- Smoke wall time: `NOT_RUN_COMPUTE_GATE`.

## Remaining blockers / CONTROLLER_DECIDE

1. Finish the shared batch path for nominal S0 and all C2 unilateral forecasts;
   remeasure one complete real anchor below the deadline and provider target.
2. The bounded-catalogue top-10 rank is still a deterministic legal-option
   proxy in construction; it must be replaced by exact nominal unilateral
   surplus before the catalogue is sealed.
3. Wire larger-set Shapley credits into actual evacuation/proposal selection,
   not only the production helper/KAT, and emit the matched-anchor A/I and
   Delta_joint reporting fields on every anchor/unit.
4. Add the remaining end-to-end discriminators requested by the audits:
   pairwise-distinct 31-setting synthetic receipts, live boundary-17 release,
   hidden-state dependency equality, full forecast margin rows/schema stamping,
   and certificate distributions including `CONVERGED_SLOW`.
5. Run the stage-4 synthetic mechanism map. Stage-2 E1–E4 remain superseded.
6. Only after 1–5 pass: create the six immutable R2 manifests/calibrations,
   run the <=10-core-minute rehearsal, derive and seal stride, then run the
   bounded smoke. Until then the seal package remains HOLD.

No commit was made: the working tree already contains controller-owned,
untracked decision documents and stage-3 changes, and the requested stage-4
deliverables are not complete enough to represent as a successful stage commit.
