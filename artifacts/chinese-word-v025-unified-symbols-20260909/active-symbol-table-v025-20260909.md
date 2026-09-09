# 單一 SINR 角度感知 EE 正式符號表

- **狀態：** `ACTIVE SYMBOL AUTHORITY`
- **原始日期：** 2026-08-17
- **正式升格日期：** 2026-08-19
- **集合記法修訂：** 2026-08-20 —— 集合符號改回花體（𝒰、𝒮、𝒱、𝒞、ℱ），集合大小改回同字母正體大寫（U、S、V、C、F），取代原本「不使用花體、以 N_U 前綴或 \(|U|\) 表集合大小」的規定。理由：花體集合＋正體大寫基數是 MODQN（Sun et al.）、HOBS（Chen et al.）與一般 RL 文獻的通用慣例，貼近此慣例才不會讓 CH4／CH5 簡報的記法反而偏離普遍論文寫法；技術上花體字母可用 Unicode Mathematical Alphanumeric Symbols（Cambria Math 內建，PowerPoint／Word 方程式編輯器 Scripts 分類即可插入）直接嵌入原生 OMML，不需要額外字型或樣式標記，先前判定「不可行」的疑慮已排除。
- **適用範圍：** 新版論文公式同步、Phase-C 英文 CH4／CH5 概念簡報與未來模擬器對照
- **同步邊界：** 本表、正式公式規格、三下標裁決、論文 base sources、三份 DOCX 與 production Family-B runtime／consumer 已完成 previous-step recurrence parity；fresh calibration、prereg 與 episode-0 training 仍須另行過關


## 2026-09-05 紙面 V0.23 單字母記號擴充層（以 R1 為基線）

本份鏡像表是給純中文版論文與 Word 紙面使用的 V0.23 版本化副本。它承接
R1 的角度感知能量效率／功率主鏈記號，並加入 current C1／C2／C3 route、
LC-SRS teacher／student 與 one-pass deployment 的單字母上下標；原始
MODQN-only 公式、歷史來源與程式欄位名稱不因本擴充層改寫。

| 舊紙面記號 | 本版紙面記號 | 定義 |
|---|---|---|
| $\theta_{3dB}$ | $\theta_3$ | 全 3 dB 半功率波束寬；半功率單邊角為 $\theta_3/2$ |
| $p_{\max}$ | $p^{+}$ | 每波束 RF 輸出上限 |
| $p_{\mathrm{sat}}$ | $p^{s}$ | 飽和功率參考值 |
| $\xi_{\max}$ | $\xi^{+}$ | 最大轉換效率 |
| $N^{\mathrm{act}}_s$ | $N^a_s$ | 衛星 $s$ 的啟用波束數 |
| $P_{\mathrm{cir}}$, $P_{\mathrm{BB}}$ | $P^c$, $P^b$ | 電路與基頻固定功率 |
| $P_{\mathrm{RF}}$, $P_{\mathrm{DC}}$ | $p_{s,v}$, $P^p_{s,v}$ | 射頻輸出與電源端功率 |
| $G_{R,\min}$, $G_{R,\max}$ | $G^R_{-}$, $G^R_{+}$ | 接收增益下、上界 |
| $\theta^R_{\min}$ | $\theta^R_{-}$ | 接收型樣的下限角 |
| $A_{\mathrm{zen}}$ | $A^z$ | 天頂大氣吸收常數 |
| $I^{\mathrm{intra}}$, $I^{\mathrm{inter}}$ | $I^i$, $I^x$ | 同衛星與跨衛星干擾 |
| $B_{\mathrm{sys}}$ | $B^g$ | 系統總頻寬 |
| $NF$, $BO$ | $N_f$, $b_o$ | 雜訊指數與輸出回退 |

這些替換不改變物理關係、數值結果或 Chapter 5 的結果資料；它們只把新 R1
紙面符號統一到本版表格。V0.23 的 C2、C3、$\lambda$、$\kappa$、teacher／student
公式與 one-pass deployment surface 由第 10.13 節定義；本表不把 gate outcome
誤寫成效能結論。

## 2026-09-09 V0.25 繼任者符號合併層（本檔為唯一合併權威）

本檔逐字承接 `active-symbol-table-v023-20260905.md` 的全部內容，並把 V0.25 物理繼任者
（主模型 `V025-ANGLE-RATE-TPC-TDM-ACM`，代號 a-r）所需的新增與再定義量一次併入，
使符號只有一個現行版本。V0.23 原有列一律不改寫；狀態變更與消歧以獨立列記錄。

- **合併日期：** 2026-09-09
- **權威順序（衝突時由高至低）：**
  ① `active-symbol-table-v023-20260905.md`（既有列一律勝出）；
  ② `SYMBOL-COLLISION-AND-SINGLE-LETTER-AUDIT.md`（碰撞規則具約束力）；
  ③ `SYMBOL-ADDITIONS.md`（V0.25 紙面新增草案）；
  ④ `.scratch/multi-catfish-v025-physics-successor/` 之密封宣告（優先序宣告 v1.0–v1.9、
  stages 6–8 契約 v1／v1.1／v1.2、CH5 掃描圖規格、stage-4h ACM 更正確認）。
- **新增標記：** 【新】＝本合併層新增列；【改】＝既有符號在 V0.25 的角色或狀態變更，
  原列保留不動、變更另立一列。未帶標記者即 V0.23 原文。
- **碰撞規則不變（權威順序 ②）：** 紙面主符號的上下標只使用單一字母或單一數字；
  `ref`／`src`／`dst`／`beam`／`sat`／`own`／`nf`／`joint`／`base`／`cand`／`main`
  等多字母上下標不得進入公式；複合索引必須由原子字母或數字組成；不使用 hat。
- **未靜默裁決：** 兩份來源對同一物件給出不同字形或不同語意者，本表依上列順序採用，
  並逐條登記於 `SYMBOL-COLLISION-AUDIT-v025-20260909.md`；密封宣告一律不修改。
- **本表不推論結果：** V0.25 的 gate outcome 尚未開啟。第 10.14 節只固定記法，
  不宣稱任何 C1／C2／C3 的效能、可學習性或 EE 結論。

新增內容集中於三處：第 9.1 節（V0.25 的狀態變更）、第 10.11 節（新增消歧列）、
第 10.14 節（V0.25 繼任者方法與物理擴充符號）。

## 1. 使用規則

本表與
[`2026-08-17-simplified-ee-presentation-spec.md`](2026-08-17-simplified-ee-presentation-spec.md)
共同構成目前正式公式契約。若兩份文件不一致，以展示公式規格的物理定義為準，並立即同步本表；不得長期保留兩套記法。

核心規則如下：

1. CH4 與 CH5 只有 \(\gamma_{u,s,v}\) 一個實際鏈路 SINR。
2. 可合理表達 user、satellite、beam ownership 的鏈路量使用 \(u,s,v\) 三下標。
3. 系統聚合量不強加三下標。
4. 函數參數順序為「時間、角度、固定波束寬」，並使用普通小括號。
5. 不使用 hat、巢狀 serving 下標或多字母 `req`／`pre`／`contrib` 標籤。集合一律使用花體（𝒰、𝒮、𝒱、𝒞、ℱ），不用正體大寫充當集合本身（見 2026-08-20 修訂）。
6. 概念公式不放工程功率 cap 或 `min`／`max` projection；每個新 served segment 的唯一起始條件是 \(p^{0}=p^{+}/2=0.825\,\mathrm{W}\)。
7. 符號在第一次出現時定義；同一章後續不重複逐字解釋。
8. 本表只約束 CH4／CH5 的共用物理與 EE 公式符號，不縮減完整章節內容；CH4 的 current method 使用第 10.13 節 C1／C2／C3 route symbols 與 Main-only one-pass composition，第三章的 P1／P2／P3 僅作 baseline formulation。
9. Multi-Catfish MCRL V0.23 的方法章與 Word 紙面使用第 10.13 節的 active 擴充符號；第 10.8--10.9 節與第 10.12 節的舊雙代理、舊 reward、target-network 與 V0.3 bookkeeping 僅供 historical／retired provenance，不得混入 V0.23 active method。

## 2. 核心最小符號集合

```text
U, S, V, u, s, v, t, tau_(u,s,v),
x_(u,s,v), d_(u,s,v), theta_(u,s,v), boldtheta,
mathbf(v)_(u,s,v), mathbf(r)_(u,s,v),
G^T, H_(u,s,v),
G_0, F, theta_3, mu, J_1, J_3,
G^R_(u,s,v), L_(u,s,v), L_f, L_g, L_c, L_s,
p_(u,s,v), I_(u,s,v), sigma^2, gamma_(u,s,v),
B^w, U_(s,v), R_(u,s,v),
xi_(s,v), P^p_(s,v), P^f, P^N, eta_(u,s,v)
```

上列已足以表達

```text
position -> angle -> gain -> power -> SINR -> throughput -> EE
```

距離／通道細節以 H 與 G^T 的一層展開對應；更深的干擾來源拆分、PA 曲線、RF-chain/baseband 分項、功率限制與跨時間正式評估均不屬於概念主鏈。

### 2.1 單位契約

| 量 | 單位／表示 |
|---|---|
| \(d\) | m |
| \(\theta\) | rad；UI 可另轉成 degree 顯示 |
| \(G^T,H,\xi,x\) | 線性無因次值；公式中不得直接代入 dB |
| \(p,I,\sigma^2,P^p,P^f,P^N\) | W |
| \(B^w\) | Hz |
| \(U_{s,v}\) | 無因次使用者計數，實際服務鏈路必須大於 0 |
| \(R\) | bit/s |
| \(\eta\) | bit/J |

## 3. 索引、集合與時間

| 符號 | 定義 | 下標裁決 |
|---|---|---|
| \(\mathcal{U}\) | 使用者索引集合 | 集合不加實體下標；花體 |
| \(\mathcal{S}\) | 衛星索引集合 | 集合不加實體下標；花體 |
| \(\mathcal{V}\) | 實體波束索引集合 | 集合不加實體下標；花體 |
| \(u\) | 使用者索引 | 結構索引 |
| \(s\) | 衛星索引 | 結構索引 |
| \(v\) | 實體波束索引 | 結構索引 |
| \(t\) | 目前離散時間步 | 函數參數，不算實體下標 |
| \(\tau_{u,s,v}\) | 目前 uninterrupted served physical link \((u,s,v)\) segment 的起始時間步 | 每次 episode reset、handover、outage、unserved 或 re-entry 重新定義；不是 per-link cache key |
| \(x_{u,s,v}(t)\) | 時間 \(t\) 是否選定鏈路 \((u,s,v)\) | 合理使用三下標；固定服務鏈路展示時預設為 1 並可省略 |

集合大小使用與集合同一字母的正體大寫：\(U\)、\(S\)、\(V\)（例：\(\mathcal{U}=\{1,\ldots,U\}\)）；不使用 \(N_U\) 這類前綴記法，也不使用 \(|U|\) 記法（2026-08-20 修訂）。

## 4. 幾何、角度與通道

| 符號 | 定義 | 建議呈現 |
|---|---|---|
| \(d_{u,s,v}(t)\) | 使用者 \(u\)、衛星 \(s\)、候選波束 \(v\) 的鏈路斜距；同一衛星不同波束可有相同數值 | 三下標保留鏈路資料所有權，不表示距離新增波束依賴 |
| \(\theta_{u,s,v}(t)\) | 使用者方向相對服務波束中心方向的離軸角 | 單一鏈路的直接角度入口 |
| \(\mathbf{v}_{u,s,v}(t)\)、\(\mathbf{r}_{u,s,v}(t)\) | 候選鏈路 \((u,s,v)\) 的波束中心方向向量，以及由衛星指向使用者的方向向量 | 兩向量都保留鏈路三下標；arccos 向量夾角形式由 \([19,\text{ Eq. }(5)]\) 支撐，來源座標語意不直接等同本文定義 |
| \(\theta_{u,s,v}(\tau_{u,s,v})\) | 目前 served segment 起始步的角度 | 只作 segment-start identity 的角度，不跨 continuity break 保留 |
| \(\boldsymbol{\theta}(t)\) | 時間 \(t\) 的全系統鏈路角度狀態 | 只有干擾或系統功率需要其他鏈路角度時使用 |
| \(G^T(\theta,\theta_3)\)、\(G_0\) | 發射端角度增益函數與波束中心增益；\(G^T(\theta,\theta_3)=G_0F(\theta,\theta_3)\)，且 \(G^T(0,\theta_3)=G_0\) | \(T\) 表示 transmit；逗號分隔可變角度與固定波束寬參數 \(\theta_3\) |
| \(F(\theta,\theta_3)\)、\(\theta_3\) | 發射角度型樣（唯一一個），逐字採用 HOBS 式 (3) 的 \(J_1/J_3\) 型樣，在 \(\theta=0\) 自然等於 1；以及 3 dB 波束寬度 | 式 (3.7) |
| \(\mu(\theta,\theta_3)\)、\(J_1\)、\(J_3\) | Bessel 型樣的角度參數與固定 Bessel 項；角度參數固定為 \(2.07123\)（HOBS 式 (3)），不是額外 runtime 控制 | 式 (3.8) |
| \(H_{u,s,v}(t)\) | 不直接承載 wanted-link 角度型樣的線性鏈路功率因子：由 \(L_{u,s,v}(t)\) 與 \(G^R_{u,s,v}(t)\) 一層展開；在 SINR numerator 中直接與 \(G^T(\theta_{u,s,v},\theta_3)\) 相乘 | 式 (3.10) |
| \(L_{u,s,v}(t)\) | 路徑／衰落損耗層：\(L_f(d_{u,s,v}(t),f_c)+L_g(\alpha_{u,s}(t))+L_c(\alpha_{u,s}(t))+L_s\!\left(\alpha_{u,s}(t)\right)\)，即 HOBS 式 (1) 的四項 | 式 (3.10b) |
| \(G^R_{u,s,v}(t)\) | 接收端線性增益；是 H 一層展開中的明示因子。以軸心增益扣除離軸損耗表示，截止於 \([G^{R}_{-},G^{R}_{+}]\) | 式 (3.10)、式 (3.10c) |
| \(\theta^{R}_{u,s}(t)\) | 使用者接收天線指向與第 \(s\) 顆衛星方向之間的夾角（度）；與發射端偏軸角 \(\theta_{u,s,v}\) 分屬鏈路兩端，沿用 \(G^T\)／\(G^R\) 的 T／R 上標慣例；不帶波束下標 \(v\)（假設接收指向固定對準服務衛星） | 式 (3.10c) |
| \(A_R\)、\(B_R\)、\(G^{R}_{+}\)、\(G^{R}_{-}\) | 式 (3.10c) 的地球站參考型樣參數與上下限。\(A_R\)、\(B_R\)、\(G^{R}_{-}\) 同出 ITU-R S.465-6 `recommends 2` 的**同一條式子**，在 \(48^{\circ}\) 連續銜接（\(32-25\log_{10}48=-10.03\)），非三個獨立設定；\(G^{R}_{+}=35\) dBi 取自同級 0.6 m 使用者終端的降額值 | 式 (3.10c)、表 5-2 |

論文正文、概念簡報與 `/` legacy simulator 前端都展開到上述同一層，以便每個可調參數都能對應到 H 或 G^T；三者只允許排版不同，不允許公式、符號或可調參數不同。更深的自由空間模型、Bessel 近似誤差、接收天線量測與 Rician 校準細節不屬於這個公開主公式層級，不能讓它們重新擴張主公式。

> **✅ 深度上限已裁決（2026-08-21，作者選 (a)）。** 式 (3.10c) 的接收型樣**保留於公開層**。
>
> 理由：本節下一段的上限，其原意是防止主公式往下長進**沒有公開標準、沒有固定參數的實作細節**
> （自由空間模型細節、Bessel 近似誤差、接收天線量測、Rician 校準）。式 (3.10c) 不屬該類——
> 它是**標準文件明載的式子加三個固定常數**，與 \(G^T\) 收下 HOBS 式 (3) 同級。
> 上限的措辭因此擴充，以符合其自身用意。
>
> 被否決的 (b)：刪除式 (3.10c) **並**把 \(A_R\)、\(B_R\)、\(G^{R}_{+}\)、\(G^{R}_{-}\) 移出表 5-2。
> 否決理由：那四個參數已在表 5-2，(b) 是倒退，且會回到「有參數、無公式」
> ——正是 C8 一開始被誤判為「無出處」的成因。

公開展開的深度上限＝原始論文正文實際展示的深度，**或標準文件明載的單層型樣**（2026-08-21 擴充）：HOBS 式 (1) 的四項損耗與式 (3) 的單一 \(J_1/J_3\) 型樣。掃描損耗 \(L_{st}\)、NLoS clutter \(L_N\) 與型樣選擇器 \(m\) 在兩篇來源論文都不存在，因此不是公開符號、不是公開可調參數；模擬器仍可在實作層計算它們並併入 \(H\)。

