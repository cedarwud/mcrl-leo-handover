Report written to `ENCODER-VARIANT-SEAM-2026-09-10.md`. Printing in full:

---

# Encoder-variant seam — Stage-C v0.25

**The seam is in place, and the default path is byte-identical: the production encoder `V025_CONTRACT_V1` reproduces the pre-change source shard bit for bit (`sha256 6572064e8048e991534178e9be61880329ec5056b602789033f2d6f1630ee0bb`, unchanged), both when selected implicitly and when driven through the new comparison runner.**

`DIAGNOSTIC_NOT_CLAIM`. No training run and no policy run was authorised or performed. No constant, threshold, sign, seed, horizon, price, service guard or acceptance rule was changed. No sealed artefact or frozen manifest was modified. `PILOT_PRIMITIVE_SOURCE_FALLBACK` is untouched at `scripts/run_v025_pilot_c3.py:89`.

---

## D1 — the seam, before the change

Widths: `q1_state` = 16 scalars, `q2_state` = 22 scalars (10 current + 3 forecast offsets × 4). The C3 route consumes the concatenation, 38.

### (a) Construction — one place, hardcoded inline

| Site | What |
|---|---|
| `src/mcrl/stagec_v025/state.py:29-46` (pre) | `Q1_FEATURES` — 16 `FeatureSpec` |
| `src/mcrl/stagec_v025/state.py:48-66` (pre) | `Q2_CURRENT_FEATURES` (10) + `Q2_OFFSET_FEATURES` (4) |
| `src/mcrl/stagec_v025/state.py:82-86` (pre) | `Q2_FEATURES = current + 3 × offsets` → 22 |
| `src/mcrl/stagec_v025/state.py:396-434` (pre) | `q1_raw` / `q2_raw` tuples built **inline inside `extract_source_rows`** — the hardcoding the task describes |
| `src/mcrl/stagec_v025/state.py:455-456` (pre) | `q1_state=_normalize(q1_raw, Q1_FEATURES)` |
| `src/mcrl/stagec_v025/state.py:288-294` (pre) | `_normalize` — the only width check at build time |

### (b) Width assumed rather than discovered

| Site | What |
|---|---|
| `src/mcrl/stagec_v025/shards.py:76` (pre) | `if len(q1) != len(Q1_FEATURES) or len(q2) != len(Q2_FEATURES)` — read-back width pinned to module constants |
| `src/mcrl/stagec_v025/synthetic.py:297-305` (pre) | evaluator fixture tables sized from `len(Q1_FEATURES)` / `len(Q2_FEATURES)` |
| `tests/.../test_stagec_pipeline.py:128,271-272,320-326` | `assert len(Q2_FEATURES) == 22`, head dims from the constants |
| `tests/.../test_contract_v1_acceptance.py:232-238,254,500-501,843-844` | same pattern |

### (c) Width baked into a serialized schema — **yes, and this is the expensive one**

`_schema_payload` (`state.py:69-79` pre) hashes `"shape": [len(features)]` **and** the full feature name/unit/scale list. Its digests are persisted in four places:

| Site | Persisted where |
|---|---|
| `state.py:460-461` (pre) | **every row**: `q1_schema_sha256`, `q2_schema_sha256` |
| `shards.py:214-215` (pre) | **shard header** (JSONL line 0) |
| `learner.py:405-406, 440-441` (pre) | **training checkpoints**, and re-checked on `load_checkpoint` |
| `merge.py:931-932` (pre) | **terminal report** |
| `interfaces.py:95` | folded into `HeadsInformation.derived_feature_schema_sha256` |

Enforced equality against the module constants at `shards.py:142` (row) and `shards.py:270` (header). **Named explicitly, as requested:** the width is inside `mcrl-v025-stagec-q1-action-v1` / `mcrl-v025-stagec-q2-action-v1`, whose SHA-256s (`c002ea88…`, `a891dd98…`) are written into `mcrl-v025-stagec-source-row-v1`, `mcrl-v025-stagec-source-shard-v1` and the lineage checkpoint schemas. Changing the encoder without a seam therefore invalidates every persisted row, header and checkpoint at once.

The **exact key-set validators** are what make this a day rather than a line: `shards.py:66` (`set(payload) != expected` for rows) and `shards.py:260` (`set(header) != expected_header`). Neither tolerates an added field, so the variant name could **not** be added as a new row or header column without breaking read-back of existing shards. That constraint drove the design in D2.

### (d) Read-back

