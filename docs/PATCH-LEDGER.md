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
| `src/mcrl/algorithms/modqn.py` | `10600c208cc13c68` | `6385ee8871b76ed0` | **來源 + P-01…P-05、P-09、P-11、P-14**(1,333 → 1,070 行) |
| `src/mcrl/env/step_types.py` | `c4995ba509bbe2e6` | `7d9f65598a44c06d` | **來源 + P-07、P-08、P-15、P-16**(696 → 343 行) |
| `src/mcrl/runtime/q_network.py` | `d11318d61ad93a77` | `d11318d61ad93a77` | 逐位元組相同 |
| `src/mcrl/runtime/replay_buffer.py` | `374a73e1b3a5e9da` | `374a73e1b3a5e9da` | 逐位元組相同 |
| `src/mcrl/runtime/state_encoding.py` | `723974bcc6db9d5d` | `fdb4675b5cc89539` | **來源 + P-09、P-10**(P-10 已依 C-1 改為預設關的消融開關) |
| `src/mcrl/runtime/objective_math.py` | `e8a55760ee1dc4da` | `e8a55760ee1dc4da` | 逐位元組相同 |
| `src/mcrl/runtime/trainer_spec.py` | `0392e66c3e2f4686` | `d48fda5b04a5d4b5` | **來源 + P-05、P-06**(250 → 158 行) |

新增檔(無來源,不屬補丁):`src/mcrl/errors.py`、`src/mcrl/env/action_contract.py`、
`src/mcrl/env/interference.py`、`src/mcrl/env/step.py`、
`src/mcrl/runtime/finiteness.py`、各 `__init__.py`、`pyproject.toml`、`tests/`。
其餘 `env/` 與 `runtime/` 模組亦為新寫,見 `docs/PROVENANCE.md`。

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
| 補丁內容 | push 前加兩道閘:(a) `is_no_op(actions[uid])` ⇒ 不寫,`_no_op_transitions_skipped += 1`;(b) `not done_t and not mask_{t+1}.any()` ⇒ 不寫,`_all_invalid_next_transitions_skipped += 1`。分母 `_decision_steps_seen` 同步累計。獎勵累計(`ep_reward`、`ep_handovers`)移到閘之前,**未被服務的步仍完整計入回合報表**。新增 `get_masking_diagnostics()` / `reset_masking_diagnostics()`,以及 `runtime/outage_gate.py` |
| 理由 | (a) 是 SDD §4A.5a(2) 逐字要求。(b) 見下方「§4A.5a(3) 的解讀」。**丟棄的代價見「§4A.5a(4) 已升格為門檻」** |
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

## W-09 / W-10 / W-08 補丁

### P-05 — 拆掉四個沒有消費者的 opt-in 介面(W-09)

| 欄位 | 內容 |
|---|---|
| 來源行 | `modqn.py`:`:65`(PopArt import)、`:152`、`:160-186`、`:362-571`(兩個休眠選取器與其 helper)、`:596-615`(select_actions 的分派)、`:941-964`(獎勵端 PopArt)、`:1291-1317`(§6.2 擷取);`trainer_spec.py`:`:13-33`(kind 常數)、`:105-199`(四組欄位) |
| 補丁內容 | 移除:Phase-04B/05B/v3/07B/07D 介面(44 欄)、HOBS 崩潰試點動作約束介面(9 欄)、線上獎勵標準化介面(4 欄)、§6.2 擷取介面(2 欄),以及它們在 `modqn.py` 的全部程式路徑。`select_actions` 只剩一條路徑 |
| 理由 | **全部沒有消費者。** `modqn.py` 一個 catfish 欄位都沒讀過(那些 trainer 在來源專案且刻意未移植);動作約束欄位餵的是兩個休眠選取器,而那是 §2.2 刪除的家族,且 **2026-08-22 裁決明令不得為已刪除的機制留插座**;PopArt 恆為 False 且模組未移植;§6.2 擷取伸手進**舊環境**的私有成員並 import 未移植的模組。**§8 的「保留程式碼供日後消融」保留的是那些程式碼本身——它們在來源專案,不在這裡。只留設定欄位等於保留了全部的陷阱、零的消融價值** |
| 副作用 | **L-4 隨之消失**(它就住在被刪的 `_select_capacity_constrained_actions` 裡)。`raw_states` 參數保留但不再被讀取 |
| 對應測試 | `test_g6_forbidden_list.py`(exemption map 現為空,11 項)、`test_w08_vanilla_td_target.py::test_action_selection_has_one_path` |
| 門 | **G-6** |