一層展開的正式對照如下；其中 dB 損耗在代入 H 前轉成線性尺度，掃描角度的 bounded ratio 只屬於掃描損耗模型，不是功率 cap：

\[
H_{u,s,v}(t)
=10^{-\frac{L_{u,s,v}(t)}{10}}
G^R_{u,s,v}(t),
\qquad
L_{u,s,v}(t)
=L_f\!\left(d_{u,s,v}(t),f_c\right)
+L_g\!\left(\alpha_{u,s}(t)\right)
+L_c\!\left(\alpha_{u,s}(t)\right)
+L_s\!\left(\alpha_{u,s}(t)\right),
\]

\[
G^T(\theta,\theta_3)=G_0F(\theta,\theta_3),
\qquad
G^T(0,\theta_3)=G_0,
\qquad
F(0,\theta_3)=1.
\]

發射型樣的角度參數與 pattern 為

\[
\mu\!\left(\theta,\theta_3\right)=2.07123\frac{\sin\theta}{\sin\left(\theta_3/2\right)},
\qquad
F\!\left(\theta,\theta_3\right)=
\left[
\frac{J_1\!\left(\mu\!\left(\theta,\theta_3\right)\right)}{2\mu\!\left(\theta,\theta_3\right)}
+\frac{36J_3\!\left(\mu\!\left(\theta,\theta_3\right)\right)}{\left[\mu\!\left(\theta,\theta_3\right)\right]^{3}}
\right]^2.
\]

\(2.07123\) 是 HOBS 式 (3) 的固定角度參數；\(F\) 在 \(\theta=0\) 自然等於 1，不需要額外正規化常數。\(G_0\) 與 \(\theta_3\) 是天線／情境參數。這些展開不改變主式的 \(pHG^T\) 結構，也不產生小寫 \(h\)。

## 5. 角度感知發射功率

| 符號 | 定義 | 備註 |
|---|---|---|
| \(p_{u,s,v}(\tau_{u,s,v},\theta_{u,s,v}(\tau_{u,s,v}),\theta_3)=p^{0}\) | served segment 起始步的 RF 發射功率 | 正文只用符號 \(p^{0}\)；**數值僅出現在第 5.1 節**(0.825 W = \(p^{+}/2\),2026-08-22 由 2 W 修正,見下)。每個新 segment 重新起始，不保留 inactive-link cache |
| \(p^{0}\) | 段起始發射功率(scenario 常數) | 單字母上標 `0` 表 segment 起始，**不是指數**。與 legacy 的 \(P_0\)(大寫、下標、PA 飽和輸出)不同,見第 11 節 |
| \(p_{u,s,v}(t,\theta_{u,s,v}(t),\theta_3)\) | 由前一步同一 physical link 的 RF power 與角度增益比遞推的實際鏈路功率 | 只有 \(x_{u,s,v}(t-1)=x_{u,s,v}(t)=1\) 時適用 |

正式功率律為

\[
p_{u,s,v}\!\left(t,\theta_{u,s,v}(t),\theta_3\right)
=p_{u,s,v}\!\left(t-1,\theta_{u,s,v}(t-1),\theta_3\right)
\frac{G^T\!\left(\theta_{u,s,v}(t-1),\theta_3\right)}
     {G^T\!\left(\theta_{u,s,v}(t),\theta_3\right)},
\qquad
x_{u,s,v}(t-1)=x_{u,s,v}(t)=1,
\quad G^T\!\left(\theta_{u,s,v}(t),\theta_3\right)>0.
\]

每個 segment 先滿足
\[
p_{u,s,v}\!\left(\tau_{u,s,v},\theta_{u,s,v}(\tau_{u,s,v}),\theta_3\right)=p^{0}.
\]

在沒有 continuity break 的前提下，重複代入才得到
\[
p_{u,s,v}\!\left(t,\theta_{u,s,v}(t),\theta_3\right)
=p^{0}\,
\frac{G^T\!\left(\theta_{u,s,v}(\tau_{u,s,v}),\theta_3\right)}
     {G^T\!\left(\theta_{u,s,v}(t),\theta_3\right)}.
\]
這個 fixed-reference 形式只是 segment 內的 telescoped identity，不是 runtime state，也不跨 handover、outage、unserved、re-entry 或 episode reset。這裡沒有目標 SINR、最低速率、lagged interference 或需求功率反推；也沒有 cap、clip 或 projection。若 \(H\) 與干擾固定，本地角度變化本身不保證 SINR／throughput 改變；角度仍透過 \(p\)、\(P^p\) 與 \(P^N\) 進入 EE 分母。

## 6. 唯一 SINR 與 Throughput

| 符號 | 定義 | 下標／角色 |
|---|---|---|
| \(I_{u,s,v}(t,\theta_{u,s,v},\theta_3)\) | 鏈路 \((u,s,v)\) 接收到的總同頻干擾功率 | 三下標；主式不拆 intra/inter 別名 |
| \(\sigma^2\) | 接收端雜訊功率 | 系統／接收端標量，不強加三下標 |
| \(\gamma_{u,s,v}(t,\theta_{u,s,v},\theta_3)\) | 鏈路 \((u,s,v)\) 的唯一實際 SINR | CH4 與 CH5 共用同一符號、同一公式 |
| \(B^w\) | 單一波束可用頻寬 | \(w\) 是 bandwidth 類別的單字母標籤 |
| \(U_{s,v}(t)\) | 波束 \((s,v)\) 目前服務的使用者數 | user 已被計數聚合，只保留 \(s,v\) |
| \(R_{u,s,v}(t,\theta_{u,s,v},\theta_3)\) | 鏈路 \((u,s,v)\) 的實際 throughput | 三下標；單一使用者展示時分子不再加總 |

唯一 SINR 為

\[
\gamma_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_3\right)
=
\frac{
p_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_3\right)
H_{u,s,v}(t)
G^T\!\left(\theta_{u,s,v},\theta_3\right)
}{
I_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_3\right)+\sigma^2
}.
\]

有效服務鏈路必須滿足
\(I_{u,s,v}(t,\theta_{u,s,v},\theta_3)+\sigma^2>0\)。

Throughput 為

\[
R_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_3\right)
=
\frac{B^w}{U_{s,v}(t)}
\log_2\!\left(1+\gamma_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_3\right)\right).
\]

實際服務鏈路要求 \(U_{s,v}(t)>0\)。單一使用者場景只令 \(U_{s,v}=1\)；公式本身不改，也不另建立單人版 SINR。

## 7. Power 與 EE 分母

| 符號 | 定義 | 下標／角色 |
|---|---|---|
| \(\xi_{s,v}(t,\boldsymbol{\theta},\theta_3)\) | 波束 RF 發射功率到電源端消耗的有效轉換效率 | **兩下標**：一支波束一個放大器；全系統角度狀態與波束寬是函數參數，不是額外 owner |
| \(P^p_{s,v}(t,\boldsymbol{\theta},\theta_3)\) | 波束 \((s,v)\) 的電源端功率 | \(p\) 是 power-consumption 階段的單字母上標；同樣為兩下標 |
| \(P^f(t)\) | 系統固定／circuit overhead 的聚合量 | 系統量，不加 \(u,s,v\)；概念簡報不展開硬體元件 |
| \(P^N(t,\boldsymbol{\theta},\theta_3)\) | 當步系統總功率 | \(N\) 表示 network total；不能改成 \(P^N_{u,s,v}\)；帶 \(\theta_3\) 因發射功率依賴波束寬 |
| \(\eta_{u,s,v}(t,\theta_{u,s,v},\theta_3)\) | 單一 UE-link 的 EE 顯示量：該鏈路 throughput 除以共同系統功率 | 三下標固定 numerator link，不代表 private per-user power |

功率關係為

\[
P^p_{s,v}\!\left(t,\boldsymbol{\theta},\theta_3\right)
=
\frac{p_{s,v}\!\left(t,\boldsymbol{\theta},\theta_3\right)}
{\xi_{s,v}\!\left(t,\boldsymbol{\theta},\theta_3\right)},
\qquad \xi_{s,v}\!\left(t,\boldsymbol{\theta},\theta_3\right)>0,
\]

\[
P^N\!\left(t,\boldsymbol{\theta},\theta_3\right)
=P^f(t)+
\sum_{s'\in \mathcal{S}}\sum_{v'\in \mathcal{V}}
z_{s',v'}(t)
P^p_{s',v'}\!\left(t,\boldsymbol{\theta},\theta_3\right).
\]

EE 為

\[
\eta_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_3\right)
=
\frac{R_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_3\right)}
{P^N\!\left(t,\boldsymbol{\theta},\theta_3\right)},
\qquad P^N>0.
\]

固定／circuit overhead 雖不直接受角度控制，仍可用單一 \(P^f\) 保留在分母；其 exact mapping 由 \(P^f(t)=\sum_s\left(N^{a}_sP^{c}+\mathbb{1}\{N^{a}_s>0\}P^{b}\right)\) 定義，\(P^{c}=0.338\,\mathrm{W}\)、\(P^{b}=0.200\,\mathrm{W}\)；數值隨 active beams 狀態改變，不是 calibration pending。簡報不需要進一步解釋 RF-chain、baseband、event energy 或 PA 曲線。

\(\eta_{u,s,v}(t,\theta_{u,s,v},\theta_3)\) 是概念簡報／模擬器的 selected-link 顯示量，不取代論文正式結果的系統級 EE。論文 headline 與方法比較仍使用全體使用者總 throughput 對系統總能耗的 ratio-of-sums；跨時間評估符號與區間留待 experiment／evaluation contract 凍結，不在本表重新引入另一個 active EE 別名。

## 8. 角度依賴的呈現層級

| 量 | 正式呈現 | 角度語意 |
|---|---|---|
| 單一鏈路角度 | \(\theta_{u,s,v}(t)\) | 幾何直接輸出 |
| wanted-link 增益因子 | \(H_{u,s,v}(t)G^T(\theta_{u,s,v},\theta_3)\) | \(H\) 承載非角度鏈路狀態；\(G^T\) 直接承載服務角度 |
| RF 發射功率 | \(p_{u,s,v}(t,\theta_{u,s,v}(t),\theta_3)\) | 新 segment 由 \(p^{0}=p^{+}/2=0.825\) W 起始（2026-08-22 F-1）；同一 physical link 連續服務時由前一步功率與增益比遞推 |
| SINR／Throughput | \(\gamma_{u,s,v}(t,\theta_{u,s,v},\theta_3)\)、\(R_{u,s,v}(t,\theta_{u,s,v},\theta_3)\) | \(p\) 與 \(G^T\) 使用本地角度；同一 segment 內的乘積延續前一步，其他變化可來自 \(H\)、全系統干擾與負載 |
| 波束耗電 | \(P^p_{s,v}(t,\boldsymbol{\theta},\theta_3)\) | 由該波束的 \(p_{s,v}(t,\boldsymbol{\theta},\theta_3)=\max_u p_{u,s,v}(t,\theta_{u,s,v},\theta_3)\) 與 \(\xi_{s,v}(t,\boldsymbol{\theta},\theta_3)\) 決定；仍只有兩個 owner 下標 |
| 系統總功率 | \(P^N(t,\boldsymbol{\theta},\theta_3)\) | 聚合所有 active link power 與固定 overhead |
| 單一 UE-link EE | \(\eta_{u,s,v}(t,\theta_{u,s,v},\theta_3)\) | 分子固定該 link，分母保留共同 system power |

不再使用整段角度軌跡 \(\boldsymbol{\Theta}\) 或 \(\Delta t\) 展開概念簡報。跨時間 ratio-of-sums 屬於正式實驗評估契約，待論文與 simulator 同步時另行定義。

## 9. 已退出 active symbol surface 的舊符號

| 舊符號／結構 | 新處理 |
|---|---|
| \(R^m\)、\(R_{\min}\) 作為功率上游 | 不再用來產生發射功率；QoS 可作獨立評估指標 |
| \(\gamma^r\)、\(\gamma^{\mathrm{req}}\) | 刪除；沒有目標 SINR |
| \(\gamma^e\)、\(\widehat\gamma\) | 刪除；CH4／CH5 共用 \(\gamma_{u,s,v}\) |
| \(p^r\)、\(P^r\) | 刪除；以實際角度相關 \(p_{u,s,v}\) 取代 |
| \(P^o\)、satellite scaling | 不屬於概念主鏈；未來若實作需要，留在 simulator engineering contract |
| \(P_{\mathrm{beam},\max}\)（舊名）、\(P_{\mathrm{sat},\max}\) | \(p^{+}=1.65\,\mathrm{W}\) 是 active 每波束 RF 輸出上限，亦是鏈路可行性檢查門檻；它不進入 recurrence。\(P_{\mathrm{sat},\max}\) 僅保留為 legacy 每星總上限，不屬 active 契約。 |
| PA back-off、\(P_0\)、效率 clamp | 不展開；概念層以正的有效效率 \(\xi\) 表示 |
| \(I^a\)、\(I^b\) | 主公式合併為總干擾 \(I\)；需要教學時可用文字解釋來源 |
| \(\gamma_u\) | 概念鏈不另造 user-level SINR；已選定鏈路直接使用 \(\gamma_{u,s,v}\) |
| \(h_{u,s,v}\) | 刪除；不再建立只靠大小寫區分的中間量，直接使用 \(H_{u,s,v}(t)G^T(\theta_{u,s,v},\theta_3)\) |
| \(L_{st}\)、\(L_{st,max}\)、\(\phi\)、\(\phi_{max}\) | 退出公開表面（2026-08-21）；兩篇來源論文都沒有掃描損耗模型，效果併入 \(H\) 的實作層，不是公開符號或公開可調參數 |
| \(L_N\) | 退出公開表面（2026-08-21）；TR 38.811 NLoS clutter 屬實作層敏感度參數，併入 \(H\)，不進入 \(L_{u,s,v}\) 的公開展開 |
| \(F_m\)、\(\mu_m\)、\(\kappa_m\)、\(F_{J_1}\)、\(F_{flat}\)、型樣索引 \(m\) | 退出公開表面（2026-08-21）；只保留 HOBS 式 (3) 的單一型樣 \(F\) 與 \(\mu\)，替代型樣是實作層敏感度選項 |
| \(\kappa\)、\(1.75\) | 退出公開表面（2026-08-21）；抄寫錯誤（\(J_1(\mu)/(2\mu)\) 誤寫為 \(2J_1(\mu)/\mu\)）加上的補丁常數與反解角度參數 \(1.8352\)，runtime 與文件均已改回 HOBS 式 (3) 的 \(2.07123\) |
| MODQN 的 \(G_{i,l,v}\) | 不與 HOBS 的 \(G^T\)／\(G^R\) 合併；它是**通道增益**，角色對應本表的 \(H_{u,s,v}\)，語意不同不可同名共用 |
| \(\eta^e_{u,s,v}(\boldsymbol{\Theta})\) | 移出概念簡報；目前只保留當步 \(\eta_{u,s,v}(t,\theta_{u,s,v},\theta_3)\) |
| 執行遮罩 \(m^e\) | **刪除**（2026-08-22 使用者裁決）：不再保留環境端帳務或三閘連線式；式 (4.5a) 使用兩閘 \(x=a\cdot z\)，「選了不一定連得上」由逐波束功率可行性（\(p_{\mathrm{req}}>p^{+}\) 判 infeasible）承擔。\(m^e\) 不屬 active symbol surface。 |
| \(v_{\max}\)（又名 `k_cap`） | **刪除**（2026-08-21，SDD-01 §2.2）。⚠ 2026-08-22 更正:當時記「改由原論文 Table I 的 \(V=7\) 表示」是**錯的** —— \(V=7\) 是原論文波束集合的大小 \(|\mathcal{V}|\)，其 7 道恆常全亮，原論文**沒有任何計數式上限**。本論文亦不設上限；波束啟用由 \(z_{s,v}=\mathbb{1}\{U_{s,v}>0\}\)（式 3.4）導出 |
| \(\mathcal{F}\)、\(F\)（射頻槽索引域與槽數） | **刪除**（2026-08-21，SDD-01 §2.2，隨 \(v_{\max}\) 與舊 \(r_3\) 一併消失）；\(F=L_w v_{\max}\) 依賴已刪除的 \(v_{\max}\)；負載平衡改以計數式 \(r_{3,u}=-U_{b_u}\) 表示，無需射頻槽域 |
| \(\widetilde{R}_{s,v}\)、\(T_k\)（依賴射頻槽的 beam throughput aggregate） | **移除**（2026-08-21，SDD-01 B13 舊 \(r_3\) 依賴項）；新 \(r_{3,u}=-U_{b_u}\) 是計數式，不需要 beam aggregate throughput 排序；\(\widetilde{R}\) 帶波浪標記的形式一併消失 |
| 舊 \(r_3\)（max−min gap 型，依賴 \(\widetilde{R}\) 與 \(\mathcal{F}\)） | **汰換**（2026-08-21，SDD-01 B13）；改為 \(r_{3,u}=-U_{b_u}\)（計數式，逐使用者獨立，不依賴射頻槽排序） |
| \(N(t)\)（定義為「填入 \(\mathcal{F}\) 個射頻槽的啟用波束數量」） | **汰換**（2026-08-21）；定義 \(0\le N(t)\le F\) 靠已刪除的 \(\mathcal{F}\) 撐住；若後續需要啟用波束計數，以 \(\sum_{s,v} z_{s,v}(t)\) 或不依賴 \(\mathcal{F}\) 的新定義重新引入 |
| \(\chi\)、z-score 壅塞情境（B8） | **⚠ 保留為可選機制，預設關閉**（2026-08-21，SDD-01 §2.1 B8）；程式保留但不接上 live 訓練路徑；此條目**不刪除**，符號狀態標記為「可選，預設關閉」 |

