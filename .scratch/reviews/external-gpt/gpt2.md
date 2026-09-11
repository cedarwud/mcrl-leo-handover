## 整體判斷

我的建議很明確：

1. **停止把原本的 C1／C2／C3 當作主方法繼續修。**
2. **不要直接把「三個 Catfish」當成先驗要求。**
3. 新方法應改成：

> **修正 EE 目標 → 建立真正能提高 pooled EE 的 specialist → 用 DQfD／Catfish 類機制把 specialist 經驗注入 MODQN。**

目前最合理的目標是先完成 **一個確定有效的 EE Catfish，再尋找一個具有互補性的 Guarded Catfish**。第三個 Catfish 只能當後備方向，不能先把名字和數量固定，再去找機制填進去。

換句話說，建議的起點是：

```text
1 個主 agent
+ 1 個 shared demonstration pool
+ 1～2 個具有明確 specialist 定義的 Catfish sources
```

而不是：

```text
3 個 reward heads
或
3 個 Catfish agents
或
3 個 replay buffers
```

---

# 一、目前數據實際支持什麼

我剛才另外對現有輸出做了兩項唯讀合併，沒有重跑物理模擬或訓練。

## 1. 原本 C1／C2／C3 路線確實不值得繼續投入訓練

我合併了：

```text
/home/sat/mcrl-v025-c1vsgain-ws/.scratch/c1vsgain/
c1vsgain-93-w0.json
c1vsgain-93-w1.json
c1vsgain-93-w2.json
```

93 個 development anchors 的 pooled 結果是：

| 方法                          |          pooled EE | served | attainment |
| --------------------------- | -----------------: | -----: | ---------: |
| `GAIN_IN_SET_LADDER`        | **62.5081 Mbit/J** | 1.0000 |     0.3271 |
| `GAIN_IN_SET` declared rule | **50.3435 Mbit/J** | 1.0000 |     0.3113 |
| `CATALOGUE_ORACLE`          |     39.2898 Mbit/J | 0.9983 |     0.2794 |
| `RSS_MAX`                   |     37.6639 Mbit/J | 0.9984 |     0.2761 |
| `S0_TOP1`                   |     37.5256 Mbit/J | 0.9981 |     0.2766 |
| `C1_ONLY`                   | **35.2347 Mbit/J** | 0.9858 |     0.2678 |
| `C1_PSI`                    | **34.6094 Mbit/J** | 0.9966 |     0.2526 |
| `BASE`                      |     10.1469 Mbit/J | 0.7992 |     0.1201 |

目前尚未做正式 cluster bootstrap，因此這不是最終統計裁決；但方向已經很清楚：

* exact C1 低於簡單 `RSS_MAX`
* 加入 exact interaction residual 後反而更低
* 一個直接的 assignment specialist 明顯高於 C1／C3 路線
* 現在再花成本訓練 C1／C2／C3 learner，沒有合理的上限依據

所以原本被 SIGSTOP 的 current-design trainings **不應恢復**。應先完成 C1VSGAIN 正式 merge、bootstrap 和事前宣告的 kill rule。

---

## 2. 同一 MODQN action space 上，已存在一個真正的 EE specialist

在原生 MODQN 28-action/user harness 上，尚未正式 canonicalize 的 pooled-EE 結果是：

| arm                  |          pooled EE | handover rate |
| -------------------- | -----------------: | ------------: |
| `MAX_NOMINAL_GAIN`   | **111.553 Mbit/J** |        0.7117 |
| frozen trained MODQN |  **93.138 Mbit/J** |        0.2796 |
| `GREEDY_R1R2`        |      75.817 Mbit/J |        0.1413 |
| `GREEDY_SCALARIZED`  |      75.272 Mbit/J |        0.1502 |
| random               |      53.060 Mbit/J |        0.8680 |

也就是：

```text
MAX_NOMINAL_GAIN / trained MODQN = 1.1977
```

約 **+19.77% pooled EE**。

這個數字目前只有：

* 一個固定 seed triplet
* 24 episodes
* V0.23 MODQN physics
* 沒有 rate-target attainment
* 沒有正式 receipt／paired bootstrap

所以不能當論文結果，但已足以作為方法設計訊號：

> **Catfish #1 的 specialist 是存在的。問題不是找不到高 EE action，而是它造成太多 handover，而且目前 learner 訓練的 scalar objective 反而懲罰它。**

