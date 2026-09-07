# R7 fourth-defect (pair keys) derivation feasibility — codex gpt-6-astra, read-only, 2026-09-07

Provenance: `codex exec --model gpt-6-astra --config 'model_reasoning_effort="max"' --sandbox read-only`, brief `codex-pairkey-feasibility-prompt.txt` (controller session e9fba164).

---

**The pair keys can be reconstructed exactly from authenticated source evidence. Repair shape (a) preserves the intended join. However, a pair-key-only R4 would still encounter a confirmed C2 JSON container mismatch downstream.**

This was a local, read-only audit; no files were modified and no network or SSH was used. Eight relevant code files matched their launch-manifest hashes. Server artifact contents and the R3 outcome remain user-reported facts.

Below, **S**, **C**, and **V** mean `v023_lcsrs_source_adapter.py`, `v023_lcsrs_composition_adapter.py`, and `verify_v023_lcsrs_final.py`, respectively, under `.scratch/multi-catfish-v023-r7-launch-ready/`.

**1. Pair-key provenance and determinism**

The upstream object is **`LCSRSC3ClosurePair`**, with fields `source_key`, `member_users`, `designated_actions`, and `destination_keys`. The keys identify `(norad_id, cell_id)` physical links. The encoder builds the physical-key surface from native action-table `norad_ids` and `cell_ids`; the source reference actions come from masked argmax of the frozen float32 Q1+Q2 snapshot. [Encoder:1234](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_lcsrs_c3_encoder.py:1234), [S:891](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:891), [Topology:365](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_lcsrs_c3_topology.py:365)

Topology enumeration:

- Groups users by `physical_keys[user, reference_actions[user]]`, sorts physical source keys and member users, and enumerates eligible exact-two sources.
- For each member, selects a legal, opening-feasible destination different from the source and occupied by a reference nonmember. Selection maximizes detached Q12, breaking ties by the lowest action index.
- Constructs the closure pair with that shared source key and the two selected destination keys, in member order. [Topology:912](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_lcsrs_c3_topology.py:912), [Topology:149](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_lcsrs_c3_topology.py:149), [Topology:958](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_lcsrs_c3_topology.py:958)

There are two equivalent JSON representations. `_pair_record()` at S:983 writes the entries used in `anchors[a].enumeration.pairs`. The representation **actually consumed by composition** is `anchors[a].topology.pairs`, produced by `topology.to_receipt()`, which also writes both keys. [S:983](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:983), [S:2300](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:2300), [Topology:733](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_lcsrs_c3_topology.py:733)

The composition path is explicit:

1. Select source NPZ pair rows belonging to each anchor; match each row against the corresponding JSON topology pair’s `pair_id`, `member_users`, and `designated_actions`.
2. Read `topology_pair["source_key"]` and `["destination_keys"]` into `DeclaredPair`.
3. Append those declared pairs to `pair_rows` in anchor/pair order.
4. Serialize their keys as int64 arrays, explicitly reshaped to `(P,2)` and `(P,2,2)`. [C:2257](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:2257), [C:2365](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:2365), [C:2818](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:2818), [C:3018](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:3018)

**Therefore both keys are deterministic functions of sealed source data.** Reconstruction needs neither composition outcomes nor simulator replay, model inference, fitting, or new randomness.

**2. Exact source-only reconstruction**

Authenticate the source JSON through its manifest-bound file hash and receipt seal, and authenticate its NPZ through the byte hash, sidecar, metadata and correct **source** array-hash domain. Preserve the existing R3 domain dispatch. [V:596](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:596), [V:607](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:607), [V:196](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:196), [R3:271](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-domain-repair-r3/verify_v023_lcsrs_final_domain_repair.py:271)

For source NPZ pair row `p`:

- Let `a = pair_anchor_index[p]`.
- Let `k` be `p`’s position in `flatnonzero(pair_anchor_index == a)`.
- Read `entry = source_json["anchors"][a]["topology"]["pairs"][k]`.
- Require the topology-list length to equal that anchor’s pair-row count. Require `entry["pair_id"]`, `["member_users"]`, and `["designated_actions"]` to match source NPZ `pair_id[p]`, `pair_user_ids[p]`, and `pair_action_ids[p]`.
- Set the expected keys from `entry["source_key"]` and `entry["destination_keys"]`.

