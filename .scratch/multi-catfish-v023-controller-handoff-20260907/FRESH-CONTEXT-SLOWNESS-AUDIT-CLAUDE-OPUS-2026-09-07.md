# Fresh-context slowness audit — why 15 days produced no learner update

Reviewer: Claude Opus 5, fresh context, read-only. Date: 2026-09-07.
Scope: process and engineering economics only. No scientific claim; no proposed threshold,
seed, world, formula or acceptance change; `STOP_PHYSICS_R7` is treated as valid and binding.

---

## A. Structural causes of slowness

### A1. The project abandoned version control on day 1 — and rebuilt it by hand, badly

`git log -1` = **2026-08-23**. Every day of Multi-Catfish work since is outside git:
`git ls-files` = 174 tracked files; `git status --porcelain` = 537 entries (501 untracked);
**106 files under `src/` have never been committed** — that is the entire `ee_axis_*` family
(the C1/C2/C3 heads, the three-route carrier, the V0.14 head, the verifiers). `.gitignore`
excludes only `.venv`, `__pycache__`, `*.pyc`; nothing was ignored on purpose.

What replaced it: 96 sibling directories under `.scratch/` (1.0 GB), **587,662 lines** of
untracked `.py`/`.sh`, **447 copies** of `ee_axis*.py` across parallel trees, **55**
hand-built `*MANIFEST*` files, **121** `verify*` files, **30** launchers, **30** preflights,
**14** sealers — 68,434 lines of launcher/preflight/sealer/verifier glue alone. The variants
are near-clones: `sync_launch_…_r5.sh` vs `…_r6.sh` differ by 166 of 477 lines.

This is the origin of the audit's own root cause #2. The "single-tree provenance assumption"
broke and needed DECISION A precisely because there is **no commit object that names a code
state** — so the factory hashes 169 files by hand and the 18-vs-51 closure had to be adjudicated.
Git gives immutable content-addressed snapshots, cross-version diffs, bisect and worktrees for
free, and sealing a commit SHA is *stronger* than sealing a hand-built manifest. One CODE-MANIFEST
was rebuilt five times in one day (`93d5f03d`→`8a290eee`→`cd0421b9`→`dc5ef936`→`79a181a3`).
**Cost: the enabling substrate for A2 and A3; directly, days of manifest/package assembly.**

### A2. Producer/consumer contracts are string literals and array layouts, discovered only by real compute

