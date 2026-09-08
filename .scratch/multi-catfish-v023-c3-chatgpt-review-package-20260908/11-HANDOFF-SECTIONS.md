# 11 — Verbatim extracts from the controller handoff (2026-09-07)

Source: `.scratch/multi-catfish-v023-controller-handoff-20260907/HANDOFF-EXECUTION-CLOSURE-AUDIT-2026-09-07.md`
(630 lines). Four passages are reproduced **verbatim and unedited**, in the source document's own
order: the `## 0` update paragraph beginning "**13:05 UTC 更新**", `## 2` (root causes),
`## 13` (the sealed R7 STOP) and `## 17` (the C3 decision under the pre-declared contingency
mechanisms). Nothing else from that document is included; ellipses are never used inside a
passage. The source document's own claim ceiling applies: **execution readiness only** — no TEST
split was opened, no learner update and no episode training happened, and its benchmark timings
and loss values are execution facts, not scientific ones.

---

## Extract 1 — from `## 0. 摘要（給使用者）`: the 13:05 UTC update paragraph

**13:05 UTC 更新（compact 後）：R7 gate 已於 12:54 UTC 封存，integrity `VERIFIED`，但科學裁定為 `STOP_PHYSICS_R7`。** 決定性條件是 `physical_signature`：兩個知情 Catfish 的 11 profile 對 00 profile 的 pooled ratio-of-sums EE 為 −0.049%，8 個開發世界只有 2 個為正（預先登錄門檻：嚴格正且 ≥4 個世界）。teacher composition（+0.335%）、held-out learner（balanced accuracy 0.705 對 placebo 0.626）、C1/C2 context 都通過；但 learned composition（−0.660%，2 個世界為正）、topology consistency（0.536，門檻 0.8）、harmful partial（超過 0.05 上限）也沒過——即使物理條件過了，依 `adjudicate_section14_r7` 的優先序也只會得到 `REDESIGN_INTERFACE_R7`，不是 GO。Provider factory 已在伺服器上實測拒絕這個 root（`R7 final result c3_decision is not the frozen GO value`），因此 100E 五臂來源訓練在凍結契約下無法啟動；這是 gate 的設計，不是缺陷。契約 §7：有效的非 GO 結果結束 LC-SRS successor 路線，不得放寬門檻、換種子／世界、依結果重跑或自動升級 CSE/EC；§8：100E 篩選只在 GO 之後開始。所以「為什麼一直沒辦法開始訓練」的完整答案是：(1) 六個 verifier 對 writer 的缺陷把 gate 的裁定藏了約 22 小時（source 陣列 09-06 15:10 就已存在）；(2) 裁定一出來，是預先登錄的科學 STOP。執行鏈上已無任何整合邊界擋在程式與啟動之間；擋住的是科學 gate 本身。接下來需要的是設計層決定（由使用者決定），不是再修執行鏈。細節見 §13、`R7-STOP-PHYSICS-RESULT-2026-09-07.md` 與 `r7-sealed-receipts/`；codex gpt-6-astra 的唯讀裁定（推導有效性、六個修正是否可能影響物理條件、契約允許的下一步）已派出，完成後附於 `ADJUDICATION-R7-STOP-PHYSICS-CODEX-GPT6-ASTRA-2026-09-07.md`。r8 C1/C2 目標產生（自有 claim ceiling，與 R7 裁定無關）照常進行。

---

## Extract 2 — `## 2. Root causes (why the project keeps looping)`

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


---

## Extract 3 — `## 13 · R7 gate sealed 12:54 UTC`

## 13 · R7 gate sealed 12:54 UTC — integrity VERIFIED, decision STOP_PHYSICS_R7 (scientific STOP)