## 9.1 V0.25 繼任者的狀態變更（不覆寫上表的權威定義）

下列符號在 V0.23 表中仍是 active 定義，**本合併層不改寫其原列**；它們只是在 V0.25
繼任者（memoryless 角度感知速率目標功率控制）之下不再進入主鏈。此類狀態變更由權威
順序 ③（`SYMBOL-ADDITIONS.md` §3 第 9 點）與 ④（優先序宣告 v1.0「no segment memory」、
v1.8 §3–§4）宣告，與權威順序 ① 的既有列存在張力，已逐條登記於本輪碰撞稽核。

| 符號 | V0.23 狀態 | V0.25 繼任者狀態 | 依據 |
|---|---|---|---|
| 【改】\(\tau_{u,s,v}\)、\(p^{0}\) | active：段起始時間步與段起始發射功率 | 退出 active surface。繼任者每一步由角度、占用與所需 SINR 直接解出名目功率，沒有 segment memory，也沒有 previous-step 遞推 | 優先序宣告 v1.0、v1.1 §1；SYMBOL-ADDITIONS §3.9 |
| 【改】\(\eta_{u,s,v}(t,\theta_{u,s,v},\theta_3)\) | active：單一 UE-link EE 顯示量 | 退出 active surface。所有 EE 宣稱一律以實現 pooled \(\Sigma B/\Sigma E\)（\(\eta^{N}\)）陳述，並附能量邊界句 | v1.8 §3–§4；SYMBOL-ADDITIONS §3.9 |
| 【改】\(r_{1,u},r_{2,u},r_{3,u},\overrightarrow R_u\) | active：三目標獎勵向量 | 退出。繼任者以組態層剩餘 \(\Omega(a)\) 與 C1／C2／C3 分解取代加權三目標；\(\Phi\) 承接換手／QoS 偏好 | SYMBOL-ADDITIONS R-2、§3.9；契約 v1 §B4 |
| 【改】\(\Omega=[\omega_1,\omega_2,\omega_3]\) | 舊三目標線性純量化權重（§10.8，V0.3 已汰換） | 字母釋出，\(\Omega\) 改指組態層剩餘 \(\Omega(a)\)；\(\omega_j\) 不得再出現 | SYMBOL-ADDITIONS R-2 |
| 【改】\(\Psi_u(t)\)（式 3.27 換手成本） | active | 改名 \(\Phi_u(t)\)；\(\Psi\) 自 V0.25 起專用於交互作用殘差 | SYMBOL-ADDITIONS R-1 |
| 【改】\(\ell_i,e_i,\Psi_B,\Psi_E,z_{3,i},y_i,x^{0},x^{1},x^{2},x^{c},c_{ia},t_{iar},m_{iar},F_i(a),Q_{3,i}(a),a^{0}_i\) | §10.13 LC-SRS active | 隨 two-user LC-SRS 一併退出 active surface；整網 C1 已含單邊外部性，繼任者的 C3 標的不含 \(e_i\) 項 | SYMBOL-ADDITIONS A-3、§3.9；stage-2 決策 5 |
| 【改】\(d_i\) | LC-SRS partial surplus \(\ell_i+e_i\) | **字形保留、語意再定義**為整網剩餘上的單邊增量（見 §10.14.3）；不再等於 \(\ell_i+e_i\) | SYMBOL-ADDITIONS A-3；v1.5 §2 |
| 【改】\(\xi^{+}\) | 「最大轉換效率」 | 語意更名為**飽和效率**（\(=0.35\)）：\(P^{p}=\sqrt{p\,p^{s}}/\xi^{+}\) 在 1.65 W 的實際 RF→DC 效率約 19.7 %、在 0.32 W 約 8.6 %。正文與宣告一律寫「飽和效率」，**不得**寫成「35 % 效率」 | v1.8 §1 |
| 【改】\(\eta_w,(c_1,c_2,c_3),\beta_M,\beta_F,\rho_I,q_1,q_2,W\) | §10.8／§10.9 舊版（已標 retired） | 確認不進入 V0.25；其中 \(W\) 尤其不得被密封宣告的「頻寬 \(W\)」讀法取代（本表頻寬為 \(B^{w}\)） | SYMBOL-ADDITIONS §3.9 |

上述任一列都不是效能結論，也不刪除第 1–8 節與第 10 節的既有定義；V0.23 論文版本
仍以原列為準。

## 10. CH4／CH5 採用表

| 章節 | 新增／定義 | 只能引用 |
|---|---|---|
| CH4 | 公式層定義 \(d\)、\(\theta\)、\(G^T\)、\(H\)、唯一 \(\gamma\)、\(R\)；其後以現行論文符號說明 P1／P2／P3 與 baseline MODQN | \(p_{u,s,v}\) 只解釋為實際 RF 發射功率，不說明控制律 |
| CH5 | 完整定義 segment-start 0.825 W、previous-step 角度感知 \(p\)、\(P^p\)、\(P^f\)、\(P^N\)、\(\eta_{u,s,v}\) | 直接重用 CH4 的 \(\gamma\) 與 \(R\)，不得重新定義；不得跨事件保留 power |

此採用表是公式與符號責任表，不是投影片頁數表。CH4／CH5 都不得再建立獨立的 \(h=HG^T\) 定義頁；需要說明 wanted-link numerator 時，直接使用 \(p_{u,s,v}H_{u,s,v}G^T(\theta_{u,s,v},\theta_3)\)。

## 11. 文件與實作邊界

- 本表是 active symbol authority。
- [`ADR-003-canonical-ee-closure.md`](../../ADR-003-canonical-ee-closure.md) 是 archived historical contract。
- Phase-C 英文 CH4／CH5 簡報已依本表重新製作並通過成品稽核，可宣稱 deck formula／symbol parity。
- `thesis-mc/notation-table.md`、論文正文、三份 DOCX 與 production Family-B runtime／consumer 已依本表完成公式／符號及 executable parity；這不等於 calibration、學習或實驗結果通過。
- 模擬器未來可以採用更可讀的程式欄位名稱，但必須建立到本表符號的一對一語義對照。
- 除了 active recurrence 明定的 0.825 W segment-start condition 外，固定數值應位於 scenario／experiment config；Family-B 的 \(\xi\) 與 \(P^f\) exact mapping 由 ADR-006 固定，reward-scale calibration 不重新決定物理常數。

## 12. 參照

- [正式單一 SINR EE 公式規格](2026-08-17-simplified-ee-presentation-spec.md)
- [三下標裁決稽核](2026-08-17-subscript-arity-audit-modqn.md)
- [Archived ADR-003](../../ADR-003-canonical-ee-closure.md)
- [ADR-005 previous-step power recurrence](../../ADR-005-previous-step-power-recurrence.md)
- [現行論文入口（正文與三份 DOCX 已同步）](../../../thesis-mc/README.md)
- [Active single-SINR runtime](../../../src/modqn_paper_reproduction/runtime/single_sinr_ee.py)
- [Family-B scenario mapping](../../ADR-006-family-b-single-sinr-scenario-mapping.md)
- [Production-path full-phase runtime gate](2026-08-19-single-sinr-full-phase-runtime-gate.md)
- [Archived legacy runtime](../../../src/modqn_paper_reproduction/runtime/angle_aware_ee.py)

---

# 10. 論文全篇符號(2026-08-22 由 `thesis-mc/notation-table.md` 併入)

> 本節收錄第三、四章正文使用的完整符號集,原本存放於 `thesis-mc/notation-table.md`。
> 該檔已改為指標存根,**不再獨立維護**,以消除兩份符號表並存造成的分歧風險。
> 下方小節編號沿用原檔,與本檔第 1–9 節的 EE 鏈路符號互補而不重疊。

## 10.0 記號原則

| 類別 | 記號方式 | 說明 |
|---|---|---|
| 集合與索引域 | 花體大寫字母 | $\mathcal{U},\mathcal{S},\mathcal{V},\mathcal{C}$ 分別表示使用者、衛星、波束與候選動作的索引域。 |
| 元素數 | 與集合同字母的正體大寫 | $U,S,V,C$ 表示對應集合的元素數。 |
| 索引 | 一般小寫字母 | $u,s,v,c,t$ 分別表示使用者、衛星、波束、候選與時間步。 |
| 鏈路量 | 三下標 $u,s,v$ | 真正屬於一條 user--satellite--beam link 的量使用三下標。 |
| Beam aggregate | 兩下標 $s,v$ | user 已被聚合後才保留 beam owner，例如 $U_{s,v}$。 |
| System quantity／constant | 無實體下標 | $G^T$、$\sigma^2$、$B^w$、$P^f$、$P^N$ 不補不存在的 $u,s,v$。 |
| 上標 | 必要的單字母角色 | 例如 $G^T$、$B^w$、$P^p$、$P^N$；不使用長 `req`、`contrib` 或 provenance 上標。 |

## 10.1 集合、索引與負載

| 符號 | 定義 | 首次位置 |
|---|---|---|
| $\mathcal{U},\mathcal{S},\mathcal{V}$ | 使用者、衛星與每顆衛星共用的波束索引集合：$\mathcal{U}=\{1,\ldots,U\}$、$\mathcal{S}=\{1,\ldots,S\}$、$\mathcal{V}=\{1,\ldots,V\}$。 | 第 3.1.1 節 |
| $U,S,V$ | 使用者數、衛星數與每顆衛星的波束索引數。 | 第 3.1.1 節 |
| $u,s,v,t$ | 使用者、衛星、波束與時間步索引。 | 第 3.1.1 節 |
| $x_{u,s,v}(t)$ | 使用者 $u$ 在時間 $t$ 是否連接衛星 $s$ 的波束 $v$；為二元值，且每位使用者至多連接一個波束。 | 式 (3.1) |
| $z_{s,v}(t)$ | 波束 $(s,v)$ 是否啟用的二元指示量；由連線結果導出，$z_{s,v}(t)=1$ 當且僅當 $U_{s,v}(t)>0$。**不受任何每衛星計數上限限制。** | 式 (3.2)、式 (3.4) |
| $U_{s,v}(t)$ | 波束 $(s,v)$ 在決策完成後實際服務的使用者數：$\sum_{u\in \mathcal{U}}x_{u,s,v}(t)$。 | 式 (3.3) |
| $L_w,J_w$ | 每位使用者候選表保留的可見衛星數，以及每顆視窗衛星保留的候選波束數。 | 第 4.1 節 |
| $\mathcal{C}=\{1,\ldots,C\}$ | 每位使用者的候選動作索引域；其長度為 $C=L_wJ_w$。 | 第 4.1 節 |

## 10.2 幾何與通道

| 符號 | 定義 | 首次位置 |
|---|---|---|
| $d_{u,s,v}(t)$ | 使用者 $u$ 與衛星 $s$ 的候選波束 $v$ 鏈路斜距；同一顆衛星的不同波束可具有相同數值。 | 式 (3.5) |
| $\alpha_{u,s}(t)$ | 使用者相對於衛星的仰角。 | 式 (3.5) |
| $R_E,h_s$ | 地球半徑與衛星高度。 | 式 (3.5) |
| $\theta_{u,s,v}(t)$ | 使用者方向與波束中心方向之間的偏軸角。 | 式 (3.6) |
| $\tau_{u,s,v}$、$\theta_{u,s,v}(\tau_{u,s,v})$ | 目前 served physical link segment 的起始時間步與起始角度；每次 reset、handover、outage、unserved 或 re-entry 重新定義。 | 式 (3.11)–(3.12) |
| $\mathbf{v}_{u,s,v}(t),\mathbf{r}_{u,s,v}(t)$ | 候選鏈路 $(u,s,v)$ 的波束中心方向向量，以及由衛星指向使用者的方向向量；兩者的 arccos 向量夾角形式由 \([19,\text{ Eq. }(5)]\) 支撐，來源文獻的地心座標定義不直接等同本文的鏈路向量定義。 | 式 (3.6) |
| $G^T(\theta,\theta_3)$、$G_0$ | 發射端角度增益函數與波束中心增益；$G^T(\theta,\theta_3)=G_0F(\theta,\theta_3)$ 且 $G^T(0,\theta_3)=G_0$。 | 式 (3.7)–(3.9) |
| $F(\theta,\theta_3)$、$\theta_3$ | $J_1/J_3$ 角度型樣（唯一一個），逐字採用 HOBS 式 (3)，在 $\theta=0$ 自然等於 1；與 3 dB 波束寬度。 | 式 (3.8)–(3.9) |
| $\mu(\theta,\theta_3)$、$J_1$、$J_3$ | Bessel 型樣的角度參數與固定 Bessel 項；角度參數固定為 HOBS 式 (3) 的 $2.07123$，不是可調參數。 | 式 (3.9) |
| $H_{u,s,v}(t)$ | 一層展開為 $10^{-\frac{L_{u,s,v}(t)}{10}}G^R_{u,s,v}(t)$ 的線性鏈路功率因子；在 SINR numerator 中直接與 $G^T(\theta_{u,s,v},\theta_3)$ 相乘。 | 式 (3.10)、式 (3.10a) |
| $L_{u,s,v}(t)$ | $L_f(d_{u,s,v}(t),f_c)+L_g(\alpha_{u,s}(t))+L_c(\alpha_{u,s}(t))+L_s(\alpha_{u,s}(t))$ 的路徑／衰落損耗層，即 HOBS 式 (1) 的四項。後三項皆隨仰角變化(2026-08-22 為 $L_s$ 補上引數)。 | 式 (3.10b) |
| $A^{z}$ | 天頂大氣氣體吸收，$L_g(\alpha)=A^{z}/\sin\alpha$；形式取 TR 38.811 式 (6.6-8) \[17\]，值 0.25 dB 由 TR 38.821 \[22\] 的 LEO Ka 20 GHz 下行預算(0.5 dB @ 仰角 30 度)反推。**2026-08-22 取代 legacy 的 $\chi_{\mathrm{atm}}$ 式**，後者天頂只給 0.015 dB(等效大氣厚 0.3 km)。 | 第 5.1 節 |
| $L_c(\alpha)$、$L_s(\alpha)$ | 閃爍與遮蔽衰落，數值取 TR 38.811 \[17\] 表 6.6.6.2.1-1(20 GHz 對流層閃爍)與表 6.6.2-3(Ka LOS shadow fading, $\sigma$ 隨仰角)。HOBS 式 (1) 只給名稱未給值，此代換是本研究的建模選擇。$L_s$ 與 $K_R$ 是模型僅有的兩個隨機項。 | 式 (3.10b)、第 5.1 節 |
| $G^R_{u,s,v}(t)$ | H 一層展開中的接收端線性增益；以軸心增益扣除離軸損耗表示，截止於 $[G^{R}_{-},G^{R}_{+}]$。 | 式 (3.10a)、式 (3.10c) |
| $\theta^{R}_{u,s}(t)$ | 使用者接收天線指向與第 $s$ 顆衛星方向之間的夾角（度）；與發射端偏軸角 $\theta_{u,s,v}$ 分屬鏈路兩端，沿用 $G^T$／$G^R$ 的 T／R 上標慣例，不帶波束下標 $v$（假設接收指向固定對準服務衛星）。 | 式 (3.10c) |
| $A_R$、$B_R$、$G^{R}_{+}$、$G^{R}_{-}$ | 式 (3.10c) 的地球站參考型樣參數與上下限；$A_R$、$B_R$、$G^{R}_{-}$ 同出一條 ITU-R 建議式，在 $48^{\circ}$ 連續銜接。 | 式 (3.10c)、表 5-2 |

## 10.3 角度功率、耗能與 EE

