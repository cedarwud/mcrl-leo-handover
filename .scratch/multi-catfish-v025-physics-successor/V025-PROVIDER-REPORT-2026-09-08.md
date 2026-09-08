# V025 legacy primitive provider report — 2026-09-08



## Disposition

`LegacyWorldProvider` is implemented and its real-world KATs pass.  No file
under `src/mcrl/env/` changed, no TEST TLE file was opened by the provider,
and no learner, matrix unit, calibration outcome, or successor outcome was
opened.

The real provider cannot be promoted to the formal stage-2 CLI yet.  The
current runner still constructs the complete Cartesian product of legal
assignments and executes three anchors.  Controller decisions 3 and 4 require
90 anchors per world and the bounded real-world catalogue.  In addition, the
later provider controller record assigns per-chain cross-gain keys and dense
NumPy boundary storage to an engine protocol change in stage 4.  The current
`PrimitiveCandidate` schema keys cross gains by NORAD and materializes Python
objects, so those two changes cannot be implemented solely in this provider
without changing the stage-2 engine seam.

## Verification

Focused command:

```text
PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest -q tests/physics_v025
113 passed in 73.67s
```

`python -m py_compile`, `git diff --check`, and the no-diff check under
`src/mcrl/env/` also pass.

Provider source SHA-256:

```text
a143612f2a4040e72433fa711743d8ca26a9744adab0dcb49342c07246537e53
```

TLE archive binding:

- resolved root: `/home/sat/mcrl-runtime/tle-frozen-20260820`
- files: 373
- digest: `fe2d0ccc2148de73c7014be8af06efc20700f5cf3e8d1f58641222910da0e934`
- digest encoding: SHA-256 of ASCII `name:size` rows in sorted filename order,
  joined with `\n` and with no trailing newline

The provider wraps `TleArchive.load` with a TEST-date guard. The normal
sampler sees only the legacy block-alternating TRAIN date list. For a TRAIN
epoch, nearest-element selection examines the available date-1/date/date+1
files, retains the closest epoch per NORAD subject to the 24-hour age guard,
and freezes those elements for the episode.

## World-1 manifest

The bounded manifest run built six physical steps: three runner steps plus
the three forecast offsets. It generated 806,400 primitive candidate rows.

- domain: `V025_PROBE/world/1`
- world seed / training seed: `5261619120743994529`
- sampled TRAIN date: `2026-01-07`
- inventory: 57,525 `(NORAD, cell_id)` chains
- inventory SHA-256: `626d6ca40cfe5232e5a49d2f4ce026eea45b9f736526188779ffc1917dbdb10a`
- layout SHA-256: `7fa7aabf20315f0db953a2e2c9520880a6b1dfef4fb6f49369a3f2396491b8ec`
- tape SHA-256: `d5e63c3fcc837b64a4705706f90672f1c44f9af4e767f88b38ec365f4e156a2e`
- carriers SHA-256: `432e07f82ab203eaf3838f043eef0e8cc14916a450d892af6b639aee79300b0b`
- aggregate world-manifest SHA-256:
  `209f2b2e6fe6b57316c26504b01bc1edbc1f512306eb4ebf02362b69c54c98dc`

The measured builder section was 69.6373 s. Including canonical JSON digest
generation, the process used 100.13 s wall, 100.09 s CPU, and 4,352,404 KiB
peak RSS.

## Physics bindings

- User RNG ancestry is the C3-S construction:
  `SeedSequence(world_seed).spawn(4)`; child 0 draws the TRAIN epoch and
  child 1 drives the 100-user scatter and between-step wandering.
- Users are held at their decision-instant location over boundaries
  `k=0..47`, then moved once between decisions, per controller T13.
- A physical beam chain is `(NORAD, cell_id)`. The chain integer is the
  legacy global earth-fixed hex-cell index, and its RF colour is
  `CellGrid.colors[cell_id] = (q-r) mod 3`. The inventory pairs every
  satellite visible at or above 10 degrees at an exact boundary with every
  cell family addressable by the world's moving user population.
- The world universe is always screened for the canonical 30 steps.
  Supplying `steps=1`, `3`, or `31` only requests a consumer horizon;
  it does not alter the first 30 steps, inventory, or layout.
- Nominal gain is V025 transmit gain at the actual off-axis angle times the
  legacy deterministic path factor and peak receive gain. Realised gain is
  nominal times the V025 actual-elevation keyed fading draw.
- D2 distance is UE-to-satellite slant. The entry threshold is 1,050 km.
  Its reproduced entry elevations are 19.6865219344, 23.3958641529, and
  27.6464782299 degrees at 426, 485, and 550 km.
