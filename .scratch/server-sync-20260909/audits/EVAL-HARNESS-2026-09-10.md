**`SEALED` is bit-identical — proved structurally, on the fixture grid with a positive control, and end-to-end by reproducing all 20 archived anchors and the pooled `+6.3590%` exactly — and a full 20-anchor panel now costs 1141 s the first time a variant is run and 0.49 s (2.2 s wall including interpreter start) every time after.**

# Standing evaluation harness — V0.25 twenty-anchor panel

`DIAGNOSTIC_NOT_CLAIM`. This document describes a measurement instrument. It contains no scientific claim, no efficacy measurement and no training run. No constant, threshold, sign, seed, horizon, price, service guard or acceptance rule in the sealed physics was changed, and no sealed artefact or frozen manifest was modified.

Workspace `/home/sat/mcrl-v025-harness-ws`, commit `1dfc6e07a10d045d5d4ba598d0368038e4787804`. All runs used `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`, one process. Runs completed 2026-09-09T18:0x–18:5xZ. `/home/sat/mcrl-leo-handover` and every sibling `mcrl-v025-*-ws` workspace were read only.

---

## 0. What was built, in one paragraph

`harness/` is 2 010 lines of Python across eleven small modules plus two variant files, driven by one entry point `bin/harness`. It does not restate any physics. The anchor evaluation — the base configuration, the iterated unilateral selector with its complete-neighbourhood certificate, the bounded coalition catalogue, the service guard, the exact `F = B − η_ref·E` objective, the 48-boundary committed endpoint and the pooled summary — is imported verbatim from the archived ladder runner, vendored byte-identically into `sealed/`. What the harness adds around it is: a named anchor panel, a named physics-variant seam, two content-addressed caches, a receipt writer, a declared screen ladder, and a query layer over stored receipts.

| Layer | File | Lines |
|---|---|---:|
| Sealed tree loader and manifest verifier | `harness/sealed.py` | 131 |
| Variant registry (auto-discovering) | `harness/variants/__init__.py` | 67 |
| Variant `SEALED` | `harness/variants/v_sealed.py` | 22 |
| Variant `MARGIN_Q` | `harness/variants/v_margin_q.py` | 26 |
| Anchor panels | `harness/panel.py` | 62 |
| World and anchor caches | `harness/cache.py` | 148 |
| Panel run and receipt | `harness/runner.py` | 246 |
| Pooled figures, gains, tables | `harness/report.py` | 154 |
| Bit-identity proof | `harness/proof.py` | 260 |
| Cache variant-independence audit | `harness/cacheaudit.py` | 72 |
| Profiler | `harness/profile.py` | 138 |
| Query layer | `harness/query.py` | 94 |
| Command line | `harness/cli.py` | 572 |
| Harness self-tests | `tests/harness/test_harness.py` | 137 |

---

## 1. The sealed tree, and why it had to be vendored

The receipts to be reproduced are `original-result.json` and `margin-result.json` from `/home/sat/mcrl-v025-ladder-ws/.scratch/ladder-floor-20260910/`. They record `probe_source_sha256 = f4122d67…4c76c`.

This workspace's own `src/mcrl` is **a different sealed version**. Its probe hashes `d430baf3…4786196`, and its `src/mcrl/physics_v025/batch.py` is 506 lines against the ladder's 602 and has no `fading_quantile_alpha` parameter at all. Nine physics modules differ. Running the archived panel against this workspace's `src/` would have failed outright, and if it had not failed it would have produced numbers from different physics under the same name.

So the exact sealed tree that produced the archive was copied into `sealed/`, laid out to mirror the ladder workspace so the archived runner's own relative paths resolve unchanged:

```
sealed/src/mcrl/…                                                        (the sealed physics)
sealed/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py
sealed/.scratch/ladder-floor-20260910/oracle_runner.py                   (the archived eval loop)
sealed/.scratch/ladder-floor-20260910/margin_batch.py                    (MARGIN_Q's one changed line)
sealed/fixtures/test_stage4d_gate.py                                     (the ladder's KAT fixture)
sealed/MANIFEST.sha256                                                   (179 files)
```