This reproduces the composition loader’s existing mapping exactly. Preserve the source pair order and include **all enumerated pairs**; do not filter by `pair_retained`. [C:2257](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:2257), [C:2365](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:2365)

The same expected values can be derived independently using only source NPZ arrays:

```python
a = source_npz["pair_anchor_index"][p]
u, v = source_npz["pair_user_ids"][p]
du, dv = source_npz["pair_action_ids"][p]
K = source_npz["physical_keys"]
R = source_npz["reference_actions"]

expected_source[p] = K[a, u, R[a, u]]
assert np.array_equal(expected_source[p], K[a, v, R[a, v]])
expected_destinations[p] = K[a, [u, v], [du, dv]]
```

All five input arrays are emitted by the source writer. Teacher identities preserve the topology pair’s member/action order. [S:1135](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1135), [S:1191](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1191), [Teacher:349](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_lcsrs_c3_teacher.py:349)

Require valid indices, exact integer JSON keys, shapes `(2,)`/`(2,2)`, nonnegative int64-representable values, and agreement between JSON extraction and NPZ derivation. Also retain the topology-content-digest binding already used by composition. [C:2245](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:2245)

Materialized as contiguous int64 arrays of `(P,2)` and `(P,2,2)`, these have **identical dtype, shape and C-order element bytes** to the composition writer’s arrays for the same pair order. There is no floating-point calculation. Explicit shapes also handle `P=0`. These are temporary verifier expectations; nothing needs to be inserted into or written back to source evidence.

**3. Comparing the two repair shapes**

| Shape | Effect | Assessment |
|---|---|---|
| **(a) Source-only expected-key reconstruction** | Replace the nonexistent source-NPZ lookup with authenticated JSON extraction/derivation; retain exact comparison against composition. | **Recommended.** Adapts storage representation while preserving explicit source-to-composition identity verification. |
| **(b) Composition-only declaration; remove both join entries** | Retain composition keys but eliminate their direct source-key comparisons. | Weaker explicit provenance contract; unnecessary because authenticated source expectations are available. |

The existing equality helper checks **shape, dtype and values**, so shape (a) can retain its full semantics. [V:257](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:257)

One qualification: shape (b) would still have indirect numeric protection if the physical-key checks and all reference/key/member/action joins remain intact. V:893 derives composition pair keys from physical keys; V:982 joins those physical/reference arrays to source. Thus removing the explicit joins does not make arbitrary key corruption acceptable. Nevertheless, shape (a) preserves the direct source JSON declaration binding and the original audit intent more clearly. [V:893](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:893), [V:982](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:982)

**4. Complete inventory of the other names in that loop**

Let `P` be the source pair count, `D=32`, and `U` the roster size. **Every other source-side name in the loop is emitted with compatible shape and dtype.**

| Source NPZ → composition NPZ | Source shape/dtype | Composition shape/dtype | Writer evidence |
|---|---|---|---|
| `pair_anchor_index` → same | `(P,)`, int64 | same | [S:1191](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1191), [C:3008](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:3008) |
| `pair_user_ids` → `pair_member_users` | `(P,2)`, int64 | same | [S:1199](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1199), [C:3012](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:3012) |
| `pair_action_ids` → `pair_designated_actions` | `(P,2)`, int64 | same | [S:1203](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1203), [C:3015](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:3015) |
| `pair_target_by_draw` → same | `(P,D,2)`, float64 | same | [S:1207](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1207), [C:2855](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:2855) |
| `profile_actions` → `pair_profile_actions` | `(P×D,4,U)`, int64 | `(P,D,4,U)`, int64 | [S:1253](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1253), [C:3024](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:3024) |
| `profile_bits` → `pair_profile_bits` | `(P×D,4,U)`, float64 | `(P,D,4,U)`, float64 | [S:1254](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1254), [C:3027](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:3027) |
| `profile_energy_j` → `pair_profile_energy_j` | `(P×D,4)`, float64 | `(P,D,4)`, float64 | [S:1258](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1258), [C:3030](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:3030) |
| `profile_served` → `pair_profile_served` | `(P×D,4,U)`, bool | `(P,D,4,U)`, bool | [S:1262](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1262), [C:2833](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:2833) |
| `common_field_digest` → `pair_common_field_digest` | `(P×D,)`, `S64` | `(P,D)`, `S64` | [S:1278](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1278), [C:3034](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:3034) |