`shards.py:71-72, 106-107` (payload → hex-float tuples), `shards.py:264` (`_row_from_payload` per line), `interfaces.py:86-87` (`q1_rows` / `q2_rows`).

### (e) Scalar heads — already width-discovering

Good news, and it is why the training code needed no width edit:

| Site | What |
|---|---|
| `learner.py:167-172` | `_route_state`: C1→q1, C2→q2, C3→q1‖q2 |
| `learner.py:342` | `dimensions = {route: batch.reference_states.shape[1] …}` |
| `learner.py:997-1004` | `AdamMLPHead.create(q1_batch.reference_states.shape[1], …)` |
| `deployment.py:34, 96, 118-119` | relative-length checks only |

Heads take `shape[1]` from the data. **Width already propagates from the rows to the heads.**

### Training / evaluation entry points

* `src/mcrl/stagec_v025/synthetic.py:714` `run_synthetic_pipeline(root, epochs, bootstrap_draws)` — the one function that runs source → shard → batches → 12-seed training → 6-arm evaluation → merge → terminal report. CLI: `python -m mcrl.stagec_v025.synthetic --output … --epochs …`.
* `scripts/run_v025_pilot_c3.py:495, 732` — the **real-physics** pilot; both call `extract_source_rows(envelope)` with no encoder argument, so it picks the seam up for free.
* Arms: `learner.py:29-36` — `FULL`, `DROP_C1`, `DROP_C2`, `DROP_C3`, `ALL_NEUTRAL_CONTROL`, plus external `BASELINE`.

---

## D2 — the seam

New module `src/mcrl/stagec_v025/encoders.py` (self-contained; imports only `canonical`, so the import graph stays acyclic).

* `EncoderVariant` (`encoders.py:95`) — name, both feature lists, both raw extractors, both schema payloads, both digests; `q1_width` / `q2_width` / `encode_q1` / `encode_q2`.
* `register_encoder_variant` (`encoders.py:130`) — the only way to add one.
* `encoder_variant(name)` (`encoders.py:191`), `active_encoder_variant()` (`encoders.py:205`), `variant_for_digests(q1, q2)` (`encoders.py:211`).
* Selection: `MCRL_STAGEC_ENCODER_VARIANT`, default `V025_CONTRACT_V1`; registration modules via `MCRL_STAGEC_ENCODER_MODULES`.

**Byte-identity.** `_schema_payload` (`encoders.py:58`) adds an `encoder_variant` key to the hashed payload **for every variant except the default**. The default payload is frozen byte-for-byte because its digest is already published in sealed shards and checkpoints. This is a deliberate one-line asymmetry, commented as such.

**Provenance — no silent misattribution.** The rows already carry `q1_schema_sha256` / `q2_schema_sha256`, and those now come from the variant (`state.py:466-467`). Because every non-default variant hashes its own name into the payload, the digest pair is unique **by construction**, and `variant_for_digests` resolves any persisted row back to exactly one variant name. A repair that changed values but not feature names would still get distinct digests — this is asserted by `test_a_variant_reusing_the_default_feature_list_still_gets_its_own_digests`. Shards may not mix variants (`shards.py:204` `_shard_encoder`). The variant name also appears literally in `schema_manifest()` (`state.py:503`).

**Width discovered, not assumed:**

| Was | Now |
|---|---|
| `shards.py:76` `len(Q1_FEATURES)` | `shards.py:76-81` — resolves the variant from the row's own digests, then compares `variant.q1_width` |
| `shards.py:142` digest equality vs constants | `shards.py:146` — subsumed by `variant_for_digests`, which rejects unregistered pairs |
| `shards.py:214-215, 270` header vs constants | `shards.py:228-229, 285-290` — header digests derive from and are checked against the shard's own encoder |
| `synthetic.py:297-305` `len(Q1_FEATURES)` | `synthetic.py:297-307` — `active_encoder_variant().q1_width` |
| `learner.py:405-406, 440-441`; `merge.py:931-932` | `active_encoder_variant().q1_schema_sha256` |

`extract_source_rows(anchor, *, encoder=None)` (`state.py:396`) defaults to the active variant. The inline raw-vector code became `default_q1_raw` / `default_q2_raw` (`state.py:141, 164`), which the default variant registers verbatim (`state.py:191`).

**Adding a variant touches no training code, no evaluation arm, no schema constant.** `encoder_variants.py` imports only `encoders` and `state`; `learner.py`, `evaluation.py`, `deployment.py`, `merge.py`, `arms.py` and `scripts/run_v025_pilot_c3.py` need no edit.

