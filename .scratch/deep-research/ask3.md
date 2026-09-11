# 總判決

**原先以「多個 demonstrators／multi-catfish／advantage filtering／constrained multi-objective RL」作為新機制的主張，已經站不住。** 這些元件各自都有 published precedent；DR-3 只支持「尚未在 LEO handover 中找到完全相同的整合」，不支持「新的 RL 原理」。此外，“catfish” 並不是穩定的 RL mechanism name，相關 RIS 譜系連 bibliographic identity、replication 與 citation lineage 都未能獨立閉環，不適合再放在論文標題、摘要或 contribution list。 

**目前最強、最誠實、也最有機會發表的核心，是 diagnostic contribution：learner 並非沒有學會，而是成功最佳化了一個與 declared endpoint 排序不同的 training objective。**

---

# 1. 這組數字在領域中位於哪裡？

## 1.1 絕對 EE magnitude：不能排 percentile

你目前的兩個主要值約為：

| Policy             |     Pooled EE |
| ------------------ | ------------: |
| Trained checkpoint |  93.14 Mbit/J |
| MAX_NOMINAL_GAIN   | 111.55 Mbit/J |

不能誠實地說它們位於 LEO literature 的高端、中位數或低端。DR-3 的核心發現正是：

* 很多 handover paper 根本不用 ratio EE，而使用 handover count、blocking、delay、throughput 或 composite utility；
* 標示為 “energy efficiency” 的論文，也混合了 system rate/system power、normalized bits/Hz/J、per-user ratios、power minimization 等不同定義；
* bandwidth、full-buffer assumption、circuit-power boundary、traffic cap 與時間 aggregation 往往不一致或無法核實。

因此，93–112 Mbit/J 在目前只能稱為**這個 simulator 與 accounting boundary 下的絕對量級**，不能變成跨文獻排名。

相同限制也適用於 19.8–22.2%：這是非常大的**內部相對差異**，但 DR-3 沒有形成一個可比較的 published improvement distribution，所以不能寫成「高於領域通常的 X% improvement」。

## 1.2 內部 effect size：強，而且不是 ratio artefact

在目前凍結 panel 上，這個結果有幾個相當強的特徵：

* EE 差異不是只由 denominator 變小造成：rule 同時有約 1.146 倍 bits 與約 0.957 倍 joules。
* service 幾乎相同。
* segment-entry anchor ablation 不但沒有消除結果，反而將 ratio 由約 1.1975 擴大至 1.2222。
* placebo 可 bit-identical reproduction。
* learner 在自己的 scalarized objective 上仍然勝過可表達的 myopic rules。

最後一點特別重要。這不是典型的「DQN 沒有收斂」；目前證據比較支持：

> **The learner is a specification success and an endpoint failure.**

也就是 learner 有效地提高了它被交付的 scalarized target，但該 target 對 policies 的排序與 declared pooled EE 不同。

## 1.3 Baseline practice：高於 learned-only paper，但仍未完整

DR-3 中 baseline identity 可直接編碼的 13 篇工作，有 10 篇包含至少一個 random、single-criterion、greedy、max-link、max-service-time 或 exhaustive-search 類 comparator；沒有正式 mandatory set，但存在非常明顯的 de facto family。

你的 suite 已覆蓋：

| De facto family                  | 目前是否有                |
| -------------------------------- | -------------------- |
| Random                           | 有：`RANDOM_MASKED`    |
| Strongest instantaneous link     | 有：`MAX_NOMINAL_GAIN` |
| Objective-related greedy         | 有：`GREEDY_R1R2`      |
| Longest remaining service / MRST | 尚缺                   |
| Load/capacity-aware single rule  | 尚缺獨立且透明的版本           |
| Exact/optimization reference     | 尚缺；可在縮小實例上提供         |

所以基線標準的判斷是：

