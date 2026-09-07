# V0.23 R7 final-verifier pair-key/C2/precision repair continuation R4

Status: `FROZEN_PRE_CORRECTED_OUTCOME_R4`

This is the versioned R4 continuation of the frozen R3 verifier repair. It
authorizes one integrity-only, read-only re-verification of the completed R7-I1
TRAIN-development shards. It does not authorize source generation, fitting,
composition replay, simulator execution, learner updates, TEST access, episode
training, threshold changes, predicate changes, decision reordering, rescue, or
scientific tuning.

## Frozen authority and authenticated prior failures

- Run root: `/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1`.
- Frozen final verifier:
  `.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py`,
  SHA-256
  `3cc573717f010d8b67ede027d05ef79f4c69497e9654d6766df50e88e9aa4717`.
- Original invalid receipt SHA-256:
  `2b14fb95b9599b1c6abd50a63ab7adaaf61e31a8bbf448ada625b4242fd6a64f`.
- Frozen R3 adapter:
  `.scratch/multi-catfish-v023-r7-domain-repair-r3/verify_v023_lcsrs_final_domain_repair.py`,
  SHA-256
  `7d242eb2ca31835ba2471334b7ab90f8d68f4c817a367a5f3f2c72fb518fff2d`.
- R3 authority manifest SHA-256:
  `4a1fb2ef124212757bdabe00bd578b5cd009977e9b4c64017b4a22ebe5990c90`.
- R3 failure log:
  `/home/sat/mcrl-v023-r7-domain-repair-20260907-r3.log`, exactly 12,279
  bytes, SHA-256
  `c76640b6b40068ad24def04d3eabcefc94d9a0ac2ba280254be4ff7a10b62fc4`,
  containing `composition/source identity array missing: pair_source_key`.

R1 and R2 evidence remains immutable and is authenticated exactly as in R3.
R4 additionally authenticates the complete R3 authority snapshot, its
two-level manifest pin, the exact R3 log bytes, size, and terminal marker, and
the absence of R3 corrected output and receipt before it creates any R4
authority snapshot.

The read-only inventory contains 193 findings: for each of 48 composition
shards, primary missing-array findings plus their cascade exceptions for both
`pair_source_key` and `pair_destination_keys` (192 findings), followed by one
decision-stage C2 diagnostic-container finding. The inventory is diagnostic
evidence, not verdict authority.

## R3 inheritance by authenticated import

R4 does not copy the R3 implementation. It imports the R3 adapter by path only
after verifying the exact R3 SHA-256 above, and calls R3's existing installs:

1. authenticated source/composition NPZ hash-domain dispatch;
2. scoped frozen-sibling import path; and
3. the unique pair-profile expected-operand broadcast.

The R3 constants `SOURCE_ARRAY_SCHEMA`, `SOURCE_ARRAY_DOMAIN`,
`COMPOSITION_ARRAY_DOMAIN`, the expected 8/48 load counts, and the frozen
preflight binding are reused from that authenticated module. R4 records the R3
digest in its receipt. No R3 source is copied into R4.

## Sole new correction 1: source-only pair-key reconstruction

The frozen identity join at
`.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:977`
receives `(source_payload, source_arrays)`. Its loop at lines 1018-1052 requires
the two names that the authenticated source NPZ does not store. R4 wraps only
`_join_composition_source` and passes the frozen function a shallow copy of the
source array mapping containing two temporary expectations:

- `pair_source_key`, contiguous int64, exact shape `(P,2)`;
- `pair_destination_keys`, contiguous int64, exact shape `(P,2,2)`.

The original mapping and every on-disk artifact remain unchanged. R4 refuses
to install if either name already exists in the source mapping. The frozen join
keeps both names and all original equality checks unchanged. No composition
value is ever read to construct a source expectation.

