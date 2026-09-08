---
name: v015r-fail-origin-adjudication-2026-09-03
description: V0.15-R 371D reference gate 三初始化全 FAIL 後的結構裁定（2026-09-03）— 缺失變數是 focal 在 reference joint 下的 origin（占用、功率領頭、身分），裁定 NEXT_B
metadata:
  type: project
---

V0.15-R（result sha 215de261…）FAIL：h=12 一致率 0.84→0.64/0.68/0.67、pivotal 0.65/0.57/0.55、stable 0.64/0.69/0.69、
支持率 0.34/0.32/0.31。在密封 shard 上做純描述統計（未訓練）得到：P(pivotal | origin 在 reference joint 下無 peer)=0.0%
於所有脈絡；origin 與 committed incumbent 相同者僅 ~36%，V0.14 的 incumbent globals 不描述 origin；per-action scorer 只能讀
destination 的 reference 區塊，讀不到 origin 列的 o_c、gap_c；checkpoint 的錯誤改動集中在 o_c=0 列，corr(max Q3, o_c) 為負。
用 origin+destination 區塊寫成的相容規則（leader 需嚴格大於，平手不改 RF 最大值）precision 1.000 / recall 0.976。
只用 (origin peers, dest peers) 25 格分箱均值的政策，TRAIN 擬合、VAL 評估，三 lineage 全過五條凍結 clause
（pivotal 0.63–0.69、stable 0.97–0.98、支持 0.93–0.97、一致率 +7–9 點、h1/h2 非劣）。

**Why:** ZR 目標分解為 origin relief（列層級）− destination loss（動作層級），且 g 也依賴 origin 領頭；
這是表示缺口而非目標或 loss 缺陷。A（支持門）改變單一 argmax 規則又修不了列層級盲點；C 的 pair-delta
非必要，因為結構是加法而非差分。物理依據：每波束 RF 功率=服務用戶鏈路功率最大值；速率=(B/負載)·log2(1+γ)。

**How to apply:** 下一個 gate = 402D（371 + origin 身分區塊 1[k_u(a)=k_u(c_u)] + 三個 origin globals：o_c、s_c、gap_c，
即既有三個 reference 區塊在 origin 的值），其餘（learner、loss、3000 updates、三脈絡平衡、五條 clause）不變，
fresh worlds 2026111001–06、inits 2026111101–03（2026111xxx 區塊未用過）。預測：o_c=0 列的改動率 ≤2%。
FAIL → STOP_C3_STRUCTURALLY，不再換家族。不可辨識的殘餘：peers 在 reference joint 下的即時容量（振幅殘差）。
相關：[[v015r-reference-gate-launch-audit-2026-09-03]]、[[v014-q3-probe-stop-design-adjudication-2026-09-03]]。
