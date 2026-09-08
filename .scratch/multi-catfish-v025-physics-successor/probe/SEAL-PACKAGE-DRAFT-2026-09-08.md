# V0.25 probe seal package — stage-4 HOLD package (2026-09-08)

Status: **HOLD — not launchable and not signed.** This package is outcome-blind.
The real provider is integrated, but the measured exact catalogue path misses
the binding compute targets. Formal R2 manifests, calibration, rehearsal, and
smoke were therefore not opened; `PENDING_NOT_RUN` is a blocker, not a wildcard.

## Governing identities

- Sealed v1.2 amendment SHA-256: `cd1922fbeae9da2df9aa8ccadddaa11410932c02dfbea63a9f620202737a25bf`.
- Sealed v1.3 count erratum SHA-256: `62cecfc48cc066a678555774bd52bc31b13677bb4ebb5e11d1e4dbb95974f917`.
- Launcher/receipt schema: `multi-catfish-mcrl-v025-matrix-probe-v1.3-stage4`.
- Canonical UTF-8 cell-list SHA-256: `2c1e47637d87daf5e559e1e4b4a9afd9904dbb3bdb891bf9f4546a75c498d2f0`.
- Launcher SHA-256: `5e311b3fec2809eb633e371d8f2df4ba569262f26fcac129f0bbed5800704534`.
- Integrated provider SHA-256: `3e6ad0b5c5c25b16b7f6c7cc4dca2b0f12487d4e400cd3d090002a24b491cb38`.
- Provider handoff SHA-256: `7140f116cff04f3614b5bedb5145949804eaad43df8a1cf56339b9d8d6e266d1`.
- Frozen TLE archive digest: `fe2d0ccc2148de73c7014be8af06efc20700f5cf3e8d1f58641222910da0e934`.
- Dry-run declared-target/decoder/reward KAT receipt SHA-256:
  `1384f24951e78c6c39b59e655a2b13b89f5ec6b9e265276d6ee38852350f6e08`.
- Current code-authority aggregate SHA-256:
  `dd821e1cfc47716e67cb63b17b817efed2386603f035f9552793b373a57bae9e`.

## Cell order to seal

The exact order is 25 primary-eligible settings from the amendment's explicit
list followed by six diagnostic-only settings (31 settings, 124 world units):

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

## World manifests to seal

The formal `world-manifest.json` must contain four probe-world aggregate
digests and, within each manifest, the inventory, user-layout, 48-boundary tape,
three-carrier, provider/TLE, and catalogue-input digests. The formal
`calibration-manifest.json` must contain the corresponding two disjoint
calibration-world digests.

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
coordinator's whole-path deadline is 30.08 s on one declared worker; operational
unit concurrency is 14.

Pre-outcome development measurements:

| Component | Measured | Target | Result |
|---|---:|---:|---|
| real-provider 48-boundary step | 9.9–12.5 s | <=1 s/anchor | FAIL |
| exact a-r0 batch, 128 rows | 4.292 s (.0335 s/row) | <=.02 s/row | FAIL |
| exact a-r0 batch, 2,912 rows | >90 s, interrupted | <=58.24 s | FAIL |
| current + nominal + three offsets, lower bound | >450 s/anchor | 30.08 s | FAIL |

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
service guard and 30.08-s whole-path deadline, receipt declared workers, and
fall back to BASE.

Admission requires: physics/integrity PASS; complete U1 census with certified
optimum; J1 beyond BASE and beyond U_all by more than certified numerical error
under matched QoS; deployable S0 >=1%; usable-energy opportunity beyond error
where claimed; and every retained factor's FULL-DROP oracle marginal positive
under QoS. U1 need not exceed BASE for C3. Training uses a-r0 regardless of
secondary-cell results. No admission gate was evaluated in this HOLD package.

## Exact detached launch commands

The provider identity below is exact. All output is under
`/home/sat/mcrl-v025-probe-launch-2026-09-08/`; the unit supervisor rejects more
than 14 concurrent processes.

```bash
install -d /home/sat/mcrl-v025-probe-launch-2026-09-08/logs /home/sat/mcrl-v025-probe-launch-2026-09-08/output

nohup bash -lc 'cd /home/sat/mcrl-v025-codex-ws-engine && PYTHONPATH=src python .scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py --manifest --provider mcrl.physics_v025.provider_legacy:LegacyWorldProvider --output /home/sat/mcrl-v025-probe-launch-2026-09-08/output' >/home/sat/mcrl-v025-probe-launch-2026-09-08/logs/manifest.log 2>&1 &

nohup bash -lc 'cd /home/sat/mcrl-v025-codex-ws-engine && PYTHONPATH=src python .scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py --calibrate --provider mcrl.physics_v025.provider_legacy:LegacyWorldProvider --output /home/sat/mcrl-v025-probe-launch-2026-09-08/output' >/home/sat/mcrl-v025-probe-launch-2026-09-08/logs/calibration.log 2>&1 &

nohup /home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/probe/launch_v025_units.sh mcrl.physics_v025.provider_legacy:LegacyWorldProvider /home/sat/mcrl-v025-probe-launch-2026-09-08 14 STRIDE_PENDING >/home/sat/mcrl-v025-probe-launch-2026-09-08/logs/units-supervisor.log 2>&1 &

nohup bash -lc 'cd /home/sat/mcrl-v025-codex-ws-engine && PYTHONPATH=src python .scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py --merge --output /home/sat/mcrl-v025-probe-launch-2026-09-08/output' >/home/sat/mcrl-v025-probe-launch-2026-09-08/logs/merge.log 2>&1 &
```

The controller runs the unit command only after both immutable manifest files
and their sidecars exist and are signed, and runs merge only after the supervisor
has exited successfully with all 124 immutable unit receipts present. These
commands remain embargoed until stage 4 changes the unit from three anchors to
30 decision instants for each of three carriers (90 anchors/world), installs the
large-world catalogue above, and applies the sealed numeric QoS guard. If the
formal rehearsal exceeds 160 core-hours, the sealed thinning integer `k` is the
smallest projection-derived value that brings cost under budget.