- Remaining visibility and D2 durations are the first forward threshold
  crossing on the 0.640-second grid. sgp4 errors and non-finite positions
  fail closed.

## Bounded rehearsal and cost

The stage-2 runner cannot express controller decisions 3-4:

- `--rehearsal` is hard-coded to three anchors, not 90.
- `_catalogue` calls `itertools.product` across all 100 users. World 1
  has 28 legal options per user at the measured anchor, so that path asks
  for `28^100` configurations before it can execute the 12 arms.
- `--calibrate` uses the same complete Cartesian catalogue and has no
  `--steps` argument. Therefore neither a full nor a reduced real-provider
  calibration can complete without the controller item-4 runner change.

No false calibration or rehearsal receipt was emitted. Instead, the allowed
per-anchor/per-row timing fallback was measured for `a-r0` on world 1:

- four-step tape acquisition (one anchor plus three offsets): 50.50 s
- acquisition cost per physical step/anchor: 12.63 s
- one complete 100-user catalogue-row evaluation over 48 boundaries:
  4.6559 s
- catalogue-row physical boundary evaluations: 48
- measured q from the stage-2 reference:
  `(4.6559/48)/(302*4/3840) = 0.30834`

At this anchor, all users have 28 legal options. Under a one-configuration
per evacuation-family interpretation, a conservative bounded-catalogue
census is at most 35,706 unique rows:

- base: 1
- all unilaterals: `100*(28-1) = 2,700`
- top-10 genuine pairwise moves: `C(10,2)*(28-1)^2 = 32,805`
- S0 top-two rows are already in the unilateral union
- up to 200 frozen/per-active-beam evacuation rows

At the measured scalar implementation cost this is 46.18 core-hours per
setting-anchor and 4,156.1 core-hours per setting-world for 90 anchors.
Literal execution of all 31 settings over four worlds projects 515,355
core-hours. Sharing the S/H/SH/T rescoring and counting only the 11 distinct
architecture/rate kernels still gives a lower-bound projection of about
182,868 core-hours, before repeated three-offset forecast evaluation. The
item-3 thinning rule would require `k >= 1,143`, impossible on a 30-step
rollout. This is an implementation-cost blocker requiring batched/shared
catalogue evaluation; it is not authority to truncate worlds, settings, or
catalogue rows.

## CONTROLLER_DECIDE / protocol blockers

1. **Per-chain interference key (new controller T7).** The checked-in
   `PrimitiveCandidate` has
   `nominal_cross_gain_by_norad: tuple[tuple[int,float],...]`; it cannot
   name two co-colour aggressor beams on one satellite. This provider
   therefore emits the current-schema cross-satellite value for the
   aggressor beam pointed at the victim candidate's cell and excludes the
   wanted NORAD. There is no across-beam aggregation. The controller has
   already assigned the required `(NORAD, beam-chain)` key and
   same-satellite P-10 term to the stage-4 engine/protocol change.
2. **Dense boundary representation (new controller T14).** A six-step
   Python-object tape peaked at 4.15 GiB RSS. The controller requires dense
   NumPy arrays consumed directly by the engine, with full sub-boundaries
   recomputed rather than serialized. That requires changing `tapes.py`
   and its consumers; this provider keeps primitive dataclass boundaries for
   the current stage-2 protocol and KATs only.
3. **Boundary row scope.** The current provider returns the legacy 28-slot
   action table for each user, not the infeasible Cartesian product of every
   user with the 57,525-chain inventory. The inventory remains a strict
   superset of every returned/legal identity. Controller T14's dense-array
   change must settle whether the phrase "every user x inventory identity"
   is literal or whether action-addressable rows are authoritative; the
   literal reading would require 5,752,500 rows per boundary and about
   8.28 billion rows per 30-step world.
4. **Beam-chain census.** The implemented chain mapping uses every legacy
   earth-fixed cell ID addressable by at least one user over the canonical
   trajectory (75 cell families in world 1), not merely the separate
   39-cell compatibility/reference subset. This preserves every legacy
   legal action identity. Seal this world-dependent addressable-cell census
   or replace it prospectively with a fixed hardware chain list.
5. **Nearest-TLE manifest fields.** `LegacyWorldProvider.tle_binding()`
   returns the exact source daily filenames and file SHA-256 values. The
   current `ExogenousWorldTape.manifest()` has no field for them or for
   per-step user positions; adding those controller-required bindings is an
   engine manifest-schema change.

Stage remains **HOLD** for a formal calibration/unit launch until items 1-5
and the bounded/batched runner are landed and sealed.