---

## 3. 第二個 Catfish 最可能存在的地方已經很清楚

從 V0.25 `SPECPROFILE` 的既有配置來看：

| specialist/configuration |  pooled EE | handover rate |   attainment |
| ------------------------ | ---------: | ------------: | -----------: |
| high-EE search winner    | **62.503** |     **0.975** |     354/1200 |
| free-polish variant      |     59.516 |         0.970 | **432/1200** |
| satellite-lock variant   |     43.819 |         0.924 |     357/1200 |
| low-HO guarded variant   |     17.258 |     **0.322** |     192/1200 |
| zero-handover incumbent  |     10.326 |             0 |     115/1200 |

目前的 Pareto 面有一個很明顯的空洞：

```text
高 EE、極高 handover
         ↕
目前沒有好的中間區域
         ↕
低 handover、EE 大幅下降
```

所以第二個 Catfish 不應再從舊 C2／C3 機制中找，而應專門解這個問題：

> **保留大部分 EE specialist 的增益，同時大幅降低不必要的 handover，並滿足 service／QoS guard。**

這是目前最有物理意義、也最有實驗空間的方向。

---

# 二、建議的新 Multi-Catfish 定義

建議不要把 Catfish 定義為一個 reward term 或一個 head，而是正式定義成：

$$
\mathrm{CF}_k =
(\pi_k^{\mathrm{specialist}},
G_k^{\mathrm{admission}},
I_k^{\mathrm{information}},
\rho_k^{\mathrm{sampling}})
$$

其中：

* \(\pi_k^{\mathrm{specialist}}\)：外部 specialist policy／solver
* \(G_k^{\mathrm{admission}}\)：哪些 transition 可以進入 demo pool
* \(I_k^{\mathrm{information}}\)：specialist 使用什麼資訊
* \(\rho_k^{\mathrm{sampling}}\)：訓練時如何取樣這個來源

因此：

> **Multi-Catfish = 多個具有不同有效區域、彼此提供互補經驗的 specialist sources。**

不是多個名字、reward heads 或 arbitrary buffers。

第二個 Catfish 必須同時證明：

1. 有不同於第一個 Catfish 的最佳化問題。
2. 產生一批第一個 Catfish 沒有提供的 positive-advantage transitions。
3. 在預先宣告的 operating region 中不被第一個 Catfish 支配。
4. 加入後對 no-demo／one-Catfish learner 有正 marginal。
5. 不是只改一個 threshold 後得到相同 action distribution。

---

# 三、最值得嘗試的兩個 Catfish

## Catfish 1：`CF-EE` — Ratio-consistent EE specialist

### 目標

直接最大化完整承諾區間的：

$$
\mathrm{EE}_H =
\frac{B_H}{E_H}
$$

而不是：

* instantaneous mean EE
* mean of ratios
* 固定的 \(B-\eta E\)
* 舊 r1+r2+r3 scalar sum

### 建議的 specialist 形狀

第一層可以保留目前已證明有 headroom 的：

```text
MAX_NOMINAL_GAIN
```

作為便宜、可表達的最低門檻 specialist。

正式版本則應使用：

```text
nominal full-horizon Dinkelbach local search
```

對目前 assignment \(a^0\)，先計算：

$$
\eta_0 = \frac{B_H(a^0)}{E_H(a^0)}
$$

再搜尋：

$$
a^* =
\arg\max_a
\left[
B_H(a)-\eta_0E_H(a)
\right]
$$

並更新 \(\eta\)，直到停止或 deadline。

這裡的重點不是固定一個全域 `eta_ref`，而是使用**與目前 policy／anchor 對應的 adaptive ratio price**。目前 ETAFIX 已證明一個固定 \(\eta\) 無法保持 EE ordering。

### 使用方式

`CF-EE` 產生的 demo 只有在：

$$
\Delta_{\eta}(s,a_\text{CF})
>
\Delta_{\eta}(s,a_\text{main})
$$

且 legality／service guard 通過時，才進入 demo pool。

---

## Catfish 2：`CF-GUARD` — Hysteretic／predictive guarded-EE specialist

### 目標

仍然最大化 pooled EE，但把 handover 的實體影響放進 numerator，而不是另外加一個任意 r2：

$$
B_H^\text{effective}
=
B_H -
B_H^\text{lost-by-interruption}
$$

例如：

