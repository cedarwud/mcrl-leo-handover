# FABLE C3 SOURCE AUDIT — clean-room scientific adjudication of the Multi-Catfish third head

Date: 2026-09-04
Adjudicator: Claude Fable 5.1 (fresh context, read-only)
Work class: non-heavy, read-only scientific/design audit. No simulator world, source harvest, learner update, episode, sweep, or TEST data was run or opened. No existing source, authority, paper, symbol table, or artifact was edited. This file is the only artifact created.

Evidence labels used throughout:

- **VERIFIED FACT** — read directly from canonical code or recomputed from raw JSON/NPZ arrays in this session (file paths given).
- **DERIVATION** — mathematical consequence of verified facts.
- **INFERENCE** — best explanation consistent with the facts; could be wrong.
- **PROPOSAL** — a design or test recommendation.
- **UNKNOWN** — could not be established without running new experiments or opening data not present locally.

Order of work (as required): Phase A read only `energy_efficiency.py`, `ee_axis_evaluation.py`, `ee_surplus_targets.py`, `env/step.py`, `env/link_budget.py`, `env/service.py`, `env/interference.py`, `env/antenna.py`, `env/action_contract.py`, `runtime/ee_axis_state.py`, `algorithms/ee_axis_pairwise.py`, and the derivation in Section 2–4 was fixed before any C3 design or historical document was opened. Phase B then opened the listed contracts, code, and artifacts. All headline numbers below were recomputed from `result.json` / `source.npz` / `validation-predictions.npz` / `background.npz`, not copied from prose. A memory index of prior sessions was visible in the session context; none of its conclusions were used as evidence.

---

## 1. Executive Verdict（執行裁定）

**主裁定：REDESIGN_R3_TARGET。**

1. **三頭目標在物理上可行、數學上不保證、目前未證明。** 模擬器提供三個彼此不同的因果通道：（a）自身鏈路品質與自身觸發的邊際能量；（b）功率段（segment）隨幾何漂移的時間軌跡與未來可行性；（c）共用資源外部性——同波束頻寬時分稀釋/解除、共通道干擾、以及共用功率帳單。第三通道真實存在，但它對 EE 的實際貢獻方式是「群體波束整併」（多個使用者同時離開同一波束使其熄滅），這是一個聯合效應，單邊反事實 target 本質上看不到它。三個獨立可加頭各自有正邊際消融效果是「可能」而非「必然」，第 4 節給出成立條件與反例。

2. **現行 ZR/R3 target 的實際機制不是它宣稱的機制。** V0.12、V0.13、V0.18 三個獨立 oracle 面板的簽名完全一致：FULL_ZR 相對 DROP_C3/BASE 的**位元下降 4.3–5.7%、能量下降 5.0–6.6%、EE 上升 0.63–1.10%、活躍波束步數下降**（V0.18 每步基準 44.2 → 選定 42.9 支波束）。ZR 只計入「零邊際能量」的正向重分配、且不含任何能量項，卻透過相容性閘門在群體層面只允許波束熄滅、不允許點亮，於是 EE 增益全部來自分母。單邊 target 預測每步非焦點位元 **+8.9e10**（淨 +5.3e10），實際聯合結果為 **−2.6e10 bits/step、−255 J/step**：符號翻轉，單邊可加性失效。

3. **λ0 定價過時，C1 低估能量代價約 28–30%。** 凍結的 λ0 = 84,994,621 bit/J（hex `0x1.443a8f481639ap+26`）被 Q1、Q2、所有 C3 oracle 共用；但現行 Q1+Q2 背景的實測 EE 為 1.184e8（V0.18 BASE）至 1.210e8（V0.13 DROP_C3）。依第 2 節推導，固定乘數 surplus 與 ratio-of-sums 條件同號的充要條件是 λ0 落在 [η_M, η_C] 內；λ0 低於區間 28% 時，每支波束的能量價格被算成 1.63 κ 而非 2.28 κ，而一支波束一步的平均位元約 2.33 κ——**在 λ0 下獨佔一支波束看起來有 +0.7 κ 的淨利，在真實 η 下接近零**。這解釋了 V0.11 所有 C3 變體「擴張活躍波束」並虧損、以及 V0.12 起 ZR「只准熄滅」就獲利的整段歷史：ZR 的 EE 增益與 λ0 誤定價混淆，尚無法歸因於一個獨立的第三機制。

4. **V0.19 失敗是 E（多重原因），主因為 C，次因 A，B 部分成立，D 不成立。** target 中 89.9% 為負、正值僅 3.65%（相容且為正的僅 3.7%），pivotal 列 15.5%；uniform MSE 讓學生學會「一切皆有害」（預測均值 −0.22…−0.32 κ、標準差僅為 target 的一半），對正尾的排序 AUC 在相容集合上 0.46–0.61（≈ 隨機）；在 pivotal 列上學生把老師動作排在基準之上的比例 0–8%。TRAIN 損失確有下降（1.8→0.20），但 100 步更新不可能擬合 nominal 解碼器所需的 log/exp 結構；VALIDATION 與 TRAIN 分佈幾乎相同，故非分佈位移。state 足以支撐 nominal 等級決策（V0.18 nominal 對老師的 pivotal 一致率 84–92%），但 action-context 第 7 維（候選波束最大功率差／p_max）存在 −2.4e6 的離群值（2.0% 的合法項 |x|>10），對 tanh MLP 是條件數災難。單位一致（三頭共用 κ = 10,097,071,012.757 bits），故字面相加在量綱上有效，但定價（λ0）不對。

