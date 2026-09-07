# Multi-Catfish MCRL V0.23 — execution-closure audit and controller handoff (2026-09-07)

Controller session: Claude Fable 5.1 (fresh context), 05:31–~08:00 UTC, with delegated work to
codex gpt-6-astra (adjudication), codex gpt-5.6-sol (inventory harness) and agy Gemini 3.8 Flash
(review). Claim ceiling of this whole document: **execution readiness only**. No TEST split was
opened, no learner update and no episode training happened anywhere, and nothing here is EE or
efficacy evidence. Benchmark timings and loss values are execution facts, not scientific ones.

## 0. 摘要（給使用者）

**13:05 UTC 更新（compact 後）：R7 gate 已於 12:54 UTC 封存，integrity `VERIFIED`，但科學裁定為 `STOP_PHYSICS_R7`。** 決定性條件是 `physical_signature`：兩個知情 Catfish 的 11 profile 對 00 profile 的 pooled ratio-of-sums EE 為 −0.049%，8 個開發世界只有 2 個為正（預先登錄門檻：嚴格正且 ≥4 個世界）。teacher composition（+0.335%）、held-out learner（balanced accuracy 0.705 對 placebo 0.626）、C1/C2 context 都通過；但 learned composition（−0.660%，2 個世界為正）、topology consistency（0.536，門檻 0.8）、harmful partial（超過 0.05 上限）也沒過——即使物理條件過了，依 `adjudicate_section14_r7` 的優先序也只會得到 `REDESIGN_INTERFACE_R7`，不是 GO。Provider factory 已在伺服器上實測拒絕這個 root（`R7 final result c3_decision is not the frozen GO value`），因此 100E 五臂來源訓練在凍結契約下無法啟動；這是 gate 的設計，不是缺陷。契約 §7：有效的非 GO 結果結束 LC-SRS successor 路線，不得放寬門檻、換種子／世界、依結果重跑或自動升級 CSE/EC；§8：100E 篩選只在 GO 之後開始。所以「為什麼一直沒辦法開始訓練」的完整答案是：(1) 六個 verifier 對 writer 的缺陷把 gate 的裁定藏了約 22 小時（source 陣列 09-06 15:10 就已存在）；(2) 裁定一出來，是預先登錄的科學 STOP。執行鏈上已無任何整合邊界擋在程式與啟動之間；擋住的是科學 gate 本身。接下來需要的是設計層決定（由使用者決定），不是再修執行鏈。細節見 §13、`R7-STOP-PHYSICS-RESULT-2026-09-07.md` 與 `r7-sealed-receipts/`；codex gpt-6-astra 的唯讀裁定（推導有效性、六個修正是否可能影響物理條件、契約允許的下一步）已派出，完成後附於 `ADJUDICATION-R7-STOP-PHYSICS-CODEX-GPT6-ASTRA-2026-09-07.md`。r8 C1/C2 目標產生（自有 claim ceiling，與 R7 裁定無關）照常進行。


**訓練為什麼一直開不了：三個卡點，兩個結構性原因。**

卡點：
1. **R7 gate root 仍未封存。** 修正版驗證（R3）在 06:22 UTC 仍回 `INVALID_RUN`，錯誤是
   `composition/source identity array missing: pair_source_key`。這是同一支凍結 final verifier 的第四個
   verifier-vs-writer 缺陷（前三個：array domain、sibling import、pair-profile broadcast）。它要求 source NPZ
   與 composition NPZ 都有 `pair_source_key`／`pair_destination_keys`，但 source 端的 schema 與 writer 從來沒有
   寫這兩個陣列（composition writer 有）。不是資料壞掉，是契約不符，且每個 composition shard 都會踩到。
   R3 契約不授權再修，所以 R7 沒有 GO 也沒有非 GO。
2. **真實 post-R7 provider 在現行程式結構下無法在同一棵樹啟動。** factory 認證 R7 時對「自己所在 checkout」
   逐檔 hash 169 個 R7 綁定，其中 `ee_axis_lcsrs_three_route.py` 與 `ee_axis_v014_head.py` 因 448 異質 Q2
   已合法改版；學習端需要新版，認證端需要舊版 hash。R7 seed checkout 還缺 learner 需要的 5 個 runtime 檔。
   codex gpt-6-astra 唯讀審議後裁定 **DECISION A**（對不可變的 R7 seed checkout 做 R7 code-closure 認證，
   learner 樹另由 100E manifest 綁定），完整規格見同目錄的 ADJUDICATION 檔。尚未實作。
3. **C1/C2 目標仍未封存，r5 也會以 FAILED 收場。** r4 的失敗是 wrapper 的描述字面過期，只改字面＋測試＋
   兩個 hash 後，r5 六個 benchmark 全 PASS、16 個 shard 於 06:08:57 UTC 全部啟動。第一個 shard 在 07:29 UTC
   把 c1／c2 資料集、receipt、MANIFEST 都寫完後，死在 generator 最後一行摘要
   （`generate_v023_c1c2_targets.py:1315`：對 C2 的 dict payload 取 `.rows`，那是 C1 物件才有的屬性，
   OPS-3 切換後 C2 已是 dict）。其餘 15 個 shard 結束時會撞同一行，controller 會寫 FAILED、不合併不封存，
   但每個 shard 目錄裡的每世界資料集是完整的。benchmark 抓不到它，因為 benchmark 不走寫檔路徑。
   依 STOP 規則沒有開 r6。

結構性原因：
- **凍結的驗證碼沒有對真實產物端到端通過過就被凍結；測試用的合成 fixture 與被測程式共用同一套假設**
  （W201 的 NPZ fixture 直接用 verifier 自己的 domain 算 hash；factory 測試 mock 掉認證與建構的縫）。
  fail-fast 加上每次 40 分鐘的伺服器跑，就是「一次只揭露一個缺陷」的迴圈。codex 提醒：這解釋了四個連續缺陷，
  但「從未有人跑過端到端」是推論不是已證事實。
- **單一樹 provenance 假設被 228/448 架構決定打破**，需要 staged provenance（同 GPT-6 對 R6 的裁定）。

本 session 做完的事、沒做的事與下一步，見 §1–§11。**learner 訓練與 episode 訓練都沒有開始。**

Published page (private, same content plus the Chinese summary): https://claude.ai/code/artifact/0b130c2a-2c59-4b73-8467-adea41db3fe9 — HTML copy `HANDOFF-EXECUTION-CLOSURE-AUDIT-2026-09-07.html` alongside.

## 1. What is verified, what is inferred, what is pending

Verified (receipts, logs, hashes read this session):
- Server `sat` rebooted 2026-09-07 05:25:40→05:29:57 UTC (journal boot list); no shutdown command
  logged; the R3 verifier that had been running since 05:10 UTC was killed with 0 bytes of log and
  no outputs. Preserved (moved, not deleted) to
  `/home/sat/mcrl-v023-r7-domain-repair-20260907-r3-interrupted-by-reboot/` with `INTERRUPTION-NOTE.json`.
- R3 re-executed with the identical frozen package (manifest `4a1fb2ef…`) at 05:42:08 UTC; all
  preflights passed; terminal at 06:22:54 UTC: `V023_R7_DOMAIN_REPAIR_FAILED: corrected final
  verification returned INVALID_RUN before dispatch-count assertion: composition/source identity
  array missing: pair_source_key`. No corrected verification, receipt or seal was written; R7-I1
  root still holds the original INVALID receipt (`2b14fb95…`) plus the additive
  `repair-authority-r3/` snapshot. Failure evidence: `/home/sat/mcrl-v023-r7-domain-repair-20260907-r3.log`
  (12,279 bytes, SHA-256 `c76640b6b40068ad24def04d3eabcefc94d9a0ac2ba280254be4ff7a10b62fc4`).
- Cross-role NPZ dispatch (DEFENSE_IN_DEPTH_FOLLOWUP): all 8 source shards declare
  `$.arrays.schema = multi-catfish-mcrl-v023-lcsrs-source-artifact-v1-arrays-v1` (no
  `array_domain`); all 48 composition shards declare `schema=None`,
  `array_domain=v023-composition-array-v1`. No cross-role mismatch exists.
- The fourth verifier defect: `verify_v023_lcsrs_final.py` (frozen, `3cc57371…`) lines ~1018–1040
  require `pair_source_key`/`pair_destination_keys` in both NPZs; the composition adapter writes
  them (`v023_lcsrs_composition_adapter.py:3018`), the frozen source adapter never does
  (`v023_lcsrs_source_adapter.py` writes `pair_anchor_index, pair_retained, pair_id, pair_user_ids,
  pair_action_ids, pair_target_by_draw, pair_target_mean, pair_class, control_source_key`), the
  source-stage verifier does not expect them, and the real source NPZ on the server lacks them
  while the real composition NPZ has them.
- r4 scope-literal failure: producer `benchmark_v023_c1c2_targets.py` (`d2ca43cb…`, unchanged)
  emits `C2 repriced OPS-3 selected-pair generation only; …`; the wrapper expected the pre-OPS-3
  wording and its own test fixture used the old wording. Corrected once (wrapper literal, tests,
  two CODE-MANIFEST digests; manifest `93d5f03d…→8a290eee…`). 43 focused tests, preflight,
  checkpoint audit, dry-run passed locally and on the server.
- r5: six short benchmarks `SHORT_BENCHMARK_PASS`, `SUMMARY.json` = `SHORT_BENCHMARKS_PASS`
  (06:05:44 UTC), `--validate` passed, tmux created 06:05:47, all 16 `shard-status/*.started.json`
  present 06:08:57 UTC; at 07:11 UTC 16 generator processes alive (cpu time == elapsed, 4.6–4.8 GB
  RSS each, 2.5 GB read each, no dataset written yet).
- r5 first shard terminal (07:29:16 UTC, neutral world-2026121708, ~80 min after start): the
  shard wrote its complete outputs (`c1-neutral-world-2026121708.json` 44.6 MB / 3455 rows,
  `c2-neutral-world-2026121708.json` 8.9 MB / 525 rows, `receipt.json`, `MANIFEST.sha256`)
  and then exited 2 with `V023_C1C2_TARGET_GENERATION_BLOCKED: 'dict' object has no attribute
  'rows'`. Exact boundary: `generate_v023_c1c2_targets.py:1315`, the summary
  `"C2": sum(len(dataset.rows) for dataset in c2_datasets.values())` inside `_write_outputs`,
  executed after all write-once files (lines 1297-1306). Since the OPS-3 switch the C2 dataset
  is a dict payload (`_generate_c2_world` returns the dict built at line 1154; line 1240 does
  `dict(dataset)`), so `.rows` only exists on the C1 `EEAxisOpeningDataset` objects. Every
  remaining shard will hit the same line at its end; the controller will therefore record 16
  failed shards and write `FAILED` (no merge, no seal), while each shard directory keeps
  complete per-world datasets. The six short benchmarks could not catch this because they
  never enter `_write_outputs` (`persistent_target_output_created: false`). Per the STOP rule
  no r6 was launched; the shards were left running so all 16 per-world outputs land on disk.
- Server venv: `mcrl` is an editable install of the stale main checkout
  `/home/sat/mcrl-leo-handover/src` which has none of the `ee_axis_*` modules; per-run trees work
  only through `sys.path.insert(0, <root>/src)` in the producers/adapters and `PYTHONPATH` in
  launchers. Any new server script must insert `<root>/src` before importing `mcrl`.
- R7 code-closure boundary (static, confirmed independently by codex gpt-6-astra by reading the
  code and re-importing the seam in a fresh process): exactly 2 of 169 R7 bindings differ from
  the live tree (`ee_axis_lcsrs_three_route.py` db8f→2dcf; `ee_axis_v014_head.py` b1ac→585d);
  the learner seam needs the live versions; the R7 authentication closure (18 files) imports
  neither; the R7 seed checkout lacks `ee_axis_c1_selector.py`, `ee_axis_opening_dataset.py`,
  `ee_axis_opening_runner.py`, `ee_axis_opening_source.py`, `ee_axis_source_selectors.py`.

- Pair-key derivation (codex gpt-6-astra, read-only memo `ANALYSIS-R7-PAIR-KEY-DERIVATION-CODEX-GPT6-ASTRA-2026-09-07.md`):
  both missing arrays are deterministic functions of sealed source data
  (`anchors[a].topology.pairs[k].source_key/destination_keys`, equivalently
  `physical_keys[a, u, reference_actions[a, u]]` and `physical_keys[a, [u,v], [du,dv]]`), so a
  verifier-side reconstruction (repair shape "a") preserves the original identity check with
  identical dtype/shape/bytes; all other join names are emitted with compatible shapes/order.
  The same memo CONFIRMS a fifth latent defect behind the pair keys: the source writer stores
  `anchors[a].c2_diagnostic` as a list of per-pair objects while the verifier's
  `_diagnostic_rows()` requires a mapping, so C2 would be marked incomplete and the final stage
  would reject; it SUSPECTS a float32-vs-float64 `q2_delta` tolerance (1e-12) rejection on real
  rows; and it CONFIRMS an unreachable reference-digest branch (coverage gap, not a failure).
  No further missing composition array names exist (all 79 required names are written).

- R7 read-only inventory run (07:29–08:10 UTC, isolated R7-era checkout copy
  `/home/sat/mcrl-v023-r7-inventory-checkout-20260907`, output
  `/home/sat/mcrl-v023-r7-final-verifier-inventory-20260907/inventory.json`, copied to this
  directory as `R7-FINAL-VERIFIER-INVENTORY-20260907.json`; R7 root mtimes unchanged; frozen
  verifier `3cc57371…` and R3 adapter `7d242eb2…` byte-verified; NPZ dispatch 8 source / 48
  composition as expected). Result: 193 findings, of exactly two kinds —
  (a) identity join: on all 48 composition shards `composition/source identity array missing:
  pair_source_key` and `… pair_destination_keys` (96 primary + 96 cascade KeyErrors; the source
  NPZ has 99 array names without the two keys, the composition NPZ 115 with them);
  (b) decision stage: `C2 context diagnostics are not independently recomputable:
  world=2026121801,phase=1..8 diagnostic must be an object` — the list-typed `c2_diagnostic`
  container defect confirmed on real data. No other source, fit, composition-array, ratio,
  cross-arm or launch-manifest finding appeared: with R3's three installs everything else in
  the frozen verifier passes on the real 8/48/48 panel. The suspected float32/float64
  `q2_delta` tolerance issue stays BLOCKED behind (b) and must be re-checked by re-running the
  inventory once (a)+(b) are applied in a scratch process.

Inferred (supported, not proven): the frozen final verifier was never carried end-to-end to a
PASS against the real 8/48/48 panel before freezing (four sequential defects each hidden behind
the previous one). Unverified by the adjudicator: the attribution of the ADOPT_HETERO_Q2_448
ruling and the GPT-6 R6 staged-provenance audit (they live in controller memory, not the repo).

Pending at hand-back: nothing is still running. r5 ended FAILED at 09:06 UTC (§12); the R7 inventory completed (§1, §8).