* same-satellite handover：失去 0.062 秒有效傳輸
* satellite change：失去 0.142 秒有效傳輸

但這兩個常數目前仍有 `VERIFY_SOURCE`，在成為論文參數前必須有來源或 sensitivity range。

### 操作規則

最基本的版本是：

```text
hold incumbent if legal
unless the predicted full-horizon EE gain
after interruption loss exceeds a declared margin
```

也就是 hysteresis：

$$
\text{switch only if }
\Delta B_H
-\eta_0\Delta E_H
-L_{\mathrm{HO}}
>m
$$

其中 \(m\) 不是事後調到最好，而應：

* 使用固定預宣告 grid
* 或根據 prediction uncertainty 設定
* 在 development panel 選 operating point
* 在獨立 OOS panel 鎖定驗證

### 為什麼它可能成為真正的第二 Catfish

`CF-EE` 會提供「現在換到高增益 beam」的經驗。

`CF-GUARD` 會提供：

* incumbent 雖非最高 gain，但換手淨收益為負的經驗
* 同星換手與跨星換手不同的經驗
* 即將失去合法性時提前切換的經驗
* QoS guard 即將觸發時的經驗

這些 transition 的 action label 和狀態區域應該與 `CF-EE` 不同，具有真正的 source complementarity。

---

# 四、第三個 Catfish 的候選，但目前不建議直接實作

## `CF-PAYLOAD` — Payload-consolidation specialist

它不使用 `−U_b` occupancy reward，而是直接根據真正會改變 payload power 的量：

* active beam 數量
* active satellite 數量
* 每 beam 的最大 required RF power
* 新開 beam 的 fixed + PA supply cost
* co-channel interference
* beam 上使用者的平均 spectral efficiency

其 incremental cost 可以寫成類似：

$$
\Delta P_N =
\Delta P_\mathrm{fixed-beam}
+
\Delta P_\mathrm{baseband-sat}
+
\Delta P_\mathrm{PA,max}
$$

然後用：

$$
\frac{\Delta B}{\Delta E}
$$

或 Dinkelbach gain 進行 sequential assignment／local search。

這是比舊 r3 更合理的 interaction mechanism。

但它目前有一個硬風險：

> active-beam set 和其他 user 的 current choices 不在原生 MODQN 的 per-user observation 中。

因此，若 specialist 做的是 set-level coordinated assignment，而 deployed policy 仍要求純 per-user argmax，可能無法模仿。

`CF-PAYLOAD` 只能在下列其中一項通過後進入：

* observation 加入足夠的 active-beam／incremental-power context
* centralized-training/decentralized-execution 能表示它
* 簡單 supervised ranker 在 OOS 上可以模仿
* 或只把它作為 reward-labelled replay，不施加 action imitation loss

所以它是第三順位，不是現在的 Catfish #3。

---

# 五、應以 DQfD 為骨架，RIS Catfish 作比較臂

## 為什麼不建議以 RIS Catfish 作主要實作基礎

原始 RIS Catfish 的可辨識機制包括：

* solver-seeded replay
* EE threshold two-buffer split
* asymmetric discounts
* 70/30 intervention
* ACRM

但現有 audit 已指出：

* 多數參數沒有論文明確數字
* 多項機制缺少成熟的 published counterpart
* ACRM 會改變 reward fixed point
* absolute EE threshold 不具 state-relative 意義
* 30% demo mix 很可能過高
* asymmetric gamma 不一定在目前 horizon 有作用

所以比較合理的角色是：

```text
RIS-Catfish = faithful comparator / ablation arm
```

而不是新方法的核心。

## 為什麼 DQfD 較適合當骨架

DQfD 有清楚的 prioritized demo replay 與 supervised action loss，也有正式 ablation；但它的 unconditional large-margin loss可能將 learner 綁在不完美 demonstrator 上。([arXiv][1])

Nair 等人的 Q-filter 做法更符合目前需求：只有在 critic 判定 demonstrator action 優於 learner action時，才啟用 imitation loss。([arXiv][2])

R2D3 進一步顯示 demo ratio 是高敏感度參數；較低比例整體上優於較高比例，而且多個任務的最佳比例是 `1/256`，因此不應把 RIS 的 30% 當預設。([arXiv][3])

### 建議的 proposed mechanism

建議主方法是：

```text
Source-aware, advantage-filtered DQfD
```

而不是完整原封不動的 DQfD。

