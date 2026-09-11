補充 owner direction：Amendment 6 的 development-first 方向正確，但現在再把 **time-to-first-gradient** 縮短。這不是放寬任何 Amendment 4/5/S1 gate，而是調整 E0 development 的執行粒度。

先注意：上一次 session 被 quota 中斷時，`.scratch/dev-training/PROGRESS.md` 已經落後於 filesystem。**不要依 PROGRESS checkbox 判斷哪些程式還沒寫；先看實際 worktree/git/files/processes，再把 PROGRESS 修正成真實狀態。不得重做已存在的工作。**

我獨立檢查到的 checkpoint，請你先重新驗證：

* B1 engineering core 已是 commit `63b02dc0`.
* `/home/u24/papers/mcrl-leo-handover-dev` 已存在，base = `63b02dc0`.
* DEVHARNESS 已有未 commit 的 `cf_dev.py`, `cf_teacher.py`, `run_dev_e0.py`, launcher/common/proctest/refs/tests。
* sat 現在沒有 DEV training process。
* A-real-floor R1 eval = 24/24.
* B-real-floor R1 eval = 24/24.
* B-real-floor R1 calibration = 24/24.
* 沒有必要再等 oracle compute 才做 E0。
* T0 representability 已完成，不 resume T0 agent。
* ceiling compute 已完成，不再啟動新 ceiling search。

## 1. 第一優先：把 DEVHARNESS 修到可 launch，不再增加新的前置研究

我實際執行：

`PYTHONPATH=<dev>/src:<dev>/scripts /home/u24/papers/mcrl-leo-handover/.venv/bin/python -m pytest -q tests/test_cf_dev.py`

目前結果是 **14 passed / 5 failed**。

五個 failure 看起來全部來自同一個 DEV-NULL seed-validator bug：

D2-null 的已宣告 RNG identity 是 composite key `(9_231_000, k)`，例如 `(9_231_000, 0)`；目前 `assert_dev_seed()` 遞迴要求 tuple 的每一個 component 都落在 9-million namespace，因此錯誤拒絕合法的 index `k=0`。

Failures 包含：

* `test_d2_null_uses_only_its_own_generator_and_ignores_the_t0_action`
* `test_teacher_weight_zero_reproduces_d0_bit_identically`
* `test_no_development_path_produces_a_formal_seed`
* `test_config_hash_is_deterministic_and_covers_the_whole_configuration`
* `test_launcher_dry_run_plans_without_starting_anything`

先確認根因。如果一致，做**最小修正**：

* 保留 Amendment 6 宣告的 composite RNG identity，不要偷偷換 seed semantics；
* validator 對 composite DEV-NULL key 應驗證 declared base namespace + 合法 index，而不是把 index 當 standalone seed；
* 補 test 防止 formal namespace leakage；
* 重跑全部 `tests/test_cf_dev.py`.

不要趁機重構無關程式。

若全部 green，立即：

1. 更新真實 PROGRESS；
2. commit minimum E0 implementation；
3. 用該 commit 做 fixed-diff fresh-context engineering review；
4. 只修 INVALIDATES/BIASES；
5. 不要因 cosmetic finding 延遲 E0。

## 2. 把 E0 改成 canary escalation，不一開始把 300 episodes × 全 arms 當成一個不可分割 batch

Amendment 6 的 300-episode budget保留作 **E0 full budget ceiling**，但第一波改成：

### E0a — first-gradient canary

paired DEV seed k=0，只跑：

1. `D0 / equal_share`
2. `D2-T0 / equal_share`
3. `D2-null / equal_share`

每個先跑到 **100 episodes**，在 episode 100 做完整 24-episode DEVVAL。

這三個 arm 優先於 D3 與任何 lighting-price arm。

目的只回答：

* learner 本身能不能學；
* D2 teacher injection 有沒有超過 D0；
* T0 information 有沒有超過 matched null。

不要等：

* B1 final report；
* lighting-price oracle-first verdict；
* B2 representability；
* oracle full report；
* R2；
* reverse order；
* ceiling/Q9/T_JOINT 後續；
  才開始 E0a。

只要 minimum E0 diff review 通過，立刻 launch optimizer training。

### E0b — expansion

E0a 的 100-episode DEVVAL 落地後才決定：

* 是否把 D0 / D2-T0 / D2-null 接續到 300；
* 是否加入 `D3-T0`;
* 是否調 α / τ / LR / clipping / target cadence 等 development parameters。

只有 DEV / DEVVAL 可以影響這些調整。

`D3-T0` 是必要 comparator，但**不是 first-gradient blocker**。

