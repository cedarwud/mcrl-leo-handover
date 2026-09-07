# ch5/ch6 跨模型 voice/claim review — 結果 (2026-06-29, local controller)

> NEXT QUEUE #1 (WRITING-HANDOFF §10.8)。codex(gpt-5.5,xhigh,full-repo)+ agy Gemini 3.1 Pro,
> refute-by-default,餵 RED LINES(FRAMEWORK-SPEC §7)+ VOICE-CALIBRATION + 控制器已驗 authority 數字。
> G1 `aa877676` / EUV `389eaaef` 全程唯讀未碰。

## 跨模型裁決
- **agy Gemini 3.1 Pro = VERDICT: SOUND**(無 RED-LINE 違反;3 MINOR:如實列出 / TABLE-5.3 CI 微誤 / §5.5 k≥13 轉負不精確)。
- **codex gpt-5.5 (xhigh, full-repo 讀真 artifact) = VERDICT: NOT-SOUND**(1 BLOCKER + 1 MAJOR + MINOR)。
  - BLOCKER = §5.2「不是訓練不足」載重因果未標 grounded + 太絕對。
  - MAJOR = TABLE-5.3 caption「單一種子的點估計」⇄ 同列顯示 95% CI 矛盾。
- **控制器裁決:** codex BLOCKER **非** RED-LINE 紅線違反(非假因果/假贏/假根因)= rigor/tagging 補強;agy/codex 分歧採嚴格方,**全部修**。無一改動實際結果或 win 框架。

## 已套用 11 處編輯(全 SOUND-WITH-FIXES;只動 ch5+ch6 中文散文)
1. §5.2 — 軟化「不是訓練不足」絕對因果 → 「主要…而非單純訓練不足」+ 標 grounded + 指 §5.4 cross-over。(codex BLOCKER)
2. §5.2 — VOICE「載入爆掉」→「負載超過容量」。
3. TABLE-5.3 — B0 上界 +3.6→**+3.7**;B2 [-0.5,+9.7]→**[-0.4,+9.8]**;A2 下界 4.52→**4.53**。(三家一致)
4. TABLE-5.3 caption — (E6 我改「單一訓練種子+48ep bootstrap CI」;後被並行 session 以 5-seed caption 取代,見下。)
5. §5.3 — VOICE「如實列出」刪;「衝高/衝到最高加權分數」→「提高/最佳化」。
6. §5.4 — cross-over 有效波束「約 11」→ A1「約 10.6」/ B1_xover「約 10.3」(eff 10.58/10.26)。
7. §5.5 — 「k≥13 A2 轉負」不精確 → 「k≥14 時 A2 轉負」(k=13 A2 仍 +1.7e-6 正)。(agy)
8. ch6 §6.3 — 「移動平均」→「平滑後的曲線」(Gaussian σ=1.3 非移動平均;handoff §10.8 已標待定)。

## 控制器已驗 authority 數字(全 artifact 直讀吻合)
TABLE-5.3/5.4/5.5 + cross-over + r1 軸貢獻(2.2e-4→8.4e-4)+ §5.5 EE 3.9e12→1.0e12 + TABLE-5.5 全 13 點
↔ smoothed CSV `scratch/final_figures/fig5_4_kcap_sweep.csv` 全吻合。win-zone 判定 CI 直接支持。

## §5.3 並行 session 5-seed 升級 — 已分流處理(2026-06-29 收尾)
本次 review 進行中,**另一個 session 把 §5.3/TABLE-5.3 的 DQN_scalar 從單種子升級成 5-seed**
(6.10e-4/min_cov 0.110/單種子 → **6.41e-4 / min_cov 0.00 / 5 種子平均**)。這是**對的升級**(= SESSION-H
5-seed nail),也把 codex 的 caption MAJOR 用更權威方式解掉。逐項複驗(field-dqn-RESULT.json `per_objective`):

- **DQN_scalar 整列全 grounded ✓**:jw 6.412e-4 [5.96,6.87]、min_cov 0.0、**qos 0.89229→0.892**(qos mean,非 qos_min)、
  **active 12.776→12.8**、jain 0.6854→0.685。(先前把 qos 0.892 / active 12.8 flag 成可疑 = 誤判,實為 grounded。)
