# R1 EE／power chain：單字母紙面符號替換表

日期：2026-09-05（Asia/Taipei）  
狀態：`PROPOSAL_FOR_SYMBOL-TABLE_AND_CHINESE-WORD_PASS`  
範圍：只處理新版 R1 angle-aware EE／power chain 的紙面符號。沒有修改
`modqn-paper-reproduction` 的符號表、論文 source、DOCX、PPTX、Chapter 5、
C2/C3 或任何 shared authority。

## 1. 裁決原則

本表以 active symbol table 的語意與 owner 規則為準（表 §10.0、§§10.2--10.4），
只把公開 R1 展開中仍含有多字母下／上標的名稱改成單一字元標記。函數參數
不是下標，因此 `t`、`theta`、`theta_3` 等函數引數不受「owner 下標」規則影響。

`+`、`-` 是單一字元的上／下界標記；它們特意取代 `max`／`min`，避免重新
引入已退出公開表面的 `m`（舊型樣 selector）或與 `L`、`h_s` 混淆的
`l`／`h`。`3` 是單一數字標記，正文第一次出現時以文字說明「全 3 dB
半功率波束寬」，不是把 `dB` 當成符號下標。

## 2. 必須替換的紙面符號

| 現行紙面符號 | 建議 R1 紙面符號 | 單字元角色定義／使用方式 | 來源定位 |
|---|---|---|---|
| `\(\theta_{3dB}\)` | `\(\theta_3\)` | `3` = full 3-dB HPBW；保留 `\(\theta_3/2\)` 作 HOBS 單邊半功率角。不得改成單邊 3.32° 的另一個參數。 | `mc-modqn-base.md:161-192`；active table:88-90；alignment report:104-124 |
| `\(p_{\max}\)` | `\(p^{+}\)` | `+` = active per-beam RF upper limit；仍是可行性門檻，不是 recurrence 內的 projection。 | `mc-modqn-base.md:330`；active table:286,543；subscript audit:160-169 |
| `\(p_{\mathrm{sat}}\)` | `\(p^{s}\)` | 上標 `s` = saturation reference；不加 satellite owner 下標，且與 `\(p_{s,v}\)` 以位置及完整 base symbol 區分。 | `mc-modqn-base.md:330-335`；active table:393-394 |
| `\(\xi_{\max}\)` | `\(\xi^{+}\)` | `+` = maximum efficiency；與 beam-level `\(\xi_{s,v}\)` 不共用 owner。 | `mc-modqn-base.md:333-338`；active table:393-395 |
| `\(N^{\mathrm{act}}_s(t)\)` | `\(N^a_s(t)\)` | 上標 `a` = active；下標 `s` 仍是 satellite owner。 | `mc-modqn-base.md:342-350`；active table:396-397 |
| `\(P_{\mathrm{cir}}\)` | `\(P^c\)` | 上標 `c` = circuit constant；系統常數，不是 candidate `c` 的下標。 | `mc-modqn-base.md:342-352`；active table:396-397 |
| `\(P_{\mathrm{BB}}\)` | `\(P^b\)` | 上標 `b` = baseband constant；系統常數，不是 `b_u(c,t)` 映射函數。 | `mc-modqn-base.md:342-352`；active table:396-397 |
| `\(P_{\mathrm{RF}}\)` | **不另造符號；改用 `\(p_{s,v}\)`** | R1 主鏈的 RF output 已由 active beam power `\(p_{s,v}\)` 表示。PA 說明若需比例式，寫 `\(p_{s,v}\propto V_o^2\)`。 | `mc-modqn-base.md:274,338`；alignment report:170-181 |
| `\(P_{\mathrm{DC}}\)` | **不另造符號；改用 `\(P^p_{s,v}\)`** | R1 主鏈的 DC／supply consumption 已由 `\(P^p_{s,v}=p_{s,v}/\xi_{s,v}\)` 表示。PA 說明若需比例式，寫 `\(P^p_{s,v}\propto V_o\)`；`\(\xi=p/P^p\)`。 | `mc-modqn-base.md:321-327,338`；active table:395 |
| `\(G_{R,\min}\)` | `\(G^R_{-}\)` | `-` = receiver-gain lower envelope；`R` 保留為 receive role。 | `mc-modqn-base.md:216-224`；active table:385-387 |
| `\(G_{R,\max}\)` | `\(G^R_{+}\)` | `+` = receiver-gain upper/boresight envelope；`R` 保留為 receive role。 | `mc-modqn-base.md:216-224`；active table:385-387 |
| `\(\theta^R_{\min}\)` | `\(\theta^R_{-}\)` | `-` = lower validity angle of the ITU envelope；不可與 `\(\theta_3\)` 混為發射波束寬。 | `mc-modqn-base.md:224`；active table:386-387 |
| `\(A_{\mathrm{zen}}\)` | `\(A^z\)` | 上標 `z` = zenith atmospheric absorption constant；在 `\(L_g(\alpha)=A^z/\sin\alpha\)` 中使用。 | active table:383；alignment report:170-181 |
| `\(I^{\mathrm{intra}}_{u,s,v}\)` | `\(I^i_{u,s,v}\)` | 上標 `i` = intra-satellite interference。 | `mc-modqn-base.md:270-290`；active table:407-410 |
| `\(I^{\mathrm{inter}}_{u,s,v}\)` | `\(I^x_{u,s,v}\)` | 上標 `x` = cross-/inter-satellite interference；避免復活已退出的 `\(I^a/I^b\)`。 | `mc-modqn-base.md:270-290`；active table:407-410 |
| `\(B_{\mathrm{sys}}\)` | `\(B^g\)` | 上標 `g` = global/system bandwidth；維持 `\(B^w=B^g/3\)`，`w` 仍只表示 per-beam bandwidth class。 | `mc-modqn-base.md:272`；active table:413 |
| `\(NF\)` | `\(N_f\)` | 下標 `f` = noise figure；用於 `\(T=T_a+T_0(10^{N_f/10}-1)\)`。 | `mc-modqn-base.md:292`；active table:411 |
| `\(BO\)`（只在 PA 說明出現） | `\(b_o\)` | `o` = output back-off；僅為 PA 參數，不能進入 R1 recurrence 的主式。 | `mc-modqn-base.md:330,338`；active table:394 |
| `\(L_{fs}\)`, `\(L_{sc}\)`, `\(L_{sf}\)`（只在 HOBS provenance 句中出現） | `\(L_f\)`, `\(L_c\)`, `\(L_s\)` | 使用 active 的四項單字母 loss names；`L_g` 不變。這些 HOBS source labels 不在新公式另建第二組符號。 | `mc-modqn-base.md:206-214`；active table:382；subscript audit:61-71 |

