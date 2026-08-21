# 補丁帳本 — 相對逐位元組來源的宣告偏離

**來源 repo**:`~/papers/modqn-paper-reproduction`,`HEAD 6aa281df`
**授權**:SDD §3.8 —「逐位元組」已改為**逐位元組 + 一份宣告的補丁帳本**。
Provenance 因此由「完全相同」變成**「來源 + N 個有記錄的補丁」**。

**規則**:任何對移植檔的改動都必須在本表有一列,含
**來源行、補丁內容、理由、對應測試**。沒有列的改動就是 provenance 破損。

---

## 檔案雜湊現況

| 檔案 | 來源 sha256(前 16) | 目前 sha256(前 16) | 狀態 |
|---|---|---|---|
| `src/mcrl/algorithms/modqn.py` | `10600c208cc13c68` | `6c9c27e802cbc03e` | **來源 + P-01…P-04 + 兩處潛伏標記** |
| `src/mcrl/env/step_types.py` | `c4995ba509bbe2e6` | `c4995ba509bbe2e6` | 逐位元組相同 |
| `src/mcrl/runtime/q_network.py` | `d11318d61ad93a77` | `d11318d61ad93a77` | 逐位元組相同 |
| `src/mcrl/runtime/replay_buffer.py` | `374a73e1b3a5e9da` | `374a73e1b3a5e9da` | 逐位元組相同 |
| `src/mcrl/runtime/state_encoding.py` | `723974bcc6db9d5d` | `723974bcc6db9d5d` | 逐位元組相同(W-10 待改 import) |
| `src/mcrl/runtime/objective_math.py` | `e8a55760ee1dc4da` | `e8a55760ee1dc4da` | 逐位元組相同 |
| `src/mcrl/runtime/trainer_spec.py` | `0392e66c3e2f4686` | `0392e66c3e2f4686` | 逐位元組相同 |

新增檔(無來源,不屬補丁):`src/mcrl/errors.py`、`src/mcrl/env/action_contract.py`、
`src/mcrl/runtime/finiteness.py`、各 `__init__.py`、`pyproject.toml`、`tests/`。

---

## W-16 補丁

### P-01 — 無效動作不得回退索引 0(訓練/評估選取路徑)

| 欄位 | 內容 |
|---|---|
| 缺陷 | **L-1**(SDD §3.8) |
| 來源行 | `algorithms/modqn.py:290`、`:293-295`、`:304`(`_select_unconstrained_actions`) |
| 補丁內容 | 動作向量改以 `NO_OP_ACTION`(`-1`)初始化;`len(valid)==0` 時寫入 `NO_OP_ACTION` 而非 `0`;greedy helper 回傳 `None` 時**拋 `MCRLContractError`**(在該分支下結構上不可達)而非吞成 `0` |
| 理由 | SDD §4A.5a(1):`mask_s` 全為 0 ⇒ 執行 **no-op**,該步 unserved,**絕不回退到任何索引**。原碼把「沒有合法動作」靜默轉成「服務波束 0」,會產生一次真實服務、一次 `φ2`,以及一筆策略從未合法選過的動作 |
| 揭露措辭 | MODQN 的 C2 是**等式**約束(人人連上),全無效狀態不會發生 ⇒ **這不是原論文的 bug**,是本設定(D2 視窗)啟用了它從未走過的路徑 |
| 對應測試 | `tests/test_w16_no_op_action.py::test_empty_mask_yields_no_op_not_index_zero_greedy`、`::test_empty_mask_yields_no_op_under_full_exploration`、`::test_index_zero_is_never_emitted_when_it_is_masked_out`、`::test_selected_action_is_always_valid_or_no_op`、`::test_unreachable_none_from_helper_fails_loud` |
| 門 | G-9(§4A.7 T12 前半) |

### P-02 — 無效動作不得回退索引 0(匯出診斷路徑)

| 欄位 | 內容 |
|---|---|
| 缺陷 | **L-1**(第二個呼叫端) |
| 來源行 | `algorithms/modqn.py:566`、`:578-580`(`select_actions_with_diagnostics`) |
| 補丁內容 | 同 P-01:向量以 `NO_OP_ACTION` 初始化;`selected_action is None` 時寫入 `NO_OP_ACTION`,診斷維持 `None` |
| 理由 | 同 P-01。此路徑餵的是 checkpoint 匯出與 §6 G-3 的診斷;若它回報「選了動作 0」,崩潰判定的 `argmax_agreement` 會把**不存在的決策**算成一致 |
| 對應測試 | `tests/test_w16_no_op_action.py::test_diagnostics_path_also_returns_no_op` |
| 門 | G-3、G-9 |

### P-03 — 全無效轉移不得寫入 replay