### P-06 — `epsilon_decay_episodes` 由 7000 改為 2000(W-09)

| 欄位 | 內容 |
|---|---|
| 來源行 | `runtime/trainer_spec.py:66` |
| 補丁內容 | 預設值 `7000 → 2000` |
| 理由 | 註冊表 `REP-004` 的 7000 已過時。已核對來源:`family_b_r3/common_trainer.py:296` 是 **2000**,來源專案 9 份 resolved config 中 **8 份是 2000**,參數規格 §6.1 亦明指 7000 過時。**留著過時預設正是我在別處設 freeze flag 要防的那種慣性凍結** |
| 對應測試 | `docs/PREREG-DRAFT.md` 已同步;值本身由 PREREG 凍結 |

### P-07 — `beam_loads` docstring 移除已不存在機制的但書(W-09)

| 欄位 | 內容 |
|---|---|
| 來源行 | `env/step_types.py:548` |
| 補丁內容 | 刪除「不會在上限熄滅波束時被歸零」的但書 |
| 理由 | 2026-08-22 裁決後**沒有任何波束會被熄滅**,啟用是導出的 `z = 1{U>0}`。該但書描述的機制已不存在 |
| 對應測試 | `test_ruling_no_beam_count_cap.py`(16 項) |

### P-08 — `UserState` 新增 `contract_fields`(W-10)

| 欄位 | 內容 |
|---|---|
| 來源行 | `env/step_types.py:522-552`(`UserState` 類別) |
| 補丁內容 | 新增 `contract_fields: np.ndarray | None = None`,承載 §4A.6 的 13 維區塊 |
| 理由 | SDD §3.6 把 `s_u = 125 = 4C + 13` 定為全文唯一權威值。13 維是**環境端帳務**而非逐波束觀測,故置於四區塊**之後**而非之內 |
| 預設值的意義 | `None` **不是合法值**,只是為了讓四區塊建構式維持位置相容。編碼器對 `None` **拋錯**,不會靜默產生 112 維向量 |
| 對應測試 | `test_w10_state_encoding.py`(14 項) |
| 門 | G-9 相關(§4A.6) |

### P-09 — `UserState` 等容器型別改由 `env.step_types` 匯入(W-10)

| 欄位 | 內容 |
|---|---|
| 來源行 | `runtime/state_encoding.py:7`;`algorithms/modqn.py:43-48` |
| 補丁內容 | `from ..env.step import UserState` → `..env.step_types`;`modqn.py` 的 `ActionMask`/`RewardComponents`/`UserState` 同樣重指,`StepEnvironment` 改為 `TYPE_CHECKING` 專用 |
| 理由 | **這是 W-01 移植缺口中最後一項未解的**(`docs/PROVENANCE.md`)。`env/step` 是**舊環境**模組,本專案取代它且從未移植 —— 那正是整棵樹無法 import 的原因。三個容器型別的正典定義本來就在 `step_types` |
| 副作用 | 測試 shim 的 `mcrl.env.step` stand-in **已退役** |
| 對應測試 | `test_w10_state_encoding.py::test_user_state_is_imported_from_its_canonical_home`、`::test_the_algorithm_no_longer_imports_the_old_environment_at_runtime` |

### P-10 — 狀態編碼附加 13 維契約區塊(W-10)