| 符號 | 定義 | 首次位置 |
|---|---|---|
| $\xi_{s,v}(t,\boldsymbol{\theta},\theta_3)$ | 波束的 RF 到電源端有效轉換效率，$\xi=\min\{\xi^{+},\xi^{+}\sqrt{p_{s,v}/p^{s}}\}$；類 B 平方根近似 \[23\]。**逐波束,不帶 $u$**；角度狀態與波束寬是函數參數。 | 式 (3.15)、(3.15a) |
| $p^{s}$、$b_o$、$\xi^{+}$ | 飽和功率 $p^{s}=p^{+}10^{b_o/10}$、輸出回退、最大效率；數值見第 5.1 節。 | 式 (3.15a) |
| $P^{p}_{s,v}(t,\boldsymbol{\theta},\theta_3)$ | 波束 $(s,v)$ 的電源端功率：$P^p_{s,v}=p_{s,v}/\xi_{s,v}$。**兩下標**；函數參數完整保留。 | 式 (3.15) |
| $P^{f}(t)$ | 固定／電路功率彙總，$P^{f}=\sum_s\left(N^{a}_sP^{c}+\mathbb{1}\{N^{a}_s>0\}P^{b}\right)$；**partial payload-power model**，不含本振與相移器功率。 | 式 (3.16)、(3.16a) |
| $N^{a}_{s}(t)$、$P^{c}$、$P^{b}$ | 衛星 $s$ 的啟用波束數、每啟用波束電路功率、衛星共用基頻功率 \[26\]。 | 式 (3.16a) |
| $p_{u,s,v}(\tau_{u,s,v},\theta_{u,s,v}(\tau_{u,s,v}),\theta_3)$ | 每個 served segment 的起始 RF 發射功率，固定為 $p^0$；不跨 continuity break 保留。 | 式 (3.11) |
| $p_{u,s,v}(t,\theta_{u,s,v}(t),\theta_3)$ | 同一 physical link 連續服務時，由前一步 RF power 乘以前一步／目前角度增益比遞推的功率。 | 式 (3.12) |
| $P^{N}(t,\boldsymbol{\theta},\theta_3)$ | 聚合所有 active link power 與固定 overhead 的系統總功率。 | 式 (3.16) |
| $\eta_{u,s,v}(t,\theta_{u,s,v},\theta_3)$ | 固定分子鏈路、共同分母系統功率的單一 UE-link EE 顯示量。 | 式 (3.17) |

## 10.4 干擾、訊號品質與吞吐量

| 符號 | 定義 | 首次位置 |
|---|---|---|
| $c_{s,v}$ | 波束 $(s,v)$ 的頻率顏色，$c_{s,v}=(q_{s,v}-r_{s,v})\bmod 3$；六角格上相鄰蜂巢必為異色，同色波束共用子頻帶。 | 式 (3.12a) 前段 |
| $I^{i}_{u,s,v}$、$I^{x}_{u,s,v}$ | 同衛星與跨衛星同色干擾；求和以啟用指示 $z$ 為門檻，不以載量加權。 | 式 (3.12a)、(3.12b) |
| $p_{s,v}(t,\boldsymbol{\theta},\theta_3)$ | 波束 $(s,v)$ 的發射功率，取其所服務使用者的最大值；全系統角度狀態與波束寬完整保留在函數參數中。 | 式 (3.12a) 前段 |
| $I_{u,s,v}(t,\theta_{u,s,v},\theta_3)$ | 總同頻干擾，$I=I^{i}+I^{x}$。 | 式 (3.13) |
| $\sigma^2$ | 接收端雜訊功率，$\sigma^{2}=k_BTB^{w}$，$T=T_a+T_0(10^{N_f/10}-1)$；數值取 3GPP TR 38.821 VSAT 設定 \[22\]，列於第 5.1 節。 | 式 (3.13) |
| $\gamma_{u,s,v}(t,\theta_{u,s,v},\theta_3)$ | 唯一的實際鏈路 SINR；第三、四章共用，沒有 estimated／required／target 版本。 | 式 (3.13) |
| $B^w$ | 單一波束可用頻寬，$B^{w}=B^{g}/3$（三色重用）；$w$ 是 bandwidth 類別的單字母標籤。 | 式 (3.12a) 前段、式 (3.14) |
| $R_{u,s,v}(t,\theta_{u,s,v},\theta_3)$ | 鏈路 $(u,s,v)$ 的實際 throughput；分母使用 beam load $U_{s,v}(t)$。 | 式 (3.14) |

## 10.5 目標、獎勵與評估

| 符號 | 定義 | 首次位置 |
|---|---|---|
| P1、P2、P3 | 長期最佳化中的能量效率、換手成本與負載平衡三個目標。 | 式 (3.24) |
| $\Psi_u(t)$ | 使用者 $u$ 在時間 $t$ 的換手成本。 | 式 (3.27) |
| $(\rho_u(t),\delta_u(t))$ | 使用者 $u$ 在時間 $t$ 的服務衛星與服務波束索引；只在換手比較式中使用。字母沿用 MODQN 原文 $\rho_i(t),\delta_i(t)$（2026-08-21 由 hat notation 改回，見 WRITING-GUIDE.md §4）。 | 式 (3.27) |
| $\varphi_1,\varphi_2$ | 同衛星換束與跨衛星換手的成本，且 $0<\varphi_1<\varphi_2$。 | 式 (3.27) |
| $r_{1,u}(t,\boldsymbol{\theta},\theta_3)$ | 所選鏈路 EE 顯示量的總和：$\sum_{s,v}x_{u,s,v}(t)\eta_{u,s,v}(t,\theta_{u,s,v},\theta_3)$。**帶 $\boldsymbol{\theta},\theta_3$**(2026-08-23):右側經 $\eta$ 與 $P^{N}$ 依賴整組偏軸角與波束寬參數,左側必須涵蓋。$r_{2,u}$、$r_{3,u}$ 不帶。 | 式 (3.25) |
| $r_{2,u}(t)$ | 換手成本目標的逐使用者獎勵：$-\Psi_u(t)$。 | 式 (3.27) |
| $r_{3,u}(t)$ | 負載平衡獎勵；使用者 $u$ 當步所選波束的服務人數取負值，$r_{3,u}(t)=-U_{b_u(t)}(t)$。逐使用者可分解：$\sum_u U_{b_u(t)}(t)=\sum_{s,v}U_{s,v}(t)^2$ 恰為 P3 目標（2026-08-21，B13）。 | 式 (3.29) |
| $\overrightarrow R_u(t,\boldsymbol{\theta},\theta_3)$ | 三目標獎勵向量 $[r_{1,u}(t,\boldsymbol{\theta},\theta_3),r_{2,u}(t),r_{3,u}(t)]$,因第一個分量而帶 $\boldsymbol{\theta},\theta_3$。 | 式 (3.29) |

## 10.51 主鏈外的實驗／legacy provenance

下列符號只可出現在第五章的實驗設定、歷史執行紀錄或附錄對照，不是 active EE 主鏈的一部分。它們不得重新出現在式 (3.11)–(3.17) 的推導中；新契約的數值參數應由 scenario／experiment config 提供。

| 類別 | 符號 | 用途 |
|---|---|---|
| 深層角度型樣校準 | $c_0,\delta,g$、$F_m,\mu_m,\kappa_m$、型樣索引 $m$ | 超過一層 Bessel pattern 的校準、量測或替代型樣選擇；active 正文使用 $\theta_3,\mu,J_1,J_3$ 的單一型樣一層展開。 |
| 深層通道展開 | $L^{\mathrm{FS}},G^{\mathrm{LS}}$、$L_{st},L_{st,max},\phi_{st},\phi_{st,max}$、$L_N$ | 超過 $L_f,L_g,L_c,L_s$ 的距離、傳播、掃描損耗、NLoS clutter、接收方向與衰落細節；active 正文使用一層 $H$ 展開，這些量併入 $H$ 的實作層。 |
| Legacy power boundary | $R^{m},P_{\mathrm{sat},\max},P_0,\eta_0$、legacy $L^{\mathrm{atm}}/\chi_{\mathrm{atm}}$ | 舊 runtime 的最低速率、每星功率上限與 PA 參考設定；只在第五章 provenance 出現，$P_0$ 不等於 active segment-start 0.825 W(但數值等於式 3.15a 的 $p^{s}$)。**2026-08-22:$P_{\mathrm{beam},\max}$ 已改名 $p^{+}$ 並升為 active 參數**(式 3.15a 與鏈路可行性檢查)，不再屬此列。 |
| 電路與事件展開 | $N_s^{\mathrm{act}},P_{\mathrm{RFC}},P^{b},E_{\mathrm{tr}},E_{\mathrm{ho}},b^{\mathrm{tr}},b^{\mathrm{ho}}$ | 完整固定功率分攤與事件能量；正文彙總為 $P^f$。 |
| 頻率與雜訊展開 | $K_{\mathrm{FR}},B^{g},q,r,\operatorname{col},k_B,T$ | 完整頻率重用與熱雜訊參數；正文使用 $c$ 與 $\sigma^2$。 |


## 10.6 候選動作與狀態

| 符號 | 定義 | 首次位置 |
|---|---|---|
| $b_u(c,t)$ | 將使用者 $u$ 的候選編號 $c$ 映射到時間 $t$ 的實際衛星－波束對，$b_u(c,t)\in \mathcal{S}\times\mathcal{V}$。 | 第 4.1 節 |
| $s_u(t)$ | 使用者 $u$ 在時間 $t$ 的原始狀態，包含前一步連線、候選 SINR、偏軸角與未篩選需求。 | 式 (4.1) |
| $x_u(t-1)$ | 依候選索引 $C$ 排列的前一步連線向量。 | 式 (4.1) |
| $[\gamma_{u,s,v}(t,\theta_{u,s,v},\theta_3)]_{\substack{(s,v)=b_u(c,t)\\c\in \mathcal{C}}}$、$[\theta_{u,s,v}(t)]_{\substack{(s,v)=b_u(c,t)\\c\in \mathcal{C}}}$ | 依候選順序堆疊的鏈路 SINR／偏軸角元素；沿用唯一的 $\gamma_{u,s,v}$，cached／predicted provenance 放在 metadata。 | 式 (4.1) |
| $n_{s,v}(t-1)$ | 前一步選向波束 $(s,v)$、尚未完成執行篩選前的需求人數。 | 式 (4.1) |
| $N_u(t-1)$ | 依候選順序排列的前一步未篩選需求向量。 | 式 (4.1) |
| $m_u(t),m_{u,c}(t)$ | 決策時的候選可行性遮罩，以及其第 $c$ 個二元分量。 | 式 (4.2) |
| $A_u(t)$ | 使用者 $u$ 在時間 $t$ 可選的候選集合：$\{c\in \mathcal{C}\mid m_{u,c}(t)=1\}$。**可以是空集合**：此時式 (4.5) 的總和為 0、執行 no-op，該步 unserved 且轉移不入回放(2026-08-22 補)。 | 式 (4.3) |
| $a_u(t),a_{u,c}(t)$ | 使用者選取的候選編號，以及表示候選 $c$ 是否被選取的 one-hot 指示量。 | 式 (4.4)、式 (4.5) |
| $a(t)$ | 全體使用者在同一時間步的聯合動作。 | 式 (4.6) |

## 10.7 情境表示與正規化(**2026-08-22 整節退出正文**)

> ⛔ 使用者裁決:χ 壅塞情境與跨使用者情境正規化**從論文完全移除**,僅保留於程式作為消融開關。
> 論文 §4.2、式 (4.7)–(4.9) 已刪除,網路輸入回到基本狀態 $s_u(t)$(112 維)。
> 下列符號一律不得出現在論文任何章節。

| 符號 | 定義 | 首次位置 |
|---|---|---|
| $\chi_{u,c}(t),\chi_u(t)$ | 使用者 $u$ 在候選 $c$ 上縮放至 $[0,1]$ 的壅塞情境，以及依候選順序組成的情境向量。 | 式 (4.7) |
| $n_{s,v}^{C}(t)$ | 在時間 $t$ 將波束 $(s,v)$ 列為可行候選的使用者數。 | 式 (4.7) |
| $\iota_{u,c}(t)$ | 使用者 $u$ 在候選 $c$ 的競爭者中的預估訊號品質排名。 | 式 (4.7) |
| $s^\chi_u(t)$ | 將原始狀態與壅塞情境串接後的擴充狀態。 | 式 (4.8) |
| $\mu_i(t),\sigma_i(t)$ | 擴充狀態第 $i$ 維在同一時間步所有使用者中的平均與標準差。 | 式 (4.8a) |
| $s^\chi_{u,i}(t)$ | 使用者 $u$ 的擴充狀態第 $i$ 維。 | 式 (4.8a) |
| $\psi_{u,i}(t),\psi_u(t)$ | 逐維情境正規化後的分量與向量。 | 式 (4.8b)、式 (4.9) |
| $\epsilon_z$ | 情境正規化分母的正數常數。 | 式 (4.8b) |
| $\widetilde s_u(t)$ | 保留擴充狀態原尺度、並接上正規化向量後的網路輸入。 | 式 (4.9) |

## 10.8 舊版多目標強化學習與 Multi-Catfish 機制（V0.3 已汰換）

> 本節只記錄 V0.3 以前的論文版本。雙代理、舊三 reward objectives、兩個
> replay pool、Bellman target network 與 post-training coordination 均已退出
> active surface；V0.23 的 active 方法符號以第 10.13 節為準。

| 符號 | 定義 | 首次位置 |
|---|---|---|
| $\overrightarrow Q(s_u,a)$ | 三個目標的動作價值向量 $[Q_1(s_u,a),Q_2(s_u,a),Q_3(s_u,a)]$。 | 第 4.1 節 |
| $Q_j(s_u,a)$ | 第 $j$ 個目標的動作價值，$j\in\{1,2,3\}$。 | 第 4.1 節 |
| $\Omega=[\omega_1,\omega_2,\omega_3]$ | 三目標線性純量化的權重。 | 第 4.1 節 |
| $\epsilon$ | $\epsilon$-greedy 探索率。 | 第 4.1 節 |
| $Q_j^M,Q_j^{F}$ | 主代理與鯰魚代理中對應第 $j$ 個目標的 Q 網路。 | 第 4.3 節 |
| $D_M,D_{F}$ | 主代理與鯰魚代理的經驗池；兩者儲存校準後的獎勵，$D_{F}$ 另保留未整形與競爭整形兩種視圖。 | 第 4.3 節 |
| $\tau_t^{F}$ | 鯰魚代理在時間 $t$ 產生的全體使用者完整轉移束。 | 式 (4.10) |
| $g^{F}(t)$ | 鯰魚轉移束中校準前、未整形第一目標的平均可加貢獻，用作分層分數。 | 式 (4.10) 前 |
| $F_W,W$ | 最近 $W$ 個轉移束分數形成的經驗分布，以及其視窗長度。 | 式 (4.10) |
| $\operatorname{routing}(\tau_t^{F})$ | 依第一個目標的分位數門檻，將轉移束送入 $D_{F}$、送入 $D_M$ 或略過的分流規則。 | 式 (4.10) |
| $q,q_1,q_2$ | 分位數引數與低、高分流門檻，滿足 $0<q_1<q_2<1$。 | 式 (4.10) |
| $F_W^{-1}(q)$ | 經驗分布 $F_W$ 的 $q$ 分位數。 | 式 (4.10) |
| $\beta_M,\beta_{F}$ | 主代理與鯰魚代理的折扣因子，且 $\beta_M<\beta_{F}$。 | 式 (4.11) |
| $\beta_j^M,\beta_j^{F}$ | 第 $j$ 個目標在兩端使用的折扣因子，分別等於 $\beta_M,\beta_{F}$。 | 式 (4.11) |
| $\rho_I$ | 週期性介入批次中取自鯰魚經驗池的比例。 | 式 (4.12) |
| $B,n_{F},n_M$ | 混合批次大小、鯰魚樣本數與主代理樣本數。 | 式 (4.12) |
| $B_I$ | 由兩個經驗池的未整形校準樣本組成、用於主代理額外更新的混合批次。 | 式 (4.12) |
| $d$ | 訓練端索引，$d\in\{M,CF\}$。 | 式 (4.13) |
| $A_u^d(t)$ | 端 $d$ 為使用者 $u$ 保留的可行候選集合。 | 式 (4.13) |
| $\widetilde s_u^d(t)$ | 端 $d$ 使用的情境正規化輸入。 | 式 (4.13) |
| $V_u^d(a,t)$ | 端 $d$ 對候選 $a$ 的三目標加權價值。 | 式 (4.13) |
| $a_u^d(t)$ | 端 $d$ 為使用者 $u$ 選出的候選動作。 | 式 (4.13) |

## 10.9 舊版獎勵塑形與更新（V0.3 已汰換）

> 本節的 reward shaping、discount factor、TD target 與 target-network
> 參數只屬於舊版，不是 V0.3 的 active paper notation。

