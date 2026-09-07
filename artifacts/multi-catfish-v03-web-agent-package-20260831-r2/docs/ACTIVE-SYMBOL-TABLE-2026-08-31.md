# 單一 SINR 角度感知 EE 正式符號表

- **狀態：** `ACTIVE SYMBOL AUTHORITY`
- **原始日期：** 2026-08-17
- **正式升格日期：** 2026-08-19
- **集合記法修訂：** 2026-08-20 —— 集合符號改回花體（𝒰、𝒮、𝒱、𝒞、ℱ），集合大小改回同字母正體大寫（U、S、V、C、F），取代原本「不使用花體、以 N_U 前綴或 \(|U|\) 表集合大小」的規定。理由：花體集合＋正體大寫基數是 MODQN（Sun et al.）、HOBS（Chen et al.）與一般 RL 文獻的通用慣例，貼近此慣例才不會讓 CH4／CH5 簡報的記法反而偏離普遍論文寫法；技術上花體字母可用 Unicode Mathematical Alphanumeric Symbols（Cambria Math 內建，PowerPoint／Word 方程式編輯器 Scripts 分類即可插入）直接嵌入原生 OMML，不需要額外字型或樣式標記，先前判定「不可行」的疑慮已排除。
- **適用範圍：** 新版論文公式同步、Phase-C 英文 CH4／CH5 概念簡報與未來模擬器對照
- **同步邊界：** 本表、正式公式規格、三下標裁決、論文 base sources、三份 DOCX 與 production Family-B runtime／consumer 已完成 previous-step recurrence parity；fresh calibration、prereg 與 episode-0 training 仍須另行過關

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
6. 概念公式不放工程功率 cap 或 `min`／`max` projection；每個新 served segment 的唯一起始條件是 \(p^{0}=p_{\max}/2=0.825\,\mathrm{W}\)。
7. 符號在第一次出現時定義；同一章後續不重複逐字解釋。
8. 本表只約束 CH4／CH5 的共用物理與 EE 公式符號，不縮減完整章節內容；CH4 在 throughput 後仍須使用現行論文符號說明 P1／P2／P3 與 baseline MODQN solution process。
9. Multi-Catfish MCRL V0.3 的方法章、圖與簡報使用第 10.12 節的擴充符號；第 10.8--10.9 節的舊雙代理、舊 reward 與 target-network 記法僅供歷史版本，不得混入 V0.3。

## 2. 核心最小符號集合