* **比只比較 DQN/DDQN/PPO/SAC 的論文嚴格。**
* **與較完整的 LEO handover baseline practice 相符，但還沒有覆蓋整個 recurring family。**
* 真正高於領域慣例的部分，不只是加入 max-gain，而是你接受它在 primary endpoint 上勝出，並繼續查原因；核心 LEO literature 幾乎都把 proposed learner 寫成最終正面結果。

## 1.4 Statistical treatment：audit 很強，algorithm-level inference 還不夠

DR-3 沒有系統性編碼每篇論文的 training seeds、confidence intervals 與 statistical unit，因此不能誠實地說「本專案統計標準高於領域的某個百分比」。

可以作出的 qualitative judgment 是：

| 層次                                  | 判斷                                                                               |
| ----------------------------------- | -------------------------------------------------------------------------------- |
| Frozen-checkpoint internal validity | 高：byte-identical weights、matched RNG、placebo、positive control、mechanism ablation |
| Evaluation uncertainty              | 尚可，但應以 episode/scenario 為 cluster                                                |
| Training-procedure uncertainty      | 不足：目前是單一 authenticated checkpoint                                                |
| Scenario/generalization uncertainty | 不足：主要結論仍來自一個有限 panel 與一套 engine                                                  |
| Good-venue standard                 | 尚未達到                                                                             |

`24 episodes × 10 steps × 100 users` 並不等於 24,000 個獨立 replication。最多只有 24 個 episode-level clusters，而且同一 checkpoint 下的 evaluation episodes不能代表重新訓練後的 policy distribution。

因此整體結論是：

> **你的 internal forensic standard 高於本 survey 中大多數可見的 reporting practice；但 training-seed replication 與 external validity 仍低於好 venue 對 algorithm-level claim 應要求的標準。**

---

# 2. 已有多種 demonstration 方法後，還剩什麼 contribution？

## 2.1 可辯護的一句話

> **我們將 heterogeneous heuristic/solver behavior data 視為可選擇重用的 partial expertise，結合 ratio-consistent EE learning 與顯式 handover/QoS constraints，並以完整基線與因子消融量測各元件對 constrained EE frontier 的實際貢獻。**

這句話的 contribution 是：

* integration；
* domain-specific design；
* measurement；
* partial-expertise characterization；
* constrained EE frontier evaluation。

**不是**「我們發明了 heterogeneous demonstrations」、「我們發明了 advantage filtering」或「我們發明了 constrained multi-objective RL」。

DR-3 已找到 wireless offline RL 使用 random、greedy、TDM、ITLinQ 與不同品質 RL behavior policies 的 heterogeneous mixtures，也找到一般 LfD 對 imperfect demonstrations 與 safe demonstrations 的處理；在 LEO handover 中未找到同樣 deployment，只形成 application/integration gap。

## 2.2 唯一可能保留的狹義 algorithmic novelty

DR-1 留下了一個比「多個 demonstrators」更具體的缺口：

$$
A_{\mathrm{ratio}}
=
A_B-\eta A_E,
$$

或相應的

$$
Q_B-\eta Q_E
$$

learner-relative demonstration acceptance gate，配合 changing Dinkelbach parameter、raw \(B,E\) replay 與 masked discrete actions。

DR-1 找到 \(B-\eta E\) 的 fractional-RL citation trail，也找到 tabular 與有限的 deep precedents；但沒有找到完整的 deep two-head replay architecture，也沒有找到 ratio-aware imitation/margin gate 的 published instance。

這可以形成一個**窄而明確的候選方法貢獻**，但需滿足三個條件：

1. gate 必須真的是 ratio-consistent learner-relative acceptance，而不是把普通 AWR/AWAC/SIL 改名；
2. 必須處理 changing-\(\eta\) 與 replay staleness，而不是忽略；
3. 必須對 scalar-advantage gate、unfiltered demonstrations、DQfD-style margin、BC/AWR/AWAC/IQL 類方法做直接消融。

目前它是 prospective contribution，還不是已完成的 contribution。