| 符號 | 定義 | 首次位置 |
|---|---|---|
| $a_{F}(t),a_{M\mid F}(t)$ | 相同動作前條件下，鯰魚代理的聯合動作與主代理的貪婪比較動作。 | 式 (4.14) 前 |
| $r_{1,u}^{F}(t,\boldsymbol{\theta},\theta_3),r_{1,u}^{M\mid F}(t,\boldsymbol{\theta},\theta_3)$ | 上述兩個聯合動作各自產生的第一個目標原始獎勵。 | 式 (4.14) |
| $r_{1,u}^{S}(t,\boldsymbol{\theta},\theta_3)$ | 鯰魚代理與主代理比較動作在第一個目標上的獎勵差值。 | 式 (4.14) |
| $\eta_w$ | 第一個目標的競爭獎勵權重。 | 式 (4.14) |
| $r_{1,u}^{C}(t,\boldsymbol{\theta},\theta_3)$ | 加入競爭項後的鯰魚代理第一個目標獎勵。 | 式 (4.14) |
| $\bar r_{j,u}^{d}(t),r_{j,u}^{d}(t)$ | 端 $d$ 第 $j$ 個目標的尺度化獎勵與尺度化前獎勵。 | 式 (4.12)、式 (4.13) |
| $y_{j,u}^{d}$ | 端 $d$ 第 $j$ 個目標的時間差分更新目標。 | 式 (4.12) |
| $\theta_j^d,\theta_j^{d,-}$ | 端 $d$ 第 $j$ 個線上網路與目標網路參數。 | 式 (4.15) |
| $\beta_d$ | 式 (4.12) 中端 $d$ 所使用的折扣因子。 | 式 (4.12) |
| $c_j$ | 第 $j$ 個目標的正數尺度校準常數。⚠ **2026-08-22:第 5.1 節列出的三個舊值已失效**,`c_1` 校準的 $r_1$ 量級隨 F-1／F-2／C-4／C-8 改變,須以新契約 runtime 重算,`c_3` 即實驗協定中 $r_3$ 尺度選取映射的輸出,不是另一個獨立校準的常數。有效取捨比例為 $\omega_j/c_j$。 | 式 (4.13)、第 5.1 節 |

## 10.10 實驗設定中沿用的符號

| 符號 | 定義 | 位置 |
|---|---|---|
| $H$ | 每回合時間步上限。 | 第 5.1 節、演算法 4-1 |
| $E$ | 訓練回合數。 | 演算法 4-1 |
| $K$ | 目標網路同步週期。 | 演算法 4-1 |
| $e$ | 訓練回合索引。 | 演算法 4-1 |
| $\epsilon_\mu$ | 波束增益公式在軸心附近使用的數值閾值。 | 第 5.1 節 |
| $T_a,T_0,N_f$ | 天線溫度、參考溫度與雜訊指數；由此得到第 4 節的接收系統溫度 $T$。 | 第 5.1 節 |
| $R_b$ | 由衛星高度與半功率波束寬計算的波束覆蓋半徑：$h_s\tan(\theta_3/2)$。**鋪格慣例(2026-08-22 補記)**:$R_b$ 取為六角格的**外接圓半徑**,故格心間距為 $\sqrt{3}R_b$、單格面積為 $2\sqrt{3}\left(\sqrt{3}R_b/2\right)^2$,此慣例使每格內接於自身的 3 dB 等高線而不留覆蓋洞。⚠ 若誤取為內切半徑,單格面積會高估 4/3 倍(509.0 → 678.7 km²),面積比估算會因此偏低。 | 第 5.1 節 |

## 10.11 容易混淆的重用記號

| 記號 | 區分方式 |
|---|---|
| $p^{0}$ 與 $p^{+}$ 的相容條件 | **必須 $p^{0}<p^{+}$,否則每個分段在第一步就不可行。** 式 (3.11) 的遞推在段內只會讓功率上升,所以起點超限便無法回到可行區。舊值 $p^{0}=2$ W 比 $p^{+}=1.65$ W 高 0.835 dB,實測 outage 率恆為 1.0,2026-08-22 改為 $p^{0}=p^{+}/2=0.825$ W,使 $p^{+}/p^{0}=3$ dB 恰等於格邊緣的增益下降。 |
| $\xi_{s,v}$、$P^{p}_{s,v}$ | **2026-08-22 去掉 $u$ 索引**。一支波束只有一個放大器,式 (3.15a) 的引數本來就只有 $p_{s,v}$,左側卻帶 $u$,式 (3.16) 因此改為對 $(s,v)$ 的二重和、過濾器用 $z_{s,v}$。逐鏈路加總會多出 $\sum_{s,v}(U_{s,v}-1)P^{p}_{s,v}$,隨佔用單調上升,汙染 P3。 |
| $G^{T}$、$F$、$\mu$ 的引數 | **2026-08-22 改為雙引數 $(\theta,\theta_3)$**。理由:$\theta_3$ 出現在 $\mu$ 定義式右側,定義式的左側必須涵蓋右側出現的量；本表採用一般函數慣例，以逗號分隔兩個參數。$G_0$ 是乘性尺度常數、不改變型樣形狀,仍不列入引數。式 (3.10) 之後仍明寫為 $G^{T}(\theta_{u,s,v},\theta_3)$。 |
| $p^{+}$ 與 $P_{\mathrm{beam},\max}$ | **同一個量,前者是現行名稱**(每波束射頻輸出上限 1.65 W,式 3.15a 的回退後操作上限,亦為鏈路可行性門檻),後者是 2026-08-22 之前的舊名,只保留在歷史文件中。 |
| 學習率 | **刻意不給符號**。$\alpha$ 已是仰角 $\alpha_{u,s}(t)$,若再用 $\alpha$ 表學習率會撞號,表 5-3 以中文「學習率」書寫,並列為受控變因掃描 $\{0.01,0.003,0.001\}$。 |
| $F$ | **三義,靠位置區分**:$F(\theta,\theta_3)$ 是天線角度型樣（帶引數的函數，式 3.9）,$F_W$ 是最近 $W$ 束分數的經驗分布（帶下標）,**上標 $F$ 是鯰魚端標籤**,$d\in\{M,F\}$（2026-08-22 由雙字母 `CF` 改為單字母,助記 Fish）。 |
| $L$ 的下標 | $L_{u,s,v}$ 是**總**路徑損耗（帶三索引）,$L_f$、$L_g$、$L_c$、$L_s$ 是它的四個分量（自由空間、氣體吸收、閃爍、遮蔽），**下標是名稱不是索引**。⚠ $L_s$ 的 $s$ **不是衛星索引**,對應 HOBS 式 (1) 的 $L_f,L_g,L_c,L_s$（2026-08-22 為單字母化改寫）。 |
| $w$ | **下標 $w$ 是視窗**（$L_w$ 可見衛星數、$J_w$ 每顆視窗衛星的候選波束槽數，兩者對所有使用者相同，故不用 $u$ 當下標）,**上標 $w$ 是頻寬類別**（$B^w$ 單一波束可用頻寬）。位置不同、意義不同。 |
| $\tau$ | $\tau_{u,s,v}$ 是 segment 起始時間步（正文使用）；softmax 溫度 $\tau$ 已隨容量懲罰刪除，不得再出現。 |
| $H$ | $H_{u,s,v}(t)$ 是線性鏈路功率因子(式 3.10)，$H$(無上下標)是 baseline 回合長度，\(H^c\) 是 V0.3 matched counterfactual horizon。V0.3 公式不得省略上標 \(c\)。 |
| \(v\) 與 \(\mathbf v\) | 斜體 \(v\) 是 beam index；粗體 \(\mathbf v_{u,s,v}(t)\) 是 beam-center direction vector。公式與圖中必須保留字重差異。 |
| $\eta$ | $\eta_{u,s,v}$ 是鏈路 EE(式 3.17),$\eta^{PA}$ 是功率放大器效率(legacy),$\eta_w$ 是鯰魚競爭權重(式 4.11)。**三義,靠上下標區分。** |
| $\chi$ | $\chi_{\mathrm{atm}}$ 是大氣衰減係數(第 5.1 節)。壅塞情境的 $\chi$ 已於 2026-08-22 從論文移除,**不得再出現**。 |
| $U$ 與 $U_{s,v}(t)$ | $U$ 是使用者集合；$U_{s,v}(t)$ 是決策後實際服務人數。 |
| $p^{0}$ 與 $P_0$ | **前者是段起始發射功率**(小寫 $p$、上標 0,正文主鏈使用),後者是 legacy 單一 PA 飽和輸出功率(大寫 $P$、下標 0,只出現在第 5.1 節的 legacy provenance 區塊)。大小寫與上下標位置都不同,不可互換。 |
| $P_0$ 與 $P_{\mathrm{sat},\max}$ | 前者是 legacy 單一 PA 飽和輸出功率；後者是 legacy 單顆衛星所有啟用波束的射頻輸出總上限；兩者都不是 active recurrence 的 cap。 |
| $q$ | $q_{s,v},r_{s,v}$ 中的 $q$ 是六角格座標；$q_1,q_2$ 與 $F_W^{-1}(q)$ 中的 $q$ 是分位數引數。 |
| $c$ | $c\in \mathcal{C}$ 是候選索引；$c_0$ 是真空光速；$c_j$ 是目標尺度常數。 |
| $s$ | $s\in \mathcal{S}$ 是衛星索引；$s_u(t)$ 是使用者狀態。 |
| $B$ | $B^{g}$、$B_{\mathrm{beam}}$ 是頻寬；$B$ 是訓練批次大小；$B_I$ 是混合批次。 |
| $\alpha$ | $\alpha_{u,s}(t)$ 是仰角；$\alpha_s(t)$ 是衛星功率縮放係數。 |
| $7$ | ⚠ **兩個 7 無關**:$J_w=7$ 是每顆視窗衛星的候選波束槽（錨定格 + 六鄰居，repo 的 `NUM_BEAM_SLOTS`）；原論文 MODQN Table I 的 $V=7$ 是**他們粒度下的每衛星波束集合大小**，已被本論文的 $V$（指向格數）取代。數值相同純屬巧合，**不得互相代入**，也不得由它推出任何上限。 |
| $L$ | $L_w$ 是候選表保留的可見衛星數（第 4.1 節）；$L_{u,s,v}(t)$ 是 Ch3 路徑／衰落損耗層（式 3.10b，逐字採用 HOBS 式 (1) 的四項）；$L$（無下標）已隨容量懲罰刪除（2026-08-21）。二者僅靠下標區分，2026-08-21 由 $L_{\mathrm{cap}}$ 簡化而來。 |
| 【新】\(\Psi\) 與 \(\Phi\) | \(\Psi\) 自 V0.25 起**專用於交互作用殘差**，恆帶花體集合下標 \(\mathcal K\)（\(\Psi_{\mathcal K},\Psi^{q}_{\mathcal K},\Psi^{1}_{\mathcal K},\Psi^{f}_{\mathcal K}\)）；換手／QoS 計價改為 \(\Phi\)，恆帶使用者下標或組態引數（\(\Phi_u(t)\)、\(\Phi(a)\)）。式 (3.27) 的 \(\Psi_u(t)\) 原列保留為 V0.23 讀法，V0.25 讀作 \(\Phi_u(t)\)。 |
| 【新】\(\Omega\) | \(\Omega(a)\)、\(\Omega^{q}(a)\)、\(\Omega^{q}_{j}(a)\) 是組態層剩餘與排序鍵，**恆帶組態引數**；舊三目標純量化權重 \(\Omega=[\omega_1,\omega_2,\omega_3]\)（§10.8）已退場，\(\omega_j\) 不得再出現。 |
| 【新】\(d\) | \(d_{u,s,v}(t)\) 是斜距（三下標、無上標）；\(d_i(a)\)、\(d^{q}_i\)、\(d^{1}_i\) 是單邊增量（單一成員下標，**再定義**，不再等於 \(\ell_i+e_i\)）；\(D(a)\) 是其總和。第 3.1.2 節僅出現一次的天線口徑 \(D=1.0275\lambda/\theta_3\) 與 \(D(a)\) 靠引數區分，定稿時應改寫為 \(D_a\) 或以文字敘述口徑，二擇一並回填本節。 |
| 【新】\(q\) | \(q_{s,v}\) 是六角格軸向座標（雙下標、無上標）；\(q^{\alpha}_{u,s,v}(t)\) 是分位通道增益因子（三下標＋上標）；單獨的上標 \(q\) 是**選擇時視圖**標記（\(\Omega^{q}\)、\(d^{q}_i\)、\(\Psi^{q}_{\mathcal K}\)、\(\gamma^{q}\)、\(m^{q}\)）；\(q_1,q_2\) 與 \(F_W^{-1}(q)\) 的分位引數隨 §10.8 退場。 |
| 【新】\(\alpha\) | \(\alpha_{u,s}(t)\) 是仰角，**恆雙下標且從不出現在上標位置**；\(q^{\alpha}\) 的 \(\alpha\) 是分位水準標籤，**恆在上標位置且不帶下標**，主要水準 \(\alpha=0.10\)，診斷掃描 \(\alpha\in\{0.05,0.10,0.25\}\)。處置與 \(w\)（下標＝視窗、上標＝頻寬）同型。 |
| 【新】\(m\) | \(m_{u,c}(t)\)、\(m_{iar}\) 是遮罩，**恆為下標且不帶上標**；\(m^{r}\)、\(m^{q}\)、\(m^{o}\) 是 ACM 模式三元組，**恆為上標＋三下標鏈路量**；\(\mathcal M\)／\(\mathrm M\) 是模式集合與其大小。三個 MODCOD 物件必須分開報告，不得互相代入。 |
| 【新】\(a\) 的上標族 | \(a^{0}\) 參考提案、\(a^{1}\) 認證單邊最適（引擎與探針記為 `u`）、\(a^{d}\) 可加分數選出的組態、\(a^{\psi}\) 交互作用感知組態、\(a^{\star}_u(t)\) 承諾動作；\(a_u(t)\)、\(a_{u,c}(t)\) 恆帶下標。上標恆為單一字母或數字，不得寫成多字母標籤。 |
| 【新】\(\nu\) | \(\nu_m\) 恆帶模式下標，是頻譜效率（bit/s/Hz）；\(v\) 恆為波束索引、\(\mathbf v_{u,s,v}\) 恆為粗體方向向量；\(\nu_j\)（loss dispersion）僅屬 §10.12 retired。⚠ 殘餘風險已登記：部分字型下 \(\nu\) 與 \(v\) 形近，備用字形為 \(\varepsilon_m\)（若採用，本節加註「\(\varepsilon_m\) 帶模式下標＝頻譜效率；\(\epsilon_\mu\)、\(\epsilon_z\) 帶角色下標＝數值閾值」）。 |
| 【新】\(R\) | \(R_{u,s,v}\) 是實際 throughput（三下標）；\(R^{\star}\) 是每使用者名目速率目標（上標 \(\star\)、無下標）；\(R^{+}\) 是每同色波束最大吞吐量；\(R_E\)、\(R_b\) 是地球半徑與波束覆蓋半徑（下標為名稱不是索引）；宣告衰落乘積中的 \(R\)（萊斯功率衰落）**無上下標且只出現在通道衰落式**。五者共用字母，靠上下標與所在式子區分。 |
| 【新】\(\gamma\) 與 \(\Gamma\) | \(\gamma_{u,s,v}\) 是唯一實際鏈路 SINR；\(\gamma^{q}_{u,s,v}\) 是選擇時視圖的預測 SINR；\(\gamma_m\) 是模式 \(m\) 的所需 SINR；\(\Gamma_r(U_{s,v}(t))\) 是速率目標對應的所需 SINR，**只決定功率設定點**；\(\gamma^{-}=-1.4418\) dB 是 PHY 可解碼門檻（上標 \(-\) 沿用 \(G^{R}_{-}\)、\(\theta^{R}_{-}\) 的下界慣例）；\(\gamma^{\star}=7.528\) dB 只屬固定 SINR 架構 a-γ 的敏感度格。 |
| 【新】\(\mathcal K\) 與 \(K\) | 花體 \(\mathcal K\subseteq\mathcal U\) 是變動使用者集合，元素數為同字母正體大寫 \(K\)。密封宣告以 \(A\) 表同一集合，本表依權威順序 ③ 採花體 \(\mathcal K\)。\(K_R\) 恆帶下標 \(R\)（萊斯因子）；舊目標網路同步週期 \(K\) 隨舊表 5-3 退場。 |
| 【新】\(\mathcal X\)、\(\mathrm X\) 與 \(X\) | 花體 \(\mathcal X(t)\) 是有界候選組態目錄、\(\mathrm X\) 是其大小；正體 \(X\)（無下標）是 dB 域高斯遮蔽，只出現在衰落乘積式；斜體小寫 \(x_{u,s,v}(t)\) 是連線指示量。三者字重與大小寫皆不同。⚠ 密封契約 §A2 以花體 \(\mathcal C\) 稱該目錄，與本表既有的候選動作索引域 \(\mathcal C\) 直接衝突，故不採用該字形。 |
| 【新】\(\mathcal M\) | 花體 \(\mathcal M\) 只表 ACM 模式集合。⚠ 密封契約 §A2 另以花體 M 表「名目物理模型」，本表不採該用法；名目模型一律以文字敘述，不給符號。 |
| 【新】\(\delta\) 與 \(\Delta\) | \(\delta_u(t)\) 是服務波束索引（帶使用者下標，式 3.27）；無下標的 \(\delta\) 是宣稱邊際（\(+0.5\%\) 相對增益，含 2.5 分位下界規則）；\(\Delta^{\star}\) 是規劃替代假說（\(+2\%\) 相對增益）；\(\Delta t\) 是決策區間長度。 |
| 【新】\(k\) | \(k\in\{0,\dots,47\}\) 是步內積分邊界索引（48 個邊界、47 個子區間）；\(k_B\) 是波茲曼常數，恆帶下標 \(B\) 且只出現在 \(\sigma^{2}=k_BTB^{w}\)；V0.3 的 matched-horizon offset \(k\) 僅屬 §10.12 retired。 |
| 【新】\(W\) | 本表的單一波束可用頻寬恆為 \(B^{w}\)。⚠ 密封宣告以 \(W\) 表該頻寬（如 \(N_0W\)、\(W\,\nu_m/n_b\)），本表不採；\(W\) 在本表僅為 §10.8 retired 的視窗長度，不得在 V0.25 公式中作頻寬使用。 |
| 【新】\(b\) | \(b_u(c,t)\) 是候選編號到衛星－波束對的映射；\(b^{-}(t)\) 是前一次承諾的關聯，\(b^{-}_{-i}(t)\) 是排除使用者 \(i\) 後的背景，**只供換手／\(\Phi\)／事件記帳**，與參考提案 \(a^{0}\) 永不混用；\(b_o\) 是輸出回退（下標 \(o\)）。 |
| 【新】\(o\) | 上標 \(o\) 只用於 \(m^{o}\)（實現解碼結果）；\(b_o\) 的 \(o\) 是下標；V0.3 的 \(D^{o}\) 僅屬 §10.12 retired。 |
| 【新】\(\Upsilon\) | \(\Upsilon\) 是淨避碰值，全表無對應小寫 \(\upsilon\)，與 \(\Psi\)、\(\Phi\)、\(\Omega\) 字形距離足夠；引擎名稱 `V_CA` 的多字母下標不得進入公式。 |
| 【新】\(F\) 與 \(G\) 的引擎讀法 | 紙面的組態層剩餘一律寫 \(\Omega(a)\)（\(\Phi\) 只計一次）。引擎與存在性探針以 \(F\) 表分數、以 \(G\) 表加上訊令計價後的協調器目標；⚠ 密封來源對「\(\Phi\) 是否在 \(F\) 之內」並不一致（契約 v1 §B4 與探針分裂修訂 1 寫 \(F=B-\eta_{\mathrm{ref}}E-\Phi\)，v1.5 §2 與探針鄰域裁決寫 \(F=B-\eta_{\mathrm{ref}}E\) 且另有 \(G\)），已登記於本輪碰撞稽核，本表不靜默取捨。表內 \(F(\theta,\theta_3)\) 仍只是天線角度型樣，\(G^T,G^R,G_0\) 仍只是增益。 |