| 欄位 | 內容 |
|---|---|
| 來源行 | `runtime/state_encoding.py:73`(`concatenate`)、`:76-78`(`state_dim_for`) |
| 補丁內容 | `concatenate([access, snr, theta, loads])` → 加上 `contract`;`state_dim_for` 由 `4*C` 改為 `4*C + 13` |
| 理由 | SDD §3.6 / §4A.6。四區塊本身**一字未動**,`(l,j)` 順序維持,故狀態與動作仍依構造對齊(§4A.1) |
| fail-loud | 缺少或長度錯誤的契約區塊**拋錯**。靜默產生 112 維向量在本專案裝不進任何網路,且只會在很後面(或根本不會)以形狀錯誤現形 |
| 對應測試 | `test_w10_state_encoding.py`(14 項) |

### P-11 — 刪除休眠的批次更新孿生 `_update_from_arrays`(W-08)

| 欄位 | 內容 |
|---|---|
| 來源行 | `algorithms/modqn.py:654-726` |
| 補丁內容 | 整個方法移除(77 行) |
| 理由 | 兩點。(1) 它持有**第二份 TD target 實作**,而 B1 的重點正是目標必須**無歧義地**是 MODQN 式 (16) vanilla —— 兩份同一條式子會漂移,而且**它們已經不一樣了**(休眠版用 out-of-place `masked_fill`,live 版用就地指派)。(2) 它的有限性檢查是**靜默略過**該目標並繼續訓練,正是 §3.7 P-3 與 §6 G-11 禁止的。**一條接上就會違反驗收門的休眠路徑是陷阱,不是備品。** 本 repo 內零呼叫端(其子類別皆為 §8 禁用,未移植) |
| 對應測試 | `test_w08_vanilla_td_target.py`(8 項),含「TD target 在原始碼中恰好出現一次」與 AST 層面的「無 `continue`/`break`」 |
| 門 | **G-11**、B1 |

### P-12 — 逐 UE EE 閉包改由 `runtime/energy_efficiency` 提供(W-06 收尾)

| 欄位 | 內容 |
|---|---|
| 來源行 | `algorithms/modqn.py:56`(import)、`:855`(`ee_result.eta_nmk[0]`) |
| 補丁內容 | import 由 `..runtime.angle_aware_ee` 改為 `..runtime.energy_efficiency`;欄位名 `eta_nmk` → `eta` |
| 理由 | 逐 UE 閉包移植進本 repo,**與系統級 EE 閉包放在同一個模組**,兩者因此共用**同一套零功率政策**(P-7)。分開放會出現「一個拋錯、一個墊 epsilon」的兩套語意 |
| 對應測試 | `tests/test_w06_per_ue_ee.py`(17 項),含 `::test_the_two_closures_share_one_zero_power_policy` |
| 副作用 | 測試 shim 的 `mcrl.runtime.angle_aware_ee` stand-in **已退役** |

### P-13 — `RewardComponents` 的 `r3` 說明仍寫著舊式(外部稽核發現)

| 欄位 | 內容 |
|---|---|
| 缺陷 | 型別契約與實作不一致 |
| 來源行 | `env/step_types.py:613` |
| 補丁內容 | 「`r3`: dimensionless ratio(negative gap / num_users)」改為 B13 的計數式 `−U_{b_u}`(單位:人) |
| 理由 | B13 換式後 `service.r3_counting` 回傳**原始人數**,而型別契約還寫著**正規化後的差距** —— **兩個不同的量、不同的單位**。留著會讓 typed contract 與實作互相打臉,而 Q-D 的尺度討論正好會讀到這一行 |
| 發現者 | `codex gpt-5.6-luna` 的獨立稽核(D-10),`docs/AUDIT-external-luna-2026-08-22.md` |
| 對應測試 | `test_w07_r3_and_execution_mask.py`(既有,值本身已測) |

### P-14 — 訓練端不再自行計算 `r1`(裁決 C-7)

