# FIGURE-HANDOFF — 新 thesis(mc-modqn 版)圖(貼進「圖」新對話)

> 一句話:在 `research-visual-lab` 專案的 pipeline 裡,做 **ch1–3 三張穩定圖**(FIG-1 overview / FIG-2 system model
> / FIG-3 MODQN baseline)+ **ch4 兩張方法圖**(FIG-4 Multi-Catfish 框架架構 / FIG-5 演算法流程圖)+ 選配 §3.4 對照圖。
> 盡量**改現有資產**。符號/標籤對齊 **MODQN 原論文聖經**;**r1 = EE(不是吞吐量)**。
>
> **★ 更新 2026-06-28:ch4 路線已拍板 = route-B fork②(catfish 式訓練 + 協調式波束分配)→ FIG-4/FIG-5 現在要做。**
> **FIG-4/FIG-5 的內容權威 = `thesis-mc/FRAMEWORK-SPEC.md`(§5 整體流程 + §3 估值+分配兩步)。圖照那份畫,跟 ch4 文字同源。**
> 敘事 = Multi-Catfish 框架贏(誠實);catfish = 具名核心組件;協調式波束分配 = 框架內整合多目標估值、在 k_cap 限制下選波束的步驟(**非獨立於 catfish 的模組**)。見 FRAMEWORK-SPEC §7 RED LINES。
> **★ 更新 2026-06-29: `scratch/final_figures` 的結果折線圖不再畫信賴區間 band / error bar。CI 只留在 CSV / 表格用於 win-zone 與顯著性判讀;後續圖整合不要把 CI band 加回折線圖。**
> **★ 更新 2026-06-30(ch3→ch4 演算法邊界重構): MODQN baseline 架構圖(本檔 FIG-3 / `mc-fig3-modqn.png`)的論文 slot 由 ch3 FIG-3-2 改為 ch4 §4.1 = 論文 slot FIG-4-1;ch4 方法圖論文 slot 全部 +1(框架=FIG-4-2 / 折扣=FIG-4-3 / 回放=FIG-4-4 / 壅塞=FIG-4-5 / 分配=FIG-4-6 / 流程=FIG-4-7)。PNG 檔名與內容不變,只是論文章節 slot 重編;production 端(本檔 FIG-1..6 命名)不受影響。詳細 slot map 見 `WRITING-RULES.md` R7 表 + `FIGURE-EXPLAINER.md`。**
> **★ 更新 2026-06-30(✅ 圖插入完成,track-4 figure-insert): 10 張 arch+cmp PNG 已由本 RVL repo 改名複製進 producer repo `modqn-paper-reproduction/thesis-mc/figures/figN.png` 並插入論文 markdown。`mc-*→figN` provenance map(D1 論文閱讀順序): `mc-fig1-overview→fig1`/`mc-fig2-sysmodel→fig2`/`mc-fig3-modqn→fig3`/`mc-fig4-framework→fig4`/`mc-figC-discount→fig5`/`mc-figD-replay→fig6`/`mc-figB-congestion→fig7`/`mc-figA-allocation→fig8`/`mc-fig5-algorithm→fig9`/`mc-cmp-cdrl-ours→fig10`(§3.4 新 slot FIG-3-3)。**本 RVL repo 的原始 PNG 保留 mc-* 檔名不動**(producer 端用複製檔 → thesis 不依賴 RVL 名;RVL 同步改名 figN = optional follow-up,待 USER。動 RVL 改名須一併改 `build_*.py`/`compile_all_pngs.py`/`README.txt`/`REUSE-INVENTORY.md` 引用 + 重跑 build 驗證,否則 build 斷)。producer 端 docx build(`build_ris.sh`)已 patch 為 copy figures→$BUILD + cwd=$BUILD,10/10 圖嵌入驗證過。bilingual build + EN 圖插入 = deferred。**圖內容/檔案本體未改。****

## 0. 在哪做
- 專案:`/home/u24/papers/research-visual-lab`(讀其 `README.md` + `figures/REUSE-INVENTORY.md` 先)。
- pipeline:每張圖 = `*.editable.svg` + `*.viz.json` + `*.validation.json`,有 `check_layout.py`。沿用此流程。
- 大量可重用資產在 `figures/`(見下表)。

## 1. 本任務要的圖(ch1–3,穩定,與 ch4 路線無關)
| slot | 圖 | 章 | 改哪個現有資產 |
|---|---|---|---|
| **FIG-3** | MODQN baseline 架構(三並行 Q 網路 + per-user 選動作 + 純量化) | ch4 §4.1（重構後；論文 slot=FIG-4-1） | `figures/modqn-baseline-training-framework.editable.svg` 或 `figures/modqn-arch/` — **最接近,直接改** |
| **FIG-2** | 系統模型(LEO 衛星 / 多波束 / 地面使用者 / 偏軸角幾何 / 換手) | ch3.1 | `figures/forecast-modqn-system-arch.editable.svg` 或 `figures/scenario.svg` — 改 |
| **FIG-1** | Overview / 三點貢獻總覽(EE 獎勵 + Multi-Catfish per-objective) | ch1 | `figures/forecast-modqn-method-pipeline.editable.svg` — 改(去掉 forecast/蒸餾元素) |
| (FIG-6) | §3.4 Catfish-DRL vs 對手模型(可做圖或留表) | ch3.4 | `figures/cdrl-vs-ours/` — 改標籤 |