5. **下一步：不再修學習器，改 R3 target。** 最佳單一候選為**成本分攤外部性（CSE）**：z3 = 非焦點速率外部性 − λ·[Δ(焦點的公平能量份額) − Δ(單邊網路能量)]，其中份額 = 波束能量/佔用數 + 衛星基頻/衛星使用者數，恆等式 Σ_u share_u = P^N 使聯合動作的逐使用者 target 之和精確等於 ΔB − λΔE，直接把「整併經濟學」寫進單邊可測的 target，且不需相容性閘門、target 稠密、可由現有 228 維 lagged state 辨識。並行篩選：P2 = 僅能量份額修正頭（最小可證偽版本、平面學習器即可）；P3 = 保留 ZR 但改用物理結構化（nominal 公式＋殘差）學習器（控制臂，回答「只是學習器問題？」）。所有候選共用一個新鮮 TRAIN 物理面板，並以「λ 混淆證偽」為前置：在 λ′ = η_M 重新定價的背景下，若 ZR oracle 的 EE 增益消失，整個現行 C3 家族即被證偽為 λ 補償而非機制。

6. **未證明的事實必須寫在論文天花板上：** 目前沒有任何學習型 C3 通過過任何 gate；C2 學到的頭對其老師改變動作的一致率僅 7.5%（V0.14），FULL > DROP_C2 這一條與 C3 無關但同樣未有證據；所有 EE 數字都是 TRAIN 開發期 oracle 篩選，不是效能宣稱。

---

## 2. Canonical EE Derivation

### 2.1 What the simulator computes (VERIFIED FACT)

Per decision step (Δt = 30.08 s, H = 10 steps, U = 100 users, 28 candidate actions = 4 satellite slots × 7 cells; `env/constants.py`, `env/action_contract.py`):

1. Action a_u → association (s, v) → off-axis angle θ_u (`env/step.py:_resolve_physics`).
2. Link power p_u = p⁰·G^T(θ(τ))/G^T(θ(t)) with p⁰ = 0.825 W; a new segment starts at p⁰; feasibility p_u ≤ p_max = 1.65 W, else outage (`link_budget.recurrence_power_w`, `classify_link_power_feasibility`).
3. Service x_u = 1 iff legal and feasible; load U_b = Σ x; activation z_b = 1{U_b > 0} (`service.resolve_service`).
4. Beam power p_b = max over served users on b (`link_budget.beam_power_w`).
5. Interference at u: z-gated sum over co-colour radiating beams of p_b·G^T(θ_{u,b})·H·G^R(sep); intra-satellite co-colour (v'≠v) with G^R = max, inter-satellite all co-colour cells (`interference.co_channel_interference`).
6. SINR γ_u = p_u G^T H G^R_max/(I_u + σ²); rate R_u = (B^w/U_b)·log2(1+γ_u), B^w = 166.67 MHz (`shannon_rate_bps`).
7. Power: ξ_b = min(ξ_max, ξ_max√(p_b/p_sat)) with ξ_max = 0.35, p_sat = 5.218 W, so for every feasible beam P^p_b = √(p_b·p_sat)/ξ_max (concave in p_b): 5.93 W at p⁰, 8.38 W at p_max. P^f = Σ_s (N^act_s·0.338 W + 1{N^act_s>0}·0.200 W). P^N = P^f + Σ_b P^p_b (`pa_efficiency`, `supply_power_w`, `fixed_power_w`, `system_power_w`).
8. Endpoint: η = Σ_t Σ_u R_u(t)Δt / Σ_t P^N(t)Δt over the episode (`ee_axis_evaluation.evaluate_ee_axis_episode`), verified as ratio-of-sums by `EEAxisEpisodeEvaluation.verify`. Deployment executes only `argmax` over the masked sum Q1+Q2+Q3 (`ee_axis_pairwise.select_greedy_actions`).

Consequences that matter (VERIFIED FACT): beam load has **zero** direct energy effect (energy is per beam, ruling F-2); handover class (φ1/φ2) has **no** bits or energy effect anywhere in the physics (r2 is legacy only); a user joining an already-lit beam without raising its max power adds exactly zero energy; lighting a beam costs 6.3–8.7 W plus 0.2 W if the satellite was dark.

### 2.2 Exact condition for candidate C to beat reference M (DERIVATION)

Let (B_M, E_M), (B_C, E_C) be episode totals with E > 0, ΔB = B_C − B_M, ΔE = E_C − E_M, η_M = B_M/E_M, η_C = B_C/E_C.

η_C > η_M ⟺ B_C E_M − B_M E_C > 0 ⟺ ΔB − η_M ΔE > 0 ⟺ ΔB − η_C ΔE > 0.

Proof: ΔB − η_M ΔE = (B_C E_M − B_M E_C)/E_M = E_C(η_C − η_M), and ΔB − η_C ΔE = E_M(η_C − η_M). Both are exact Dinkelbach identities. Because f(λ) = ΔB − λΔE is affine in λ and has the sign of (η_C − η_M) at both endpoints, **f(λ) has the correct sign for every λ in the closed interval between η_M and η_C**, and can have the wrong sign outside it whenever ΔE ≠ 0.

### 2.3 Fixed multiplier surplus versus ratio-of-sums (DERIVATION + VERIFIED FACT)

The project's surplus is S_λ0 = ΔB − λ0ΔE. Then S_λ0 − (ΔB − η_M ΔE) = (η_M − λ0)ΔE. Therefore:

- exactly equivalent when ΔE = 0 (this is precisely the ZR compatibility case, which is why ZR was made λ-invariant);
- exactly equivalent at the aggregate level when λ0 ∈ [η_M, η_C] and the per-anchor terms are additive;
- otherwise biased by (η_M − λ0)ΔE: if λ0 < η_M, energy-spending actions are over-rewarded.

VERIFIED FACT: λ0 = 84,994,621.126 bit/J (hex `0x1.443a8f481639ap+26`; present in 6,880 E1/Q1 lineage receipts, in the V0.14 Q2 gate, V0.12 and V0.18 results). The realised reference EE of the frozen learned background is 118,424,223 bit/J (V0.18 BASE, `artifacts/multi-catfish-v018-relational-zr-20260904-r2/.../merged/result.json`), 119,840,000 (V0.12 DROP_C3) and 120,980,000 (V0.13 DROP_C3). Hence λ0/η_M = 0.72: **the frozen multiplier prices energy 28–30% below the operating EE**. In κ units (κ = 10,097,071,012.757 bits): one average active beam (285.1 W / 44.2 beams = 6.45 W) costs 1.63 κ per step at λ0 but 2.28 κ at η_M, while one beam-step delivers on average 1.04e12/44.2 = 2.33 κ. A user who lights a private beam with typical spectral efficiency therefore shows a surplus of about +0.7 κ under λ0 and ≈ 0 under the true criterion (INFERENCE on the typical magnitude; the comparison of prices is exact).

### 2.4 Additivity across users (DERIVATION)

Per-anchor targets are unilateral deviations against a fixed background; deployment applies argmax to all users simultaneously. The joint surplus equals the sum of unilateral surpluses only if effects are additive. They are not: energy is a shared per-beam cost, so if k users occupy beam A, the unilateral marginal energy of each leaving is 0 while the joint saving is e_A (public-good gap); conversely k users independently judged to "join B" jointly over-dilute B. VERIFIED quantification (Section 5.4): the ZR teacher's unilateral targets on VALIDATION anchors predict +8.86e10 bits/step of non-focal gain (net +5.26e10 after Q1's own-rate loss), while the executed joint teacher action in V0.18 realised −2.63e10 bits/step and −255 J/step. Sign flip of the bit effect; the EE gain came from the energy term that the ZR target does not contain.