| 欄位 | 內容 |
|---|---|
| 來源行 | `algorithms/modqn.py`:`per_ue_energy_efficiency` 的 import 與 `reward_vector_from_step_result` 內的角度感知 EE 區塊 |
| 補丁內容 | 整段移除;`r1` 改由環境在 `RewardComponents.r1_angle_aware_ee` 提供 |
| 理由 | 式 (3.25) 的分母是**共同系統功率 `P^N`** —— 一個**全域**量。訓練端要自己算就得知道其他 99 人的鏈路,結構上不可能。被移除的區塊用的是逐鏈路 `κ` 占比,裁決 C-7 已判定那是**另一個量** |
| 對應測試 | `test_w06_link_ee.py`(8 項) |

### P-15 — 兩個移植預設與 §IV 不符(裁決 §8)

| 欄位 | 內容 |
|---|---|
| 來源行 | `env/step_types.py` 的 `user_scatter_distribution`、`mobility_model` |
| 補丁內容 | `"uniform-circular"` → `"uniform-rectangle"`;`"deterministic-heading"` → `"random-wandering"` |
| 理由 | §IV 給的是 **200×90 km 矩形**與 **"random wandering"**。裁決明說**不要留著當選項** ——「留著就會有人選到」 |
| 對應測試 | `test_pointing_and_mobility.py` 的移動段 |

---

## W-17 補丁(接上干擾與 `StepEnvironment`)

### P-16 — 刪除 HOBS 功率介面整組(裁決 C-2)

| 欄位 | 內容 |
|---|---|
| 來源行 | `env/step_types.py`:`PowerSurfaceConfig` 全類、七個 `HOBS_POWER_SURFACE_*`、三組 `POWER_CODEBOOK_*`、`_HOBS_ACTIVE_TX_EE_EPSILON_P_W`(約 250 行) |
| 補丁內容 | 整組刪除;`StepResult` 隨之移除 `selected_power_profile` / `total_active_beam_power_w` / `power_budget_violation` / `power_budget_excess_w` 四欄 |
| 理由 | C-2「載量式 PA 整條移除」。其中兩個模式不只是沒用到,而是**被點名禁止**:`active-load-concave` 就是 `P_base+P_scale·N^exp` 本身,`angle-aware-thesis-3.13-3.15a` 就是「目標 SINR 反推 + 雙重 cap」。其餘五個是來源專案的死介面,與 W-09 的 P-05 同一理由 ——「留著就會有人選到」 |
| 消費者 | **零。** 刪除前 grep 過:`src/` 與 `tests/` 都沒有任何一處讀這些欄位 |
| 取代者 | `env/step.PhysicsConfig` + `env/link_budget`,**沒有模式開關** |
| 對應測試 | `test_no_shim_remains.py::test_the_deleted_power_surface_has_no_home_left` |

### P-17 — 載量鍵值由「格」改為「波束」(本次整合發現的缺陷)

| 欄位 | 內容 |
|---|---|
| 來源行 | `env/service.py`:`demand_by_cell` / `eligible_load_by_cell` / `active_cells` 全部以 `cell_id` 為鍵 |
| 補丁內容 | 改為以 `(norad_id, cell_id)` 為鍵,並更名 `demand_by_beam` / `eligible_load_by_beam` / `active_beams`;`activation_vector()` 改吃波束鍵 |
| 缺陷 | (3.3) 是 `U_{s,v}(t)=Σ_u x_{u,s,v}(t)` —— **對一支波束求和,不是對一塊地面**。兩顆衛星可以同時照同一格,而 (3.12b) 的內層和**沒有** `v'≠v` 限制正是因為這是合法組態。以格為鍵會把這兩支波束併成一支 |
| 後果(量化) | 兩位使用者分別在兩顆衛星的同格波束上,各自獨佔一支波束,卻雙雙回報載量 2:`r3` 各罰兩倍、(3.14) 各把頻寬砍半、`z` 少報一支輻射中的波束(於是干擾和少一項) |
| 為何現在才浮現 | 它只在「同格、異星」時發生,而那正是干擾模型第一次要求列舉全域輻射波束時才會構造出來的組態 |
| ⚠ 連 C-11 的等價性測試也漏了 | 該測試的**參考實作自己也以格為鍵**,兩邊一起錯,所以一直相符。參考實作已一併改為波束鍵 |
| 對應測試 | `test_c11_gate_order_equivalence.py::test_the_same_cell_reached_through_two_different_satellites`(現在斷言兩支獨立波束各載量 1)、`test_ruling_no_beam_count_cap.py::test_one_satellite_may_light_far_more_than_seven_cells`(7 → **14** 支) |