`harness/sealed.py` re-hashes all 179 files on every load and refuses to run on any drift. The probe digest is additionally checked against the constant recorded in the archived receipts.

```
sealed_manifest_sha256 = d5e94654510225aaf6ca7f8422ecd12ba64e8f3b8690c55a55d791063db8b916
probe_source_sha256    = f4122d6784cb56de7743c55d51dc80a6c968ccea601d637cd1b41a8b5604c76c   (matches archive)
```

`sealed/` is written once and never written again. This workspace's `src/`, `archive/`, `docs/` and `tests/physics_v025/` are untouched. The only tracked file this work modified is `.gitignore`, which gained one line (`.harness-cache/`); everything else added is new and untracked: `harness/`, `bin/`, `sealed/`, `receipts/`, `logs/`, `ladder-archive/`, `tests/harness/`, `run-all.sh` and this report.

---

## 2. H1 — one command, one panel, one table

```
bin/harness run --variant SEALED --panel FULL20 --arms UNILATERAL,ORACLE_SET --out receipts/x.json
```

Command line as run:

```console
$ PYTHONPATH=src nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python -m harness.cli \
    run --variant SEALED --panel FULL20 --arms UNILATERAL,ORACLE_SET --quiet \
    --out receipts/sealed-full20-two-arms.json

arm                               bits                joules            ee_bit_per_j    served
UNILATERAL        1660779577104.984619       58332.519445156      28470904.272640795      1939
ORACLE_SET        1694404970756.871826       55955.362097867      30281369.063313689      1957

pooled relative EE gain                            ratio         percent
UNILATERAL_over_ORACLE_SET               -0.059788075859        -5.9788%
ORACLE_SET_over_UNILATERAL                0.063589999578         6.3590%

anchor_id                                  UNILATERAL.ee    served         ORACLE_SET.ee    served
V025_PROBE_R2/world/1:step/0             31358500.509405        98       32863112.026049        99
V025_PROBE_R2/world/1:step/1             35289578.212381        99       37285910.241600        99
…  (20 rows)
V025_PROBE_R2/world/4:step/4             33250832.238217        97       34010420.256520        97

wall_seconds=0.452  cache={'world_hits': 4, 'anchor_hits': 20, …}
```

The receipt keeps the archived schema `mcrl-v025-perfect-knowledge-oracle-ceiling-v1` — same `anchors`/`worlds`/`summary` shape, same `committed[ARM]` keys `bits`, `joules`, `ee_bit_per_j`, `served_count` — and adds, inside the file: `receipt_sha256` (SHA-256 over the canonical unsigned JSON), `variant`, `variant_source_sha256`, `panel`, `sealed_manifest_sha256`, `probe_source_sha256`, `reported_arms`, and the per-world `world_sha256` digests. `formulation` is retained with its archived values (`original`, `margin`) so old and new receipts remain comparable.

**Arms are a reporting selection, not a compute selection.** `--arms` restricts the printed table and the pooled gains. All three arms are always computed, because `ORACLE_SET` is defined relative to `UNILATERAL` and both are guarded by the `BASELINE` served count. The receipt says this in `arms_note`.

### Reproducing the archived `+6.3590%` in one command

```console
$ PYTHONPATH=src nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python -m harness.cli reproduce

{
  "archive": "/home/sat/mcrl-v025-harness-ws/ladder-archive/original-result.json",
  "archive_receipt_sha256": "327e2ff15b5acb185f656285ff9ab02a49b615b4f4c676f026498d9c2fe9b5d4",
  "archived_oracle_over_unilateral": 0.06358999957766232,
  "archived_percent": "+6.3590%",
  "produced_oracle_over_unilateral": 0.06358999957766232,
  "produced_percent": "+6.3590%",
  "exact_float_match_to_archive": true,
  "pooled_matches_archive_exactly": true,
  "per_anchor": { "anchor_count": 20, "scalar_comparisons": 300, "exact_match": true, "mismatches": [] },
  "verdict": "REPRODUCED",
  "wall_seconds": 0.4697421570017468
}
```

