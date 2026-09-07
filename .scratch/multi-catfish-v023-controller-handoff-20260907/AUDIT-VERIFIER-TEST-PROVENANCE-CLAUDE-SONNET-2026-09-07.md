# Final-verifier test provenance audit (Claude Sonnet sub-agent, read-only, 2026-09-07)

Provenance: general-purpose Claude Sonnet sub-agent dispatched by the controller session e9fba164 with a read-only
brief; 34 tool uses; every claim below is a file:line citation the agent read, except the one item marked INFERENCE.

## Key structural finding (verified)

`tests/test_w201_ee_axis_lcsrs_final_verifier.py:16` loads the verifier from
`.scratch/multi-catfish-v023-c3-observability/verify_v023_lcsrs_final.py`, not the frozen R7 copy under audit.
A diff between that copy and `.scratch/multi-catfish-v023-r7-launch-ready/verify_v023_lcsrs_final.py` is 282
lines: the R7 copy's `adjudicate_section14` delegates to `r7_balanced_successor_gate.adjudicate_section14_r7`
and adds `_authenticate_launch_manifest` and new predicates. Even where test_w201's assertions pass, they
exercise a function body the frozen R7 verifier does not have.

## Table

| Test file | Fixture origin | Defects it could not catch | Evidence |
|---|---|---|---|
| `tests/test_w201_ee_axis_lcsrs_final_verifier.py` | Verifier-derived (digest) + hand-built `_CompositionShard` dicts; wrong module version | All 4 — wrong verifier copy; `_synthetic_shards()` builds `_CompositionShard(...)` directly and calls `_composition_metrics` (L113), bypassing `_load_npz`, `_validate_pair_arrays`, `_validate_composition_arrays`, `_join_composition_source` | L16 (path); L72-109; L298 `"sha256": FINAL._array_digest(array, domain=FINAL.V023_ARRAY_DOMAIN)` — digest built from the verifier's own constant |
| `tests/test_w196_ee_axis_lcsrs_fit_adapter.py` | Hand-built, test-local reimplementation | N/A to final verifier; same anti-pattern: test defines its own `_array_digest` hardcoding `b"source-array-v1"` | L67-75 |
| `tests/test_w202_ee_axis_lcsrs_server_launch_glue.py` | Text/string presence only | 1,2,3,4 — never imports or executes the verifier | L231, L262 |
| `.scratch/…/r7-launch-ready/test_r7_launch_ready.py` | Text presence + unit tests of sibling modules | 1,2,3,4 — verifier never importlib-loaded; only 4 substrings read from its text | L34-36; L208-213; L103-127 |
| `.scratch/…/r7-domain-repair-r3/test_v023_r7_domain_repair.py` | Hand-built, post-hoc (after the real-shard diagnosis) | Defect 3 — suite exists because R2 already failed on the server; contract L59-63 cites the real shard shape `[96,32,4,100]`; test reduces to toy dims | contract L59-63; test L26-97 |
| `.scratch/…/r7-final-verifier-inventory/test_inventory_v023_lcsrs_final_verifier.py` | Harness self-tests + one real-bytes call on an empty panel | 1,3,4 — `_source_raw_identity` called with `()`; no pair/composition array reaches the validators | L143-168; L163 |
| `.scratch/…/r7-balanced-successor/test_v023_lcsrs_source_adapter.py` | Real producer call (`adapter._build_sidecar_arrays`) + hand-picked subset assertion | Defect 4 — `required.issubset(arrays)` checks 8 names; `pair_source_key`/`pair_destination_keys` not in `required` | L154-183; composition writes keys at `v023_lcsrs_composition_adapter.py:3018-3021`; source never does |
| `.scratch/…/r7-balanced-successor/test_r7_pipeline_receipts.py` | Real verifier module, hand-built JSON dicts, no NPZ | 1,3,4 — only `_fit_panel_metrics` and `adjudicate_section14` | L28, L98, L109 |
| `.scratch/…/{r5,r6,r7-balanced-successor}/test_v023_r5_verifier_semantics.py` (3 identical copies) | Real production call vs independent recompute | Out of scope (scientific verifier) | L12, L50-83 |

## Per-defect verdict

1. NPZ digest domain — not catchable: `V023_ARRAY_DOMAIN` is one module constant (`verify_v023_lcsrs_final.py:55`,
   used at `:218`); the only test exercising `_load_npz`/`_array_digest` (`test_w201:298`) builds its "correct"
   digest from that same constant.
2. Sibling import — not catchable: `preflight_r7_balanced.py:17` does a bare `from r7_balanced_successor_gate import …`;
   no test loads the verifier from a foreign working directory; the r3 regression test was written after R2 failed.
3. Pair-profile equality without broadcasting — not catchable: `verify_v023_lcsrs_final.py:900` uses bare
   `np.array_equal(profile_actions[p], expected_profiles[None, :, :])`; test_w201 never calls `_validate_pair_arrays`.
4. pair_source_key/pair_destination_keys join — not catchable: `_validate_composition_arrays` (`:646`) and
   `_join_composition_source` (`:977`, keys at `:1018/1025`) are referenced by name in two test files, never with
   real composition-vs-source data; the source adapter's completeness test omits both keys from its subset.

## End-to-end integration test

None exists. `verify_v023_final_gate(` is called only from each verifier copy's `__main__` block and from the
domain-repair scripts run manually against the real run root. No test combines the real source writer and the real
composition writer with the verifier. INFERENCE: this absence is why the defects surfaced one per ~40-minute server
run — each sits behind the previous one in the same call path (`_load_npz` domain → sibling import →
`_validate_pair_arrays` → `_join_composition_source`).

## Recommendations

- One producer-to-consumer test: run the real `v023_lcsrs_source_adapter.py` and `v023_lcsrs_composition_adapter.py`
  write paths on a tiny synthetic world, feed the resulting NPZ+JSON into `verify_v023_final_gate` from the frozen
  file. This single path would have hit all four defects in one run.
- Pin `test_w201`'s verifier path by byte hash to the frozen R7 copy so predecessor drift cannot decouple the tests.
- Derive the "expected" side of every cross-module assertion from the other module's real output (e.g.
  `set(source writer emitted keys) == set(names _join_composition_source reads)`), never from hand-typed lists or the
  verifier's own constants.
