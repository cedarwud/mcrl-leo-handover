# Engineering-lane verification — stage-A launch bundle fix passes 2+3 (2026-09-07)

Branch `wip/multi-catfish-v023-20260907`. No code edited by hand.

## 1. Fix pass 2 claims (all FIXED, R1 out of scope)

| ID | Anchor cited |
|---|---|
| 03 | factory.py:425, :743 — transitive import closure + exact manifest compare |
| 04 | factory.py:506 — contract/declaration/predecessor/PREREG-TLE authenticated from disk; test:546 |
| 08 | test_factory.py:107 — fixtures derived from producer records/import graph |
| L1 | build_…_manifest.py:28 `closure_groups` — each path in exactly one group |
| L2 | common.py:337 typed digest validation + semantic-only token scan; test:52 |
| L3 | common.py:310 fail-closed placeholder disposition; binder.py:249 |
| L4 | preflight.py:272; formal wrapper:140; verifier.py:399 |
| L5 | verifier.py:194/:227/:355; tests :245/:264 |
| L6 | common.py:232; test:81 |
| L7 | preflight.py:88; sync script:127 |

Deferred placeholders reported (all reason `DEFERRED_UNTIL_STAGEC_BUNDLE_LANDS`): contract
`evaluation_runner_manifest_sha256`; §9 `stage_c.runner_bundle_manifest_sha256`;
§9 `stage_c.verifier_bundle_manifest_sha256`. All three confirmed present in
`bind_v023_c1c2_successor_freeze.py:290-293` and `:366-373`.

## 2. Test suite (56 collected: launch 15, factory-v3 12, runner 10, rehearsal 8, eng-lane 11)

- **Run 1 (fix pass 3 mid-edit)** — 53 passed, 3 failed, rc=1. All three in files fix pass 3
  owned: `test_binder_write_then_check_is_idempotent_on_clean_tree` (binder `--check`
  returned 3, "frozen file drifted"); `test_preflight_rejects_factory_identity_field_set_drift`
  (`SuccessorLaunchError: provider identity names a closed split` at
  `preflight_v023_c1c2_successor.py:84`); `test_real_factory_identity_is_accepted_with_its_declared_field_set`
  (`AttributeError: module 'v023_c1c2_provider_factory_v3' has no attribute 'PROVIDER_IDENTITY_FIELDS'`).
- **Run 2 (after `CODEX_EXIT=0`, 16:34 UTC)** — **56 passed, rc=0.**
- **Run 3 (after manifest `--write`)** — **56 passed, rc=0.**

## 3. Bundle entrypoints

- Manifest `--check` (pre) → rc=3, `frozen file drifted` (bundle changed under fix pass 3).
- Manifest `--write` → rc=0, `SUCCESSOR_LAUNCH_MANIFEST_WRITTEN sha256=8b020cd25c8c4068b6d9e40eb01f2bb866d10031e4066e75f2386b60a1f8676e`.
- Manifest `--check` → rc=0, `SUCCESSOR_LAUNCH_MANIFEST_CURRENT sha256=8b020cd2…676e`.
- `sync_launch_…_server.sh --dry-run` → rc=2, exactly:
  `SUCCESSOR_EXECUTION_BINDINGS_FAIL: required r8 target root is absent: /home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8`
  `SUCCESSOR_LAUNCH_REFUSED: execution bindings are not current`
  Binder `--check` run directly gives rc=3 on that same single cause — the refusal is solely the absent r8 root.
- `bind_…_freeze.py --help` → rc=0, mutually exclusive `--write | --check | --verify-learner-manifest-only`.

## 4. Static spot-checks — all four PASS

- **L2** `successor_launch_common.py:129` `digest()` enforces `^[0-9a-f]{64}$`; `:337`
  `reject_forbidden_config` routes any `*sha256`/`*digest*` field to `digest()` (never token-scanned)
  and applies the token regex only to semantic keys (`path|root|route|split|arm|module|source`) — matching the audit's stated remediation.
- **L5** `verify_v023_c1c2_successor.py:191-192` raises unless reconstruction is required; `:198-199`
  rejects `REHEARSAL-NONFORMAL` roots; `:226-227` rejects `formal:false` provenance; `:109`/`:248`
  require `formal is True` on ledger and preflight. Hidden `--no-reconstruct` (`:474`) fail-closes at `:191`.
- **L6** `common.py:232-249` requires exactly 246 byte-sorted unique real (non-symlink) paths;
  `:252-262` demands two-way set equality; `test_…_launch.py:81` asserts every closure path is covered exactly once.
- **L3** The contract has 8 machine-readable `<<BIND_AT_FREEZE:…>>` keys: 7 RESOLVED by the binder,
  1 (`evaluation_runner_manifest_sha256`) explicitly DEFERRED with reason. **None is neither.**
  A 9th literal at contract line 4 uses an ellipsis and is prose, not a binding.

## 5. Commit

Green after fix pass 3 → committed **`1e6310e8c45d012809f4c5cda6760d36092f68c8`** (15 files, +1293/−162).

## Caveats

1. Current manifest SHA (`8b020cd2…`) differs from fix pass 3's reported `1bbe34cb…` because a later
   concurrent codex task edited closure path 55
   (`.scratch/multi-catfish-v023-c3-contingency-f1/test_run_v023_c3_contingency_f1.py`).
   I waited for its `CODEX_EXIT=0` before regenerating; no codex task in this repo was running at write time.
2. The committed manifest binds files outside the commit scope (`…-physical-evaluation`,
   `…-c3-contingency-f1`) that remain uncommitted in the working tree. It will drift again if the
   Stage-C lane touches them, and must be regenerated before freeze.