### 2.1 對應後可直接使用的 R1 片段

以下不是新公式，只是把現有 active chain 的長標籤替換成上表記法：

```text
G^T(theta,theta_3) = G_0 F(theta,theta_3)
mu(theta,theta_3) = 2.07123 sin(theta) / sin(theta_3/2)

G^R_(u,s,v)(t)
  = min{ max{ A_R - B_R log10(theta^R_(u,s)(t)), G^R_- }, G^R_+ }

I_(u,s,v) = I^i_(u,s,v) + I^x_(u,s,v)
sigma^2 = k_B T B^w,
T = T_a + T_0 (10^(N_f/10) - 1),
B^w = B^g / 3

xi_(s,v) = min{ xi^+, xi^+ sqrt( p_(s,v) / p^s ) }
P^p_(s,v) = p_(s,v) / xi_(s,v)
P^f = sum_s [ N^a_s P^c + 1{N^a_s > 0} P^b ]
P^N = P^f + sum_(s,v) z_(s,v) P^p_(s,v)
```

在正式 LaTeX／Word／OMML 中，集合、粗體 `\(\boldsymbol{\theta}\)`、三下標
`\((u,s,v)\)` 及函數參數按 active table 原規則排版；上面使用 ASCII 只是
對照，不是要把數學式改成等寬字串。

## 3. 不需替換的 R1 canonical symbols

下列已符合單字母 owner／role 規則，維持原 active spelling：

`\(d,\alpha,R_E,h_s,\theta,\mathbf v,\mathbf r,G^T,G_0,F,\mu,J_1,J_3,`
`\(H,L,L_f,L_g,L_c,L_s,G^R,\theta^R,A_R,B_R,p,p^0,x,z,U,I,\sigma^2,`
`\(k_B,T,T_a,T_0,\gamma,B^w,R,\xi,P^p,P^f,P^N,\eta,r_1\)`。

