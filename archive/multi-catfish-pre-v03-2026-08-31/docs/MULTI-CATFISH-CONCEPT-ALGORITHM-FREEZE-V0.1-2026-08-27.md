# Multi-Catfish 概念演算法凍結稿 v0.1-R5

> **2026-08-30 同步邊界。** 公開方法名稱是 **Multi-Catfish MCRL**。目前拓撲
> 嚴格為 `C1 -> Q_1^M`、`C2 -> Q_2^M`、`C3 -> Q_3^M`；完整 reward bundle
> 只用於 audit，不表示一個 specialist 更新 Main 的三個 heads。C2 採用
> policy-aligned Forecast-Certified Temporal Fork V0.3A。本文可供結構圖、講解及非結果章節
> 起稿，但不代表 C1/C2/C3 已提升 EE。

日期：2026-08-27（2026-08-30 R5 同步）  
論文方法權威：`MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md`。  
C2 細節權威：`C2-TEMPORAL-FORK-CANDIDATE-V0.3-2026-08-29.md`。  
圖稿與非結果章節邊界：`MULTI-CATFISH-NONRESULTS-PAPER-AUTHORING-CONTRACT-V0.1-2026-08-27.md`。  
EE 驗收：`THREE-CATFISH-EE-POSITIVE-ACCEPTANCE-CONTRACT-V0.1-2026-08-28.md`
中的 diagonal、direct-objective 與 fresh-seed Main-only EE 條件；該文件的舊
Activation-Churn C2 機制已被 policy-aligned Temporal Fork V0.3A 取代。

## 使用邊界

本文件凍結的是可起稿的演算法架構、三個候選角色與因果敘事，不宣稱實驗已
證明有效。結構圖起稿 gate 已開放；final/camera-ready handoff 尚未開放。圖中
三個角色都必須標為 proposed；C3 另外標示 `shadow-only until consumer gate
pass`。不可使用 validated、improved 或 state of the art。目前技術稿中的三步
hold 加第一個 release 是 C2 V0.3A 的實作設定；總覽圖可寫 bounded
hold-plus-release，C2 細圖可畫三個 hold 加第一個 release。經驗比例與其他
超參數仍由 Stage-0、carrier smoke 與短訓練 pilot 裁決。

目前 C2 已有一筆使用既有 9000-EP Main checkpoint 的 K=4 工程證據：完整
candidate schedule 經 hash 封存後，恰好執行一次四步 option、一次 Q2F update
與一次 combined Main update，兩個 ledger 各 commit 一次。這可在流程圖上標為
`bounded trained-checkpoint mechanics PASS`，但不可改寫成 fresh-start、EE
improvement 或 Chapter 5 結果。

policy-aligned V0.3A 另有四個 fresh-start、U=10、兩個 episode 的固定 seed
receipts：總計 8 schedules、32 candidates、6 pass、10 certificate fail、16
support rejection、0 contract error；`K0=5`、`K1=0`、`K>=2=3`，其中 2/4
seeds 出現 K>=2，並實際形成 3 options、1 次 Q2F update 與 1 次 Q2F/Main
joint commit。這只能標為 `replicated bounded opportunity/mechanics PASS`，不可
標為 EE improvement、training trend 或 Chapter 5 result。正式演算法仍要求每
100 episodes checkpoint，尚待長程驗證。

## 一句話定義

Multi-Catfish MCRL 在訓練期使用三個彼此獨立、分別對齊 canonical
`r1/r2/r3` 的 Catfish 產生完整環境經驗；每條來源通過自己的 Main-consumer
gate 後，只把該來源的 TD 影響送到對應的 Main objective head。完整未塑形
reward vector 隨 bundle 保留供 audit。測試與部署時移除所有 Catfish，只由
Main 決策。

## 已凍結的三個角色

| 角色 | 核心問題 | 專屬行為機制 | 對 EE 的路徑 |
|---|---|---|---|
| C1 Energy-Frontier (`F_1`) | 哪些已執行軌跡具有較佳即時 rate/system-power 比？ | local SNR-greedy source 對 masked-uniform neutral source control 的 LEO-native EXP + C1-private ACRM | 直接對齊 canonical `r1`；fresh-seed Main-only system EE 仍為 empirical |
| C2 Temporal-Continuity (`F_2`) | 哪些短期關聯承諾可避免不必要切換與 ping-pong，同時在 forecast model 中不犧牲 EE？ | matched detached-Main reference/candidate temporal fork；各 branch 重算 local Main，candidate 只 hold focal action，cross-world non-focal equality 不要求；三個 holds 加第一個 release；forecast-EE 與 hold/full system-R2 certificate；K0/K1/K>=2 分流 | 直接學 unchanged `r2`；forecast EE 只過濾 support；fresh-seed Main-only EE 必須另外實證 |
| C3 Spatial Load-Balancing (`F_3`) | 哪些同衛星高負載到低負載重配置可形成 strict `r3`-improving fork，且同時通過獨立 power/service safeguard？ | strict-load certificate + separate persistent-power safeguard | 直接對齊 `r3`；power/service 是 safeguards；fresh-seed Main-only EE 必須另外實證 |

