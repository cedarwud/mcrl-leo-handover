# E1 C2 train-only action-graph expansion contract

Status: implementation and non-heavy unit tests complete; neither phase has
been run against experiment artifacts.

## Scientific boundary

This is a one-time structural repair of C2 train comparison-graph coverage.
It is not a canonical equal-budget source ablation and it does not change or
replace the original 4-train/3-validation/0-test corpus.

The fixed prospective source-seed order is exactly
`2026092201..2026092220`. `prepare` seals that order before it discovers any
candidate topology. It then inspects only the pre-outcome
`(reference_action, candidate_action)` edges emitted by the existing
`_discover_c2_schedule` implementation. It selects the first prefix for which:

1. every C2 validation action contrast reported unsupported by the sealed
   census is connected in the augmented train comparison graph; and
2. every endpoint action of those contrasts occurs in at least three new C2
   clusters drawn from at least two selected source seeds.

If the fixed pool cannot satisfy both conditions, the prepare status is
`INSUFFICIENT_COVERAGE`. A missing/insufficient schedule inside the prefix is
also terminal. No seed may be skipped, reordered, substituted, or drawn from
a second pool.

Selection never reads target values, detached forecast outcomes, validation
dataset documents, a test split, model predictions, MAE, service metrics, or
EE. The already-sealed source receipt supplies the corpus file digests. This
runner hashes only source authority/control files and never reads an opening,
temporal, or generation-detail dataset byte. Its output is required to live
outside the source root, so the original corpus cannot be overwritten.

## Two sealed phases

`prepare` authenticates and cross-binds:

- the action-shared base source supplement result and seal;
- the independent 4/3/0 no-test verification result and seal;
- the target-free action-graph census result and seal;
- the source receipt, preregistration, source manifest, frozen Main
  checkpoint, environment/reward lineage, original receipt-bound dataset
  digests, frozen lambda/interval constants, and exact authority/control-file
  hashes.

It writes `authority.json` before schedule discovery, then immutable schedule
files, `prepare-result.json`, and their seals. The prepare-result seal binds
both the result file digest and `authority_sha256`.

`generate` refuses a prepare status other than
`READY_FOR_ONE_TIME_GENERATION`, authenticates the exact selected prefix and
the unchanged base source authority/control bytes, and writes
`generation-attempt.json` before
loading Main. That marker makes any second generation attempt fail closed,
including after an interrupted first attempt. Outcome materialization calls
only the existing `_generate_c2_for_seed`; publication calls only
`write_temporal_dataset` and then reloads each dataset to verify its file,
dataset, source-manifest, and checkpoint digests. It does not run a new
calibration rollout: lambda comes from the authenticated source prereg and the
interval comes from the frozen base prereg, both sealed into the authority.

The final graph is recomputed from completed generated rows. A schedule-level
pass followed by insufficient completed-row coverage ends honestly as
`INSUFFICIENT_COVERAGE`; it never authorizes more seeds. Final datasets remain
separate, `source_partition=TRAIN`, and `held_out=false`.

## Result contract

The final `result.json` always fixes these consumer-facing fields:

- `schema`, `status`, `completion_status`, and `authority_sha256`;
- base-source, independent-verification, and census result+seal digests;
- `selected_seed_order` and `selected_schedule_file_sha256s`;
- `temporal_dataset_paths`, `temporal_dataset_file_sha256s`, and
  `temporal_dataset_sha256s` (also grouped under `temporal_datasets`);
- `final_c2_graph_report` with components, remaining contrasts, and per-needed
  action cluster/seed evidence;
- `validation_dataset_bytes_opened=false`, `test_split_opened=false`,
  `held_out_ee_evaluated=false`, `source_partition=TRAIN`, and
  `held_out=false`.

`result-seal.json` binds both `result_file_sha256` and `authority_sha256`.

## Usage

First calculate the six expected digests from already-approved immutable
artifacts; do not infer or auto-discover them inside the runner.

```bash
.venv/bin/python .scratch/ee-axis-redesign/run_v03_e1_c2_train_action_graph_expansion.py prepare \
  --source-root /absolute/path/to/action-shared-source \
  --independent-root /absolute/path/to/independent-verification \
  --census-root /absolute/path/to/action-graph-census \
  --output-dir /absolute/path/to/new-c2-train-expansion \
  --expected-base-source-result-sha256 BASE_RESULT_SHA256 \
  --expected-base-source-result-seal-sha256 BASE_SEAL_SHA256 \
  --expected-independent-result-sha256 INDEPENDENT_RESULT_SHA256 \
  --expected-independent-result-seal-sha256 INDEPENDENT_SEAL_SHA256 \
  --expected-census-result-sha256 CENSUS_RESULT_SHA256 \
  --expected-census-result-seal-sha256 CENSUS_SEAL_SHA256 \
  --tle-root /absolute/path/to/frozen/tle/root
```

Review the sealed prepare result. Run generation only if its status is
`READY_FOR_ONE_TIME_GENERATION`:

```bash
.venv/bin/python .scratch/ee-axis-redesign/run_v03_e1_c2_train_action_graph_expansion.py generate \
  --source-root /absolute/path/to/action-shared-source \
  --independent-root /absolute/path/to/independent-verification \
  --census-root /absolute/path/to/action-graph-census \
  --output-dir /absolute/path/to/new-c2-train-expansion \
  --tle-root /absolute/path/to/frozen/tle/root
```

Generation is the heavy phase. Run it on the Ubuntu server: SSH there, sync
the repository plus the exact sealed source/authority artifacts, confirm the
project `.venv` and frozen TLE path, open the worker session in this checkout,
and run the command above. Expected wall time depends on the selected prefix;
budget roughly the existing C2 per-seed generation time multiplied by the
selected seed count. Do not launch EE, tests, or validation metrics afterward
as part of this runner.

The non-heavy contract test is:

```bash
.venv/bin/python .scratch/ee-axis-redesign/test_v03_e1_c2_train_action_graph_expansion.py
```

It covers the exact pool, shortest-prefix rule, connectivity-versus-redundancy
distinction, no later-topology inspection after the first pass, pool
replacement rejection, fixed-pool insufficiency, duplicate cluster rejection,
mandatory final result fields/boundaries, result-authority cross-sealing, and
the exact existing generation/writer call boundary.