### 非補丁:向量化 Bessel(效能,數值不變)

`runtime/bessel.py` 新增 `bessel_j_array`,`antenna.transmit_gain_linear` 改走它。
干擾和要對每個(受害使用者 × 輻射波束)配對算 `G^T`,純量路徑每次約 28 µs,
100 位使用者對 60 支波束就是每步 6000 次。

**純量 `bessel_j` 一個字都沒動** —— G-10 的錨點仍量在它身上。
向量版與純量版逐元素比對:全域最大絕對誤差 **2.9e-16**,
`transmit_gain_linear` 最大絕對誤差 **2.2e-16**(涵蓋 J₁ 前四個零點與 34 的路由分界兩側)。
10,000 點由 280 ms 降至 8.4 ms。

---

---

## ★ 對來源行為的一項宣告偏離:`η` 分母不再墊 epsilon

**來源** `angle_aware_ee.py:866`:`eta = rates / max(alpha * p_tot + p0, 1e-12)`。

那個 floor **正是 §3.7 P-7 禁止的構造**:一條已允入、分母為零而速率為正的鏈路
會回傳 `R × 1e12` —— 在**消耗最少的那條鏈路上**靜默產生天文數字的 EE。

**本移植改為 fail-closed,與 `additive_system_ee` 一致**:

| 情形 | 行為 |
|---|---|
| 已允入、分母為 0、速率 > 0 | **拋錯** |
| 已允入、分母為 0、速率 = 0 | `η = 0`,帶 `zero_over_zero` 旗標 |

**所有可達的情形行為完全不變** —— 真實已允入鏈路的 `κ·P_tot > 0`,floor 從不生效。
改變的是那個不可達但災難性的分支:從「靜默灌高 19 個數量級」變成「大聲說出來」。
`EPSILON_NUM` 常數保留僅供 provenance,測試斷言它**不出現在函式本體內**。

**功率占比 `κ` 則逐字忠實移植**(piecewise 形式,S11a M-10 的修正):
`κ = q_u / Σ_{u'∈U_b} q_{u'}`(已允入)或 `0`,`q = min(p_req, P_max)`。
式 (3.27) 的雙重和會在**每一道波束**上計算 `κ`,舊的 `x·q/(Σ+ε)` 形式因此在空波束上
產生 0/0 而被 epsilon 蓋掉;piecewise 形式**依定義**隔離空波束,
且已允入者的占比**恰好加總為 1**(而非 `1 − O(ε)`)。已測。

---

## 新增:乾淨版 `TrainerConfig` 驗證器(非補丁,新檔)

`src/mcrl/runtime/trainer_config_validation.py`,**新寫而非移植**。

來源版 1,124 行,絕大部分在驗證 W-09 已移除的那些介面 ——
移植它等於**把 §8 的字彙以驗證規則的形式搬回來**。

新版只約束本專案真的有的欄位,且每一條都對應一種**靜默**失效:
權重不加總為 1 會**整體重新縮放獎勵**(run 只是看起來比較差);
replay 小於 batch 會在**訓練深處**才拋錯(離肇因很遠);
`ε` 排程上升會讓探索**隨時間打開**(讀起來像不穩定而非打字錯);
折扣為 0 **靜默刪除未來**;校準尺度為 0 **把該目標整個除掉**。

另加一條交叉檢查:`reward_calibration_enabled` 為真但 `R3_SCALE_IS_FROZEN` 為假時**拋錯** ——
B13 把 `r3` 從正規化差距換成原始人數,繼承來的尺度對它沒有意義(Q-D)。

