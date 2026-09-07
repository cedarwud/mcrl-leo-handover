# 圖 ↔ 正文 同步基準（自動產生，勿手改）

> 基準設定時間：**2026-08-09 17:25:41**。以 `python3 figures/check_figure_sync.py` 檢查漂移，
> `--update` 重設基準（**先確認正文與圖說已同步**再重設，否則等於把漂移蓋掉）。
> 雜湊為 sha256 前 16 碼。`png_mtime` 只供人閱讀，判斷是否真的改變請看雜湊。

| 圖 | 檔案 | 最後修改 | PNG 雜湊 | builder | 論文位置 |
|---|---|---|---|---|---|
| 圖 2-1 | `fig2-1_modqn-baseline.png` | 2026-07-27 23:35:09 | `00e544b802356dc9` | —（既有點陣圖，無 builder） | mc-modqn-base.md §2.1 |
| 圖 3-1 | `03_fig3-1__mcrl.png` | 2026-07-27 23:35:09 | `c09b910e3fbe3f60` | —（既有點陣圖，無 builder） | mc-modqn-base.md §3.1.1 |
| 圖 4-1 | `fig4-0_modqn-update-interventions.png` | 2026-07-27 23:35:09 | `44ff9c01b93f73c7` | —（既有點陣圖，無 builder） | ch4-method.md §4.1 |
| 圖 4-2 | `fig4-1_mcrl-architecture.png` | 2026-07-27 23:35:09 | `ee4ba997dee9afdd` | —（既有點陣圖，無 builder） | ch4-method.md §4.1 |
| 圖 4-3 | `fig4-1_training-architecture.png` | 2026-07-27 23:35:09 | `01ec9a2eff93d664` | —（既有點陣圖，無 builder） | ch4-method.md §4.1 |
| 圖 4-4 | `fig4-2_ee-stratification.png` | 2026-07-27 23:35:09 | `1b6e39f34ad6d06b` | —（既有點陣圖，無 builder） | ch4-method.md §4.3 |
| 圖 4-5 | `fig4-3_asymmetric-discount.png` | 2026-07-27 23:35:09 | `424520ffb486e741` | —（既有點陣圖，無 builder） | ch4-method.md §4.3 |
| 圖 4-6 | `fig4-4_periodic-intervention.png` | 2026-07-27 23:35:09 | `716c8ca03d8c4c1b` | —（既有點陣圖，無 builder） | ch4-method.md §4.3 |
| 圖 4-7 | `fig4-5_competitive-reward.png` | 2026-07-28 14:27:29 | `fd0a86bf90bab1c7` | —（既有點陣圖，無 builder） | ch4-method.md §4.4 |
| 圖 4-8 | `fig4-6_capacity-penalty.png` | 2026-07-28 14:27:29 | `bb8dd7c2327e784b` | —（既有點陣圖，無 builder） | ch4-method.md §4.5 |

> ⚑ **2026-08-21 狀態更新**：圖 4-8（容量懲罰）已隨 §4.5 Penalty Shaping 整節自論文移除（2026-08-21）。本行的 sync 紀錄保留作 provenance；圖 4-8 不再是需要監控同步漂移的有效論文圖。現行 sync 追蹤對象為圖 2-1、圖 3-1、圖 4-1 至圖 4-7（共九張）。

## 偵測到漂移時要做什麼

1. **PNG 變了** → 該圖的內容改過：重讀「論文位置」那一節的正文與圖說，確認仍相符。
2. **builder 或 editable SVG 變了、PNG 沒變** → 多半是改了圖但忘記重繪論文實際嵌入的
   那一張（2026-07-20 發生過）。重跑 builder，再重新檢查。
3. **圖說變了、圖沒變** → 正常（改文字），確認新圖說仍描述得到圖上的東西即可。

確認同步後再跑 `--update` 重設基準。
