# V0.12 attempt 1 incident receipt

At 2026-09-03 00:35 UTC, all six `DROP_C3` shards had written valid receipts,
while all twelve `FULL_ZR` / `FULL_HR` processes reached receipt serialization
and failed with the same exception: a NumPy Boolean scalar was not accepted by
the standard JSON encoder.  No FULL shard wrote `shard.json`, so attempt 1
contains no usable C3 oracle outcome and cannot be merged.

The repair is confined to the canonical JSON boundary: finite NumPy Boolean,
integer, and floating scalars are converted to their equal Python scalar
values.  Arrays, objects, and non-finite floating values remain rejected.
Neither C3 formula, candidate order, seed, lineage, action, physics path, nor
acceptance gate changed.

The repaired focused suite passed 30/30 and the related suite passed 94/94.
Because the runner SHA changed, the six successful DROP receipts from attempt
1 are not reused.  The entire 18-shard panel must run again under one repaired
runner authority.

Claim ceiling: plumbing incident and repair evidence only; no C3 scientific
outcome was available from attempt 1.