## 10.12 歷史 Multi-Catfish MCRL V0.3 方法擴充符號（retired）

本節只保留 V0.23 以前的 V0.3 paper notation，明確標記為 historical／retired，不能作為 current method 或 active claim。
主符號維持單字母；需要多個 owner／route 維度時，只組合既有的單字母
或數字索引。程式與 evidence receipt 的 `z1`、`z2`、`z3` 欄位分別映射
到論文符號 \(\zeta_{1,u}\)、\(\zeta_{2,u}\)、\(\zeta_{3,u}\)，不得直接
拿 schema field 當論文公式符號。

### 10.12.1 系統級 EE 與 matched accounting

| 符號 | 定義 | 單位／限制 |
|---|---|---|
| \(i\) | 一般使用者索引；在 C3 中表示 \(i\in\mathcal U\setminus\{u\}\) 的非焦點使用者 | user index；\(v\) 仍專屬 beam index |
| \(R_u(t)\) | 使用者 \(u\) 的 selected-link aggregate throughput：\(\sum_{s\in\mathcal S}\sum_{v\in\mathcal V}x_{u,s,v}(t)R_{u,s,v}(t)\) | bit/s |
| \(\Delta t\) | 一個離散決策區間的時長 | s；V0.3 的跨時間 EE 與 surplus 公式可使用 |
| \(\mathcal B\) | 評估窗內 delivered bits：\(\sum_t\sum_{u\in\mathcal U}R_u(t)\Delta t\) | bit；不是集合 |
| \(\mathcal E\) | 評估窗內 network energy：\(\sum_tP^N(t)\Delta t\) | J；不同於訓練回合數 \(E\) |
| \(\eta^N\) | network-level ratio-of-sums EE：\(\mathcal B/\mathcal E\) | bit/J；不同於 link 顯示量 \(\eta_{u,s,v}\) |
| \(M,C\) | matched reference branch 與 unilateral candidate branch 的單字母角色標籤 | superscript/subscript role |
| \(P_M^N(k),P_C^N(k)\) | offset \(k\) 的 reference/candidate canonical network power | W |
| \(\lambda_0\) | TRAIN-only frozen calibration multiplier：\(\mathcal B_0^M/\mathcal E_0^M\) | bit/J |
| \(\Delta\mathcal B_k\) | offset \(k\) 的 candidate-minus-reference total-bit difference | bit |
| \(\Delta\mathcal E_k\) | offset \(k\) 的 candidate-minus-reference network-energy difference | J |
| \(g_k\) | fixed-\(\lambda_0\) system surplus：\(\Delta\mathcal B_k-\lambda_0\Delta\mathcal E_k\) | bit |
| \(H^c\) | matched counterfactual horizon length | positive integer；Pilot 1 uses \(H^c=4\) |
| \(k\) | matched-horizon offset | \(0,\ldots,H^c-1\) |

未加參數的 \(\tau\) 不用作 V0.3 評估窗；\(\tau_{u,s,v}\) 繼續專指
served-segment start time。評估窗以 prose 說明，公式直接對 \(t\) 求和。

### 10.12.2 三路 target、資料與學習

| 符號 | 定義 | 單位／限制 |
|---|---|---|
| \(\zeta_{1,u}\) | C1 focal opening surplus | bit |
| \(\zeta_{2,u}\) | C2 downstream temporal surplus | bit |
| \(\zeta_{3,u}\) | C3 non-focal opening rate externality | bit |
| \(D^o,D^t,D^a\) | opening source、temporal source、held-out identity dataset | \(D^a\) 不得產生 gradient |
| \(j\) | route index | \(j\in\{1,2,3\}\) |
| \(Q_j(s_u(t),a)\) | 第 \(j\) 個 independent online Q surface | normalized surplus |
| \(\kappa\) | shared output scale：\(\mathcal B_0^M/n_0\) | bit |
| \(n_0\) | TRAIN-only scale-calibration window 的 decision count | positive integer |
| \(\widetilde\zeta_{j,u}\) | normalized route target：\(\zeta_{j,u}/\kappa\) | dimensionless |
| \(\nu_j\) | frozen route-\(j\) loss-dispersion scale | positive |
| \(w_j\) | route-\(j\) loss weight：\(1/\nu_j^2\) | optimization only |
| \(\beta\) | reference-action gauge coefficient | nonnegative；與舊版 discount factor 無關 |
| \(\ell_j\) | route-\(j\) pairwise zero-bootstrap regression loss | nonnegative |

V0.3 不使用 hat notation；因此 loss dispersion 寫作 \(\nu_j\)，不寫
\(\widehat\sigma_j\)。\(\lambda_0\)、\(\kappa\)、\(\beta\) 是 V0.3
明確重新進入 active surface 的單字母參數，其舊語意仍保持汰換。

### 10.12.3 狀態、動作與部署

| 符號 | 定義 | 限制 |
|---|---|---|
| \(s_u(t)\) | 使用者 \(u\) 在時間 \(t\) 的 deployed state | 不以裸 \(s\) 表示 state；裸 \(s\) 仍是 satellite index |
| \(A_u(t)\) | 使用者 \(u\) 的 legal, service-safe action set | 沿用第 10.6 節 |
| \(a_u^M(t),a_u^C(t)\) | matched reference 與 unilateral candidate action | branch role 為單字母上標 |
| \(\Phi_u(t,a)\) | deployment score：\(\sum_{j=1}^3Q_j(s_u(t),a)\) | normalized surplus |
| \(a_u^\star(t)\) | 唯一執行的 Main action：\(\arg\max_{a\in A_u(t)}\Phi_u(t,a)\) | no auction／coordinator／vote |

V0.3 的三路 bookkeeping identity 為

\[
\zeta_{1,u}+\zeta_{3,u}+\zeta_{2,u}
=\sum_{k=0}^{H^c-1}g_k.
\]

這個 identity 只證明 non-overlap，不是 learnability 或 EE efficacy
證明。

## 10.13 Multi-Catfish MCRL V0.23 方法擴充符號（active）

本節是 V0.23 current method 的唯一 active Multi-Catfish notation。它取代
V0.3 的三路 bookkeeping；第 10.12 節保留的內容全部屬 historical／retired。
紙面 primary symbols 的上下標只使用單一字母或單一數字；ref、src、dst、
beam、sat、own、nf、joint、base、cand、main 等多字母上下標不得進入公式。
程式欄位名、receipt key 與內部 gate token 不是紙面符號。

### 10.13.1 Main objective and shared counterfactual

| 符號 | 定義 | 單位／限制 |
|---|---|---|
| \(x^0,x^1,x^2,x^c\) | 四個 matched current-slot profiles；依序對應 00、10、01、11。上標 \(c\) 是 coalition profile 標籤，與候選索引 \(c\) 的字形碰撞須靠上下文區分。 | profile label；只限 C3 two-user game |
| \(B_u(x)\) | profile \(x\) 中使用者 \(u\) 的 delivered bits | bit |
| \(E(x)\) | profile \(x\) 的 current-slot network energy | J |
| \(G(x)\) | 共同 network surplus：\(\sum_{u\in\mathcal U}B_u(x)-\lambda E(x)\) | bit |
| \(\lambda\) | frozen bits-per-joule multiplier | bit/J；不得換成 outcome 後價格 |
| \(\kappa\) | 三路共用的輸出尺度；teacher target 只除以一次 | bit |
| \(\eta^N\) | Main 的 network ratio-of-sums EE：完整範圍總 delivered bits 除以總 network energy | bit/J；不是 per-row EE 平均 |
| \(\mathcal A_u^+(t)\) | 使用者 \(u\) 在時間 \(t\) 通過 native safe mask 的 action set | \(+\) 為單一符號，不使用多字母 safe 下標 |
| \(a_u^\star(t)\) | 唯一執行的 Main action：\(\arg\max_{a\in\mathcal A_u^+(t)}[Q_1+Q_2+Q_3]\) | one-pass；無 coordinator／auction／vote |

### 10.13.2 Three route roles

| 符號 | 定義 | 狀態 |
|---|---|---|
| \(C_1\) | focal current-slot own-rate 加完整 opening-step marginal network-energy surplus 的 route | source／comparison lineage；efficacy 未定 |
| \(C_2\) | 固定 OPS-3 projected-persistence route | present but empirically unqualified；不得以舊 r2／handover objective 取代 |
| \(C_3\) | two-user Local Coalition-Shapley Spatial Residual Surplus（LC-SRS）route | current method candidate；不等同 efficacy |
| \(Q_1,Q_2,Q_3\) | 恰好三個獨立 Q surface，分別承接 \(C_1,C_2,C_3\) 的 route-specific source | normalized bits-per-\(\kappa\)；部署無權重相加 |

### 10.13.3 Two-user LC-SRS teacher

| 符號 | 定義 | 單位／限制 |
|---|---|---|
| \(i\) | ordered two-user member index，\(i\in\{1,2\}\) | 僅限嚴格兩人 wrapper |
| \(\ell_i\) | member \(i\) 的 own-rate 加 network-energy marginal local term：\(B_i(x^i)-B_i(x^0)-\lambda[E(x^i)-E(x^0)]\) | bit |
| \(e_i\) | member \(i\) 的 non-focal bits externality：\(\sum_{u\ne i}[B_u(x^i)-B_u(x^0)]\) | bit |
| \(d_i\) | partial surplus：\(\ell_i+e_i\) | bit；diagnostic |
| \(\Psi_B\) | 11 相對於 10、01 的 total-bit interaction | bit |
| \(\Psi_E\) | 11 相對於 10、01 的 network-energy interaction | J |
| \(\Psi\) | fixed-\(\lambda\) interaction surplus：\(\Psi_B-\lambda\Psi_E\) | bit |
| \(z_{3,i}\) | LC-SRS paper target：\(e_i+\Psi/2\) | bit；只限 two-user game |
| \(y_i\) | normalized teacher target：\(z_{3,i}/\kappa\) | dimensionless |
| \(\sum_{i=1}^{2}(\ell_i+z_{3,i})=G(x^c)-G(x^0)\) | exact scoped identity | 只對 named 00/10/01/11 current-slot game 成立 |

teacher 只在 training 取得 privileged physical profiles、matched random field
與 outcome。它不得被解讀為一般 \(m\)-player Shapley、partial-adoption 或
all-roster decomposition；\(\Psi/2\) 不改成 \(\Psi/m\)。reference cells 與
legal-but-unsupported cells 是 zero controls，supported member cells 只寫入
一次 \(y_i\)，正負與零值均保留。

### 10.13.4 Deterministic C3View and scalar learner

| 符號 | 定義 | 限制 |
|---|---|---|
| \(c_{ia}\) | focal member \(i\) 與候選 action \(a\) 的 action-context descriptor | 僅 predecision；\(i,a\) 各為單字母索引 |
| \(t_{iar}\) | relation token；\(r\) 表普通關係或唯一 pair-context token 槽 | deterministic；不含 profile outcome |
| \(m_{iar}\) | action／relation mask | illegal row 與 token 需為零 |
| \(f\) | ordinary 與 pair-context token 共用的 67-64-64-1 scorer | 不另設 pair head 或 allocation head |
| \(F_i(a)\) | masked token score：\(\sum_{r:m_{iar}=1}f(c_{ia},t_{iar})\) | latent aggregate |
| \(Q_{3,i}(a)\) | reference-centred scalar surface：\(F_i(a)-F_i(a_i^0)\) | reference output exact zero |
| \(a_i^0\) | detached reference action | 上標 0；不寫多字母 ref |

C3View 只由 captured committed context、native mask、candidate／cross-user
geometry、detached reference occupancy 與 detached \(Q_1+Q_2\) descriptors
建立；不讀 raw outcome、rate、energy、active set、future field、teacher
fading、label 或 fresh RNG。raw identifiers 只作 metadata。三路在共同 safe
mask 下直接無權重相加並只做一次 masked argmax；沒有 coordinator、auction、
vote、joint decoder、fallback、retry 或 post-selection repair。

### 10.13.5 Active status and retired boundary

V0.23 的 method core 已凍結為 paper-visible draft，但 gate outcome 尚未開啟。
C1／C2 qualification、C3 learnability、composition benefit、FULL-over-ablation
ordering 與 EE efficacy 都不由本表推論。第 10.12 節的 \(\zeta\)、\(D^o,D^t,D^a\)、
\(H^c\) 與 V0.3 三路 bookkeeping 僅作 historical／retired provenance，不得
與本節的 \(z_{3,i}\)、\(y_i\) 或 \(x^0,x^1,x^2,x^c\) 混用。


## 10.14 Multi-Catfish MCRL V0.25 物理繼任者擴充符號（active，2026-09-09 併入）

本節是 V0.25 繼任者（主模型 `V025-ANGLE-RATE-TPC-TDM-ACM`，代號 a-r；宣告參考模型
`V025-FIXED-EIRP-ACM`，代號 b）的唯一 active 擴充符號集合。它取代第 10.13 節的
two-user LC-SRS 三路記法；第 10.12、10.13 節保留為 historical／retired provenance。
紙面主符號的上下標只使用單一字母或單一數字；程式欄位名、receipt key 與 gate token
不是紙面符號（對照見 §10.14.6）。本節**只固定記法**，不宣稱任何結果。

### 10.14.0 兩項先決處置（讓新增量有位置可放）