The match is exact at the binary64 level, not to four decimal places: `produced == archived` as Python floats. The comparison covers all 20 anchors × 3 arms × 5 scalars (`bits`, `joules`, `ee_bit_per_j`, `served_count`, `configuration_id`) plus the full assignment vector, and separately the four pooled quantities per arm. The first, uncached execution of this same command is in `logs/02-reproduce-cold.log` and took 1141.18 s.

The same holds for the second archived receipt. `receipts/margin-q-full20.json` against `ladder-archive/margin-result.json`: pooled block identical, per-anchor scalar mismatches **0**, `oracle_set_over_unilateral_relative` `0.005447658598398464` on both sides.

---

## 3. H2 — the named physics-variant seam, and the bit-identity proof

A variant is one named replacement for exactly one object: `probe.evaluate_ar_tdm_catalogue`, the dense catalogue evaluator. Nothing else may differ between variants — not the panel, the anchors, the selector, the guard, the objective or the committed endpoint.

```console
$ bin/harness variants
MARGIN_Q
  source: harness.variants.v_margin_q
  Provision against Gamma / q, where q is the same alpha-fading product quantile the committed
  mode selection is judged at (margin_dB = -10 log10 q). All other equations are sealed.

SEALED (default)
  source: harness.variants.v_sealed
  The sealed dense catalogue evaluator, unmodified. Provisioning targets the sealed rate-target
  SINR threshold Gamma exactly as published.
```

`MARGIN_Q` is one line of difference from the sealed evaluator:

```diff
-                targets = gamma[np.minimum(occupancy, users)]
+                targets = gamma[np.minimum(occupancy, users)] / quantile
```

`quantile` is `fading_product_quantile_array(elevations, α)` at the same `α = 0.10` the committed mode selection is later judged at, so the added margin is exactly `−10 log₁₀ q` dB.

**Adding a third variant is one file.** Drop `harness/variants/v_<name>.py` defining `NAME`, `DESCRIPTION` and `build(sealed)`. Discovery is `pkgutil.iter_modules`; no registry list, no CLI change, no runner change, no test change. Its module bytes are hashed into `Variant.source_sha256` automatically and become part of its cache key.

### The proof

```console
$ PYTHONPATH=src nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python -m harness.cli \
    verify-sealed --out receipts/sealed-bit-identity.json

{
  "verdict": "PASS",
  "sealed_manifest_sha256": "d5e94654510225aaf6ca7f8422ecd12ba64e8f3b8690c55a55d791063db8b916",
  "probe_source_sha256": "f4122d6784cb56de7743c55d51dc80a6c968ccea601d637cd1b41a8b5604c76c",
  "structural": {
    "sealed_variant_is_module_attribute": true,
    "sealed_variant_is_probe_attribute": true,
    "independent_reference_is_a_distinct_object": true,
    "probe_module_file": ".../sealed/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py",
    "sealed_batch_module_file": "mcrl.physics_v025.batch"
  },
  "sealed_fixture_cases_alpha_none": 16,
  "sealed_all_fields_equal_alpha_none": true,
  "sealed_all_fields_equal_alpha_0_10": true,
  "margin_q_all_fields_equal_alpha_none": true,
  "teeth_positive_control": {
    "margin_q_alpha_0_10_differs": true,
    "max_rf_power_w_differs": true,
    "transmitted_mode_counts_differ": true,
    "differing_fields": ["attained","bits","cap_hits","certificate_iterations","decoding_time_s",
      "joules","max_rf_power_w","mean_acm_se_bit_s_hz","min_decoding_margin_db","mode_counts",
      "pa_j","realised_decode_failures","realised_decode_successes","residual_w",
      "transmitted_mode_counts"]
  },
  "route_ok": true
}
```

Four independent legs, all required:

1. **Structural.** `SEALED` resolves to the very object the sealed probe imported (`is` identity against both `mcrl.physics_v025.batch.evaluate_ar_tdm_catalogue` and the pristine probe attribute captured before any variant can be installed). Installing `SEALED` is therefore a no-op on the seam. `install_variant` raises if this ever stops holding, so a mis-registered `SEALED` cannot run at all.

