# V0.25 probe seal package — stage-4b HOLD package (2026-09-08)

Status: **HOLD — not launchable and not signed.** This package is outcome-blind.
The real provider is integrated, but the measured exact catalogue path misses
the binding compute targets. Formal R2 manifests, allocation, calibration,
rehearsal, and smoke were therefore not opened; `PENDING_NOT_RUN` is a blocker,
not a wildcard. Stage 4b changes the executable package and its prospective
digests only; it does not convert this HOLD into a launch signature.

## Governing identities

- Sealed v1.2 amendment SHA-256: `cd1922fbeae9da2df9aa8ccadddaa11410932c02dfbea63a9f620202737a25bf`.
- Sealed v1.3 count erratum SHA-256: `62cecfc48cc066a678555774bd52bc31b13677bb4ebb5e11d1e4dbb95974f917`.
- Sealed v1.5 amendment SHA-256: `f0501b2fc9e0ca9b73a18d4246f1787d4a77a1b44b95b20577ecb3224acb568c`.
- Sealed contingency ladder SHA-256: `dd0a13caef63af55abbfa99ee66dd82f349e51d37d382200ab500fa4062e4570`.
- Coupled-solve decision SHA-256: `5d981573fece213be5a241c6f05fbecbb83c155479b90e03ba9acd84421d6ef4`.
- Pipeline-audit-A decision SHA-256: `ff216e724d7af8789f467693c02438763e2e77ee0290a9f4ec08fe42b7f4ada6`.
- Launcher/receipt schema: `multi-catfish-mcrl-v025-matrix-probe-v1.5-stage4b`.
- Canonical UTF-8 cell-list SHA-256: `2c1e47637d87daf5e559e1e4b4a9afd9904dbb3bdb891bf9f4546a75c498d2f0`.
- Launcher SHA-256: `099f8c7e3b7778a3ecd2a84ab7a86011752cae7ddfc0e4edfb9f3668ed06cb2e`.
- Integrated provider SHA-256: `51101e98b260efae544116027fe9b726cac20fe7983755eedc7cd8ae7bcc28a6`.
- Provider handoff SHA-256: `7140f116cff04f3614b5bedb5145949804eaad43df8a1cf56339b9d8d6e266d1`.
- Frozen TLE archive digest: `fe2d0ccc2148de73c7014be8af06efc20700f5cf3e8d1f58641222910da0e934`.
- a-r0 off-axis KAT artifact SHA-256:
  `87e8bb4598c1212c823469f33775dc8650dbc7667c2e2623c3ef44d4ad8e7d03`.
- a-r0 off-axis SVG SHA-256:
  `cdcd912cdc0ab6b4cff78c3c7847b68a8ee57b5c42e3172647497b23e826cf17`.
- Dry-run declared-target/decoder/reward/set-score KAT receipt SHA-256:
  `d1abddb27d90996cc7057865a2f078472012db734e4b7cf6800ecd0ee5c8da16`.
- Current code-authority aggregate SHA-256:
  `ff672ff1e3f35d99bd0d980ca6e032d735e3f409ba78cc790b1c4721ec80de4b`.

## Cell order to seal

The inherited 31-cell list remains byte-for-byte ordered below. Under v1.5,
only `a-r0` is primary; every other row is `EXPLORATORY_SENSITIVITY`:

```text
a-r0
a′-r0
a-γ0
b0
a′-γ0
a-rS
a′-rS
a-γS
bS
a′-γS
a-rH
a′-rH
a-γH
bH
a′-γH
a-rSH
a′-rSH
a-γSH
bSH
a′-γSH
a-rT
a′-rT
a-γT
bT
a′-γT
a-γU-cap
bU-cap
a′-γU-cap
a-γU-margin
bU-margin
a′-γU-margin
```

The sealed v1.3 erratum resolves v1.2's “28” typo: 25 + 6 = 31 and no
additional labels are inferred.