The allocated source profile arrays are actually added to the output dictionary at S:1349; `common_field_digest` is added at S:1378. [S:1349](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1349), [S:1378](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1378)

Ordering is compatible:

- Source assigns `pair_index = len(all_pair_teachers)` while iterating anchors and topology pairs, then appends teacher/profile records in that order. Each pair evaluates draws `0..31`. [S:2253](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:2253), [S:2272](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:2272), [S:1813](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1813)
- Source emits int64 `draw_pair_index` and `draw_index`; composition gathers each pair’s rows and requires ordered draws `0..31` plus matching `draw_pair_id`. [S:1280](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1280), [S:1297](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1297), [C:2280](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:2280)
- The final join explicitly indexes source rows by `(p,d)` and reshapes into `(P,D,...)`. Therefore the flat source profile layout is intentional and compatible. [V:1040](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:1040)

The schema’s ASCII-width notation should not be mistaken for another array axis: actual `pair_id` is `(P,)` with dtype `S256`, and the digest is `(P×D,)` with dtype `S64`. [S:1196](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1196), [Schema:143](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/SOURCE-ARTIFACT-SCHEMA.md:143)

**5. Additional failures and verification gaps**

- **CONFIRMED — C2 diagnostic container mismatch, an additional downstream blocker.** Each pair produces a diagnostic object containing `rows`; source appends those objects to an anchor list and writes that list as `anchors[a].c2_diagnostic`. The shard writer preserves the payload structure when sealing it. [S:2030](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:2030), [S:2277](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:2277), [S:2409](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:2409), [Shard writer:337](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/run_v023_lcsrs_observability_gate.py:337)

  `_diagnostic_rows()` instead requires a mapping. `_context_status()` catches that rejection, marks C2 incomplete, and skips that anchor’s diagnostic rows; the final stage rejects incomplete C2. This also affects an empty anchor list. A local in-memory probe reproduced `diagnostic must be an object`. [V:479](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:479), [V:1291](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:1291), [V:1873](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:1873)

- **SUSPECTED — real-row C2 delta rejection from arithmetic precision.** Source computes serialized `q2_delta` by subtracting float32 snapshot values, then converting the result to Python float. Its NPZ stores those Q2 operands as float64. The final verifier subtracts the float64 operands and compares against the serialized result with a float64-scale tolerance. [S:920](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:920), [S:1148](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1148), [S:1949](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1949), [V:1375](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:1375), [V:264](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:264)

  The precision-path difference is code-proven; rejection depends on actual operands. A synthetic float32 `0.3 − 0.1` example differs by `7.45e-9`, exceeding the verifier’s `1e-12` tolerance. Inventory must inspect the nested real rows even though the container failure currently prevents reaching them.

- **CONFIRMED — unreachable reference-digest validation.** V:1266 guards the Q1/Q12 reference-digest checks with `q1.shape == reference.shape`. Earlier checks establish shapes `(A,U,28)` and `(A,U)`, so this branch cannot execute for valid artifacts. This is a validation coverage gap. [V:1128](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:1128), [V:1266](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:1266)

- **CONFIRMED, already covered by R3 — inherited domain and broadcast defects.** The frozen loader uses the composition hash domain for source arrays; the frozen pair-profile comparison uses `array_equal` on `(32,4,U)` versus `(1,4,U)`. R3 installs domain dispatch, explicit profile broadcasting, and sibling-import handling. Preserve these existing adaptations. [V:55](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:55), [V:218](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:218), [V:900](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:900), [R3:339](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-domain-repair-r3/verify_v023_lcsrs_final_domain_repair.py:339)