| 欄位 | 內容 |
|---|---|
| 缺陷 | **L-3** |
| 來源行 | `algorithms/modqn.py:1235-1252`(`train()` 的逐使用者 push 迴圈) |
| 補丁內容 | push 前加兩道閘:(a) `is_no_op(actions[uid])` ⇒ 不寫,`_no_op_transitions_skipped += 1`;(b) `not done_t and not mask_{t+1}.any()` ⇒ 不寫,`_all_invalid_next_transitions_skipped += 1`。獎勵累計(`ep_reward`、`ep_handovers`)移到閘之前,**未被服務的步仍完整計入回合報表**。新增 `get_masking_diagnostics()` / `reset_masking_diagnostics()` |
| 理由 | (a) 是 SDD §4A.5a(2) 逐字要求。(b) 見下方「⚠ 對 §4A.5a(3) 的解讀」 |
| 行為差異(須知) | 「排除於學習、保留於報表」是刻意的:丟掉獎勵會讓回合曲線與實際服務水準脫節,而 §6 G-8 要求 EE 比較必附服務率 |
| 對應測試 | `tests/test_w16_replay_exclusion.py`(全部 6 項) |
| 門 | G-9(§4A.7 T12 後半)、T10 |

### P-04 — `update()` 補上 fail-loud 有限性電池

| 欄位 | 內容 |
|---|---|
| 缺陷 | **L-2** |
| 來源行 | `algorithms/modqn.py:766-772`(`update()`,原本 loss → zero_grad → backward → step,中間無任何檢查) |
| 補丁內容 | 依 P-3 逐項補齊:`assert_finite_loss` 於 `backward()` 前、`assert_finite_gradients` 於 `step()` 前、`assert_finite_parameters` 於三個目標更新完成後。三者皆拋 `NonFiniteTrainingError` |
| 來源護欄出處 | `family_b_r3/common_trainer.py:516-517`(loss)、`:520-525`(梯度)、`:529-530`(參數);helper 語意抄自 `:173` `_all_finite_networks` |
| 理由 | SDD §3.7 P-3 / §6 G-11。缺了會**靜默續訓於 NaN 策略**,而 G-3 的四項崩潰指標就會在 NaN 上算出來並被當成有效結果。P6 規定要跑已知發散的 `α=0.01`,這條路徑一定會被走到 |
| 未採 | 來源 `:531-537` 的參數 L2 範數檢查未移植;SDD 只點名 516-517/520-525/529-530,且參數有限性檢查已涵蓋其攔截目標 |
| 對應測試 | `tests/test_w16_finiteness.py`(全部 7 項) |
| 門 | G-11 |

---

## 標記為潛伏、**刻意不修**

| # | 位置 | 狀態 |
|---|---|---|
| **L-4** | `_select_capacity_constrained_actions`(來源 `:344-349` 的 `ranked[0]` 回退,以及 `:328`/`:342` 的兩處索引 0 回退) | 已加註解標記潛伏。**不接上、不修**(W-16 brief)。`anti_collapse_action_constraint_enabled` 為 False 時不可達,而 SDD §8 要求本里程碑內一律為 False |
| L-4 家族 | `_select_qos_sticky_overflow_reassignment_actions` | 已加註解。它消費 `_select_unconstrained_actions`,P-01 後可能拿到 `-1`,而其 `np.bincount` 會直接拒絕負值 ⇒ **啟用即拋錯**,是刻意的絆線 |
| P-3 分歧 | 休眠孿生 `_update_from_arrays`(`:700-708`)的有限性檢查是**靜默略過**(`continue`),不是拋錯 | 本 repo 內無呼叫端(子類別未移植)。**未改**,不在 W-16 的 L-1…L-3 範圍。**接上前必須先改為 fail-loud**,否則違反 G-11 |

---

## ⚠ 對 SDD §4A.5a(3) 的解讀(需作者確認)

§4A.5a 定案第 3 點寫:

> 於是 `mask_{t+1}` 全為 0 的分支**在 replay 中不可達**,被 (2) 消掉。

**這一步推不出來。** (2) 丟掉的是**從**全無效狀態出發的轉移;
`(s_t, a_t, r_t, s_{t+1})` 是在 `t` 決策的,只要 `mask_t` 非空就會被寫入,
**即使 `s_{t+1}` 的遮罩全為 0**。於是目標那一列全被 `masked_fill(~nm, -1e9)`,
`max` 得 `-1e9`,非終端時 `y = r + 0.9×(−1e9)` —— 正是同節要防的災難性汙染。

**本次採用的解讀(保守、可證安全)**:轉移入 replay 的條件為
**`mask_t` 非空 ∧(`done_t` ∨ `mask_{t+1}` 非空)**。
如此 (3) 才真的成立,且與 (1)、(2)、T10 全部相容。

**兩個丟棄理由分開計數**(`get_masking_diagnostics()`),因為 §4A.5a(4) 要求
「必須量測全無效狀態的發生率」,而**入邊率與出邊率不是同一個量**;
probe P1 兩者都要報。若任一非可忽略,(4) 的 semi-MDP 改法就被觸發。

**若作者認為 (3) 另有所指(例如原意就是連入邊一起丟),本補丁不需改動,只需把 §4A.5a(3) 的文字補明確。**