C1 是即時 energy frontier；C2 是時間維度的關聯穩定；C3 是空間維度的負載
重配置並附帶 power safeguard。C2 可能傾向保持關聯，C3 可能主動付出一次 intra-satellite handover；
這個衝突由完整三目標 reward vector 呈現，不由額外 coordinator 隱藏。

## Q-network 拓撲

角色的 learning route 是一對一；每個 Catfish 同時擁有自己的 specialist Q：

```text
Main MODQN:     Q_1^M, Q_2^M, Q_3^M
Specialists:   Q_1^F, Q_2^F, Q_3^F
Role mapping:  r_1 <-> F_1, r_2 <-> F_2, r_3 <-> F_3
```

Main 保留原本三個 objective DQN。每個 Catfish 另有自己的 specialist
online/target Q、optimizer、RNG、replay memory `D_j^F` 與 checkpoint。C1 可在
自己的更新內使用 ACRM；C2/C3 只學 unchanged canonical `r2/r3`。這是四個
邏輯 learner states：`Main, F_1, F_2, F_3`；以 online Q function 計數則是 Main 的三個加三個
specialist，共六個（target copies 另計）。

Catfish bundle 進入 Main 時仍攜帶每位使用者的完整
`overrightarrow R_u(t,boldsymbol theta,theta_{3dB})`，其中三個分量沿用第三章
完整引數，以便稽核同一行為對三目標的真實後果；但 specialist-origin 的梯度
嚴格沿對角線，只到 matching head：`C1 -> Q_1^M`、`C2 -> Q_2^M`、
`C3 -> Q_3^M`。Catfish 不修改 Main 的 network 輸出，也不在部署時接管 action。

## 凍結的共同 Catfish operator

每個 Catfish 都只在自己的 collection branch 執行以下四步：

1. **Trigger**：只讀 canonical pre-outcome state、mask、實體 ID、
   specialist-private option state 與獨立 RNG。
2. **Propose**：提出一個合法介入或短期 option；不得讀取 realised reward、
   future RNG、fading outcome、successor 或 oracle EE。
3. **Execute and retain**：實際執行並保留完整 joint outcome；負面結果也不得
   刪除。
4. **Gate and route experience**：C1 只在自己的更新內使用 ACRM，C2/C3 使用
   canonical `r2/r3`；通過來源專屬 Main-consumer gate 後，matching Main head
   只接收該來源定義的 source-unit TD 影響。原始 `U x 3` environment reward 與
   完整 atomic joint bundle 保留供 audit；gate 失敗則保留 shadow lineage。

目前 C3 有一個明確而未通過的 representability gap：Main state 只有前一步的
ungated demand `n_{s,v}`，C3 certificate 與 canonical `r3` 使用本步 eligible
load `U_{s,v}`。因此所有 C3→Main 箭頭都必須先穿過 consumer gate，並保留
`shadow-only` 失敗支線。

## 與 RIS CDRL 三階段的關係

```text
Phase I   source preparation / replay seeding       (offline; not dual-rollout)
Phase II  Main + independent Catfish collection     (training-time rollouts)
Phase III Main-only policy evaluation/deployment
```

原始 RIS Phase-I 以 DFT codebook 枚舉、WMMSE 求解及 max-EE 選擇產生 exemplar。
目前 LEO C1 不宣稱 literal RIS fidelity；它使用實際執行的 local SNR-greedy
source 與 masked-uniform neutral source control，建立
immutable LEO-native EXP corpus。source quality 必須先通過非學習 Source Gate A。
兩者都屬訓練前的 source preparation，均不是 dual-rollout。

Immutable EXP prefill 只進 `D_1^F`，不得進 `D_M`、Main quota、evaluation、
checkpoint selection 或 headline metric。只有 Phase-II 中後續真正執行的 C1
branch bundle，才有資格經 consumer gate 送 Main。Frozen-Main
self-distillation 不是本設計的 source generator。

