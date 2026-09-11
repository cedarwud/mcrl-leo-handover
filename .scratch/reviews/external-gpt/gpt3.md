## 結論

我重新讀取了 Claude 主 session `e9fba164-4724-465f-8afa-7891b4efee90`、最新 registry、四個 live sub-agent transcript、B0 評估輸出與 CFSCREEN 完整報告。

我的裁決是：

> **可以在今天（2026-09-11）晚上把「三個 Catfish 候選版」凍結並開始短 episode pilot，但目前宣告的版本不建議原封不動啟動。應先做一次 pre-result amendment。**
>
> **工程可行性高；三隻 Catfish 全部各自帶來正 EE marginal 的科學可行性，目前不是高機率。**

更精確地區分：

| 問題                                                  | 判斷                                      |
| --------------------------------------------------- | --------------------------------------- |
| 今晚能否完成實作、smoke、啟動短 pilot                            | **可行性高**                                |
| A2 三 Catfish 臂能否贏舊 MODQN baseline                   | **有合理機會**，但可能主要是新 objective／learner 的功勞 |
| A2 能否同時贏 A1 OFF 與 A3 NULL3，證明 Catfish 有方向性效果        | **目前未知，約中等偏低信心**                        |
| 後續 drop-one ablation 能否證明 C1、C2、C3 三者各自都有正 marginal | **目前偏低**                                |
| 是否已有三個不同且有潛力的行為來源                                   | **有**                                   |
| 是否已證明它們適合「一隻只訓練一個 Q-network」                        | **沒有**                                  |

因此不能把「三個 source policy 已找到」直接等同於「三個 head-specific Catfish 已證明成立」。

---

# 一、目前實際進度

目前**三 Catfish 訓練還沒有開始**。

## B0CORRECT

已完成：

* baseline MODQN 的 `eq16-per-head-max` 模式保留。
* 新 learner 的 shared-continuation bootstrap 已做成開關。
* outage floor 修正。
* calibrated scalar logging。
* TLE archive 已固定：

  * 路徑：`/home/sat/mcrl-v025-b0-ws/tle-pinned-427e6a91`
  * hash：`427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9`
* local／sat 的 RANDOM placebo 已逐位元一致。
* `READY FOR PILOT` 已寫入 `.scratch/b0-corrected/PROGRESS.md`。
* 500-episode round-2 評估也已完成。

固定 TLE、500 episode 的結果：

| arm                |         pooled EE |  served | handover rate | calibrated scalar |
| ------------------ | ----------------: | ------: | ------------: | ----------------: |
| `BASELINE_EQ16`    | **85.977 Mbit/J** | 0.99817 |        0.1845 |            0.6298 |
| `SHARED_BOOTSTRAP` | **85.156 Mbit/J** | 0.99867 |        0.1720 |        **0.8099** |
| RANDOM             |     52.421 Mbit/J | 0.93583 |        0.8695 |           −1.6680 |

這代表 shared bootstrap 在 500 episode 時：

* 訓練 scalar 較高；
* handover 較低；
* pooled EE 尚未較高。

差異很小，而且只是 500 episode，不能解讀為失敗；但它也表示目前沒有證據保證新 learner 天然會提高 EE。

依據：

* `.scratch/b0-corrected/PROGRESS.md`
* `/home/sat/mcrl-v025-b0-ws/r2-eval-ep500.log`
* commit `363845e8`

## CF3PILOT

目前只完成部分 source-policy 程式：

```text
src/mcrl/algorithms/cf_sources.py
```

尚未完成：

* `DECLARATION-ADDENDUM.md`
* `cf_ratio.py`
* trainer
* tests
* server workspace
* `eta_0`
* smoke
* 正式 training launch

`/home/sat/mcrl-v025-cf3-pilot-ws` 目前甚至尚未建立。

CF3PILOT 在開始寫 `cf_sources.py` 後遇到 Claude usage limit。沒有任何 CF3 訓練 process 在 server 上執行。

## CFSCREEN

主要報告已經寫完：

```text
.scratch/catfish-screens/CATFISH-SCREENS-2026-09-11.md
```

這份報告提供了目前判斷三隻 Catfish 最重要的依據。

## CURATE

已開始整理：

