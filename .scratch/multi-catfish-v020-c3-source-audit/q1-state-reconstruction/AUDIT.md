# V0.14 compact-source Q1-state reconstruction audit

Date: 2026-09-04  
Scope: offline, read-only reconstruction of the frozen V0.14 compact source  
Claim ceiling: `OFFLINE_Q1_STATE_RECONSTRUCTION_ONLY_NO_EE_EFFICACY`

## Decision

**Verified decision: source regeneration is not required for this specific Q1
state-reconstruction task.** The stored V0.14 `q2_states` and `q3_states`
contain enough information to recover the native 228-D Q1 input layout. Applying
the already frozen Q1 checkpoint for each lineage reproduces the stored
`q1_values` surface within float32 forward-pass tolerance on all 21 allowed
shards and preserves every legal argmax.

This is an offline closure result only. It does not establish EE efficacy, does
not validate a new learner, and does not authorize an episode or long training
run. It may support a separately authorized offline Q1 relabeling/repricing
step.

## Verified scope and boundaries

The re-runnable script
[`reconstruct_q1_state_from_v014.py`](reconstruct_q1_state_from_v014.py)
authenticated and read only the frozen source panel at
`artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/source-panel/shards/`:

* four TRAIN worlds (`2026108001`–`2026108004`) and three internal-validation
  worlds (`2026108005`–`2026108007`), each crossed with the three frozen Q1
  lineages (`2026092101`–`2026092103`);
* exactly 21 regular shard directories, 1,000 rows per shard, 21,000 rows total;
* 558,278 legal action entries in the stored masks;
* per-shard metadata, NPZ, array-set, and `source.sha256` receipts all passed;
* every source metadata record explicitly keeps `test_split_opened`,
  `episode_training`, and `learner_update` false.

No simulator was instantiated or advanced. No RNG, learner, episode, TEST split,
or source file was opened for writing.

## Reconstruction verified from the current source contracts

The compact V0.14 Q3 state has ten action-aligned 28-wide blocks followed by
seven globals. The reconstruction uses the following non-overlapping mapping:

```text
Q1 blocks 0..3 = Q3 blocks 0..3
Q1 block 4    = Q3 block 9 + Q3 block 8 / 100
Q1 block 5    = Q3 block 5
Q1 block 6    = (Q3 block 6 > 0) OR focal continuation satellite-slot
Q1 block 7    = Q3 block 7
Q1 globals    = Q3 globals 0..3
```

Here Q3 block 8 is the binary continuation surface, Q3 block 9 is committed
non-focal beam load, Q3 block 6 is the strictly non-focal previous-satellite
rate-burden surface, and the focal continuation signal is expanded from the
four seven-action satellite groups. The satellite block is a logical OR, not an
addition; addition would create invalid binary value `2`. Q2 is used for shape,
mask, and terminal/context cross-checks, not as a substitute for the Q3
continuation information.

The mapping agrees with the implementation contracts in:

* `src/mcrl/runtime/ee_axis_state.py` (native 228-D block order and binary
  satellite-active semantics);
* `src/mcrl/runtime/ee_axis_v04_c3_state.py` (V0.4 changes only the two burden
  blocks while retaining the native beam/power and temporal layout);
* `src/mcrl/runtime/ee_axis_v014_q3_state.py` (V0.14 Q3 block/global order);
* `src/mcrl/runtime/ee_axis_v014_q2_state.py` (Q2 shape and mask surface); and
* `.scratch/multi-catfish-v014-learner/run_v014_source_shard.py` (the stored
  Q1 labels were produced from the native encoder before Q2/Q3 compact surfaces
  were written).

The ten-step contract was also checked on every shard: terminal step 9 has the
frozen all-zero Q2 surface, while non-terminal Q2 block 3 (`satellite_active`)
equals the positive-signal test of Q3 block 6 on every non-terminal row. This
prevents incorrectly inferring terminality from a zero background feature.

## Q-value and action agreement

The table reports the maximum absolute error over all 28 actions, the maximum
pointwise relative error using `max(abs(q_expected), 1e-12)` as denominator, and
the legal-mask argmax agreement. All rows are 1,000 per shard.

