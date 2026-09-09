# V0.25 engine stage-3 report — 2026-09-08

## Disposition

Stage 3 is implemented on `v025/engine`. The v1.2 amendment, the stage-1/1b
controller decisions, the round-6 addendum, and the newly arrived sealed v1.3
count erratum are reflected in the engine/probe package. No real-world successor
outcome, TEST world, training update, or source regeneration was opened.

The overnight matrix remains **HOLD**. The controller's stage-2 decision record
prospectively assigns stage 4 the formal provider merge, 90-anchor-per-world
runner, large-world bounded catalogue, numeric QoS guard, formal calibration,
and provider rehearsal. The later engine-audit and compute-budget records add
factor-only selectors/comparators, per-chain interference identities, null-user
catalogue handling, vectorised catalogue evaluation, and a prospective thinning
order. The draft launch commands are therefore complete but embargoed until
those changes and values are sealed.

## Verification receipt

Focused acceptance command:

```bash
PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest tests/physics_v025
```

Exact pytest line:

```text
122 passed in 9.09s
```

`python -m compileall`, `bash -n` for the bounded launcher, and
`git diff --check` also passed. A repository-wide pytest run completed with the
same 57 out-of-scope historical failures recorded by stage 2 (legacy C3 fixture
signature drift, missing R7 sealed artefacts, old manifest drift, and global
vocabulary/ruling checks); the V0.25 focused surface is green.

No file under `src/mcrl/env/` changed. All old-system physics remain byte-identical
to `HEAD`. The sealed v1.2 and v1.3 declaration SHA-256 values still match their
sidecars; neither sealed file was edited.

## Cells and launcher schema

The canonical UTF-8 enumeration has **31 settings**: **25 primary-eligible + 6
diagnostic**. The sealed v1.3 erratum resolves v1.2's erroneous number 28. The
order is the five architectures in `a-r, a′-r, a-γ, b, a′-γ` priority for 0,
then S, H, SH, T; diagnostics are U-cap then U-margin for `a-γ, b, a′-γ`.

The test compares the enumeration byte-for-byte with the independent sealed-list
UTF-8 literal. Cell-list digest:
`2c1e47637d87daf5e559e1e4b4a9afd9904dbb3bdb891bf9f4546a75c498d2f0`.
All setting digests and `--estimate` output bind the list. The estimate retains
one 48-boundary physical tape per architecture and treatment-only rescoring,
240 reference equivalents before q. Launcher/receipt schema is
`multi-catfish-mcrl-v025-matrix-probe-v1.2-stage3`.

## Controller CHANGEs and register A/B verification

- Treatment T uses the left decision-time sample. The controller KAT now calls
  the implementation directly: `R(t)=2+t` over two seconds gives integral 6 and
  left hold 4. Every T arm receipt reports its left-snapshot bits/joules beside
  the converged integral built from the same physical instant/tape.
- Rate architectures persist all 48 per-boundary target-attainment maps in each
  arm receipt, in addition to step attainment and all-boundary feasibility.
- H and SH now build their interruption inputs from the same physical transition
  ledger used by Φ and receipts before candidate selection; the candidate score
  loses useful time while its transmitted energy remains charged.
- Shadow and scintillation are drawn at actual link elevation (10°/60° KAT),
  and the interference path uses the S.465-6 2.043298703° branch (1°,
  2.043298703°, 5° KAT).
- Every step tape enforces `t + k·0.640 s`, `k=0..47`; transition ledgers use
  physical `(NORAD, beam-chain)` identity; the boundary-conditional re-key rate
  is computed from ledger events over eligible boundary-user opportunities and
  is reported as undefined when a run observes no eligible boundary. Primitive
  boundaries carry explicit per-user re-key flags; a positive refresh-boundary
  KAT observes one re-key over two eligible user-boundaries (`0.5`).

## Target × decoder parity

`src/mcrl/physics_v025/parity/` records SHA-256 provenance for the imported
V0.23 audit sources and adapts them to exact V0.25 endpoints. Public target and
endpoint producers require explicit λ, η, and κ and pass through the common
equality assertion. The independent declared formula and production C3 formula
cross on the same `00/10/01/11` physical profiles.

The fixed round-6 fixture holds bits unchanged and energies at 10/10/10/8 with
λ=η=1: unilateral C3 is zero, Ψ=2, equal shares are `(1,1)`, and both additive
and atomic decoders execute action 11 and observe the 8-J endpoint. The suite
also proves non-binding demand-cap invariance, per-regime atomic J
re-optimisation, and common-action bootstrap selection: heads `[10,0]` and
`[0,9]` select one scalarised action `[10,0]`, never unattainable `[10,9]`.
No `t3_energy` field is used. Following the stage-2 controller decision that
arrived during this pass, C3 now carries only Ψ's equal share because
whole-network C1 owns unilateral bits and energy.