* `.scratch/DOCUMENT-STATUS.md`
* `.scratch/curation/PROVENANCE-HEADER.md`

但 `.scratch/RESULTS-REGISTRY.md` 尚未完成。

目前四個主要 agent 都因 usage limit 停在原 transcript；我沒有恢復它們，也沒有修改專案。

---

# 二、三個 Catfish 現在是否真的各自存在

目前凍結版本是：

| Catfish | source rule      | head  |
| ------- | ---------------- | ----- |
| C1      | `A m=2dB`        | `Q_B` |
| C2      | `A m=12dB`       | `Q_H` |
| C3      | `B1_NO_NEW_BEAM` | `Q_E` |

依據：

```text
.scratch/multi-catfish-v025-physics-successor/
V025-CONTROLLER-DECLARATION-THREE-CATFISH-PILOT-2026-09-11.md
```

## C1：有強 specialist，但與 C2 是同一家族

`A m=2dB`：

* local FEASFRONT pooled EE：`112.459 Mbit/J`
* inter-satellite handover：`0.5497`
* 在宣告的 `0.6016` 上限內
* BC probe held-out top-1：`0.838`
* closed-loop probe 只損失約 `1.3% EE`

所以 C1 確實是：

* 可由 learner observation 表達；
* 有明顯 headroom；
* learner 目前不同意它的大部分 action；
* 有東西可以教。

但要修正敘事：

> `A m=2dB` 不是純 gain-only 規則。它也讀 incumbent，實際是**aggressive hysteresis**。

純 gain-only 是 `m=0` 的 `MAX_NOMINAL_GAIN`。

## C2：最容易學，但可能在目前 constraint 下完全不啟動

`A m=12dB`：

* pooled EE：`101.467 Mbit/J`
* total handover：`0.2258`
* inter-satellite handover：`0.2248`
* BC probe top-1：`0.935`
* closed-loop probe幾乎完整重現 source operating point
* 與 C1 在相同 state 上有 `35%–55%` action disagreement

所以 C2 的 action target 是不同的，而且非常容易學。

但它有兩個問題。

### 問題一：C1 和 C2 是同一 hysteresis family 的不同 threshold

CFSCREEN 證明：

* C1／C2 的 action disagreement，幾乎恰好就是 gain gap 落在 `(2,12] dB` 的那些 state。
* C2 的 state distribution 被 C1 包含。
* C2 沒有帶來 C1 沒去過的新 state。

因此兩者可以說是兩個**不同 action specialists**，但不能說是兩個不同資訊來源或兩個不同 state-coverage Catfish。

比較誠實的命名是：

* C1：aggressive hysteresis specialist
* C2：conservative hysteresis specialist

### 問題二：目前 `Q_H` 很可能是 dormant head

目前 action rule 是：

$$
\arg\max_a
\left[
Q_B-\eta Q_E-\lambda Q_H
\right]
$$

但：

* `lambda_0 = 0`
* 只有 inter-satellite handover 超過 `0.6016` 才提高 λ
* C1 的 `A m=2dB` 已經是 `0.5497`
* C2 是 `0.2248`
* C3 既有結果也低於上限
* frozen learner 本身約 `0.2243`

也就是目前已知所有合理 policy 都可能在 constraint 內。

若 training 中 greedy policy 也低於 `0.6016`：

```text
lambda = 0
```

那麼：

```text
Q_H 完全不進入 action argmax
```

C2 只是在訓練一個部署時沒被使用的 network。

這是目前三 Catfish 設計最大的結構風險之一。

在這種情況下，即使 A2 CF3 勝出，也比較接近：

```text
C1 + C3 + 一個 dormant C2
```

不能說是三隻 Catfish 都有效。

---

## C3：最有獨特性，但也是最危險的一隻

`B1_NO_NEW_BEAM`：

* pooled EE：`103.475 Mbit/J`
* active beams：約 `37.9`
* frozen learner：約 `67.9`
* energy 約 learner 的 `0.57×`
* states 與 learner 最不同：

  * coverage ratio `R = 2.19–2.25`
  * `out95 ≈ 0.66–0.67`
* 與 C1／C2 action disagreement約 `44%–72%`

這是目前唯一真正帶來不同 state coverage 的 Catfish。

但 representability 最弱：