2. **Fixture parity, against an independently re-executed copy.** Comparing a function against itself proves nothing, so the reference side is a *second* execution of `sealed/src/mcrl/physics_v025/batch.py`, loaded from disk under a different module name. Over the ladder's grid — 4 `(ρ, isolated target power)` cases × {`nominal`, `realised`} × {1 boundary, 48 boundaries} = 16 cases, at both `α = None` and `α = 0.10` — **all 23 fields of `BatchARResult` are equal in every case**, with `bits`, `transmissions`, `mode_counts` and `max_rf_power_w` asserted and reported by name. `MARGIN_Q` passes the same 16 cases at `α = None`, where `q = 1` makes its one changed line an identity.

3. **Teeth.** The same assertion is required to **fail** for `MARGIN_Q` at `α = 0.10`, and it does, on 15 of 23 fields including `max_rf_power_w` and `transmitted_mode_counts`. A parity check that cannot fail is not evidence; this one demonstrably can.

4. **Route.** Both real evaluation routes are observed reaching the installed seam with the sealed arguments: the selector at `field="realised"`, `boundary_indices=(0,)`, `α=0.10`, and the committed endpoint at `field="realised"`, 48 boundaries, `α=0.10`.

And the strongest leg of all, which the fixture grid cannot give: **the 20-anchor `SEALED` panel run on the real world tapes reproduces the archived receipt exactly** — 300 scalar comparisons, all assignment vectors, all four pooled quantities per arm, and the headline pooled ratio, bit for bit (§2).

---

## 4. H3 — making the second and later runs cheap

### Where the time actually goes

```console
$ bin/harness profile --variant SEALED --anchors 1 --no-cache --out receipts/profile-sealed.json
```

One anchor, world 1 step 0, `cProfile` over the real loop:

| | value |
|---|---:|
| Cold world-tape build (1 world, 5 steps) | 25.66 s |
| One anchor, end to end | 48.07 s |
| — of which inside `_evaluate_ar_tdm_catalogue_core` (cumulative) | 45.42 s (**94.5 %**) |
| — `fading_product_quantile_array`, 392 calls (cumulative) | 0.855 s (1.8 %) |
| — `resolve_configuration` seam overhead itself | 0.025 s |
| — `_legal_options` | 0.009 s |
| Selection boundary evaluations in that anchor | 10 324 |
| Committed boundary evaluations in that anchor | 144 |

Top single line by self time is `batch.py:77(_evaluate_ar_tdm_catalogue_core)` at 36.85 s of 48.07 s; everything else is numpy reduction machinery called from inside it.

### What is cached

Two content-addressed caches under `.harness-cache/`, each keyed by a SHA-256 over a declared input record.

**World tapes** — key `{sealed_manifest_sha256, domain, steps, start_time_s, provider}`. A tape is the geometry, the gains and the per-boundary link inputs: elevations, distances, masks, nominal and realised direct gains, the cross-gain tensor, the identity table. Deliberately **not** keyed by variant.

**Finished anchor rows** — key `{sealed_manifest_sha256, variant, variant_source_sha256, world_sha256, step_index}`. This is variant-dependent by construction and keyed as such, including the variant module's own source bytes, so editing a variant file without renaming it invalidates its rows instead of serving them stale.

### Why the world cache may omit the variant

Structurally: a tape is built by `probe.build_world_tape` from the provider alone, before any evaluator object exists in the call graph, and a variant only ever replaces `probe.evaluate_ar_tdm_catalogue`. Empirically as well —

```console
$ bin/harness cache-audit --world 1 --out receipts/world-cache-variant-independence.json
{
  "check": "world-tape-variant-independence-v1",
  "verdict": "PASS",
  "world_digest_identical_across_variants": true,
  "tape_contents_identical_across_variants": true,
  "rows": [
    {"variant": "MARGIN_Q", "installed_evaluator": "harness_variant_margin_q",
     "world_sha256": "b6d15d06…5eb971f",
     "tape_content_sha256": "0a04ae93e7b09bf77393a33010cfd08147ab155b1e69ce6bed9b771501bcff94"},
    {"variant": "SEALED",   "installed_evaluator": "mcrl.physics_v025.batch",
     "world_sha256": "b6d15d06…5eb971f",
     "tape_content_sha256": "0a04ae93e7b09bf77393a33010cfd08147ab155b1e69ce6bed9b771501bcff94"}
  ]
}
```