Dual-rollout 描述 Phase-II 中 Main 與 Catfish 各自以自己的 policy 在獨立分支
產生經驗。Multi-Catfish MCRL 將舊的 Main + one-Catfish pair 擴展成 Main 加 C1/C2/C3 三個
獨立 specialist collection branches。圖中不可把 Phase-I corpus generation 畫成
Main/Catfish 同步競跑，也不可把 LEO EXP 標成 RIS DFT/WMMSE solver。

## 具體訓練演算法

```text
Input:
    Main learner M
    independent specialists F_1, F_2, F_3
    frozen source quotas, safety masks, intervention schedule and controls

Initialize:
    independent online/target networks, optimizers, RNGs and replay views
    pass the C1 source-quality gate
    freeze local_snr_greedy and masked_uniform executed source corpora
    prefill D_1^F only; never prefill D_M

For each training collection block:
    freeze the Main comparator/version for this block

    For source k in {Main, C1, C2, C3} under the fixed source schedule:
        observe canonical state s_u(t), valid-action mask and source-local state
        compute the uncommitted Main reference action
        for C2, do not reuse this opening action at later candidate offsets;
        every branch and offset recomputes frozen Main locally

        if k = Main:
            execute Main behavior action
        else if k = C1:
            execute C1 EE-frontier behavior; apply EXP/ACRM only inside C1
        else if k = C2:
            at a detached-Main handover boundary, run the complete fixed
            pre-outcome schedule from one common anchor
            in the reference fork, recompute Main on the reference state
            in every candidate fork, recompute Main on that candidate state;
            override only the focal action with the incumbent for hold offsets
            0--2, then execute the complete candidate-local Main action at release
            certify forecast EE, hold/full system-R2, focal service,
            no-new-non-focal-outage, branch-local Main alignment and lineage
            if K = 0: execute Main fallback and create no C2 source unit
            if K = 1: execute the forced singleton control
            if K >= 2: rank certified candidates by epsilon-greedy Q_2^F
            execute three holds plus the first detached-Main release
        else if k = C3:
            if the option is open or the certified mask is non-empty:
                select or continue a certified spatial load-balancing option
            else:
                execute the preregistered C3 fallback

        execute the source action or bounded option for its actual length
        retain atomic bundle(s) containing all users, actions, masks,
        successors, U x 3 rewards and complete source/RNG/option lineage
        if k = Main:
            admit the Main-origin bundle to D_M under the Main quota
        else if k = C1:
            update F_1 from the complete bundle
            conditionally route its source unit only to Q_1^M after the F_1 gate
        else if k = C2:
            learn the observed zero-bootstrap focal option return in Q_2^F
            average the same primitive Q_2^M TD losses as one C2 source unit
            if replay warm-up is active:
                retain the admitted outcome but do not update or commit
            else:
                let the joint transaction own exactly one Q_2^F update and
                exactly one combined Main update
        else if k = C3:
            update F_3 from the focal row with canonical r_3
            conditionally route its source unit only to Q_3^M after the F_3 gate
        on gate failure, retain that source in shadow lineage and do not route

    for each decision not already owned by a committed C2 transaction:
        execute exactly one combined Main update from canonical Main replay
        plus its matching-head specialist unit
    record receipts without a second Main optimizer step
    preserve fixed quotas, zero-block source age and at-most-once identity
    checkpoint complete resumable state every 100 episodes

Evaluation/deployment:
    set all Catfish doses to zero
    discard C1/C2/C3
    execute only Main MODQN masked-greedy/scalarized actions
```

## 圖中應呈現的資料流

```text
                                   training only
F_1: r1 / energy ---- source unit ----> [gate F_1] --pass--> Q_1^M
                                             +--fail--> shadow
F_2: r2 / time ------ source unit ----> [gate F_2] --pass--> Q_2^M --> Main-only
                                             +--fail--> shadow             deployment
F_3: r3 / load ------ source unit ----> [gate F_3] --pass--> Q_3^M
      +-- separate power/service safeguard   +--fail--> current shadow-only

Every executed source object also retains the complete U x 3 reward vector
for audit; this audit payload does not create cross-head gradients.

No vote / no auction / no action fusion / no post-training override
```

圖可用三條不同顏色的 experience stream 匯入 Main；不要畫成三個 Catfish 在
部署端投票，也不要把三個 specialist signals 相加成一個新 reward。三條 stream
不是無條件承諾；三條路徑各有一個 source-specific consumer gate，不能合併成
all-stream gate。C3 目前明確保留 shadow-only 支線，C1/C2 也仍各自 conditional。

