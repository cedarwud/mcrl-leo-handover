# V0.23 C1/C2 predecision capture bridge (R4)

This directory contains the source-stage bridge that supplies the missing
V0.23 C1/C2 **predecision** records.  It is deliberately separate from the
live R4 C3 gate.  Nothing here changes the C3 gate, shared authority, learner
configuration, or episode-policy training.

R3 is retained as a failed-closed historical attempt.  R4 uses a fresh server
root and the additive C1 heterogeneous-profile control documented in
`PRE-OUTCOME-CONTRACT.md`; it never overwrites or repairs R3 output.

## What is captured

For one authenticated TRAIN world, `capture_world` reuses the existing V0.23
source adapter's `_authenticate` and `_native_q12_anchor` seams.  At each
current anchor it:

* captures the existing `capture_c1_dull_rollout_sample` record;
* takes the frozen `Q1+Q2` masked argmax as Main's reference action;
* compares that physical association with the environment's previous served
  association by `(norad_id, cell_id)`;
* emits a C2 anchor only for a served physical departure; and
* applies the fixed `incumbent-hold`, otherwise maximum current
  candidate-SINR non-Main-rival rule.

The C2 anchor includes the current slot table, candidate-SINR vector, current
V0.23 state digest, native observation provenance digest, world/seed, and the
common Q1/Q2 checkpoint/manifest lineage.  Its digest is delegated to
`materialize_v023_c1c2.py:c2_anchor_sha256`, so the bridge and V2 materializer
share one formula.  The resulting canonical JSON has exactly the V2 capture
shape accepted by the materializer.  After all eight write-once world files
exist, `merge_world_captures` authenticates every file and reconstructs one
canonically ordered panel pool.  C1 lower-frontier selection and both neutral
samplers therefore run once over the complete frozen panel, not independently
per world.

The C1 neutral sampler uses the frozen rule
`c1-cluster-profile-matched-randomized-predecision-v2`.  A homogeneous
informed profile keeps the original uniform anchor-subset path.  For
heterogeneous profiles, a seeded randomized one-to-one exact-profile
bipartite matching assigns every informed anchor to a unique feasible neutral
anchor, followed by uniform without-replacement user sampling within each
alternative-count stratum.  The augmenting-path matcher is feasibility
complete, but is not uniform over the set of feasible perfect matchings.  It
uses only sealed predecision structure; informed anchors remain eligible and
overlap is allowed.  The materialized receipt must report the overlap and the
profile-preservation audit.

## Explicit boundary

The capture is source preparation only.  Its explicit runtime does use the
TRAIN simulator to traverse the frozen ten-slot source trajectory.  It retains
the C1 dull-policy frontier scores required by the existing selector and the
C2 predecision candidate-SINR vector required by the frozen source rule, but
does not retain candidate-vs-reference targets, downstream outcome traces, or
any evaluation/efficacy result and never opens TEST.  It performs no learner
update and no episode-policy training.  A capture is not an efficacy result.

The pure helpers are safe to test locally.  The server wrapper is import-inert;
it loads the source adapter and simulator only after an explicit CLI launch and
checks the output path before doing so.  It refuses to overwrite a capture.

Example on the Ubuntu server (not executed by this worker):

```text
python3 run_v023_c1c2_predecision_capture_server.py \
  --world 2026121705 \
  --tle-root /path/to/frozen/train/tle \
  --prereg /path/to/PREREG-FROZEN-2026-08-25-R2.json \
  --preflight-sha256 <preflight-manifest-sha256> \
  --output /path/to/new/v023-train-predecision-capture.json
```

The default route-local neutral seeds are `world + 17` for C1 and `world + 31`
for C2; the CLI may supply explicit frozen seeds.  Those seeds are for later
neutral materialization only, not learner initialization.

## R3 finding and current R4 blocker

R3 produced the eight write-once source captures and a panel capture, but
failed closed at true merged C1 materialization because its former
one-common-profile assumption did not fit the heterogeneous predecision
anchor profiles.  That source-only diagnosis used only the authorized capture
records (including C1 dull-frontier scores) and occurred before any candidate
target, downstream outcome, reward, or efficacy EE value was opened.  R3 bytes
remain historical failure receipts and must not be relabelled or reused.

The next source-stage action is to run this R4 entrypoint in a fresh server
root for the frozen TRAIN panel, merge the exact eight write-once JSON captures
using the predeclared panel neutral seeds, and pass the merged panel through
the V2 materializer.  True C1/C2 source ablation rows still do not exist until
that R4 run seals.  Old V0.20/E1 bytes must not be relabelled.