| 處置 | 舊 | 新 | 理由（碰撞層面） |
|---|---|---|---|
| 【改】R-1 換手成本改名 | \(\Psi_u(t)\)（式 3.27） | \(\Phi_u(t)\)、\(\Phi(a)\) | \(\Psi\) 在繼任者中必須專用於交互作用殘差（語意一脈相承自 §10.13.3 的 \(\Psi_B,\Psi_E,\Psi\)）。\(\Phi\) 與價格 \(\varphi_1,\varphi_2\) 形成大小寫同族對，與 \(p^{s}\)／\(p^{+}\) 同一慣例。 |
| 【改】R-2 組態剩餘改字母 | \(G(x)=\sum_u B_u(x)-\lambda E(x)\)（§10.13.1） | \(\Omega(a)\) | 繼任者需要餘裕調整版的剩餘，若沿用 \(G\) 則 \(G^{q}(a)\) 會與 \(G^T(\theta,\theta_3)\)、\(G^{R}_{u,s,v}\)、\(G_0\) 形成「\(G\) 加單字母上標＝增益」的既有讀法直接衝突，而 §10.13 對 \(G(x)\) 的原有解法（靠 profile 引數區分）在加上上標後失效。\(\Omega\) 由已退場的三目標純量化權重釋出。 |

### 10.14.1 ACM 階梯、速率目標與時間積分

| 符號 | 定義 | 單位／限制 |
|---|---|---|
| 【新】\(m\in\mathcal M=\{1,\dots,\mathrm M\}\) | ACM 模式索引、模式集合與其大小；花體集合＋同字母正體大寫基數。密封表為 \(\mathrm M=28\) 個模式（QPSK／8PSK／16APSK／32APSK 全表） | 索引；模式表自 EN 302 307-1 Table 13 取用並經 SHA 釘選。⚠ 圖 1 計算稿使用的是 11 個 QPSK 模式的截斷表，與密封宣告不一致，以宣告為準（見碰撞稽核 C-15） |
| 【新】\(\nu_m\) | 模式 \(m\) 的頻譜效率；最高模式 \(\nu_{\mathrm M}=3.7109\) | bit/s/Hz；恆帶模式下標。備用字形 \(\varepsilon_m\)（見 §10.11） |
| 【新】\(\gamma_m\) | 模式 \(m\) 的所需 SINR（含一次 roll-off 0.20 與一次 1.7 dB 實作餘裕） | 線性或 dB，公式中用線性 |
| 【新】\(R^{\star}\) | 每使用者名目速率目標；主要工作點 \(R^{\star}=50\) Mbit/s | bit/s；是**功率設定點**，不是需求模型；regime R7／a-r0／R1 分別為 25／50／100 Mbit/s |
| 【新】\(\Gamma_r\!\left(U_{s,v}(t)\right)=\gamma_{m^{r}}\) | 達成 \(R^{\star}\) 所需的最低模式對應 SINR：\(m^{r}=\min\{m\in\mathcal M: B^{w}\nu_m/U_{s,v}(t)\ge R^{\star}\}\) | 只決定功率設定點；占用經由 \(U_{s,v}\) 進入功率 |
| 【新】\(R^{+}=B^{w}\nu_{\mathrm M}\) | 每（同色）波束在最高模式下的最大吞吐量 | bit/s；量測值 618.476 Mbit/s（\(B^{w}\approx166.7\) MHz、\(\nu_{\mathrm M}=3.7109\)），故等 airtime 下每波束至多 12 位使用者可各得 50 Mbit/s，13 位時對所有使用者皆不可行 |
| 【新】\(m^{r}_{u,s,v}(t)\) | **目標模式**：滿足速率目標所需的最低模式，只用於設定發射功率 | 上標 \(r\)＝rate target；三下標鏈路量 |
| 【新】\(m^{q}_{u,s,v}(t)\) | **發射模式**：發射前由同一份因果可得（餘裕調整名目）視圖選出的模式。當目標模式已是最低模式、沒有回退空間時，\(m^{q}\) 取宣告狀態 `NO_MODE`（不發射任何可記帳模式） | 上標 \(q\)＝選擇時視圖（§10.14.2）；記入的位元是 \(m^{q}\) 的位元。`NO_MODE` 是狀態 token，不是模式索引值 |
| 【新】\(m^{o}_{u,s,v}(t)\) | **實現解碼結果**：實現 SINR 清過 \(\gamma_{m^{q}}\) 時 \(m^{o}=m^{q}\)，否則 \(m^{o}=0\)（不記入位元） | 上標 \(o\)＝outcome。⚠ 本字形為本表新增：密封宣告（v1.8 §8、stage-4h ACM 更正）固定了「三個物件必須分開報告」但未固定字形 |
| 【新】\(\gamma^{-}=-1.4418\) dB | PHY 可解碼門檻 | 上標 \(-\) 為單一符號，沿用 \(G^{R}_{-}\)、\(\theta^{R}_{-}\) 的下界慣例 |
| 【新】\(\gamma^{\star}=7.528\) dB | 固定 SINR 架構（a-γ）的常數目標 SINR（8PSK 2/3，含 roll-off 與餘裕修正） | 只屬 a-γ 敏感度格，**不進入 a-r 主模型** |
| 【新】\(\Delta t=30.08\ \mathrm{s}\)、\(k\in\{0,\dots,47\}\) | 決策區間長度與步內積分邊界索引（48 個邊界、47 個子區間） | s；\(k\) 與波茲曼常數 \(k_B\) 靠下標 \(B\) 區分 |

繼任者的名目功率律（取代第 5 節的 previous-step 遞推，memoryless）為

\[
p_{u,s,v}(t)=\min\!\left\{
p^{+},\;
\frac{\Gamma_r\!\left(U_{s,v}(t)\right)\left(\sigma^{2}+I_{u,s,v}(t,\theta_{u,s,v},\theta_3)\right)}
     {H_{u,s,v}(t)\,G^T\!\left(\theta_{u,s,v}(t),\theta_3\right)}
\right\},
\]

其中 \(H_{u,s,v}G^T(\theta_{u,s,v},\theta_3)\) 即密封宣告的 \(\hat h_u\)（本表不使用 hat）。
角度經由 \(G^T\) 進入功率，占用經由 \(\Gamma_r(U_{s,v})\) 進入功率；同時服務的鏈路以
歷史無關的初始化耦合求解，並附凍結容差與殘差認證。若在上限處沒有任何模式能達成
速率目標，該使用者標記為速率目標不可行、以 \(p^{+}\) 發射，實際部分交付、干擾與能量
照常計入，不做修剪或重排；PHY 服務定義（可解碼）不因此改變，速率目標達成率另行報告。

**速率回退的結構性後果（必須在正文明說為一項選擇）。** v1.9 §1 禁止把餘裕回解為
發射功率，改以降低發射模式取得保留量，因此可靠度是用頻譜效率買的、不是用焦耳買的。
其推論無法迴避：**目標模式已經是最低模式的使用者沒有可回退的對象，任何保留量都會
使其 \(m^{q}=\) `NO_MODE`**。由於目標模式由占用 \(U_{s,v}\) 經 \(\Gamma_r\) 決定，
低占用即低目標模式、低目標模式即無回退空間；\(m^{q}=\) `NO_MODE` 的使用者仍以其
計算功率發射、仍貢獻干擾、仍消耗 PA 能量，也仍留在可用度分母中。

### 10.14.2 選擇時視圖、宣告衰落與餘裕規則

| 符號 | 定義 | 單位／限制 |
|---|---|---|
| 【新】\(R\)（無上下標） | 萊斯功率衰落 | 無因次；只出現在宣告衰落乘積式，與 \(R_{u,s,v}\)、\(R^{\star}\)、\(R^{+}\)、\(R_E\)、\(R_b\) 靠上下標與所在式子區分 |
| 【新】\(X\)（正體、無下標） | dB 域高斯遮蔽損耗 | dB；與斜體 \(x_{u,s,v}\)、花體 \(\mathcal X\) 字重／大小寫皆不同 |
| 【新】宣告衰落乘積 \(R\cdot 10^{-\left(X+L_c(\alpha)\right)/10}\) | 萊斯功率衰落 × dB 域高斯遮蔽 × 決定性閃爍的完整乘積；\(q^{\alpha}\) 即取自此乘積的 \(\alpha\) 分位 | 無因次。⚠ 密封宣告 v1.9 §3 在散文中把此乘積寫作 \(G\)；本表**不採 \(G\) 字形**（R-2 已裁定「\(G\) 加單字母上標＝增益」），改以乘積式直書，衝突已登記 |
| 【新】\(q^{\alpha}_{u,s,v}(t)\) | \(\alpha\) 分位通道增益因子：鏈路在其**實際仰角** \(\alpha_{u,s}(t)\) 上，宣告衰落乘積的 \(\alpha\) 分位除以其名目值；主要水準 \(\alpha=0.10\)，診斷掃描 \(\alpha\in\{0.05,0.10,0.25\}\)。以密封程序計算：於該鏈路仰角抽取 200 000 次宣告乘積、固定導出種子、依 0.5° 仰角分箱與 \(\alpha\) 快取；KAT 將快取分位與直接評估比對至相對 \(10^{-3}\) | 無因次、\(\le 1\) 的保留量因子。稱為「**預先指定的第十百分位通道增益評分規則**」，**不得**稱為「標準 90 % 可用度鏈路預算慣例」（v1.7 §1 已撤回該說法） |
| 【新】\(\gamma^{q}_{u,s,v}(t)\) | 選擇時視圖的預測 SINR：\(q^{\alpha}_{u,s,v}H_{u,s,v}G^T(\theta_{u,s,v},\theta_3)\,p_{u,s,v}\big/\left(\sigma^{2}+I_{u,s,v}\right)\) | 分位**只乘在想要鏈路的預測接收端**；干擾與雜訊維持名目值 |
| 【新】上標 \(q\)（視圖標記） | 同一式在選擇時視圖求值：發射功率、干擾與能量皆取名目值，只有想要鏈路的預測接收端乘上 \(q^{\alpha}\)；服務、ACM 模式、位元與能量在該視圖下內部一致地重算 | 適用於 \(\Omega^{q}\)、\(d^{q}_i\)、\(\Psi^{q}_{\mathcal K}\)、\(\gamma^{q}\)、\(m^{q}\) |

兩項構造性限制（v1.9 §1–§2，均為已確認缺陷的更正）：

1. **餘裕不得回解為發射功率。** 執行與預測的發射功率一律由名目增益算出；分位只進入
   想要鏈路的預測接收端。否則 \(p_m=p_N/q\)，鏈路又剛好打回門檻，餘裕只換來更多功率
   與干擾，並改變上限處的可行性。
2. **分位只作用於想要鏈路。** 對干擾鏈路同步套用只會縮放雜訊
   （\(S/(N/q+I)\)），對干擾受限情形反而不保守。

已執行的物理、標籤、承諾組態的評估與 48 邊界端點一律使用實現衰落，不受本視圖影響。

### 10.14.3 組態層剩餘、分解與參考點

| 符號 | 定義 | 單位／限制 |
|---|---|---|
| 【新】\(\Omega(a)=B(a)-\lambda E(a)-\Phi(a)\) | 組態 \(a\) 的整網剩餘（結果視圖）：整網交付位元、乘以凍結 bits-per-joule 乘子的整網能量、以及**在同一式中只計一次**的 \(\Phi\) 計價換手／QoS 偏好 | bit；於實現的 48 邊界端點求值 |
| 【新】\(\Omega^{q}(a)\) | 同一式在選擇時視圖求值（§10.14.2） | bit；**兩個分解永不混用**：\(\Omega^{q}\) 只產生機制統計，\(\Omega\) 只產生標籤、證書與端點，每個報出的量必須標明出自哪一個 |
| 【新】\(B(a)\)、\(E(a)\) | 組態 \(a\) 的整網交付位元與整網能量 | bit、J；沿用 §10.13.1 的 profile-argument 解法，\(B^{w}\) 仍是頻寬 |
| 【新】\(\Phi(a)\)、\(\Phi_u(t)\) | \(\Phi\) 計價的換手／QoS 偏好；\(\varphi_1=0.5\kappa\)（同星換束）、\(\varphi_2=1.0\kappa\)（跨星） | bit（κ 單位）；計價的是**訊令／QoS 偏好**，不是時間也不是焦耳；與換手率並列為 co-primary QoS 結果 |
| 【新】\(\lambda\) | 凍結 bits-per-joule 乘子（＝校準時的參考 EE） | bit/J；沿用 §10.13.1，不得換成 outcome 後的價格 |
| 【新】\(\kappa\) | 三路共用的輸出尺度（bits per user-step） | bit；若引擎以 bits per user-second 呈現，換算恰為 \(\times\,30.08\) s |
| 【新】\(a^{0}\) | 參考提案：\(Q_1+Q_2\) 逐使用者 argmax 且已驗證為聯合合法的組態 | 與 \(b^{-}(t)\)（前一次承諾的關聯）是**兩個不同的參考**，永不混用 |
| 【新】\(b^{-}(t)\)、\(b^{-}_{-i}(t)\) | 前一次承諾的關聯，以及排除使用者 \(i\) 後的背景 | 只供換手／\(\Phi\)／事件記帳與 Q1／Q2 的歷史欄位 |
| 【新】\(\mathcal K\subseteq\mathcal U\)、\(K\) | 相對於 \(a^{0}\) 的變動使用者集合與其元素數 | 花體集合＋同字母正體大寫基數；密封宣告寫作 \(A\)，本表採花體 \(\mathcal K\) |
| 【新】\(d_i(a)=\Omega\!\left(a_i,a^{0}_{-i}\right)-\Omega\!\left(a^{0}\right)\) | 單邊增量：在 \(a^{0}\) 上只移動使用者 \(i\) 所得的整網剩餘變化 | bit。**再定義**：不再等於 LC-SRS 的 \(\ell_i+e_i\)；因整網剩餘已含所有非焦點使用者的位元與焦耳變化，繼任者的 C3 標的**不含 \(e_i\) 項** |
| 【新】\(D(a)=\sum_{i\in\mathcal K}d_i(a)\) | 可加單邊價值總和（即組態層的 C1 分數） | bit；與第 3.1.2 節的天線口徑 \(D\) 靠引數區分 |
| 【新】\(\Psi_{\mathcal K}\) | 交互作用殘差：\(\Omega\!\left(a_{\mathcal K},a^{0}_{-\mathcal K}\right)-\Omega\!\left(a^{0}\right)-\sum_{i\in\mathcal K}d_i\)（即組態層的 C3 分數） | bit；計算成本為 \(K+2\) 次評估，故**對任意大小的選定聯盟都計算** |
| 【新】\(d^{q}_i\)、\(\Psi^{q}_{\mathcal K}\) | 上述兩量的選擇時視圖版本 | 只產生機制統計。⚠ 密封 v1.7 §2 以上標 \(m\) 標示同一視圖（\(d_i^{m},\Psi_A^{m}\)），本表依權威順序採上標 \(q\)，衝突已登記 |
| 【新】\(a^{1}\)、\(d^{1}_i\)、\(\Psi^{1}_{\mathcal K}\) | \(a^{1}\)＝認證單邊最適：以與協調器完全相同的名目評估器、快照、守衛與目標，對**完整合法集合**反覆執行精確單邊最佳回應直到不存在改善的單邊移動，只在最終組態做一次原子承諾，並附完整鄰域終止證書與迭代次數。\(d^{1}_i\)、\(\Psi^{1}_{\mathcal K}\) 是在該錨點重錨的兩量 | 依構造 \(d^{1}_i\le 0\)，故任何有改善的聯合脫離必須滿足 \(\Psi^{1}_{\mathcal K}>0\)。⚠ 存在性探針與 v1.6 §3 記為 \(a^{1}=u\)、\(d_i^{u}\)、\(\Psi_A^{u}\)；本表依權威順序採上標 \(1\)（與 \(a^{0}\)、\(a^{\star}\) 同族），\(u\) 為引擎別名，衝突已登記。**未附終止證書者**只是作業層比較器，須標為 budget-limited，其對比不具承載力 |
| 【新】\(\Psi^{f}_{\mathcal K}\) | 學習型集合條件化交互作用頭的輸出：對 \(\mathcal K\) 置換不變，錨定條件 \(\Psi^{f}_{\varnothing}=\Psi^{f}_{\{u\}}=0\) 由構造保證 | **不使用 hat**（§1 規則 5）；上標 \(f\) 指向 §10.13.4 已在案的共享 scorer \(f\) |
| 【新】\(\mathcal X(t)\)、\(\mathrm X\) | 有界候選組態目錄與其大小 | 花體 \(\mathcal X\) 未被使用；⚠ 密封契約 §A2 以花體 \(\mathcal C\) 稱之，與本表候選動作索引域 \(\mathcal C\) 衝突，不採用 |
| 【新】\(a^{d}\)、\(a^{\psi}\) | 只用可加分數 \(D\) 選出的組態，與含交互作用項選出的組態 | 上標為單一（希臘）字母；引擎記為 `a_D`／`a_C` |