`local_snr_greedy`、`masked_uniform`、所有 `C1-*`/`C2-*`/`C3-*` arm ID、
`a_C2`、`s_tilde_*` 與 provenance field name 都是 implementation-receipt
identifier，不得出現在論文正文、公式、caption 或 figure label。圖面改用
`local SNR-greedy source`、`masked-uniform neutral source control`、
`F_1/F_2/F_3`、canonical `s_u(t)`/`a_u(t)`，以及 specialist-private option
state 的文字描述。

## 可畫、但須標為 experimental 的角色內部

- C2：matched detached-Main temporal fork；forecast-EE 與 hold/full system-R2
  certificate；`K0 fallback / K1 forced control / K>=2 Q_2^F ranking`；三個
  hold 加第一個 release；observed zero-bootstrap option return 與 Main primitive
  `r2` source unit 經 joint transaction 一次提交。
- C3：`strict load gap -> same-satellite relocation -> power/service safeguard`
  的空間 option；直接 learning reward 仍是 canonical `r3`。
- C1：`local SNR-greedy source vs masked-uniform neutral source control ->
  source-quality gate -> C1-only EXP prefill`
  與 `ACRM comparator` 兩條可分離消融路徑。

圖解可用「short-horizon」描述 C2/C3，不必把目前 pilot 的數值畫成不可改變的
理論常數。C3 的完整 recurrence、反事實 twin 與證書條件應放在
方法細圖或演算法框，不放在第一張總覽圖。

## 完整圖組分鏡

### Fig. 4-1 — Multi-Catfish MCRL architecture overview

- 左側三個垂直排列的 specialist：`F_1` Energy、`F_2` Temporal、`F_3` Spatial。
- 三條 `objective-aligned source unit` 各自先進 `F_j`-specific consumer gate；
  各路 pass 才到 matching Main head，各路 fail 進自己的 shadow-only 支線。
- Main 內畫出 `Q_1^M / Q_2^M / Q_3^M`，箭頭嚴格對角：C1→Q1、C2→Q2、
  C3→Q3；另以 audit 標籤表示每個 bundle 保留完整 reward vector。
- 右側是 `Main-only deployment`；三個 Catfish 停在 training-only 邊界內。
- 圖下注明 `No action fusion, auction, coordination, or post-training override`。

### Fig. 4-2 — Four-learner / six-Q topology

- Main 擁有 `Q_1^M,Q_2^M,Q_3^M` 與 `D_M`。
- `F_j` 各只擁有一個 `Q_j^F` 與 `D_j^F`，不是三個完整 Catfish MODQN。
- 每個 learner 的 online/target、optimizer、RNG 與 replay boundary 分開。
- 每個 specialist 的 learning arrow 只指向 matching Main head；完整 reward
  vector 只畫成 bundle 內的 audit payload，不畫成跨 head 更新箭頭。

### Fig. 4-3 — C1 Energy-Frontier mechanism

- 上支線：`local SNR-greedy source` / `masked-uniform neutral source control`
  -> source-quality gate -> executed source corpus -> EE strata -> immutable
  prefill -> `D_1^F` only。
- 下支線：C1 executed branch 與 frozen Main counterfactual comparator -> ACRM
  private signal。
- 兩支線進入 `Q_1^F`；offline prefill 不得有直接到 Main 的箭頭。只有後續
  executed C1 source unit 可經 gate 送 `Q_1^M`；完整 original reward vector
  只留在 bundle 內作 audit。
- 用 source quality、stratification、EXP、ACRM 與 joint-effect 五條 mechanism
  path 表達消融；不要把 implementation arm ID 放在圖中。

### Fig. 4-4 — C2 Temporal-Continuity option

- 在 detached-Main handover anchor 畫同一 pre-decision state 分出的 Main
  reference 與 candidate forks，兩邊使用 matched、domain-separated forecast RNG。
- reference 與每個 candidate 都在自己的 branch state 上重算同一 frozen Main
  policy。candidate side 畫三個 holds 加第一個 contemporaneous detached-Main
  release：hold 期間只以 incumbent physical satellite/beam ID 覆寫 focal user，
  release 則執行完整 candidate-local Main joint action；candidate branch 內的
  focal physical-ID continuity 必須跨 candidate-table remap 保持一致。
- certificate 方塊包含 forecast-EE surplus、hold/full system-R2 margins、service、
  no-new-non-focal-outage、branch-local Main policy alignment 與 lineage；所有固定
  schedule outcomes 先 seal 再 selection。兩個 counterfactual branches 的 non-focal
  realised actions 可以不同，不可畫成 reference future-action replay 或 cross-world
  non-focal identity gate。
