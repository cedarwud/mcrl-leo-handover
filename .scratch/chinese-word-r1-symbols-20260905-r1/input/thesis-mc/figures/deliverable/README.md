# 論文／口試可用圖 — 集中資料夾（2026-07-19 快照；2026-07-20 同步稽核）

> **★ 2026-07-22 現行狀態**：`fig-cdrl-vs-mccrl` 已自論文正文移除，不得作為交付圖重新嵌入。
> `fig-mcrl-architecture` 已作為圖 4-1 嵌入 ch4 §4.1；其餘嵌入狀態以 `FIGURE-SYNC-MANIFEST.md` 為準。


> **這是什麼**：把「本輪畫的 13 張概念圖」＋「現行論文沿用、可放的既有圖」集中一處，方便你取用於
> 論文與口試簡報。
>
> **⚠ 這是複製，不是搬移**（刻意）。正本仍在上一層 `thesis-mc/figures/`：
> - ch4 的圖是以 `figures/*.png` 相對路徑嵌入的——搬走正本會弄斷剛嵌好的論文圖。
> - builder pipeline（`src/*.py` 互相引用 `figkit`、寫 `figures/*.svg`、`eye/*.json`）也依賴原位置。
> 所以這裡放的是**輸出副本**。若哪張圖之後重繪，這裡的副本會過期——以上一層的正本為準，或重跑對應 builder。
> 若你要的是把「正本位置」整個搬過來（連 ch4 嵌入路徑一起改），那是另一件事，跟我說我再做。
>
> **圖說**：每張圖的正式繁中圖說在 `captions.md`（＝ `FIG-CAPTIONS-2026-07-19.md` 的副本）。
> 圖上文字＝英文，圖說＝繁中，兩者分工。
>
> **視覺鍵（USER-SET 2026-07-19）**：**淺沙色填底＝本論文相對 MODQN 基準新增的元件**；白底＝沿用／系統模型。
> 實線框＝部署路徑；虛線框＝僅訓練期。灰階列印下填色仍可辨（已驗）。

---

## A. 本輪畫的 13 張概念圖（`concept-figures-this-session/`）

`png/`＝可直接丟進投影片或看的點陣圖（2× 解析度）；`svg/`＝可進 Illustrator 編輯的向量原始檔。

| 檔名 | 章節 | 內容 | 論文狀態 | 口試簡報用途 |
|---|---|---|---|---|
| ~~`fig4-2-mccrl-architecture`~~ | — | 舊 MCCRL 整體架構 | **未嵌入；已由 `fig-mcrl-architecture` 取代** | 不再交付 |
| ~~`fig-cdrl-vs-mccrl`~~ | — | 舊 CDRL ↔ MCCRL 對照 | **未嵌入；2026-07-22 自正文移除** | 不再交付 |
| `fig-mcrl-architecture` | §4.1 | MCRL 訓練架構 | **已嵌入，圖 4-1** | 框架總覽 |
| ~~`fig4-7-training-deployment-flow`~~ | — | 舊訓練／部署備選圖 | **未嵌入；已淘汰** | 2026-07-22 移除現行訓練／部署圖後不再交付 |
| `fig-stratification` | §4.3 | 能效分層（三路分流） | 已嵌入 ch4，圖 4-2 | 訓練策略一 |
| `fig-intervention-annealing` | §4.3 | 週期性介入 | 已嵌入 ch4，圖 4-4 | 訓練策略三 |
| `fig-competitive-reward` | §4.4 | 競爭獎勵機制 | 備選；論文現行版本為圖 4-7 | 機制：同狀態配對比較 |
| `fig-capacity-penalty` | §4.5 | 容量懲罰 $L_{\mathrm{cap}}$ | 已嵌入 ch4，圖 4-6 | 訓練目標塑形 |
| `fig-problem-overcrowding` | §4.1–4.2 | 問題圖：過度集中怎麼發生 | 圖說備妥，待 slot | **口試第一張**：你解決什麼問題 |
| `fig-momdp-structure` | §4.1 | 多目標 MDP 結構 | 圖說備妥，待 slot | 問題形式化 |
| `fig-system-scenario` | §3.1 | 系統情境（方塊圖） | ch3 圖，待授權後 slot | 系統設定、容量閘、換手成本 |