分解恆等式（KAT 驗證，另有一條不含 \(\Phi\) 的物理恆等式）為

\[
\sum_{i\in\mathcal K}d_i+\Psi_{\mathcal K}=\Omega\!\left(a_{\mathcal K}\right)-\Omega\!\left(a^{0}\right).
\]

逐使用者 Shapley 分攤（成對即 \(\Psi/2\)）**只作報告且只在 \(K\le 4\)**；\(K>4\) 時 receipt
記 `credit_split = NOT_COMPUTED_LARGE_SET`。任何選擇或驗證步驟都不得依賴逐使用者分攤。
目標落差註記：\(\lambda\) 在校準時凍結，故 \(\Omega>0\) 本身不蘊含實現 pooled
\(\Sigma B/\Sigma E\) 較高；所有宣稱與證書一律以實現 pooled 比值陳述。

### 10.14.4 每臂排序鍵（四臂各一把）

任何一臂都不得以它已被移除的分數進行排序、修剪、可行性守衛或 tie-break。四把鍵、
次鍵與所屬臂如下；臂以單一數字下標標示（\(0\)＝FULL、\(1\)＝DROP_C1、\(2\)＝DROP_C2、
\(3\)＝DROP_C3），上標 \(q\) 表選擇時視圖。

| 符號 | 所屬臂 | 即時排序鍵 | 次鍵 |
|---|---|---|---|
| 【新】\(\Omega^{q}_{0}(a)\) | FULL | \(D^{q}(a)+\Psi^{q}_{\mathcal K}(a)\) | C2 延續值 |
| 【新】\(\Omega^{q}_{1}(a)\) | DROP_C1 | \(\Psi^{q}_{\mathcal K}(a)\) | C2 延續值 |
| 【新】\(\Omega^{q}_{2}(a)\) | DROP_C2 | \(D^{q}(a)+\Psi^{q}_{\mathcal K}(a)\) | 固定決定性規則（不得用 C2） |
| 【新】\(\Omega^{q}_{3}(a)\) | DROP_C3 | \(D^{q}(a)\) | C2 延續值 |

⚠ 本組字形為本表新增：密封 v1.9 §4 以文字式（`C1_m + C3_m` 等）固定了四把鍵的內容
與「不得以被移除的分數排序」的規則，但未固定符號；本表以既有的 \(\Omega\)、\(D\)、
\(\Psi_{\mathcal K}\) 組合成鍵，未引入新字母。C2 以 tie-break 進入集合層選擇器
（相對容差 \(10^{-9}\)），故在唯一最大值的情形下 FULL 與 DROP_C2 會重合，
集合層 C2 邊際為零是**可接受的結果**，不得以 Q2 對提案 \(a^{0}\) 的另一個效果替代；
C2 在物理矩陣中的證書是**預測有效性**，不是選擇邊際。

### 10.14.5 機制統計、比較臂與准入狀態

| 符號 | 定義 | 單位／限制 |
|---|---|---|
| 【新】\(\Upsilon\)、\(\Upsilon(t)\) | 淨避碰值：在匹配錨點上，以相同錨點、目錄、餘裕規則與 C2 規則，\(\Upsilon=\left[\Omega\!\left(a^{\psi}\right)-\Omega\!\left(a^{d}\right)\right]/\kappa\)。同時報出兩個分量（皆不截斷）：已避免的交互作用損失 \(\Psi(a^{\psi})-\Psi(a^{d})\)，與被犧牲的單邊價值 \(D(a^{d})-D(a^{\psi})\) | 無因次（κ 單位）。\(\Upsilon\) 是**機制證書**，不是效能證書；作業層證書仍是實現 pooled EE 對認證單邊比較器的對比 |
| 【新】反轉頻率 | \(D(a^{d})>0\) 但 \(D(a^{d})+\Psi(a^{d})<0\) 的錨點比例 | 比例；與 \(\Upsilon\) 一併報出 |
| 【改】\(\eta^{N}\) | 實現 pooled ratio-of-sums EE：完整範圍總 delivered bits 除以總 network energy | bit/J。V0.25 起是**唯一**的 EE 宣稱量（\(\eta_{u,s,v}\) 退出，見 §9.1）；每次出現都必須附能量邊界句 |
| 【新】\(\delta=+0.5\%\) | 宣稱邊際：\(\mathrm{EE}_{\text{FULL}}/\mathrm{EE}_{\text{DROP}}-1\ge\delta\)，且 95 % 下界（2.5 分位）亦須高於 \(\delta\) | 相對增益；與服務波束索引 \(\delta_u(t)\) 靠下標區分 |
| 【新】\(\Delta^{\star}=+2\%\) | 規劃替代假說（power 計算用），不是宣稱邊際 | 相對增益 |
| 【新】准入三分狀態 | `ADMIT_FULL`／`ADMIT_C1C2`／`NOT_ADMITTED`（見下） | **決策狀態 token，不是公式符號**；不得寫成上下標 |

准入三分（v1.9 §6 取代 v1.6 §4，已重述為單調形式；只適用於主格 a-r0）：

| 狀態 | 條件 |
|---|---|
| 【新】`ADMIT_FULL` | 全部承載性證書通過：S0 對 BASE 的**實現**增益 \(\ge +1\%\)；S0 優於**認證** S_UNI 且超出認證數值誤差；C1 的 oracle 邊際為正且超出數值誤差；C3 的交互作用項具決策相關性（協調器的選擇在可報告的非平凡比例錨點上不同於可加選擇，且實現對比為正）；C2 的預測有效性成立；QoS／有效性／期限皆通過 |
| 【新】`ADMIT_C1C2` | 除 C3 條件未達成外與上同：准予訓練，C3 以**被評估的一層**帶入，其學習結果明確標記為缺 oracle 證書，是比 `ADMIT_FULL` 更弱的宣稱 |
| 【新】`NOT_ADMITTED` | C1 的 oracle 邊際或 QoS／有效性／期限條件失敗 → 進入應變階梯 rung 1（regimes R1–R7，只能作「在 regime R_k 之下」的條件式陳述） |

臂、選擇器與設定的識別碼（**非公式符號**，不得作為上下標進入公式）：

| 類別 | 識別碼 | 說明 |
|---|---|---|
| 【新】因子臂 | `FULL`、`DROP_C1`、`DROP_C2`、`DROP_C3`、`ALL_NEUTRAL` | 對應 §10.14.4 的四把鍵與中性來源對照 |
| 【新】報告臂 | `ONLY_C1`、`ONLY_C1C2`、`BASELINE` | CH5 掃描圖的累積曲線與外部基線；不進入任何證書或准入分支 |
| 【新】選擇器 | `BASE`（載體提案 \(a^{0}\)）、`S0`（以精確 \(\Psi_{\mathcal K}\) 選）、`S3`（以 \(\Psi^{f}_{\mathcal K}\) 選）、`S_UNI`（\(a^{1}\)，須附終止證書）、`NULL`、`random-feasible`、`nominal-greedy` | `NULL` 逐步等同 `BASE` |
| 【新】架構設定 | `a-r0`（主格，TDM 速率目標）、`a′-r0`（FDM）、`a-γ0`（固定 SINR）、`b0`（固定 EIRP）、`a′-γ0` | 主格以外一律為探索性敏感度，不能改變准入決定或主宣稱 |
| 【新】處置與 regime | `0`／`S`／`H`／`SH`／`T`、診斷用 `U-cap`／`U-margin`；`R1`–`R7` | 25 個 primary-eligible 設定 + 6 個診斷設定 = 31 個設定 |

### 10.14.6 引擎與密封宣告名稱對照（不得進入公式）

程式欄位名、receipt key 與密封宣告的英文散文記法不是紙面符號。下表只作一對一對照；
凡多字母上下標或 hat 一律不得出現在公式中。

| 引擎／宣告名稱 | 紙面符號 | 備註 |
|---|---|---|
| 【新】`eta_ref`、\(\eta_{\mathrm{ref}}\) | \(\lambda\) | 多字母下標；\(\lambda=B_{\text{校準}}/E_{\text{校準}}\) 的識別式以文字敘述 |
| 【新】`kappa` | \(\kappa\) | \(\kappa=B_{\text{校準}}/(U\cdot N_{\text{校準}})\) 亦以文字敘述，不引入 `ref` 下標符號 |
| 【新】\(\hat h_u\) | \(H_{u,s,v}(t)\,G^T(\theta_{u,s,v},\theta_3)\) | 禁用 hat；名目值 |
| 【新】\(\hat I_u\) | \(I_{u,s,v}(t,\theta_{u,s,v},\theta_3)\) | 禁用 hat；選擇時視圖維持名目值 |
| 【新】\(N_0W\)、\(N\) | \(\sigma^{2}=k_BTB^{w}\) | 本表不使用 \(N_0\)、\(W\) 字形 |
| 【新】\(W\) | \(B^{w}\) | 頻寬；\(W\) 在本表僅為 retired 的視窗長度 |
| 【新】\(n_b\) | \(U_{s,v}(t)\) | 波束占用人數 |
| 【新】`SE_m` | \(\nu_m\) | 頻譜效率 |
| 【新】`p_sat`＝5.2178 W、`eta_max`＝0.35 | \(p^{s}\)、\(\xi^{+}\) | \(P^{p}_{s,v}=\sqrt{p_{s,v}p^{s}}/\xi^{+}\) 與 `PA_supply` 完全等價；\(\xi^{+}\) 讀作**飽和效率** |
| 【新】`P_circuit`＝0.338 W、`P_bb`＝0.200 W | \(P^{c}\)、\(P^{b}\) | 沿用 \(P^{f}=\sum_s\left(N^{a}_sP^{c}+\mathbb 1\{N^{a}_s>0\}P^{b}\right)\) |
| 【新】`V_CA` | \(\Upsilon\) | 多字母下標 |
| 【新】\(\hat\Psi_\theta\) | \(\Psi^{f}_{\mathcal K}\) | 禁用 hat；\(\theta\) 已是角度 |
| 【新】\(A\)（changed-user set） | \(\mathcal K\) | 花體集合 |
| 【新】`u`（certified unilateral optimum） | \(a^{1}\) | \(d_i^{u}\to d^{1}_i\)、\(\Psi_A^{u}\to\Psi^{1}_{\mathcal K}\) |
| 【新】`a_D`、`a_C` | \(a^{d}\)、\(a^{\psi}\) | |
| 【新】\(F\)、\(G\)（探針） | \(\Omega(a)\) | \(F\)＝分數、\(G\)＝加上訊令計價後的協調器目標；⚠ 密封來源對 \(\Phi\) 是否在 \(F\) 之內不一致，見 §10.11 與碰撞稽核 |
| 【新】\(\mathcal C\)（catalogue，契約 §A2） | \(\mathcal X(t)\) | 與本表候選動作索引域 \(\mathcal C\) 衝突 |
| 【新】\(\mathcal M\)（nominal model，契約 §A2） | —（以文字敘述） | 與 ACM 模式集合 \(\mathcal M\) 衝突，不給符號 |
| 【新】`I_heads`、`I_coordinator`、\(Z_t\) | —（以文字敘述） | 多字母下標；且 \(I\) 已是干擾 |
| 【新】\(\Sigma g_I\)、\(\Delta I_N\)、\(\Delta c_h^{N}\) | —（以文字敘述） | 開發切片與 C2 三路診斷量，由 \(\Upsilon\) 的兩個分量與預測／實現落差報告取代 |
| 【新】`m_target`、`m_tx`、`realised_outcome` | \(m^{r}\)、\(m^{q}\)、\(m^{o}\) | 三者每 user-step 分別輸出 |

### 10.14.7 Active 狀態與邊界

V0.25 的物理與方法記法已凍結為 paper-visible draft，**gate outcome 尚未開啟**：
a-r0 的准入、C1／C2／C3 的邊際、S0 對認證 S_UNI 的對比、學習層的價值與 EE efficacy
都不由本表推論。第 10.12、10.13 節的 \(\zeta\)、\(D^{o},D^{t},D^{a}\)、\(H^{c}\)、
\(z_{3,i}\)、\(y_i\)、\(x^{0},x^{1},x^{2},x^{c}\) 僅作 historical／retired provenance，
不得與本節的 \(\Omega\)、\(d_i\)、\(\Psi_{\mathcal K}\)、\(m^{r},m^{q},m^{o}\) 或
\(q^{\alpha}\) 混用。所有 EE 陳述一律附能量邊界句：

> 「每焦耳**已建模之部分酬載直流能量**所成功解碼的前向下行資訊位元；該能量涵蓋
> 使用者鏈路 PA 供電、宣告的每波束鏈路電路與宣告的共用處理增量，並明列閒置狀態；
> 太空載具匯流排、未建模酬載功能、饋線與星間鏈路、地面與終端能量皆在本度量之外。」


---

## 2026-08-22 汰換紀錄

| 移除的符號 | 依據 |
|---|---|
| $v_{\max}$ | 使用者裁決刪除（SDD-01 §2.2）。⚠ 2026-08-22 更正:當時記「改由 Table I 的 $V=7$ 表示」是錯的，見下列 $V_b$ |
| $V_b$（同時輻射波束數上限，式 3.3 舊版） | **刪除**（2026-08-22 作者裁決）。理由:(1) 原論文 $V=7$ 是 $|\mathcal{V}|$ 而非上限，其 7 道恆常全亮，`G6-VERBATIM-blind-audit-2026-07-15.md:62` 逐字「Paper: no cap」,(2) 與 ch3 既有散文「$z=1$ 當且僅當 $U>0$」直接矛盾,(3) 與 P3（$\min\sum U^2$）衝突，上限 $k$ 使 P3 下界抬高為 $n^2/k$。式 (3.3) 改為 $U_{s,v}$ 定義，式 (3.4) 改為啟用規則 |
| $\mathcal{F}$、$F$、$T_k$ | 射頻槽索引域，隨 $v_{\max}$（$F=L_wv_{\max}$）與舊 $r_3$ 一併消失（SDD-01 §2.1 B13） |
| $N(t)$ | 其定義為「填入 $F$ 個槽位的數量、$0\le N(t)\le F$」，依賴已刪除的 $F$ |
| $\widetilde R_{s,v}$、$\widetilde R_{s_k,v_k}$ | 舊 $r_3$ 的 beam aggregate throughput。B13 改為計數式 $r_{3,u}=-U_{b_u}$，不再需要 |
| $m^e_{u,c}$ | **刪除**(2026-08-22 使用者裁決,原話「不用統計了直接刪 mask」)。式 (4.5a) 改為 $x=a\cdot z$,「選了不一定連得上」改由**逐波束功率可行性**($p_{\mathrm{req}}>p^{+}$ 判 infeasible)承擔,該機制有出處且已實作。⚠ 先前一版曾記為「保留為環境端帳務」,那是助理裁決、非使用者授權,已撤回 |
| $\Delta_s$ | 定義為「超出前 $v_{\max}$ 個波束名額的偏好質量」，依賴已刪除的 $v_{\max}$ |

| $\chi_{u,c}$、$s^{\chi}_u$、$\psi_{u,i}$、$\mu_i$、$\sigma_i$、$\epsilon_z$、$\tilde s_u$ | **從論文完全移除**(2026-08-22 使用者裁決:「不刪掉先保留」指的是**程式**,論文要刪)。§4.2 整節與式 (4.7)–(4.9) 已刪,式號 4.10–4.16 重編為 4.7–4.13,網路輸入回到 $s_u(t)$(112 維)。**程式保留為消融開關,論文任何章節不得出現。** |
| $\epsilon_h$、$\epsilon_V$ | 隨需求功率反推與容量懲罰刪除,ch5 表已移除該列 |

**保留於程式、不入論文**:$\chi$ 與跨使用者正規化(B8 修訂 2026-08-22)。

**權威**：`docs/research/ee-definition-cleanup/2026-08-17-simplified-ee-symbol-table.md`。

| $a_u^{d,*}(t+1)$（共用純量化下一步動作） | **刪除**（2026-08-22，決策 B1）；TD target 改回原論文式 (16) 的 vanilla 形式，每個目標各自在自己的目標網路取 max，不再有跨目標共用的單一動作 |

| 容量懲罰整組符號 $V_u^M$、$\widetilde V_u^M$、$\pi_u$、$\Pi_{s,v}$、$\tau$（softmax 溫度）、$L$、$\lambda$、$\epsilon_V$ | **刪除**（2026-08-22）；容量懲罰整節（原 §4.5 與式 4.15–4.17、圖 4-8）已自論文移除。已逐一驗證正文零殘留（$\lambda$、$L$、$\epsilon_V$ 皆 0 命中）；⚠ 正文仍有 $\tau_{u,s,v}$，那是 segment 起始時間步，**與此處的 softmax 溫度 $\tau$ 同字母不同義** |