Thirteen integration defects of one shape, each hidden behind the previous. R7 verifier (§1, §2):
array domain → sibling import → pair-profile broadcast → missing `pair_source_key` → list-typed
`c2_diagnostic` → float32/float64 `q2_delta`. C1/C2 pipeline (§1b, §12): scope literal → `.rows`
on a dict (`generate_v023_c1c2_targets.py:1315`) → claim-ceiling literal → `q2_state` action-major
vs feature-major → `ops3_future_d2_indices` horizon length → sealer literal → merged-receipt
fields. All were invisible to synthetic-fixture tests (`tests/test_w201` derives expected hashes
from the verifier's own constant and loads a verifier copy 282 diff-lines from the frozen file),
and each surfaced only after 40 min–3 h of real compute.
**Cost: r4→r8 (five C1/C2 launches, none sealed) + R7-I1 R1→R4 = ~11 real runs. ≈ 30–35 h server
wall plus repair/relaunch cycles. The R7 decision was determinable at 2026-09-06 15:10 and was
read at 2026-09-07 12:54 — 22 h of pure verifier-crash latency (§13).**

### A3. No cheap falsification tier — every scientific question is asked at full scale first

The LC-SRS gate is 8 worlds × 3 learner seeds × 100 users × 10 steps × 28 actions × 32 fading
draws × 2,000 updates × 8 LOWO folds (`…R7-BALANCED…md:37–59`), plus seven launch/relaunch
decisions R1→R7 over two days. The ladder
(`V023-C3-RAPID-CONTINGENCY-LADDER-PREOUTCOME-2026-09-06.md`) shows the alternative: **F1 = one
world, one lineage, two steps, one shared tape** — order-of-magnitude cheaper, pre-outcome,
with fixed kill rules. It was written **2026-09-06, day 14**, after the expensive gate was
already running. MEMORY.md records ten STOP/REJECT/FAIL rulings between 09-01 and 09-07
(C3 STOP, C3_CONTEXT_FAIL, PNFE RETRY, V0.14 gate STOP, STOP_THREE_HEAD, V0.15 REJECT,
STOP_C3_STRUCTURALLY, V0.18 STOP, V0.20 REVISE, STOP_PHYSICS_R7) — **ten mechanisms killed, each
at full price.**
**Cost: the dominant term. Most of 09-01 → 09-07, ≈ 6 days.**

### A4. Design-document inflation outrunning experiment throughput

66 `MULTI-CATFISH*` docs in `docs/` over 8 days (peak 22 on 09-02); 13 version families V0.3…V0.23;
121 docs / 21,077 lines total; 409 `.md` under `.scratch/`. Package creation is *accelerating*:
33 new `.scratch` packages on 09-06 and 22 on 09-07 — 55 of 96 in the last two days. That is the
signature of thrash. Each version costs a contract + prereg + adjudication + review before any
compute. Adjudication, not CPU, is the serial bottleneck.
**Cost: ≈ 1–2 days of controller/reviewer time.**

### A5. Serial execution where parallel was free

The r5/r6 controller blocks on its first child, so a sibling failure is invisible until that child
exits (§12) — r6 lost ~95 min × 15 shards. 16 shards at 4.8 GB RSS (~77 GB of 91 GB) blocked
concurrent read-only diagnostics. An unplanned reboot (05:25 UTC) killed a 40-min run, uncheckpointed.
**Cost: ≈ 6–10 h.**

---

## B. Is there a core problem nobody has caught? **Yes.**

**The freeze discipline that is correct and mandatory for the *confirmatory* claim was applied
to *every* activity — exploration, integration, plumbing, debugging — where the owner's rules
never required it and where it costs 2–3 orders of magnitude too much per bit of information.**

The owner's rules forbid outcome-selected tuning, outcome-selected reruns, and rewriting sealed
artifacts. They do **not** forbid: version control, unlimited read-only rehearsals against real
artifacts, cheap pre-declared kill screens, or static contract checks. The project behaved as if
they did. Consequences: no git (A1); no dry-run tier, so integration bugs cost real compute (A2);
no screening ladder, so ten mechanisms died at full scale (A3).

The proof is in the project's own last 24 hours. Once read-only probes against **real** shards were
finally built, defects #4, #5 and #6 were each found in **~1 minute**
(`PROBE-CONTROLLER-POSTSHARD-RESULT`, `PROBE-Q2-DELTA-PRECISION-RESULT`) instead of a 40-min
inventory run, and `dryrun_v023_c1c2_controller_postshard.py` proved the r6 shard authenticates
offline before r7 was launched. That technique was discovered on day 15; it should have been the
first thing built. The audit's stated root causes are symptoms; the missing engineering tier is the cause.

---

## C. Top 5 changes for the next 72 hours

**1. Put everything in git today. — ENGINEERING-PARALLEL / non-heavy — codex implementation model, controller supervises.**
`git add` the 106 untracked `src/` files, the 35 modified tracked files, `.scratch/` and
`artifacts/` on a branch; then one commit per package going forward. Bind future freezes to
**commit SHA + tree hash** *in addition to* existing manifests.
*Must NOT*: modify, reformat, renumber, relabel or re-hash any sealed artifact, receipt or
frozen manifest; must not rewrite history; must not change any file content while adding.

**2. Make an offline real-artifact dry-run mandatory before any launch. — ENGINEERING-PARALLEL / non-heavy — codex.**
Generalize `dryrun_v023_c1c2_controller_postshard.py` into one reusable tool: authenticate →
merge → seal against **real** artifacts in a scratch root, non-fail-fast, reporting every check
PASS/FAIL/BLOCKED. No launcher runs until its dry-run is green.
*Must NOT*: write into any sealed root; open TEST; produce any EE or efficacy number; alter
producer code.

**3. Import producer-owned constants; static-check the rest. — ENGINEERING-PARALLEL / non-heavy — read-only reviewer enumerates, codex implements.**
Every claim-ceiling string, schema literal, array layout and horizon constant must be imported from
the module that writes it, with a parity test, plus a static consumer/producer contract scan across
the successor chain (factory v3, two-route runner, target adapter, sealer).
*Must NOT*: change any numeric value, sign, threshold or tolerance — only prove consumer equals
producer by import.

**4. Run astra's timed vertical slice before freezing the successor execution section. — ENGINEERING-PARALLEL / heavy (Ubuntu server) — codex builds, controller declares the claim ceiling first.**
v3 load → one source epoch → export/reload/resume → one matched four-arm world, with per-phase
timings. This is the only real measurement of source cost and τ.
*Must NOT*: emit any EE comparison, be used to select any threshold, world, seed or budget, or
be cited as efficacy. Claim ceiling: plumbing and timing only.

**5. Freeze the C1/C2 successor contract now; stop writing new design documents. — PROCESS — controller.**
Apply astra's seven `FREEZE_AFTER_FIXES` defects (already done in R2) plus the missing-declaration
list, freeze the scientific section immediately, and bind r8 digests at consumption rather than
waiting for the seal to start the freeze.
*Must NOT*: widen scope to C3; must not re-open any settled parameter; must not add a new version
family before the first learner update exists.

---

## D. Top 3 structural changes for the following weeks

**D1. Cheap-kill-first becomes the only admission path.** No mechanism gets a full-scale gate until
it survives pre-declared cheap rungs (the pre-outcome ladder F0→F1→F2→F3→F4 already qualifies, dated
before any R7 outcome). Not outcome tuning: rungs, worlds, lineages and kill rules are fixed in
advance and survivors are not selected by score.

**D2. One codebase, one parameterised harness.** Collapse 96 packages / 30 launchers / 121
verifiers / 55 manifests into one launcher, one verifier library and per-experiment configs,
versioned by commit and sealed by SHA. The per-experiment glue rewrite is the single largest
recurring engineering cost in this repository.

**D3. Institutionalise two lanes.** An ENGINEERING lane — unlimited, read-only, unfrozen, running
continuously against real artifacts (dry-runs, contract scans, timing rehearsals, kill-screens
declared in advance) — and a SCIENCE lane — frozen, one shot, sealed, adjudicated. Today
everything sits in the science lane, which is why debugging costs the same as an experiment.

---

## 中文摘要（給使用者）

**(B) 有一個沒人抓到的核心問題，答案是「有」。** 真正的病灶不是 verifier 的六個缺陷，也不是
單一樹 provenance——那些都是症狀。病灶是：**「凍結／封存」這套本來只該用在「確認性科學宣稱」
的紀律，被套用到了所有活動上**，包括探索、整合、接線與除錯。你的科學規則從來沒有禁止版本控制、
沒有禁止對真實產物做唯讀彩排、也沒有禁止事先宣告的便宜 kill screen；但專案的做法等於默認它禁止。
後果有三：(1) 從 2026-08-23 之後就沒有再 commit，`src/` 底下 106 個檔案從未進版控，取而代之的是
96 個 `.scratch` 複本、58 萬行未追蹤程式碼、447 份 `ee_axis*.py`、55 份手工 manifest——git 免費提供
的東西被手工重建且做壞了；(2) 沒有便宜的 dry-run 層，所以 13 個 producer/consumer 字面／版面不合
每一個都要花 40 分鐘到 3 小時的真實計算才會現形，R7 的答案 09-06 15:10 就已寫在磁碟上，卻被藏了
22 小時；(3) 沒有便宜的篩選階梯，所以 09-01 到 09-07 之間十個機制全部以「全尺寸 gate」的價格被殺死，
而那份便宜的 ladder 設計是第 14 天才寫出來的。證據就在專案自己最後一天：改用對真實 shard 的一分鐘
唯讀 probe 之後，第 4、5、6 個缺陷各只花一分鐘就找到。

**(C) 未來 72 小時的五件事：** ①今天就把所有東西進 git（工程並行，codex 做；**不得**改動任何已封存
產物或重寫歷史）；②把 `dryrun_…_postshard.py` 通用化成「所有 launcher 上機前必過的真實產物離線
彩排」（工程並行；**不得**寫入封存 root、不得開 TEST、不得產生任何 EE 數字）；③所有 claim ceiling
字串、schema、陣列版面一律從 producer 模組 import，並加靜態契約掃描（工程並行；**不得**更動任何數值、
符號或容差）；④在凍結後繼契約的執行段之前，先跑 astra 的計時垂直切片（heavy，伺服器；**不得**輸出
任何 EE 比較或被用來選門檻）；⑤現在就凍結 C1/C2 後繼契約、停止再寫新的設計文件（流程，controller；
**不得**擴張到 C3）。
