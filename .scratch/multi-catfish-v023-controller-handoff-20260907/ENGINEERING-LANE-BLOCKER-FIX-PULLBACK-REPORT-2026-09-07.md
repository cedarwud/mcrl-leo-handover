# Engineering-Lane Blocker-Fix Pullback Report — 2026-09-07

## 1. Server workspace diff scope
`git diff --stat` / `status --porcelain` on `mcrl-v023-codex-ws-blockers-20260907` confirm exactly 9 files changed, only under `provider-factory-v3/` (3 files) and `two-route-source-training-runner/` (6 files). Nothing else touched. No STOP triggered.

## 2. Pullback
rsync'd both directories into the local repo. Local `diff --stat` matches the server's byte-for-byte: 9 files, 933 insertions / 312 deletions.

## 3. Local pytest (5 packages, exact command)
- `c1c2-provider-factory-v3`: **11/11 PASS**
- `two-route-source-training-runner`: **7/7 PASS**
- `c1c2-successor-physical-evaluation`: **24/24 PASS**
- `two-route-rehearsal`: 4/6, **2 FAIL**
- `engineering-lane`: 7/10, **3 FAIL**

Both packages codex fixed pass fully. All 5 failures are in *other* packages, and are ripple effects of the two hardened contracts codex added, not defects in the fixed code:
- `rehearsal_two_route_training_real_shards.py:284` → `TypeError: V023TwoRouteOrchestratorConfig.__init__() missing 1 required positional argument: 'model_config_sha256'` (2 tests).
- `engineering-lane/dryrun_support.py:80` → `ValueError: train_seed must be exactly 2927175120652069826` (per-arm seed increment now rejected by the new strict check); the two `test_stage_bc_*` failures are a subprocess returning exit 2 instead of expected 3 for the same underlying reason.

Not fixed (per instructions).

## 4. Shadow-checkout verification
Pushed the two fixed packages + `r6-fit-binding-fix` to `mcrl-v023-successor-shadow-20260907/.scratch/`. 

**Correction**: the specified interpreter `/home/u24/papers/mcrl-leo-handover/.venv/bin/python` does not exist on `sat` (verified). Substituted `/home/sat/mcrl-leo-handover/.venv/bin/python` — the venv already referenced by ~19 other automation scripts across this shadow checkout, confirmed executable with torch 2.13.0+cu130 / pytest 9.1.1. Ran with `oom_score_adj=1000` set first and `TMPDIR` created.

Result: **18/18 PASS** (11 + 7), exit 0.

## 5. Codex final message + blocker locations
`codex-sol-blocker-fixes-final.md`: reports all 8 fixes done, local run blocked only by the missing `r6-fit-binding-fix` closure file (now resolved). All 9 changed-file SHA-256 hashes in that message were cross-checked and **match exactly** against the local files.

| # | Marker | Location |
|---|---|---|
| 01 | model-config sha `9eafcd18…` | `v023_c1c2_provider_factory_v3.py:65,284`; `ee_axis_two_route_model.py:50,63` |
| 02 | train seed `2927175120652069826` | `ee_axis_two_route_model.py:49,174` (`FORMAL_TRAIN_SEED`); `v023_c1c2_provider_factory_v3.py:64,282-283` (`TRAIN_SEED`) |
| 03 | learner-closure list | `v023_c1c2_provider_factory_v3.py:92-119` (`REQUIRED_LEARNER_RUNTIME_MODULES`), enforced ~604-632 |
| 04 | route check `["C1","C2"]` | `v023_c1c2_provider_factory_v3.py:61,825` (`next_batch` guard); test at `test_...:454` |
| 05 | `_require_root` before advance | defined `v023_two_route_source_training_runner.py:447`; guards `run_to_epoch` at `:543` |
| 06 | resume validates exports vs checkpoints | `_validate_exports` def `:728`, called from `resume_from_checkpoint` `:872` |
| 07 | epoch-100 exact-restore before completion | `EPOCH_100_INTEGRITY_DECISION` `:77`; `_verify_epoch_100_integrity` def `:811`, called `:558` |
| 08 | producer-derived fixtures in runner tests | `test_v023_two_route_source_training_runner.py:26` (`import ... as PRODUCER_FIXTURE`), used `:56-69` |

All 8 located; none UNVERIFIED.