```text
U, S, V, u, s, v, t, tau_(u,s,v),
x_(u,s,v), d_(u,s,v), theta_(u,s,v), boldtheta,
mathbf(v)_(u,s,v), mathbf(r)_(u,s,v),
G^T, H_(u,s,v),
G_0, F, theta_(3dB), mu, J_1, J_3,
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
| \(G^T(\theta,\theta_{3dB})\)、\(G_0\) | 發射端角度增益函數與波束中心增益；\(G^T(\theta,\theta_{3dB})=G_0F(\theta,\theta_{3dB})\)，且 \(G^T(0,\theta_{3dB})=G_0\) | \(T\) 表示 transmit；逗號分隔可變角度與固定波束寬參數 \(\theta_{3dB}\) |
| \(F(\theta,\theta_{3dB})\)、\(\theta_{3dB}\) | 發射角度型樣（唯一一個），逐字採用 HOBS 式 (3) 的 \(J_1/J_3\) 型樣，在 \(\theta=0\) 自然等於 1；以及 3 dB 波束寬度 | 式 (3.7) |
| \(\mu(\theta,\theta_{3dB})\)、\(J_1\)、\(J_3\) | Bessel 型樣的角度參數與固定 Bessel 項；角度參數固定為 \(2.07123\)（HOBS 式 (3)），不是額外 runtime 控制 | 式 (3.8) |
| \(H_{u,s,v}(t)\) | 不直接承載 wanted-link 角度型樣的線性鏈路功率因子：由 \(L_{u,s,v}(t)\) 與 \(G^R_{u,s,v}(t)\) 一層展開；在 SINR numerator 中直接與 \(G^T(\theta_{u,s,v},\theta_{3dB})\) 相乘 | 式 (3.10) |
| \(L_{u,s,v}(t)\) | 路徑／衰落損耗層：\(L_f(d_{u,s,v}(t),f_c)+L_g(\alpha_{u,s}(t))+L_c(\alpha_{u,s}(t))+L_s\!\left(\alpha_{u,s}(t)\right)\)，即 HOBS 式 (1) 的四項 | 式 (3.10b) |
| \(G^R_{u,s,v}(t)\) | 接收端線性增益；是 H 一層展開中的明示因子。以軸心增益扣除離軸損耗表示，截止於 \([G_{R,\min},G_{R,\max}]\) | 式 (3.10)、式 (3.10c) |
| \(\theta^{R}_{u,s}(t)\) | 使用者接收天線指向與第 \(s\) 顆衛星方向之間的夾角（度）；與發射端偏軸角 \(\theta_{u,s,v}\) 分屬鏈路兩端，沿用 \(G^T\)／\(G^R\) 的 T／R 上標慣例；不帶波束下標 \(v\)（假設接收指向固定對準服務衛星） | 式 (3.10c) |
| \(A_R\)、\(B_R\)、\(G_{R,\max}\)、\(G_{R,\min}\) | 式 (3.10c) 的地球站參考型樣參數與上下限。\(A_R\)、\(B_R\)、\(G_{R,\min}\) 同出 ITU-R S.465-6 `recommends 2` 的**同一條式子**，在 \(48^{\circ}\) 連續銜接（\(32-25\log_{10}48=-10.03\)），非三個獨立設定；\(G_{R,\max}=35\) dBi 取自同級 0.6 m 使用者終端的降額值 | 式 (3.10c)、表 5-2 |

論文正文、概念簡報與 `/` legacy simulator 前端都展開到上述同一層，以便每個可調參數都能對應到 H 或 G^T；三者只允許排版不同，不允許公式、符號或可調參數不同。更深的自由空間模型、Bessel 近似誤差、接收天線量測與 Rician 校準細節不屬於這個公開主公式層級，不能讓它們重新擴張主公式。

> **✅ 深度上限已裁決（2026-08-21，作者選 (a)）。** 式 (3.10c) 的接收型樣**保留於公開層**。
>
> 理由：本節下一段的上限，其原意是防止主公式往下長進**沒有公開標準、沒有固定參數的實作細節**
> （自由空間模型細節、Bessel 近似誤差、接收天線量測、Rician 校準）。式 (3.10c) 不屬該類——
> 它是**標準文件明載的式子加三個固定常數**，與 \(G^T\) 收下 HOBS 式 (3) 同級。
> 上限的措辭因此擴充，以符合其自身用意。
>
> 被否決的 (b)：刪除式 (3.10c) **並**把 \(A_R\)、\(B_R\)、\(G_{R,\max}\)、\(G_{R,\min}\) 移出表 5-2。
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
G^T(\theta,\theta_{3dB})=G_0F(\theta,\theta_{3dB}),
\qquad
G^T(0,\theta_{3dB})=G_0,
\qquad
F(0,\theta_{3dB})=1.
\]

發射型樣的角度參數與 pattern 為

\[
\mu\!\left(\theta,\theta_{3dB}\right)=2.07123\frac{\sin\theta}{\sin\left(\theta_{3dB}/2\right)},
\qquad
F\!\left(\theta,\theta_{3dB}\right)=
\left[
\frac{J_1\!\left(\mu\!\left(\theta,\theta_{3dB}\right)\right)}{2\mu\!\left(\theta,\theta_{3dB}\right)}
+\frac{36J_3\!\left(\mu\!\left(\theta,\theta_{3dB}\right)\right)}{\left[\mu\!\left(\theta,\theta_{3dB}\right)\right]^{3}}
\right]^2.
\]

\(2.07123\) 是 HOBS 式 (3) 的固定角度參數；\(F\) 在 \(\theta=0\) 自然等於 1，不需要額外正規化常數。\(G_0\) 與 \(\theta_{3dB}\) 是天線／情境參數。這些展開不改變主式的 \(pHG^T\) 結構，也不產生小寫 \(h\)。

## 5. 角度感知發射功率

| 符號 | 定義 | 備註 |
|---|---|---|
| \(p_{u,s,v}(\tau_{u,s,v},\theta_{u,s,v}(\tau_{u,s,v}),\theta_{3dB})=p^{0}\) | served segment 起始步的 RF 發射功率 | 正文只用符號 \(p^{0}\)；**數值僅出現在第 5.1 節**(0.825 W = \(p_{\max}/2\),2026-08-22 由 2 W 修正,見下)。每個新 segment 重新起始，不保留 inactive-link cache |
| \(p^{0}\) | 段起始發射功率(scenario 常數) | 單字母上標 `0` 表 segment 起始，**不是指數**。與 legacy 的 \(P_0\)(大寫、下標、PA 飽和輸出)不同,見第 11 節 |
| \(p_{u,s,v}(t,\theta_{u,s,v}(t),\theta_{3dB})\) | 由前一步同一 physical link 的 RF power 與角度增益比遞推的實際鏈路功率 | 只有 \(x_{u,s,v}(t-1)=x_{u,s,v}(t)=1\) 時適用 |

正式功率律為

\[
p_{u,s,v}\!\left(t,\theta_{u,s,v}(t),\theta_{3dB}\right)
=p_{u,s,v}\!\left(t-1,\theta_{u,s,v}(t-1),\theta_{3dB}\right)
\frac{G^T\!\left(\theta_{u,s,v}(t-1),\theta_{3dB}\right)}
     {G^T\!\left(\theta_{u,s,v}(t),\theta_{3dB}\right)},
\qquad
x_{u,s,v}(t-1)=x_{u,s,v}(t)=1,
\quad G^T\!\left(\theta_{u,s,v}(t),\theta_{3dB}\right)>0.
\]

每個 segment 先滿足
\[
p_{u,s,v}\!\left(\tau_{u,s,v},\theta_{u,s,v}(\tau_{u,s,v}),\theta_{3dB}\right)=p^{0}.
\]

在沒有 continuity break 的前提下，重複代入才得到
\[
p_{u,s,v}\!\left(t,\theta_{u,s,v}(t),\theta_{3dB}\right)
=p^{0}\,
\frac{G^T\!\left(\theta_{u,s,v}(\tau_{u,s,v}),\theta_{3dB}\right)}
     {G^T\!\left(\theta_{u,s,v}(t),\theta_{3dB}\right)}.
\]
這個 fixed-reference 形式只是 segment 內的 telescoped identity，不是 runtime state，也不跨 handover、outage、unserved、re-entry 或 episode reset。這裡沒有目標 SINR、最低速率、lagged interference 或需求功率反推；也沒有 cap、clip 或 projection。若 \(H\) 與干擾固定，本地角度變化本身不保證 SINR／throughput 改變；角度仍透過 \(p\)、\(P^p\) 與 \(P^N\) 進入 EE 分母。

## 6. 唯一 SINR 與 Throughput

| 符號 | 定義 | 下標／角色 |
|---|---|---|
| \(I_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})\) | 鏈路 \((u,s,v)\) 接收到的總同頻干擾功率 | 三下標；主式不拆 intra/inter 別名 |
| \(\sigma^2\) | 接收端雜訊功率 | 系統／接收端標量，不強加三下標 |
| \(\gamma_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})\) | 鏈路 \((u,s,v)\) 的唯一實際 SINR | CH4 與 CH5 共用同一符號、同一公式 |
| \(B^w\) | 單一波束可用頻寬 | \(w\) 是 bandwidth 類別的單字母標籤 |
| \(U_{s,v}(t)\) | 波束 \((s,v)\) 目前服務的使用者數 | user 已被計數聚合，只保留 \(s,v\) |
| \(R_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})\) | 鏈路 \((u,s,v)\) 的實際 throughput | 三下標；單一使用者展示時分子不再加總 |

唯一 SINR 為

\[
\gamma_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_{3dB}\right)
=
\frac{
p_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_{3dB}\right)
H_{u,s,v}(t)
G^T\!\left(\theta_{u,s,v},\theta_{3dB}\right)
}{
I_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_{3dB}\right)+\sigma^2
}.
\]

有效服務鏈路必須滿足
\(I_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})+\sigma^2>0\)。

Throughput 為

\[
R_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_{3dB}\right)
=
\frac{B^w}{U_{s,v}(t)}
\log_2\!\left(1+\gamma_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_{3dB}\right)\right).
\]

實際服務鏈路要求 \(U_{s,v}(t)>0\)。單一使用者場景只令 \(U_{s,v}=1\)；公式本身不改，也不另建立單人版 SINR。

## 7. Power 與 EE 分母

| 符號 | 定義 | 下標／角色 |
|---|---|---|
| \(\xi_{s,v}(t,\boldsymbol{\theta},\theta_{3dB})\) | 波束 RF 發射功率到電源端消耗的有效轉換效率 | **兩下標**：一支波束一個放大器；全系統角度狀態與波束寬是函數參數，不是額外 owner |
| \(P^p_{s,v}(t,\boldsymbol{\theta},\theta_{3dB})\) | 波束 \((s,v)\) 的電源端功率 | \(p\) 是 power-consumption 階段的單字母上標；同樣為兩下標 |
| \(P^f(t)\) | 系統固定／circuit overhead 的聚合量 | 系統量，不加 \(u,s,v\)；概念簡報不展開硬體元件 |
| \(P^N(t,\boldsymbol{\theta},\theta_{3dB})\) | 當步系統總功率 | \(N\) 表示 network total；不能改成 \(P^N_{u,s,v}\)；帶 \(\theta_{3dB}\) 因發射功率依賴波束寬 |
| \(\eta_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})\) | 單一 UE-link 的 EE 顯示量：該鏈路 throughput 除以共同系統功率 | 三下標固定 numerator link，不代表 private per-user power |

功率關係為

\[
P^p_{s,v}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)
=
\frac{p_{s,v}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)}
{\xi_{s,v}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)},
\qquad \xi_{s,v}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)>0,
\]

\[
P^N\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)
=P^f(t)+
\sum_{s'\in \mathcal{S}}\sum_{v'\in \mathcal{V}}
z_{s',v'}(t)
P^p_{s',v'}\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right).
\]

EE 為

\[
\eta_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_{3dB}\right)
=
\frac{R_{u,s,v}\!\left(t,\theta_{u,s,v},\theta_{3dB}\right)}
{P^N\!\left(t,\boldsymbol{\theta},\theta_{3dB}\right)},
\qquad P^N>0.
\]

固定／circuit overhead 雖不直接受角度控制，仍可用單一 \(P^f\) 保留在分母；其 exact mapping 由 \(P^f(t)=\sum_s\left(N^{\mathrm{act}}_sP_{\mathrm{cir}}+\mathbb{1}\{N^{\mathrm{act}}_s>0\}P_{\mathrm{BB}}\right)\) 定義，\(P_{\mathrm{cir}}=0.338\,\mathrm{W}\)、\(P_{\mathrm{BB}}=0.200\,\mathrm{W}\)；數值隨 active beams 狀態改變，不是 calibration pending。簡報不需要進一步解釋 RF-chain、baseband、event energy 或 PA 曲線。

\(\eta_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})\) 是概念簡報／模擬器的 selected-link 顯示量，不取代論文正式結果的系統級 EE。論文 headline 與方法比較仍使用全體使用者總 throughput 對系統總能耗的 ratio-of-sums；跨時間評估符號與區間留待 experiment／evaluation contract 凍結，不在本表重新引入另一個 active EE 別名。

## 8. 角度依賴的呈現層級

| 量 | 正式呈現 | 角度語意 |
|---|---|---|
| 單一鏈路角度 | \(\theta_{u,s,v}(t)\) | 幾何直接輸出 |
| wanted-link 增益因子 | \(H_{u,s,v}(t)G^T(\theta_{u,s,v},\theta_{3dB})\) | \(H\) 承載非角度鏈路狀態；\(G^T\) 直接承載服務角度 |
| RF 發射功率 | \(p_{u,s,v}(t,\theta_{u,s,v}(t),\theta_{3dB})\) | 新 segment 由 \(p^{0}=p_{\max}/2=0.825\) W 起始（2026-08-22 F-1）；同一 physical link 連續服務時由前一步功率與增益比遞推 |
| SINR／Throughput | \(\gamma_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})\)、\(R_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})\) | \(p\) 與 \(G^T\) 使用本地角度；同一 segment 內的乘積延續前一步，其他變化可來自 \(H\)、全系統干擾與負載 |
| 波束耗電 | \(P^p_{s,v}(t,\boldsymbol{\theta},\theta_{3dB})\) | 由該波束的 \(p_{s,v}(t,\boldsymbol{\theta},\theta_{3dB})=\max_u p_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})\) 與 \(\xi_{s,v}(t,\boldsymbol{\theta},\theta_{3dB})\) 決定；仍只有兩個 owner 下標 |
| 系統總功率 | \(P^N(t,\boldsymbol{\theta},\theta_{3dB})\) | 聚合所有 active link power 與固定 overhead |
| 單一 UE-link EE | \(\eta_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})\) | 分子固定該 link，分母保留共同 system power |

不再使用整段角度軌跡 \(\boldsymbol{\Theta}\) 或 \(\Delta t\) 展開概念簡報。跨時間 ratio-of-sums 屬於正式實驗評估契約，待論文與 simulator 同步時另行定義。

## 9. 已退出 active symbol surface 的舊符號

| 舊符號／結構 | 新處理 |
|---|---|
| \(R^m\)、\(R_{\min}\) 作為功率上游 | 不再用來產生發射功率；QoS 可作獨立評估指標 |
| \(\gamma^r\)、\(\gamma^{\mathrm{req}}\) | 刪除；沒有目標 SINR |
| \(\gamma^e\)、\(\widehat\gamma\) | 刪除；CH4／CH5 共用 \(\gamma_{u,s,v}\) |
| \(p^r\)、\(P^r\) | 刪除；以實際角度相關 \(p_{u,s,v}\) 取代 |
| \(P^o\)、satellite scaling | 不屬於概念主鏈；未來若實作需要，留在 simulator engineering contract |
| \(P_{\mathrm{beam},\max}\)（舊名）、\(P_{\mathrm{sat},\max}\) | \(p_{\max}=1.65\,\mathrm{W}\) 是 active 每波束 RF 輸出上限，亦是鏈路可行性檢查門檻；它不進入 recurrence。\(P_{\mathrm{sat},\max}\) 僅保留為 legacy 每星總上限，不屬 active 契約。 |
| PA back-off、\(P_0\)、效率 clamp | 不展開；概念層以正的有效效率 \(\xi\) 表示 |
| \(I^a\)、\(I^b\) | 主公式合併為總干擾 \(I\)；需要教學時可用文字解釋來源 |
| \(\gamma_u\) | 概念鏈不另造 user-level SINR；已選定鏈路直接使用 \(\gamma_{u,s,v}\) |
| \(h_{u,s,v}\) | 刪除；不再建立只靠大小寫區分的中間量，直接使用 \(H_{u,s,v}(t)G^T(\theta_{u,s,v},\theta_{3dB})\) |
| \(L_{st}\)、\(L_{st,max}\)、\(\phi\)、\(\phi_{max}\) | 退出公開表面（2026-08-21）；兩篇來源論文都沒有掃描損耗模型，效果併入 \(H\) 的實作層，不是公開符號或公開可調參數 |
| \(L_N\) | 退出公開表面（2026-08-21）；TR 38.811 NLoS clutter 屬實作層敏感度參數，併入 \(H\)，不進入 \(L_{u,s,v}\) 的公開展開 |
| \(F_m\)、\(\mu_m\)、\(\kappa_m\)、\(F_{J_1}\)、\(F_{flat}\)、型樣索引 \(m\) | 退出公開表面（2026-08-21）；只保留 HOBS 式 (3) 的單一型樣 \(F\) 與 \(\mu\)，替代型樣是實作層敏感度選項 |
| \(\kappa\)、\(1.75\) | 退出公開表面（2026-08-21）；抄寫錯誤（\(J_1(\mu)/(2\mu)\) 誤寫為 \(2J_1(\mu)/\mu\)）加上的補丁常數與反解角度參數 \(1.8352\)，runtime 與文件均已改回 HOBS 式 (3) 的 \(2.07123\) |
| MODQN 的 \(G_{i,l,v}\) | 不與 HOBS 的 \(G^T\)／\(G^R\) 合併；它是**通道增益**，角色對應本表的 \(H_{u,s,v}\)，語意不同不可同名共用 |
| \(\eta^e_{u,s,v}(\boldsymbol{\Theta})\) | 移出概念簡報；目前只保留當步 \(\eta_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})\) |
| 執行遮罩 \(m^e\) | **刪除**（2026-08-22 使用者裁決）：不再保留環境端帳務或三閘連線式；式 (4.5a) 使用兩閘 \(x=a\cdot z\)，「選了不一定連得上」由逐波束功率可行性（\(p_{\mathrm{req}}>p_{\max}\) 判 infeasible）承擔。\(m^e\) 不屬 active symbol surface。 |
| \(v_{\max}\)（又名 `k_cap`） | **刪除**（2026-08-21，SDD-01 §2.2）。⚠ 2026-08-22 更正:當時記「改由原論文 Table I 的 \(V=7\) 表示」是**錯的** —— \(V=7\) 是原論文波束集合的大小 \(|\mathcal{V}|\)，其 7 道恆常全亮，原論文**沒有任何計數式上限**。本論文亦不設上限；波束啟用由 \(z_{s,v}=\mathbb{1}\{U_{s,v}>0\}\)（式 3.4）導出 |
| \(\mathcal{F}\)、\(F\)（射頻槽索引域與槽數） | **刪除**（2026-08-21，SDD-01 §2.2，隨 \(v_{\max}\) 與舊 \(r_3\) 一併消失）；\(F=L_w v_{\max}\) 依賴已刪除的 \(v_{\max}\)；負載平衡改以計數式 \(r_{3,u}=-U_{b_u}\) 表示，無需射頻槽域 |
| \(\widetilde{R}_{s,v}\)、\(T_k\)（依賴射頻槽的 beam throughput aggregate） | **移除**（2026-08-21，SDD-01 B13 舊 \(r_3\) 依賴項）；新 \(r_{3,u}=-U_{b_u}\) 是計數式，不需要 beam aggregate throughput 排序；\(\widetilde{R}\) 帶波浪標記的形式一併消失 |
| 舊 \(r_3\)（max−min gap 型，依賴 \(\widetilde{R}\) 與 \(\mathcal{F}\)） | **汰換**（2026-08-21，SDD-01 B13）；改為 \(r_{3,u}=-U_{b_u}\)（計數式，逐使用者獨立，不依賴射頻槽排序） |
| \(N(t)\)（定義為「填入 \(\mathcal{F}\) 個射頻槽的啟用波束數量」） | **汰換**（2026-08-21）；定義 \(0\le N(t)\le F\) 靠已刪除的 \(\mathcal{F}\) 撐住；若後續需要啟用波束計數，以 \(\sum_{s,v} z_{s,v}(t)\) 或不依賴 \(\mathcal{F}\) 的新定義重新引入 |
| \(\chi\)、z-score 壅塞情境（B8） | **⚠ 保留為可選機制，預設關閉**（2026-08-21，SDD-01 §2.1 B8）；程式保留但不接上 live 訓練路徑；此條目**不刪除**，符號狀態標記為「可選，預設關閉」 |

## 10. CH4／CH5 採用表

| 章節 | 新增／定義 | 只能引用 |
|---|---|---|
| CH4 | 公式層定義 \(d\)、\(\theta\)、\(G^T\)、\(H\)、唯一 \(\gamma\)、\(R\)；其後以現行論文符號說明 P1／P2／P3 與 baseline MODQN | \(p_{u,s,v}\) 只解釋為實際 RF 發射功率，不說明控制律 |
| CH5 | 完整定義 segment-start 0.825 W、previous-step 角度感知 \(p\)、\(P^p\)、\(P^f\)、\(P^N\)、\(\eta_{u,s,v}\) | 直接重用 CH4 的 \(\gamma\) 與 \(R\)，不得重新定義；不得跨事件保留 power |

此採用表是公式與符號責任表，不是投影片頁數表。CH4／CH5 都不得再建立獨立的 \(h=HG^T\) 定義頁；需要說明 wanted-link numerator 時，直接使用 \(p_{u,s,v}H_{u,s,v}G^T(\theta_{u,s,v},\theta_{3dB})\)。

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
| $G^T(\theta,\theta_{3dB})$、$G_0$ | 發射端角度增益函數與波束中心增益；$G^T(\theta,\theta_{3dB})=G_0F(\theta,\theta_{3dB})$ 且 $G^T(0,\theta_{3dB})=G_0$。 | 式 (3.7)–(3.9) |
| $F(\theta,\theta_{3dB})$、$\theta_{3dB}$ | $J_1/J_3$ 角度型樣（唯一一個），逐字採用 HOBS 式 (3)，在 $\theta=0$ 自然等於 1；與 3 dB 波束寬度。 | 式 (3.8)–(3.9) |
| $\mu(\theta,\theta_{3dB})$、$J_1$、$J_3$ | Bessel 型樣的角度參數與固定 Bessel 項；角度參數固定為 HOBS 式 (3) 的 $2.07123$，不是可調參數。 | 式 (3.9) |
| $H_{u,s,v}(t)$ | 一層展開為 $10^{-\frac{L_{u,s,v}(t)}{10}}G^R_{u,s,v}(t)$ 的線性鏈路功率因子；在 SINR numerator 中直接與 $G^T(\theta_{u,s,v},\theta_{3dB})$ 相乘。 | 式 (3.10)、式 (3.10a) |
| $L_{u,s,v}(t)$ | $L_f(d_{u,s,v}(t),f_c)+L_g(\alpha_{u,s}(t))+L_c(\alpha_{u,s}(t))+L_s(\alpha_{u,s}(t))$ 的路徑／衰落損耗層，即 HOBS 式 (1) 的四項。後三項皆隨仰角變化(2026-08-22 為 $L_s$ 補上引數)。 | 式 (3.10b) |
| $A_{\mathrm{zen}}$ | 天頂大氣氣體吸收，$L_g(\alpha)=A_{\mathrm{zen}}/\sin\alpha$；形式取 TR 38.811 式 (6.6-8) \[17\]，值 0.25 dB 由 TR 38.821 \[22\] 的 LEO Ka 20 GHz 下行預算(0.5 dB @ 仰角 30 度)反推。**2026-08-22 取代 legacy 的 $\chi_{\mathrm{atm}}$ 式**，後者天頂只給 0.015 dB(等效大氣厚 0.3 km)。 | 第 5.1 節 |
| $L_c(\alpha)$、$L_s(\alpha)$ | 閃爍與遮蔽衰落，數值取 TR 38.811 \[17\] 表 6.6.6.2.1-1(20 GHz 對流層閃爍)與表 6.6.2-3(Ka LOS shadow fading, $\sigma$ 隨仰角)。HOBS 式 (1) 只給名稱未給值，此代換是本研究的建模選擇。$L_s$ 與 $K_R$ 是模型僅有的兩個隨機項。 | 式 (3.10b)、第 5.1 節 |
| $G^R_{u,s,v}(t)$ | H 一層展開中的接收端線性增益；以軸心增益扣除離軸損耗表示，截止於 $[G_{R,\min},G_{R,\max}]$。 | 式 (3.10a)、式 (3.10c) |
| $\theta^{R}_{u,s}(t)$ | 使用者接收天線指向與第 $s$ 顆衛星方向之間的夾角（度）；與發射端偏軸角 $\theta_{u,s,v}$ 分屬鏈路兩端，沿用 $G^T$／$G^R$ 的 T／R 上標慣例，不帶波束下標 $v$（假設接收指向固定對準服務衛星）。 | 式 (3.10c) |
| $A_R$、$B_R$、$G_{R,\max}$、$G_{R,\min}$ | 式 (3.10c) 的地球站參考型樣參數與上下限；$A_R$、$B_R$、$G_{R,\min}$ 同出一條 ITU-R 建議式，在 $48^{\circ}$ 連續銜接。 | 式 (3.10c)、表 5-2 |

## 10.3 角度功率、耗能與 EE

| 符號 | 定義 | 首次位置 |
|---|---|---|
| $\xi_{s,v}(t,\boldsymbol{\theta},\theta_{3dB})$ | 波束的 RF 到電源端有效轉換效率，$\xi=\min\{\xi_{\max},\xi_{\max}\sqrt{p_{s,v}/p_{\mathrm{sat}}}\}$；類 B 平方根近似 \[23\]。**逐波束,不帶 $u$**；角度狀態與波束寬是函數參數。 | 式 (3.15)、(3.15a) |
| $p_{\mathrm{sat}}$、$BO$、$\xi_{\max}$ | 飽和功率 $p_{\mathrm{sat}}=p_{\max}10^{BO/10}$、輸出回退、最大效率；數值見第 5.1 節。 | 式 (3.15a) |
| $P^{p}_{s,v}(t,\boldsymbol{\theta},\theta_{3dB})$ | 波束 $(s,v)$ 的電源端功率：$P^p_{s,v}=p_{s,v}/\xi_{s,v}$。**兩下標**；函數參數完整保留。 | 式 (3.15) |
| $P^{f}(t)$ | 固定／電路功率彙總，$P^{f}=\sum_s\left(N^{\mathrm{act}}_sP_{\mathrm{cir}}+\mathbb{1}\{N^{\mathrm{act}}_s>0\}P_{\mathrm{BB}}\right)$；**partial payload-power model**，不含本振與相移器功率。 | 式 (3.16)、(3.16a) |
| $N^{\mathrm{act}}_{s}(t)$、$P_{\mathrm{cir}}$、$P_{\mathrm{BB}}$ | 衛星 $s$ 的啟用波束數、每啟用波束電路功率、衛星共用基頻功率 \[26\]。 | 式 (3.16a) |
| $p_{u,s,v}(\tau_{u,s,v},\theta_{u,s,v}(\tau_{u,s,v}),\theta_{3dB})$ | 每個 served segment 的起始 RF 發射功率，固定為 $p^0$；不跨 continuity break 保留。 | 式 (3.11) |
| $p_{u,s,v}(t,\theta_{u,s,v}(t),\theta_{3dB})$ | 同一 physical link 連續服務時，由前一步 RF power 乘以前一步／目前角度增益比遞推的功率。 | 式 (3.12) |
| $P^{N}(t,\boldsymbol{\theta},\theta_{3dB})$ | 聚合所有 active link power 與固定 overhead 的系統總功率。 | 式 (3.16) |
| $\eta_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})$ | 固定分子鏈路、共同分母系統功率的單一 UE-link EE 顯示量。 | 式 (3.17) |

## 10.4 干擾、訊號品質與吞吐量

| 符號 | 定義 | 首次位置 |
|---|---|---|
| $c_{s,v}$ | 波束 $(s,v)$ 的頻率顏色，$c_{s,v}=(q_{s,v}-r_{s,v})\bmod 3$；六角格上相鄰蜂巢必為異色，同色波束共用子頻帶。 | 式 (3.12a) 前段 |
| $I^{\mathrm{intra}}_{u,s,v}$、$I^{\mathrm{inter}}_{u,s,v}$ | 同衛星與跨衛星同色干擾；求和以啟用指示 $z$ 為門檻，不以載量加權。 | 式 (3.12a)、(3.12b) |
| $p_{s,v}(t,\boldsymbol{\theta},\theta_{3dB})$ | 波束 $(s,v)$ 的發射功率，取其所服務使用者的最大值；全系統角度狀態與波束寬完整保留在函數參數中。 | 式 (3.12a) 前段 |
| $I_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})$ | 總同頻干擾，$I=I^{\mathrm{intra}}+I^{\mathrm{inter}}$。 | 式 (3.13) |
| $\sigma^2$ | 接收端雜訊功率，$\sigma^{2}=k_BTB^{w}$，$T=T_a+T_0(10^{NF/10}-1)$；數值取 3GPP TR 38.821 VSAT 設定 \[22\]，列於第 5.1 節。 | 式 (3.13) |
| $\gamma_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})$ | 唯一的實際鏈路 SINR；第三、四章共用，沒有 estimated／required／target 版本。 | 式 (3.13) |
| $B^w$ | 單一波束可用頻寬，$B^{w}=B_{\mathrm{sys}}/3$（三色重用）；$w$ 是 bandwidth 類別的單字母標籤。 | 式 (3.12a) 前段、式 (3.14) |
| $R_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})$ | 鏈路 $(u,s,v)$ 的實際 throughput；分母使用 beam load $U_{s,v}(t)$。 | 式 (3.14) |

## 10.5 目標、獎勵與評估

| 符號 | 定義 | 首次位置 |
|---|---|---|
| P1、P2、P3 | 長期最佳化中的能量效率、換手成本與負載平衡三個目標。 | 式 (3.24) |
| $\Psi_u(t)$ | 使用者 $u$ 在時間 $t$ 的換手成本。 | 式 (3.27) |
| $(\rho_u(t),\delta_u(t))$ | 使用者 $u$ 在時間 $t$ 的服務衛星與服務波束索引；只在換手比較式中使用。字母沿用 MODQN 原文 $\rho_i(t),\delta_i(t)$（2026-08-21 由 hat notation 改回，見 WRITING-GUIDE.md §4）。 | 式 (3.27) |
| $\varphi_1,\varphi_2$ | 同衛星換束與跨衛星換手的成本，且 $0<\varphi_1<\varphi_2$。 | 式 (3.27) |
| $r_{1,u}(t,\boldsymbol{\theta},\theta_{3dB})$ | 所選鏈路 EE 顯示量的總和：$\sum_{s,v}x_{u,s,v}(t)\eta_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})$。**帶 $\boldsymbol{\theta},\theta_{3dB}$**(2026-08-23):右側經 $\eta$ 與 $P^{N}$ 依賴整組偏軸角與波束寬參數,左側必須涵蓋。$r_{2,u}$、$r_{3,u}$ 不帶。 | 式 (3.25) |
| $r_{2,u}(t)$ | 換手成本目標的逐使用者獎勵：$-\Psi_u(t)$。 | 式 (3.27) |
| $r_{3,u}(t)$ | 負載平衡獎勵；使用者 $u$ 當步所選波束的服務人數取負值，$r_{3,u}(t)=-U_{b_u(t)}(t)$。逐使用者可分解：$\sum_u U_{b_u(t)}(t)=\sum_{s,v}U_{s,v}(t)^2$ 恰為 P3 目標（2026-08-21，B13）。 | 式 (3.29) |
| $\overrightarrow R_u(t,\boldsymbol{\theta},\theta_{3dB})$ | 三目標獎勵向量 $[r_{1,u}(t,\boldsymbol{\theta},\theta_{3dB}),r_{2,u}(t),r_{3,u}(t)]$,因第一個分量而帶 $\boldsymbol{\theta},\theta_{3dB}$。 | 式 (3.29) |

## 10.51 主鏈外的實驗／legacy provenance

下列符號只可出現在第五章的實驗設定、歷史執行紀錄或附錄對照，不是 active EE 主鏈的一部分。它們不得重新出現在式 (3.11)–(3.17) 的推導中；新契約的數值參數應由 scenario／experiment config 提供。

| 類別 | 符號 | 用途 |
|---|---|---|
| 深層角度型樣校準 | $c_0,\delta,g$、$F_m,\mu_m,\kappa_m$、型樣索引 $m$ | 超過一層 Bessel pattern 的校準、量測或替代型樣選擇；active 正文使用 $\theta_{3dB},\mu,J_1,J_3$ 的單一型樣一層展開。 |
| 深層通道展開 | $L^{\mathrm{FS}},G^{\mathrm{LS}}$、$L_{st},L_{st,max},\phi_{st},\phi_{st,max}$、$L_N$ | 超過 $L_f,L_g,L_c,L_s$ 的距離、傳播、掃描損耗、NLoS clutter、接收方向與衰落細節；active 正文使用一層 $H$ 展開，這些量併入 $H$ 的實作層。 |
| Legacy power boundary | $R^{m},P_{\mathrm{sat},\max},P_0,\eta_0$、legacy $L^{\mathrm{atm}}/\chi_{\mathrm{atm}}$ | 舊 runtime 的最低速率、每星功率上限與 PA 參考設定；只在第五章 provenance 出現，$P_0$ 不等於 active segment-start 0.825 W(但數值等於式 3.15a 的 $p_{\mathrm{sat}}$)。**2026-08-22:$P_{\mathrm{beam},\max}$ 已改名 $p_{\max}$ 並升為 active 參數**(式 3.15a 與鏈路可行性檢查)，不再屬此列。 |
| 電路與事件展開 | $N_s^{\mathrm{act}},P_{\mathrm{RFC}},P_{\mathrm{BB}},E_{\mathrm{tr}},E_{\mathrm{ho}},b^{\mathrm{tr}},b^{\mathrm{ho}}$ | 完整固定功率分攤與事件能量；正文彙總為 $P^f$。 |
| 頻率與雜訊展開 | $K_{\mathrm{FR}},B_{\mathrm{sys}},q,r,\operatorname{col},k_B,T$ | 完整頻率重用與熱雜訊參數；正文使用 $c$ 與 $\sigma^2$。 |


## 10.6 候選動作與狀態

| 符號 | 定義 | 首次位置 |
|---|---|---|
| $b_u(c,t)$ | 將使用者 $u$ 的候選編號 $c$ 映射到時間 $t$ 的實際衛星－波束對，$b_u(c,t)\in \mathcal{S}\times\mathcal{V}$。 | 第 4.1 節 |
| $s_u(t)$ | 使用者 $u$ 在時間 $t$ 的原始狀態，包含前一步連線、候選 SINR、偏軸角與未篩選需求。 | 式 (4.1) |
| $x_u(t-1)$ | 依候選索引 $C$ 排列的前一步連線向量。 | 式 (4.1) |
| $[\gamma_{u,s,v}(t,\theta_{u,s,v},\theta_{3dB})]_{\substack{(s,v)=b_u(c,t)\\c\in \mathcal{C}}}$、$[\theta_{u,s,v}(t)]_{\substack{(s,v)=b_u(c,t)\\c\in \mathcal{C}}}$ | 依候選順序堆疊的鏈路 SINR／偏軸角元素；沿用唯一的 $\gamma_{u,s,v}$，cached／predicted provenance 放在 metadata。 | 式 (4.1) |
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

> 本節只記錄 V0.3 之前的論文版本。V0.3 不使用雙代理、舊三 reward
> objectives、兩個 replay pool、Bellman target network 或 post-training
> coordination；V0.3 的 active 方法符號以第 10.12 節為準。

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
| $r_{1,u}^{F}(t,\boldsymbol{\theta},\theta_{3dB}),r_{1,u}^{M\mid F}(t,\boldsymbol{\theta},\theta_{3dB})$ | 上述兩個聯合動作各自產生的第一個目標原始獎勵。 | 式 (4.14) |
| $r_{1,u}^{S}(t,\boldsymbol{\theta},\theta_{3dB})$ | 鯰魚代理與主代理比較動作在第一個目標上的獎勵差值。 | 式 (4.14) |
| $\eta_w$ | 第一個目標的競爭獎勵權重。 | 式 (4.14) |
| $r_{1,u}^{C}(t,\boldsymbol{\theta},\theta_{3dB})$ | 加入競爭項後的鯰魚代理第一個目標獎勵。 | 式 (4.14) |
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
| $T_a,T_0,NF$ | 天線溫度、參考溫度與雜訊指數；由此得到第 4 節的接收系統溫度 $T$。 | 第 5.1 節 |
| $R_b$ | 由衛星高度與半功率波束寬計算的波束覆蓋半徑：$h_s\tan(\theta_{3dB}/2)$。**鋪格慣例(2026-08-22 補記)**:$R_b$ 取為六角格的**外接圓半徑**,故格心間距為 $\sqrt{3}R_b$、單格面積為 $2\sqrt{3}\left(\sqrt{3}R_b/2\right)^2$,此慣例使每格內接於自身的 3 dB 等高線而不留覆蓋洞。⚠ 若誤取為內切半徑,單格面積會高估 4/3 倍(509.0 → 678.7 km²),面積比估算會因此偏低。 | 第 5.1 節 |

## 10.11 容易混淆的重用記號

| 記號 | 區分方式 |
|---|---|
| $p^{0}$ 與 $p_{\max}$ 的相容條件 | **必須 $p^{0}<p_{\max}$,否則每個分段在第一步就不可行。** 式 (3.11) 的遞推在段內只會讓功率上升,所以起點超限便無法回到可行區。舊值 $p^{0}=2$ W 比 $p_{\max}=1.65$ W 高 0.835 dB,實測 outage 率恆為 1.0,2026-08-22 改為 $p^{0}=p_{\max}/2=0.825$ W,使 $p_{\max}/p^{0}=3$ dB 恰等於格邊緣的增益下降。 |
| $\xi_{s,v}$、$P^{p}_{s,v}$ | **2026-08-22 去掉 $u$ 索引**。一支波束只有一個放大器,式 (3.15a) 的引數本來就只有 $p_{s,v}$,左側卻帶 $u$,式 (3.16) 因此改為對 $(s,v)$ 的二重和、過濾器用 $z_{s,v}$。逐鏈路加總會多出 $\sum_{s,v}(U_{s,v}-1)P^{p}_{s,v}$,隨佔用單調上升,汙染 P3。 |
| $G^{T}$、$F$、$\mu$ 的引數 | **2026-08-22 改為雙引數 $(\theta,\theta_{3dB})$**。理由:$\theta_{3dB}$ 出現在 $\mu$ 定義式右側,定義式的左側必須涵蓋右側出現的量；本表採用一般函數慣例，以逗號分隔兩個參數。$G_0$ 是乘性尺度常數、不改變型樣形狀,仍不列入引數。式 (3.10) 之後仍明寫為 $G^{T}(\theta_{u,s,v},\theta_{3dB})$。 |
| $p_{\max}$ 與 $P_{\mathrm{beam},\max}$ | **同一個量,前者是現行名稱**(每波束射頻輸出上限 1.65 W,式 3.15a 的回退後操作上限,亦為鏈路可行性門檻),後者是 2026-08-22 之前的舊名,只保留在歷史文件中。 |
| 學習率 | **刻意不給符號**。$\alpha$ 已是仰角 $\alpha_{u,s}(t)$,若再用 $\alpha$ 表學習率會撞號,表 5-3 以中文「學習率」書寫,並列為受控變因掃描 $\{0.01,0.003,0.001\}$。 |
| $F$ | **三義,靠位置區分**:$F(\theta,\theta_{3dB})$ 是天線角度型樣（帶引數的函數，式 3.9）,$F_W$ 是最近 $W$ 束分數的經驗分布（帶下標）,**上標 $F$ 是鯰魚端標籤**,$d\in\{M,F\}$（2026-08-22 由雙字母 `CF` 改為單字母,助記 Fish）。 |
| $L$ 的下標 | $L_{u,s,v}$ 是**總**路徑損耗（帶三索引）,$L_f$、$L_g$、$L_c$、$L_s$ 是它的四個分量（自由空間、氣體吸收、閃爍、遮蔽），**下標是名稱不是索引**。⚠ $L_s$ 的 $s$ **不是衛星索引**,對應 HOBS 式 (1) 的 $L_{fs},L_g,L_{sc},L_{sf}$（2026-08-22 為單字母化改寫）。 |
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
| $B$ | $B_{\mathrm{sys}}$、$B_{\mathrm{beam}}$ 是頻寬；$B$ 是訓練批次大小；$B_I$ 是混合批次。 |
| $\alpha$ | $\alpha_{u,s}(t)$ 是仰角；$\alpha_s(t)$ 是衛星功率縮放係數。 |
| $7$ | ⚠ **兩個 7 無關**:$J_w=7$ 是每顆視窗衛星的候選波束槽（錨定格 + 六鄰居，repo 的 `NUM_BEAM_SLOTS`）；原論文 MODQN Table I 的 $V=7$ 是**他們粒度下的每衛星波束集合大小**，已被本論文的 $V$（指向格數）取代。數值相同純屬巧合，**不得互相代入**，也不得由它推出任何上限。 |
| $L$ | $L_w$ 是候選表保留的可見衛星數（第 4.1 節）；$L_{u,s,v}(t)$ 是 Ch3 路徑／衰落損耗層（式 3.10b，逐字採用 HOBS 式 (1) 的四項）；$L$（無下標）已隨容量懲罰刪除（2026-08-21）。二者僅靠下標區分，2026-08-21 由 $L_{\mathrm{cap}}$ 簡化而來。 |

## 10.12 Multi-Catfish MCRL V0.3 方法擴充符號

本節是 V0.3 方法章、論文圖與英文簡報的 active notation extension。
主符號維持單字母；需要多個 owner／route 維度時，只組合既有的單字母
或數字索引。程式與 evidence receipt 的 `z1`、`z2`、`z3` 欄位分別映射
到論文符號 \(\zeta_{1,u}\)、\(\zeta_{2,u}\)、\(\zeta_{3,u}\)，不得直接
拿 schema field 當論文公式符號。

主文與主簡報不需要一次展示本節所有符號。公開主線只使用
`MULTI-CATFISH-MCRL-V03-PRESENTATION-LAYER-2026-08-31.md` 第 7 節列出的
子集；\(\nu_j,w_j,\beta,D^o,D^t,D^a\) 等只在完整 loss、資料或附錄首次
需要時才引入。這是 presentation-depth 裁決，不刪除本節的正式定義。

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


---

## 2026-08-22 汰換紀錄

| 移除的符號 | 依據 |
|---|---|
| $v_{\max}$ | 使用者裁決刪除（SDD-01 §2.2）。⚠ 2026-08-22 更正:當時記「改由 Table I 的 $V=7$ 表示」是錯的，見下列 $V_b$ |
| $V_b$（同時輻射波束數上限，式 3.3 舊版） | **刪除**（2026-08-22 作者裁決）。理由:(1) 原論文 $V=7$ 是 $|\mathcal{V}|$ 而非上限，其 7 道恆常全亮，`G6-VERBATIM-blind-audit-2026-07-15.md:62` 逐字「Paper: no cap」,(2) 與 ch3 既有散文「$z=1$ 當且僅當 $U>0$」直接矛盾,(3) 與 P3（$\min\sum U^2$）衝突，上限 $k$ 使 P3 下界抬高為 $n^2/k$。式 (3.3) 改為 $U_{s,v}$ 定義，式 (3.4) 改為啟用規則 |
| $\mathcal{F}$、$F$、$T_k$ | 射頻槽索引域，隨 $v_{\max}$（$F=L_wv_{\max}$）與舊 $r_3$ 一併消失（SDD-01 §2.1 B13） |
| $N(t)$ | 其定義為「填入 $F$ 個槽位的數量、$0\le N(t)\le F$」，依賴已刪除的 $F$ |
| $\widetilde R_{s,v}$、$\widetilde R_{s_k,v_k}$ | 舊 $r_3$ 的 beam aggregate throughput。B13 改為計數式 $r_{3,u}=-U_{b_u}$，不再需要 |
| $m^e_{u,c}$ | **刪除**(2026-08-22 使用者裁決,原話「不用統計了直接刪 mask」)。式 (4.5a) 改為 $x=a\cdot z$,「選了不一定連得上」改由**逐波束功率可行性**($p_{\mathrm{req}}>p_{\max}$ 判 infeasible)承擔,該機制有出處且已實作。⚠ 先前一版曾記為「保留為環境端帳務」,那是助理裁決、非使用者授權,已撤回 |
| $\Delta_s$ | 定義為「超出前 $v_{\max}$ 個波束名額的偏好質量」，依賴已刪除的 $v_{\max}$ |

| $\chi_{u,c}$、$s^{\chi}_u$、$\psi_{u,i}$、$\mu_i$、$\sigma_i$、$\epsilon_z$、$\tilde s_u$ | **從論文完全移除**(2026-08-22 使用者裁決:「不刪掉先保留」指的是**程式**,論文要刪)。§4.2 整節與式 (4.7)–(4.9) 已刪,式號 4.10–4.16 重編為 4.7–4.13,網路輸入回到 $s_u(t)$(112 維)。**程式保留為消融開關,論文任何章節不得出現。** |
| $\epsilon_h$、$\epsilon_V$ | 隨需求功率反推與容量懲罰刪除,ch5 表已移除該列 |

**保留於程式、不入論文**:$\chi$ 與跨使用者正規化(B8 修訂 2026-08-22)。

**權威**：`docs/research/ee-definition-cleanup/2026-08-17-simplified-ee-symbol-table.md`。

| $a_u^{d,*}(t+1)$（共用純量化下一步動作） | **刪除**（2026-08-22，決策 B1）；TD target 改回原論文式 (16) 的 vanilla 形式，每個目標各自在自己的目標網路取 max，不再有跨目標共用的單一動作 |

| 容量懲罰整組符號 $V_u^M$、$\widetilde V_u^M$、$\pi_u$、$\Pi_{s,v}$、$\tau$（softmax 溫度）、$L$、$\lambda$、$\epsilon_V$ | **刪除**（2026-08-22）；容量懲罰整節（原 §4.5 與式 4.15–4.17、圖 4-8）已自論文移除。已逐一驗證正文零殘留（$\lambda$、$L$、$\epsilon_V$ 皆 0 命中）；⚠ 正文仍有 $\tau_{u,s,v}$，那是 segment 起始時間步，**與此處的 softmax 溫度 $\tau$ 同字母不同義** |
