# Two-route real-shard rehearsal (non-formal engineering lane)

This package exercises the C1/C2 successor learner against whatever completed,
producer-completed real shards currently exist under separate `informed/` and
`neutral/` directories. Each shard's manifest and receipt are authenticated by
the target-generation controller before the existing target adapter admits its
typed C1 raw-surplus and C2 already-normalized `target_delta` batches. Worlds
missing from one mode are skipped;
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
  informed/<shard-dir>/{MANIFEST.sha256,receipt.json,c1-*.json,c2-*.json}
  neutral/<shard-dir>/{MANIFEST.sha256,receipt.json,c1-*.json,c2-*.json}
```

Each shard directory is producer-complete when every file listed by its
`MANIFEST.sha256` verifies, its canonical `receipt.json` passes the
controller's mode/world shard validation, and the producer tree has the
canonical sibling `shard-status/<mode>-world-<id>.terminal.json` naming that
same mode/world. The provider records the terminal file's absolute path,
SHA-256, and reported state; a terminal record is evidence that the producer
process ended, not a merged-root seal or a reinterpretation of that state.
`COMPLETE` is deliberately neither required nor expected inside a shard: it is
the sealer's marker for the final merged target root only.

Directories missing manifest/receipt evidence or the sibling terminal record
are recorded and skipped with a reason. A shard with present but malformed or
tampered evidence, the wrong mode/world identity, or invalid typed data stops
the rehearsal. At least one authenticated shard is required in each mode.

## Local tests

From the repository root:

```bash
./.venv/bin/python -m pytest -q \
  .scratch/multi-catfish-v023-two-route-rehearsal
```

The tests build unsealed shards with the producer's own writer and controller
terminal receipts, reuse the
factory-v3 fixture helpers and the real C2 excerpt, compare delivered arrays
bit-for-bit with adapter-produced typed arrays, exercise asymmetric worlds,
prove C2 is not divided by kappa, test sampler resume, mutate one authenticated
file, cover missing terminal evidence, and execute a one-epoch rehearsal
including exact continuation.

## Read-only real-shard probe

The probe authenticates and types the available shards, then requests exactly
one batch for each route/source in provider order. It performs no learner
update or training:

```bash
/home/sat/mcrl-leo-handover/.venv/bin/python \
  .scratch/multi-catfish-v023-two-route-rehearsal/probe_real_shard_root.py \
  /home/sat/mcrl-v023-real-shards-rehearsal
```

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

The rehearsal accepts only the formal run seed `2927175120652069826`, while
explicitly labelling it `REHEARSAL_NONFORMAL` in the receipt. The model-config
file must have the frozen formal-run SHA-256
`9eafcd184bd0ec015498832be61b5c95a71373e98f63ab804c9654775a8b1d5d`.
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