## A2. 模型示意數據圖（`model-illustration-figures/`；matplotlib 數據曲線）

> **工具鏈不同**：A 夾的 13 張是 figkit 方塊圖；此夾放 matplotlib **數據曲線**（把公式畫出來），走
> 「圖表繪製標準」（plain line、無信賴帶、每圖附 CSV），不走方塊圖的四道 gate。分類同樣是 `png/`＋`svg/`
> （另加 `data/` 放 CSV）。細節與誠實邊界見該夾 `README.md`。

| 檔名 | 章節 | 內容 | 論文狀態 |
|---|---|---|---|
| `fig-beam-pattern` | §3.1.2 | 波束增益 $G^T(\theta)$ 隨偏軸角變化（式 3.7a 貝索型樣） | **USER 決定不進論文（2026-07-20）**；留作素材／簡報備用 |

## B. 現行論文沿用的既有圖（`kept-raster-figures/`，點陣，無向量原始檔）

**本輪已逐張開圖核對內容**（不是只信 manifest 標籤）：保留的系統模型圖之符號與現行 notation-table 一致
（beam (s,v)、θ/α/d，無 cell/coordinate 用語）。原生解析度 321 DPI，可印。

| 檔名 | 論文 | 內容 | 核對結果 |
|---|---|---|---|
| `paper-3-1-system-model.png` | 圖 3-1 | 多波束系統模型（角度幾何剖面 θ/α/d、波束錐、換手） | ✓ 現行（舊 `fig2.png`） |

---

## C. 口試簡報：重要提醒

這 13 張是**論文規格**（實體寬 175mm、節點字 ≈8.3pt）。丟進投影片能用，但字是為 A4 近距離閱讀設計的，
**後排會偏小、資訊密度偏高**。真正為投影片優化的一組（16:10、大字少框、一個 headline）＝**尚未做**，
是下一個 session 的工作（見 `../HANDOFF-FIGURES-2026-07-19.md` 剩餘工作 1）。若要我接著做那組，說一聲。

口試用圖的建議順序：問題圖（動機）→ MCRL 架構（完成版面微調後）→ 各機制圖。

## D. 為什麼有些既有圖【不在】這裡（刻意排除，別誤用）

| 舊檔 | 原本是 | 為何排除 |
|---|---|---|
| `fig7.png`（舊 圖 4-3） | 壅塞情境狀態擴充 | **REMOVED FROM THESIS (2026-07-22)**—the old cell/coordinate drawing and its redrawn successor were both removed; Eqs. (4.7)–(4.8) retain the method definition. |
| `fig1.png` | 圖 1-1 整體概觀 | **USER 決定不用（2026-07-20）**——畫的是已移除的協調式波束分配，圖說含第五章結果宣稱。已自論文移除（引用句＋嵌入＋圖說），**第一章現無圖**；圖檔保留不刪。口試亦不建議用。 |
| `fig4/fig5/fig6/fig9/fig10.png` | 舊 4-2/4-5/4-6/4-7/4-3 | **本輪已取代**（含已移除的分配步驟或與現行機制不符） |
| `fig8.png` | 舊「協調式波束分配」 | 該概念**已從敘事移除**（decoder 退出）——絕不可放 |

 ## PNG 渲染修正（2026-07-19，USER 抓到「大片空白」後修）

先前 PNG 有大片空白＝渲染錯誤：Chrome 視窗依 viewBox 像素（1440）開，但 SVG 內建顯示尺寸是
`175mm`（≈661px），內容只填了視窗 ~44%、其餘是空白，等效只有 ~192 DPI。**已修**：改成把 SVG 依
viewBox 像素渲染、填滿畫面，現在每張 2880px 寬 ＝ 175mm 下 **~418 DPI**，內容填滿、不糊。
SVG 本身是向量、放大不糊；`width="175mm"` 是給論文用的正確實體尺寸，螢幕上顯示小是正常的。

## E. 要編輯或重生

- 改內容：改 `../src/build_<name>.py` → 重跑（會過四道 gate）→ 重新 render PNG → 更新此資料夾副本。
- 規格與 USER-SET override：`../FIGURE-MANIFEST.md` §2。
- 別手改 `svg/` 裡的 SVG（下次重繪會蓋掉；驗證器也只比對元素數量）。要向量微調就改 builder 或在 Illustrator 另存。
