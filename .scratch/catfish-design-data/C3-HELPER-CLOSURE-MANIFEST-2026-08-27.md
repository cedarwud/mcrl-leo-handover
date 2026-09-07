# C3 shadow helper-closure manifest

Status: frozen execution dependency closure for the evaluation-only C3 shadow.
No reward, runtime, training, Main-transfer, or effectiveness authority.

Date: 2026-08-27

The top-level runner records its own byte SHA in every bundle. Its scratch and
script import closure is separately pinned here because those files are not
covered by `_code_sha256(_default_code_paths())`:

| Import role | Path | SHA-256 |
|---|---|---|
| C3 v1 power/candidate helper | `.scratch/catfish-design-data/run_c3_intra_bottleneck_shadow.py` | `c9558d4db702bc3a84efc00b92e809f9a190409a9b6f286cb225e5ce52a40706` |
| v1 oracle/action/provenance helper | `.scratch/catfish-oracle-gate/run_oracle_gate.py` | `b50c396ea344d444e5db704aea05db613f9d6e29930524185d0f33f3cee338cb` |
| checkpoint/TLE/environment loader | `scripts/run_head_pivotality_probe.py` | `563c5c5fa04068868d02cbce542dc3a15305fd840b766dc919f257ea49dddeb9` |

Import chain:

```text
run_c3_disjoint_median_shadow.py
  -> run_c3_intra_bottleneck_shadow.py
    -> run_oracle_gate.py
      -> scripts/run_head_pivotality_probe.py
```

All ordinary `src/mcrl/**/*.py`, `scripts/run_server_training.py`, and
`pyproject.toml` remain covered by the reviewed analysis-code fingerprint
`4cfc7e3043453994fc0686c3bbfa14d9a95156aeabc578b26decb2f210603a2e`.
The C3 runner must verify this manifest and all three helper hashes before
loading the checkpoint or reading an evaluation seed. Any mismatch is an input
failure; it may not be described as a new C3 result.
