# 遷移表(W-14)— 舊名 ↔ 新名 ↔ 論文符號

**用途**:任何人拿舊 repo 的成果、舊註冊表、或論文式子來對照本 repo 時,
先查這張表。**同一個量在三處有三個名字是常態,而不是例外。**

`—` 表示該欄不存在該概念。

---

## 1. 已刪除的量(查到請停,不要重新引入)

| 舊名 | 別名 | 為何刪除 | 裁決 |
|---|---|---|---|
| `k_cap` | `v_max`、每衛星同時波束上限 | **原論文沒有上限**。`Σ_v z_{s,v} = V` 在 MODQN 是**恆等式**不是不等式;上限是舊 repo 自己發明的。量測顯示照 7 執行會讓約 2/3 使用者落在熄滅波束上 | `RULING-2026-08-22-no-beam-count-cap.md` |
| `capacity penalty` | — | 與 catfish 無關,硬掛勉強 | SDD §2.2 |
| `apply_satellite_aggregate_cap` | 每衛星 RF 總功率上限 `P_sat,max` | 它是**比例縮放不砍波束**,且其上游 `beam_power_w` 被閘為 historical negative control ⇒ §2.6 的 r6 是在已停用路徑上論證的 | 裁決 §7.6 |
| `anti_collapse_*`(9 個欄位) | capacity-aware / QoS-sticky 選取器 | 同 `k_cap` 家族;**L-4 潛伏缺陷隨之消失** | W-09 / 裁決 §7.2 |
| `catfish_*`(44 個欄位) | Phase-04B/05B/v3/07B/07D 介面 | 本 repo 零消費者;§8 保留的是**那些程式碼**,它們在來源專案 | W-09 |
| `popart_*` | 線上獎勵標準化 | 恆為 False 且模組未移植 | W-09 |
| `section_6_2_row_capture_*` | — | 伸手進**舊環境**的私有成員 | W-09 |
| `_update_from_arrays` | 休眠批次更新孿生 | 持有**第二份 TD target**(且已與 live 版漂移),其有限性檢查**靜默略過** | W-08 |

## 2. 改名或改定義的量

| 舊 repo / 舊註冊表 | 本 repo | 論文符號 | 註 |
|---|---|---|---|
| `beam` = 載量通道 | 指向格 + 波束槽 | `v ∈ 𝒱`;`V = 39` | 原論文的波束**沒有幾何**;本論文加入指向與 3 dB 涵蓋圈 ⇒ **`X` 級偏離 7 → 39** |
| `V = 7`(MODQN Table I) | `NUM_BEAM_SLOTS = 7`(`J_w`) | `J_w` | ⚠ **數值相同純屬巧合,概念無關。** Table I 的 `V` 是 `\|𝒱\|`,已由本論文的 `V=39` 取代;`J_w` 是每位使用者看得到幾格 |
| `L_w` 最近 4 顆 | D2 合格者依餘裕排序取 4 | `L_w = 4` | 視窗成員由 D2 決定,不再是「最近 4 顆」 |
| `r3` = `R̃` 的 max−min | `−U_{b_u}` 計數式 | (3.28) | 舊式中 `U_{s,v}` **完全約掉** ⇒ 對負載盲 |
| `beam_loads`(後允入) | `demand_by_beam`(**未經閘**) | `n_{s,v}(t−1)` | 狀態用未經閘的需求;鍵是**波束** `(s,v)` 不是格(P-17) |
| — | `eligible_load_by_beam`(**經逐鏈路功率可行性**) | `U_{s,v}`(3.3) | 獎勵/功率/`γ_req`/(3.14) 的頻寬除數用這個。~~經 `m^e`~~ 已隨 C-11 退場 |
| `assignments_slot` 的 0 佔位 | `NO_OP_ACTION = −1` | — | P-8 真空首步;0 曾被誤當成實體動作 |
| 索引比較判換手 | `Association(norad_id, cell_id)` | `(ρ_u, δ_u)`(3.27) | **絕不比較索引**;G-9 的 T1–T12 |
| `epsilon_decay_episodes = 7000` | `2000` | §5.1 表 5-3 | 註冊表 `REP-004` 已過時;程式與論文皆 2000 |
| `angle_aware_ee.per_ue_energy_efficiency` | `runtime/energy_efficiency.link_energy_efficiency` | (3.17)(3.25) | **C-7 已裁決**:分母是共同系統功率 `P^N`;逐鏈路 `κ` 占比**已撤除** |
| `state_dim = 125 = 4C + 13` | **`112 = 4C`** | (4.1)、§5.1 | **C-1 已裁決**:112 是 live 值;13 維契約區塊降為**消融開關,預設關** |
| `PowerSurfaceConfig` 及七個 `HOBS_POWER_SURFACE_*` 模式 | `env/step.PhysicsConfig` | — | **C-2 / P-16**:整組刪除,**沒有模式開關**。其中兩個模式是被點名禁止的機制本身 |

