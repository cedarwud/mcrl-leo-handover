# Codex Sol Track-B iteration-2 implementation report

## Outcome

Implemented the Astra-selected `B2_RATE_TARGET_SUM_POWER` lever without heavy compute.
The override uses rate-derived SINR, summed user RF power, beam-average-PSD overlap,
the declared capped fixed point, proportional cap allocation, inherited PA/fixed power,
full-buffer Shannon bits, and separate 95% target attainment.

The r2 finite-demand tapes are not reused because this lever changes action feasibility,
RF/interference, achieved rates, energy, OPS-3 inputs and therefore tape validity. The
preflight builder records a SHA-256 for every r2 raw tape despite rejecting those rows,
and records every authenticated E1 input file used by the per-world regeneration path.
Original snapshots/actions/masks/geometry/keyed fields remain the anchor authority;
counterfactuals are detached and only original reference physics advances continuation.

Rejected r2 tape SHA-256 records (also recomputed per-file by the preflight builder):

```text
ff1bf2160046605c7bcd22ad48514331a93c6607fc93bd43b178916de53133ca  world-1341435503386059806-nearest-eligible
ab88fbb9b4685786902c9be7f4e977013991b8db54baf62f0bedfdb7c38c35ce  world-1341435503386059806-random-masked
6f9f01672a5f2713758e6d5013f40a5001f9fa563b6eed911b3a5910e4c856c1  world-1341435503386059806-stay-if-possible
7d6e24a702cb64aa899c255c4e5ec6494fa331637986d56db98f6f1e06ee5d0a  world-3226893802015760720-nearest-eligible
28be1bfb43c6a0925f5830fd855d8f94c5d9a1152264d27832720b864eaceb0f  world-3226893802015760720-random-masked
9a5dcd7f726cb05412f2ae6f5995d5645e9b44eadc9e46d2a84e4707576c76bd  world-3226893802015760720-stay-if-possible
12ddf2328d478897ead7bfaddfc9d63769ffd2301f4520646ef65cd2223dfdf5  world-5683200792433982503-nearest-eligible
8893126c7a33e0d4a8489530bc4babf6ee5e424b6c1c3a5cb9437e1fd538d758  world-5683200792433982503-random-masked
39043c4cfb4f6865194fbb05a3f309aa9d17846769d23fd156b912073fa47940  world-5683200792433982503-stay-if-possible
6877b1505fc2836906eb59d6ae68498f641f40c1ad844350b42438187ad0e1b4  world-7374843801585642838-nearest-eligible
668382495b4fc3a8c2b8a745f1b228cae11f0017df27cebc5352d2edf38f96cf  world-7374843801585642838-random-masked
5e4cda56e7a0c2af41c3928a6c255f0ce647cf1028630cd4464e251f8bc8b117  world-7374843801585642838-stay-if-possible
```

Implemented output contracts for the original-physics control, overridden reference,
O1/O12/O123, privileged and nominal set decoders, all three literal DROP arms, the
separate exposed others-bit substitution diagnostic, pooled EE/bits/joules/service/rate
guard, all oracle marginals, exact U1/J1 map solving, LC-SRS interaction, global-witness
per-world J-U direction, immutable receipts, and no-TEST/no-training claim ceilings.

## Required controller declaration

- `TODO_CONTROLLER_DECLARE: NOMINAL_DECODER_CHANNEL_RULE`

Astra requires a deployable nominal decoder and says it may not inspect realised fading,
but does not declare the exact causal channel/fading statistic. That choice also governs
the regenerated OPS-3 and nominal set profiles. No value was invented. Unit, merge,
dry-run, preflight and launch-authority sealing fail before simulator access until the
controller supplies the rule and its matching adapter binding. `--estimate` remains
available and simulator-inert.

Observed fail-closed output:

```text
V024_ITERATION2_ERROR: TODO_CONTROLLER_DECLARE blocks launch: NOMINAL_DECODER_CHANNEL_RULE
```

## Verification

Exact test CLI (synthetic fixtures only):

```bash
cd /home/sat/mcrl-v024-codex-iter2
PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest -o addopts='' -q .scratch/multi-catfish-v024-regime-b/probe/test_iteration2_probe.py .scratch/multi-catfish-v024-regime-b/probe/test_run_v024_regime_probe.py
```

