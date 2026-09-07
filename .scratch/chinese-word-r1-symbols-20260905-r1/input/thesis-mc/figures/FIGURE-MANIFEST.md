# 論文圖表清單（0727／chart_0722 批次）

> 2026-07-28 起，本檔只記錄目前實際嵌入 `thesis-mc/` 的圖。逐檔雜湊與正文同步位置由
> `figure-sync.json` 與自動產生的 `FIGURE-SYNC-MANIFEST.md` 管理。

## 第 2、3 章

| 圖號 | 路徑 | 用途 |
|---|---|---|
| 圖 2-1 | `0727/fig2-1_modqn-baseline.png` | 本研究使用的 MODQN 基準骨幹 |
| 圖 3-1 | `0727/03_fig3-1__mcrl.png` | 低軌多波束系統、角度、干擾、容量與換手成本 |

## 第 4 章

| 圖號 | 路徑 | 用途 |
|---|---|---|
| 圖 4-1 | `0727/fig4-0_modqn-update-interventions.png` | 各機制在資料蒐集／更新流程的介入位置 |
| 圖 4-2 | `0727/fig4-1_mcrl-architecture.png` | 主代理與鯰魚代理兩組三目標 MODQN 的一一對應 |
| 圖 4-3 | `0727/fig4-1_training-architecture.png` | 兩個代理、各自環境／回放池與部署邊界 |
| 圖 4-4 | `0727/fig4-2_ee-stratification.png` | 以平均原始能效分層完整三目標轉移束 |
| 圖 4-5 | `0727/fig4-3_asymmetric-discount.png` | 非對稱折扣 |
| 圖 4-6 | `0727/fig4-4_periodic-intervention.png` | 週期性介入 |
| 圖 4-7 | `0727/fig4-5_competitive-reward.png` | 競爭獎勵 |
| 圖 4-8 | `0727/fig4-6_capacity-penalty.png` | 容量懲罰 |

> ⚑ **2026-08-21 狀態更新**：圖 4-8（容量懲罰）已隨 §4.5 Penalty Shaping 整節自論文正文移除（2026-08-21）。圖檔 `fig4-6_capacity-penalty.png` 保留於 `figures/` 供 provenance；不再列為現行嵌入圖，不計入重畫任務清單。現行方法圖為圖 2-1、圖 3-1、圖 4-1 至圖 4-7 共九張。

正文的正式語意是：圖 4-2 中 Catfish 1、2、3 為鯰魚代理 MODQN 內依目標分工的三個 Q 網路角色，
$Q_j^M\leftrightarrow Q_j^{CF}\leftrightarrow r_j$ 一一對應。鯰魚代理三網路共用單一 `Rollout`、
`\mathcal D_{CF}` 與一個由 $\Omega$ 純量化後的動作；這與現行 `0727` 圖中的單數資料流一致。

## 第 5 章

| 圖號 | 路徑 | 用途 |
|---|---|---|
| 圖 5-1 | `chart_0722/fig-ep1700-ee-vs-vmax.png` | 主動波束容量 |
| 圖 5-2 | `chart_0722/fig-ep1700-ee-vs-beam-load.png` | 每波束使用者負載 |
| 圖 5-3 | `chart_0722/fig-ep1700-ee-vs-users.png` | 使用者數 |
| 圖 5-4 | `chart_0722/fig-ep1700-ee-vs-powers.png` | 單束發射功率 |
| 圖 5-5 | `chart_0722/fig-ep1700-ee-vs-bandwidth.png` | 系統頻寬 |
| 圖 5-6 | `chart_0722/fig-ep1700-ee-vs-noise.png` | 雜訊功率頻譜密度 |

`chart_0722` 是受保護的 episode-1700 診斷批次；本清理只保存其檔案、來源與雜湊，
不替換第五章圖表或結果。等最新訓練回傳且由使用者確認後，再統一更新同位置內容。

## 檢查

```bash
cd thesis-mc
python3 figures/check_figure_sync.py
```

第五章維持 placeholder 時，此檢查應回報 10 張已嵌入圖且無漂移；待新結果經使用者
授權回填後才恢復為 16 張。圖檔與圖說的最終視覺接受仍須以 Word 開啟雙語 DOCX 後由人確認。
