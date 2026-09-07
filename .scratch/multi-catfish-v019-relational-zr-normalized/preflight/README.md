# V0.19 TRAIN-only preflight

This directory is an isolated implementation preflight for the normalized
Q3 output unit.  It is intentionally not a scientific gate.

The authoritative pre-outcome declaration is
`MULTI-CATFISH-MCRL-V019-TRAIN-PREFLIGHT-CONTRACT-2026-09-04.md`.  The reserved
development identities and the pre-run local `rg` census are in
`SEED-CENSUS-DEV-2026-09-04.md`.

## Execution boundary

Run the worker on the Ubuntu server, not in the local WSL/browser environment.
The only permitted input is the already-opened V0.18 TRAIN source root:

```text
/home/sat/mcrl-v018-relational-learner-20260904-r1/learned-q3-panel-r1/sources/TRAIN
```

The runner authenticates its twelve source closures, then trains one Q3
learner only on the four worlds of predeclared lineage `2026092101` for
exactly 100 updates.  This matches production's one-lineage Q1/Q2 binding; the
other eight closures are authenticated but not used for an update.  It does not read
`VALIDATION` or `TEST`, start a simulator, harvest a source, or update Q1/Q2.
The local verification command is deliberately limited to synthetic tests:

```bash
.venv/bin/pytest -q \
  .scratch/multi-catfish-v019-relational-zr-normalized/preflight/tests
```

Do not run `train_only_preflight_v019.py` locally.  When the parent lane later
authorizes the server preflight, use a new write-once output directory, for
example:

```bash
python .scratch/multi-catfish-v019-relational-zr-normalized/preflight/train_only_preflight_v019.py \
  --source-root /home/sat/mcrl-v018-relational-learner-20260904-r1/learned-q3-panel-r1/sources/TRAIN \
  --output /home/sat/mcrl-v019-relational-q3-normalized-20260904-r1/preflight
```

The command exits `0` only for `GO_FRESH_GATE` and exits nonzero for `ABORT`.
Both decisions produce a receipt when the output directory itself is new.

## Receipt schema

The runner writes `receipt.json` and `receipt.sha256` once.  `receipt.json` is
canonical ASCII JSON (sorted keys, compact separators, no NaN/Infinity) and
contains:

| field | meaning |
|---|---|
| `schema`, `schema_version` | `multi-catfish-mcrl-v019-relational-q3-train-preflight-v1`, `1` |
| `status`, `decision` | `COMPLETED` with `GO_FRESH_GATE`, or `ABORTED` with `ABORT` |
| `preflight_contract_sha256`, `seed_census_sha256` | pre-outcome file identities |
| `source_root`, `source_split`, `source_count`, `source_hashes` | exact TRAIN root and all twelve authenticated source/array/bridge hashes |
| `selected_source_lineage`, `selected_source_count` | fixed lineage `2026092101` and its four used TRAIN worlds |
| `development_seeds` | one initialization seed and one schedule seed |
| `fixed_hyperparameters` | widths, activation, Adam, learning rate, batch/update counts, kappa and explicit output mode |
| `predicates` | fixed gradient and final-20 MSE thresholds plus observed values and pass/fail values |
| `diagnostics` | per-update loss, ZERO-null MSE, gradient RMS, output standard deviation, and parameter movement |
| `updates_completed` | must be exactly `100` for `GO_FRESH_GATE` |
| `q1_q2` | must remain `loaded: false`, `updated: false` |
| `boundary` | opened split and explicit false validation/TEST/simulator/source-harvest/episode flags |
| `receipt_body_sha256` | canonical digest of the receipt body before this field |

The companion file contains the SHA-256 of the exact encoded `receipt.json`
file, so it can be checked directly with `sha256sum -c`.  It has the form:

```text
<sha256 of the exact receipt.json bytes>  receipt.json
```

The final 20 scheduled records use pre-step TRAIN pair-MSE and the same-batch
all-zero Q3 MSE, both on the `bits/kappa` scale.  These numbers are
implementation diagnostics only.  A GO receipt does not establish C3 or
three-Catfish EE efficacy.