The stage-4b launcher executes `a-r0` alone, waits for all four successful
receipts, and only then creates `AR0-DONE`. It next queues
`R1,R2,R3,R4,R5=a′-r0,R6=a-γ0,C2-H1,C2-H2`, followed by the remaining
inherited treatments. R1–R4 and the two C2 horizons are additional sealed run
settings, so the executable inventory is 37 settings / 148 world units; R5 and
R6 alias existing cells and are not duplicated. Their prospective digests are:

```text
a-r0   e69bd641ab2799aa9ec09114b36e15ca0d1569937cd71dfe27576c59e84cd31a
R1     52d3565c5ffbc1729b5f1388fa53446c60be8cee683be5caa22126eb34bec1a9
R2     91f8065fb53dee15f3240148ce1d276fe543b44099ed0b3b9f1c68ff6d50d2d5
R3     ca99b6536e3d1c93751c064411f13d533f4eba2343eb838c0f59cc2e8ac91264
R4     90a1585df9a475e0b3be8fed8a6ecc577e0e5d752a952e2d6954fdfa766fe0cb
R5     9fc69c513998b9cf92bd7c200885a3d3d14f43e5979195887778af76e8e35065
R6     6904b7fcaab49bb093f06d409d79831664194ad88f23afa0aa7e7a26734c443f
C2-H1  e30a31b998a065d67cb6f9288256000604372deefdd7ce330694c148091721a0
C2-H2  8e3e490793382677d91a034f080caa34bcf2a9d27871d32fa0d458d5b4b385d2
```

## World manifests to seal

The formal `world-manifest.json` must contain four default and four R2
user-count-profile aggregate digests. The formal `calibration-manifest.json`
must likewise contain two default and two R2 profiles. Each embedded manifest
must carry and re-verify, before a unit opens: split, exact start UTC, every TLE
filename/hash, split-rule digest, provider-source digest, inventory/layout,
mobility/fading stream identities, and world digest. Tapes contain 33 steps
(30 executed + three forecast offsets). The executable allocation-manifest
builder records the same full identity plus role/world/learner seeds and fails
closed unless CLAIM_PANEL plus PROBE, CALIBRATION, REHEARSAL, KAT and
SYNTHETIC_REAL are all enumerated with role-wise disjoint TLE dates. Formal
allocation remains `PENDING_NOT_RUN`.

TLE selection is the inherited per-NORAD nearest epoch from date-1/date/date+1
at episode start with absolute age <=24 h. Future epochs are permitted. This is
an accuracy-first, explicitly **non-causal benchmark convention** shared by all
arms, not a deployment claim.

| Domain | Formal SHA-256 to sign | Synthetic package-check SHA-256 (not admissible) |
|---|---|---|
| `V025_PROBE_R2/world/1` | `PENDING_NOT_RUN` | `SUPERSEDED_R1_SYNTHETIC` |
| `V025_PROBE_R2/world/2` | `PENDING_NOT_RUN` | `SUPERSEDED_R1_SYNTHETIC` |
| `V025_PROBE_R2/world/3` | `PENDING_NOT_RUN` | `SUPERSEDED_R1_SYNTHETIC` |
| `V025_PROBE_R2/world/4` | `PENDING_NOT_RUN` | `SUPERSEDED_R1_SYNTHETIC` |
| `V025_CAL_R2/world/1` | `PENDING_NOT_RUN` | `SUPERSEDED_R1_SYNTHETIC` |
| `V025_CAL_R2/world/2` | `PENDING_NOT_RUN` | `SUPERSEDED_R1_SYNTHETIC` |

Synthetic aggregate receipt digests are `7bafa6fac30cdf9ffa80f324ae73fbb87fe4e83280ff2180241a5b654c4d5b46`
(probe) and `4e25b452e4c2d5e38b94225d6e2538d8b90ba9c0d4102ac4ed2e3af6e74988ca`
(calibration). They prove deterministic package generation only.