## 3. 論文符號 ↔ 程式識別字

| 論文 | 程式 | 位置 |
|---|---|---|
| `x_{u,s,v}(t)` | `ServiceResolution.served` + `serving_cell` / `serving_satellite` | `env/service.py` |
| `z_{s,v}(t)` | `ServiceResolution.active_beams` / `activation_vector()` | 同上,**導出** `z = 1{U>0}`;與 `RadiatingBeams` 逐項相同 |
| `U_{s,v}(t)` | `eligible_load_by_beam` / `user_beam_load()` | 同上,鍵為 `(norad_id, cell_id)`(P-17) |
| `d_{u,s,v}(t)`(3.5) | `slant_range_from_elevation_km` / `CandidateGeometry.slant_range_km` | `env/pointing.py` |
| `θ_{u,s,v}(t)`(3.6) | `off_axis_angle_deg` / `CandidateGeometry.off_axis_deg` | 同上,**度** |
| `G^T(θ)`(3.7–3.9) | `transmit_gain_linear` | `env/antenna.py`,傳入 `θ_3dB/2` |
| `μ(θ)`(3.9) | `mu_of` | 同上 |
| `ε_μ` | `1e-10` 的極限分支 | 同上;論文 §5.1 同值 |
| `G^R_{u,s,v}(t)`(3.10c) | `receive_gain_dbi` / `receive_gain_linear` | 同上 |
| `A_R, B_R, G_R,min, G_R,max` | `RX_ENVELOPE_A_DBI` 等 | 同上 |
| `L_f`(自由空間) | `free_space_loss_db` | `env/link_budget.py` |
| `L_g`(大氣) | `atmospheric_loss_db` | **C-4 已裁決**:TR 38.811 (6.6-8) 餘割律,`A_zenith = 0.25 dB` |
| `L_c`(閃爍)、`L_s`(遮蔽) | `SCINTILLATION_LOSS_DB` / `SHADOWING_LOSS_DB`,皆 **0.0** | **C-8**:具名的零,不是消失的項。`L_s = 0` 另有出處(TR 38.821「0 dB for VSAT」) |
| `K_R`(Rician) | `RICIAN_K_FACTOR_DB = 20.0` / `rician_fading_gain` | **C-9 已裁決**;單位均值,逐(使用者, 衛星)抽,進 PREREG 種子集 |
| `σ² = k_B T_sys B^w` | `noise_power_w` | `env/link_budget.py` |
| `B^w = B_sys/3` | `BEAM_BANDWIDTH_HZ` | 同上 |
| `c_{s,v} = (q−r) mod 3` | `CellGrid.colors` | `env/cells.py`,**規則字面相同** |
| `R_b = h_s tan(θ_3dB/2)` | `cell_radius_km` | 同上 |
| `I^intra_{u,s,v}`(3.12a) | `co_channel_interference(...).intra_w` | `env/interference.py` ✓ 同色、同星、`v'≠v` |
| `I^inter_{u,s,v}`(3.12b) | `co_channel_interference(...).inter_w` | 同上 ✓ 同色、異星、**含 `v'=v`**;`s' ∈ 𝒮` **全域**不限四槽視窗 |
| `H_{u,s,v}`(3.10a) | `link_power_factor` / `BeamFieldAtUsers` | `env/link_budget.py` + `env/interference.py` ✓ |
| `γ_{u,s,v}`(3.13) | `StepOutcome.link_sinr`(經 `link_budget.sinr`) | `env/step.py` ✓ |
| `R_{u,s,v}`(3.14) | `shannon_rate_bps` | `env/link_budget.py` ✓ 含 `/U_{s,v}` |
| `p_{u,s,v}`(3.11)(3.12) | `recurrence_power_w` + `env/step.Segment` | **C-2 已裁決**:角度遞推;載量式 PA 已整條刪除 |
| `p_{s,v} = max_u p`(聚合) | `beam_power_w` | **C-10 已裁決** ✓ max,絕不是和或平均 |
| `ξ`(3.15a)、`P^p`(3.15) | `pa_efficiency` / `supply_power_w` | **C-5 已裁決** ✓ |
| `P^f`(3.16a) | `fixed_power_w` | **C-6 已裁決** ✓ 基頻功率每衛星只計一次 |
| `P^N`(3.16) | `system_power_w` | ✓ 含 `P^f`。⚠ 逐**鏈路**求和,見 F-2 |
| `η_{u,s,v}`(3.17) | `link_energy_efficiency` | **C-7 已裁決**:分母是 `P^N` |
| `r_{1,u}`(3.25) | `r1_energy_efficiency` | 同上;逐使用者相加**恰好**還原系統 EE |
| `Ψ_u`、`r_{2,u}`(3.27) | `HandoverClass` / `classify_handover` | `env/action_contract.py` ✓ |
| `r_{3,u}`(3.28) | `r3_counting` | `env/service.py` ✓ |
| `s_u(t)`(4.1) | `encode_state` / `StepObservation.state_matrix` | **C-1 已裁決:112**。`γ` 區塊的 provenance 為 `theta-current-interference-previous-step` |
| `a_{u,c}(t)`(4.5) | 動作索引 `a = 7l + j` | `env/action_contract.py` ✓ |
| `m_{u,c}(t)` | `SlotTable.mask` | 同上 |
| `x = a·z`(4.5a) | `resolve_service` | **C-11 已裁決:兩閘**;等價性測試 `test_c11_gate_order_equivalence.py` |
| TD target(4.12) | `MODQNTrainer.update` | ✓ vanilla、逐目標、含 done 項 |
| `Ω = (ω₁,ω₂,ω₃)` | `objective_weights` | ✓ |
| `φ₁, φ₂` | `PHI1, PHI2` | ✓ |

