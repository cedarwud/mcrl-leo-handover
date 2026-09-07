# G-9 驗收對照表 — §4A.7 T1–T12 → 測試

**門 G-9**:「§4A.7 的 T1–T6 六項測試全數通過。**不得以索引比較實作 `r2`**」。
T7–T10 為第 4 輪加入,T9 於 r7 更正,T11 於 r8 撤除,T12 為第 5 輪加入。

| # | 情境 | 必須得到 | 測試 |
|---|---|---|---|
| **T1** | 現任於 `t` 跌出 D2 資格;`t-1` 與 `t` 皆選 `a=0` | `φ2` | `test_w03_g9_handover_accounting.py::test_T1_incumbent_loses_eligibility_and_the_same_index_is_a_phi2` |
| **T2** | `t-1` 選 `a=2` 換到 C;`t` 時 C 成為現任佔槽 0,選 `a=0` | `0` | `::test_T2_returning_to_slot_zero_after_a_handover_is_free` |
| **T3** | 同一衛星、不同格 | `φ1` | `::test_T3_same_satellite_different_cell_is_phi1`、`::test_phi1_is_structurally_reachable_at_all` |
| **T4** | 某動作在 `s_t` 有效、在 `s_{t+1}` 無效 | 不得進入目標的 max | `test_w03_td_target_masking.py::test_T4_an_action_invalid_at_t_plus_one_is_excluded_from_the_max`、`::test_T4_the_masked_max_is_taken_over_the_valid_actions_that_remain` |
| **T5** | `t-1` 未被服務、`t` 被服務 | `φ2` | `test_w03_g9_handover_accounting.py::test_T5_reentry_after_an_outage_is_phi2`、`::test_T5_reentry_is_charged_even_returning_to_the_same_satellite` |
| **T6** | dwell 邊界前後 `j` 相同但 `cell_id` 不同 | `φ1` | `::test_T6_same_beam_slot_across_a_dwell_boundary_is_phi1`、`::test_dwell_rekey_that_lands_on_the_same_cell_is_free` |
| **T7** | 同時換衛星**且**換格 | 恰為 `φ2` | `::test_T7_changing_satellite_and_cell_is_exactly_phi2` |
| **T8** | 連續多步未被服務 | 每步皆 0,不重複收 re-entry | `::test_T8_consecutive_outage_steps_each_score_zero` |
| **T9** | 打亂原始候選列舉順序後重新正規化 | `s`、`mask`、`slot_table`、實體動作對應完全相同 | `::test_T9_shuffled_candidate_order_rebuilds_an_identical_contract` |
| **T10** | 回合最後一步 | `y = r`,不得自舉 | `test_w03_td_target_masking.py::test_T10_a_terminal_transition_does_not_bootstrap`(反向由 `::test_non_terminal_transition_does_bootstrap` 守住) |
| ~~T11~~ | — | **r8 撤除**(與 §4A.5a 衝突,該分支不可達) | 無測試對象 |
| **T12** | `mask_s` 全為 0 | 不得執行或訓練任何回退索引 | 選取端:`test_w16_no_op_action.py`(5 項);replay 端:`test_w16_replay_exclusion.py`(6 項);契約端:`test_w03_g9_handover_accounting.py::test_T12_*`(2 項) |

## 「不得以索引比較實作 `r2`」如何被強制

`HandoverLedger` 只持有**上一步的實現關聯** `Association(norad_id, cell_id)`,
**沒有任何欄位存動作索引**。`classify_handover()` 的簽章只收 `Association | UNSERVED | None`,
所以「拿索引來比」在型別上就寫不出來。

`SlotTable.association(a)` 是索引→身分的唯一入口,且它對**遮罩外的索引直接拋錯**,
不會回傳一個看似合理的關聯。

## 附帶(非 T 編號,但屬同一契約)

| 主張 | 測試 |
|---|---|
| 回合起始 ≠ 前一步未被服務(P-8 真空首步) | `::test_episode_start_is_not_a_reentry`、`::test_episode_start_differs_from_previously_unserved` |
| 現任即使餘裕較差仍佔槽 0(§4A.3) | `::test_incumbent_takes_slot_zero_even_with_a_worse_margin` |
| 現任失格則槽 0 給當步餘裕最大者 | `::test_an_ineligible_incumbent_yields_slot_zero_to_the_best_margin` |
| 餘裕相同以 NORAD ID 破平手 | `::test_ties_in_margin_are_broken_by_norad_id` |
| `cell_id(j)` 與 `l` 無關(§4A.2 正交性) | `::test_cell_identity_does_not_depend_on_the_satellite_slot` |
| 正式狀態為 112 維；13 維契約欄位僅於消融開關啟用時追加，屆時總維度 125 | `::test_contract_state_block_is_thirteen_dimensions`、`::test_state_dimension_is_the_authoritative_112` |
| 每目標各自在自己的目標網路取 max(B1 vanilla) | `test_w03_td_target_masking.py::test_each_objective_maxes_over_its_own_target_network` |
| P-4 動作有效性斷言 | `::test_T12_selected_action_validation_rejects_a_fallback_index` |