## 2.3 一篇 integration/measurement paper 必須攜帶什麼

### Baselines

至少需要以下三層：

| 層次                     | 必要 comparator                                                                                                                                                                   |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Physical rules         | Random、MAX_NOMINAL_GAIN/max-SINR、MRST/longest-service、load/free-channel rule、endpoint-aware greedy                                                                              |
| Optimization reference | 小規模實例的 exhaustive/MILP/solver oracle；大規模可用 bounded rolling-horizon 或 local-search reference                                                                                     |
| Learning               | 原始 MODQN、相同 backbone 的 corrected-reward learner、no-demonstration learner、unfiltered behavior-data learner、標準 advantage-filtered learner、constrained RL、ratio/Dinkelbach learner |

每個 demonstrator 本身也必須被當成 standalone arm，報告它在：

* pooled EE；
* bits；
* joules；
* service；
* handover；
* constraint violations；

上的完整表現。不能只稱其為 expert，而不揭露它在哪些 objective 上其實很差。

### Ablations

至少需要：

* 每個 demonstrator individually；
* 所有 demonstrators pooled；
* demonstrator number/source sweep；
* mixture proportion sweep；
* no filter；
* static quality threshold；
* learner-relative scalar advantage filter；
* ratio-aware advantage filter；
* constraint-feasibility gate；
* with/without pretraining；
* with/without supervised margin；
* ordinary versus prioritized replay；
* scalarization versus explicit CMDP constraints；
* original \(r_2\)、original \(r_3\)、outage correction 各自與聯合 knockout；
* equal environment interactions、equal wall-clock 與 equal tuning budget。

只做 `FULL` 對 `NO_DEMO` 不足以支持「heterogeneous demonstrations」的機制主張。

### Statistical treatment

最終 confirmatory experiment 應至少包含：

* 獨立 training seeds，而非只重跑 evaluation；
* 以 fresh、未參與 baseline 發現的 scenario panel 作 final test；
* common random numbers 僅用於 paired variance reduction；
* 每個 seed 內維持 ratio of sums：

  $$
  \hat\eta=\frac{\sum B}{\sum E};
  $$
* 對 episode/scenario blocks 做 paired cluster bootstrap，每次重新計算 numerator 與 denominator；
* 不能將 per-user、per-step observation 當成獨立樣本；
* service 與 handover constraint 報 simultaneous confidence intervals；
* 報 effect size、95% interval、failure seed、median/worst case，不只 mean ± SEM。

以目前約 1.32 小時／3000 episodes 的成本，final arms 採 10 個 training seeds 只是下限；約 20 個獨立 seeds 會更有說服力。這是本專案的實務建議，不是全領域的硬性規範。

### Venue

正向 integration/measurement paper 的 venue fit：

1. **IEEE Transactions on Machine Learning in Communications and Networking**：最合適。其 scope 明確包含 autonomous resource management、ML performance evaluation，並鼓勵公開 code、dataset 與 artifacts。([IEEE 通信學會][1])
2. **IEEE Transactions on Green Communications and Networking**：若 paper 的中心是 EE definition、power accounting、green ML 與 constrained ratio optimization。([IEEE 通信學會][2])
3. **IEEE Transactions on Aerospace and Electronic Systems**：若重點是 satellite-system integration、payload/power model 與多 constellation 驗證。([IEEE AESS][3])
4. **IEEE Transactions on Wireless Communications**：只有在方法已超出單一 simulator，包括一般化分析、完整 ratio/CMDP repair 與多模型驗證時才合理；TWC 要求的是對 wireless theory/application 的高品質原創推進。([IEEE 通信學會][4])

只有「把四個已知元件接在一起，在一個 simulator 報正 improvement」的版本，比較接近 ICC/GLOBECOM 類 conference paper，而不是一篇強 transaction paper。

---

# 3. 19.8–22.2% 的 negative result 是否可發表？