## Calibration values to seal

For every cell in the exact list above, the controller signs the exact rational
triplet in `calibration-manifest.json`: `η_ref`, `lambda_bits_per_j`, and
`kappa_bits_per_user_s`, plus the setting digest, selected nominal-greedy
configuration IDs, two calibration domains, and per-setting calibration digest.
The manifest enforces `λ = η_ref = ΣB_ref/ΣE_ref` and
`κ = ΣB_ref/(U·N_ref)` bits per user-step, where `N_ref` is a decision-step
count and never seconds. None may be supplied by a runtime default.

The per-setting checklist is:

```text
a-r0       η=PENDING λ=PENDING κ=PENDING
a′-r0      η=PENDING λ=PENDING κ=PENDING
a-γ0       η=PENDING λ=PENDING κ=PENDING
b0         η=PENDING λ=PENDING κ=PENDING
a′-γ0      η=PENDING λ=PENDING κ=PENDING
a-rS       η=PENDING λ=PENDING κ=PENDING
a′-rS      η=PENDING λ=PENDING κ=PENDING
a-γS       η=PENDING λ=PENDING κ=PENDING
bS         η=PENDING λ=PENDING κ=PENDING
a′-γS      η=PENDING λ=PENDING κ=PENDING
a-rH       η=PENDING λ=PENDING κ=PENDING
a′-rH      η=PENDING λ=PENDING κ=PENDING
a-γH       η=PENDING λ=PENDING κ=PENDING
bH         η=PENDING λ=PENDING κ=PENDING
a′-γH      η=PENDING λ=PENDING κ=PENDING
a-rSH      η=PENDING λ=PENDING κ=PENDING
a′-rSH     η=PENDING λ=PENDING κ=PENDING
a-γSH      η=PENDING λ=PENDING κ=PENDING
bSH        η=PENDING λ=PENDING κ=PENDING
a′-γSH     η=PENDING λ=PENDING κ=PENDING
a-rT       η=PENDING λ=PENDING κ=PENDING
a′-rT      η=PENDING λ=PENDING κ=PENDING
a-γT       η=PENDING λ=PENDING κ=PENDING
bT         η=PENDING λ=PENDING κ=PENDING
a′-γT      η=PENDING λ=PENDING κ=PENDING
a-γU-cap   η=PENDING λ=PENDING κ=PENDING
bU-cap     η=PENDING λ=PENDING κ=PENDING
a′-γU-cap  η=PENDING λ=PENDING κ=PENDING
a-γU-margin  η=PENDING λ=PENDING κ=PENDING
bU-margin    η=PENDING λ=PENDING κ=PENDING
a′-γU-margin η=PENDING λ=PENDING κ=PENDING
```

## Catalogue definition to seal

- Coarse provider satellite/beam shortlist is generated before successor masks
  and must be a superset of the complete visible-10° and D2-eligible physical
  set. Each unit receipts the miss count; it must be zero but is not confused
  with an empty or physically headroom-limited legal set.
- Synthetic catalogues use the complete Cartesian product when it has at most
  4,096 configurations. Before formal launch, stage 4 must install the declared
  large-world bounded union: every unilateral; S0 top-two plus frozen
  evacuations; all pairwise joint moves for the top 10 users by nominal
  unilateral surplus, restricted to their top-two legal options each; and every
  per-active-beam evacuation set. U1 changes one
  user and J1 is re-optimised per cell over changed-user-count > 1 entries.
- S0 retains two nominal proposals per user and every frozen evacuation composed
  only from those proposals. LC-SRS uses atomic `00/10/01/11` profiles and the
  declared `Ψ = F11 − F10 − F01 + F00`; `t3_energy` is absent.
- Current catalogue-definition digest:
  `f99f9e9d2bbbd0673a3c18239408216f198f4d8566f891166daa2b0d8b679679`.
  The controller must replace this digest if provider-owned mask semantics alter
  any catalogue input before launch.