- 畫出 `K=0 Main fallback / K=1 forced control / K>=2 Q_2^F ranking`；只有 K>=2
  可以標 learned ranking。
- live side 保留 adverse outcomes 與 true terminal prefixes；`Q_2^F` 學 observed
  zero-bootstrap option return，`Q_2^M` 接同一實際序列的 mean primitive loss，
  兩者經 one-at-most-once joint transaction。
- 右側以 `fewer avoidable varphi_1/varphi_2 events` 實線指向 canonical `r2`；
  forecast EE 是 support certificate，fresh-seed Main-only EE 仍以虛線標 empirical。

### Fig. 4-5 — C3 Spatial Load-Balancing with separate safeguards

- 左圖：同衛星 source `(s,v)` 與 already-active destination `(s,v')`；標示
  reference-fork pre-move eligible loads，source 包含 focal、destination 不包含。
- 中圖：每個 certified interval 都檢查
  `U_{s,v}(h) >= U_{s,v'}(h)+2`，並列出
  `Delta sum_u r_{3,u}(h)=2(U_{s,v}(h)-U_{s,v'}(h)-1)`。
- 另畫獨立 power/service safeguard，不可把 power difference 接成 reward。
- 右圖：`Q_3^F` 只學 canonical `r3`；direct `r3` arrow 用實線，system energy、
  useful bits 與 EE 用虛線 supporting endpoints。
- Main 前畫 consumer gate；因 Main 使用 lagged `n_{s,v}`，gate fail 必須通往
  `shadow-only`。

### Fig. 4-6 — Atomic routing and Main update

- 一個 bundle 含完整 joint action、所有 user rows、successors/masks 與 `U x 3`
  canonical reward matrix。
- source quota、age 與 injection dose 以 source unit 計數；一般 bundle unfold 後
  平均 loss，使每個 bundle total weight = 1；C2 的一至四個 primitive losses
  先平均成一個 C2 source unit。
- 每條 specialist-to-Main 箭頭各有 source-specific consumer gate，且只到 matching
  Main head；private shaping、power diagnostic 與 option state 不進 Main reward。
- C2 額外畫 `Q_2^F + Q_2^M joint transaction`、commit-last 與 narrow rollback
  邊界；可另外畫 episode-boundary resumable snapshot，但不得暗示 surrounding
  environment/replay/carrier 已具備 mid-episode crash atomicity，也不得把
  clock-aware training-result parity 畫成完整 carrier-state byte identity。
- adverse outcomes 保留，duplicate bundle 不得重複送入 Main。

### Fig. 4-7 — Training and deployment sequence

- Phase-I：`local SNR-greedy source` / `masked-uniform neutral source control`
  preparation -> source-quality gate -> C1-only EXP prefill；標明 offline、
  `not dual-rollout`、`never D_M`。
- Phase-II：source-specific collection -> retain all outcomes -> specialist update ->
  consumer gate -> unshaped atomic routing or shadow-only -> fixed-quota Main update。
- Phase-III：all specialist doses zero -> Main scalarization -> masked-greedy action。
- 用叉號排除 voting、auction、coordination、action fusion。

以上七張 Chapter 4 圖可由本文件直接起稿。需要把 C2/C3 的正式數學證書完整
畫成附錄級流程圖時，再以權威技術稿與 frozen Stage-0 specs 補入細節；不要由
繪圖 session 自行發明 guard、係數或結果。

## 實驗失敗時會改動哪一層

| 結果 | 可保留 | 必須處理 |
|---|---|---|
| 通過 Stage-0 與短 pilot | 整體架構與角色機制 | 只凍結 horizon、quota、超參數與報告規則 |
| 有事件支撐，但方向弱或不穩 | 三角色問題定義與 canonical reward alignment | 可能重做 selector、support 或 transfer dose；C2/C3 不得改成私有 reward 來救援 |
| 幾乎沒有合格事件 | Multi-Catfish 架構、C1、時間／空間角色問題定義 | 該角色的具體 option/support 必須重新設計 |
| 跨種子明確傷害 EE／service | 其他已通過角色 | 不得靠事後調係數救援；移除或重新預註冊該機制 |

因此，總覽圖和講解現在可以平行開始；實驗最可能改的是 C2/C3 方塊內部的
選擇、support 與 gate 狀態，而不是「三個候選互補經驗來源 -> consumer gate
-> 一個 Main -> Main-only deployment」這條主幹。但若 sealed evidence 否定
某一機制或 consumer gate，最終圖必須把該來源留在 shadow/ablation 或移除，
不預先承諾三條都能路由，也不靠事後改 reward 救援。