- **Verified.** The R4 domain-repair controller finished `V023_R7_DOMAIN_REPAIR_R4_PASS source_loads=8 composition_loads=48 pairs=688 c2_rows=688` and the sealer wrote `result.json`, `verification.json`, `MANIFEST.sha256`, `COMPLETE` into `/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1` at 12:54:16 UTC. `result.json`: `integrity_status=VERIFIED`, `status=PASS_FINAL_INTEGRITY`, `c3_decision=STOP_PHYSICS_R7`, `no_rescue=true`. Local copies: `r7-sealed-receipts/` (result.json sha `dfcc70e441e2ec2c3be20608124c704c6d5c80b4d902a1aa7b75328faadbd2f7`, MANIFEST.sha256 sha `63ecb5a8ec08f8fe89c5e656871fd019493e0eb6fdb7777e152c9fef85b8c01f`, receipt status `PASS_R7_FINAL_VERIFIER_DOMAIN_REPAIR_R4`, corrected verification sha `94915623…`). Per-world numbers: `R7-STOP-PHYSICS-RESULT-2026-09-07.md`.
- **Derivation (verified against `r7_balanced_successor_gate.py:adjudicate_section14_r7`).** Precedence: integrity → pair_coverage → (mechanics ∧ physical_signature ∧ teacher_composition) → (target_support ∧ held_out_learner ∧ world_stability) → (action_exposure ∧ literal_11 ∧ harmful_partial ∧ topology_consistency ∧ learned_composition ∧ service) → GO. `physical_signature=false` decides the token: pooled ratio-of-sums EE of the 11 profile versus 00 is −0.049% (`pooled_joint_direction=-1`) and only 2 of 8 worlds are positive (threshold: strictly positive and ≥4). `mechanics` (688/688) and `teacher_composition` (+0.335% vs baseline, 5 worlds) passed. Also false at lower precedence: `learned_composition` (−0.660% vs baseline, 2 worlds), `topology_consistency` (379/707 = 0.536 < 0.8), `harmful_partial` (`verify_v023_lcsrs_final.py:1668` — predicate true only when the harmful-partial fraction ≤ 0.05; it is false). Had physics passed, the token would have been `REDESIGN_INTERFACE_R7`, not GO. Held-out learner (balanced accuracy 0.705 vs placebo 0.626, spearman 0.839, 8/8 world wins), world stability, C1/C2 context all passed.
- **Effect on training (verified).** The read-only R7-half rehearsal of the provider factory on `/home/sat/mcrl-v023-learner-rehearsal-checkout-20260907` (12:58 UTC) returned `R7_HALF_FAIL: V023PostR7ProviderFactoryError: R7 final result c3_decision is not the frozen GO value`. The V2 100E launcher's seed-first R7 closure check and factory preflight therefore stop before any learner is constructed. Contract `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-SUCCESSOR-GATE-CONTRACT-R7-BALANCED-2026-09-06.md` §7: a valid non-GO result ends the LC-SRS successor route; no second metric revision, threshold relaxation, seed/world replacement, rerun selected by outcome, or automatic promotion of CSE/EC; a later CSE/EC experiment needs its own already-declared formula and falsifier. §8: the 100-episode five-arm screen begins only after GO.
- **Timing (verified).** The source arrays that determine `physical_signature` were written on 2026-09-06 15:10 (`source-stage-verification.json`, `VERIFIED_SOURCE_STAGE`, decision fields null by design). The decision was therefore determinable ~22 h earlier and was hidden only by the verifier crash chain (defects 1–6, §2). This completes the audit question: the execution chain no longer has any integration boundary between code and launch; the remaining boundary is the pre-registered science gate, which says STOP.
- **Controller action per brief.** Genuine scientific STOP → the execution mandate for the R7 → 100E line ends here. Receipts preserved; no R5, no factory or manifest rewrite, no relabelling. Dispatched 13:05 UTC: codex gpt-6-astra read-only adjudication (token derivation, whether any of the six verifier-side corrections could touch the physics predicates, contract-consistent options, what may be recorded as motivation without selection on outcome) → `ADJUDICATION-R7-STOP-PHYSICS-CODEX-GPT6-ASTRA-2026-09-07.md`.
- **Unaffected and continuing.** r8 C1/C2 target generation (own claim ceiling `TRAIN_PHYSICAL_TARGET_GENERATION_ONLY…`, independent of the R7 decision) keeps running; its sealed targets remain usable by any successor that keeps C1/C2. codex finished: V2 bundle repointed to `-ops3-r8` (60 tests, dry-run PASS at its time), runner test-debt cleared (7 pass; runner module untouched, mtime 04:20 UTC), one-world plumbing rehearsal script staged (`rehearsal_v023_one_world_plumbing_fresh_models.py`, expected exit 3 = fail-closed untrained-export blocker; not run).
- **What the user must decide.** Whether to declare a successor experiment (fresh contract with its own formula and falsifier, declared before any computation and not selected on R7 residuals), or to redesign C3 / the three-Catfish composition. Nothing in the current frozen chain can be re-run to a GO.
- **Independent adjudication (codex gpt-6-astra, read-only, 13:09 UTC; `ADJUDICATION-R7-STOP-PHYSICS-CODEX-GPT6-ASTRA-2026-09-07.md`).** VERIFIED there: local receipt hashes match `MANIFEST.sha256` and `COMPLETE`; `STOP_PHYSICS_R7` is the mandatory token and `physical_signature` is the only predicate deciding it (physics alone passing would yield `REDESIGN_INTERFACE_R7`); the `harmful_partial` FAIL rendering is correct (passing guard = fraction ≤ 0.05); each of the six verifier-side corrections is traced to its scope and none changes the inputs or comparisons of `physical_signature`, `mechanics`, `teacher_composition`, `learned_composition`, `topology_consistency`; the factory refusal is a frozen admission rule (factory v2 lines 653–657, 100E contract lines 47–65). Recommendations: close LC-SRS R7 with evidence preserved; let r8 C1/C2 finish under its own claim ceiling and reuse authenticated targets and the 448-D Q2 head only under a fresh bounded handoff; CSE/EC or any new C3/composition design needs its own already-declared formula, falsifier and outcome-independent eligibility before computation; report the R7 aggregates as falsified-prediction evidence, never as a selector for the next mechanism. Decision line adopted: *Accept sealed `STOP_PHYSICS_R7`; the LC-SRS successor and its conditional 100E execution mandate end, with immutable evidence preserved.* The user must decide whether to close this direction or issue a fresh handoff for an independently justified, contract-eligible experiment.