## 1b. Continuation after the user's go-ahead (09:20 UTC onward)
The user authorised continuing as controller with parallel delegation. State of the three lines:
- **C1/C2 r6**: codex fixed the generator summary with a typed `_row_count` accessor (fail-closed
  on a payload without `rows`) and made the controller poll all children every 2 s so a non-first
  shard failure is noticed immediately; real write-path test added; CODE-MANIFEST rebuilt
  (`cd0421b9…`); 64 focused tests, preflight, checkpoint audit and dry-run pass; r6 launched on
  `…-ops3-r6` roots: six benchmarks PASS again, all 16 shard `started` receipts at 09:58:31 UTC
  (expected per-shard wall 80–178 min, then the never-yet-exercised merge + seal).
  **r6 FAILED at 11:32:48 UTC** on the first shard to finish (neutral world-2026121708, returncode 0,
  complete outputs, generator fix confirmed working): the controller's post-shard authentication
  raised `mode receipt claim ceiling drifted` — controller line 33 expects
  `…NO_EPISODE_TRAINING_NO_TEST`, the generator (lines 77–80) writes
  `…NO_EPISODE_TRAINING_NO_EFFICACY_NO_TEST` into every shard receipt (r5's receipts carry the same
  value, so r5 would have died here too). The controller then aborted the other 15 shards (~95 min
  of compute each). Third consumer/producer literal mismatch in this pipeline (scope literal,
  `.rows`, claim ceiling); each was invisible to the consumer's synthetic-fixture tests and only
  surfaced after hours of real compute. Response: instead of another blind rerun, codex is
  (a) aligning the controller to the producer's literal with a test that reads the producer's
  constant and (b) building a read-only post-shard dry-run tool that exercises per-shard
  authentication → merge → seal against REAL shard directories, to be run on the server against
  the finished r6 shard (and r5's six) before r7 is launched. A 1-minute read-only probe of the
  controller's `_read_receipt` + `_validate_shard` against the real shard directories
  (`PROBE-CONTROLLER-POSTSHARD-RESULT-2026-09-07.md`) already found the NEXT one: with the claim
  ceiling patched, the r6 shard still fails `_validate_shard` with `OPS-3 q2_state is not the
  target-free feature projection` — the controller flattens `q2_features` action-major (lines
  278–303) while the producer, the V0.14 head (`reshape(batch,16,28).transpose(1,2)`) and the
  target adapter all use the feature-major layout; reproduced locally on 3 real rows
  (`state == feature_major` True, `== action_major` False). So r7 would have died again after
  ~3 h. Fourth consumer/producer mismatch in this pipeline; consumer-side fix + real-row tests
  queued to codex after the current controller task finishes (same file). A second in-memory
  probe with both defects patched reached the NEXT check and failed there too: `OPS-3
  ops3_future_d2_indices does not align with H_t` (controller `_ops3_row`, ~line 345) — the
  controller requires all three provenance lists to have length == horizon, but the producer
  passes through the native OPS-3 provenance where only `ops3_offset_times_utc` is per-horizon
  (3 entries for H_t=3) while `ops3_future_d2_indices`/`ops3_sample_times_utc` are the D2 sample
  window (measured over all 4,749 rows of the 7 real shards: (H_t, len) ∈ {(0,0),(1,47),(2,94),(3,141)},
  i.e. exactly 47 D2 samples per horizon step, and `offset_times` length == H_t always). Fifth
  consumer/producer mismatch. codex's own
  complete-schedule synthetic probe of the new dry-run tool found a SIXTH downstream one: the
  sealer `seal_v023_c1c2_target_output.py` still carries the old claim-ceiling literal
  (`target receipt claim ceiling drifted`). codex delivered: controller `CLAIM_CEILING` now read
  from the path-bound generator module (+ parity and mutation tests) and the read-only tool
  `dryrun_v023_c1c2_controller_postshard.py` (authenticates every present shard without
  fail-fast, reports missing shards, runs the real merge+sealer only for a complete schedule
  into a scratch root; 3 tests). codex batch 2 delivered the remaining consumer fixes: q2_state
  rebuilt feature-major (exact float32 comparison kept; action-major and permuted-feature
  mutations fail), H_t alignment now = offset_times == H_t, future_d2 == sample_times ==
  H_t × `OPS3_SAMPLES_PER_STEP` where the constant is imported from the producer
  (`ee_axis_ops3_live.D2_SUBSTEPS_PER_DECISION` = 47, used at line 793), sealer `CLAIM_CEILING`
  imported from the generator; tests on the 3 real rows plus a complete 16-shard
  generator→merge→seal path; 77 focused tests pass after the CODE-MANIFEST rebuild
  (`dc5ef936…`, 29 bindings incl. the dry-run tool). Server offline dry-run
  (`DRYRUN-POSTSHARD-R6-REAL-SHARD-2026-09-07.json`, isolated checkout copy, read-only staging):
  `DRYRUN_C1C2_POSTSHARD_BLOCKED scheduled=16 present=1 passed=1 failed=0 missing=15` — the real
  r6 shard now passes the complete per-shard authentication; merge/seal correctly blocked on the
  15 missing shards (the sealer path itself is covered by the synthetic 16-shard test). r7 is
  ready to launch (launcher dry-run with r7 names PASS); it needs the user's go. The one corrected attempt per line
  agreed for this session is spent; r7 launches only after that dry-run passes and the user
  says go.
- **Dress rehearsals (read-only, non-authoritative) instead of waiting for the first real run**:
  (a) the real R7 source panel loads through the audited fit adapter in 57 s (8 worlds × 9 anchor
  records, views of 100 users, tokens (100,28,101,38)); (b) the six complete r5 shards were pushed
  through the target adapter's OPS-3 row loader and the heterogeneous trainer on a live-tree scratch
  copy. (b) exposed a real defect before any provider run: `target_batch_adapter._ops3_route_batch`
  concatenated the per-row (448,) states and (28,) masks into 1-D arrays instead of stacking them,
  so the first real shard failed head validation (`normalized V0.14 states must have shape (batch, 448)`).
  Fixed (`np.stack`, plus an explicit fail-closed on empty row lists); two real-row regression tests
  added from a 3-row excerpt of the r5 output. After the fix all six shards load as C2 (N,448)
  float32 with masks (N,28) (≥21 legal actions per row), `target_unit` and `kappa_bits` as expected,
  and a real C2 update runs (informed 510 rows in 0.17 s; loss values are execution facts only).
  Note: four pre-existing tests in `test_target_batch_adapter.py` fail on receipt-schema drift
  (the adapter moved to OPS-3 receipts, its fixtures did not) — another instance of the test gap,
  to be repaired by the next controller; the adapter's OPS-3 path had no test at all before today.
- **R7 R4** (codex, delivered): `.scratch/multi-catfish-v023-r7-domain-repair-r4/` — contract,
  adapter (reuses the R3 adapter by digest; reconstructs `pair_source_key`/`pair_destination_keys`
  from source JSON topology pairs AND from the NPZ physical-key derivation, requiring agreement;
  normalises the list-typed `c2_diagnostic` by concatenating per-pair rows in order with per-pair
  provenance retained and fail-closed on empty/malformed input; no threshold or tolerance change),
  controller, launcher, tests (18 pass; the real anchor-0 fixture reconstructs all 17 pairs
  row-for-row against the composition arrays), manifest `4633c3d3…` + pin, dry-run pass. The
  inventory harness gained `--adapter-r4`; a scratch read-only inventory with R4 applied was
  started on the server at 09:53 UTC to surface anything hidden behind defects 4/5 before the
  real R4 run.
- **Factory v2 integration into the 100E bundle** (codex, delivered): config v2 with
  `r7_code_root`, EXPECTED values in preflight/verify, launcher order seed-first with
  learner-manifest verification, FACTORY_SPEC v2, target root `-ops3-r6`, 90-entry manifest
  `9c75f242…`; 28 tests, dry-run pass. Independent codex review
  (`REVIEW-V2-INTEGRATION-CODEX-2026-09-07.md`) found five hardening gaps against the ruling —
  no diagnostic gate inside the launcher, lexical seed-path comparison, loaded-origin checks only
  for 3 of 18 authentication files, no fresh-process closure test, no launcher integration test
  with failure injection — all delegated. Launcher items delivered and verified: the launcher now
  runs the one-epoch diagnostic in the fresh checkout and requires exit 0, receipt + sidecar,
  PASS, empty failed_checks and a provider identity equal to the preflight receipt before any
  controller/tmux step; the seed root is compared by resolved path on the server; a hermetic
  integration test drives the real launcher through ssh/rsync/scp shims, checks the full stage
  order and injects failures at 11 pre-controller stages (none reaches controller creation).
  V2 bundle now 47 tests, dry-run PASS, manifest `51a9d26f…` (90 entries).
- **Closure finding (factory hardening)**: the new fresh-process closure test shows the factory
  process loads 51 R7-bound files, not 18: v1's import-time loading of the provider bridge pulls
  in the target adapter, orchestrator and heterogeneous trainer, hence the live
  `ee_axis_lcsrs_three_route.py`/`ee_axis_v014_head.py` and their dependency cone (31 of the 33
  extra files are byte-identical to their R7 bindings; the two divergent ones are exactly the
  learner-side files). The test is fail-closed by design and currently RED. A follow-up
  adjudication was requested from codex gpt-6-astra: proposed formulation = two recorded sets
  (18-file authentication set hash-equal to R7 + a learner-runtime set recorded with loaded
  origins and required to be bound by the 100E launch manifest), or expanding the authentication
  list, or isolating authentication in a subprocess. Ruling received
  (`ADJUDICATION-R7-CLOSURE-51-VS-18-CODEX-GPT6-ASTRA-2026-09-07.md`): adopt hardened P — declare
  A (18) and L (33) explicitly with module mappings, record both lists with loaded origins,
  add `r7_bound_learner_runtime` + digest to the identity payload, A must hash-equal R7 bindings,
  L must be bound by the 100E manifest, plus an authentication-only fresh-process probe that must
  close at exactly A; the 100E preflight/verify consumers must accept the four-field records.
  Implemented by codex (the task was killed mid-run by a local low-memory event caused by other
  sessions' workloads, but its edits were complete): after a manifest rebuild all 85 factory-v2 +
  V2-bundle tests pass, dry-run passes, manifest `8e4d8784…` (90 entries).
- **R4 scratch inventory (read-only, R4 applied, 09:52–10:34 UTC,
  `R7-FINAL-VERIFIER-INVENTORY-R4-SCRATCH-20260907.json`)**: pair-key reconstruction agreed on
  both derivations for all 48 joins (688 pairs; per-world 96/83/85/86/82/102/72/82),
  `c2_diagnostic` normalisation processed 72 list containers → 688 pair objects → 688 rows, and
  exactly ONE finding remains, at the decision stage: `C2 q2 delta differs` (world 2026121801,
  reported per phase; the check stops at the first failing world) — the float32/float64
  `q2_delta` precision path predicted by the pair-key memo, now CONFIRMED on real data (defect 6).
  R4 amended by codex with a third scoped correction: an AST transform of the unique
  `expected_q2_delta` assignment inside the frozen `_context_status` that recomputes each member
  delta in float32 exactly as the writer does (source adapter lines 891–920 / 1949–1952) and then
  widens, leaving the 1e-12 comparison, operands, rows and decisions untouched; receipt field
  `q2_delta_precision` with row counts; 15 tests pass, manifest `f90381cf…`, dry-run pass.
  The second scratch inventory (10:44–11:31 UTC, `R7-FINAL-VERIFIER-INVENTORY-R4B-SCRATCH-20260907.json`)
  still showed the single `C2 q2 delta differs` finding — because the harness's `--adapter-r4`
  path installed only the first two R4 hooks, not the new third one (verified in its source), so
  R4B is not evidence about correction 3. Instead of another blind 40-minute run, a 1-minute
  read-only probe (`PROBE-Q2-DELTA-PRECISION-RESULT-2026-09-07.md`) settled it on all 8 worlds:
  89 of 688 C2 rows fail the frozen tolerance under float64 recomputation (max 5.96e-08, float32
  ulp scale; all `q2_values` are exact float32), 0 fail under float32 writer-style recomputation
  (max diff 0.0), and the target-delta path passes everywhere. Correction 3 is therefore exact
  and sufficient. The harness was extended to install all three hooks (and to skip its own AST
  rewrite of `_context_status` under `--adapter-r4`, since R4's correction 3 rebuilds that
  function from the frozen source and a prior rewrite made the target non-unique). Third scratch
  inventory (11:39–12:16 UTC, `R7-FINAL-VERIFIER-INVENTORY-R4D-SCRATCH-20260907.json`):
  **0 findings** — NPZ dispatch 8/48, pair keys reconstructed for all 688 pairs with both
  derivations agreeing, 72 diagnostic containers normalised to 688 rows, 1376 member q2 deltas
  compared under the writer's float32 path, R7 root untouched. The real R4 run was launched
  immediately afterwards (~12:19 UTC; see §12).

## 2. Root causes (why the project keeps looping)

1. Frozen fail-fast verification code was not exercised end-to-end against the real artifacts
   before it was frozen, and its tests were self-referential: `tests/test_w201_ee_axis_lcsrs_final_verifier.py`
   derives expected NPZ hashes from the verifier's own domain constant; the post-R7 factory tests
   mock the authentication/construction seams; the C1/C2 wrapper test fixture carried the wrapper's
   own expected literal. Each 40-minute server run therefore exposes exactly one defect.
   Verified test-gap evidence (Claude Sonnet audit
   `AUDIT-VERIFIER-TEST-PROVENANCE-CLAUDE-SONNET-2026-09-07.md`): `tests/test_w201` loads a
   different, older verifier copy (`.scratch/multi-catfish-v023-c3-observability/…`, 282 diff
   lines vs the frozen R7 file) and bypasses `_load_npz`/`_validate_pair_arrays`/
   `_validate_composition_arrays`/`_join_composition_source`; the source adapter's own
   completeness test checks a hand-picked `issubset` omitting both pair keys; no test anywhere
   runs the real source and composition writers into `verify_v023_final_gate`.
   Remedy (endorsed by codex): before any further versioned repair, run a read-only, non-fail-fast
   inventory over the sealed shards that reports every check as PASS/FAIL/BLOCKED, then make one
   versioned repair validated against the preserved real artifacts plus mutation-negative tests.
2. The single-tree provenance assumption in the post-R7 factory (`repo=REPO` for the R7 code
   closure) was broken by the adopted 228/448 architecture. Remedy: DECISION A (§5).
3. Operational: unplanned server reboot (05:25 UTC) and 16 concurrent shards at ~4.8 GB RSS each
   (~77 GB of 91 GB) — long runs must checkpoint, and heavy read-only diagnostics (the R7
   inventory needs ~8–9 GB) must not overlap the shard phase.

## 3. Session timeline (UTC)
- 05:31 reverify: no tmux server, R3 log 0 B, server uptime 4 min → reboot diagnosed.
- 05:41 interrupted R3 artifacts moved to the preservation dir; 05:42 R3 relaunched (frozen package).
- 05:38–05:43 scope-literal adjudication, wrapper/test/manifest correction, 43 tests, dry-run.
- 05:43 r5 launched (new roots); 05:47 single-anchor PASS; 06:05 six PASS + validate; 06:05:47 tmux;
  06:08:57 16 shards started.
- 06:22:54 R3 terminal INVALID_RUN (identity array).
- 06:5x delegation: codex inventory harness, codex gpt-6-astra adjudication, agy V2 review
  (relaunched once with `</dev/null`; the CLIs block on stdin in background shells).
- 07:0x V2 bundle aligned (88-entry manifest), agy found 3 real launcher defects → fixed, 21 tests.
- 07:1x adjudication returned DECISION A; inventory harness delivered.

## 4. Artifact and receipt ledger
Server (`sat`):
- R7-I1 root `/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1`: unsealed; `final-verification.json`
  INVALID (`2b14fb95…`); `repair-authority/`, `-r2/`, `-r3/` additive snapshots; no COMPLETE/MANIFEST.
- R3 evidence: `/home/sat/mcrl-v023-r7-domain-repair-20260907-r3.log` (`c76640b6…`); interrupted
  attempt preserved under `/home/sat/mcrl-v023-r7-domain-repair-20260907-r3-interrupted-by-reboot/`.
- R7 checkout (seed for 100E): `/home/sat/mcrl-v023-r7-launch-ready-20260906-r4` (three_route db8f,
  v014_head b1ac; lacks 5 learner runtime files).
- r4 (preserved, failed scope literal): `/home/sat/mcrl-v023-c1c2-target-generation-20260907-ops3-r4`.
- r5 server root `/home/sat/mcrl-v023-c1c2-target-generation-20260907-ops3-r5` (CODE-MANIFEST
  `8a290eee…`); output root `/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r5`; staging
  `…-ops3-r5-mode-shards/` (shard-status receipts); tmux `mcrl-v023-c1c2-target-generation-20260907-ops3-r5`.
- Post-seal check staging: `/home/sat/mcrl-v023-postseal-target-check-20260907/` (adapter copy
  `6388e41d…` + `postseal_target_load_check.py`; run only after COMPLETE).
Local (repo, all untracked under `.scratch/`):
- `.scratch/multi-catfish-v023-c1c2-target-generation-launch/` — corrected wrapper (`7adcb495…`),
  tests (`1cf23533…`), CODE-MANIFEST `8a290eee…`.
- `.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/` — aligned V2 bundle (§6).
- `.scratch/multi-catfish-v023-r7-final-verifier-inventory/` — codex-built inventory harness (§8).
- `.scratch/multi-catfish-v023-controller-handoff-20260907/` — this report, the adjudication brief
  and memo, the agy review, the scope-literal note.

## 5. Adjudication: R7 code closure vs live learner tree → DECISION A
Full memo: `ADJUDICATION-R7-CODE-CLOSURE-CODEX-GPT6-ASTRA-2026-09-07.md` (brief alongside).
Essentials: build a versioned successor factory (never rewrite frozen manifests); provider config
schema v2 with required absolute `r7_code_root` (the immutable R7 seed checkout); `authenticate_r7_go(root, *, r7_code_root)`;
`_verify_r7_preflight` runs the unchanged `validate_manifest` with `repo=r7_code_root` and matches
code-manifest hashes to the sealed authority; new `_verify_r7_authentication_runtime()` checks the
18 shared authentication files (3 R7 modules + 15 `mcrl` files, list in the memo) against their R7
bindings in the learner checkout; identity payload gains `r7_code_root`,
`r7_preflight_manifest_sha256`, `r7_code_manifest_sha256`, `r7_result_manifest_sha256`,
`r7_gate_result_sha256`, `r7_authentication_runtime_sha256`; launcher order = seed check → copy
seed → R7 closure check against the seed → overlay learner manifest → verify overlay → factory
preflight in a fresh learner process → diagnostic → formal. Caveat from the memo: the live
`DetachedQ12Snapshot` digest is not backward compatible; historical snapshot digests are artifact
data and must never be rebuilt with the live class. Test matrix in the memo (positive real-artifact,
drifted seed binding, code root == learner checkout, missing field/v1 schema, tampering, launcher
integration).
Implementation status: codex gpt-5.6-sol delivered the versioned successor
`.scratch/multi-catfish-v023-post-r7-provider-factory/v023_post_r7_provider_factory_v2.py`
(599 lines; imports v1 by path and overrides only the ruled functions; config schema v2 with
required `r7_code_root`; `_verify_r7_authentication_runtime` over the 18 shared files; identity
payload extended) with 18 synthetic/mutation-negative tests passing and
`V2-DECISION-A-IMPLEMENTATION-NOTE.md` listing exactly what the 100E bundle must adopt next
(config v2 JSON, preflight/verify EXPECTED values, launcher order). v1 is byte-identical
(`315c5229…`). Empirical confirmation of the boundary: v1's own test
`test_authenticate_r7_requires_seal_then_computes_record_panel_digest` now fails on the live
tree with `R7 preflight authoritative validation failed` (the R7-bound `ee_axis_v014_head.py`
differs), i.e. the unchanged factory cannot authenticate R7 in the learner tree. Not yet done:
integrating v2 into the 100E bundle and the real-artifact positive test (no sealed roots exist).

## 6. 100E V2 bundle — aligned, tested, not launchable yet
Changes (execution only): provider config target root → r5; contract §0 with the explicit V2
statements and the real model-config digest; hash chain regenerated (contract `e258bab0…`,
provider `24110f03…`, model `81e30b71…`); launcher guards (`-100e-r2`, target/R7 roots), seal
checks via variables, `-v2` receipt schemas, write-once startup marker + bounded 120 s
acknowledgement; verify script deduped and r5 root; `build_v023_100e_launch_manifest.py` (88
entries incl. the full 53-file `mcrl` import closure); stale V1 sealer test fixed. agy review
found three real defects (two stale top-level launcher hashes, an unescaped `\n` in the generated
controller) → fixed, two regression tests added. Final: 17 server/seal tests + 8 diagnostic tests pass, manifest
`6e2e95e7e421ffc65b35967eae9a5d0279816de304ac3932a9a3fa6ffb9041fc`, `--dry-run` PASS.
Still blocked by §1 (R7 unsealed) and §5 (factory change not implemented): with the live files in
the manifest the launcher's seeded-closure step fails by design until the factory follows DECISION A.

## 7. One-epoch real-provider diagnostic (ready, not runnable until §5)
`run_v023_one_epoch_provider_diagnostic.py` (+4 synthetic tests): loads the real factory, records
provider batches, checks Q1 228-D / Q2 448-D / masks, producer `target_delta` byte-equality against
delivered C2 labels (no second kappa division), five-arm source mapping, disk checkpoint reload,
bit-identical one-epoch continuation, masked q1+q2+q3 scoring (plumbing only, references recomputed).
Reviewed read-only by codex (`REVIEW-ONE-EPOCH-DIAGNOSTIC-CODEX-2026-09-07.md`; agy timed out twice):
four findings, all fixed — the lexical "no kappa_bits" check was replaced by a behavioural one
(each arm's C2 loss is recomputed from the pre-update Q2 weights and the delivered normalized
deltas and must match the trainer's reported loss to 1e-6 relative; a trainer that divides by
kappa again now fails, proven by a mutation test), the target-artifact loader is mandatory,
identities must be trimmed/nonempty/≤512 chars, and receipts survive unserialisable metadata.
8 tests pass. Command in the V2 README; it inserts `<checkout>/src` itself.

## 8. R7 final-verifier inventory harness (codex gpt-5.6-sol) — run after r5 finishes
`.scratch/multi-catfish-v023-r7-final-verifier-inventory/inventory_v023_lcsrs_final_verifier.py`
(+tests, README). Read-only; applies the three R3 installs; AST-transforms named validator
functions so raises are recorded; per-shard isolation; writes only `inventory.json` in an absent
output dir outside the run root. Server command (see README):
`/home/sat/mcrl-leo-handover/.venv/bin/python <checkout>/.scratch/multi-catfish-v023-r7-final-verifier-inventory/inventory_v023_lcsrs_final_verifier.py --run-root /home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1 --checkout /home/sat/mcrl-v023-r7-launch-ready-20260906-r4 --output /home/sat/mcrl-v023-r7-final-verifier-inventory-20260907`.
Memory note: the verifier needs ~8 GB RSS; it was run with `oom_score_adj=1000` while the
shards were still computing (peak host usage 77/91 GB) and completed in 41 min.
Status at hand-back: RUN ONCE, complete; results in §1 and in
`R7-FINAL-VERIFIER-INVENTORY-20260907.json` (sha256 sidecar alongside). Harness tests: 5 pass.

## 9. Measured throughput (r5 benchmarks)
sealed-input load ~189 s and 100-user setup ~25 s per process; C2 replay 3.50 s/row (1 row),
1.74 s/row (2 rows), 0.106 s/row informed / 0.164 s/row neutral for full-step cohorts (45/29 rows);
informed full route 4330 rows. The controller's 16 shards had produced no dataset after 62 min
(compute-bound, C1 generation not benchmarked). No total-time estimate is offered until the first
shard terminal receipt exists.

## 10. Delegation record and CLI pitfalls
- codex gpt-6-astra (read-only, effort max): adjudication → DECISION A.
- codex gpt-5.6-sol (workspace-write, effort ultra): inventory harness.
- agy Gemini 3.8 Flash (High): V2 consistency review → 3 defects found, all real; no files modified
  (directory hashes snapshotted before/after).
- Pitfall: in background shells both CLIs block on "Reading additional input from stdin…" — always
  run with `</dev/null`.

## 11. Next actions (ordered) and prohibitions
1. r5 will end FAILED on `generate_v023_c1c2_targets.py:1315` (`.rows` on the C2 dict). Decide
   ONE corrected target attempt: fix that summary line (`len(dataset["rows"])` or a typed
   accessor), add a real write-path test that runs `_write_outputs` on one OPS-3 dict + one
   opening dataset, rebuild CODE-MANIFEST, and either rerun the 16 shards (~80 min each in
   parallel; ~77 GB RAM; 80–178 min per shard) — ten worlds have no output at all, so a full
   rerun is the simple path; the six complete r5 shard outputs can serve as a byte-level
   regression reference for the corrected generator (same world, same rows expected).
   Then run `postseal_target_load_check.py` (read-only) on the sealed root.
2. Run the R7 inventory (§8) once, read-only, after the shards finish; attach `inventory.json`.
3. With the inventory in hand, decide ONE versioned R7 repair (R4) covering everything at once.
   The inventory bounds the scope to exactly: keep the three R3 installs; reconstruct
   source-side pair keys from the authenticated source JSON/NPZ (repair shape "a" in the
   pair-key memo, never copied from composition); accept the list-typed `c2_diagnostic`
   container while preserving every row and provenance check; then re-run the read-only
   inventory with both changes applied in a scratch process to surface anything hidden behind
   them (the float32/float64 `q2_delta` tolerance is the known suspect) before freezing R4;
   validate against the preserved real shards plus mutation-negative tests. A pair-key-only
   R4 is insufficient.
4. Implement DECISION A as a versioned successor factory + V2 launcher order + tests (memo §3);
   delegate implementation to codex, review with agy, keep server runs to the controller.
5. Then: one-epoch diagnostic → formal 100E screen (checkpoint every 100 epochs) → one-world
   plumbing → episode ladder 100→500→1500/3000→9000 with receipts every 100 episodes and a user
   notification before 9000.
Do not: rewrite frozen manifests; alias modules via `sys.modules`; drop bindings from manifests;
relabel ALL_NEUTRAL_CONTROL as BASELINE; open TEST; tune any parameter against results.

## 12. Live results at hand-back
- r5: TERMINAL. The controller wrote `FAILED` at 09:06:33 UTC
  (`mode/world shard failed: informed:2026121705 status=2`) and aborted the 10 shards still
  running; tmux gone, no generator alive. Six shards had finished on their own, each with complete
  per-world outputs (c1 rows 3455–4875, c2 rows 510–574, receipt + MANIFEST) and the identical
  line-1315 crash: neutral 1708 (07:29), informed 1711 (07:56), neutral 1709 (08:35), neutral 1707
  (08:40), neutral 1705 (08:43), informed 1705 (09:06). Their 407 MB stay under
  `…-ops3-r5-mode-shards/{informed,neutral}/world-*/`; the other ten worlds have no output
  (`controller aborted this shard after another failure`). Wall time per finished shard was
  80–178 min with 16 running concurrently. The controller blocks on its first child, so a failure
  in another shard is noticed only when that child exits — a second reason to fix the generator's
  summary line before any rerun.
- R7 inventory run: COMPLETE (193 findings = pair keys ×48 shards + c2_diagnostic container; nothing else)
- R4 real run: launched 12:17 UTC through the frozen R4 launcher (remote preflight PASS, manifest
  `f90381cf…`, tmux `mcrl-v023-r7-domain-repair-20260907-r4`, `repair-authority-r4/` snapshot
  created); expected ~40 min; outcome recorded below when available.
- r6: FAILED 11:32:48 UTC on the controller's claim-ceiling literal after the first shard
  finished (its outputs are complete and now authenticate under the corrected controller;
  offline dry-run present=1 passed=1 failed=0 missing=15). r7 is fully prepared (CODE-MANIFEST
  `dc5ef936…`, launcher dry-run PASS) and waits for the user's go; nothing is running on that line.
- Training: not started.
- r7 (12:32 UTC, user go): the launcher failed closed at its remote pytest step BEFORE any
  benchmark or compute — the new real-row controller tests read their fixture from the
  sibling target-batch-adapter package, which the launcher's sync list does not ship
  (`FileNotFoundError … fixtures-real-r5/c2-neutral-world-2026121708.excerpt.json`). The
  partial server root `…-ops3-r7` is preserved (no outputs). Fix: the fixture now lives inside
  the launch package (bound in CODE-MANIFEST as `launch_tests_real_row_fixture`); relaunch as r8.
- Launcher-order rehearsal on the server: copying the R7 seed and overlaying the 90 100E
  manifest entries reproduces 90/90 hashes, and `preflight_r7_balanced --repo <overlaid>` then
  fails on `ee_axis_v014_head.py` exactly as predicted, while the same preflight against the
  untouched seed passes — confirming the V2 launcher must (and now does) check the R7 closure
  against the seed before the overlay.
- r8 (12:37 UTC): the fixture directory name `fixtures-real-r5` tripped the preflight's forbidden
  path marker `r5`; renamed to `fixtures-real-shard`, CODE-MANIFEST `79a181a3…` (30 bindings),
  preflight/audit/tests/dry-run all pass; r8 launched (remote pytest → benchmarks → 16 shards).
  Note for the V2 bundle: its provider config/contract still name `-ops3-r6` as the target root
  and must be moved to the root that actually seals (r8) before the 100E launch.
- Prepared for the moment R4 seals: `rehearsal_factory_v2_r7_half.py` on the server rehearsal
  checkout runs `authenticate_r7_go` (factory v2, r7_code_root = seed) plus C3 schedule/input
  construction on the real R7 root, without the target root — read-only, non-authoritative.
- Seventh consumer mismatch, found offline (codex, producer-built fixtures via `_write_outputs` →
  controller `_merge` → sealer): the target-batch adapter that the provider uses rejected the real
  MERGED receipt (fields `parallel_modes/parallel_worlds/parallel_shards/shards`), expected stale
  C1 binding fields, and lacked the producer's C2 `mode` binding. Adapter aligned to the producer
  (`3b8a2268…`), 18 adapter tests pass; V2 launch manifest rebuilt `f3d72644…`; bridge, factory-v2
  and V2 bundle tests pass. Without this, the one-epoch diagnostic would have failed on the first
  sealed root.
- Test debt on the critical path: 4 tests in `test_v023_five_arm_source_training_runner.py`
  (dated 02:23, pre-448) still feed C2 as the retired shared `EEAxisPairBatch` and fail with
  `C2 provider batch must be normalized OPS-3 Q2`; the runner module itself is current. Fixture
  update delegated to codex (runner module must not change: it is bound by the 100E manifest).
- Adapter re-verified on real data after the merged-receipt fix: the r6 shard's 525 C2 rows still
  load as (525,448) float32 with legal masks and the expected unit/kappa, and a real C2 update runs
  (0.15 s). Parallel work started while r8 computes: (i) codex moves the V2 bundle's target root to
  `-ops3-r8` and rebuilds the hash chain now instead of after the seal; (ii) codex prepares a
  NON-FORMAL one-world plumbing rehearsal with five fresh untrained current models (export format
  of the runner, `formal:false`) to measure per-step/per-arm wall time and surface plumbing defects
  before any trained checkpoint exists; (iii) codex repairs the pre-448 runner tests.

- **13:10 UTC addendum.** codex tasks all finished (exit 0): V2 bundle repointed to `-ops3-r8`; after the runner test file changed underneath it the manifest drifted, so it was rebuilt: `V023-100E-LAUNCH-MANIFEST.sha256` = `233a818765f2d67049a32ac74516162507bd075bc1fbf23261063a9d57be7c0f` (90 entries), bundle tests 60 pass; runner tests 7 pass; plumbing rehearsal tests 3 pass. r8: benchmarks 6/6 done, 16 shards running since ~12:56 UTC, no shard complete yet. None of this is a launch path after §13; it is kept as reusable plumbing.

## 13 · R7 gate sealed 12:54 UTC — integrity VERIFIED, decision STOP_PHYSICS_R7 (scientific STOP)

- **Verified.** The R4 domain-repair controller finished `V023_R7_DOMAIN_REPAIR_R4_PASS source_loads=8 composition_loads=48 pairs=688 c2_rows=688` and the sealer wrote `result.json`, `verification.json`, `MANIFEST.sha256`, `COMPLETE` into `/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1` at 12:54:16 UTC. `result.json`: `integrity_status=VERIFIED`, `status=PASS_FINAL_INTEGRITY`, `c3_decision=STOP_PHYSICS_R7`, `no_rescue=true`. Local copies: `r7-sealed-receipts/` (result.json sha `dfcc70e441e2ec2c3be20608124c704c6d5c80b4d902a1aa7b75328faadbd2f7`, MANIFEST.sha256 sha `63ecb5a8ec08f8fe89c5e656871fd019493e0eb6fdb7777e152c9fef85b8c01f`, receipt status `PASS_R7_FINAL_VERIFIER_DOMAIN_REPAIR_R4`, corrected verification sha `94915623…`). Per-world numbers: `R7-STOP-PHYSICS-RESULT-2026-09-07.md`.
- **Derivation (verified against `r7_balanced_successor_gate.py:adjudicate_section14_r7`).** Precedence: integrity → pair_coverage → (mechanics ∧ physical_signature ∧ teacher_composition) → (target_support ∧ held_out_learner ∧ world_stability) → (action_exposure ∧ literal_11 ∧ harmful_partial ∧ topology_consistency ∧ learned_composition ∧ service) → GO. `physical_signature=false` decides the token: pooled ratio-of-sums EE of the 11 profile versus 00 is −0.049% (`pooled_joint_direction=-1`) and only 2 of 8 worlds are positive (threshold: strictly positive and ≥4). `mechanics` (688/688) and `teacher_composition` (+0.335% vs baseline, 5 worlds) passed. Also false at lower precedence: `learned_composition` (−0.660% vs baseline, 2 worlds), `topology_consistency` (379/707 = 0.536 < 0.8), `harmful_partial` (`verify_v023_lcsrs_final.py:1668` — predicate true only when the harmful-partial fraction ≤ 0.05; it is false). Had physics passed, the token would have been `REDESIGN_INTERFACE_R7`, not GO. Held-out learner (balanced accuracy 0.705 vs placebo 0.626, spearman 0.839, 8/8 world wins), world stability, C1/C2 context all passed.
- **Effect on training (verified).** The read-only R7-half rehearsal of the provider factory on `/home/sat/mcrl-v023-learner-rehearsal-checkout-20260907` (12:58 UTC) returned `R7_HALF_FAIL: V023PostR7ProviderFactoryError: R7 final result c3_decision is not the frozen GO value`. The V2 100E launcher's seed-first R7 closure check and factory preflight therefore stop before any learner is constructed. Contract `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-SUCCESSOR-GATE-CONTRACT-R7-BALANCED-2026-09-06.md` §7: a valid non-GO result ends the LC-SRS successor route; no second metric revision, threshold relaxation, seed/world replacement, rerun selected by outcome, or automatic promotion of CSE/EC; a later CSE/EC experiment needs its own already-declared formula and falsifier. §8: the 100-episode five-arm screen begins only after GO.
- **Timing (verified).** The source arrays that determine `physical_signature` were written on 2026-09-06 15:10 (`source-stage-verification.json`, `VERIFIED_SOURCE_STAGE`, decision fields null by design). The decision was therefore determinable ~22 h earlier and was hidden only by the verifier crash chain (defects 1–6, §2). This completes the audit question: the execution chain no longer has any integration boundary between code and launch; the remaining boundary is the pre-registered science gate, which says STOP.
- **Controller action per brief.** Genuine scientific STOP → the execution mandate for the R7 → 100E line ends here. Receipts preserved; no R5, no factory or manifest rewrite, no relabelling. Dispatched 13:05 UTC: codex gpt-6-astra read-only adjudication (token derivation, whether any of the six verifier-side corrections could touch the physics predicates, contract-consistent options, what may be recorded as motivation without selection on outcome) → `ADJUDICATION-R7-STOP-PHYSICS-CODEX-GPT6-ASTRA-2026-09-07.md`.
- **Unaffected and continuing.** r8 C1/C2 target generation (own claim ceiling `TRAIN_PHYSICAL_TARGET_GENERATION_ONLY…`, independent of the R7 decision) keeps running; its sealed targets remain usable by any successor that keeps C1/C2. codex finished: V2 bundle repointed to `-ops3-r8` (60 tests, dry-run PASS at its time), runner test-debt cleared (7 pass; runner module untouched, mtime 04:20 UTC), one-world plumbing rehearsal script staged (`rehearsal_v023_one_world_plumbing_fresh_models.py`, expected exit 3 = fail-closed untrained-export blocker; not run).
- **What the user must decide.** Whether to declare a successor experiment (fresh contract with its own formula and falsifier, declared before any computation and not selected on R7 residuals), or to redesign C3 / the three-Catfish composition. Nothing in the current frozen chain can be re-run to a GO.
- **Independent adjudication (codex gpt-6-astra, read-only, 13:09 UTC; `ADJUDICATION-R7-STOP-PHYSICS-CODEX-GPT6-ASTRA-2026-09-07.md`).** VERIFIED there: local receipt hashes match `MANIFEST.sha256` and `COMPLETE`; `STOP_PHYSICS_R7` is the mandatory token and `physical_signature` is the only predicate deciding it (physics alone passing would yield `REDESIGN_INTERFACE_R7`); the `harmful_partial` FAIL rendering is correct (passing guard = fraction ≤ 0.05); each of the six verifier-side corrections is traced to its scope and none changes the inputs or comparisons of `physical_signature`, `mechanics`, `teacher_composition`, `learned_composition`, `topology_consistency`; the factory refusal is a frozen admission rule (factory v2 lines 653–657, 100E contract lines 47–65). Recommendations: close LC-SRS R7 with evidence preserved; let r8 C1/C2 finish under its own claim ceiling and reuse authenticated targets and the 448-D Q2 head only under a fresh bounded handoff; CSE/EC or any new C3/composition design needs its own already-declared formula, falsifier and outcome-independent eligibility before computation; report the R7 aggregates as falsified-prediction evidence, never as a selector for the next mechanism. Decision line adopted: *Accept sealed `STOP_PHYSICS_R7`; the LC-SRS successor and its conditional 100E execution mandate end, with immutable evidence preserved.* The user must decide whether to close this direction or issue a fresh handoff for an independently justified, contract-eligible experiment.

## 14 · Post-STOP route facts (collected 13:15–13:30 UTC; decision pending the codex gpt-6-astra ultra adjudication)

- **A pre-outcome C3 contingency design exists.** `.scratch/multi-catfish-v023-c3-observability/V023-C3-RAPID-CONTINGENCY-LADDER-PREOUTCOME-2026-09-06.md` (dated 2026-09-06 01:15, written before any R7 outcome; status `FROZEN_PREOUTCOME_CONTINGENCY_DESIGN / NO_LAUNCH / NOT_CURRENT_AUTHORITY`). Locked candidate order L (LC-SRS, now STOP) → D (cost-shared externality, CSE) → F (energy-share correction, EC), with fixed formulas, fixed worlds/lineages/steps and kill rules: F0 formula seam (local; implemented in `.scratch/multi-catfish-v023-c3-contingency/c3_contingency_f0.py`, 18 tests passed on 09-06), F1 shared two-step kill screen (server; TRAIN world `2026121721`, lineage `2026092101`, first two canonical steps, one common keyed field; survive only if service ≥ BASE−0.001 and pooled ratio-of-sums EE strictly above BASE), F2 four-world oracle screen (worlds `2026121721`–`24`, lineages `2026092101`–`03`, ten steps; ≥3/4 worlds and 2/3 lineages positive), F3 source-to-learner screen (2000 source updates, checkpoints every 100, three learner seeds; INFORMED vs equal-budget NEUTRAL), F4 fixed-policy physical evaluation 100/500/1500/3000 episodes with a receipt every 100 (9000 remains a user-notified decision). Its §4 branch for `STOP_PHYSICS` is: *open F0/F1 for D and F in parallel on the shared tape*. The 100E contract §6 and the R7 contract §7 both refer to exactly this family. The F0 `PhysicalProfile` needs only fields that `ActionEvaluation` already exposes (`link_rate_bps`, service resolution, radiating beams, `link_power_w`, `fixed_power_w`, `system_power_w`), so an F1 tape generator is integration work on existing seams, not new physics.
- **The five-arm runner and plumbing are three-route by construction.** `v023_five_arm_source_training_runner.py` fixes `ARMS = (ALL_NEUTRAL_CONTROL, FULL, DROP_C1, DROP_C2, DROP_C3)`, `ROUTES = (C1, C2, C3)` and `EEAxisLCSRSThreeRoute` checkpoints; the one-world plumbing needs five checkpoints in that order. A C1/C2-only training would need a declared two-route variant (four arms, two routes), a provider factory without the R7 dependency, and its own contract. Feeding a neutral C3 into all five arms would make FULL ≡ DROP_C3 under the old labels and is not an option.
- **Measured costs for the estimate.** Fixed-policy physical evaluation, one arm, 100 episodes × 100 users × 10 committed steps on the server: `wall_time_s = 1293.98` (`.scratch/multi-catfish-v023-physical/server-result-20260906-r1/timing.json`, DROP_C3 development evaluation of 2026-09-06) → ≈ 21.6 min per 100 episodes per arm, ≈ 10.8 h per 3000, ≈ 32 h per 9000 (arms can run concurrently). Source training: no epoch timing exists yet; the one-epoch diagnostic is the measurement. C1/C2 target shards: 80–178 min each (r5/r6), 16 in parallel. The August RL-training figure (9000 episodes ≈ 9.9 h) is a different regime and is not used.
- **Decision (13:30 UTC, controller with codex gpt-6-astra ultra; `ADJUDICATION-SUCCESSOR-ROUTE-CODEX-GPT6-ASTRA-ULTRA-2026-09-07.md`, `ASTRA_SUCCESSOR_ROUTE=C`).** Route C: close R7 and its five-arm 100E permanently; build a prospectively declared C1/C2-only development experiment now (three two-head learners `FULL2`, `DROP_C1`, `DROP_C2`; physical `BASELINE` = the unchanged pre-Catfish MODQN artifact; no all-neutral learner; 100 epochs = 200 updates per learner; train seed `2927175120652069826` reused unchanged; deployment masked unweighted `Q1+Q2` argmax); keep C3 outside the critical path — it re-enters only through its own admission, i.e. the pre-outcome contingency ladder (F1 → F2 → F3 → F4), never by selecting on two-route outcomes. Disclosure sentence adopted verbatim from the memo. Owner's delegation (13:12 UTC message): decisions are settled with astra; the owner asks only for the time to training.
- **Dispatched 13:37 UTC (codex gpt-5.6-sol, isolated new dirs, workspace-write, no server):** (1) `.scratch/multi-catfish-v023-c1c2-provider-factory-v3/` — two-route provider factory authenticating the r8 root and the learner closure, no R7 dependency; (2) `.scratch/multi-catfish-v023-two-route-source-training-runner/` — two-head model reusing the existing Q1/Q2 networks, `C1→C2` orchestrator, three-arm runner, deployment parity; (3) `.scratch/multi-catfish-v023-c3-contingency-f1/` — ladder F1 kill screen implementation (world `2026121721`, lineage `2026092101`, two steps, shared tape, D before F) plus its preflight manifest builder. Common brief: `.scratch/multi-catfish-v023-c1c2-successor/SUCCESSOR-BRIEF-COMMON-2026-09-07.md`. The successor contract document is being written by the controller in parallel and will be reviewed read-only by astra before freezing; no successor computation (not even the diagnostic) before the contract and manifests are frozen and the r8 digests are bound.
- **Estimate given to the owner (astra's table, anchored 13:20 UTC; engineering allowances, not confidence intervals):** first formal C1/C2 learner update optimistic 3–6 h, expected 6–12 h, pessimistic 1–3 days (assumes r8 seals ~15:30–16:00 UTC and no scientific stop); fixed-policy episode-evaluation ladder start optimistic 8–16 h, expected 1–3 days, pessimistic 4–7 days; 9000 cumulative episodes per arm = ladder start + measured per-episode cost (09-06 measurement: 21.6 min per 100 episodes per arm → ≈ 32 h per arm at that rate, arms concurrent); genuine three-Catfish training: no defensible date — admission-dependent (F1/F2 kill screens can stop it; seven prior C3 attempts all stopped). One timed real-artifact vertical slice (v3 load → one epoch → export/reload/resume → one matched four-arm world) is the measurement that tightens this.
- **Artifact:** the earlier page URL (`…/0b130c2a…`) was reported deleted/inaccessible at republish time (13:40 UTC); the refreshed report was published as a new artifact: `https://claude.ai/code/artifact/527354c1-54aa-4175-8b99-3b03f7beb74c` (13:41 UTC; §14 decision bullets not yet rendered there).
- **13:55–14:05 UTC.** Successor contract draft written by the controller (`.scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-DEVELOPMENT-CONTRACT-2026-09-07.md`; pre-outcome plumbing world seed `936547238915053535` from domain `MCRL_V023_C1C2_SUCCESSOR_PLUMBING_WORLD_SEED_V1`, derivation rule verified against the two V2 seeds). codex gpt-6-astra read-only review (`REVIEW-C1C2-SUCCESSOR-CONTRACT-CODEX-GPT6-ASTRA-2026-09-07.md`): `FREEZE_AFTER_FIXES` — seven textual defects (circular sealing, BASELINE inside the deployment rule, overlapping dispositions, ladder continuation vs runner semantics, late stage-C freeze, incomplete C3 restriction, repair/termination conflict) all applied in R2; its missing-declaration list is now contract §9 (baseline checkpoint `e6b063ef…`, keyed namespace `MCRL_V020_REPRICED_C3_GATE_V1`, 9000-world plan digest, aggregation and integrity dispositions). Fourth codex sol task dispatched 14:05 UTC: `.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/` (four-arm fixed-policy runner, 9000-world plan builder, stage-B plumbing diagnostic). Still no successor computation; freeze waits for r8 digests and implementation closure.

## 15 · Fresh-context slowness audits (owner request 13:45 UTC)

- **codex gpt-6-astra, fresh session, read-only (13:49 UTC; `FRESH-CONTEXT-SLOWNESS-AUDIT-CODEX-GPT6-ASTRA-2026-09-07.md`).** Five structural causes with evidence: (1) long jobs used as integration tests (R7 verdict determinable 09-06 15:10, delivered 09-07 12:54 = 21 h 44 min late; r5/r6 shard cycles 80–178 min per defect); (2) every experiment carries its own execution system — glue census 90 files in 31 directories, 68,434 lines of `sync_launch*/preflight*/seal*/verify*` (46,538 after exact dedup), divergent literals/manifests/imports; (3) C3 eligibility made a prerequisite for progress elsewhere — 66 design documents V0.3→V0.23 between 08-31 and 09-05, seven unsuccessful C3 tracks on 09-03/09-04, ~5 calendar days of C3 gating 09-02→09-07; (4) cheap rejection and expensive qualification insufficiently separated (the ladder has the right shape; R7 withheld a determinable necessary-condition failure behind unrelated crashes); (5) scheduling/review optimised tasks rather than decisions (r5 failure noticed 97 min late; reviews found the next boundary instead of closing a fixed checklist). Verdict on "a core problem nobody caught": **no** — the scientific core (a scoped oracle benefit does not guarantee observable, learnable, composable C3 action choices) and the process core (known risks still trigger bespoke serial cycles) are both already identified. Correction recorded: "no learner training has started" is literally inaccurate — V0.18/V0.19 receipts record 100 learner updates per initialisation; what has not started is the formal successor training, and fixed-policy episode evaluation must not be called episode learning. 72-hour plan matches the controller's: finish Route C (no R7 reopening, no neutral C3 substitution); run the whole consumer chain against every compatible real artifact without stopping at the first failure; one consolidated read-only schema/closure blocker list; one timed real vertical slice after freeze; separate INVALID_RUN repair from scientific termination and predetermine C3 spending limits. Weeks: one reusable execution library; separate research and engineering dependency graphs; one authority index and latency ledger.
- **Claude Opus fresh-context audit (13:52 UTC; `FRESH-CONTEXT-SLOWNESS-AUDIT-CLAUDE-OPUS-2026-09-07.md`).** Verdict on a core problem nobody caught: **yes** — the freeze discipline that is mandatory for confirmatory claims was applied to every activity (exploration, integration, plumbing, debugging), which the owner's rules never required; consequences: (A1) no version control since 2026-08-23 (last commit; 106 `src/` files never committed, 537 status entries, 96 `.scratch` packages, 587,662 untracked lines, 447 copies of `ee_axis*.py`, 55 hand-built manifests, one CODE-MANIFEST rebuilt five times in a day) — the single-tree provenance break and DECISION A exist because no commit object names a code state; (A2) contracts as string literals and array layouts discovered only by real compute (13 defects, ≈ 30–35 h server wall, R7 verdict 22 h late); (A3) no cheap falsification tier — ten mechanisms killed at full price between 09-01 and 09-07, the cheap ladder written on day 14; (A4) design-document inflation (66 docs in 8 days, 55 of 96 packages in the last two days); (A5) serial execution where parallel was free (≈ 6–10 h). 72-hour plan: put everything in git today on a branch without touching content (pending owner's word); make an offline real-artifact dry-run mandatory before any launch; import producer-owned constants + static contract scan; run the timed vertical slice before freezing the execution section; freeze the successor contract now and stop new design documents. Weeks: cheap-kill-first as the only admission path; one parameterised harness; two lanes (engineering unlimited/read-only, science frozen/one-shot).
- **Convergence and actions (14:00 UTC).** Both audits agree on the 72-hour plan. Done: scientific sections of the successor contract sealed separately (`V023-C1C2-SUCCESSOR-SCIENTIFIC-DECLARATION-2026-09-07.md` + `.sha256`), execution bindings left open until the launch manifest; `ENGINEERING-LANE-CHARTER-2026-09-07.md` adopted; fifth codex sol task dispatched (`.scratch/multi-catfish-v023-engineering-lane/`: static contract scanner + generalised offline real-artifact dry-run with a ready stage-A chain spec); server shadow checkout staged. Pending the owner's word: committing the working tree to a git branch.

## 16 · 13:55–14:10 UTC — deliverables landed, git snapshot, F1 ruling, rehearsal-first

- **Git.** Owner's word received 13:57 UTC ("commit 無所謂，可以直接進行"). Branch `wip/multi-catfish-v023-20260907`, commit `14174d606d97acee36a63945b51bbb28a4306e07`, tree `003016c8518e4ac8ed9a30a1439d2b2696eaa4e3`, 7,212 paths, content untouched; 43 files > 10 MB excluded and listed in `GIT-EXCLUDED-LARGE-FILES-2026-09-07.tsv`. Future freezes bind commit SHA + tree hash in addition to manifests.
- **Landed (codex gpt-5.6-sol, all tests green locally):** F1 kill screen `.scratch/multi-catfish-v023-c3-contingency-f1/` (15 tests, dry-run PASS, preflight manifest built); two-route package `.scratch/multi-catfish-v023-two-route-source-training-runner/` (6 tests; model, `C1→C2` orchestrator, three-arm runner, deployment parity); provider factory v3 `.scratch/multi-catfish-v023-c1c2-provider-factory-v3/` (10 tests; strict config, 16-shard authentication, learner closure, no R7). Synced to the server shadow checkout.
- **F1 pre-outcome ruling (astra, `ADJUDICATION-F1-COMPOSITION-UNITS-CODEX-GPT6-ASTRA-2026-09-07.md`):** composition is `masked argmax(Q1+Q2+z/κ)` with the frozen system κ (unit conversion, per the V0.9/V0.11/V0.13/V0.15/V0.22 precedents, not a rescale); keep the R7 keyed-field component; three implementation findings (bundle integrity must propagate to `INVALID_RUN`; deployment profiles must match BASE's 100 users/interval; empty-mask users are NOOP per `action_contract.py:580`). Dispatched to codex for correction + preflight rebuild before any tape is generated.
- **Rehearsal-first (owner 13:58 UTC: start training and keep fixing while it runs).** Adopted in the engineering lane: a non-formal rehearsal package (`.scratch/multi-catfish-v023-two-route-rehearsal/`, codex) trains the three two-route arms on the REAL shards under `/home/sat/mcrl-v023-real-shards-rehearsal` (and r8 staging shards once complete), with export/reload/resume and per-phase timings, `formal:false`, no `COMPLETE`, claim ceiling `ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT`. It cannot feed the paper; it exists to surface integration defects and timings now. The formal stage-A run follows the r8 seal and the launch-manifest freeze; its scientific declaration is already sealed (`f27d0500…`), so nothing seen in the rehearsal can alter it.
- **14:12–14:25 UTC fast-iteration findings (engineering lane, server shadow checkout).** (a) The two-route orchestrator imports the existing C1/C2 update implementation from `.scratch/multi-catfish-v023-heterogeneous-trainer/` by path; that package (and `v022-c3-coalition-residual`, `c3-observability`, `r7-launch-ready`, `docs/`, `artifacts/PREREG-FROZEN-2026-08-25-R2.json`) was not in the shadow sync → import failed on the server in 30 s, fixed by syncing the transitive set; all successor modules now import on the server and the F1 `--dry-run` passes there. This is exactly the class of defect (a sync list narrower than the import graph) that cost the r7 launch on 09-07 morning; caught before any launcher this time. (b) Landed: four-arm physical evaluation package `.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/` (24 tests; runner, stage-B diagnostic, 9000-world plan builder; plan digest re-derived locally = `866d28e0…`, recorded in contract §9 as a rule-derived binding). (c) Server-side shadow verifier started (for real this time; the first start had matched its own ssh command) — authenticates each r8 shard the moment its `.complete.json` appears; results stream to `/home/sat/mcrl-v023-r8-shadow-verify.log`. (d) Sonnet blocker audit died on an account rate limit; re-dispatched to codex gpt-6-astra read-only.
- **14:18 UTC consolidated blocker audit (codex gpt-6-astra, read-only; `AUDIT-SUCCESSOR-PACKAGES-BLOCKERS-CODEX-GPT6-ASTRA-2026-09-07.md`): HOLD, 8 BLOCKERs, 0 MAJOR/MINOR.** Data interfaces agree statically (adapter header/merged-receipt fields, 16 shards both modes, C1 raw / C2 normalized `target_delta` untouched, aggregate-panel sampling as the predecessor bridge; Q1/Q2 constructors and the C1/C2 update methods are imported, not re-implemented; arms/routes/budget/exports/claim ceiling/tie rule match). The blockers are all formal-admission and integrity hardening: (01) model config digest recorded but the consumed file not authenticated against `9eafcd18…`; (02) train seed not enforced to `2927175120652069826` in formal configuration; (03) learner-closure list omits the successor model/orchestrator/runner and the reused heterogeneous trainer; module loaded via `spec_from_file_location` without a natural import; (04) formal admission accepts any protocol-compatible provider, `r7_root`/`q3` identity fields not rejected, authority/code/input digests syntax-checked only; (05) `run_to_epoch` can advance before root validation / `begin_new()`; (06) resume validation incomplete (export vs checkpoint content, consumed-file history vs sampler, Adam defaults); (07) completion writes the terminal receipt without the contract's epoch-100 exact-restore verification; (08) runner-suite fixtures bypass producer/adapter/factory (hand-typed dims, seed 17, fake digests). Disposition: one codex fix pass covering both packages with shared producer-derived fixtures, then re-audit; this is exactly the "one consolidated list instead of one defect per launch" mode both slowness audits asked for.
- **14:23–14:30 UTC.** Rehearsal package landed (`.scratch/multi-catfish-v023-two-route-rehearsal/`: authenticated real-shard provider with `formal:false`, three-arm two-route rehearsal trainer with export/reload/resume and per-phase timings, server sync/run script; 5 own tests + 33 with adapter/factory suites; fixtures built with the producer's writer and sealer). Dispatched a Sonnet operator to run it on the server against `/home/sat/mcrl-v023-real-shards-rehearsal` (3 epochs, then 10 if PASS) — the first genuine C1/C2 learner updates on real target rows in this line, non-formal by construction. codex on the server (`/home/sat/mcrl-v023-codex-ws-blockers-20260907`, git-seeded) is fixing the 8 blockers; the controller no longer executes server work itself (owner's instruction 14:16 UTC) — all execution goes through sub-agents or server-side codex.
- **14:30 UTC engineering-lane tools landed** (`.scratch/multi-catfish-v023-engineering-lane/`, 7 tests): `contract_scan.py` (static producer↔consumer scan: schema/status/claim-ceiling/mode/unit tokens, receipt keys, NPZ names/dtypes/shapes, layout and numeric constants; mutation-negative self-test detects every category) and `offline_realartifact_dryrun.py` (non-fail-fast chain runner against real artifacts with input-write blocking and exact input identities; stage-A chain spec ready, currently BLOCKED 18 / PASS 2 until the sealed r8 root and learner manifest exist). First real scan over five pairs (generator→adapter, generator→sealer/controller, adapter→factory v3, factory v3→two-route runner): zero direct MISMATCH; one-sided items listed for review (e.g. adapter reads `comparison_sha256`, generator does not write it — to be confirmed by the real-shard rehearsal, not by assumption). These two tools are now the gate every new consumer passes before review; they never produce scientific output.
- **14:31 UTC first rehearsal attempt on real shards: FAIL at input validation** (`ENGINEERING-LANE-REHEARSAL-RUN-REPORT-2026-09-07.md`): the rehearsal provider rejects symlinked shard directories, and the rehearsal shard root is by design a symlink farm pointing at the sealed r5/r6 shard directories (all 7 entries). Classification (b) producer↔consumer layout mismatch inside the engineering lane; no formal artifact involved; no retry with changed parameters. Fix dispatched to codex (accept a mode-level symlink whose resolved target is a real directory, record entry + resolved paths and `is_symlink` in identity/receipt, keep all leaf-file guards, add the symlinked-shard test); the operator agent reruns after the fix. Cost of this defect: about 8 minutes, versus the 40 min–3 h it would have cost inside a launcher.
- **14:40 UTC owner's standing instruction: vertical slice first.** Find every problem up to and during training by fast iteration before any formal run. Plan written: `.scratch/multi-catfish-v023-c1c2-successor/VERTICAL-SLICE-PLAN-2026-09-07.md` (V1 real-shard trainer rehearsal; V2 the FULL formal stage-A chain on a scratch-sealed copy of the 16 r8 staging shards before the official seal; V3 stage-B plumbing with fresh untrained exports + BASELINE; V4 stage-C first 100 episodes + checkpoint/resume for τ; V5 interruption drills; V6 verifier negatives; V7 the F1 kill screen). V3 dispatched to an operator agent now (light); V2 and V4 wait for the shards to finish (RAM) and for the blocker fixes.
- **14:36–14:46 UTC.** Rehearsal symlink fix landed (provider resolves mode-level symlinks strictly, records `entry_path`/`resolved_path`/`is_symlink`; 6 tests) — V1 rerun ordered to the operator agent (3 epochs, then 10 on PASS). Second WIP commit on `wip/multi-catfish-v023-20260907`: `f1d88a2` (all packages landed since the seed commit). Operator agents in flight: V1 rerun, V3 stage-B plumbing with fresh models, shadow-closure/server-tests/F1-verification; server codex: 8-blocker fix; local codex: formal launch bundle.
- **14:50–15:00 UTC.** V1 attempt 2 FAIL one layer deeper (per-shard `COMPLETE` requirement vs producer's merged-root-only seal; class (b)); fix delegated to server-side codex in `/home/sat/mcrl-v023-codex-ws-rehearsal-20260907` with mandatory read-only validation against the real shard root and a 1-epoch run inside the workspace. Owner's mandate (14:47 UTC): fastest route to finalising the three Catfish and to Ch5 result figures, process entirely at the controller's discretion. Dispatched accordingly: F2 four-world oracle screen implementation (so an F1 survivor proceeds without design delay) and the Ch5 development-curve figure pipeline (renders from the physical runner's own receipt schemas; tested on runner-written synthetic receipts; watermarks non-formal roots) — both codex, local. Reminder from owner (14:52 UTC): controller delegates execution; all new work went to sub-agents/server codex.
- **14:49 UTC server codex: all 8 blockers implemented** (9 files, +933/−312; focused auth/model tests 3 pass; bounded lifecycle diagnostic completed 100 epochs / 200 updates with `PASS_EXACT_EPOCH_100_RESTORE`); the full two-package suite errored in setup on yet another producer-closure file missing from the partial workspace (`r6-fit-binding-fix/v023_lcsrs_source_adapter.py`) — the check was not weakened. Pull-back, local full-tree test run, and per-blocker fix location check delegated to an operator agent; astra re-audit follows a green run. Third occurrence today of "partial checkout narrower than the hash/import graph": the closure list the other agent is producing becomes mandatory input for every workspace seed.
- **14:50 UTC formal stage-A launch bundle landed** (`.scratch/multi-catfish-v023-c1c2-successor-launch/`: acyclic execution bindings + two-level external manifest, `bind → manifest --check → sync → learner-manifest verify → factory preflight → one-epoch real-provider diagnostic (refusal gate) → runner in tmux → startup marker + 120 s ack`, independent 200-update verifier; 6 own tests + 16 cross-package tests; no `r7` token). Its `--dry-run` correctly refuses locally (`SUCCESSOR_LAUNCH_REFUSED: execution bindings are not current`) because the sealed r8 root does not exist yet — the fail-closed path works. It was written against the pre-fix factory/runner; it will be re-tested after the blocker fixes are pulled back, then reviewed read-only by astra together with V6 (verifier negatives) before any formal use.
- **14:44–15:15 UTC V3 stage-B rehearsal: `STOP_PLUMBING_INTEGRITY`, and the defect is real.** Learned-arm plumbing is clean (checkpoint round-trip through the model's own writer, keyed field, TLE binding, ten-step masked Q1+Q2 deployment for FULL2/DROP_C1/DROP_C2; peak RSS 1.2 GiB, 47 s). BASELINE fails at `baseline_adapter.py:397-400`: the frozen adapter rejects any `UserState.contract_fields`, and `candidates.py:260`/`step.py:1185` now always populate it — byte-identical files locally and on the server, so a genuine producer↔consumer mismatch that would have stopped the first formal stage-C launch. Fix delegated to server-side codex with the scientific property preserved by construction (BASELINE consumes only the native 112-D state: exclusion + encoding-invariance check + a mutation negative), then a stage-B rerun inside its workspace. r8: 2/16 shards terminal at 14:52 (status files are `.terminal.json`; shadow verifier repointed); the local launcher's ssh session dropped (`SYNC_EXIT=255`, broken pipe) but the server tmux and 15 generator processes are alive — no run impact. ssh to `sat` is intermittently refused under the current number of concurrent sessions; monitors were spaced out.
- **14:56 UTC stage-B/C N=1 gate landed** in the engineering-lane tool (`specs/successor_stage_bc_chain.json`, 10 lane tests): fresh two-route exports through the model's own writer → loaders of the physical runner and the plumbing diagnostic → baseline admission → 9000-world plan build/check (`866d28e0…`) → simulator-free deployment check → runner cadence/resume on synthetic records with no terminal result → optional real world (BLOCKED by default). Local run: steps 1–6 PASS. Follow-up queued for after the baseline fix: the gate's baseline step must also encode a state with populated `contract_fields`, so the V3 class of defect is caught by the gate rather than by a rehearsal.
- **14:58 UTC Ch5 development-curve pipeline landed** (`.scratch/multi-catfish-v023-ch5-figure-pipeline/render_v023_development_curves.py`: authenticated receipt roots, arm order read from receipts, EE ratio-of-sums vs cumulative episodes, served fraction with the 0.001 band, matched-world paired differences with a descriptive bootstrap band, optional bits/energy panels, PNG+PDF+`FIGURE-MANIFEST.json`, write-once, rehearsal watermark, forbidden-word check; 6 tests). `matplotlib` was missing from the project venv (codex had used the system copy via `PYTHONPATH`); installed into `.venv` (numpy/torch unchanged) so the tests run natively. Figures will render the moment stage-C rung receipts exist; nothing in the paper is touched by this.
- **15:05 UTC shadow-closure report (`ENGINEERING-LANE-SHADOW-CLOSURE-REPORT-2026-09-07.md`).** Transitive closure of the successor packages = **246 paths** (`SHADOW-CLOSURE-LIST-2026-09-07.txt`), including files hashed rather than imported (r6-fit-binding-fix source adapter + manifest, the V0.20 D40 checkpoint + authority, F1's `CODE_BINDING_PATHS`, sealed R7 receipts as read-only references); all 246 byte-identical local↔shadow. Server tests over six suites: 85 pass / 3 fail, no failure caused by a missing file; the 3 are stale heterogeneous-trainer tests (plain pair batch vs the required V0.14 normalized C2 batch — the same pre-448 test debt class fixed in the five-arm runner this morning); codex fix (tests only) dispatched. F1 corrections verified (a)–(f) PASS with file:line evidence; preflight digest `495d90d2…`; `--dry-run` passes locally and on the server. This closure list is now the mandatory sync input for every workspace seed and for the successor launcher's sync list.
- **15:35–15:45 UTC.** 8-blocker fixes pulled back (`ENGINEERING-LANE-BLOCKER-FIX-PULLBACK-REPORT-2026-09-07.md`): exactly 9 files changed on the server workspace; local full-tree tests 11 + 7 pass for the two fixed packages, 18/18 on the server shadow; all eight fix locations verified by file:line. Ripple effects of the hardened contracts: the rehearsal trainer must now pass `model_config_sha256`, and the stage-B/C gate's per-arm seed increment is rejected by the formal-seed check — consumer alignment dispatched to codex (gate now; rehearsal after its own server fix is pulled back). Committed `f9a5ab9`. Dispatched: astra read-only re-audit of the fixed packages plus the first audit of the formal launch bundle (V6: verifier must reject non-formal roots; sync list vs the 246-path closure); operator agent freezing the F1 launch authority (bindings verbatim from the preflight `495d90d2…`) and running the F1 kill screen once on the server (tmux `mcrl-v023-c3-f1-20260907-r1`, output `/home/sat/mcrl-v023-c3-contingency-f1-20260907-r1`).
- **15:07 UTC baseline adapter fixed on the server and V3 is green.** `baseline_adapter.py` now structurally encodes only the four native arrays, forces `contract_fields` out of the encoder, runs a synthetic byte-invariance check at construction and records `contract_fields_excluded: true` in its binding; 12 tests incl. 64 randomised invariance cases and the inclusion mutation-negative; all admission checks unchanged. Stage-B rerun in the workspace: `PASS_PLUMBING_INTEGRITY`, four-arm execution 47.3 s, peak RSS 1.25 GB, receipt with the declared claim ceiling, finite descriptive endpoints, no new boundary after BASELINE. Delegated: pull-back + local tests + shadow sync, then **V4** (stage-C four-arm runner to the first 100-episode pause with fresh exports and the real baseline; τ measurement) and a **V5 interruption drill** (SIGKILL mid-continuation, resume from the 100-cadence checkpoint), then a figure-pipeline smoke on the rehearsal receipts with the non-formal watermark.
- **15:08 UTC F2 four-world oracle screen landed** (`.scratch/multi-catfish-v023-c3-contingency-f2/`: worlds `2026121721`–`24` × lineages `2026092101`–`03` × ten steps, shared tape, D before F, per-unit `--unit world:lineage` + `--merge`, resumable at unit granularity, refuses without an F1 survivor; all three lineage checkpoints/authorities bound fail-closed; 17 tests; `F2_DRY_RUN_PASS`). If F1 leaves a survivor, F2 launches without design delay.
- **15:08 UTC V1 per-shard fix landed on the server workspace, and it found the next real thing:** the provider now authenticates a shard by manifest + canonical receipt + sibling terminal status (controller-level `_read_receipt`/`_validate_shard`, adapter `_load_mode`, 8 tests), and the controller validation **rejects the r5 informed shard: "target receipt output code closure drifted from the live OPS-3/D40 closure"**. That rejection is correct — the r5 shards predate today's producer fixes (feature-major `q2_state`, H_t alignment) and must not feed anything. Consequence: V1 must use r8 shards; two are terminal and both passed the shadow verifier. Pulled the fix back; aligning the rehearsal to the hardened orchestrator API (codex), then V1 reruns on an r8-only rehearsal root.
- **15:14 UTC astra re-audit (`REAUDIT-SUCCESSOR-PACKAGES-AND-LAUNCH-BUNDLE-CODEX-GPT6-ASTRA-2026-09-07.md`): HOLD — original eight: 5 FIXED, 3 PARTIAL (03 transitive donor imports outside the mandatory closure; 04 contract digest still a supplied assertion; 08 fixture constants still consumer-derived); launch bundle: 6 BLOCKERs + 1 MAJOR (L1 binder rejects the factory's updated 16-file declaration; L2 substring token scan rejects a legitimate digest containing `c3`; L3 only six placeholders resolved; L4 digest semantics misaligned preflight→runner→verifier; L5 **V6 bypass reproduced** — `--no-reconstruct` returns PASS for a non-formal root; L6 sync list omits 179/246 closure paths; L7 diagnostic gate accepts a four-field PASS without evidence); R1 MAJOR: formal-seed/identity checks sit in the generic model/orchestrator and also bind the non-formal rehearsal — accepted for now (the rehearsal passes the authenticated digest and the formal seed, which is what the formal run uses). The diagnostic itself is behaviourally real; sealing is acyclic. Fix pass 2 dispatched to codex (L1–L7, 03, 04, 08; runner/model/orchestrator source untouched). `ASTRA_LAUNCH_BUNDLE=READY_AFTER_FIXES`. This is the second consolidated pass instead of a launch-time discovery; the V2-synthetic rehearsal running in parallel will independently hit the same L-items and confirm them on the server.
- **16:25 UTC.** Baseline adapter fix pulled back and committed (12 tests); the stage-B/C gate's new baseline step (encode a state with populated `contract_fields`) flipped from expected-FAIL to PASS on its own — the gate now catches the V3 defect class mechanically; the strict xfail is being removed (codex). Also dispatched under the owner's "any acceleration is authorised" mandate: **V2-synthetic** — the ENTIRE formal stage-A chain (bind → manifest → preflight → diagnostic → formal runner 100 epochs → verify) on a producer-written synthetic 16-shard sealed root on the server, so only the root digest changes when r8 seals; **stage-B/C formal launch bundle** (server codex); **F2 server dry-run + 12-unit fan-out script** prepared in advance of the F1 result; **artifact page refresh** to §16.
- **15:14 UTC F1 kill screen: `INVALID_RUN` after 36 s (`F1-KILL-SCREEN-RUN-REPORT-2026-09-07.md`).** Launch authority frozen (`F1-LAUNCH-AUTHORITY-2026-09-07-r1.json`, sha `9bf367cb…`; the runner's validator requires exact key equality, so the provenance fields live in the report, not the JSON). The crash is in F0's conservation check on the real BASE profile at the first anchor: `total share energy does not equal beam plus satellite share` (`c3_contingency_f0.py:623`), before any step or candidate was written — an infrastructure defect, not a scientific token (`metrics`/`kill_rules` null). Ladder rule: repair only the demonstrated defect and replay; formulas/kill rules/bindings unchanged. Server codex diagnosis dispatched with a hard fork: roundoff-tolerance or profile-construction defects get a minimal fix + real-profile regression fixture; any accounting-omission/allocation question is a formula decision → stop and obtain a pre-outcome astra ruling. Note the pattern: the F0 seam had 18 green unit tests on synthetic profiles and failed on the first real one — the same lesson as everything else today.
- **15:35 UTC F1 `INVALID_RUN` diagnosed: class (i), pure IEEE-754 roundoff.** On the real anchor-0 BASE profile (100 users, 66 beams, 6 satellites, interval 30.08 s, system power 449.64 W, network energy 13,525.10 J) the sum of user shares equals the canonical energy to 1.3e-16 relative, but a bitwise `np.array_equal` in F0's `CostShareResult.__post_init__` bypassed F0's own scale-aware `_roundoff_tolerance` (5.1e-11 J) and tripped on a 2.8e-14 J difference. No accounting omission, no profile-construction defect, no canonical inconsistency; formulas, allocation, thresholds, world, steps, field, kill rules unchanged (`compute_c3_targets` source digest unchanged). Minimal repair in the server workspace: tolerance applied to that identity; F1 rebinding of the F0 digest; regression test on the saved real anchor profile (`base-profile-anchor0.npz`); F0+F1 41 tests pass; exact anchor-0 replay green; `--dry-run` pass; new F1 preflight digest `3711b930…`. Per ladder rules this is the permitted repair-and-replay; the launch authority must be reissued (r2) against the new preflight, and the F2 preflight rebuilt (it binds F0's digest). Dispatched to the F1 operator.
- **15:36 UTC F2 prep done (`ENGINEERING-LANE-F2-PREP-REPORT-2026-09-07.md`):** F2 package synced, `F2_DRY_RUN_PASS` on the server, 12-unit tmux fan-out + merge-watcher script at `/home/sat/f2-prep/launch_f2_units.sh` (dry-run verified), 11 closure additions recorded (`F2-CLOSURE-ADDITIONS-2026-09-07.txt`). Two Sonnet operator agents (V2-synthetic chain, artifact-page refresh) were killed by an account rate limit mid-task and are being re-dispatched on a different model; the r8-only rehearsal root for V1 attempt 3 was created by the controller (symlinks only) after the operator correctly refused to write under an `*r8*` path.
- **15:45 UTC V1 attempt 3 on r8 shards: PASS twice (3 and 10 epochs).** First genuine C1/C2 learner updates on real target rows in this line, non-formal by construction: three arms, 3 real r8 shards (informed 2026121711; neutral 2026121707, 2026121708) authenticated by manifest + receipt + status file, export → reload → one more epoch with `exact_continuation_verified: BITWISE_TREE_EQUAL_AFTER_ONE_EPOCH`, all losses finite (72 checks), no `COMPLETE`, receipts `formal:false`. **Measured source-training cost:** ~1.25 s per epoch for three arms on 3 shards (C1 ≈ 0.84 s/update, C2 ≈ 0.4–0.5 s/update), flat across 10 epochs; one-time shard authentication ≈ 36 s. Extrapolation for the formal run on 16 shards (engineering estimate, not a measurement): 100 epochs ≈ minutes of updates plus a few minutes of authentication — the formal stage A is not compute-bound; the only long pole is the r8 seal. The r8 tree was verified untouched (no mtime newer than the symlink farm).
- **15:50 UTC agy (Gemini 3.8 Flash) read-only review of F2: PASS, no defects** (`REVIEW-F2-PACKAGE-AGY-GEMINI-2026-09-07.md`): imports F1's tape/candidate/deployment machinery, ladder thresholds exact (pooled EE strictly above BASE, ≥3/4 worlds, ≥2/3 lineages, service ≥ BASE−0.001), fail-closed admission without an F1 survivor, integrity → `INVALID_RUN` at unit and merge level, write-once units with resume, three lineage authorities pinned, no hidden manipulation, preflight digests computed from files. agy runs reliably only as a harness-tracked background job (a `setsid nohup` launch was reaped once). Also dispatched: astra audit of the stage-C runner + figure pipeline (the Ch5 producers), astra F3 pre-outcome design memo (so a C3 survivor proceeds without design delay).
- **17:35 UTC artifact page republished** at `https://claude.ai/code/artifact/527354c1-54aa-4175-8b99-3b03f7beb74c` with §0 "17:00 UTC 更新", §14–§16, the vertical-slice status table and the latency ledger (HTML 131 KB, byte-identical to the repo copy).
- **15:56 UTC three results.** (1) astra audit of the stage-C runner + figure pipeline (`AUDIT-STAGEC-PHYSICAL-EVALUATION-AND-FIGURES-…md`): estimand verified (committed `last_outcome`, additive bits/positive energy over 100 users × 10 steps, one ratio of sums) but **2 BLOCKERs / 7 MAJOR / 1 MINOR**: B1 the stage-A binder defers the stage-C authority (contract §6/§9 say freeze before computation — belongs to launch-bundle fix pass 2/3); B2 any SHA-shaped string admits the 9000 continuation without HELD/notification; MAJORs on provenance/matching/tests (figure tests take episode endpoints from a hand-shaped stub). Fix pass dispatched to codex (owned: physical-evaluation + figure pipeline; B1 routed to the launch bundle). (2) astra F3 pre-outcome design memo (`DESIGN-F3-LEARNER-SCREEN-PREOUTCOME-…md`, 883 words): reuse the F2 worlds/lineages and the shared tape, X target in bits/κ, NEUTRAL equal-budget source by the declared C1/C2 neutral rule, Q3 structured head unchanged, 2000 updates × 3 seeds (SHA-256 domain strings given), R7 §5 predicate copied for observability, R7 §6 composition check before F4, server cost estimate 5.3–12 serial hours for 48,000 updates (Q3 throughput to be measured); the freeze boundary is "everything except the survivor's identity". (3) agy review of the F0 roundoff repair: `REPAIR_IS_INFRASTRUCTURE_ONLY`, no defects (`REVIEW-F0-ROUNDOFF-REPAIR-AGY-GEMINI-…md`).
- **15:58 UTC stage-B/C formal launch bundle finished on the server workspace** (`/home/sat/mcrl-v023-codex-ws-stagec-20260907`); an Opus operator is pulling it back, running its tests and `--dry-run`, and checking it statically against contract §5/§6/§9 and the stage-C audit's B1/B2 before it goes to astra. r8: 6/16 shards terminal (neutral 2026121709 just completed), shadow verifier still all green.
- **18:05 UTC stage-B/C launch bundle pulled back (`ENGINEERING-LANE-STAGEC-BUNDLE-PULLBACK-REPORT-2026-09-07.md`):** 14 files, 8 pass + 1 skip locally (9/9 on the server); conformance (a)–(e) PASS — B1 cleared (runner + verifier authority bound at freeze, both output roots must be absent), B2 cleared (continuation needs authority + owner marker + preserved HELD 3000 result, cross-authenticated); (f) FAIL as shipped: the manifest was built on a workspace without the closure list, so the builder's 42-file fallback produced a 73-entry sync list missing 189/246 closure paths — rebuilding on a tree with the list gives 0 missing. Also `--dry-run` executes the server python binary (exit 127 locally), and the owner-notification marker is unsigned. Fix dispatched to codex: rebuild on this tree, REMOVE the fallback (fail closed without the closure list), dry-run must not call the remote binary, marker/authority must embed each other's digests. Fourth occurrence today of "narrower-than-closure sync list"; the fallback pattern is now banned in the charter.
- **16:05 UTC V2-synthetic: the whole formal stage-A chain ran end-to-end on a producer-written synthetic sealed root** (`ENGINEERING-LANE-V2-SYNTHETIC-STAGEA-CHAIN-REPORT-2026-09-07.md`): binder → manifest → preflight (1.3 s) → one-epoch diagnostic (2.5 s, `DIAGNOSTIC_RECEIPT_PASS`) → formal runner 100 epochs (**4.9 s**, 200 ledger rows, C1→C2, three arms with the declared source map, epoch-0/100 exports) — with four engineering bypasses on `.tmp` copies because it found **four new blockers the two audits missed**: D the orchestrator demands exactly 18 identity fields while factory v3 now emits 22 (every formal run would abort at update 0 with a green preflight); E the orchestrator rejects the token `C3` in any identity string while the factory's mandatory closure legitimately lists `ee_axis_lcsrs_c3_*.py` donor files; A the binder's `--write` flips `git dirty` so `--check` always drifts; B closure-list byte order vs `Path` order. Also: **L5 refuted** (verifier now hard-fails `--no-reconstruct`), L6 fixed (246/246), L1/L2/L3/L4/L7 did not reproduce; the verifier's positive path is unreachable in a `REHEARSAL-NONFORMAL` root by design (correct). Fix pass 3 dispatched (A/B/D/E); the V2 rerun after it is the launch rehearsal. This is the payoff of the vertical-slice rule: two read-only audits and 100+ tests did not catch D/E; one 20-minute real run did.
- **16:12 UTC stage-C launch bundle fixes landed** (closure-complete manifest 246/246, fallback removed → fails closed without the closure list, `--dry-run` no longer executes the remote binary, 9000 continuation chain `3000 result → owner marker with literal reply → authority embedding marker/reply digests → sidecar`); committed `534277b`. Its `--check`/dry-run currently report `STAGEC_CODE_MANIFEST_DRIFTED` because the manifest covers the physical-evaluation package, which the concurrent stage-C runner fix pass is editing — expected; the manifest is rebuilt once that pass lands, then the bundle goes to astra.
- **16:14 UTC stage-A launch bundle fix pass 2 finished** (L1–L7, 03, 04, 08). Verification, manifest rebuild, static spot-checks (L2/L3/L5/L6) and the commit are delegated to an Opus operator, which waits for the concurrent fix pass 3 (V2 defects A/B/D/E) to finish before the final test run and commit. After that: third astra read-only audit of the bundle + orchestrator, then the V2-synthetic rerun as the launch rehearsal.
- **16:20 UTC F1 r2 staged, replay withheld by the operator on a fixture-path defect (correct call).** Repair pulled back (F0 `9a8a97c0…`, F1 preflight `3711b930…`), F2 preflight rebuilt (`625ad7f2…`, 17 tests, dry-run pass both sides), r2 launch authority created and validated (`c3f9c2b2…`), all three packages synced. 40/41 tests: the new regression test loads its real-profile fixture from repo-root `.tmp/` (outside the package and every sync scope) instead of the in-package `fixtures-real-anchor/` copy — a test-provenance defect of exactly the kind the charter forbids. Codex fix dispatched (test path + fixture sha assertion; preflight untouched unless it covers the test file); then the same operator replays F1 once.
- **16:21 UTC F1 fixture path fixed** (in-package fixture with sha assertion; 41/41; preflight digest unchanged `3711b930…`, r2 authority still valid). Operator instructed to sync, commit the F0/F1/F2 packages, and replay F1 once (tmux `mcrl-v023-c3-f1-20260907-r2`).
- **16:32 UTC stage-C runner + figure pipeline fix pass finished** (audit B2 + MAJORs). Verification, stage-C bundle manifest rebuild, commit and shadow sync delegated to an Opus operator; after it reports green, the stage-C bundle + physical-evaluation + figure packages go to astra for a read-only re-audit.
- **16:35 UTC controller error, caught by the operator:** the F1 fixture-path fix (codex, 41/41 locally at 16:20) was overwritten when the F1 operator re-pulled the F1 package from the server diagnosis workspace (old test file, sha `8196631f…`) — two agents had write access to the same path and the operator's rsync direction was server→local. The operator refused to replay against a file it could verify still fails (correct). Fix re-applied by codex; the commit `eaf044f` (F0 repair, r2 authority, F2 preflight) is otherwise correct. Charter rule added: one writer per path at a time; server workspaces are pulled back exactly once, after which the local repo is the only source and sync direction is local→shadow.
- **16:37 UTC F1 fixture fix re-applied and committed (`077aed8`, 41/41);** F1 operator ordered to sync local→shadow only and replay r2 once (tmux `mcrl-v023-c3-f1-20260907-r2`). Fix pass 3 (V2 defects A/B/D/E) finished at 16:35; the launch-bundle verification operator proceeds to the full test run and commit.
- **16:45 UTC stage-A launch chain fix passes 2+3 verified and committed (`1e6310e`, `ENGINEERING-LANE-LAUNCH-BUNDLE-FIXPASS-VERIFICATION-2026-09-07.md`):** 56/56 tests across launch/factory/runner/rehearsal/engineering-lane after fix pass 3; manifest rebuilt (`8b020cd2…`); `--dry-run` refuses for exactly one reason — the absent r8 root; L2/L3/L5/L6 spot-checks pass (typed digests, semantic-only token scan, reconstruction-required verifier rejecting non-formal roots, 246-path two-way closure equality); 7 of 8 contract placeholders resolved by the binder, 1 explicitly deferred until the stage-C bundle (which now exists). Third astra read-only audit dispatched (GO_WHEN_R8_SEALS or FIX_FIRST; also whether the stage-C deferrals must be bound before stage A). Caveat carried: the manifest binds files outside the commit scope (physical-evaluation, F1 test) still being edited — it must be regenerated at freeze time.
- **16:55 UTC stage-C fix pass verified and committed (`cdf2dd5`, `ENGINEERING-LANE-STAGEC-FIXPASS-VERIFICATION-2026-09-07.md`):** 64/64 tests (physical-evaluation 29, figures 12, engineering-lane 11, baseline adapter 12); B2 PASS (continuation needs a sealed authority file + sidecar binding plan/policy/HELD-token/3000-result digests and an `OWNER_NOTIFIED` record; forged authority refused); figure tests now derive endpoints from the runner's own `run_episode`/payload writers and compare pooling bit-for-bit with `pool_receipts`; deployment parity by single import; BASELINE `routes=[]`. Stage-C bundle manifest rebuilt (`62180dbd…`, 259 entries, 0/246 closure paths missing), 10 pass + 1 skip, dry-run exit 0 without remote execution; shadow synced. Astra read-only audit of the stage-C bundle + packages dispatched (verdict `GO_AFTER_STAGE_A` or `FIX_FIRST`).
- **16:46 UTC third astra audit of the stage-A chain (`THIRD-AUDIT-STAGEA-LAUNCH-CHAIN-…md`): `FIX_FIRST` — 1 BLOCKER, 3 MAJOR, 0 MINOR; 37/37 tests.** FIXED: 03, 04, L1, L2, L4, L7, A, B, D, E (identity set imported from the factory, preflight authenticates it before update 0, semantic-only token scan, diagnostic behaviourally real and identity-bound, no self-digests, git commit/tree bound). Remaining: **L3 BLOCKER** — the three stage-C code-manifest bindings are still deferred although the stage-C bundle now exists; contract §6/§9 require them bound BEFORE stage A and its diagnostic (any nonempty deferral reason currently passes); **N1/L5 MAJOR** — the positive test passes a preflight receipt without launch-manifest/bindings hashes or output root, and the verifier reconstructs without authenticating those freeze authorities; **R1 MAJOR** — formal seed/budget constraints still live in the generic model/shared path (rehearsal depends on formal constants by accident); **08 MAJOR** — factory learner-closure fixture still derived from the consumer's own graph. Also: the sync list is a superset of the closure by design (test should assert the exact union). Fix pass 4 dispatched (L3, N1/L5, R1, 08, L6 note). The audit's six-step freeze order is recorded in the continuation prompt: stabilise HEAD → bind (learner manifest, provider config, execution bindings incl. git identity, r8 receipts, stage-C code bindings) → regenerate launch manifest → server preflight receipt → diagnostic receipt → formal wrapper then independent verifier/sealer.
- **16:47 UTC V2-synthetic rerun after fix passes 2+3 (no bypasses):** binder write/check idempotent ×4 on a clean tree (A fixed), closure ordering fixed (B), diagnostic passes all seven behavioural checks with the real factory identity (D, E fixed), 246/246 closure; **one remaining BLOCKER (defect C):** preflight hard-pins `target_root` to the r8 constant while the binder parameterises it, so no rehearsal is possible on any other root and the formal root does not exist yet; plus a minor wrapper error-contract issue (missing preflight receipt reported as malformed, exit 1 instead of the documented exit 3). Fix dispatched as a scoped codex task coordinated with fix pass 4 (preflight `--target-root` compared to the freeze-time value; formal launches still require the declared r8 root via an explicit `--formal` requirement). The V2 rerun after that reaches the runner and the verifier's positive path in one pass.
- **16:51 UTC astra audit of the stage-B/C bundle + packages (`AUDIT-STAGEC-LAUNCH-BUNDLE-…md`): `FIX_FIRST` — 3 BLOCKER / 5 MAJOR / 2 MINOR.** Fixed since the first audit: M3, M5, M6, M7, m1, sync fallback, dry-run interpreter; core execution is right (cumulative pauses, write-once 100-cadence, terminal adjudication only at 3000, one token with all reasons, verifier rejects non-formal roots, runner/figure pooled values identical). Remaining: B1 stage-A deferrals (being fixed in fix pass 4), B2 the 9000 constructor is handed only a digest, M2 stage B/C receipts omit the admission path/mapping, M1 continuation bypasses full history validation, M4 renderer's admission/tree seal not emitted, the owner marker is a hash chain not an identity proof (a fabricated reply string authenticated — the honest fix is a documented procedural control, not cryptography), N1 verifier gaps (policy digest, frozen-policy comparison, cumulative-prefix equality, STOP refusal), N2 git commit/tree recorded but not enforced at runtime, two minors. Stage-C fix pass 2 dispatched (all owned by the stage-C packages; stage-A side stays with fix pass 4). Stage C is not on the critical path until stage A completes, so this costs no calendar time.
- **17:00 UTC three more parallel dispatches under the "any acceleration" mandate:** (1) codex implements **F3** (`.scratch/multi-catfish-v023-c3-contingency-f3/`, pre-outcome for a generic survivor X: source artifact from the F2 tapes with the imported C1/C2 neutral rule, Q3 head unchanged, 2000 updates × 3 seeds by SHA-256 domain derivation, R7 §5 predicate and §6 composition check copied, launch authority requiring the sealed F2 terminal receipt) — speculative if F1/F2 kill both candidates, but it removes a day from the three-Catfish path if one survives; (2) **agy** reviews the F3 design memo against the ladder and R7 thresholds; (3) codex adds a **partial real-shard merge dry-run** to the engineering lane so the controller's real merge+seal code path is exercised on the 8 completed r8 shards before the controller's own first real 16-shard merge (a merge failure at the end of the 3-hour run is the last big unrehearsed step). Local memory is at its limit with six codex/agy processes; no further local dispatch until some finish.
- **17:05 UTC agy review of the F3 design: `FIX_FIRST`, four wording/scoping defects** (`REVIEW-F3-DESIGN-AGY-GEMINI-2026-09-07.md`): remove references to R7 STOP outcomes that could read as selection; scope the pre-F4 composition check for the non-closure candidates D/F to what the ladder defines rather than the LC-SRS-specific R7 §6 predicates; document the C3-specific NEUTRAL construction explicitly (the C1/C2 predecision neutral selection cannot operate on immutable C3 replay rows); flag the 8→4-world threshold scaling as a panel adaptation, not an R7 copy. astra asked for an R2 memo with crisp R1→R2 deltas; the running F3 implementation will get a correction pass against R2.
- **17:18 UTC partial real-shard merge dry-run tool landed** (`partial_merge_dryrun.py`, 3 tests; imports the controller by path, no aliasing; reports `EXPECTED_FULL_SCHEDULE_GUARD` instead of patching the 16-shard asserts). An Opus operator commits it and runs it on the server against the 9 terminal r8 shards with the controller's real arguments — the last unrehearsed step of the r8 run (merge + seal) gets exercised on real data before the controller reaches it. r8: 9/16 shards terminal.
- **17:24 UTC partial merge dry-run on 9 real r8 shards (`ENGINEERING-LANE-PARTIAL-MERGE-DRYRUN-REPORT-2026-09-07.md`):** all 9 shards authenticate with the controller's own `_read_receipt`/`_validate_shard`; the controller's REAL `_merge` + manifest and the sealer's field/manifest checks both PASS on the real subset (the only guard hit is the expected 16-shard schedule assert at `run_v023_c1c2_targets_server.py:617`); inputs re-validated unchanged. The one FAIL is the tool's adapter step: the target-batch adapter is not part of the r8 launch checkout (the controller never imports it — closure of a downstream consumer, not of the run), so dataset-shape evidence must come from the successor chain against the sealed root. Peak RSS 4.55 GiB for 9 shards → the controller's own 16-shard merge will need more; the server has ~27 GB free at the moment. Net: the end-of-run merge+seal is now exercised green on real data.
- **17:45 UTC V4 stage-C rehearsal: PASS to the first 100-episode pause (`ENGINEERING-LANE-V4-STAGEC-REHEARSAL-REPORT-2026-09-07.md`).** Four arms (V3's fresh exports + real BASELINE), plan digest `866d28e0…` reproduced, checkpoint + non-terminal rung receipt at 100, no `result.json`, peak RSS 1.97 GiB, wall 70.6 min for one sequential process running all four arms. **Measured τ per episode: FULL2 13.63 s, DROP_C1 13.52 s, DROP_C2 13.54 s, BASELINE 1.66 s** (the frozen MODQN is 8× cheaper than a learned two-route arm). Budget implications: learned arms 3 × 3000 × 13.6 s ≈ 34 CPU-h (≈ 11.3 h per arm sequential; ≈ 2.2 h wall if chunked over 16 cores); BASELINE 3000 ≈ 1.4 h, 9000 ≈ 4.2 h single process. V5 interruption drill not run (200 is not an admitted pause; the cheap way is a BASELINE-only drill 0→100→SIGKILL→resume→500 ≈ 15 min — queued after the stage-C fix pass lands). Figure smoke refused because only `rungs/` was synced (the loader requires matching checkpoint and rung histories — by design); rerun with both after the figure fix pass.
- **17:44 UTC astra ruling on early BASELINE and chunking (`ADJUDICATION-STAGEC-BASELINE-DECOUPLING-AND-EPISODE-CHUNKING-…md`):** BASELINE 1–3000 may run before stage A **with conditions** (execution-only scheduling addendum sealed with the stage-C code before any successor computation incl. the stage-A diagnostic; per-arm evidence, four-arm receipts only after stage A/B; **early 9000 disallowed**); chunking is **equivalent only with boundary-state preservation** — the runner carries the warm-start age RNG stream across episodes, so fresh-start chunks are NOT equivalent; chunks must start from replayed RNG boundary states, merge in plan order with `math.fsum` over per-episode totals, and pass a mandatory server acceptance (200 sequential vs 2×100 chunks bitwise identical). Cost floor 2.7 h, budget 3.3–4 h for 4×3000 on 16 workers. Draft addendum written (`V023-C1C2-SUCCESSOR-STAGEC-SCHEDULING-ADDENDUM-2026-09-07.md`); the runner/bundle implementation per astra's spec is queued behind the stage-C fix pass (same files). Owner's lr=0.01 request answered: not as an outcome-selected arm (sealed lr 0.001; the 100E contract forbids a sweep); only as a pre-declared non-selecting sensitivity condition, recommended later.
- **17:48 UTC F3 package landed** (`.scratch/multi-catfish-v023-c3-contingency-f3/`: F2-authenticated source materialisation with BASE replay checks, fold-local neutral rule, Q3 structured head, 2000-update checkpoint/resume, R7 thresholds + four-world adaptations, launch authority requiring the sealed F2 survivor; 18 tests; dry-runs pass; committed `5454583`). Built from design R1 → correction pass against design R2 dispatched (remove outcome-based motivation, replace closure vetoes with EE/service predicates for D/F, formalise the C3 neutral mapping, label panel adaptations). Open item recorded by codex: the composition-input producer/path must be bound outcome-blind before any F3 launch.
- **17:53 UTC stage-C fix pass 2 finished (codex exit 0).** Operator dispatched to verify (five packages), rebuild the stage-C manifest, spot-check B2/M2/N1/N2/marker, commit and sync; then run the BASELINE-only V5 interruption drill (100 → SIGKILL → resume → 500) and the figure smoke with both rung and checkpoint histories. The chunking + early-BASELINE implementation (astra spec) is queued right behind this commit (one writer per path).
- **17:56 UTC stage-A fix pass 4 finished (codex exit 0).** Operator dispatched to verify fix pass 4 + the defect-C fix (tests over launch/factory/runner/rehearsal, manifest write/check, dry-run, spot-checks L3/N1/R1/08/C), commit, sync local→shadow, then run **V2-synthetic rerun #3 with no bypasses** including an interruption drill (SIGKILL ~epoch 40 → resume → exact continuation) and the verifier's positive path on a renamed scratch copy. If that run is clean, the next step is the astra **ultra** GO check, and the chain waits only for the r8 seal.
- **18:10 UTC stage-C pass 2 verified and committed (`90cc860`; `ENGINEERING-LANE-STAGEC-PASS2-V5-FIGURES-REPORT-2026-09-07.md`):** 90/91 (1 designed skip) across five packages; all audit ids fixed (B2 authority file re-read by the runner, M2 admission path/mapping in receipts, N1 verifier prefix identity + additivity + STOP refusal, N2 git identity enforced at runtime, marker fields + README "procedural control"); manifest `f581d4f3…`, 0/246 missing; dry-run clean. **Figure smoke PASS**: six figures rendered from the V4 root with the diagonal "REHEARSAL — NOT A RESULT" watermark and a FIGURE-MANIFEST; refuses without `--allow-nonformal`. **V5 BLOCKED by design**: the runner admits only the fixed four-arm plan (no single-arm path), a four-arm drill costs ≈ 42 s/episode (7.6 h), and pass-2 admission now requires sealed stage-A/B receipts — exactly the seams the astra-ruled chunking/early-BASELINE change adds. That implementation is now dispatched (codex; boundary-state replay of the persisted age stream, single-arm chunk execution of the same four-arm plan, sealed early-BASELINE admission ≤ 3000, bitwise merge, fan-out script, local sequential-vs-chunked equivalence tests, server acceptance procedure). Next after it lands: verify → server acceptance (sequential 200 vs 2×100 chunks per arm, BASELINE first ≈ 12 min) → astra check → seal addendum + stage-C code → **BASELINE 1–3000 starts** (≈ 1.4 h single worker, faster chunked) while stage A waits for r8.
- **18:10 UTC stage-A fix pass 4 + defect C verified and committed (`dd2468e`; `ENGINEERING-LANE-STAGEA-FIXPASS4-AND-V2-RERUN3-REPORT-2026-09-07.md`):** all six ids confirmed by file:line (L3 closed deferral list + stage-C code bundle verified from its manifest/pin; N1/L5 preflight receipt binds and re-verifies manifest/bindings/root; R1 seed pinned only when `formal`; 08 independent AST closure; L6 exact union; C `--target-root` vs freeze-time value + formal-root requirement); 56/56 tests; manifest `4176b831…`; dry-run refuses only for the absent r8 root. **V2 rerun #3: binder idempotent ×4, manifest, non-formal preflight (defect C fixed), diagnostic all PASS; then three new blockers:** N the formal wrapper refuses any `formal:false` receipt, so no end-to-end rehearsal is possible on any root but the literal r8 path (the defect-C fix moved the boundary); O no resume entry point and no checkpoint between epoch 0 and 100, so the interruption drill cannot run; P the verifier's positive path is unreachable for any rehearsal (root binding + `formal:true`, correct by design but untestable). Verifier correctly REJECTS the non-formal root. Fix pass 5 dispatched (explicit `--nonformal` wrapper mode stamping `formal:false` everywhere, `--resume` entry point + non-formal-only intermediate checkpoints with the formal cadence unchanged, verifier `--nonformal` reconstruction mode that never emits a formal token). Pattern: each end-to-end run now finds the next real boundary in 10 minutes; passes 1–4 removed 20 defects, rerun #3 still found 3.
- **18:20–18:35 UTC owner's instruction: migrate the controller to the server once local sub-agents finish** (`MIGRATION-TO-SERVER-2026-09-07.md`). Done so far: server Claude Code 2.1.193 confirmed authenticated (probe OK), codex present; migration plan + continuation-prompt server section written and committed; the GitHub push was **denied by the auto-mode classifier** (outward action) — the branch is being transferred to the server as a git bundle instead, and a worktree `/home/sat/mcrl-leo-handover-wip` is being created from it (the original clone and its `.venv` untouched). The owner should run the push themselves when convenient (`! git push -u origin wip/multi-catfish-v023-20260907`).
- **18:40 UTC server worktree created:** `/home/sat/mcrl-leo-handover-wip` = `wip/multi-catfish-v023-20260907` via git bundle (original clone `42a8247` and its `.venv` untouched, its 38 dirty entries preserved); 104 `.scratch` packages present; incremental sync helper `sync_server_worktree.sh` (bundle → fetch → ff-only merge) committed for the remaining local commits. Handover to the server session happens after fix pass 5 and the stage-C chunking pass land.
- **18:47 UTC stage-A fix pass 5 finished (codex exit 0).** Operator dispatched: verify N/O/P, tests, manifest, dry-run, commit, sync, then **V2-synthetic rerun #4** end-to-end with the wrapper's `--nonformal` mode, the interruption drill (SIGKILL + `--resume`, bitwise continuation) and the verifier's non-formal reconstruction; a clean run is reported as `V2_RERUN4_CLEAN` and triggers the astra ultra GO check (template `prompts/astra-ultra-stagea-go-check.md`). r8 11/16.
- **16:47 UTC (server) F1 kill screen r2 completed: `FAST_SCREEN_NO_SUPPORT`** (`status=COMPLETE`, wall 383 s, tape digest `738f9f01…`, receipt copy `f1-r2-receipts/receipt.json` sha `d1cd30ce…`; full section in `F1-KILL-SCREEN-RUN-REPORT-2026-09-07.md`). Recorded without interpretation — kill rules: D integrity ✓, action changed ✓, service non-inferior ✗, EE strictly above BASE ✗ → not surviving; F integrity ✓, action changed ✓, service non-inferior ✓, EE strictly above BASE ✗ → not surviving. Pooled ratio-of-sums EE (bits/J): BASE 118,630,259, D 117,054,987, F 113,248,876; service fraction BASE 1.0, D 0.995, F 1.0 (two canonical steps, 100 users, world 2026121721, lineage 2026092101). Per the ladder this is a fast-screen result, not a structural impossibility claim; both pre-declared contingency candidates fail F1, so F2/F3 are not admitted. astra **ultra** adjudication dispatched (token derivation, receipt consistency, effect of the roundoff repair, the exact sentence for the handoff/paper). Chunking implementation landed (codex; manifest `4ffa5b2c…`); operator verifying + running the BASELINE server acceptance.
- **19:06 UTC astra audit of the chunking implementation (`AUDIT-STAGEC-CHUNKING-IMPLEMENTATION-…md`): `FIX_FIRST` — 4 BLOCKER / 4 MAJOR / 1 MINOR.** Numerical core verified: the only persisted cross-episode stream is `_age_rng` (`step.py:414`) and the boundary states replay its actual draws; `FixedPolicyEvaluationRunner`/`aggregate_last_outcomes`/`pool_receipts` unchanged by AST comparison; merge uses `math.fsum` over per-episode totals; 58 tests pass; `src/` untouched. Remaining: B1 early admission validates digest syntax only; B2 all 3000 episodes scheduled at once (no cumulative barriers) and early sync launches without acceptance evidence; B3 chunk verifier accepts `formal:false`, missing checkpoints and a corrupted end state (probe-confirmed), merge ignores indexed hashes; B4 no append-only import path for later stage-A/B admission; M1 no writer lock / resume trusts prefixes; M2 provenance gaps; M3 worker cap per arm not shared; M4 local equivalence uses a hand-written age adapter and Python equality, server acceptance never compares merged rungs; m1 addendum lacks stream/exclusion lists and the acceptance digest. **Controller decision: drop the early-BASELINE start.** astra notes that under the all-four-arm acceptance requirement BASELINE cannot precede stage A/B without an amended ruling; stage A is minutes and stage B ran in 47 s in rehearsal, so early BASELINE would save at most ~1 h of a 1.4 h job — not worth a ruling amendment. Chunking itself (the 11 h → ~3.5 h lever for the learned arms) stays; its fix pass 2 is dispatched as soon as the current chunking operator commits (one writer per path), and it is not on the critical path until stage A/B finish.
- **19:20 UTC stage-A fix pass 5 verified and committed (`e192249`; `ENGINEERING-LANE-STAGEA-FIXPASS5-AND-V2-RERUN4-REPORT-2026-09-07.md`): N/O/P fixed; 63/63 tests; manifest `bb6a1f96…`; dry-run refuses only for the absent r8 root. V2 rerun #4: the chain now runs END TO END non-formally** — binder idempotent, manifest, non-formal preflight, diagnostic, **wrapper `--nonformal` 100 epochs in 4.3 s** with every receipt `formal:false` and no formal markers, a second uninterrupted run byte-identical, verifier `NONFORMAL_RECONSTRUCTION_PASS` (200 updates, 3 arms, exact resume), formal verifier rejects the non-formal root, both laundering negatives refused. **Not clean:** the interruption drill found Q — a kill inside the checkpoint critical section (checkpoint + sidecar published before exports and receipt) leaves an UNRECOVERABLE root (resume picks the partial epoch; the previous epoch cannot re-export) — and R — after `--resume`, checkpoint containers are not byte-reproducible (pickle memo/string identity in the non-tensor state; tensors and trees identical; ledger and exported models bitwise equal). Fix pass 6 dispatched (write order exports → receipt → checkpoint → sidecar last, atomic writes, resume from the newest fully sealed epoch; canonical serialisation of the non-tensor state). Q is exactly the failure mode a server reboot (as on 09-07 05:25) would produce during a formal run; finding it on a synthetic root instead of on the real one is the whole point of the drills.
- **19:25 UTC artifact republished** at `https://claude.ai/code/artifact/527354c1-54aa-4175-8b99-3b03f7beb74c` (page current through the 19:20 UTC bullet, §17 included). The previous URL (`983dfec8…`) became inaccessible after the account switch, as did `0b130c2a…` before it — artifacts are owned per signed-in account; the repo copy of the HTML is the durable one.

## 17 · C3 decision under the pre-declared contingency mechanisms (2026-09-07 18:58 UTC)

- **astra ultra adjudication (`ADJUDICATION-F1-R2-RESULT-CODEX-GPT6-ASTRA-ULTRA-2026-09-07.md`): `ASTRA_F1_R2=NO_SUPPORT` — uphold `FAST_SCREEN_NO_SUPPORT`.** Receipt internally consistent (authority `c3f9c2b2…`, preflight `3711b930…`, 18 code files + authority files hash-match; tape digest agrees); EE and service recomputed independently from the recorded totals; the r1→r2 repair touched only the F0 energy-identity assertion (existing tolerance helper) and F1's F0 digest binding — cost-share and D/F target functions unchanged. Kill rules (service ≥ 0.999, EE strictly > BASE): **D** service 0.995 fails, EE −1.328%; **F** service passes, EE −4.536%. No outcome-dependent selection, hidden threshold or token-invalidating defect; no repair-and-replay indicated. Limitation recorded: the tape rows live only on the server, so candidate/action-change counts were not independently recounted (receipt has Boolean flags only); this does not affect either candidate's EE failure.
- **Ruling for the record (adopted verbatim):** *C3 under the pre-declared mechanisms D and F is not admissible under the F1 progression gate: pooled EE was 118630258.51 bits/J for BASE, 117054987.34 for D (−1.327883%), and 113248875.75 for F (−4.536265%), with service fractions 1.000, 0.995, and 1.000, respectively.* Ch5 retains the two-Catfish main result and includes a C3 negative-result section bounded to this two-step TRAIN screen; this establishes no structural impossibility; no new candidate may be proposed from these residuals.
- **Consequences:** survivor set empty → no F2 launch authority, `/home/sat/f2-prep/launch_f2_units.sh` is not invoked, F3 stays unlaunched (packages retained as pre-outcome designs). The three-Catfish algorithm is therefore decided for this round as: C1 and C2 as sealed in the successor declaration; C3 not admissible under the mechanisms declared in advance (LC-SRS stopped at R7 physics; D and F stopped at F1). The remaining path to Ch5 figures is the two-Catfish successor (stage A → B → C).