核心包括：

1. 一個 shared demo pool。
2. 每筆 demo 保留：

   * `source_id`
   * bits
   * joules
   * pooled-EE／Dinkelbach advantage
   * guard status
   * specialist confidence
3. TD／n-step loss作用在所有合格 demonstrations。
4. supervised margin 只在 Q-filter／positive-advantage gate 通過時作用。
5. demo ratio 低比例起始，並做預宣告 sweep。
6. source-specific quota 防止單一 specialist 壟斷 replay。
7. deployed 時仍只使用 main agent。

---

# 六、不要一開始就做「多 buffer、多 agent」

多 demonstrator 文獻已指出，多來源可能有互相衝突的目標，不能假設最高 reward 的 demonstrator 一定是最適合的 teacher；ZPD 的結果就是最佳 demonstrator 不一定帶來最佳 learner。([arXiv][4])

BERS 也直接處理多個目標衝突 demonstrators，做法是估計來源可信度，再決定取樣機率，而不是無條件把每個來源各設一個 agent。([arXiv][5])

因此建議：

```text
一個 physical replay store
+ source_id logical partitions
+ source-aware sampling
```

而不是：

```text
CF1 buffer
CF2 buffer
CF3 buffer
main buffer
四套固定 sampling ratio
```

這會讓：

* attribution 比較乾淨
* demo 數量容易匹配
* one-vs-two source ablation 容易做
* 不會把 buffer count 誤當貢獻

---

# 七、在恢復 Claude session 前，應先做哪些測試

## A. 先正式化 pooled-EE 結果

目前的：

```text
pooled_ee.py
pooled_ee.txt
```

還在 Claude session 的 `/tmp/.../scratchpad`。

應先建立正式 package，至少包含：

* source hash
* checkpoint hash
* environment hash
* seed list
* 每 episode bits/joules
* paired differences
* bootstrap interval
* mean-of-ratios 與 ratio-of-sums 並列
* handover rate
* service availability
* active beams
* information class
* numerator convention

並將 V0.23 結果明確標為：

```text
design evidence, not final claim
```

這能先確認 `MAX_NOMINAL_GAIN +19.77%` 是否跨 seed／date 穩定。

---

## B. 執行 hysteresis Pareto sweep

在同一 action space、同一 physics 上測：

```text
switch margin m ∈ fixed grid
```

候選規則至少包括：

* hold-while-legal
* max nominal gain
* max nominal gain with same-satellite preference
* physical interruption-aware gain
* full-horizon Dinkelbach gain
* Dinkelbach gain + QoS guard

每個點報：

* pooled EE
* bits
* joules
* handover rate
* same-sat/inter-sat split
* service
* attainment
* active beams
* latency

真正的問題是：

> 是否存在一個點，在保留大部分 `CF-EE` 增益的同時，把 handover 從約 0.7–0.98 顯著壓低？

如果沒有，第二 Catfish 不成立；如果有，這就是 `CF-GUARD`。

---

## C. 測 specialist complementarity

對 `CF-EE` 和 `CF-GUARD` 計算：

* action agreement
* accepted-transition Jaccard overlap
* 只有 CF-EE 正 advantage 的 state 比例
* 只有 CF-GUARD 正 advantage 的 state 比例
* 兩者衝突時，哪個在 realised pooled EE 上勝出
* 各自覆蓋哪些 handover／QoS regime
* source-conditioned regret

第二個 Catfish 的必要條件不是 global score 不同，而是：

```text
有一個可辨識的 state region，
第二 specialist 提供第一 specialist 沒有的正確 action。
```

---

## D. 先做 supervised representability gate

在實作 DQfD 前，使用相同 observation 訓練一個簡單 ranker／behavior-cloning head，測：

* OOS top-1
* top-k recall
* action regret
* mask legality
* action coverage
* calibration
* specialist action是否能由 learner-visible state 預測

若模仿不了：

* 不應直接使用 DQfD margin loss
* 先增加必要 observation features
* 或將該 specialist 設為 replay-only source

這比直接修改 600 行 trainer 再跑大訓練便宜得多。

---

## E. 一個 source 先選 mechanism，再測 multiple sources

不要直接做完整 factorial。

第一輪固定 `CF-EE` demonstrations，比：