For every source NPZ pair row `p`, let `a = pair_anchor_index[p]` and let `k`
be its position in `flatnonzero(pair_anchor_index == a)`. R4 requires the source
JSON anchor order and phase schedule, requires the topology content digest to
match the authenticated source NPZ digest witness, and reads
`anchors[a].topology.pairs[k]`. It requires anchor-local pair counts and exact
agreement for:

- JSON `pair_id` versus source NPZ `pair_id[p]`;
- JSON `member_users` versus source NPZ `pair_user_ids[p]`; and
- JSON `designated_actions` versus source NPZ `pair_action_ids[p]`.

Only exact JSON integers in the nonnegative int64 domain are accepted. Member,
reference, and designated-action indices must be in range and legal under the
authenticated source `action_mask`.

R4 then performs two independent source-only derivations in source pair order.

JSON/topology derivation:

```text
source[p]       = anchors[a].topology.pairs[k].source_key
destinations[p] = anchors[a].topology.pairs[k].destination_keys
```

NPZ/physical derivation, with `u,v = pair_user_ids[p]`,
`du,dv = pair_action_ids[p]`, `K = physical_keys`, and
`R = reference_actions`:

```text
source_u = K[a,u,R[a,u]]
source_v = K[a,v,R[a,v]]
require source_u == source_v
source[p] = source_u
destinations[p] = K[a,[u,v],[du,dv]]
```

R4 requires shape, dtype, index, legal-mask, nonnegative-key, shared-source,
and elementwise agreement between the two derivations. It preserves global
source row order, includes every enumerated pair, and never applies
`pair_retained`. `P=0` is materialized explicitly as `(0,2)` and `(0,2,2)`
contiguous int64 arrays.

This reconstruction mirrors the source-to-topology mapping in
`.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:2257-2378`
and the composition serialization at lines 3018-3023. The writer evidence for
the source arrays is at
`.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1135-1217`.

## Sole new correction 2: exact C2 list-to-object normalization

The source writer creates one C2 diagnostic object per topology pair at
`.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:2017-2045`,
appends those objects in topology-pair order at lines 2253-2277, and writes the
resulting list as `anchors[a].c2_diagnostic` at lines 2327-2410. The frozen
accessor at
`.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:479-487`
accepts only one mapping.

R4 wraps only `_diagnostic_rows`. An existing mapping is passed to the frozen
accessor unchanged. A list is accepted only when it is nonempty and every
element is an object with exactly these writer fields:

- `diagnostic_lambda_bits_per_j_hex`;
- `exposure_count`;
- `kind`;
- `nontrivial_count`;
- `rows`;
- `runtime_default_lambda_used_for_target`;
- `target_filter_applied`; and
- `target_free_inference`.

The fixture-only `rows_total` annotation describes excerpt truncation and is
not a writer field; tests remove it before exercising normalization.

Normalization is deterministic:

1. traverse list elements in pair order;
2. assert exact agreement of `kind`, multiplier hex,
   `target_filter_applied`, `target_free_inference`, and
   `runtime_default_lambda_used_for_target`;
3. concatenate every `rows` list without filtering, dropping, changing, or
   reordering a row;
4. sum `exposure_count` and `nontrivial_count`; and
5. add `r4_per_pair_provenance`, whose entries retain the pair offset, row
   offset/count, and all seven per-pair scalar fields, plus an R4 normalization
   schema tag.

The normalized mapping is then passed to the original `_diagnostic_rows`, and
the frozen `_context_status` performs every original row identity, reference,
numeric-delta, transition, completeness, threshold, and decision check at
lines 1291-1426. R4 does not filter diagnostics by `pair_retained`; any
writer/verifier retained-panel mismatch therefore remains a closed failure.

An empty list has no object from which the five shared provenance fields or
the two count fields can be authenticated. R4 does not invent them and fails
closed with that precise reason. A missing/malformed row or field also fails
closed.

## Sole new correction 3: writer-precision C2 Q2-delta recomputation

The writer freezes the Q2 model surface as float32 at
`.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:891-920`.
It serializes each per-row `q2_delta` by subtracting two scalars from that
float32 surface and only then converting the float32 subtraction result to a
Python float at lines 1949-1952. The same frozen float32 Q2 values are widened
to float64 when stored as `q2_values` in the source NPZ at lines 1144-1151.