The tape is rebuilt from scratch with each variant installed and compared both on its own digest and on a SHA-256 of its complete serialised contents. Identical.

### Measured before and after

All on this machine, one process, `nice -n 15`. Cold world and anchor costs are carried inside every receipt (`worlds[].construction_wall_seconds`, `anchors[].wall_seconds`), so the "before" column is recoverable from a receipt the harness wrote even after the cache is warm.

| Run | Worlds | Anchors | Measured wall |
|---|---|---|---:|
| `SEALED` FULL20, caches empty | 4 built, 101.86 s | 20 solved, 1 038.28 s | **1 141.18 s** (19:02.6 incl. start) |
| `SEALED` FULL20, warm | 4 loaded, 0.45 s | 20 read | **0.49 s** (2.2 s incl. start) |
| `MARGIN_Q` FULL20, worlds warm, anchors cold | 4 loaded, 0.45 s | 20 solved, 711.43 s | **712.83 s** (11:54.5 incl. start) |
| `MARGIN_Q` FULL20, warm | 4 loaded, 0.43 s | 20 read | **0.47 s** |
| `SEALED` SCREEN2, cache disabled entirely | 2 built, 67.97 s | 2 solved, 94.40 s | 162.47 s |

Read that as three different questions:

* *Ask the same variant again* — 1 141.18 s → **0.49 s**, a factor of 2 300. Anchors and summary are bit-identical to the cold run (verified: `anchors` and `summary` compare equal element for element).
* *Change only the provisioning rule* — `MARGIN_Q` would have cost 101.86 + 711.43 = 813.3 s from cold. It cost 712.83 s. The 101.9 s the provisioning rule cannot affect was not spent again; the 711.4 s it does affect was. That is a 12.5 % saving, and it is the honest ceiling for a variant change.
* *Ask a question that does not need a new run at all* — the query layer (§6) answers in well under a second.

**The caches change no number.** `receipts/sealed-screen2-nocache.json` was produced with the cache disabled entirely, from freshly built tapes, and its two anchor rows are bit-identical to the corresponding rows of the cached FULL20 receipt (`screen_rows_bit_identical_to_full_rows: true` over `bits`, `joules`, `served_count` and `configuration_id`).

### What I expected to be cacheable and is not

**The 94.5 % inside `_evaluate_ar_tdm_catalogue_core` cannot be cached, and no amount of engineering will change that.** It is precisely the quantity the provisioning rule alters. Worse than that, the variant changes the selector's *path*: `MARGIN_Q` reaches different unilateral optima, so it does not even visit the same set of configurations. There is no shared sub-result between `SEALED` and `MARGIN_Q` at the configuration level to memoise.

**The per-boundary fading product quantile is the one thing I expected to cache and did not.** It is genuinely variant-independent — it depends only on the tape's elevations and on `α` — and `margin_batch.py`'s own comment says recomputing it "dominated the real four-worker gate". On this panel it does not. It measures 0.855 s cumulative out of a 48.07 s anchor, 1.8 %, because the sealed `channel` module already memoises it internally in `_cached_fading_product_quantile` (0.788 s of the 0.855 s is the cached lookup path). Adding a harness-level cache in front of it would mean reaching inside sealed physics for a saving smaller than run-to-run noise. I did not do it.

**Cost of the cache.** 481 MB of disk for four world tapes (≈120 MB each) plus 1.5 MB for 40 anchor rows, to save 101.9 s per run. That is a poor ratio in absolute terms and a good one if the panel is run more than a handful of times. There is no eviction policy; deleting `.harness-cache/` is safe and only costs time.

---

## 5. H4 — the declared screen ladder

### The rule, declared before use

The rule is committed as data in `harness/cli.py:PROMOTION_RULE`, printed by `bin/harness rule`, and evaluated mechanically by `bin/harness screen`, which writes its own receipt. It was written before either screen was run.