### Test — the one that matters

`tests/stagec_v025/test_encoder_variant_seam.py`. The golden digests were captured from the **pre-change tree** before any file was edited, so this is a real regression test, not a tautology:

```
PRE_CHANGE_ROWS_BLOB_SHA256      73cfb9b232347a50fc154d83185b1be9100917238ba8c1bcbd8dcb3ebdf6afee
PRE_CHANGE_ROWS_CANONICAL_SHA256 8ac8affe787bc589c7e1183b568395ddbf12f8ba04a892b6d7c79f3ae3f1a0f3
PRE_CHANGE_SHARD_FILE_SHA256     6572064e8048e991534178e9be61880329ec5056b602789033f2d6f1630ee0bb
PRE_CHANGE_Q1_SCHEMA_SHA256      c002ea883a4ab727f9e00cc15866f5b9d37abca645963fd3db2f2db7c6cc887a
PRE_CHANGE_Q2_SCHEMA_SHA256      a891dd9831d76bccd981cef054ff204fa1d49c3cf6e5f3265015f16f1057019c
```

The tests build all 12 rows of `make_synthetic_anchors()` both implicitly and with the variant named explicitly, and compare exact canonical-JSON bytes against those digests and against each other, in memory and after `write_source_shard`.

---

## D3 — `IDENTITY_PLUS_ZERO`

`src/mcrl/stagec_v025/encoder_variants.py`, 31 lines, imports nothing from training, evaluation or serialization. Appends one always-zero scalar (`FeatureSpec("identity_plus_zero_pad", "constant", 1.0)`) to each vector: 16→17, 22→23. Scientifically meaningless on purpose.

Proven end to end by tests and by the runner below: rows build (17/23 with the last element exactly `0.0` and the prefix equal to the default), persist, read back identically through `write_source_shard`/`read_source_shard`, and train-step — `build_pairwise_batches` yields C1 `shape[1] == 17`, C2 `== 23`, C3 `== 40`. **No edit outside `encoder_variants.py` was needed to make the width change propagate.**

---

## D4 — comparison runner

`scripts/compare_encoder_variants.py`. Runs the existing `run_synthetic_pipeline` unchanged, once per named variant in its own subprocess (so encoder selection is a clean process-wide fact), over identical anchors, seeds and arms, and emits a side-by-side table plus `comparison.json` / `comparison.txt`.

```
PYTHONPATH=src nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python \
  scripts/compare_encoder_variants.py --output .scratch/encoder-seam-smoke \
  --epochs 3 --bootstrap-draws 16
```

```
SMOKE TEST OF THE ENCODER-VARIANT PLUMBING -- NOT EVIDENCE ABOUT ANY ENCODER.
variant             q1_w  q2_w  row_q1  row_q2  rows  seeds  arms  epochs  eval_calls  q1_schema     shard_sha256
------------------  ----  ----  ------  ------  ----  -----  ----  ------  ----------  ------------  ------------
V025_CONTRACT_V1    16    22    16      22      12    12     6     3       1161        c002ea883a4a  6572064e8048
IDENTITY_PLUS_ZERO  17    23    17      23      12    12     6     3       1161        9fbe9727dd98  307186e80ee0
```

**This is a smoke test of the plumbing. It is not evidence about any encoder.** The two rows differ only in width and in the digests that width implies; the arm count, seed count, anchor count and evaluator call count are identical, which is the point.

Note the default arm's `shard_sha256` `6572064e8048…` is the pre-change golden — byte identity holds through the *whole* pipeline, not just the unit test.

Configuration is the smallest that exercises every path: **one world** (`V025_SYNTHETIC/source/1`), **two anchors** × 2 users → 12 rows, **3 epochs**, 6 arms. It is **12 learner seeds, not one** — see D5.

---

## Commands run, and their output

```
$ PYTHONPATH=src nice -n 15 …/python -m pytest tests/stagec_v025/ -q     # pre-change baseline
...................                                                      [100%]
real 20m1.868s

$ PYTHONPATH=src nice -n 15 …/python -m pytest tests/stagec_v025/test_encoder_variant_seam.py -q
...............                                                          [100%]

$ PYTHONPATH=src nice -n 15 …/python -m pytest tests/stagec_v025/ -q     # post-change
..................................                                       [100%]   (exit 0)
```

19 pre-existing tests passed before; 34 pass after (19 pre-existing, unmodified, + 15 new). No pre-existing test was edited.