**⇒ 測試 shim 的 `trainer_config_validation` stand-in 已退役。**
⚠ 該 stand-in 是**寬容的 no-op**,若不移除會**遮蔽**這個真的驗證器 —— 已加測試守住。

---

## 標記為潛伏、**刻意不修**

| # | 位置 | 狀態 |
|---|---|---|
| ~~**L-4**~~ | ~~`_select_capacity_constrained_actions`~~ | **W-09 已解決:整個方法連同它所在的介面一起刪除。** 潛伏缺陷不再存在,因為承載它的程式碼不再存在 |
| ~~L-4 家族~~ | ~~`_select_qos_sticky_overflow_reassignment_actions`~~ | **W-09 已刪除。** |
| ~~P-3 分歧~~ | ~~休眠孿生 `_update_from_arrays` 的靜默略過~~ | **W-08 已刪除**(P-11)。`update()` 現為唯一更新路徑,唯一有限性政策即 fail-loud |

**本表現在是空的。W-16 標記的三項潛伏全部由 W-08/W-09 以刪除解決,而非修補。**

---

## SDD §4A.5a(3) 的解讀 —— **作者已裁決(2026-08-22):採用**

§4A.5a 定案第 3 點原寫:

> 於是 `mask_{t+1}` 全為 0 的分支**在 replay 中不可達**,被 (2) 消掉。

**這一步推不出來**(作者已確認推論有洞)。(2) 丟掉的是**從**全無效狀態出發的轉移;
`(s_t, a_t, r_t, s_{t+1})` 是在 `t` 決策的,只要 `mask_t` 非空就會被寫入,
**即使 `s_{t+1}` 的遮罩全為 0**。於是目標那一列全被 `masked_fill(~nm, -1e9)`,
`max` 得 `-1e9`,非終端時 `y = r + 0.9×(−1e9)`。

**已採用的解讀**:轉移入 replay 的條件為
**`mask_t` 非空 ∧(`done_t` ∨ `mask_{t+1}` 非空)**。
如此 (3) 才真的成立,且與 (1)、(2)、T10 全部相容。

**兩個丟棄理由分開計數**,因為**入邊率與出邊率不是同一個量**;probe P1 兩者都要報。

## ★ §4A.5a(4) 已升格為**門檻**(作者裁決 2026-08-22)

**丟棄不只是為了避免 `-1e9` 汙染。** outage 期間三個獎勵分量全部讀起來是中性的:

| 分量 | outage 時 | 為何看起來中性 |
|---|---|---|
| `r1` | ≈ 0 | 無吞吐量 ⇒ 無能效積分 |
| `r2` | = 0 | §4A.4:未被服務不是關聯變更 |
| `r3` | = 0 | 不在任何波束上 ⇒ 對 `U_{b_u}` 無貢獻 |

**若再把未來截斷,outage 就變成「免費」** —— 而那正是 §4A.4 用 re-entry `φ2`
堵住的漏洞(策略刻意離線以清除換手成本)。丟棄等於**從另一側把同一個洞打開**。

**⇒ 定案:若丟棄率非可忽略,semi-MDP(跨 outage 累計獎勵至恢復服務那一步)
是強制的,不是可選的** —— 因為丟棄會讓 agent **永遠學不到 outage 有代價**。

實作:`src/mcrl/runtime/outage_gate.py`。
`assert_drop_is_admissible()` 在超標時拋錯,錯誤訊息明說**這不是 run 的 bug,
是門檻告訴你 semi-MDP 已成為義務**。
門檻值 `OUTAGE_RATE_NEGLIGIBLE_DEFAULT = 1e-3` 為 **S,提案中**,
**W-13 的 PREREG 必須先凍結它,probe P1 才可以跑**(§7.1:門檻須事前凍結,否則就是洩漏)。
測試:`tests/test_w16_outage_gate.py`(10 項)。