- **CONFIRMED inventory result — no additional missing composition-required names found.** Static extraction found write sites for all **79** names required by `_verify_composition_shard`—the function’s actual name. In particular, `pair_partial_ratio_direction` is emitted as int8, collateral-by-user as bool, and tie counts as int64. No additional mandatory composition shape/dtype contradiction emerged from these writers. [V:635](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:635), [C:2689](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:2689), [C:3093](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:3093)

The decision module emits the predicate names consumed by the final stage and accepts the supplied adjudication arguments. I found no further guaranteed decision-interface failure; whether scientific predicates pass requires artifact evaluation. [Decision module:326](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/r7_balanced_successor_gate.py:326), [Decision module:340](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/r7_balanced_successor_gate.py:340), [V:1879](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:1879)

**Recommended single R4 scope:** Freeze one versioned verifier-only repair after the inventory: retain R3, reconstruct source pair keys using shape (a), and explicitly address the confirmed C2 list/object mismatch while preserving every row, provenance check and numeric comparison. Resolve the precision finding against actual rows before freezing the complete scope. Preserve sealed artifacts, thresholds and decision precedence. A pair-key-only R4 is insufficient for the frozen writer output.

The read-only inventory must include:

- Frozen-code identities, artifact seals, manifest/path bindings, NPZ byte hashes, metadata, and correct source/composition hash domains.
- Every array’s presence, actual shape and dtype across **all 8 source and 48 composition shards**, rather than only representative files.
- Exact pair panels; anchor-local JSON/NPZ pair mapping; member/action order; JSON-versus-physical-key reconstruction; final key shape/dtype/value/byte equality.
- Every remaining join listed above, plus complete, unique `(pair_index, draw_index)` coverage and matching `draw_pair_id`.
- All composition validators, including pair-level checks, baseline/teacher cross-arm identity, fit/model bindings, and confirmation that R3’s inherited fixes remain effective.
- C2 diagnostic container types; every nested diagnostic row and its provenance; float32-versus-float64 delta differences; reference-digest checks; full C2 gap lists and validation reachability.
- Complete source/fit/composition panel and decision-input coverage, recording primary failures separately from cascade errors and skipped checks. Inventory output must remain non-authoritative.
tokens used
208,994
**The pair keys can be reconstructed exactly from authenticated source evidence. Repair shape (a) preserves the intended join. However, a pair-key-only R4 would still encounter a confirmed C2 JSON container mismatch downstream.**

This was a local, read-only audit; no files were modified and no network or SSH was used. Eight relevant code files matched their launch-manifest hashes. Server artifact contents and the R3 outcome remain user-reported facts.

Below, **S**, **C**, and **V** mean `v023_lcsrs_source_adapter.py`, `v023_lcsrs_composition_adapter.py`, and `verify_v023_lcsrs_final.py`, respectively, under `.scratch/multi-catfish-v023-r7-launch-ready/`.

**1. Pair-key provenance and determinism**

The upstream object is **`LCSRSC3ClosurePair`**, with fields `source_key`, `member_users`, `designated_actions`, and `destination_keys`. The keys identify `(norad_id, cell_id)` physical links. The encoder builds the physical-key surface from native action-table `norad_ids` and `cell_ids`; the source reference actions come from masked argmax of the frozen float32 Q1+Q2 snapshot. [Encoder:1234](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_lcsrs_c3_encoder.py:1234), [S:891](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:891), [Topology:365](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_lcsrs_c3_topology.py:365)

Topology enumeration:

- Groups users by `physical_keys[user, reference_actions[user]]`, sorts physical source keys and member users, and enumerates eligible exact-two sources.
- For each member, selects a legal, opening-feasible destination different from the source and occupied by a reference nonmember. Selection maximizes detached Q12, breaking ties by the lowest action index.
- Constructs the closure pair with that shared source key and the two selected destination keys, in member order. [Topology:912](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_lcsrs_c3_topology.py:912), [Topology:149](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_lcsrs_c3_topology.py:149), [Topology:958](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_lcsrs_c3_topology.py:958)