## Stage-4 compute disposition

The engine now rolls 30 steps under all three carriers (90 anchors/world) and
records `--anchor-stride` (default 1); merge rejects mixed strides. The arm list
is the original twelve plus `UNI` and arm 13 `S_UNI` (14 reported arms). The
coordinator's Level-B whole-path deadline is 10 s on one declared worker; operational
unit concurrency is 20. `a-r0` is completed before any exploratory setting.

Every complete configuration now has the executable v1.5 set-score
decomposition: unilateral `d_i`, set residual `Psi_A`, exact Shapley interaction
credits, and the exact `C1+C3 = F(a_A)-F(a0)` core identity. Factor arms use the
same catalogue/selector with exactly FULL=`C1+C2+C3`, DROP_C1=`C2+C3`,
DROP_C2=`C1+C3`, and DROP_C3=`C1+C2`.

Learner experiments use a two-way date x learner-seed pigeonhole bootstrap as
primary, with arms paired and all pooled ratios recomputed per draw. The
learner-free physics matrix uses the one-way date bootstrap as primary. Both
use central 95% percentile intervals and relative EE gain with a +0.5% margin;
zero-bit clusters remain in the primary pooled ratio while the log supplement
is marked undefined. QoS availability, Phi-priced handover cost and handover
rate pool additive numerators/denominators inside each draw. Merge always emits
Level B (FULL vs DROP_C3) and Level A (FULL vs S_UNI), each with the matched
nonadditivity fraction.

Pre-outcome development measurements:

| Component | Measured | Target | Result |
|---|---:|---:|---|
| real-provider 48-boundary step | 9.9–12.5 s | <=1 s/anchor | FAIL |
| exact a-r0 batch, 128 rows | 4.292 s (.0335 s/row) | <=.02 s/row | FAIL |
| exact a-r0 batch, 2,912 rows | >90 s, interrupted | <=58.24 s | FAIL |
| current + nominal + three offsets, lower bound | >450 s/anchor | 10 s | FAIL |

The formal rehearsal would exceed its 10-core-minute ceiling before completing
three anchors, so it was not opened. Formal `q`, 31×4×90 projected cost, and
the smallest sealable stride are `PENDING_NOT_RUN`. A rough lower bound would
require approximately stride 10, but it is not sealed because C2 is not yet on
the batch path. The smoke (90 anchors, or first 10 anchors) would likewise
exceed 60 core-minutes on the current path and was not opened. No outcome was
used to change a default, order, constant, or rule.

## Rehearsal cost to seal

Stage-3 synthetic re-measurement (a-r0, world 1, three carrier anchors, all 12
arms): 6,048 boundary evaluations, measured runner wall `1.1486061489995336 s`,
process wall `1.50 s`, user CPU `1.47 s`, peak RSS `54,196 KiB`,
`q = 0.0006037034316196435`, projected 31-cell matrix cost with 30% reserve
`0.06320372460103255 core-hours`. Rehearsal receipt SHA-256:
`780ba4549dfbb56bbee029613f345b270fa62c45ede392296cd237a555ada8cd`.

This stage-3 number is superseded and is not a real-provider transfer estimate.
Do not use it to launch or choose a stride.

The formal stage-4 rehearsal additionally seals a cost table containing provider
seconds per world, catalogue rows and seconds per anchor, and projection per
setting. Engineering is attempted first (dense NumPy tapes, realisable inventory,
batched configuration × boundary evaluation, and provider acquisition once per
world). If projection still exceeds 160 core-hours, record the smallest applied
prospective sequence: anchor stride 2 then 3; then drop treatment cells from the
bottom of the sealed priority order (T, SH, H, S, lowest-priority architecture
first); then reduce four probe worlds to three. Baselines and U diagnostics,
48-boundary integration, calibration, placebo/dry-run, and the final 12+1 arm
inventory are never thinned.