## 1b. ★ ch4 方法圖(現在做;內容權威 = `thesis-mc/FRAMEWORK-SPEC.md`)
| slot | 圖 | 章 | 內容(照 FRAMEWORK-SPEC) | 改哪個現有資產 |
|---|---|---|---|---|
| **FIG-4** | Multi-Catfish 框架架構(以三隻鯰魚為核心,估值+分配兩步銜接) | ch4 | **估值**(三個 per-objective 鯰魚 Q + χ_u 壅塞輸入 + 不對稱 γ + 價值分層回放)→ 每使用者每候選波束的多目標綜合價值 `b_u(a)=Σ_k ω_k Q_k`;**分配**(框架內的協調式波束分配:每顆衛星 k_cap 開集 → 指派)。兩步是框架內彼此銜接的流程,**非兩個獨立模組**。FRAMEWORK-SPEC §5/§3。 | **重畫內容**;可借 `figures/modqn-arch/` 元件風格,**勿**照搬 route-C 蒸餾框 |
| **FIG-5** | 演算法流程圖(訓練 + 線上推論) | ch4 | 訓練迴圈:reset → χ_u → 三 Q 綜合價值 → 該欄分配規則(argmax/協調式波束分配)+ε → step →(r1=EE,r2,r3)→ 存 step-bundle(高 J 進優先池)→ 抽 batch(catfish ρ=0.25)→ Double-DQN 不對稱 γ_k 一步 TD → 同步 target / 存 ckpt。線上:狀態 → χ_u → 綜合價值 → 協調式波束分配 → 動作。FRAMEWORK-SPEC §5。 | 新流程圖;借 pipeline 風格 |

- **標籤用詞(binding):** 用「分配規則 / 協調式波束分配 / 綜合價值 / 壅塞情境 χ_u / 多目標 Q」這類白話;**不要**「解碼器 / decode / 蒸餾 / distilled / amortized / decorative / 2.8× / collapse headline」這些 route-C/jargon 字樣(FRAMEWORK-SPEC §7、WRITING-HANDOFF §4)。
- **誠實(binding):** FIG-4/FIG-5 是**方法/架構**圖,**不放結果數字**(ch5 結果圖另議、server-pending);不畫成「鯰魚驅動解崩」的假因果(解崩來自框架的協調式波束分配步驟,把它畫成框架內的一步,別標成獨立於 catfish 的模組)。

## 2. ★ 不要做 / 不要直接重用的
- **ch5 結果圖(崩潰曲線 / Pareto / k_cap sweep)本任務先不做** —— server k_cap∈{6,9,12} sweep 還在跑,等資料齊再議。
- `figures/per-objective-multi-catfish-modqn.editable.svg` = **route-C 舊版(含蒸餾/decorative 框)= 錯脊椎**,FIG-4 要照 FRAMEWORK-SPEC 重畫內容,**別**當成品。
- `figures/forecast-*`、`figures/ca-cpbr-*`、`collapse-mechanism` 等 = route-C/forecast 線資產,**只借風格/元件,不照搬語意**。
- `scratch/final_figures` 的 Chapter 5 折線圖已採「只畫曲線、不畫信賴區間」政策;不要在 visual-lab 或 Origin 重製時補回 CI band / error bar。

## 3. ★ 標籤/符號規則(binding)
- **符號聖經 = MODQN 原論文**:`paper-catalog/ref/2024_09_Handover_for_Multi-Beam_LEO_Satellite_Networks...MORL.pdf`。圖內符號($\mathcal{U}/\mathcal{S}/\mathcal{V}$、$\gamma$、$R$、$\theta$、$N(t)$、$s_u/a_u$、$Q$…)用這篇 + ch3 文字的記號,**圖↔文字同一套**。
- **r1 = 能量效率(EE / $\eta^{EE}$),不是吞吐量。** 任何舊圖的「throughput / 吞吐量」第一目標標籤要改 EE。
- 主角名 = **Multi-Catfish**(per-objective 輔助代理,延伸 CDRL 鯰魚效應);**不要**「蒸餾 / distilled / amortized / decorative / 2.8× / collapse headline」這些 route-C 字樣。
- FIG-3 是 baseline = 照原始 MODQN 畫(三並行 Q + per-user-argmax + 純量化),**不要**加鯰魚(baseline 要乾淨,之後對照才清楚)。

## 4. 對齊 + 收尾(USER 的「補完圖再用圖改文字」)
- 文字對話會在 ch1–3 放 `[FIG-1]/[FIG-2]/[FIG-3]` placeholder + caption brief。**圖的標籤用詞要對齊那份 caption / ch3 符號**。
- 兩個對話**共用同一套記號(聖經 + ch3 符號表)**→ 可平行;最後一次性微調圖標籤 ↔ 文字符號一致即可。
- 圖檔產出狀態權威若有,記在 `research-visual-lab` 那邊既有的 HANDOFF;本專案這邊只引用最終 PNG/SVG。

## 5. 邊界
- 不碰本 repo 的 G1 `modqn.py`(`aa877676`)、env EUV(`3cd5000a`);圖是衍生物。
- 誠實:baseline=原 MODQN;主角=Multi-Catfish(提案/待驗證);不放未驗證的效果數字、不放結果圖(ch5 結果圖另議、server-pending)。
