---
name: v020-repriced-c3-gate-adjudication-2026-09-05
description: V0.20 repriced-C3 λ-confound gate 的獨立裁定：收據有效、REVISE_NOMINAL_Q3；exact ZR 在修正定價下存活、nominal 掉到 2/3 lineage；首輪序列化失敗只曝露 BASE 值；下一步提議 EXPECTED_ZR（fading 平均）可部署天花板 gate
metadata:
  type: project
---

2026-09-05 由 Fable 5.1 以獨立科學控制者身分裁定 V0.20 repriced-C3 gate
（`artifacts/multi-catfish-v020-repriced-c3-gate-20260904-r1`）：

- 收據有效。36 shard、seal、field digest、Q 參數不變、旗標全 false 皆獨立重算通過；
  runner 在 prelaunch→relaunch 之間只多了 16 行（NumPy 標量序列化修補，traceback 行號錨點吻合）。
  伺服器上 `server-run-serialization-failure/` 首輪在修補前已印出 7 個 BASE shard 的 EE，
  treatment 臂全部在寫檔前 TypeError，未曝露任何對比結果；7 個 BASE row 物理欄位與重跑逐位相同。
- 結果（frozen 4 條款）：EXACT_ZR +0.985%（4/4 world、3/3 lineage）通過；NOMINAL_ZR +0.424%
  （3/4 world、2/3 lineage，lineage 2026092103 為 −0.10%）不通過 → `REVISE_NOMINAL_Q3`。
  V0.18 的 2/3 lineage 規則下 nominal 本會過；V0.20 契約改成 3/3，是凍結前的加嚴。
- λ 混淆對 exact 臂被證偽：λ' / η_BASE 從 0.72 變 1.03，效應 +1.031% → +0.985% 幾乎不變。
  機制仍是聯合波束整併（bits −5.3%、能量 −6.2%；同狀態聯合效應約佔一半，軌跡分歧佔另一半；
  step-0 exact 聯合 bits 12/12 為正且能量為 0，之後聯合 bits 多為負）。
- 服務率三臂皆 1.000，服務條款在此面板為空操作。
- 提案下一步：V0.21 `EXPECTED_ZR`（同一 live 反事實機制，對輔助 keyed fading 抽 K 次平均，
  不用 physics 事件的實現值）作為 ZR 家族的「可部署資訊天花板」，fresh 4 世界 × 3 lineage、
  同四條款、heavy → Ubuntu server；不授權任何 episode 訓練。

**Why:** 這是 C3 路線的分岔點；exact oracle 用了 physics 事件的實現 fading，任何可部署 Q3
都拿不到，所以 nominal（+0.42%）比 exact（+0.99%）更接近 learner 的真實天花板。

**How to apply:** 後續若有人引用 V0.20 說「C3 機制已證實」，要指出 claim ceiling 是 TRAIN
oracle 開發證據、且 nominal 未過；任何 Q3 learner gate 前先看 [[v019-learner-gate]] 的
判準與 [[c3-stop-adjudication-2026-09-01]]。