## 3.1 可以，而且目前比 intended positive mechanism 更有辨識度

DR-3 找到的鄰近 precedents 大多只是：

* scalarization coefficient 改變 component trade-off；
* training 不足時 RL 落後 rule；
* poor behavior dataset 限制 offline RL；
* constrained RL 優於 penalty-based reward shaping；
* training reward 與 episodic endpoint 不完全相同。

沒有找到核心 LEO paper 將「訓練完成的 checkpoint，在自己宣稱的 primary endpoint 上被一行 physical rule 顯著擊敗，並進一步定位 reward–physics mismatch」作為主要 contribution。

因此，這種結果不是因為是 negative 就不可發表。問題在於必須把它提升成**一般化的方法學診斷**，而不是「我們在 code 裡找到 bug」。

## 3.2 正確的 claim 句子

目前可支持的版本是：

> **在一個凍結且可重現的 LEO handover 實作中，MODQN 成功提高其 scalarized training objective，卻在 declared pooled EE 上被一行 max-gain 規則領先 19.8–22.2%；code-level audit 顯示該 scalarization 含有與 simulator EE accounting 不一致的 handover 與 occupancy incentives。**

目前**不應**寫成：

> “The 19.8% loss was caused by the handover reward \(r_2\).”

原因是目前同時存在：

* \(r_2\) 對 handover 的 shadow price；
* \(r_3\) 在該 beam-power/interference model 下方向相反；
* outage reward free ride；
* scalar reward logging defect；
* per-user independent policy class；
* 非標準或至少需進一步審核的 multi-head optimizer loop。

現有證據證明了：

1. performance ordering reversal；
2. reward–endpoint inconsistency；
3. reward–physics inconsistency。

但尚未以 controlled intervention 證明 \(r_2\) 是 19.8% gap 的唯一或主要 causal mediator。

## 3.3 另一個必須修正的敘述：rule 並未在完整多目標向量上支配 learner

`MAX_NOMINAL_GAIN`：

* pooled EE 較高；
* bits 較高；
* joules 較低；
* service 相近；
* 但 handover rate 為 0.7117，而 learner 為 0.2796。

所以在完整的 \((EE,-HO,\text{service})\) vector 中，max-gain 並沒有 Pareto-dominate learner。

這不削弱 declared-primary-endpoint finding，但它限制了論文語言：

* 可以說：「rule wins decisively on declared pooled EE。」
* 不可以說：「rule is unconditionally the better handover policy。」
* 可以說：「fixed scalarization trades away 19.8% EE for lower handover rate without making that exchange rate explicit in the endpoint。」
* 不可以說：「handover penalty is inherently illegitimate。」

即使 handover 在 simulator 中沒有 energy term，它仍可代表 stability、signaling、interruption 或 operational preference。問題不是「不能 penalize handover」，而是：

> **它應被報成明確 secondary objective 或 constraint，而不應被當成 pooled EE 的 surrogate，卻又用 EE 作主要成功敘事。**

## 3.4 最強的 paper 形狀

單純 negative paper 可以發表；但更強的版本是：

> **Reward–Endpoint Misalignment in LEO Handover RL: Diagnosis, Constrained Ratio Repair, and Demonstration-Guided Acceleration**

論文順序應是：

1. **Endpoint audit**：重現 19.8–22.2% reversal。
2. **Causal isolation**：分別 retrain `DROP_R2`、`DROP_R3`、fixed-outage、corrected-scalar、all-fixed。
3. **Generalization**：多 user loads、constellations、traffic caps、ACM、power accounting variants、handover interruption。
4. **Repair**：ratio/Dinkelbach objective，加顯式 service/handover constraints。
5. **Demonstration study**：最後才問 heterogeneous behavior data 是否加快或改善 repaired learner。

這會把 demonstrations 從一個薄弱的 novelty claim，變成一個有合理科學問題的 secondary contribution。

## 3.5 Venue 判斷