## Deployment capability and admission wording

S0, S_UNI, FULL/DROP and UNI consume authenticated current geometry for every
user, live legal-option sets, and the nominal joint-physics model. They consume
no realised fading and no future TLE beyond the declared three-offset horizon.
S0 uses nominal top-two proposals plus frozen evacuations; S_UNI uses iterated
exact unilateral best response; FULL/DROP share the bounded catalogue and sum
the declared C1/C2/C3 targets with one term removed by each DROP; UNI retains
all targets but restricts search to unilateral moves. All apply the matched
service guard and 10-s whole-path deadline, receipt declared workers, and
fall back to BASE.

Admission requires: physics/integrity PASS; complete U1 census with certified
optimum; J1 beyond BASE and beyond U_all by more than certified numerical error
under matched QoS; deployable S0 >=1%; usable-energy opportunity beyond error
where claimed; and every retained factor's FULL-DROP oracle marginal positive
under QoS. U1 need not exceed BASE for C3. Training uses a-r0 regardless of
secondary-cell results. The executable merge evaluates this primary decision
from `a-r0` only. It also reports R1–R6 certificates and decisions separately,
each labelled “in regime R_k”; these cannot change the a-r0 result. No formal
admission gate was evaluated in this HOLD package. A nonzero coupled-solver
update residual is not treated as an F-error bound: J1 admission fails closed
until independently proved objective bounds cover power convergence, nonlinear
PA energy and ACM threshold stability.

## Exact detached launch commands

The provider identity below is exact. All output is under
`/home/sat/mcrl-v025-probe-launch-2026-09-08/`; the unit supervisor rejects more
than 20 concurrent processes.

```bash
install -d /home/sat/mcrl-v025-probe-launch-2026-09-08/logs /home/sat/mcrl-v025-probe-launch-2026-09-08/output

nohup bash -lc 'cd /home/sat/mcrl-v025-codex-ws-engine && PYTHONPATH=src python .scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py --manifest --provider mcrl.physics_v025.provider_legacy:LegacyWorldProvider --output /home/sat/mcrl-v025-probe-launch-2026-09-08/output' >/home/sat/mcrl-v025-probe-launch-2026-09-08/logs/manifest.log 2>&1 &

nohup bash -lc 'cd /home/sat/mcrl-v025-codex-ws-engine && PYTHONPATH=src python .scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py --calibrate --provider mcrl.physics_v025.provider_legacy:LegacyWorldProvider --output /home/sat/mcrl-v025-probe-launch-2026-09-08/output' >/home/sat/mcrl-v025-probe-launch-2026-09-08/logs/calibration.log 2>&1 &

nohup /home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/probe/launch_v025_units.sh mcrl.physics_v025.provider_legacy:LegacyWorldProvider /home/sat/mcrl-v025-probe-launch-2026-09-08 20 STRIDE_PENDING >/home/sat/mcrl-v025-probe-launch-2026-09-08/logs/units-supervisor.log 2>&1 &

nohup bash -lc 'cd /home/sat/mcrl-v025-codex-ws-engine && PYTHONPATH=src python .scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py --merge --output /home/sat/mcrl-v025-probe-launch-2026-09-08/output' >/home/sat/mcrl-v025-probe-launch-2026-09-08/logs/merge.log 2>&1 &
```

The controller runs the unit command only after both immutable manifest files
and their sidecars exist and are signed, and runs merge only after the supervisor
has exited successfully with all 148 immutable unit receipts present. These
commands remain embargoed until the outstanding compute/C2 batching blockers
are closed and a bounded formal rehearsal produces a valid q. The unit already
contains 30 decision instants for each of three carriers (90 anchors/world), the
large-world catalogue and the numeric QoS guard. If the formal rehearsal exceeds
160 core-hours, the sealed thinning integer `k` is the smallest
projection-derived value that brings cost under budget.