* BC top-1：`0.714`
* 7.4% 的預測會點亮 source 明確禁止的新 beam
* closed-loop probe：

  * source 37.9 beams
  * probe 47.3 beams
  * 只保留約 68% consolidation
  * EE 相對 source 下降 `4.28%`，約 `−7.5 SEM`

所以 C3 有最大的潛在互補價值，也有最大的學習失敗風險。

我的目前排序是：

1. **C2 最容易被網路學到**
2. **C1 有最強的直接 EE source**
3. **C3 最具獨立性，但最可能在 learner 裡失真**

---

# 三、目前版本不能原封不動開跑的四個原因

## 1. `gamma = 0.9` 與 pooled finite-horizon EE 不一致

新 learner 的 endpoint 是：

$$
\frac{\sum_{t=0}^{9}B_t}
{\sum_{t=0}^{9}E_t}
$$

這是十個 step 等權加總。

但目前宣告寫：

> `gamma` as in baseline trainer, unchanged.

也就是 `γ=0.9`。

那第十個 step 的權重只有：

$$
0.9^9 \approx 0.387
$$

這表示 learner 實際估計的是：

$$
\frac{
B_0+0.9B_1+\cdots+0.9^9B_9
}{
E_0+0.9E_1+\cdots+0.9^9E_9
}
$$

而 eta 更新卻來自 undiscounted pooled sums。

這是兩個不同 objective。

**建議：**

* A0 baseline 繼續使用論文版 `γ=0.9`。
* A1／A2／A3 新 ratio learner 使用 finite-horizon `γ=1.0`，episode terminal 保持真 terminal。
* A1 作為控制臂，自然吸收「gamma／objective change」的效果。

若堅持 `γ=0.9`，就必須把方法稱為 discounted ratio learner，不能聲稱其 TD target與 primary pooled EE 一致。

這一點應在第一個 CF3 結果出現前 amendment。

---

## 2. 一個 source 只訓練一個 head，會產生不一致的 Q-vector

目前宣告是：

* C1 transition只進 `Q_B`
* C2 transition只進 `Q_H`
* C3 transition只進 `Q_E`

但每筆 transition 明明都已經帶有完整：

```text
(B, E, H)
```

目前設計可能形成：

* `Q_B` 知道 C1 action 的 bits
* `Q_E` 沒在 C1 action 上看過對應 energy
* `Q_H` 沒在 C1 action 上看過對應 handover
* 最後卻把三者相加選 action

這會產生一個「Frankenstein Q-vector」：

$$
Q_B(s,a)
-\eta Q_E(s,a)
-\lambda Q_H(s,a)
$$

三個分量可能來自不同 state-action support。

尤其 C1 和 C2 在 35%–55% state 上教不同 action，這個問題會很明顯。

### 建議修正

保留語意上的一對一：

| source | primary meaning     |
| ------ | ------------------- |
| C1     | bits specialist     |
| C2     | handover specialist |
| C3     | energy specialist   |

但**每筆 transition 應更新三個 head**：

```text
C1 sample carries B/E/H → trains Q_B/Q_E/Q_H
C2 sample carries B/E/H → trains Q_B/Q_E/Q_H
C3 sample carries B/E/H → trains Q_B/Q_E/Q_H
```

一對一表示「這個 source 是為哪個物理量設計」，不是「把另外兩個真實 label 丟掉」。

最簡單且較一致的 common batch：

```text
8/9 main replay
1/27 C1
1/27 C2
1/27 C3
```

總 demo fraction仍是 `1/9`，三個 head共用同一批 transition。

這也比較符合 shared-continuation Q-vector 的數學要求。

目前宣告所稱「Nair 的 1/9」只支持總示範比例的近似參考，並不直接支持「每個 head各自 1/9、且只訓練一個 head」；這必須標成專案自訂。

---

## 3. C2 constraint 很可能不 binding

如前述，`0.6016` 高於目前最佳 C1 source 的 `0.5497`。

不能為了讓 C2 有效果，在看到數字後把 threshold 改成 0.40；那會變成為了產生正結果而挑 constraint。

因此較乾淨的作法不是強迫 λ 非零，而是：

* 保留 `0.6016`
* 明確記錄：

  * λ trajectory
  * `lambda > 0` 的 episode比例
  * `Q_H` 項有沒有改變 argmax
  * 去掉 `Q_H` 後 action 改變多少