`--dry-run` executes all of the above plus reward/endpoint identity through the
probe runner's production `_independent_proposal` and `_set_select` decoders.
KAT receipt SHA-256:
`1384f24951e78c6c39b59e655a2b13b89f5ec6b9e265276d6ee38852350f6e08`.

## Catalogue and usable-energy diagnostics

Primitive candidates now declare coarse-shortlist membership before successor
visibility/D2 masks. Catalogue construction independently computes the full
legal set, reports the missing legal-option count, and uses only shortlisted
legal candidates. All four synthetic worlds have zero misses; a negative KAT
removes one legal candidate from the shortlist and observes a miss count of one.

Each cell receipt reports, for FULL's selected physical profiles:

- selected ACM mode counts (including `NO_MODE`);
- the top-mode SE-plateau share;
- the RF-cap transmission share; and
- the best feasible DC-energy change available by incumbent beam.

These diagnostics apply no threshold or exclusion. Catalogue/service limits
remain scoring/reporting concerns. The controller's newly declared large-world
catalogue (4,096 threshold, top-K=10 pairwise set, and beam evacuations) remains
the stage-4 runner change.

## Energy identities

The suite now includes the exact requested identities:

- equal-airtime TDM at 0.1 W and 1.6 W equals
  `0.5·PA(0.1)+0.5·PA(1.6)`, distinct from PA(max) and PA(mean);
- FDM evaluates PA once on summed simultaneous beam RF under the beam cap;
- a no-mode user radiates at cap, creates interference and PA energy, and is not
  served; and
- circuit energy is charged once per active chain and baseband once per active
  satellite for one versus three users on one beam.

## Uncertainty

Merge-time primary uncertainty remains the paired cluster bootstrap that
recomputes `ΣB/ΣE` within every resample. For this oracle probe the cluster key is
TLE date × world, with the world's bound training seed retained in the receipt.
Paired per-world log-EE remains supplementary and is tested to differ from the
pooled-ratio interval on unequal blocks.

Every contrast now also reports, without gating:

- the paired-block delta-method interval for
  `L=log(ΣB_F/ΣE_F)−log(ΣB_D/ΣE_D)` using the declared ψ influence function; and
- a two-way TLE-date × training-seed pigeonhole bootstrap.

A 400-block IID KAT makes all three intervals finite and places the delta-method
interval width within 10% of the pooled bootstrap width.

## Rehearsal and sealing package

The final bounded synthetic rehearsal re-measured a-r0, world 1, three carrier
anchors, all 12 arms: **6,048 boundary evaluations**, runner wall
**1.1486061489995336 s**, process wall **1.50 s**, user CPU **1.47 s**, peak RSS
**54,196 KiB**. The measured `q` is **0.0006037034316196435** and the current
31-setting projection with 30% reserve is **0.06320372460103255 core-hours**.
Receipt SHA-256:
`780ba4549dfbb56bbee029613f345b270fa62c45ede392296cd237a555ada8cd`.
The total rehearsal was far below ten core-minutes.

The controller checklist and exact detached commands (hard maximum eight units,
all logs below `/home/sat/mcrl-v025-probe-launch-2026-09-08/`) are in
`probe/SEAL-PACKAGE-DRAFT-2026-09-08.md`, SHA-256
`1751d040e479c0a3bcb5b8377adbe7adc99f2602c69e3d17c5228c4f2164c96c`.
The helper launcher is mode 0755 and rejects concurrency outside 1..8.

## `CONTROLLER_DECIDE`

No new scientific ambiguity was introduced in stage 3. The unresolved work is
the controller's already recorded stage-4 carry-over, not a new decision:

1. merge and authenticate `LegacyWorldProvider`, seal its source/TLE/user/start-
   time/cross-gain identities, per-chain colour/re-key observations, realisable
   inventory, and populate the six formal world digests;
2. implement 30 canonical decisions × three carriers per world, amortised
   world acquisition and vectorised catalogue scoring; seal the provider/row/
   per-setting cost table and the declared stride/cell/world thinning sequence;
3. implement/seal the refined bounded catalogue, null-user behavior, larger-set
   Shapley split, factor-only FULL/DROP selector, and UNI/S_UNI arm inventory;
4. route every arm through the common resolver, make the declared producers
   live in receipts, and replace the remaining tautological audit fixtures; and
5. implement the −0.5 pp complete-service and +5% handover/Φ QoS guards, then
   replace all 31 pending calibration triplets and the synthetic q in the seal
   package before any unit outcome is opened.