| 完成程度                                                        | 合理定位                                                     |
| ----------------------------------------------------------- | -------------------------------------------------------- |
| 單 checkpoint、單 engine、只有 code diagnosis                     | 還不足以投好 journal                                           |
| 多 training seeds、fresh panel、reward-component retraining    | ICC/GLOBECOM 類完整 conference paper；或較窄 journal submission |
| 再加多模型 sensitivity、正式 endpoint audit framework、open artifact | TMLCN、TGCN、TAES                                          |
| 再加一般化條件／ratio-consistent repair／跨任務驗證                       | 可嘗試 TWC                                                  |

TMLCN 對 ML performance evaluation 與 reproducibility 的明確 scope，使它成為目前最自然的第一 journal target；TGCN 適合以 EE 與 power accounting 為中心；TAES 適合把 simulator physics 與 satellite-system implications 做深。([IEEE 通信學會][1])

一個有用的 litmus test 是 ACM SIGCOMM 2026 的 NetNeg workshop：它明確歡迎 negative results、failed generalization 與 methodological lessons，但也明確排除只屬於 implementation bug 或 misconfiguration 的工作。你的結果要進好 venue，就必須跨過同一條線：從「這份 code 寫錯」提升成「這類 reward construction 在什麼條件下會 misorder the declared endpoint，以及如何檢測與修復」。([SIGCOMM 會議][5])

---

# 4. 好 venue 的 referee objections，按拒稿風險排序

下表的「致命」是指對**目前相應的 claim** 致命，不代表整個專案無法修復。

| Rank | Referee objection                                                                                                                                          | 判定                                                                | 必要回答                                                                                                                                                                              |
| ---: | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
|    1 | **This is one simulator bug, not a scientific result.**                                                                                                    | 對 field-wide claim 致命；可修復                                         | 推導一般條件：surrogate reward 與 declared ratio endpoint 何時可能反向排序；在第二 engine、替代 power/interference model 或多個 published-style formulations 上驗證。                                           |
|    2 | **You are calling a multi-objective trade-off a failure.** Max-gain 有較高 handover rate，並未 Pareto-dominate learner。                                          | 對 “better policy overall” 致命；對 primary-EE claim 可回答               | 明確限定 claim 為 declared pooled EE；畫完整 EE–handover–service frontier；改用 maximize EE subject to externally justified HO/service bounds。                                                |
|    3 | **The causal statement is not identified.** \(r_2\)、\(r_3\)、outage defect、policy class 與 trainer 都可能造成差異。                                                  | 對 “because \(r_2\)” 致命；可修復                                        | 以獨立 training seeds 做 factorial reward knockouts；固定 architecture、data budget 與 evaluation panel；觀察 gap 是否隨單一 intervention 關閉。                                                      |
|    4 | **One frozen checkpoint is not an algorithm comparison.**                                                                                                  | 對 “MODQN generally loses” 致命；可修復                                  | 多個 independent training seeds；每 seed 使用相同 paired evaluation scenarios；報 seed-level distribution，而非只報一個 checkpoint 的 episode SEM。                                                  |
|    5 | **The result may be post-hoc.** Endpoint、baseline 或 panel 可能是在看到失敗後選出的。                                                                                    | 可修復                                                               | 公開原始 declaration、timestamp 與 frozen artifacts；預先固定 final contrasts；在 untouched confirmatory panel 上完整重跑。                                                                          |
|    6 | **MAX_NOMINAL_GAIN may have privileged information or a different decision protocol.**                                                                     | 若成立則致命；若不成立可在 text/code 回答                                        | 證明兩者使用完全相同 observation availability、legal mask、action timing、tie-breaking、simultaneous/sequential semantics，而且 rule 不讀 future state 或 hidden nominal variables。                   |
|    7 | **The learner/training loop is too weak or nonstandard.** No Double DQN、n-step、PER；三 optimizer sequential update；per-user argmax 無 coordinator。            | 對 “RL cannot solve it” 致命；對 frozen implementation finding 不致命；可修復 | 加入 standard single-loss DQN/Double DQN、corrected multi-head update、endpoint-aligned learner；檢查 shared-trunk gradients；加入至少一個可處理 joint coupling 的 coordinator/sequential baseline。 |
|    8 | **The conclusion depends on unrealistic physics.** Full-buffer Shannon、no demand cap、max-per-beam power、load-unweighted interference、zero handover energy。 | 對外部泛化可修復                                                          | 做 demand-capped traffic、ACM、time-weighted beam power、load-weighted interference、nonzero HO downtime/signaling cost、不同 load/constellation 的 sensitivity matrix。                    |
|    9 | **The demonstration mechanism is not novel.**                                                                                                              | 對原 intended novelty claim 致命；文字可回答                                | 不再宣稱新 demonstration paradigm；定位成 integration/measurement。只有精確的 ratio-aware learner-relative gate 可作狹義候選 novelty，且須單獨比較與消融。                                                        |
|   10 | **The logged scalar curve is invalid, so how do we know training converged?**                                                                              | 可修復                                                               | 不再使用錯誤 headline curve；從 stored calibrated reward vector 重建；以 policy evaluation、TD diagnostics、multiple seeds 與 trained-objective holdout 佐證。                                      |