There are two equivalent JSON representations. `_pair_record()` at S:983 writes the entries used in `anchors[a].enumeration.pairs`. The representation **actually consumed by composition** is `anchors[a].topology.pairs`, produced by `topology.to_receipt()`, which also writes both keys. [S:983](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:983), [S:2300](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:2300), [Topology:733](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_lcsrs_c3_topology.py:733)

The composition path is explicit:

1. Select source NPZ pair rows belonging to each anchor; match each row against the corresponding JSON topology pair’s `pair_id`, `member_users`, and `designated_actions`.
2. Read `topology_pair["source_key"]` and `["destination_keys"]` into `DeclaredPair`.
3. Append those declared pairs to `pair_rows` in anchor/pair order.
4. Serialize their keys as int64 arrays, explicitly reshaped to `(P,2)` and `(P,2,2)`. [C:2257](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:2257), [C:2365](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:2365), [C:2818](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:2818), [C:3018](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:3018)

**Therefore both keys are deterministic functions of sealed source data.** Reconstruction needs neither composition outcomes nor simulator replay, model inference, fitting, or new randomness.

**2. Exact source-only reconstruction**

Authenticate the source JSON through its manifest-bound file hash and receipt seal, and authenticate its NPZ through the byte hash, sidecar, metadata and correct **source** array-hash domain. Preserve the existing R3 domain dispatch. [V:596](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:596), [V:607](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:607), [V:196](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:196), [R3:271](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-domain-repair-r3/verify_v023_lcsrs_final_domain_repair.py:271)

For source NPZ pair row `p`:

- Let `a = pair_anchor_index[p]`.
- Let `k` be `p`’s position in `flatnonzero(pair_anchor_index == a)`.
- Read `entry = source_json["anchors"][a]["topology"]["pairs"][k]`.
- Require the topology-list length to equal that anchor’s pair-row count. Require `entry["pair_id"]`, `["member_users"]`, and `["designated_actions"]` to match source NPZ `pair_id[p]`, `pair_user_ids[p]`, and `pair_action_ids[p]`.
- Set the expected keys from `entry["source_key"]` and `entry["destination_keys"]`.

This reproduces the composition loader’s existing mapping exactly. Preserve the source pair order and include **all enumerated pairs**; do not filter by `pair_retained`. [C:2257](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:2257), [C:2365](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:2365)

The same expected values can be derived independently using only source NPZ arrays:

```python
a = source_npz["pair_anchor_index"][p]
u, v = source_npz["pair_user_ids"][p]
du, dv = source_npz["pair_action_ids"][p]
K = source_npz["physical_keys"]
R = source_npz["reference_actions"]

expected_source[p] = K[a, u, R[a, u]]
assert np.array_equal(expected_source[p], K[a, v, R[a, v]])
expected_destinations[p] = K[a, [u, v], [du, dv]]
```

All five input arrays are emitted by the source writer. Teacher identities preserve the topology pair’s member/action order. [S:1135](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1135), [S:1191](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1191), [Teacher:349](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_lcsrs_c3_teacher.py:349)

Require valid indices, exact integer JSON keys, shapes `(2,)`/`(2,2)`, nonnegative int64-representable values, and agreement between JSON extraction and NPZ derivation. Also retain the topology-content-digest binding already used by composition. [C:2245](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:2245)

Materialized as contiguous int64 arrays of `(P,2)` and `(P,2,2)`, these have **identical dtype, shape and C-order element bytes** to the composition writer’s arrays for the same pair order. There is no floating-point calculation. Explicit shapes also handle `P=0`. These are temporary verifier expectations; nothing needs to be inserted into or written back to source evidence.

**3. Comparing the two repair shapes**

| Shape | Effect | Assessment |
|---|---|---|
| **(a) Source-only expected-key reconstruction** | Replace the nonexistent source-NPZ lookup with authenticated JSON extraction/derivation; retain exact comparison against composition. | **Recommended.** Adapts storage representation while preserving explicit source-to-composition identity verification. |
| **(b) Composition-only declaration; remove both join entries** | Retain composition keys but eliminate their direct source-key comparisons. | Weaker explicit provenance contract; unnecessary because authenticated source expectations are available. |