Pytest summary line:

```text
27 passed in 1.02s
```

The tests cover inherited constants, occupancy-to-power causality, proportional cap
conservation, nonconvergence, byte-identical disabled delegation, LC-SRS versus the
others-bit diagnostic, exact additive/DROP composition, set ties, guards/marginals,
map thresholds, immutable publication, disclosure length, and the TODO refusal.

## Estimate

Exact CLI:

```bash
cd /home/sat/mcrl-v024-codex-iter2
PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/run_v024_iteration2_probe.py --estimate
```

Exact output:

```json
{
  "anchors": 120,
  "arms": 10,
  "carriers": 3,
  "controller_todos": [
    "NOMINAL_DECODER_CHANNEL_RULE"
  ],
  "drop_arms": 3,
  "execution_ready": false,
  "lever": "B2_RATE_TARGET_SUM_POWER",
  "maximum_workers": 2,
  "ops3_horizon": 3,
  "raw_r2_tapes_reused": false,
  "regeneration_reason": "RATE_TARGET_SUM_POWER_CHANGES_FEASIBILITY_RF_INTERFERENCE_RATES_ENERGY_AND_OPS3",
  "units": 12,
  "worlds": 4
}
```

## Exact controller CLIs after resolving the TODO

Preflight (the sealing timestamp is intentionally controller-supplied):

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/build_iteration2_preflight.py --output .scratch/multi-catfish-v024-regime-b/probe/V024-ITERATION2-PREFLIGHT.json --exposure-timestamp-utc 2026-09-08T12:03:54Z --reviewer controller
```

One unit authority and launch (repeat for the declared 12 `WORLD:CARRIER` units, at most
two single-thread workers):

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/build_iteration2_launch_authority.py --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-ITERATION2-PREFLIGHT.json --output-root /home/sat/mcrl-v024-iteration2-probe-20260908-r1 --output .scratch/multi-catfish-v024-regime-b/probe/V024-ITERATION2-AUTHORITY-861587764845384088-2026092101.json --exposure-timestamp-utc 2026-09-08T12:03:54Z --launch-arguments -- --unit 861587764845384088:2026092101 --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-ITERATION2-PREFLIGHT.json --launch-authority .scratch/multi-catfish-v024-regime-b/probe/V024-ITERATION2-AUTHORITY-861587764845384088-2026092101.json --output /home/sat/mcrl-v024-iteration2-probe-20260908-r1
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/run_v024_iteration2_probe.py --unit 861587764845384088:2026092101 --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-ITERATION2-PREFLIGHT.json --launch-authority .scratch/multi-catfish-v024-regime-b/probe/V024-ITERATION2-AUTHORITY-861587764845384088-2026092101.json --output /home/sat/mcrl-v024-iteration2-probe-20260908-r1
```

Merge authority and launch:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/build_iteration2_launch_authority.py --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-ITERATION2-PREFLIGHT.json --output-root /home/sat/mcrl-v024-iteration2-probe-20260908-r1 --output .scratch/multi-catfish-v024-regime-b/probe/V024-ITERATION2-AUTHORITY-MERGE.json --exposure-timestamp-utc 2026-09-08T12:03:54Z --launch-arguments -- --merge --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-ITERATION2-PREFLIGHT.json --launch-authority .scratch/multi-catfish-v024-regime-b/probe/V024-ITERATION2-AUTHORITY-MERGE.json --output /home/sat/mcrl-v024-iteration2-probe-20260908-r1
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/run_v024_iteration2_probe.py --merge --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-ITERATION2-PREFLIGHT.json --launch-authority .scratch/multi-catfish-v024-regime-b/probe/V024-ITERATION2-AUTHORITY-MERGE.json --output /home/sat/mcrl-v024-iteration2-probe-20260908-r1
```

Dry-run (same exact authority binding is required if an authority is supplied):

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v024-regime-b/probe/run_v024_iteration2_probe.py --dry-run --merge --preflight .scratch/multi-catfish-v024-regime-b/probe/V024-ITERATION2-PREFLIGHT.json
```
