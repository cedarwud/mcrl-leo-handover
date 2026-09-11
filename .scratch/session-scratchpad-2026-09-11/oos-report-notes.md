# OOS-PANELS report notes (fill from receipts/logs)

## Established facts so far (verified by running code)

- Disjointness: out/disjointness.json. overlap 0 vs 22-anchor (exact22 launch receipt) and 0 vs 93-anchor
  (exact93 launch receipt); 0 vs all 32 corpora found (every launch-receipt corpus.anchor_list on the box,
  EXACTGEN2 manifest anchor_records, sealed pilot-c3 / pilot-min corpora). Comparison key (world_id, step, carrier).
  No training corpus contains V025_PROBE/world/3 or V025_PROBE_R2/world/1 at all (world-level disjointness),
  and none shares the two panel dates (training worlds: world 1 = 2026-01-07, world 2 = 2026-03-11).
- Declared development: DATE-ALLOCATION-DECISION-2026-09-10.md (sha256 1d747cc4c3ba35a633db8cbd4c851ef0d3c37b52c91436e8d8826aa147ba65a5)
  lines 49-52: PROBE_R2 dates 2026-05-30/2025-07-28/2026-05-01/2026-05-28 "Remain development";
  "Earlier evaluation world 3 | 2025-11-16 | Remains development evaluation".
  tapes.py: DEVELOPMENT_WORLD_DOMAINS = V025_PROBE/world/1..4, PROBE_WORLD_DOMAINS = V025_PROBE_R2/world/1..4,
  both inside the declared V025 TRAIN inventories accepted by build_world_tape.
  Provider attestation: split TRAIN, no TEST-split TLE file opened (provider_legacy.py:431 fail-closed).
  Measured tape start dates: world 3 = 2025-11-16, PROBE_R2 world 1 = 2026-05-30. Both TRAIN.
- Encoding validation (out/validate-encoding-anchor000.json), in-sample anchor 000:
  q1v1 992/992 rows bit-identical to the EXACTGEN2 exact-source view; keys equal for all five schemas;
  q1v2/q1v3/q1v3-control max |dQ1| = 1.3094321633932982e-13 (Q2 identical);
  q1v2z max |dQ1| = 5.426242788431068e-12, max |dQ2| 0. Cause: OOS rows take the public ECEF resolver path
  (accepted 1e-9 deg seam) used by PANELFIX/PANELZ/PANELV3 for regenerated rows, not the physics-shard angle.
- Clean reference path validation: clean first-improvement at world-1 anchor 000 reproduces RANK2's clean-path
  FIRST_IMPROVEMENT_FP exactly (377 moves, 10 passes, identical assignments, bits and joules),
  strict-surface scalar evaluate calls 0. RANK2 receipt sha256 06285db20ee885700a0cfbf74c550f539d94bf2a9114c68ba7ac7df44a9f7fe7.

## To fill

- per-anchor: profiles, moves, moves_by_10s, missing actions regenerated, wall, peak RSS (core fragments)
- panel SHA-256 x5, widths, schema digests
- acceptance table: checkpoint, sha, exit, F6/F7/F8, peak RSS
- caveats: anytime incumbent is wall-clock dependent (host load recorded); rawdup v2d schema not covered;
  future exact-source prefix growth cannot reach these worlds (world 3/PROBE_R2 are outside the declared
  180-anchor order, which covers only V025_PROBE worlds 1-2).
