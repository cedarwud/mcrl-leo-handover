# V0.23 C1/C2 target-generation server launch

This is a launch-only wrapper for the sealed R4 TRAIN panel. It does not
modify the C1/C2 source selection, open TEST, update a learner, or run an
episode policy. The local preflight binds the complete target-generation
runtime import closure and the current R6 fit-binding preflight manifest by
SHA-256.

The controller derives one isolated shard for every authenticated mode×world
pair (informed/neutral × each sealed world):

* `informed`: all authenticated informed C1/C2 rows;
* `neutral`: the equal-budget neutral C1/C2 rows.

Each shard writes its own target datasets, receipt, and manifest, plus
write-once started/terminal status receipts under `shard-status/`. The
controller verifies every shard against the authenticated schedule and shared
source provenance, merges only the authenticated files, and invokes the
sealer. The final output contains the four route families split by world and
a write-once `COMPLETE` marker; any failure receives a write-once `FAILED`
marker.

Before the controller is started, the launcher runs six independent bounded
C2 checks (informed/neutral × single/double/full-step), each with a strict
timeout below 600 seconds. Their write-once receipts bind the current code
manifest, generator, capture, materialization, R6 source, and D40 checkpoint;
the launcher revalidates the complete receipt root before starting tmux, and
any failed or drifted receipt blocks target generation.

## Current checkpoint closure status

The R4 capture and the R6 source authority are bound to the repriced V0.20
Q1/Q2 checkpoint
`.scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092101/checkpoints/lineage-2026092101-q2init-2026108101-rung-003000.pt`
(`d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc`).

The target generator now authenticates the same d40 bytes through
`d40_checkpoint_runtime_adapter.py` and projects C2 through the current
repriced OPS-3 selected-pair surface.  Each C2 label is already in the
normalized `delta/kappa` unit; the consumer is forbidden to divide by kappa
again.  Late anchors use the predeclared `H_t=0` terminal truncation rather
than a legacy release/fork fallback.  The historical e6 MODQN
checkpoint is not an active binding and is not copied by this launcher.  The
read-only closure audit reports `READY_TO_RELAUNCH` without opening SSH:

```bash
.venv/bin/python .scratch/multi-catfish-v023-c1c2-target-generation-launch/audit_v023_c1c2_checkpoint_closure.py --repo .
```

The adapter does not alter reward/formula/world/seed authority, and it never
trains or writes replay.  The source adapter remains the owner of d40 weight
loading; this lane only authenticates the checkpoint and consumes its Q1/Q2
background through the typed OPS-3 projection.  The old Temporal-Fork
producer is not in the active sync or preflight closure.  Do not relabel or
replace the historical checkpoint bytes.

The R4 panel is already sealed at
`/home/sat/mcrl-v023-c1c2-predecision-20260906-r4/capture-run` and is read
in place on Ubuntu. The target output is the fresh d40 root
`/home/sat/mcrl-v023-c1c2-targets-20260906-d40`.

## Local checks

```bash
.venv/bin/python -m pytest -q \
  .scratch/multi-catfish-v023-c1c2-target-generation-launch/test_v023_c1c2_target_generation_launch.py \
  .scratch/multi-catfish-v023-c1c2-target-generation-launch/test_v023_c1c2_short_benchmarks.py
.venv/bin/python .scratch/multi-catfish-v023-c1c2-target-generation-launch/preflight_v023_c1c2_targets.py \
  --manifest .scratch/multi-catfish-v023-c1c2-target-generation-launch/CODE-MANIFEST.json \
  --manifest-digest .scratch/multi-catfish-v023-c1c2-target-generation-launch/CODE-MANIFEST.sha256 \
  --repo .
```

## Dry run (no remote write)

```bash
bash .scratch/multi-catfish-v023-c1c2-target-generation-launch/sync_launch_v023_c1c2_targets_server.sh --dry-run
```

## Exact Ubuntu launch command

Run only after confirming the R6 gate has been sealed and the R4 capture
remains unchanged:

```bash
bash .scratch/multi-catfish-v023-c1c2-target-generation-launch/sync_launch_v023_c1c2_targets_server.sh
```

The launcher refuses an existing server root, output root, or tmux session.
It creates no remote state in dry-run mode. For a real invocation it runs the
checkpoint-closure audit before any SSH inspection, so the current mismatch
checkpoint-closure audit before any SSH inspection. This worker did not execute
the launch command.