| arm                                     | 用途                   |
| --------------------------------------- | -------------------- |
| `D0` no demonstrations                  | 必要控制                 |
| `D1` replay-buffer spike only           | 判斷是否只是資料             |
| `D2` faithful RIS Catfish               | 原論文比較臂               |
| `D3` full DQfD                          | published family     |
| `D4` Q-filtered／advantage-filtered DQfD | proposed utilization |

先決定哪種 demonstration utilization 有效。

第二輪才固定 winner，測：

| arm             | sources              |
| --------------- | -------------------- |
| `S0`            | none                 |
| `S1`            | `CF-EE`              |
| `S2`            | `CF-EE + CF-GUARD`   |
| `S2-unlabelled` | 兩來源混在一起但不給 source id |

其中 `S2` 對 `S1` 才是 Multi-Catfish 的主 marginal。

這樣可以分離：

* demonstrations 是否有效
* DQfD／RIS mechanism 是否有效
* 多一個 specialist 是否有效
* source-aware gate 是否有效

---

# 八、必須先修正 objective，否則 Catfish 只會更快學錯

這是最重要的設計前提。

目前已有直接證據顯示：

* learner 能把 scalar objective 學得比 myopic rules 好
* 但該 objective 因 r2 懲罰 handover，反而讓 pooled EE 低於 max-gain rule
* r2 在 V0.23 沒有對應的 energy 或 interruption cost
* r3 occupancy 與實際 payload power derivative 方向不一致
* 固定 \(B-\eta E-\Phi\) 無法保持 \(B/E\) ordering
* boundary-0 objective 和 full-48 endpoint horizon 不一致

所以所有比較 Catfish 的 arms 必須共享一個**新的 corrected baseline**。

建議：

```text
B0 = corrected ratio-consistent MODQN, no demonstrations
B1 = B0 + one Catfish
B2 = B0 + two Catfish
```

原始 MODQN checkpoint只能作為 external historical baseline，不能作為 Catfish causal control。

否則如果 B2 比原始 MODQN好，無法分辨是：

* objective 修正造成
* handover physics 修正造成
* Catfish demonstrations 造成
* DQfD mechanism 造成

---

# 九、建議的新 learner objective

一個可行的設計候選是保留兩個可加總的 critic：

```text
Q_B(s,a) = expected delivered bits
Q_E(s,a) = expected consumed joules
```

action selection 使用 adaptive multiplier：

$$
a^*
=
\arg\max_a
\left[
Q_B(s,a)-\eta_k Q_E(s,a)
\right]
$$

其中：

$$
\eta_{k+1}
=
\frac{\sum B(\pi_k)}
     {\sum E(\pi_k)}
$$

QoS／service 應優先作為：

* hard action mask
* constrained critic
* non-inferiority guard

而不是再加一個固定大權重的 reward。

如果保留第三 head，應是具有明確物理或約束語義的量，例如：

```text
Q_service_violation
```

但 action selection 應是 constrained optimization，而不是固定：

```text
Q_B + Q_E + Q_QoS
```

這一部分需要文獻深挖，因為要嚴格區分：

* \(E[B]/E[E]\)
* \(E[B/E]\)
* sample pooled \(\sum B/\sum E\)
* finite-horizon ratio
* long-run reward-per-cost ratio

---

# 十、需要 Deep Research，但要做聚焦式的三軌研究

**需要。** 而且建議在 Claude session 恢復、解除任何舊訓練之前完成。

不需要再做一次泛泛的「DQfD 是什麼」研究；現有 `DQFD-FAMILY-GROUNDING` 已足夠。

真正需要的三條研究軌是：

## DR-1：Ratio／fractional reinforcement learning

核心問題：

> 對有限時域或 average-reward MDP，如何正確最大化 pooled bits / pooled joules？

應比較：

* Dinkelbach policy iteration
* reward-per-cost／semi-Markov formulations
* average-reward RL
* two-critic ratio optimization
* direct ratio policy gradient
* constrained MDP
* off-policy DQN compatibility
* convergence及估計偏差

產出必須回答：

* 哪個 formulation 與本專案 endpoint 一致
* 如何建立 per-transition training signal
* demonstrator advantage 如何計算
* 是否可在 discrete masked DQN 中實作

---

## DR-2：Multiple heterogeneous demonstrators

需要查清：

* one shared demo buffer vs per-source buffers
* state-dependent teacher selection
* Q-filter／advantage filtering
* source confidence
* curriculum／ZPD
* negative transfer
* conflicting demonstrators
* source-conditioned policy或source-agnostic policy
* 多 specialist 數量的合理 ablation