```json
{
  "id": "screen-promotion-rule-v1",
  "declared": "2026-09-09",
  "screen_panel": "SCREEN2",
  "full_panel": "FULL20",
  "statement": "A variant is promoted from SCREEN2 to FULL20 if and only if all four conditions below hold on the SCREEN2 receipt. The rule is a spend-authorisation rule for compute. It is not evidence about the variant, it does not rank variants, and a variant that fails it may still be run on FULL20 by explicit instruction, which must be recorded as an override in the promotion receipt.",
  "conditions": [
    "C1 the SEALED bit-identity proof passes at the same sealed manifest digest",
    "C2 both SCREEN2 anchors completed with no evaluation error",
    "C3 both SCREEN2 anchors have a defined ORACLE_SET-over-UNILATERAL gain, that is, UNILATERAL pooled EE is non-zero on the screen",
    "C4 the screen's two world digests equal the FULL20 world digests for worlds 1 and 2, so the screen rows are literal FULL20 rows"
  ],
  "explicitly_not_a_condition": [
    "the sign of any gain",
    "the magnitude of any gain",
    "agreement with any other variant",
    "whether the result looks favourable"
  ]
}
```

**No condition reads any outcome.** The rule authorises spending compute; it says nothing about whether a variant is good. A harness self-test asserts that the conditions contain no outcome language, so the rule cannot be quietly rewritten into a filter on results.

The screen itself: `SCREEN2` is anchors `(world 1, step 0)` and `(world 2, step 0)`, with world tapes built at the **same 5 steps** as `FULL20`. That makes a screen row a literal `FULL20` row rather than a different computation — verified, `screen_rows_are_subset_of_full: true` and `screen_rows_bit_identical_to_full_rows: true` for both variants. Cost: 162.47 s from completely cold, or two anchor solves (76.95 s for `SEALED`, 58.53 s for `MARGIN_Q`) once the world cache is warm, against 1 141 s and 813 s for the full panels.

Both variants were screened; both satisfy C1–C4; both `promote: true`.

### Measured agreement between screen and full panel

```console
$ bin/harness agreement --screen receipts/screen2-<v>.json --full receipts/<v>-full20.json
```

| Pooled gain | `SEALED` screen | `SEALED` full | Δ | sign agrees |
|---|---:|---:|---:|:--:|
| ORACLE_SET / UNILATERAL | +3.4902 % | +6.3590 % | −2.869 pp | yes |
| UNILATERAL / BASELINE | +782.99 % | +664.36 % | +118.6 pp | yes |
| ORACLE_SET / BASELINE | +813.81 % | +712.96 % | +100.9 pp | yes |

| Pooled gain | `MARGIN_Q` screen | `MARGIN_Q` full | Δ | sign agrees |
|---|---:|---:|---:|:--:|
| ORACLE_SET / UNILATERAL | **−2.3837 %** | **+0.5448 %** | −2.928 pp | **no** |
| UNILATERAL / BASELINE | +478.40 % | +442.14 % | +36.3 pp | yes |
| ORACLE_SET / BASELINE | +464.61 % | +445.10 % | +19.5 pp | yes |

Sign agreement across all six ordered arm pairs: **6 / 6 for `SEALED`, 4 / 6 for `MARGIN_Q`**. The two disagreements are the `ORACLE_SET`↔`UNILATERAL` pair, which flips sign between the screen and the full panel for `MARGIN_Q`.

That is the honest finding about this screen, and it is why the promotion rule deliberately does not condition on any outcome: on the one variant where the screen and the panel disagree, an outcome-conditioned screen would have made the wrong call. Two anchors out of twenty, on a quantity whose full-panel per-anchor distribution for `MARGIN_Q` contains 7 negative anchors out of 20 (§6), is not a predictor of the pooled sign. **n = 2 variants is not a calibration**; it is two data points, reported as such.

---

## 6. H5 — the query layer

Three questions, answered from stored receipts with no recomputation. These are the figures that were being derived by hand from receipt JSON on every previous question.

**Pooled figures for any stored run.**