The existing equality helper checks **shape, dtype and values**, so shape (a) can retain its full semantics. [V:257](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:257)

One qualification: shape (b) would still have indirect numeric protection if the physical-key checks and all reference/key/member/action joins remain intact. V:893 derives composition pair keys from physical keys; V:982 joins those physical/reference arrays to source. Thus removing the explicit joins does not make arbitrary key corruption acceptable. Nevertheless, shape (a) preserves the direct source JSON declaration binding and the original audit intent more clearly. [V:893](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:893), [V:982](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:982)

**4. Complete inventory of the other names in that loop**

Let `P` be the source pair count, `D=32`, and `U` the roster size. **Every other source-side name in the loop is emitted with compatible shape and dtype.**

| Source NPZ → composition NPZ | Source shape/dtype | Composition shape/dtype | Writer evidence |
|---|---|---|---|
| `pair_anchor_index` → same | `(P,)`, int64 | same | [S:1191](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1191), [C:3008](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:3008) |
| `pair_user_ids` → `pair_member_users` | `(P,2)`, int64 | same | [S:1199](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1199), [C:3012](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:3012) |
| `pair_action_ids` → `pair_designated_actions` | `(P,2)`, int64 | same | [S:1203](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1203), [C:3015](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:3015) |
| `pair_target_by_draw` → same | `(P,D,2)`, float64 | same | [S:1207](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1207), [C:2855](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:2855) |
| `profile_actions` → `pair_profile_actions` | `(P×D,4,U)`, int64 | `(P,D,4,U)`, int64 | [S:1253](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1253), [C:3024](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:3024) |
| `profile_bits` → `pair_profile_bits` | `(P×D,4,U)`, float64 | `(P,D,4,U)`, float64 | [S:1254](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1254), [C:3027](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:3027) |
| `profile_energy_j` → `pair_profile_energy_j` | `(P×D,4)`, float64 | `(P,D,4)`, float64 | [S:1258](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1258), [C:3030](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:3030) |
| `profile_served` → `pair_profile_served` | `(P×D,4,U)`, bool | `(P,D,4,U)`, bool | [S:1262](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1262), [C:2833](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:2833) |
| `common_field_digest` → `pair_common_field_digest` | `(P×D,)`, `S64` | `(P,D)`, `S64` | [S:1278](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1278), [C:3034](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:3034) |

The allocated source profile arrays are actually added to the output dictionary at S:1349; `common_field_digest` is added at S:1378. [S:1349](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1349), [S:1378](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1378)

Ordering is compatible:

- Source assigns `pair_index = len(all_pair_teachers)` while iterating anchors and topology pairs, then appends teacher/profile records in that order. Each pair evaluates draws `0..31`. [S:2253](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:2253), [S:2272](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:2272), [S:1813](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1813)
- Source emits int64 `draw_pair_index` and `draw_index`; composition gathers each pair’s rows and requires ordered draws `0..31` plus matching `draw_pair_id`. [S:1280](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1280), [S:1297](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1297), [C:2280](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:2280)
- The final join explicitly indexes source rows by `(p,d)` and reshapes into `(P,D,...)`. Therefore the flat source profile layout is intentional and compatible. [V:1040](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:1040)

The schema’s ASCII-width notation should not be mistaken for another array axis: actual `pair_id` is `(P,)` with dtype `S256`, and the digest is `(P×D,)` with dtype `S64`. [S:1196](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1196), [Schema:143](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/SOURCE-ARTIFACT-SCHEMA.md:143)

**5. Additional failures and verification gaps**

- **CONFIRMED — C2 diagnostic container mismatch, an additional downstream blocker.** Each pair produces a diagnostic object containing `rows`; source appends those objects to an anchor list and writes that list as `anchors[a].c2_diagnostic`. The shard writer preserves the payload structure when sealing it. [S:2030](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:2030), [S:2277](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:2277), [S:2409](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:2409), [Shard writer:337](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/run_v023_lcsrs_observability_gate.py:337)

  `_diagnostic_rows()` instead requires a mapping. `_context_status()` catches that rejection, marks C2 incomplete, and skips that anchor’s diagnostic rows; the final stage rejects incomplete C2. This also affects an empty anchor list. A local in-memory probe reproduced `diagnostic must be an object`. [V:479](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:479), [V:1291](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:1291), [V:1873](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:1873)

