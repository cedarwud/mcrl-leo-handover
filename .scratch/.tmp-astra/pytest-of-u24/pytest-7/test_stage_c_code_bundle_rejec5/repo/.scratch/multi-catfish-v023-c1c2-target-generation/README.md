# V0.23 C1/C2 source-to-target generation seam

This directory prepares the next bounded server step.  It does not launch a
server, open `TEST`, update a learner, or modify any shared authority.  The
entry point is `generate_v023_c1c2_targets.py`.

## What the seam does

1. Authenticates one canonical V0.23 `TRAIN` predecision capture and the four
   write-once materialization files (`C1 informed`, `C1 neutral`, `C2
   informed`, `C2 neutral`).  It checks the materializer's own serializers,
   receipt, file hashes, pool digest, and equal budgets before loading the
   simulator.
2. Replays only the declared source world/anchor.  C1 anchors are recovered
   with the captured source seed, step, state digest, Main action vector, and
   slot tables.  C2 anchors are recovered with the captured world/seed,
   observation/state digests, departure key, SINR vector, slot table, horizon,
   and release grammar.  Any digest or action mismatch fails closed.
3. Delegates all physical target work to existing production primitives:

   * C1: `mcrl.runtime.ee_axis_opening_runner.materialize_opening_opportunity`
     -> `EEAxisOpeningDataset.from_results/write_opening_dataset`.
   * C2: `.scratch/c2-v03/c2_temporal_fork_trainer_backend.py`'s
     `C2TemporalForkTrainerBackend.prepare_one_candidate` and
     `PreparedC2Fork.run_forecast` ->
     `mcrl.runtime.ee_axis_temporal_capture.capture_temporal_anchor` /
     `materialize_temporal_pair` -> `EEAxisTemporalDataset`.

No target formula is copied into this directory.  Lambda, kappa, the keyed
common-field family, C2 horizon, and release grammar are read from the current
authenticated V0.23 source/temporal contracts and are bound in the output
receipt.  The replay also requires each C2 anchor's declared `world_id` and
`source_seed` to agree before using that seed.

## Inputs and outputs

The input capture must be a fresh panel sealed by
`.scratch/multi-catfish-v023-c1c2-predecision-capture`; the materialization
directory must be the output of
`.scratch/multi-catfish-v023-c1c2-neutral-materialization` for that exact
capture.  Use a new output root every time; all target files are write-once.

Example server command (do not run on a workstation):

```bash
python3 .scratch/multi-catfish-v023-c1c2-target-generation/generate_v023_c1c2_targets.py \
  --capture /path/to/fresh/v023-train-panel.json \
  --materialization-dir /path/to/fresh/materialized-source \
  --output /path/to/fresh/targets-r1 \
  --tle-root /path/to/frozen/tle \
  --prereg artifacts/PREREG-FROZEN-2026-08-25-R2.json \
  --input-dir artifacts/training-2026-08-25-rerun01 \
  --manifest .scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.json \
  --manifest-digest .scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.sha256 \
  --execution-addendum docs/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md
```

The output contains one typed opening dataset per C1 route/world and one typed
temporal dataset per C2 route/world, plus a receipt and SHA-256 manifest.  C1
is kept per world because the existing opening-dataset contract binds one
keyed-field root per dataset.  C2 rows are likewise emitted per world for
uniform replay accounting, although the temporal dataset contract can combine
worlds later.

## Claim ceiling

`TARGETS_MATERIALIZED_TRAIN` means only that current physical source records
were generated and validated.  It is not evidence of C1/C2 learnability, EE
efficacy, ablation ordering, policy quality, or deployment improvement.  A
target-generation failure is not a scientific negative result; it means the
declared source/replay contract was not reproduced.

The next heavy step after this local seam is a fresh Ubuntu-server replay over
the sealed TRAIN panel for both informed and equal-budget neutral arms.  Only
after its receipt is green should a separate learner-screen contract be frozen.

## Bounded runtime probe (no target output)

Before launching the full replay, run the read-only benchmark on Ubuntu.  It
imports this exact generator, prepares the same 100-user runtime, selects one
same-world/same-step C2 opportunity at a step no later than 2, and prints only
a timing JSON to stdout.  The temporary archive/cache is removed on exit; no
target root, receipt, dataset, TEST input, learner, or replay update is used.

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
/home/sat/mcrl-leo-handover/.venv/bin/python \
  .scratch/multi-catfish-v023-c1c2-target-generation/benchmark_v023_c1c2_targets.py \
  --capture /home/sat/mcrl-v023-c1c2-predecision-20260906-r4/capture-run/panel-capture.json \
  --materialization-dir /home/sat/mcrl-v023-c1c2-predecision-20260906-r4/capture-run/materialized-source \
  --tle-root /home/sat/mcrl-runtime/tle-frozen-20260820 \
  --prereg artifacts/PREREG-FROZEN-2026-08-25-R2.json \
  --manifest .scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.json \
  --manifest-digest .scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.sha256 \
  --execution-addendum docs/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md \
  --mode informed --anchor-count 1 --max-step 2 --timeout-s 540
```

The output's `linear_estimate` is C2-only and excludes C1 plus controller
merge/seal overhead.  If the one-anchor unit is green and under 9 minutes,
repeat with `--anchor-count 2` or `4`; a timeout fails closed and must not be
extrapolated.  Add `--mode neutral` (or use `--mode both`) to measure the
equal-budget control route.