---

## 3. Action-to-EE Causal Map

One focal action a_u at step t (VERIFIED FACT for the chain; magnitudes VERIFIED from V0.19 victim tokens and V0.18 per-step receipts):

| Channel | Term touched | Mechanism | Magnitude at the operating point |
|---|---|---|---|
| N1 own rate | numerator, t | own SINR (p⁰·G^T(θ(τ)) invariant for a continuing segment; p⁰·G^T(θ) for a new one), own bandwidth share B^w/U_b | median SINR 14.9 dB (nominal), per user-step ≈ 1.03 κ; solo beam ≈ 2.33 κ |
| N2a others: load sharing | numerator, t | joining beam b with k incumbents cuts each incumbent's rate by 1/(k+1); leaving refunds | 77% of the |Δrate| mass in the ZR victim panel |
| N2b others: interference | numerator, t | lighting/darkening a co-colour beam or raising a beam's max power changes I_v for co-channel victims | 23% of |Δrate|; 14% of victim rows are interference-limited (I₀ > N), median I₀/N = −15 dB |
| D1 activation energy | denominator, t | new beam: +P^p(p_u)+0.338 W (+0.2 W new satellite); darkening: symmetric | 6.3–8.9 W ≈ 1.6–2.5 κ per step |
| D2 beam power | denominator, t | joining with p_u above the beam max raises P^p concavely; load itself costs nothing | ≤ P^p(p_max) − P^p(p⁰) = 2.45 W |
| T1 segment trajectory | both, t+1… | new segment restarts at p⁰; continuing segment power grows as G^T falls; 3 dB budget vs median 1.19°/step drift; outage when p > p_max | median segment life 5 steps (docstring, `env/step.py`) |
| T2 future activation/others | both, t+1… | state effects: previous radiating set, demand N(t−1), dwell/slot assignment | policy dependent |
| T3 handover | none | φ1/φ2 have no physical cost in this simulator | 0 |

DERIVATION: total system bits per step = B^w Σ_b (mean spectral efficiency of the users on beam b). Total energy ≈ Σ_b e_b. So EE ≈ B^w·⟨mean SE per beam⟩/⟨e per beam⟩ is *first-order invariant to the number of beams* when SE and per-beam power are homogeneous; the EE-relevant spatial levers are therefore (i) dilution/enrichment of a beam's mean SE by who joins it, (ii) interference reduction from fewer lit beams, (iii) abandoning beams whose per-user cost is high relative to their SE. Lever (iii) is inherently joint for beams with ≥2 occupants.

---

## 4. Is Three-Head Positive Marginality Possible?

### 4.1 Conditions under which FULL > DROP_Ck can hold for all k (DERIVATION)

