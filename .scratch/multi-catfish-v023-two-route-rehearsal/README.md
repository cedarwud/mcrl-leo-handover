# Two-route real-shard rehearsal (non-formal engineering lane)

This package exercises the C1/C2 successor learner against whatever completed,
individually sealed real shards currently exist under separate `informed/` and
`neutral/` directories. Each shard is authenticated by the existing target
adapter before its typed C1 raw-surplus and C2 already-normalized
`target_delta` batches are admitted. Worlds missing from one mode are skipped;
the exact worlds and shard digests consumed by each mode are recorded in the
provider identity.

This is **not** a formal source-training run, a simulator or episode run, a
scientific result, an efficacy screen, or an outcome selector. It does not
invoke the formal runner CLI. Every receipt carries `formal: false`,
`rehearsal: true`, `scientific_claim: false`, `episode_training: false`, and
the claim ceiling `ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT`. The
rehearsal never creates `COMPLETE`, `canonical-receipt.json`, or another formal
completion marker.

## Input layout

```text
<shard-root>/
  informed/<shard-dir>/{COMPLETE,MANIFEST.sha256,receipt.json,c1-*.json,c2-*.json}
  neutral/<shard-dir>/{COMPLETE,MANIFEST.sha256,receipt.json,c1-*.json,c2-*.json}
```

Incomplete directories are recorded and skipped. A completed-looking shard
that fails authentication, has the wrong mode/world receipt, or fails typed
adapter loading stops the rehearsal. At least one authenticated shard is
required in each mode.

## Local tests

From the repository root:

```bash
./.venv/bin/python -m pytest -q \
  .scratch/multi-catfish-v023-two-route-rehearsal
```

The tests build shards with the producer's own writer and sealer, reuse the
factory-v3 fixture helpers and the real C2 excerpt, compare delivered arrays
bit-for-bit with adapter-produced typed arrays, exercise asymmetric worlds,
prove C2 is not divided by kappa, test sampler resume, mutate one authenticated
file, and execute a one-epoch rehearsal including exact continuation.

## Direct rehearsal command

The output-root parent must already exist. The output basename must contain
the exact substring `REHEARSAL-NONFORMAL`, and the root must not exist before
launch.

```bash
PYTHONPATH="$PWD/src" OMP_NUM_THREADS=2 ./.venv/bin/python \
  .scratch/multi-catfish-v023-two-route-rehearsal/rehearsal_two_route_training_real_shards.py \
  --shard-root /path/to/read-only-rehearsal-shards \
  --output-root /tmp/mcrl-two-route-REHEARSAL-NONFORMAL-example \
  --model-config .scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-MODEL-CONFIG.json \
  --epochs 3 \
  --train-seed 2927175120652069826
```

The declared seed is explicitly labelled `REHEARSAL_NONFORMAL` in the receipt.
Loss values are retained only as finite, non-decisional engineering telemetry.
The final stdout line is `REHEARSAL_TWO_ROUTE_PASS` or
`REHEARSAL_TWO_ROUTE_FAIL`, followed by JSON phase timings.

## Sync and run on the Ubuntu server

Run this from the controller checkout; do not run it from this implementation
session. The command syncs only the listed code packages into the shadow
checkout, then reads the rehearsal shard root and writes a fresh timestamped
non-formal output root:

```bash
.scratch/multi-catfish-v023-two-route-rehearsal/sync_run_rehearsal_server.sh \
  sat@SERVER 3 /home/sat/mcrl-v023-real-shards-rehearsal \
  2927175120652069826
```

For a later r8 **staging copy** with the same per-shard layout, replace the
third argument with that staging root. The script rejects
`/home/sat/mcrl-v023-c1c2-targets-*` and paths containing `sealed`; it must not
be pointed at a formal or sealed root. It runs with:

```text
checkout: /home/sat/mcrl-v023-successor-shadow-20260907
python:   /home/sat/mcrl-leo-handover/.venv/bin/python
PYTHONPATH=<checkout>/src
OMP_NUM_THREADS=2
oom_score_adj=1000
output:   /home/sat/mcrl-v023-two-route-REHEARSAL-NONFORMAL-<UTC timestamp>
```

The output contains `REHEARSAL-RECEIPT.json`, per-arm non-formal exports, the
pre-resume orchestration checkpoint, and the exactly continued one-epoch
checkpoint. It contains no formal completion token.