- **「A1 Jain 0.99」= 查無源且不可算 → 已修(移除)。** `route-b-factorial-RESULT.json` 0 個 jain 欄;A1 `per_episode`
  只有 {calib_Jw,qos,cap_bump,min_cov,active},**無 per-user 吞吐序列** → jain_crosstime(`dqn_baselines.py:487`)
  無法從 artifact 算,需 A1 rollout 重跑。fix = 改成單邊 grounded:「DQN_scalar Jain 約 0.69,顯示它把吞吐集中在
  少數使用者」(保留 grounded 的 0.6854,丟無源的 A1 0.99);論點由已 grounded 的 min_cov 0.999 vs 0.00 撐。
  順手修「餓死/覆蓋率」口語 → 「沒被服務到/覆蓋」。
- **剩 1 個未解(並行 session domain,不搶改):** caption 寫「DQN_throughput 為 5 種子平均」但 TABLE-5.3 行仍
  factorial 值 3.80e-4(0.04/0.635/7.0;field-dqn 5-seed 應 ~3.54e-4/min_cov 0.0)= 半更新不一致。row 本身 grounded
  (factorial);錯在 caption 的 5-seed 歸屬。**並行 session 收尾時:要嘛把 DQN_throughput 列更新成 field-dqn 5-seed
  (連帶 §5.3 line 80 的 3.80e-4 引用),要嘛 caption 只把 5-seed 歸給 DQN_scalar。**(兩種都行,屬其 propagation 決定。)

**⇒ §5.3 = 本次 review 後又被並行 session 動過 → 那次 5-seed 改動已逐項複驗(全 grounded,A1 Jain 已修)。
唯一遺留 = DQN_throughput row/caption seed-basis 一致性(待並行 session)。ch5 其餘 + ch6 = 過本次 cross-model + 修畢。**

---

## scratch/final_figures/ 審查(2026-06-29,同 session)— punch-list 給圖整合(NEXT #2)
數字全 grounded(CSV 直讀對齊 RESULT.json + field-dqn;含 5-seed DQN + TABLE-5.5 全 13 點)。命名 MCCRL 對照一致。

**已修(MANIFEST.md 文字,本 session):**
- RED-LINE #5:line 11「beats by **3.85x** on EE」headline 移除 → 「substantially raises EE + 維持覆蓋」+ 註明禁倍數。
- stale CSV 名 `fig5_k_cap_matched_sweep.csv`(不存在)→ `fig5_4_kcap_sweep.csv`(+raw)。

**待調整(下個 session / visual-lab):**
- **A [一致性,需 protocol 決定]** DQN_throughput 圖⇄表:FIG-5.2 用 field-dqn **5-seed**(3.54e-4/min_cov 0.0),
  TABLE-5.3+§5.3 用 factorial(3.80e-4/min_cov 0.04)。⚠ TABLE-5.3 的 DQN_scalar 也已是 field-dqn 5-seed(不同
  harness)→ **決定:兩個 field-DQN 都用 5-seed(圖一致,需 caption 揭露 harness 混用)還是全表回 factorial
  matched(G3 較乾淨,但 DQN_scalar 退回單種子 6.10e-4 = 放掉 SESSION-H 5-seed nail)。USER/圖 track 拍。**
- **B [label]** ch5 [FIG-5.3](Jw A2 vs B0)+[FIG-5.4](維度消融)↔ 圖檔 Option A(分開 `5_4a-e`)/ Option B
  (combined 4-panel)。選一個 + 對齊標籤。combined panel(a) 含維度消融線,與 §5.3「只 A2 vs B0」略出入 → Option A 較乾淨。
- **C [可讀性]** FIG-5.1 `r3` panel = penalty(越負越差),caption 註「越接近 0 越好」;ch5 §5.2 FIG-5.1 caption
  line 55 寫「公平性」但 panel 是「負載平衡 r3」→ 用詞改「負載平衡」(load-balance≠公平/覆蓋)。
- **D [選配]** FIG-5.2 加 Pareto frontier 虛線(非支配集 {DQN_scalar,A1,AF})。

**確認 OK:** FIG-5.2 DQN_scalar min_cov 0.0(5-seed)⇄§5.3 已一致;FIG-5.1 A1 Jw 略高 A2 = 誠實(RED-LINE #2);
FIG-5.4 crossover ~k=10-11 + min_cov 全程 1.0 ⇄ win-zone k≤12 ✓。fig5_5 訓練曲線 = 不進論文(USER)。
render script = `scratch/render_thesis_chapter5_plots.py`(圖重生在此)。