## 4. 出處類別變更

| 量 | 舊出處 | 新出處 |
|---|---|---|
| `G_0 = 2000` | HOBS Table I | **否定** HOBS 的 40 dBi(該表三值互斥,兩種讀法孔徑效率皆 > 1);改由波束寬一致的孔徑重導 `D = 1.0275λ/θ_3dB`,取 TR 38.821 的 Ka 孔徑效率 0.639–0.645 |
| `h_s` | Table I 的 780 km(**P**) | 由星曆決定(**X** 級偏離);語料中位數 483.0 km |
| `V` | Table I 的 7(**P**) | 39(**D**,依 95% 覆蓋目標);**`X` 級偏離** |
| `P_cir`、`P_BB` | 無 | You 等人 Table II [25] |
| 波束數上限 | 舊 repo 自訂 `k_cap` | **不存在** |

## 5. 驗收門 ↔ 測試檔

| 門 | 測試 |
|---|---|
| G-1 幾何一致性 | `test_w02_g1_sgp4.py` |
| G-2 鏈路預算包絡 | `test_w06_link_budget_g2.py` |
| (3.12a)(3.12b)(3.13) 干擾與 SINR | `test_w17_interference.py` |
| 端到端環境 | `test_w17_step_environment.py` |
| G-3 崩潰四項齊報 | `test_w12_collapse_metrics.py` |
| G-4 `r3` 可分解性 | `test_w07_r3_and_feasibility.py` |
| G-6 無禁用路徑 | `test_g6_forbidden_list.py`(exemption map 為空) |
| G-7 角度單位錨點 | `test_w06_antenna.py` |
| G-8 EE 必附服務率 | `test_w06_energy_efficiency.py` |
| G-9 換手帳目 T1–T12 | `test_w03_g9_handover_accounting.py` + `test_w03_td_target_masking.py`,對照表 `G9-TEST-MAP.md` |
| G-10 `G^T` 錨點與數值域 | `test_w06_antenna.py` + `test_w15_bessel.py`(向量版逐元素比對純量版,最大絕對誤差 2.9e-16) |
| G-11 訓練期有限性 | `test_w16_finiteness.py` + `test_w08_vanilla_td_target.py` |
| G-12 載量語意單一性 | `test_w07_r3_and_feasibility.py` + `test_w17_step_environment.py`(端到端載量恆等式) |