The frozen verifier reads those NPZ operands as float64 at
`.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:1110-1112`
and currently subtracts them in float64 when constructing
`expected_q2_delta` at lines 1375-1383. It then compares the serialized
writer value with that recomputation at lines 1394-1399 using the unchanged
float64 reporting tolerance defined at lines 264-276. Thus its operands agree,
but its arithmetic precision path does not: subtracting widened float32 values
in float64 need not equal subtracting those values in float32 and widening the
result.

R4 AST-transforms only the unique `expected_q2_delta` assignment inside
`_context_status`. For each of its two member operands, it casts the source-NPZ
value back to float32, performs the subtraction in float32 exactly as the
writer does, converts the result to Python float, and materializes the same
float64 expected array consumed by the frozen comparison. The transform fails
closed unless exactly one full expression matches. It does not change the
serialized value, operand identity, row identity, comparison function,
tolerance, target-delta path, transition checks, thresholds, or decisions.

## Scope, restoration, and receipt postconditions

All six repairs are in-memory only. The exact original `_load_npz`,
`V023_ARRAY_DOMAIN`, `_validate_pair_arrays`, `_join_composition_source`,
`_diagnostic_rows`, `_context_status`, and `sys.path` values are restored on
success and failure. Each new target is a unique named callable/expression and
a second install is refused. No global NumPy override or broad exception
suppression is permitted.

Before writing output, a successful full invocation must prove:

- exactly 8 authenticated source loads and 48 composition loads;
- exactly 48 source/composition join applications covering 8 unique worlds;
- exactly 72 list-container normalizations (8 worlds by 9 anchors), with no
  mapping fallback on the frozen writer panel;
- the unique source pair count equals both the normalized per-pair object count
  and preserved row count; and
- the float32-as-writer Q2-delta expression is applied exactly once per
  preserved C2 row and produces exactly two checked member deltas per row; and
- both source-only pair-key derivations agreed for every row.

The R4 receipt schema is
`multi-catfish-mcrl-v023-r7-final-verifier-domain-repair-v4`; its successful
status is `PASS_R7_FINAL_VERIFIER_DOMAIN_REPAIR_R4`. It records the R3 digest,
all inherited R3 installs, both reconstructed names, their dtype/shapes/order,
both-derivations agreement, source-world/pair/join counts, normalization
container/object/row/count totals, `q2_delta_precision` with
`expected_computed_in: float32-as-writer`, `rows_checked`, and checked member
delta count, and the no-TEST/no-training boundary.

## Additive server outputs and terminal rule

The controller uses checkout
`/home/sat/mcrl-v023-r7-launch-ready-20260906-r4` and server Python
`/home/sat/mcrl-leo-handover/.venv/bin/python`. Before remote package sync, the
launcher refuses an existing R4 package, log, tmux session, authority snapshot,
corrected output, or repair receipt. The controller itself refuses an existing
`repair-authority-r4/`, `final-verification-domain-repair-r4.json`, or
`domain-repair-r4-receipt.json`. It writes only those additive artifacts and,
on successful integrity verification, the existing sealer's terminal outputs.

The sealer
`.scratch/multi-catfish-v023-r7-launch-ready/seal_v023_lcsrs_result_directory.py`
must retain SHA-256
`0ac192e8bb79c9bb0deba751c595839a4723c4dede0770604cfc9f6636022a91`.
It may be invoked only after the corrected receipt and corrected verification
both authenticate `PASS_FINAL_INTEGRITY` / `VERIFIED`. Any invalid result leaves
the root unsealed. No R5, rescue, alternate threshold, or scientific token is
authorized here.

Claim ceiling:
`TRAIN_DEVELOPMENT_INTEGRITY_ONLY_DOMAIN_AND_IMPORT_CLOSURE_REPAIR_NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY`.