Change footprint: 5 files modified (`state.py`, `shards.py`, `learner.py`, `merge.py`, `synthetic.py`; +143/−108), 3 files added (`encoders.py`, `encoder_variants.py`, `compare_encoder_variants.py`), 1 test file added.

---

## D5 — what I did not do, and where the seam is still leaky

**Did not do**

1. **No encoder repair, and no opinion on one.** `IDENTITY_PLUS_ZERO` adds a zero. It carries no hypothesis about what the two investigations will recommend.
2. **No training run, no policy run.** The D4 demonstration is the pre-existing synthetic fixture pipeline at 3 epochs. It produces no measurement and supports no claim.
3. **No sealed artefact or frozen manifest touched.** Nothing under `artifacts/` was written or read for mutation; all output went to `.scratch/encoder-seam-smoke/`.
4. **Did not add a row or header column for the variant name.** `shards.py:66` and `shards.py:260` validate exact key sets, so a new field would have broken read-back of existing shards and would have broken byte-identity. The name is carried by the schema digests instead (see the leak below).
5. **Did not touch the real pilot** `scripts/run_v025_pilot_c3.py`, or `PILOT_PRIMITIVE_SOURCE_FALLBACK`. It inherits the seam through `extract_source_rows`.
6. **Did not run the real-physics pilot under either variant.** Only the synthetic pipeline was exercised. The real path is wired but unproven at runtime.

**Still leaky**

1. **The pilot's `CODE_DIGEST` moves.** `scripts/run_v025_pilot_c3.py:121` computes `CODE_DIGEST` by hashing *every* `.py` in `src/mcrl/stagec_v025/`. Adding `encoders.py` and `encoder_variants.py` changes it from `43b4f4f4fb0a1214…` to `e41dfabe7f9db56b…`. Rows from the real pilot after this change will therefore differ from previously sealed real-pilot rows in `code_digest` — correct semantics (the code did change), but it means "byte-identical rows" is literally true only where `code_digest` is a fixture constant, which is the synthetic path. **Anyone diffing new real-pilot rows against sealed ones must expect exactly this one field to move.** This is the single most likely thing to surprise a reviewer.
2. **The variant name is carried by digest, not as a literal string, on the wire.** A row names its encoder via `(q1_schema_sha256, q2_schema_sha256)`. Resolution requires the defining module to be importable. If a variant is registered, rows are written, and the module is later deleted, those rows become unreadable (`variant_for_digests` raises) rather than misattributed. That is the safe failure direction, but it is a real operational coupling: **variant modules must outlive the rows they produce.**
3. **`active_encoder_variant()` is process-global.** Two variants cannot be built in one interpreter via the env var; the comparison runner uses subprocesses for exactly this reason. In-process callers must pass `encoder=` explicitly. Nothing prevents a future caller from forgetting to.
4. **Checkpoint stamps use the active variant, not the batch's.** `learner.py:406-407` and `441-442` read `active_encoder_variant()` because the orchestrator holds batches, not rows. If someone trains with `encoder=` passed explicitly while the env var says something else, the checkpoint stamp would be wrong. The batches' `source_authority_sha256` still binds the true row digests (`learner.py:209-211`), so the inconsistency is detectable but not prevented. **Threading the encoder through `PairwiseBatch` would fix this properly and was deliberately not done**, because it would change the batch payload digest and therefore every checkpoint.
5. **`run_synthetic_pipeline` has no seed knob.** D4 asked for one seed; the fixture hardcodes 12 (`learner.py:40-41`). Adding a parameter is refactoring beyond the seam, so the demonstration runs 12 seeds. Wall-clock is a few minutes per arm, so this did not matter, but the "smallest configuration" is 12 seeds, not one.
6. **Pre-existing tests still assert the literal widths** (`test_stagec_pipeline.py:128` `assert len(Q2_FEATURES) == 22`, and similar). They pass because the default is unchanged. Under a non-default variant they would be wrong. They were deliberately left alone — they are correct assertions about the *production* encoder.
7. **`schema_manifest()` gained an `encoder_variant` key**, moving its digest from `d93d0ed5cda3806f…` to `0ce8c2328ab4cd83…`. This is the one payload in the change whose bytes are *not* preserved. It has no consumer in `src/mcrl/stagec_v025/`, `tests/` or `scripts/` (verified by grep — the only `schema_manifest` test is `physics_v025`'s own, unrelated function), and it is not written into any row, header or checkpoint, so this is believed safe. It is called out here rather than buried because it is the sole exception to the byte-identity claim on the default path.