```console
$ bin/harness show receipts/sealed-full20-warm.json
variant=SEALED  panel=FULL20  anchors=20
receipt_sha256=a358cda5cf7bbb361b24c2916168f9e7965461ce062cc2daab1fd5b1e62201fe

arm                               bits                joules            ee_bit_per_j    served
BASELINE           545927267996.825317      146564.590465533       3724823.753560106       826
UNILATERAL        1660779577104.984619       58332.519445156      28470904.272640795      1939
ORACLE_SET        1694404970756.871826       55955.362097867      30281369.063313689      1957

pooled relative EE gain                            ratio         percent
BASELINE_over_UNILATERAL                 -0.869170865882       -86.9171%
BASELINE_over_ORACLE_SET                 -0.876992888077       -87.6993%
UNILATERAL_over_BASELINE                  6.643557428839       664.3557%
UNILATERAL_over_ORACLE_SET               -0.059788075859        -5.9788%
ORACLE_SET_over_BASELINE                  7.129611242511       712.9611%
ORACLE_SET_over_UNILATERAL                0.063589999578         6.3590%

recomputed pooled matches stored summary: True
```

The last line is a standing self-check: the query layer recomputes the pooled block from the anchor rows with `math.fsum` in anchor order and compares it to the `summary` the run stored. If they ever disagree, the receipt is not trustworthy and the harness says so.

**Difference between any two runs.**

```console
$ bin/harness diff receipts/sealed-full20-warm.json receipts/margin-q-full20.json
{
  "anchor_sets_identical": true,
  "shared_anchor_count": 20,
  "delta_pooled_right_minus_left": {
    "BASELINE":   {"bits":  844658166521.90, "joules": 28724.19, "ee_bit_per_j":  4208287.70, "served_count_sum": 339},
    "UNILATERAL": {"bits": 1541361801792.37, "joules": 16120.60, "ee_bit_per_j": 14537925.33, "served_count_sum":  61},
    "ORACLE_SET": {"bits": 1507523858979.85, "joules": 18089.44, "ee_bit_per_j": 12961757.96, "served_count_sum":  43}
  },
  "delta_pooled_gains_right_minus_left": {
    "ORACLE_SET_over_UNILATERAL": -0.05814234097926385,
    "UNILATERAL_over_BASELINE":   -2.2221247620142313,
    "ORACLE_SET_over_BASELINE":   -2.6786444614028815,
    "…": "…"
  }
}
```

**Per-anchor distribution of any arm-over-arm gain, including the count of negative anchors.**

```console
$ bin/harness dist receipts/margin-q-full20.json --over ORACLE_SET --base UNILATERAL
variant=MARGIN_Q  panel=FULL20  gain=ORACLE_SET over UNILATERAL
defined=20 undefined=0 negative=7 zero=0 positive=13
  min    -0.043708314327
  q25    -0.002074484968
  median +0.002454546713
  q75    +0.007234092328
  max    +0.069427709762
  mean   +0.004912805426
  negative anchors:
    V025_PROBE_R2/world/1:step/0      -0.005227946869
    V025_PROBE_R2/world/1:step/2      -0.001811277013
    V025_PROBE_R2/world/2:step/0      -0.043708314327
    V025_PROBE_R2/world/2:step/1      -0.007137952537
    V025_PROBE_R2/world/2:step/3      -0.033906153684
    V025_PROBE_R2/world/2:step/4      -0.002864108836
    V025_PROBE_R2/world/4:step/3      -0.000577700697
  per anchor:
    …  (20 rows)
```

The same command on `SEALED` gives `defined=20 undefined=0 negative=0 zero=0 positive=20`, min `+0.008476845895`, median `+0.049948090197`, max `+0.174406143956`. `undefined` counts anchors where the reference arm's pooled EE is zero and the ratio does not exist; it is reported separately from `zero` so a missing value can never be silently read as a null result.

---

## 7. Receipts and logs

Every number in this document comes from one of these files, all written by the harness.