* 預先寫死：

  * 如果 λ 全程為 0，且 `Q_H` 改變 action <1%，C2 在這個 pilot 中判定為 **inactive**
  * 即使 A2 勝出，也不算三隻都有效

長期要讓 C2 成為真正的 constrained head，較正規的方法是：

* remaining handover budget進入 state
* `Q_H` 預測累積 constraint consumption
* 在 target argmax與deployment action mask中排除會超過 remaining budget 的 action

這比較接近 constrained DQN／shielding，而不是一個可能永遠為零的 Lagrange multiplier。

今晚的 pilot不必先實作完整 shield，但必須加 activation diagnostic。

---

## 4. 三個 source 的 headroom 還不是在 pinned TLE 上量的

FEASFRONT 與 CFSCREEN 的：

* 112.46M
* 101.47M
* 103.47M

都是 local、unpinned TLE 條件。

後來 B0 已發現：

* local RANDOM：53.060M
* pinned sat RANDOM：52.421M

所以不能直接把原 source 結果當成 pinned pilot 的正式先驗。

這不表示三條規則失效；但在它們被凍結成 source 之前，應在 pinned TLE 上重新跑一次：

```text
TRAINED
A m=2dB
A m=12dB
B1_NO_NEW_BEAM
RANDOM
```

只需無訓練 rollout。

必須確認：

* C1仍是高 EE source
* C2仍同時有較低 handover與合理 EE
* C3仍顯著減少 energy／active beams
* 三者都符合 C-S
* C1是否仍低於 C-H 0.6016

若 pinned ranking翻轉，現在的三 source選擇就不能稱為已定案。

---

# 四、另一個應記錄但可先不阻擋 pilot 的風險：Q_E credit assignment

目前：

$$
E_u =
\frac{P_{\mathrm{sys}}\Delta t}{U}
$$

同一步裡每個 user拿到完全相同的 energy label。

優點是：

$$
\sum_u E_u = E_\mathrm{sys}
$$

精確 closure。

缺點是 learner 看不出：

* 哪個 user點亮了新 beam
* 哪個 user提高了某 beam的 max power
* 哪個 user讓 satellite從 inactive變 active

`Q_E(s_u,a_u)` 得到的是一個 global team reward，而不是 action-specific energy contribution。

這會讓 C3 特別難學，與 CFSCREEN 中 C3只有 `0.714` top-1 的結果相符。

在正式長訓練前，應考慮改成精確可加總的 attribution：

* 每 beam 的 PA＋circuit energy在該 beam users間分攤
* satellite baseband energy在該 satellite的 served users或 active beams間分攤
* 保持：

  $$
  \sum_u E_u = E_\mathrm{sys}
  $$
* 同時讓 \(E_u\) 隨 user選擇的 beam改變

今晚可先保留 equal share，但需增加一個 no-training diagnostic：

> 固定其他 99 users，將第 u 個 user從 incumbent改成 C3 action，測 \(\Delta E_\mathrm{sys}\) 的分布。

如果大多數局部 action的 energy contrast接近零，`Q_E` 無法靠目前 local observation穩定學到 consolidation，C3 pilot負結果就不能解讀成 C3概念失敗。

---

# 五、目前 pilot 並不是 faithful RIS Catfish，也不是 DQfD

目前 A2 的實際機制是：

* 三個 scripted behavior policies
* 三個 source buffers
* uniform source mixing
* raw rewards
* 沒有 imitation loss
* 沒有 n-step
* 沒有 prioritized replay
* 沒有 ACRM
* 沒有 EE threshold stratification
* 沒有 asymmetric discount
* 沒有 RIS 的 70/30 intervention

所以最準確的名稱是：

> **three-source Catfish-inspired off-policy replay pilot**

或：

> **source-conditioned hybrid Q-learning pilot**

它是在測：

> 三個有方向的行為來源，是否比三個 random sources提供更有用的 replay data。

這是一個合理而且低風險的第一步；但不能在 pilot成功後直接寫成：

* faithful RIS Catfish成功
* DQfD成功
* ACRM成功

DQfD／RIS Catfish應在 source-value signal成立後，成為後續 demonstration-utilisation比較臂。

---

# 六、今晚建議凍結的修正版