對正向 integration paper 而言，第 9 項會升到前三名；對 negative diagnostic paper 而言，第 1–4 項才是主要 rejection risks。

---

# 5. 最直接的結論

**是的：原本想作為主貢獻的 demonstration／multi-catfish 設計，在構成元件層面已經被發表。** 多個 heterogeneous behavior policies、advantage-based selective imitation、imperfect-demonstration handling 與 constrained RL 都不是新的概念。把它們放進 LEO handover 可以是有價值的 integration，但不能再當成新 mechanism。

**目前已經由實驗支持的剩餘主貢獻，確實是 diagnostic：**

* 一行 rule 在 declared pooled EE 上領先 19.8–22.2%；
* learner 卻在 training objective 上勝出；
* gap 同時反映 numerator 與 denominator；
* 主要 artefact attack 失敗且差距擴大；
* code audit 找到 training incentives 與 simulator EE physics 不一致。

最合適的定位不是：

> “A new multi-catfish MODQN for improving EE.”

而是：

> **“An endpoint audit showing that a multi-objective LEO handover learner can successfully optimize the wrong policy ordering, followed by a constrained ratio-consistent repair.”**

Demonstration guidance應降為 repaired learner 的 sample-efficiency／partial-expertise study，而不是 paper 的 novelty anchor。

唯一可能重新形成 algorithmic novelty 的方向，是精確定義並驗證 ratio-aware learner-relative demonstration gate，以及 changing-\(\eta\) replay protocol；在它完成前，不能把它列為現有 contribution。其餘部分，應直接承認是 integration and measurement。

[1]: https://www.comsoc.org/publications/journals/ieee-tmlcn?utm_source=chatgpt.com "IEEE Transactions on Machine Learning in Communications and Networking | IEEE Communications Society"
[2]: https://www.comsoc.org/publications/journals/ieee-transactions-green-communications-and-networking?utm_source=chatgpt.com "IEEE Transactions on Green Communications and Networking | IEEE Communications Society"
[3]: https://ieee-aess.org/publications/taes?utm_source=chatgpt.com "IEEE Transactions on Aerospace and Electronic Systems | IEEE AESS"
[4]: https://www.comsoc.org/publications/journals/ieee-twc?utm_source=chatgpt.com "IEEE Transactions on Wireless Communications | IEEE Communications Society"
[5]: https://conferences.sigcomm.org/sigcomm/2026/netneg/?utm_source=chatgpt.com "ACM Workshop on Negative Results in Network Measurements (NetNeg) | ACM SIGCOMM 2026"
