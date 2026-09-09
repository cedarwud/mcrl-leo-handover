# C3 pairwise cross-gain repair — 2026-09-09

## Outcome

The C3 learner now consumes the ordered pairwise cross-gain structure instead
of reducing it to pooled relation statistics. `interference_summary` and the
existing global scalar features remain unchanged, so their meanings and old
receipt comparisons are preserved.

The starting workspace already passed `_cross_gain_terms(...)` from
`scripts/run_v025_pilot_c3.py::_coalition_context` into a coalition-level
`pairwise_cross_gain_terms` tuple, but the head reduced that tuple to six
sum/max values. The repair makes the tuple a fixed-width, ordered encoder block.
No physics, thresholds, signs, seeds, horizons, prices, service guard, or
acceptance rule was changed.

## Canonical ordering and truncation

- The complete serialized relation block is sorted by `(source beam key,
  target beam key)`. Construction also canonicalizes the in-memory tuple, so
  caller order cannot affect payload bytes, payload hashes, or predictions.
- The encoder limit is **K = 32 directed pairs**.
- Selection is top-K by descending absolute gain. Ties are resolved by source
  beam key and then target beam key. The selected rows are put back into
  canonical `(source, target)` order before encoding.
- Each of the 32 positions carries normalized deterministic source-key hash,
  normalized deterministic target-key hash, gain, and a presence bit. Missing
  positions are zero-padded. The `math.fsum` of every omitted gain is appended
  as a residual, making the block width 129 and preventing silent loss.
- The payload retains the complete canonical relation list and declares K and
  the residual sum. The 180 existing pilot shards contain 2, 6, or 12 pairs,
  so none would be truncated and every residual is zero.

## Schema and hashing

- Context schema: `mcrl-v025-stagec-c3-coalition-context-v2`.
- Coalition row schema: `mcrl-v025-stagec-c3-coalition-row-v2`.
- Coalition shard schema: `mcrl-v025-stagec-c3-coalition-shard-v2`.
- Coalition batch schema: `mcrl-v025-stagec-c3-coalition-batch-v2`.
- Context payload hashing now includes the schema, declared K, residual, and
  complete ordered relation list. Each shard header also carries
  `context_payloads_sha256`, independently binding the ordered context payloads.
- Shard loading compares shard, row, and context versions before accepting
  rows. A stale shard now reports the expected and actual version triplets;
  context field drift reports missing and extra fields, and K/residual drift
  has its own explicit error.

Old v1 coalition shards therefore cannot be mixed silently with v2 training
data. They were read as raw JSON only for the diagnostic below, never loaded
into a v2 learner batch.

## T2 rewrite

T2 now constructs information twins rather than encoding their answer in
scalar `synergy`/`antagonistic` flags:

- Dominant-aggressor distribution: `(0.7, 0.1, 0.1)` into one victim beam.
- Diffuse-aggressor distribution: `(0.3, 0.3, 0.3)` into the same victim beam.
- Both total 0.9. The twins have the same anchor, physical actions, member
  features, occupancies, activation, member count, shared capacity,
  `interference_summary`, capacity margins, and global scalar features.
- Their exact normalized objective deltas have opposite signs: the dominant
  case is profitable and the diffuse case is not.
- With the pair block present, the trained interaction head predicts opposite
  signs (`dominant > 1.0`, `diffuse < 0.0`).
- With `pairwise_cross_gain_terms=()` on both, their complete canonical context
  payloads are asserted **byte-identical**. This proves that no model receiving
  only the old scalar information can separate them.
- Member-order invariance remains independently asserted. Reversing only the
  pair tuple is also asserted to preserve canonical payload bytes, payload
  SHA-256, and the head prediction.
- T2 additionally authenticates a deliberately stale v1 context shard and
  asserts the legible expected-v2/got-v1 error.

While exercising the full suite, T1's stale large-set fixture was aligned with
the already-sealed v1.2 uncapped-label rule: one size-five row, unit weight, no
capped decomposition, and reporting-only Shapley omission. This changes no
acceptance rule; it removes the fixture's contradiction with the amendment and
the existing production validator.

## Existing-shard variance diagnostic

Data: all 180 coalition shards under
`artifacts/v025-pilot-c3-20260909-PILOT_NOT_CLAIM/rows/world-*`, with exact
`psi_normalized_hex` as the response.

Method: deterministic five-fold ridge regression. Folds are assigned by the
SHA-256 of `world_id|anchor_id`; features are standardized using each training
fold; 25 ridge strengths from 1e-6 through 1e6 are compared; and the reported
number is pooled held-out R-squared at the best strength. This is a diagnostic
linear fit, not a performance or causal claim. Selecting the strength on the
same cross-validation folds can mildly bias both values upward.

| Encoder inputs | Varying predictors | Selected ridge | Held-out R-squared |
|---|---:|---:|---:|
| Old scalar features only (pair block zeroed) | 79 | 31.6227766017 | **0.651880908822** |
| Old scalar features plus ordered pair block | 113 | 100 | **0.640599043540** |

The old scalar features are therefore not near-uninformative on these pilot
rows: the linear diagnostic explains about **65.19%** of held-out variance.
Adding the pair block does not improve this particular linear diagnostic; its
R-squared is about **64.06%**, a change of **-1.13 percentage points**. This
does not negate the information-twin result: T2 proves a collision in the old
representation that the full representation removes, while the finite pilot
sample does not show incremental linear predictive value from that block.

## Verification

The TDD pass began with T2 failing on the missing v2 context contract, then
moved through the context/encoder slice to green before running the broader
suite. The scope guard kept all production changes inside the Stage-C learner
context and head; the pilot's physics and decision paths were not edited.

Command:

```text
nice -n 10 env PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest -q tests/stagec_v025 --continue-on-collection-errors
```

Pass line:

```text
...............                                                          [100%]
```

The suite contains 15 tests: T1, T2, T3, and 12 Stage-C pipeline tests.
Python compilation of the changed modules and test also passed.

## Could not do

Nothing required was left undone. Ruff was not installed in the specified
environment, so no optional Ruff run was available; `git diff --check`, Python
compilation, targeted T1/T2/T3 runs, the 12 pipeline tests, and the complete
Stage-C suite all passed.