鏈路量的 `\((u,s,v)\)`、beam quantity 的 `\((s,v)\)`、以及 system quantity
不加實體 owner 的原則全部保留；本任務沒有把 `\(\xi_{s,v}\)` 或
`\(P^p_{s,v}\)` 改回三下標。

## 4. Collision audit

### 4.1 Exact-symbol collision check

以完整 base、上標／下標位置及 owner 維度區分後，新的 R1 surface 沒有下列
完整符號重複：

```text
theta_3, p^+, p^s, xi^+, N^a_s, P^c, P^b,
G^R_-, G^R_+, theta^R_-, A^z, I^i, I^x, B^g, N_f, b_o
```

- `p^s`（saturation constant）與 `p_(s,v)`（satellite/beam-owned RF power）
  的 `s` 位於不同位置，不能互換。
- `N^a_s` 的 `a` 是 active role，`a_u`（若在方法章出現）仍是 action；
  base 與 owner 位置不同。
- `P^c`／`P^b` 是固定功率常數；它們不取代 `c_(s,v)` 頻率顏色或
  `b_u(c,t)` 候選映射。
- `I^i`／`I^x` 不使用已退出的 `I^a`／`I^b`，也不把 C3 的非焦點 user
  index `i` 引入 R1 公式；`i` 只作 I 的 interference-family tag。
- `B^g` 不取代 `B^w`；前者是 full system bandwidth，後者是 per-beam
  bandwidth after reuse。
- `N_f` 不取代 `N^a_s`；一者是 receiver noise-figure parameter，一者是
  per-satellite active-beam count。

### 4.2 Deliberately avoided labels

- 不使用 `m` 作 max tag：`m` 曾是已退出的 pattern selector，會與
  `F_m`／`\mu_m` 的歷史記號混淆。
- 不使用 `l`／`h` 作 gain bounds：`L` 已是 total loss，`h_s` 已是 satellite
  height；`-`／`+` 是更清楚且不佔用物理字母的界線標記。
- 不使用 `P^r`／`P^d` 表示 RF/DC：`P^r` 已在 legacy surface 出現過，且
  `r_1` 是 R1 reward；直接重用 active `p`／`P^p` 可消除第二套 power names。
- 不把 legacy `P_{\mathrm{sat},\max}`、`P_{\mathrm{RFC}}`、event-energy
  labels 或 `\chi_{\mathrm{atm}}` 拉回 R1 主鏈；它們是 provenance／實作層，
  不屬本次替換範圍。

### 4.3 Formula-semantics preservation

這套映射只改 token spelling，不改物理意思：

1. `\(\theta_3\)` 仍代表**完整** HPBW，HOBS pattern 的 denominator 仍為
   `\(\sin(\theta_3/2)\)`。
2. `\(p^+\)` 是 active per-beam operating limit；它不是把 cap／projection
   偷塞回 previous-step recurrence。
3. `\(P^p\)` 仍是逐波束 supply-side power，`\(P^N\)` 仍是共同 system
   denominator；沒有產生 private per-user power。
4. `\(I^i+I^x\)` 只是干擾來源的紙面拆分，總干擾仍只有一個 active
   `\(I_{u,s,v}\)`，SINR 仍只有一個 `\(\gamma_{u,s,v}\)`。
5. `\(A^z\)`、`\(N_f\)`、`\(b_o\)` 與 `\(P^c/P^b\)` 僅服務於已存在的
   channel／PA／circuit 展開；不引入 C2、C3、Expected-ZR 或任何 learner
   symbol。

## 5. 對後續 source-first pass 的精確要求

後續若獲授權更新符號表與純中文版 Word source，應以本檔第 2 節作為唯一
替換表，並在同一 pass：

1. 先更新 active symbol table 的 R1 rows，再更新 `mc-modqn-base.md` 的
   公式與第一次定義文字；
2. 以 source-first 流程重建 DOCX，不直接 patch `mcrl-thesis-ZH.docx`；
3. 對式 (3.7)--(3.17)、(3.25) 重新檢查 `theta_3`、`B^g`、`N_f`、
   `I^i/I^x`、`P^c/P^b`、`N^a_s`、`p^+/p^s`、`xi^+` 及 bounds 的一致性；
4. 只做 R1 paper-facing symbol pass。不要順便改 Chapter 5 數值、C2/C3
   公式、training claims 或外部 PPTX。

本檔是 mapping／collision receipt，不是 active authority，也不表示 R1 或
任何 Catfish learner 已通過 efficacy gate。