| shard | max abs error | max pointwise relative error | legal argmax |
|---|---:|---:|---:|
| 2026108001-2026092101 | 5.960464477539062e-08 | 4.602144599383312e-05 | 1000/1000 |
| 2026108001-2026092102 | 1.192092895507812e-07 | 6.144393241167435e-05 | 1000/1000 |
| 2026108001-2026092103 | 1.192092895507812e-07 | 5.924872615238772e-05 | 1000/1000 |
| 2026108002-2026092101 | 5.960464477539062e-08 | 3.235198964736332e-04 | 1000/1000 |
| 2026108002-2026092102 | 1.192092895507812e-07 | 1.021346134204882e-04 | 1000/1000 |
| 2026108002-2026092103 | 1.192092895507812e-07 | 5.373455131649651e-04 | 1000/1000 |
| 2026108003-2026092101 | 5.960464477539062e-08 | 1.109877913429523e-04 | 1000/1000 |
| 2026108003-2026092102 | 1.192092895507812e-07 | 1.502178158329578e-05 | 1000/1000 |
| 2026108003-2026092103 | 5.960464477539062e-08 | 4.173971116119877e-05 | 1000/1000 |
| 2026108004-2026092101 | 5.960464477539062e-08 | 1.162340178225494e-04 | 1000/1000 |
| 2026108004-2026092102 | 1.192092895507812e-07 | 1.402131239484016e-04 | 1000/1000 |
| 2026108004-2026092103 | 1.192092895507812e-07 | 2.306406042783832e-05 | 1000/1000 |
| 2026108005-2026092101 | 7.450580596923828e-08 | 7.011311582686734e-05 | 1000/1000 |
| 2026108005-2026092102 | 1.192092895507812e-07 | 1.251016450866329e-04 | 1000/1000 |
| 2026108005-2026092103 | 5.960464477539062e-08 | 5.250032812705079e-05 | 1000/1000 |
| 2026108006-2026092101 | 5.960464477539062e-08 | 2.342432381785246e-05 | 1000/1000 |
| 2026108006-2026092102 | 1.192092895507812e-07 | 2.203905320227443e-05 | 1000/1000 |
| 2026108006-2026092103 | 5.960464477539062e-08 | 3.457635323202462e-05 | 1000/1000 |
| 2026108007-2026092101 | 5.960464477539062e-08 | 1.296428339923511e-04 | 1000/1000 |
| 2026108007-2026092102 | 1.192092895507812e-07 | 1.493875112040633e-04 | 1000/1000 |
| 2026108007-2026092103 | 1.192092895507812e-07 | 3.091954733782697e-05 | 1000/1000 |
| **pooled** | **1.1920928955078125e-07** | **5.373455131649651e-04** | **21000/21000** |

The pointwise-relative maximum is driven by a value close to zero. Relative to
the per-shard maximum absolute Q1 surface scale, the pooled maximum is
`1.6962849324437563e-07`. These are numerical reconstruction diagnostics, not
performance or acceptance thresholds. The audit tolerances used by the script
are `1e-6` absolute and `1e-3` pointwise relative.

## OPS-3 reading cross-check

**Verified fact:** the Fable lane's Addendum A and the current
`src/mcrl/runtime/ee_axis_ops3.py` agree on the physical projected-persistence
mechanics: `H_t = min(3, T-1-t)`, absorbing `chi`, frozen non-focal background,
canonical marginal network power, per-outage `-kappa`, and `1/H_t` aggregation.
The runtime also enforces an all-zero terminal surface and retains the
action-aligned projected features described by
`docs/MULTI-CATFISH-C2-OPS3-FORMULA-PROBE-CONTRACT-2026-09-02.md`.

**Verified discrepancy:** the frozen formula contract and runtime define the
centered surface

```text
Q2*(s,a) = (Z(s,a) - Z(s,a^M)) / kappa
```

whereas Addendum A and the Fable Stage 1b OPS-3 receipt explicitly use
`Q2*_OPS3 = Z(s,a) / kappa` and leave the reference-row subtraction as a
diagnostic. The omitted reference term is action-independent and therefore does
not change an argmax, but it changes the Q-value gauge and violates the current
formula contract's exact reference-row-zero convention. Consequently, the O-arm
numbers are correctly labelled **the Fable lane's reading of OPS-3**, not a
result from the current canonical centered OPS-3 surface. No attempt was made
here to repair or rerun that lane.

## Evidence classification

* **Verified fact:** all 21 authenticated compact shards reconstruct the frozen
  Q1 state sufficiently to reproduce all stored Q1 values within the reported
  float32 forward-pass errors and agree on every legal action argmax.
* **Inference:** under the same native state layout, action ordering, user-count
  normalization, and frozen Q1 checkpoint loader, these compact shards are
  sufficient for an offline Q1 relabeling/repricing operation. A new source
  regeneration is not needed solely to obtain the missing 228-D Q1 state.
* **Proposal:** if an independently authorized learner experiment later needs
  Q1 relabels, use the reconstruction script as a preprocessing receipt and
  keep its claim ceiling separate from any subsequent learner or EE result.

## Reproduction and integrity

Run from the repository root:

```bash
.venv/bin/python .scratch/multi-catfish-v020-c3-source-audit/q1-state-reconstruction/reconstruct_q1_state_from_v014.py
.venv/bin/pytest -q .scratch/multi-catfish-v020-c3-source-audit/q1-state-reconstruction/test_reconstruct_q1_state_from_v014.py
```

The first command rewrites `RESULT.json` from the authenticated source panel;
the test command includes the synthetic layout/OR regression and a full
read-only 21-shard rerun. `MANIFEST.sha256` records the final hashes of this
report, the result, the script, and the tests.