目前公開工作已包含：

* multiple conflicting demonstrators 的 Bayesian weighting
* 最佳 demonstrator 不一定是最佳 teacher
* demonstration-guided MORL
* imperfect demonstration filtering

因此「有多個 specialist」本身不會構成 novelty。([arXiv][5])

真正可能有新意的是：

> **ratio-consistent EE specialists + physical guards + source-aware advantage-filtered DQfD，在 LEO handover 上的整合。**

---

## DR-3：LEO handover 與 payload 的物理成本

應聚焦：

* same-satellite／inter-satellite handover interruption
* interruption distribution，不只固定常數
* signalling／reacquisition／beam switching energy
* active beam fixed payload power
* active satellite baseband cost
* PA supply vs radiated power
* tens-of-seconds timescale是否合理
* nominal future geometry是否可用於 deployment
* service／QoS guard應採什麼標準

這會決定 `CF-GUARD` 和 `CF-PAYLOAD` 是否具有可發表的物理基礎。

---

# 十一、Claude session 恢復前的建議交接包

建議先在獨立目錄建立：

```text
.scratch/chatgpt-multi-catfish-redesign-20260911/
```

內容應包括：

```text
00-EVIDENCE-LEDGER.md
01-OBJECTIVE-RESET.md
02-SPECIALIST-CANDIDATES.md
03-SPECIALIST-SCREEN-CONTRACT.md
04-DEMO-UTILISATION-ARMS.md
05-MULTI-SOURCE-GATES.md
06-DEEP-RESEARCH-FINDINGS.md
07-CLAUDE-RESUME-DELTA.md
```

`CLAUDE-RESUME-DELTA.md` 第一段應明確寫：

```text
Do not resume any C1/C2/C3 current-design training.
Treat those routes as a closed negative branch pending the formal
C1VSGAIN bootstrap ruling.

Read the ratio-objective and specialist-screen package first.
The new question is not how to repair C1/C2/C3.
It is whether one or two physically grounded specialist sources,
used through a DQfD-family mechanism, improve a corrected
ratio-consistent MODQN baseline.
```

OOSPANEL 若仍在正常跑，讓它完成；其他 paused training 不解除。

---

# 最終建議

最值得進行的主線是：

## **Ratio-consistent Two-Specialist DQfD**

```text
Corrected MODQN objective
        │
        ├── CF-EE
        │     full-horizon pooled-EE specialist
        │
        └── CF-GUARD
              pooled-EE specialist with
              physical handover interruption
              + QoS/service constraints
```

訓練機制：

```text
shared source-tagged demo replay
+ low/adaptive demo ratio
+ n-step TD / prioritized replay
+ Q-filtered or positive-advantage imitation
+ one deployed main agent
```

比較臂：

```text
corrected no-demo MODQN
faithful RIS Catfish
single-source DQfD
two-source Multi-Catfish DQfD
original MODQN external baseline
```

第三個 `CF-PAYLOAD` 暫時只做無學習 specialist screen；未通過 representability 和 unique-advantage gate 前，不升格成第三個 Catfish。

因此，接下來的正確順序是：

1. 正式封存 C1／C2／C3 負結果。
2. canonicalize pooled-EE 反轉結果。
3. 做 hysteresis／physical-interruption Pareto sweep。
4. 找出並驗證第二 specialist。
5. 做 ratio-RL 與多 demonstrator 的聚焦式 Deep Research。
6. 先選 demonstration utilization mechanism。
7. 最後才比較 one-Catfish 與 two-Catfish。

**目前已有足夠證據支持「先做一個 EE Catfish」，也有足夠跡象支持尋找第二個 guarded Catfish；但還沒有證據支持直接做三個。**

[1]: https://arxiv.org/abs/1704.03732 "https://arxiv.org/abs/1704.03732"
[2]: https://arxiv.org/html/1709.10089v2 "Overcoming Exploration in Reinforcement Learning with Demonstrations"
[3]: https://arxiv.org/html/1909.01387v1 "Making Efficient Use of Demonstrations to Solve Hard Exploration Problems"
[4]: https://arxiv.org/abs/1910.12154 "https://arxiv.org/abs/1910.12154"
[5]: https://arxiv.org/abs/2006.05725 "https://arxiv.org/abs/2006.05725"