---

## Extract 4 — `## 17 · C3 decision under the pre-declared contingency mechanisms`

## 17 · C3 decision under the pre-declared contingency mechanisms (2026-09-07 18:58 UTC)

- **astra ultra adjudication (`ADJUDICATION-F1-R2-RESULT-CODEX-GPT6-ASTRA-ULTRA-2026-09-07.md`): `ASTRA_F1_R2=NO_SUPPORT` — uphold `FAST_SCREEN_NO_SUPPORT`.** Receipt internally consistent (authority `c3f9c2b2…`, preflight `3711b930…`, 18 code files + authority files hash-match; tape digest agrees); EE and service recomputed independently from the recorded totals; the r1→r2 repair touched only the F0 energy-identity assertion (existing tolerance helper) and F1's F0 digest binding — cost-share and D/F target functions unchanged. Kill rules (service ≥ 0.999, EE strictly > BASE): **D** service 0.995 fails, EE −1.328%; **F** service passes, EE −4.536%. No outcome-dependent selection, hidden threshold or token-invalidating defect; no repair-and-replay indicated. Limitation recorded: the tape rows live only on the server, so candidate/action-change counts were not independently recounted (receipt has Boolean flags only); this does not affect either candidate's EE failure.
- **Ruling for the record (adopted verbatim):** *C3 under the pre-declared mechanisms D and F is not admissible under the F1 progression gate: pooled EE was 118630258.51 bits/J for BASE, 117054987.34 for D (−1.327883%), and 113248875.75 for F (−4.536265%), with service fractions 1.000, 0.995, and 1.000, respectively.* Ch5 retains the two-Catfish main result and includes a C3 negative-result section bounded to this two-step TRAIN screen; this establishes no structural impossibility; no new candidate may be proposed from these residuals.
- **Consequences:** survivor set empty → no F2 launch authority, `/home/sat/f2-prep/launch_f2_units.sh` is not invoked, F3 stays unlaunched (packages retained as pre-outcome designs). The three-Catfish algorithm is therefore decided for this round as: C1 and C2 as sealed in the successor declaration; C3 not admissible under the mechanisms declared in advance (LC-SRS stopped at R7 physics; D and F stopped at F1). The remaining path to Ch5 figures is the two-Catfish successor (stage A → B → C).