我建議保持三隻的身份不變，但把技術版本改成：

## C1 — aggressive hysteresis／bits source

```text
A m=2dB
primary association: Q_B
```

## C2 — conservative hysteresis／handover source

```text
A m=12dB
primary association: Q_H
```

敘事承認它和 C1是同一家族的不同 operating point。

## C3 — consolidation／energy source

```text
B1_NO_NEW_BEAM
primary association: Q_E
```

## Learner

```text
Q_B, Q_E, Q_H
shared continuation action
argmax [Q_B - eta Q_E - lambda Q_H]
```

但需做以下更正：

1. A1／A2／A3 使用 `gamma=1.0`。
2. 所有 source transition更新三個 head。
3. total source fraction為 `1/9`，三 source各 `1/27`。
4. eta在前 500 episode固定為 `eta_0`。
5. A1通過 learning check後，才允許 ep500更新 eta。
6. 保留 λ dual update，但強制報告 C2 activation。
7. 先在 pinned TLE重跑三 source。
8. 所有 code進 isolated worktree，不再直接在 shared tree並行改 `modqn.py`。

這樣仍然符合：

> 三個 Q-network各有一個主要 Catfish來源。

但不會為了圖上的一對一，把完整的真實 transition label切碎。

---

# 七、今晚實際執行順序

## 第 1 步：完成現有兩份結果的收尾

* B0CORRECT只需把已完成的 round-2 eval寫回報告。
* CFSCREEN已產生完整報告，只需完成 progress與commit。
* 不必等待 CURATE完成整個 registry才開始實作，但新報告必須使用 provenance header。

## 第 2 步：CF3PILOT建立獨立 worktree

目前它已直接在 shared tree產生未追蹤的：

```text
src/mcrl/algorithms/cf_sources.py
```

之前 B0／PENALTYARM已經發生一次並行修改 `modqn.py` 的事故。

因此後續應改到：

```text
branch: cf3/pilot-20260911
worktree: /home/u24/papers/mcrl-leo-handover-cf3
```

shared tree只用來讀，不再由 CF3PILOT直接寫。

## 第 3 步：先寫 amendment，再看任何結果

至少寫明：

* gamma
* common vector replay
* source fraction如何整數化
* eta第一次更新時間
* C2 inactive判定
* pinned source重測
* Q_E attribution caveat
* 此 pilot不是 faithful RIS／DQfD

## 第 4 步：pre-launch tests

必須有：

1. `A m=2/12`、B1與 FEASFRONT source parity。
2. pinned TLE source-only rollout。
3. `Σ_u B_u = system bits`。
4. `Σ_u E_u = system joules`。
5. `Σ` head TD target等於 scalar transformed TD target。
6. shared continuation action在三 head完全相同。
7. source env RNG不改變 main env RNG。
8. A1與 A2在 source sampling前的 main rollout逐位元一致。
9. NULL3確實 uniform legal。
10. source比例精確、可重現。
11. checkpoint resume不重複 episode。
12. eta／lambda只在預定 boundary更新。

## 第 5 步：三 episode smoke

每一 arm至少確認：

* 三個 loss有限
* Q-value有限
* source buffers有資料
* 每個 head真的抽到預定來源
* NULL3與 CF3 batch shape完全相同
* main agent是唯一 evaluated policy
* pinned TLE hash寫進 receipt

## 第 6 步：100 episode diagnostic

這不是結果，只檢查：

* Q_B／Q_E／Q_H的尺度
* transformed Q中三項的實際占比
* C2的 λ／argmax activation
* C3 source是否改變 Q_E ranking
* CF3與 NULL3是否已經完全沒有可辨識差異
* replay composition是否正確

## 第 7 步：四臂 × 三 seed × 1000 episode

保留目前 arms：

* A0 baseline MODQN
* A1 new learner OFF
* A2 CF3
* A3 NULL3

ep500 early stop規則保留。

---

# 八、今晚什麼結果才算真正有意義

## A2 贏 A0

只表示：

> 整套新方法達到使用者設定的成功門檻。

不能歸因給 Catfish，因為 A2同時改了：

* reward decomposition
* ratio objective
* bootstrap
* outage handling
* Catfish replay

## A2 贏 A1

表示加入三個有方向的 source，比無 source的新 learner好。