| File | `receipt_sha256` |
|---|---|
| `receipts/sealed-full20-warm.json` (SEALED FULL20) | `a358cda5cf7bbb361b24c2916168f9e7965461ce062cc2daab1fd5b1e62201fe` |
| `receipts/sealed-full20.json` (`reproduce`) | `7497c6d0587ca9df2eb2bd301e51bcc0bb790ef9195b8975db371b3fd8915e6f` |
| `receipts/sealed-full20-two-arms.json` | `f91286fd5a899267be637f522387cec8d30025d9d9b4bc3f393a01f2145f1b02` |
| `receipts/margin-q-full20.json` | `d0d39ae5b6b7aa7bc9e4849700747704d87b2be7438b40c33ff91e1552c2e1b1` |
| `receipts/sealed-screen2-nocache.json` (cache disabled) | `33e71bb96182dbcf55c0f89781fc719346efda943c0ec2b0de058a444ea04778` |
| `receipts/screen2-sealed.json` | `d9b1c97090ad7b7d92cda205e24721d62bba9fd69e7d670688dc03c17b3bcf1c` |
| `receipts/screen2-margin-q.json` | `5f8baf3cc2bf955412e9a35e5060a9ec352bb671b9342dbf9d09f852a671689d` |
| `receipts/sealed-bit-identity.json` (file SHA-256) | `21942b85b09874be77e4d5e49a0a04914ab44eefb59a0405097219f95e0d1d23` |
| `receipts/world-cache-variant-independence.json` (file SHA-256) | `b4381944ae6136fc55dedfbace8ac4e36eef9a66869f66b6016eaacca783d8e3` |
| `receipts/profile-sealed.json` (file SHA-256) | `6f246323d9bd569bc169ddafa6a3f0e4009984c9831fee6777d74930b31cebdb` |

Run logs, including `/usr/bin/time -v` for the timed runs, are in `logs/00-sequence.log` … `logs/05-screen2-nocache.log`. The archived comparison receipts are copied read-only to `ladder-archive/`.

`tests/harness/test_harness.py` — 11 tests, all passing, no physics evaluated:

```console
$ PYTHONPATH=src nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest tests/harness/test_harness.py -q
...........                                                              [100%]
```

---

## 8. What I did not build

* **No parallelism.** Selection runs in one process with `pool=None`, exactly as the archived runs did. `SELECTION_WORKERS` in the sealed runner is 1 and I did not touch it. A four-worker path would be the single largest remaining speed-up on a cold panel and is untouched.
* **No arm-level compute selection.** `--arms` filters reporting only. Computing `ORACLE_SET` without `UNILATERAL`, or either without `BASELINE`, is not possible under the sealed definitions and was not attempted.
* **No third variant.** The seam is built and the two required variants are registered. Nothing was screened, ranked or recommended.
* **No new panels.** Only `FULL20` and `SCREEN2`. There is no way to run an arbitrary subset of anchors by id; a new panel is a small edit to `harness/panel.py`, not a command-line option.
* **No statistical inference.** No confidence intervals, no hypothesis tests, no bootstrap. The `dist` command reports order statistics and counts, nothing more. Adding inference would make this an experiment rather than an instrument.
* **No cache management.** No eviction, no size cap, no locking. Two harness processes writing the same cache key concurrently is not guarded against. 481 MB for four tapes.
* **No verification of the sealed physics itself.** The harness proves that the bytes it runs are the bytes that produced the archive. It says nothing about whether those bytes are physically correct, and the `MARGIN_Q` results are a diagnostic of a provisioning rule, not a finding about it.
* **No repair of the pre-existing test baseline.** The 2026-09-09 harness audit in this workspace found 6 failing tests and one non-terminating Stage-C test in `tests/physics_v025` and `tests/stagec_v025`. I did not touch those suites and did not fix them. The harness deliberately does not import this workspace's `src/mcrl` at all, so those failures neither affect nor are affected by anything here — but they remain open.
* **No cross-machine claim.** All timings are from this machine, one process, `nice -n 15`. The archived ladder run of the same panel took 1 598.9 s on its machine; that is not a before/after comparison and is not presented as one.
* **No receipt immutability beyond SHA-256.** Receipts are plain files. Nothing signs them or prevents them being edited.
* **No migration of this workspace's `src/` to the sealed version.** They differ in nine physics modules. I vendored rather than replaced, deliberately, because replacing a sealed tree is exactly the thing this brief forbids. Anyone running the repo's own tests is still running the older physics; that divergence is real and unresolved.
