# V0.25 probe seal package — DRAFT (2026-09-08)

Status: **HOLD / controller signature and stage-4 runner update required before
any overnight unit is opened.** This draft is outcome-blind. The controller has
named `mcrl.physics_v025.provider_legacy:LegacyWorldProvider`, but its source and
TLE bindings are still being completed in the provider worktree. Synthetic
digests are labelled and are not admissible as formal world or calibration seals.

## Governing identities

- Sealed v1.2 amendment SHA-256: `cd1922fbeae9da2df9aa8ccadddaa11410932c02dfbea63a9f620202737a25bf`.
- Sealed v1.3 count erratum SHA-256: `62cecfc48cc066a678555774bd52bc31b13677bb4ebb5e11d1e4dbb95974f917`.
- Launcher/receipt schema: `multi-catfish-mcrl-v025-matrix-probe-v1.2-stage3`.
- Canonical UTF-8 cell-list SHA-256: `2c1e47637d87daf5e559e1e4b4a9afd9904dbb3bdb891bf9f4546a75c498d2f0`.
- Launcher SHA-256: `e3d8e617d193d6df3f00e666a54c0e7dfc9e031ba10e064b0ada2aac3ab2f6a7`.
- Dry-run declared-target/decoder/reward KAT receipt SHA-256:
  `1384f24951e78c6c39b59e655a2b13b89f5ec6b9e265276d6ee38852350f6e08`.

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
| `V025_PROBE/world/1` | `PENDING_FORMAL_PROVIDER` | `ba04fe101fd43e760147c3e05980f908b029817fa3f3cca050fe71136e7ae31e` |
| `V025_PROBE/world/2` | `PENDING_FORMAL_PROVIDER` | `9e12402f3987ca33017b569dbcbf75156468f1d6b7f227a9a988eab21ab19c99` |
| `V025_PROBE/world/3` | `PENDING_FORMAL_PROVIDER` | `2254af4119d61fcc9ab90ef3e577af621f103ea0ca7ed4ef8e1538758268de11` |
| `V025_PROBE/world/4` | `PENDING_FORMAL_PROVIDER` | `aebcc45b801a244280b68301ff17770319bfb553a1cdd04f2fd44e7d78c7c8c9` |
| `V025_CAL/world/1` | `PENDING_FORMAL_PROVIDER` | `8149e7399177779b13dc6dee58c18b156100a4fc43bde9aab46fac4c83a1ca94` |
| `V025_CAL/world/2` | `PENDING_FORMAL_PROVIDER` | `7f47d3abc19e644e0cc62b3d8ccd4f0194d0949e3e79e6e1ef04969de4287109` |

Synthetic aggregate receipt digests are `7bafa6fac30cdf9ffa80f324ae73fbb87fe4e83280ff2180241a5b654c4d5b46`
(probe) and `4e25b452e4c2d5e38b94225d6e2538d8b90ba9c0d4102ac4ed2e3af6e74988ca`
(calibration). They prove deterministic package generation only.

## Calibration values to seal

For every cell in the exact list above, the controller signs the exact rational
triplet in `calibration-manifest.json`: `η_ref`, `lambda_bits_per_j`, and
`kappa_bits_per_user_s`, plus the setting digest, selected nominal-greedy
configuration IDs, two calibration domains, and per-setting calibration digest.
The manifest enforces `λ = η_ref = ΣB_ref/ΣE_ref` and
`κ = ΣB_ref/(U·T_ref)`. None may be supplied by a runtime default.

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
  `cde4da460bf47ab9b6ac04f4beec1b6930261a4be2d903c0f038782805926fb0`.
  The controller must replace this digest if provider-owned mask semantics alter
  any catalogue input before launch.

## Rehearsal cost to seal

Stage-3 synthetic re-measurement (a-r0, world 1, three carrier anchors, all 12
arms): 6,048 boundary evaluations, measured runner wall `1.1486061489995336 s`,
process wall `1.50 s`, user CPU `1.47 s`, peak RSS `54,196 KiB`,
`q = 0.0006037034316196435`, projected 31-cell matrix cost with 30% reserve
`0.06320372460103255 core-hours`. Rehearsal receipt SHA-256:
`780ba4549dfbb56bbee029613f345b270fa62c45ede392296cd237a555ada8cd`.

This is below the ten-core-minute rehearsal ceiling but remains a synthetic
transfer estimate. Repeat the same command with the formal provider, then seal
that q and projection without truncating worlds, cells, or catalogues.

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

## Exact detached launch commands

The provider identity below is exact. All output is under
`/home/sat/mcrl-v025-probe-launch-2026-09-08/`; the unit supervisor rejects more
than eight concurrent processes.

```bash
install -d /home/sat/mcrl-v025-probe-launch-2026-09-08/logs /home/sat/mcrl-v025-probe-launch-2026-09-08/output

nohup bash -lc 'cd /home/sat/mcrl-v025-codex-ws-engine && PYTHONPATH=src python .scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py --manifest --provider mcrl.physics_v025.provider_legacy:LegacyWorldProvider --output /home/sat/mcrl-v025-probe-launch-2026-09-08/output' >/home/sat/mcrl-v025-probe-launch-2026-09-08/logs/manifest.log 2>&1 &

nohup bash -lc 'cd /home/sat/mcrl-v025-codex-ws-engine && PYTHONPATH=src python .scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py --calibrate --provider mcrl.physics_v025.provider_legacy:LegacyWorldProvider --output /home/sat/mcrl-v025-probe-launch-2026-09-08/output' >/home/sat/mcrl-v025-probe-launch-2026-09-08/logs/calibration.log 2>&1 &

nohup /home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/probe/launch_v025_units.sh mcrl.physics_v025.provider_legacy:LegacyWorldProvider /home/sat/mcrl-v025-probe-launch-2026-09-08 8 >/home/sat/mcrl-v025-probe-launch-2026-09-08/logs/units-supervisor.log 2>&1 &

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