(i) Each head must change the masked argmax on some anchors (its action gaps must be comparable to the other heads' gaps there; shared κ makes this possible). (ii) At those pivotal anchors the true EE effect of the switch must be positive on net, i.e., the head must be accurate where it is pivotal, not on average. (iii) The joint application of the switches must not undo the unilateral gains (non-additivity bounded). (iv) The three heads must not be affine copies of one another as functions of state-action.

### 4.2 Why it is not guaranteed — two counterexamples (DERIVATION)

Collinearity: if the true surplus is a function of a single sufficient statistic (e.g. target-beam load), any three-way split yields heads that re-weight one score; dropping one rescales the ordering rather than changing it → zero marginal effect.

Antagonistic cancellation: joining beam b with k incumbents of mean SE c̄ gives own bits B c_u/(k+1) (in z1) and costs the incumbents B c̄/(k+1) (in z3). For a homogeneous population c_u ≈ c̄ the two nearly cancel; the sum's ranking is then decided by energy and SE differences, so a learned Q3 with estimation error larger than |c_u − c̄|/(k+1) makes the sum noisier than Q1 alone → DROP_C3 > FULL. Positive marginality of a rate-externality head requires estimation error below the dilution asymmetry, which the V0.19 head did not approach (Section 6).

### 4.3 Does the physics supply three degrees of freedom? (INFERENCE from verified facts)

Yes for the *targets*: own-link/energy, temporal segment trajectory, and shared-resource externality are physically distinct. But the third channel's EE-relevant realisation is joint consolidation, which a single-argmax policy can only express as a shared statistical bias ("prefer beams other users also prefer / avoid being one of few on an expensive beam"). Evidence that the physics permits this bias to pay: three independent oracle panels (V0.12, V0.13, V0.18) show the same signature (bits −4.3…−5.7%, energy −5.0…−6.6%, EE +0.63…+1.10%, active-beam steps down). Evidence that it is a *distinct* mechanism rather than λ0-compensation: none yet (Section 2.3). Verdict for this section: **feasible, unproven**.

---

## 5. Audit of Current R3/C3

Files audited: `docs/MULTI-CATFISH-EE-AXIS-REDESIGN-CONTRACT-V0.3-2026-08-31.md`, `docs/MULTI-CATFISH-MCRL-V012-ZERO-ENERGY-C3-ORACLE-PREREG-2026-09-03.md`, `src/mcrl/runtime/ee_axis_zero_marginal_c3.py`, `src/mcrl/runtime/ee_axis_relational_zr_c3.py`, `src/mcrl/algorithms/ee_axis_relational_zr_c3_head_v019.py`, the V0.19 learner and both V0.18/V0.19 contracts, and the raw artifacts named in the task.

### 5.1 What ZR is (VERIFIED FACT)

For focal u, legal a, reference b⁰_u = argmax(Q1+Q2_hat), victims v ≠ u: e[a,v] = Δt(R_v(c^a) − R_v(b⁰)); ZR(a) = Σ_v min(e,0) + g(a)·Σ_v max(e,0), centred at the reference; g(a) is the bit-exact five-component compatibility gate (served vector, active-beam keys, active-satellite keys, per-beam RF vector, P^N). No energy term, no λ. The V0.12 prereg states the gate's purpose explicitly: "the smallest direct repair of the observed V0.11 activation-expansion mechanism" — earlier C3 candidates raised active-beam steps (1195 → 1711/1770) and lost EE.

### 5.2 Verified quantitative profile of the ZR target (V0.19 sources, 12 TRAIN + 9 VALIDATION shards, 1000 rows each)

| Statistic (legal non-reference entries) | TRAIN | VALIDATION |
|---|---|---|
| legal actions per row | 26.54 | 26.56 |
| target > 0 | 3.65% | 3.96% |
| target < 0 | 89.90% | 90.19% |
| target = 0 | 6.45% | 5.85% |
| compatible (g = 1) | 8.98% | 9.02% |
| P(target > 0 | compatible) | 0.406 | 0.438 |
| P(target > 0 | incompatible) | 0 (by construction) | 0 |
| rows with any positive target | 38.7% | 40.4% |
| |target| mean (κ) | 0.303 | 0.309 |
| target quantiles p01/p25/p50/p75/p99 (κ) | −1.76 / −0.47 / −0.018 / −0.001 / +0.48 | −1.73 / −0.50 / −0.017 / −0.001 / +0.49 |
| positive targets median / p95 (κ) | 0.27 / 0.94 | 0.27 / 0.93 |
| pivotal rows (teacher ≠ base) | 15.7% | 15.3% |
| teacher's chosen action compatible & positive | 100% | 100% |
| teacher's target gain median (p10–p90), κ | 0.475 (0.16–0.96) | 0.472 (0.16–0.99) |
| Q1+Q2 gap the teacher overcomes, median (p10–p90), κ | 0.150 (0.025–0.47) | 0.169 (0.032–0.47) |
| Q1+Q2 top-1/top-2 margin quantiles p10/p50/p90 (κ) | 0.021 / 0.141 / 0.450 | 0.022 / 0.147 / 0.469 |
| victims per legal action | 56.7 | 56.9 |
| pivotal rate at step 0 vs steps 1–9 | 5.8% vs 10–22% | 7.8% vs 10–20% |

TRAIN and VALIDATION are statistically indistinguishable on every measure: the V0.19 failure is not a distribution shift.

On pivotal rows the teacher moves the focal user to a beam with **more** non-focal incumbents in 85.2% of cases (reference-beam non-focal load median 1, candidate-beam median 3); among all positive-target entries the candidate beam is more loaded in 64.5%. The ZR teacher is a consolidator.

### 5.3 Verified physical outcome of ZR as a decision surface

| Panel (arm vs its C3-free comparator) | Δ bits | Δ energy | Δ EE | active-beam steps | served |
|---|---|---|---|---|---|
| V0.12 FULL_ZR vs DROP_C3 (2 worlds × 3 lineages) | −4.425% | −5.025% | +0.632% | 2597 → 2468 | unchanged |
| V0.13 FULL_ZR vs DROP_C3 (4 worlds × 3) | −5.698% | −6.575% | +0.938% (4/4 worlds) | 5031 → 4709 | unchanged |
| V0.18 EXACT_ZR vs BASE (4 worlds × 3) | −4.258% | −5.234% | +1.031% (10/12 cells > 0; two cells +0.02%, −0.20%) | per step 44.2 → 42.9 | 11987/12000 both |
| V0.18 NOMINAL_ZR vs BASE | −5.202% | −6.236% | +1.103% | per step 43.7 → 42.4 | unchanged |

V0.18 per-step joint receipts (120 step-cells): 15.3 users changed per step, every change compatible and positive under the unilateral teacher, joint `network_power_nonincrease` and `no_new_active_beam` true by construction, realised joint Δbits = −2.63e10 per step (−2.5%), Δenergy = −255 J per step (−2.9%).

### 5.4 Answers to the eight audit questions

**Q1 — Is "current-slot non-focal spatial externality under zero marginal network energy" a valid and sufficiently distinct EE contribution?** The quantity is well-defined and λ-invariant (VERIFIED). As *realised* it is not distinct: its entire EE effect is a denominator effect (energy down more than bits) produced by joint beam consolidation, i.e. the energy channel that the V0.3 contract assigns to C1, and the C1 that it corrects is priced at λ0 = 0.72·η_M (Section 2.3). INFERENCE: the observed ZR gain is at least partly λ0-compensation. Distinctness is therefore **unproven**, not refuted.

**Q2 — Does the zero-marginal-energy compatibility restriction preserve the right causal quantity, or make the target sparse and remove useful trade-offs?** It is a support filter with an energy-safety role, not a causal quantity (VERIFIED from the V0.12 rationale and the gate's construction). It removes every energy trade-off (a darkening move that saves 6–9 W is never credited; a lighting move that would raise the system's mean SE is only charged), and it makes the *joint* action energy-non-increasing by construction because compatible unilateral moves can only empty beams, never light them. Its price is the profile in 5.2: 90% negative entries, 3.7% positive, all pivotal moves forced into the 9% compatible subset.

**Q3 — Is ZR a true EE contribution, a heuristic support filter, or a mixture?** A mixture: the credited quantity (non-focal rate redistribution, 77% load-sharing / 23% interference) is a true unilateral quantity, but it did not materialise jointly (bits fell); the EE gain is delivered by the gate's side effect. The mechanism story in the contract ("C3 learns the immediate effect of the focal action on other users through eligible beam load, bandwidth sharing, co-channel interference") is not the mechanism that produced +1%.

**Q4 — Does the action reference remain coherent after learned Q1+Q2 changes the background?** VERIFIED: the V0.19 background is `Q1_PLUS_Q2_SUM_WITH_ZERO_RIGHT` (the q1 column holds Q1+Q2, q2 is a zero placeholder by convention — not a defect), and the V0.18 learned-Q2 surfaces vary per anchor (302 distinct digests over 360 step-cells). The reference is coherent *at the anchor*. It is incoherent *jointly*: Q3 changes 15% of actions, so the deployed joint background differs from the source background every step, and Section 2.4 shows the unilateral prediction has the wrong sign for bits. Also VERIFIED: the background's Q1 is the E1 ladder's common rung **10** (ten updates; C1 validation skill 0.14–0.20 at rungs 10–300, C2 skill 0.01–0.02 at rung 10 and negative beyond, flat-state C3 skill ≈ 0 at every rung), and the learned OPS-3 Q2 reproduces its own teacher's action changes only 7.5% of the time (V0.14 rung 3000). The "learned Q1+Q2 background" is weak; under a stronger or correctly priced Q1 the ZR gain may shrink (UNKNOWN until tested).

**Q5 — Is the target stationary and identifiable from deployable predecision state?** Identifiable to nominal precision: the parameter-free nominal decoder built from the same predecision variables reproduces the exact teacher's pivotal choice in 84–92% of pivotal rows (V0.18, all lineages, h = 12/1/2) and matches its EE effect. The irreducible part is the keyed Rician/shadow draw (nominal uses unit fading, zero shadow). Stationary given a fixed background; non-stationary across background versions (every Q1/Q2 refresh changes b⁰ and hence the centred surface). Additionally VERIFIED: action-context feature 7 (`nonfocal_reference_max_power_at_candidate_beam_minus_candidate_power_div_pmax`) has min −2.41e6, |x| > 10 in 2.0% and x < −1 in 6.1% of legal entries — an unbounded input to a tanh MLP.

**Q6 — Could Q1/Q2 already absorb the same information?** Within-row correlation between the ZR surface and Q1+Q2 is 0.007 (no surface-level redundancy). A linear fit of the compatible targets on the seven action-context features explains R² = 0.50 — half the decision-relevant variance is a simple function of loads and headroom that the flat 228-D state also carries. The load-sharing dilution −B c̄/(k+1) is genuinely absent from z1 (new information); the consolidation energy saving is absent from *every* unilateral target (nobody's information); the marginal energy is in z1 but under-priced. Redundancy risk is therefore concentrated in the energy channel, antagonism risk in the rate channel (Section 4.2).

**Q7 — Does literal unweighted Q1+Q2+Q3 remain valid for the current gauges and units?** Dimensionally yes: all three heads are reference-centred bits/κ with the same κ (VERIFIED in the Q1 E1 config, the Q2 rung-3000 config, and the V0.19 contract). Numerically the sum is not the EE criterion because λ0 is stale (Section 2.3), and in practice the sum is Q1 + Q3 because the learned Q2 barely discriminates (Q4).

**Q8 — Why did V0.19 fail?** **E**, with weights: C (primary), A (secondary), B (partial), D (no). Details in Section 6.

---

## 6. Diagnosis of V0.19

Verified from `artifacts/multi-catfish-v019-relational-q3-learner-20260904-r1/server-run/{gate-output/report/result.json, learner-output/*/result.json, learner-output/*/validation-predictions.npz, gate-output/background/*/background.npz, sources/*/source.npz}`; all counts in the report were reproduced exactly (changes 62/15/0, supported 0/6/0, pivotal rows 497/424/454, pivotal agreement 0/6/0).

| Initialisation | 2026120711 | 2026120712 | 2026120713 |
|---|---|---|---|
| validation skill vs strongest null | −0.074 | −0.068 | −0.066 |
| model MAE vs zero-null MAE (κ) | 0.324 vs 0.310 | 0.266 vs 0.321 | 0.268 vs 0.309 |
| TRAIN loss, mean of first 20 → last 20 updates | 1.80 → 0.203 | 1.21 → 0.137 | 3.05 → 0.144 |
| prediction std / target std (VALIDATION) | 0.17–0.21 / 0.43–0.50 | 0.23–0.29 / 0.44–0.51 | 0.16–0.23 / 0.42–0.52 |
| prediction mean (κ) | −0.22…−0.29 | −0.26…−0.32 | −0.23…−0.29 |
| max prediction (κ) | +0.24 | +0.56 | +0.04 |
| corr(prediction, target) | 0.28–0.34 | 0.58–0.63 | 0.52–0.61 |
| AUC ranking target > 0, all entries / compatible only | 0.26–0.47 / 0.50–0.61 | 0.54–0.66 / 0.46–0.52 | 0.25–0.36 / 0.55–0.61 |
| AUC ranking target < 0 | 0.65–0.79 | 0.67–0.78 | 0.49–0.61 |
| pivotal rows: student ranks teacher above base | 0.0–0.6% | 2–8% | 0% |
| pivotal rows: needed gap / student gap / true gap (median, κ) | 0.17 / −0.28 / 0.45 | 0.13–0.20 / −0.15…−0.18 / 0.42–0.50 | 0.13–0.18 / −0.29…−0.31 / 0.43–0.57 |

Reading (INFERENCE grounded in the numbers above):

- **C — loss/imbalance/argmax mismatch (primary).** The surface is 90% negative; uniform pairwise MSE rewards learning the harm regression (negative-tail AUC up to 0.79, negative bias −0.25 κ) and never the 4% positive tail that alone decides the argmax (positive-tail AUC ≈ 0.5 among compatible entries). On pivotal rows the student believes the teacher's action is *worse* than the base by 0.15–0.31 κ while it is better by 0.42–0.57 κ. The TRAIN loss fell by 8–20× within 100 updates, but 100 Adam steps cannot fit the log/exp structure that the nominal decoder computes in closed form from the same six tokens; the preflight's "MSE below zero-null" on TRAIN batches did not transfer to VALIDATION MAE.
- **A — wrong physical target (secondary).** Even a perfectly learned ZR would deliver EE only through the joint consolidation side effect and under a mispriced Q1; the target's own semantics (unilateral positive redistribution) do not materialise jointly (Section 5.3–5.4).
- **B — state (partial).** The predecision relational state suffices for nominal-level decisions (84–92% pivotal agreement of the parameter-free decoder), so information is not the binding constraint; but the unbounded feature 7 is a conditioning defect that any learner would need fixed, and 4,000 TRAIN rows (four worlds) is a small panel for a relational head.
- **D — additive interface (no).** Units and gauges are consistent; the interface defect is λ0 pricing, which is upstream of C3.

Distribution similarity, prediction scale, positive-tail ranking, action-change support, and background interaction are all quantified above; none of the saved arrays contradicts this reading.

---

## 7. Candidate R3/C3 Designs

Common notation: reference joint action b⁰ = argmax(Q1+Q2), focal candidate a, unilateral configuration c^a = b⁰_{−u} ⊕ a; per-beam energy e_b = P^p_b + P_cir; per-satellite baseband P_BB; k_b = eligible occupants of beam b; n_s = served users on satellite s. **Cost share** of a served user (PROPOSAL, new definition): share_u = e_{b(u)}/k_{b(u)} + P_BB/n_{s(u)}; share_u = 0 if unserved. DERIVATION: Σ_u share_u = P^N exactly in every configuration, hence for any joint move Σ_u[ΔR_u Δt − λΔshare_u Δt] = ΔB − λΔE exactly.

### A. Retain ZR, decision-aligned learner (control)
- Target: unchanged ZR. Head: relational scorer with the nominal per-victim rate formula as a differentiable, parameter-free inductive bias plus a learned residual and learned victim weighting; loss weighted toward compatible and pivotal pairs (margin/ranking on B-gap), 1,000–3,000 updates, feature 7 clipped/log-compressed.
- Deployment/training info: as V0.19. Relation to EE: indirect (consolidation side effect). Overlap: energy channel with C1. Learnability: high (the closed form exists). Support density: 3.7% positive. Genuine Catfish: yes (training-time counterfactual). Paper story: preserved only if the mechanism is re-described as gated consolidation.
- Smallest falsifiable TRAIN-only test: source-only gate on the existing 21 V0.19 shards with the V0.19 acceptance rule (positive pivotal skill vs strongest null, supported-change rate > 0.5). Cost: CPU minutes. Falsified if skill ≤ 0 with the closed form available.

### B. Conditional marginal EE relative to the frozen Q1+Q2 background (= V0.3 ζ3 without the gate)
- Target: z3 = Δt Σ_{v≠u}[R_v(c^a) − R_v(b⁰)], symmetric credit. Relation to EE: exact partition of the unilateral opening surplus with z1. Overlap: none by identity. Learnability: the flat-state E1 learner had zero skill on it at every rung; a structured relational head is untested. Support: dense (≈ 94% of entries non-zero). Risk (DERIVATION + V0.11 receipts): symmetric relief credit plus under-priced energy in Q1 pushes toward activation expansion; V0.11's C3 variants raised active-beam steps by 40% and lost 1.2–4.4% EE. Not recommended as a primary; viable only after λ re-pricing.
- Smallest test: oracle arm on the shared fresh panel (Section 8); kill if energy rises.

### C. Spatial externality residual "including every numerator and denominator effect not assigned to C1/C2"
- Under the V0.3 partition the residual is exactly B (C1 already holds all opening energy). Giving C3 the opening energy requires narrowing C1 to own-rate only (z1' = ΔR_u Δt, z3' = Σ_{v≠u}ΔR_v Δt − λΔE Δt). Exact partition, dense, highly learnable (energy is a near-deterministic function of lagged activation state), strongly distinct from C1. Cost: DROP_C3 = Q1'+Q2 becomes energy-blind, so "each DROP arm > MAIN" is at risk for DROP_C3, and C1's existing lineage/evidence is discarded. Classified as an additive-interface redesign, second choice.

### D (recommended, "CSE"). Cost-share externality — Shapley/equal-split attribution of the shared power bill plus the non-focal rate externality
- Exact target (PROPOSAL):
  z3^CSE_u(a) = Δt Σ_{v≠u}[R_v(c^a) − R_v(b⁰)] − λ Δt { [share_u(c^a) − share_u(b⁰)] − [P^N(c^a) − P^N(b⁰)] }.
  z1 (V0.3, unchanged) + z3^CSE = Δt Σ_v ΔR_v − λ Δt Δshare_u: "system bits change minus the change in my fair share of the power bill". z2 unchanged.
- Physical interpretation: C3 = what my association does to the shared system — other users' bits (dilution, relief, interference) and the difference between the marginal energy the system charges me and the share I fairly owe. Leaving a beam of k occupants that stays lit credits λe_A/k (my share is released; jointly the k releases sum to the real saving e_A when all leave); joining a lit beam of k' users charges λe_B/(k'+1) (no longer free-riding); lighting a private beam is charged in full by z1 and refunded only my old share by z3. Consolidation economics are thus unilaterally measurable, and the compatibility gate becomes unnecessary.
- Training-time information: identical to ZR's teacher (one `evaluate_actions` per (u,a); loads, beam powers, P^N all come from the same `ActionEvaluation`). Deployment information: candidate beam's lagged eligible load, lagged beam power, satellite-active flag, own required power — all in the 228-D V0.3 state; share is a simple deterministic function of them.
- Relation to final EE: exact for joint moves via the share identity; unilateral measurement approximates the joint surplus with the shared-cost gap closed (the gap that flipped the sign in Section 2.4). Requires a correctly priced λ (Section 8, Stage 0).
- Overlap/double counting: none in the sum (identity above); z1 and z3 carry the marginal energy with opposite signs by design, which must be stated explicitly. Note the paper's ruling C-7 withdrew per-link *private power shares as an EE display quantity*; CSE uses shares only as a training-target component, and must never be presented as "private EE".
- Learnability risk: low for the energy part (dense, deterministic up to the one-step lag), medium for the rate part (as B). Expected support density: dense (every action that changes beam, load, or activation has a non-zero target). Genuine Q3/Catfish mechanism: yes (multi-user counterfactual, training time only, no coordination at deployment). Three-Q one-argmax story: preserved; C1 = "my surplus", C2 = "my future", C3 = "my externality and my fair share".
- Smallest falsifiable TRAIN-only test: oracle arm EXACT_CSE vs BASE' on the shared fresh panel; kill if pooled ΔEE ≤ 0 or service falls; then a source-only learner gate with the V0.19 metrics where "supported" = exact z3^CSE > 0 at the selected action.

### E. Third head structurally unjustified
- Not supported by the derivation: three physical channels exist and one consolidation signature is reproducible. It becomes the verdict only if Stage 0 shows the ZR gain vanishes under correct pricing **and** the CSE/EC oracles fail to beat BASE' on the shared panel (Section 8 kill rule).

### F (parallel minimal). Energy-share-only head ("EC")
- Target: z3^EC = −λ Δt {Δshare_u − ΔP^N} (the CSE energy correction alone). Deterministic from lagged state; learnable with the existing flat pairwise learner (E1 machinery). It isolates whether the consolidation economics alone is the mechanism; if EC ≈ CSE in the oracle screen, the rate externality adds nothing and the head can stay flat.

---

## 8. Parallel Fast-Falsification Plan

Constraints honoured: at most three learned candidates (A/control, D/CSE, F/EC); existing opened TRAIN evidence used only for development; formulas, λ′, thresholds, and selection rules frozen before any fresh outcome; one shared fresh TRAIN physical panel; no episode training unless a learned C3 passes its gate.

**Stage 0 — λ-confound falsifier and existence screen (heavy → Ubuntu server; est. 1–2 h wall with 18 workers, ~72 world×lineage×arm episodes at ~700–1,750 s each as in V0.18).**
1. Declare λ′ = η of the frozen Q1+Q2 background on the already opened TRAIN worlds (available: 1.184e8 V0.18 BASE; 1.210e8 V0.13 DROP_C3; choose and hex-freeze one before any fresh world is opened). Retrain Q1 on the already opened E1 opening sources at λ′ (E1 ladder, CPU minutes) → BASE′ background.
2. Fresh panel: 4 new TRAIN worlds × 3 lineages; arms BASE, BASE′, EXACT_ZR|BASE, EXACT_ZR|BASE′, EXACT_CSE|BASE′, EXACT_EC|BASE′ (exact teachers only; no learner). Endpoints: pooled ratio-of-sums EE, bits, energy, active-beam steps, served fraction (margin 0.001).
3. Decisions (frozen): the current C3 family is **falsified as a distinct mechanism** if EXACT_ZR|BASE′ − BASE′ ≤ 0 pooled or its bits/energy signature disappears while EXACT_ZR|BASE − BASE stays positive. CSE/EC **exist** if pooled ΔEE > 0 vs BASE′ in ≥ 3/4 worlds and ≥ 2/3 lineages with service non-inferior; otherwise Section 7E becomes the verdict (THREE_HEAD_STRUCTURALLY_INFEASIBLE for a single-argmax interface, pending Q2).

**Stage 1 — source-only learner gates for the survivors (non-heavy; CPU, minutes to ~1 h each).**
- Harvest CSE/EC/ZR labels at the Stage 0 anchors (already computed by the oracle arms) plus the opened V0.19 shards for development. Fix feature 7 (clip or asinh) before any outcome. Learners: A = ZR + nominal-structured head; D = CSE relational head (nominal rate formula + share formula as inductive bias, learned residual); F = EC flat head (E1 pairwise). Updates 1,000–3,000 with a preregistered schedule; complete-world TRAIN/VALIDATION split.
- Metrics (as V0.19): pivotal-row agreement vs strongest state-independent null, stable preservation ≥ 0.95, supported-change rate with support = exact target sign at the selected action. Pass: mean skill > 0 with ≥ 2/3 initialisations, supported rate > 0.5. Kill otherwise; no retry against the same outcomes.

**Stage 2 — one shared fresh physical panel for surviving learned heads (heavy → server; est. 3–5 h wall).**
- 12 fresh TRAIN worlds × 3 lineages; arms FULL, DROP_C3, MAIN for each survivor (DROP_C1/DROP_C2 added only for the single best survivor). Success: pooled ΔEE(FULL − DROP_C3) > 0 in ≥ 9/12 worlds and 3/3 lineages, DROP_C3 > MAIN pooled, service non-inferior. Kill: any survivor failing this is not carried to episode training.

**Evidence required before the 100-episode five-arm evaluation:** (a) Stage 0 passed with the C3 gain surviving correct pricing; (b) one learned C3 passing Stage 1 and Stage 2; (c) λ′ frozen and used consistently by all heads of that stage; (d) service non-inferiority; (e) a runtime benchmark showing checkpointing every 100 episodes fits the budget.

**Evidence required before 500/1500/3000-episode training:** five-arm ordering FULL > DROP_C3 and DROP_C3 > MAIN reproduced on the 100-episode panel with sign-consistent worlds; an explicit decision on Q2, whose learned head currently has ≈ 0.02 validation skill and 7.5% teacher-change agreement — FULL > DROP_C2 is unsupported by any current evidence and is independent of the C3 redesign; user notification before any 9000-episode run as the contract requires.

Estimated total wall time to a go/no-go on the redesigned C3: about three server-days including preregistration, dominated by the two oracle/physical panels.

---

## 9. Claim Ceiling and Remaining Unknowns

Claim ceiling: everything here is TRAIN-development evidence and read-only analysis. No TEST world has been opened by this audit. No statement in this document is an efficacy claim; the EE deltas quoted are analytic-oracle screens under one frozen weak background.

UNKNOWN (require new experiments):
- whether the ZR/consolidation EE gain survives a correctly priced Q1 (Stage 0);
- whether CSE/EC oracles beat BASE′ (Stage 0);
- whether the learned OPS-3 Q2 contributes any positive marginal effect (independent of C3);
- the exact split of the V0.18 energy reduction between same-step joint consolidation (−255 J/step measured) and trajectory divergence (remainder of −55,161 J total);
- whether the nominal-vs-exact gap (keyed fading/shadow) bounds achievable learner skill on the positive tail;
- the sensitivity of all results to λ′ within [η_M, η_C].

Non-obvious verified facts worth carrying forward: the V0.19 background sidecar stores Q1+Q2 in the q1 column with q2 = 0 by declared convention (`Q1_PLUS_Q2_SUM_WITH_ZERO_RIGHT`), so any reader computing "Q2 = 0" from `background.npz` is seeing the representation, not a defect; the V0.18 learned-Q2 surfaces do vary per anchor.

---

## 10. Final Decision Token

Primary: **REDESIGN_R3_TARGET**

Secondary status (not a token): three-head positive marginality is feasible in this physics but unproven, and the existence evidence for the current C3 is confounded with λ0 mispricing. The specific redesign is the cost-share externality target (Section 7D) with the λ-confound falsifier (Section 8, Stage 0) as the mandatory first step.

REDESIGN_R3_TARGET
