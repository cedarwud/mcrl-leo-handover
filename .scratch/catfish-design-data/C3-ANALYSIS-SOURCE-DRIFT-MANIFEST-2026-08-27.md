# C3 analysis-source drift manifest

Status: reviewed compatibility exception for the frozen C3 shadow only. This is
not training-source parity and gives no runtime, reward, Main-transfer, or
scientific-effectiveness authority.

Date: 2026-08-27

## Bound fingerprints

- launched training code SHA-256 (55 paths):
  `544fcf078f7e0d74c38e79288081c60357bc64b59540120dbe4e30bffe014ec4`;
- analysis code SHA-256 (56 paths):
  `4cfc7e3043453994fc0686c3bbfa14d9a95156aeabc578b26decb2f210603a2e`;
- checkpoint SHA-256:
  `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`;
- preregistration digest:
  `3a920671dcce62075b1a21362d392b6c370c99979cba70d72a513da9ae9773f4`;
- preregistration file SHA-256:
  `8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543`.

The launched hash was independently recomputed from the exact server checkout
copied to `/tmp/mcrl-launched-source-20260825`; it equals the fingerprint stored
in the completed Main `status.json`. The analysis hash is the live result of
`_code_sha256(_default_code_paths())`. Any future change to either bound hash
invalidates this exception.

## Exhaustive source-tree difference classification

`diff -rq` over `src/`, excluding bytecode caches, found four changed files and
one analysis-only file. `scripts/run_server_training.py` and `pyproject.toml`
are byte-identical.

| Path | Launched SHA-256 | Analysis SHA-256 | Reviewed effect on C3 |
|---|---|---|---|
| `src/mcrl/env/step.py` | `db2ad1aca9c6cead0c795b7d8e72d5cdc082c7d97f004f039c140771985a4b36` | `ef6a5c73c8f22d98bbe06a6e10b0a47adc7010318d042ab32d59eb23633c9d15` | Adds `ActionEvaluation`, non-committing `evaluate_actions`, and `commit=False` handover classification. The deployed `step` path still calls `_rewards` with default `commit=True`; no existing physics expression was changed. Required by the shadow counterfactual and guarded by preview/commit parity. |
| `src/mcrl/runtime/collapse_metrics.py` | `2245562b6ee1c5c4221243e1dae0b9e095e1b29cbd72d4e8362a4a062b239089` | `fb053e68ef44d8458489a5029e05dc1c17f939d10f122b2e371b471343e4af34` | Corrects diagnostic naming and per-user Q-margin aggregation. C3 does not call collapse aggregation. |
| `src/mcrl/runtime/trainer_spec.py` | `07bffee999e20926a020cc877872651351ced43820606c6b89c3699c6e03b12b` | `85c17a2e23a26fe3abac81f747271b14bf63e2890d05c30932372949e7be3fe9` | Adds diagnostic alias properties only; no trainer configuration, state, action, or inference calculation changes. |
| `src/mcrl/runtime/training_pipeline.py` | `a735c4f4c0357151baf8c2c1fb7b155d1ebe97c57391393888cb806622091fb0` | `0e3088bb620cd08bbdcb1a8e8ae24d2ffb3a021087c44a94b8b206faedf82352` | Changes only post-run `_collapse_summary` window/aggregation. C3 imports unchanged fingerprint/RNG/config helpers, not this reporter. |
| `src/mcrl/runtime/head_pivotality.py` | absent | `82bc221a7e20886f29cbf8719406382b1ed366ca062b3663c1b641f4df507612` | Analysis-only assertions and action-key helpers; no training or environment mutation. |

All other launched source files are byte-identical, including MODQN, Q network,
state encoding, replay, candidate assembly, action contract, service resolution,
scenario, antenna, interference, link budget, energy-efficiency, and reward
calibration.

## Deployed-path dynamic parity

The retained probe
`.scratch/catfish-design-data/run_c3_source_parity_probe.py` ran the same frozen
checkpoint, preregistration, 373-file TLE view, 100 users, seed `2026082801`, and
two Q1-only Main steps once under each source tree. The probe deliberately uses
only committed `step`, not `evaluate_actions`. The two canonical JSON receipts
were byte-for-byte equal.

Exact equality held at both steps for the candidate table, 112-D encoded state,
Q1 tensor, selected action vector, served vector, link-power vector, link-rate
vector, reward matrix, active physical-beam list, system power, system
throughput, and system EE.

Selected receipts:

| Step | Candidate | Encoded state | Q1 | Actions | Link power | Link rate |
|---|---|---|---|---|---|---|
| 0 | `4d500b75...b541e` | `c9ac6498...7a90` | `003fb219...2e26` | `bcf5a4ae...3ef6` | `94e76507...8eb5` | `9f4558ac...0593` |
| 1 | `4d500b75...b541e` | `94cf6588...ed41` | `fa69480b...793e` | `a3c45972...b048` | `38bc86d0...3abe` | `414128fe...c7ac` |

The exact scalar triples were also equal:

- step 0: `P=418.97044400409544 W`,
  `R=52048457109.392456 bit/s`, `EE=124229424.42422903 bit/J`;
- step 1: `P=410.1268463886432 W`,
  `R=48442080722.88704 bit/s`, `EE=118114873.84803505 bit/J`.

Commands (each exited zero):

```text
.venv/bin/python .scratch/catfish-design-data/run_c3_source_parity_probe.py \
  --source-root /home/u24/papers/mcrl-leo-handover \
  --repo /home/u24/papers/mcrl-leo-handover \
  --tle-root /home/u24/demo/tle_data/starlink/tle

.venv/bin/python .scratch/catfish-design-data/run_c3_source_parity_probe.py \
  --source-root /tmp/mcrl-launched-source-20260825 \
  --repo /home/u24/papers/mcrl-leo-handover \
  --tle-root /home/u24/demo/tle_data/starlink/tle
```

## Ruling

For this evaluation-only C3 shadow, the analysis checkout is compatible with
the launched checkpoint for state encoding, Q1 inference, and the committed
physics path. The sole semantic extension used by C3 is the non-committing
counterfactual path, which must independently pass preview/commit parity on
every evaluated baseline and selected branch. The runner must pin this manifest
by byte SHA-256, pin both source fingerprints, and fail closed on any mismatch.