lighting-price D0/D2 pair 仍可作 development diagnostic，但不要排在 E0a 前面；目前 B1 no-training screen 尚未正式 PASS，而且已知它可能有 bits-ratio 問題。

Exact-DR learner arms仍遵守既有 formal restriction，不在 E0a 偷跑。

## 3. Rolling development 的定義：不要 hot-patch 同一條 running trajectory

「訓練中持續修改」請實作成**versioned immutable short cycles**，不是直接改一個已經跑到一半的 process/code 然後繼續當同一個 run。

例如：

`MCRL-Dev-v0.1 → DEVVAL → v0.2 → DEVVAL → v0.3`

每次 algorithmic/hyperparameter change 都要：

* 新 config hash；
* 對應 code commit/digest；
* 原因；
* 使用了哪個 DEV/DEVVAL evidence；
* paired seed；
* 明確是 fresh start 還是 intentionally resume from checkpoint。

不得 silently overwrite config。

這樣才能快速迭代又保留因果可讀性。

## 4. 現在 provisional algorithm 暫時定案為 MCRL-Dev-v0

目前先不要再為「最終演算法還沒全部知道」而停工。

Development kernel 暫定：

* current ratio learner / 3 Q heads;
* existing 113-dim base input;
* 28-action contract;
* pluggable credit;
* pluggable observation adapter;
* teacher interface = masked action + 28-score/advantage vector;
* T0 = LP-prev(1,0) non-privileged anchor teacher;
* D2 soft on-student-state distillation = primary;
* D3 = required hard-imitation comparator;
* D0 and matched-null remain controls.

尚未定案、允許後插拔：

* B1 vs B2 observation/execution contract;
* final credit;
* T_DR/T_SEQ/T_JOINT;
* final Catfish count.

不要把這些尚未定案項目重新變成 E0 blocker。

## 5. B2 representability 現在可並行啟動，但不得阻塞 E0

目前已有：

* A-floor eval 24/24;
* B-floor eval 24/24;
* B-floor calibration 24/24.

直接重新聚合 raw JSON 並核對：
A-floor 約 113.532 M bit/J；B-floor 約 134.129 M bit/J；B−A 約 +19.25 percentage points of the A m=2dB rule；A-floor 的 rate tail仍退化，而 B-floor 沒有相同 collapse。

`.scratch/b2-representability/BRIEF-DRAFT.md` 已存在。

確認 B-floor calibration 的 NPZ 確實帶有 brief 所需的 obs / mask / joint_ref / joint_chosen / order / adv vector 後，可以 dispatch T_SEQ representability lane。

但它和 E0a **平行**：

* B2 screen 決定 final observation/execution instantiation；
* E0a 決定 shared learner + teacher-injection kernel 能不能 work。

兩者不得再序列化。

## 6. Oracle/measurement lanes現在收尾，不再擴張

LP-ORACLE：

* 需要的 A-floor eval、B-floor eval、B-floor calibration都已 24/24。
* 立即聚合 branch numbers / 寫最小 branch adjudication artifact。
* HOLD A-floor calibration、R2、reverse order、unfloored tie-ins，除非後續某一個正式 branch 明確需要。
* 不再用「完整 oracle matrix 尚未完成」阻止 learner。

B1-CREDIT：

* 已有 engineering core commit。
* 目前已啟動的 lighting-price screen讓它跑完並寫 PASS/FAIL。
* 它的結果不得阻止 E0a equal-share kernel canary。
* 不要再把 DEVHARNESS ownership拿回 B1 lane。

CEILING/T0：

* 已完成，不 resume compute。

## 7. launch policy

只要：

* `tests/test_cf_dev.py` 全 green；
* minimum E0 diff 已 commit；
* fresh-context engineering review = 0 INVALIDATES / 0 BIASES，或 findings 已修正；
* launcher smoke / stop-resume identity test通過；

就 launch E0a。

不要新增新的科學 gate、文獻 review、report polish 或完整 formal harness 作為第一個 optimizer step 的前置條件。

下一次回覆 owner 時，不要再只報「還有哪些 gate 在等」。

請直接報：

1. DEVHARNESS test：pass/fail；
2. minimum E0 commit hash；
3. review verdict；
4. E0a 三個 arm 的 PID / cwd / config hash；
5. 是否已有真正 optimizer step；
6. B2 representability 是否已並行；
7. 真正還會阻止 **下一個 development iteration** 的 blocker，只列實際 blocker。

核心原則：

**先讓 MCRL-Dev-v0 真正開始學，再讓 oracle / B2 / credit 的證據滾動決定它的 final instantiation；不要再要求 final algorithm 完全定案後才允許 development learner 存在。**