- **SUSPECTED — real-row C2 delta rejection from arithmetic precision.** Source computes serialized `q2_delta` by subtracting float32 snapshot values, then converting the result to Python float. Its NPZ stores those Q2 operands as float64. The final verifier subtracts the float64 operands and compares against the serialized result with a float64-scale tolerance. [S:920](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:920), [S:1148](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1148), [S:1949](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:1949), [V:1375](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:1375), [V:264](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:264)

  The precision-path difference is code-proven; rejection depends on actual operands. A synthetic float32 `0.3 − 0.1` example differs by `7.45e-9`, exceeding the verifier’s `1e-12` tolerance. Inventory must inspect the nested real rows even though the container failure currently prevents reaching them.

- **CONFIRMED — unreachable reference-digest validation.** V:1266 guards the Q1/Q12 reference-digest checks with `q1.shape == reference.shape`. Earlier checks establish shapes `(A,U,28)` and `(A,U)`, so this branch cannot execute for valid artifacts. This is a validation coverage gap. [V:1128](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:1128), [V:1266](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:1266)

- **CONFIRMED, already covered by R3 — inherited domain and broadcast defects.** The frozen loader uses the composition hash domain for source arrays; the frozen pair-profile comparison uses `array_equal` on `(32,4,U)` versus `(1,4,U)`. R3 installs domain dispatch, explicit profile broadcasting, and sibling-import handling. Preserve these existing adaptations. [V:55](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:55), [V:218](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:218), [V:900](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:900), [R3:339](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-domain-repair-r3/verify_v023_lcsrs_final_domain_repair.py:339)

- **CONFIRMED inventory result — no additional missing composition-required names found.** Static extraction found write sites for all **79** names required by `_verify_composition_shard`—the function’s actual name. In particular, `pair_partial_ratio_direction` is emitted as int8, collateral-by-user as bool, and tie counts as int64. No additional mandatory composition shape/dtype contradiction emerged from these writers. [V:635](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:635), [C:2689](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:2689), [C:3093](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_composition_adapter.py:3093)

The decision module emits the predicate names consumed by the final stage and accepts the supplied adjudication arguments. I found no further guaranteed decision-interface failure; whether scientific predicates pass requires artifact evaluation. [Decision module:326](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/r7_balanced_successor_gate.py:326), [Decision module:340](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/r7_balanced_successor_gate.py:340), [V:1879](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py:1879)

**Recommended single R4 scope:** Freeze one versioned verifier-only repair after the inventory: retain R3, reconstruct source pair keys using shape (a), and explicitly address the confirmed C2 list/object mismatch while preserving every row, provenance check and numeric comparison. Resolve the precision finding against actual rows before freezing the complete scope. Preserve sealed artifacts, thresholds and decision precedence. A pair-key-only R4 is insufficient for the frozen writer output.

The read-only inventory must include:

- Frozen-code identities, artifact seals, manifest/path bindings, NPZ byte hashes, metadata, and correct source/composition hash domains.
- Every array’s presence, actual shape and dtype across **all 8 source and 48 composition shards**, rather than only representative files.
- Exact pair panels; anchor-local JSON/NPZ pair mapping; member/action order; JSON-versus-physical-key reconstruction; final key shape/dtype/value/byte equality.
- Every remaining join listed above, plus complete, unique `(pair_index, draw_index)` coverage and matching `draw_pair_id`.
- All composition validators, including pair-level checks, baseline/teacher cross-arm identity, fit/model bindings, and confirmation that R3’s inherited fixes remain effective.
- C2 diagnostic container types; every nested diagnostic row and its provenance; float32-versus-float64 delta differences; reference-digest checks; full C2 gap lists and validation reachability.
- Complete source/fit/composition panel and decision-input coverage, recording primary failures separately from cascade errors and skipped checks. Inventory output must remain non-authoritative.