## A2 贏 A3

表示不是「多三個 environment／多 replay data」就能做到，而是 source方向有意義。

## A2 同時贏 A1與 A3

這才是第一個 Catfish directional signal。

另外還要同時滿足：

* C-H
* C-S
* 至少 2/3 paired seeds同方向
* 結果不是只由某一個 eta／lambda跳變造成
* C2不是全程 inactive
* C3 buffer確實被採樣且改變 Q_E

即使這些都通過，也只能說：

> 三 source bundle有正 signal。

仍不能說三隻各自有效。

後續一定要跑：

```text
CF3
DROP_C1
DROP_C2
DROP_C3
OFF
NULL3
```

才能回答每隻的 marginal。

---

# 九、成功機率的誠實判斷

## 「找到三個具有合理角色的 source policy」

這部分已經做到，證據比之前強很多。

* C1：高 EE／aggressive
* C2：低 handover／conservative
* C3：low-energy／distinct coverage

所以不是憑空湊三隻。

## 「三 source replay讓 learner贏 baseline」

有真實機會。

原因：

* 三個 source本身都在既有 matched local screen高於 frozen learner。
* 所有規則都可由 observation精確表示。
* CFSCREEN證明它們不是都選同一批 action。
* C3確實走到 learner沒去過的 state。

## 「三隻各自對應一個 head，三隻都有獨立正 marginal」

目前不能說機率高。

主要原因：

1. C2可能因 λ=0完全不作用。
2. C1／C2是同一家族的兩個 threshold。
3. C3最難學，而且 equal-share energy credit很弱。
4. 目前沒有任何一次 Catfish ON/OFF training結果。
5. 現行 exclusive routing會讓三個 Q-head的 state-action support不一致。
6. 1000 episode、3 seeds最可能得到的是方向不明確，而不是乾淨結論。

我的實際判斷是：

> **三 source bundle提高 EE：有合理機會。**
>
> **三隻都必要、都能在 drop-one 中顯示正 marginal：目前偏低。**
>
> **最可能的成功形狀是 C1或C2其中一隻加上 C3有效，而另一隻主要提供冗餘或穩定性。**

這仍可能形成兩隻或三隻的論文，但不能先假設最後一定是三隻。

---

# 十、現在需不需要再做 Deep Research

目前不需要再做廣泛 Deep Research來阻擋今晚的 pilot。

現有研究已經回答：

* ratio objective應使用 `B−ηE` inner problem
* pooled EE是 evaluation endpoint
* raw B/E replay重算是專案自己的新做法
* 多來源的合理性來自 coverage
* DQfD固定 margin有 misaligned-demonstration風險
* JSRL、Hy-Q、constrained DQN是後續可比較的成熟家族
* 沒有現成論文涵蓋目前完整配置

現在真正的瓶頸是：

* gamma一致性
* replay routing
* C2 activation
* Q_E credit assignment
* pinned source parity

這些是程式與實驗問題，不是再搜尋十篇論文能解決的問題。

後續若 pilot有正 signal，再做一輪聚焦研究：

> **多來源、raw-vector replay、Dinkelbach outer loop、masked discrete Q-learning的理論定位與最接近先例。**

目前不需要因研究而延後第一輪短 pilot。

---

## 最終建議

我給現在版本的裁決是：

> **GO AFTER PRE-LAUNCH FIXES。**

今天晚上可以定案的是：

> **三 Catfish candidate pilot v0.1**

不能定案成：

> **已確認有效的最終三 Catfish方法**

三隻身份可以保留：

* C1 → aggressive hysteresis → `Q_B`
* C2 → conservative hysteresis → `Q_H`
* C3 → no-new-beam consolidation → `Q_E`

但在第一個 training result前，至少應修正：

1. 新 learner `gamma=1`
2. source transition訓練完整 B/E/H vector
3. total demo ratio `1/9`，不是三個互相割裂的 head batch
4. pinned TLE source重測
5. C2 inactive判定與 activation logging
6. isolated worktree與 RNG parity tests

**原封不動啟動目前 frozen declaration，確實有相當機率得到一個難以解釋的結果；做完上述修正後，今晚的 pilot才會是一個能真正幫助決策的實驗，而不是只為了「今天有開始訓練」而開始。**
