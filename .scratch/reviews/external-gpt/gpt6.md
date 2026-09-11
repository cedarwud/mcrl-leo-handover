我已完成這次 fresh-context 接手：指定 Claude session `f508c755-8fc6-4503-9548-0225a1607848`、9 份優先 authority files，以及目前 `sat` 上的實際 processes / result artefacts 都重新核對過。以下判讀只用目前 repository 與 server artefacts，不沿用舊 ChatGPT 結論。

## 1. Ceiling、H4、Q9 的實際進度

### Ceiling：主問題其實已經有相當明確的答案，但完整報告尚未收尾

最重要的是：**物理／action space 並不是沒有 EE headroom。Scenario A 基本上已被目前 artefacts 排除。**

| 項目                               |                          目前結果 | 判讀                                               |
| -------------------------------- | ----------------------------: | ------------------------------------------------ |
| constrained service-floor search |                  **24/24 完成** | 主體完成                                             |
| pooled EE                        |           **151.257 M bit/J** | vs `A m=2dB` 107.001 M                           |
| pooled gain                      |                  **+41.361%** | paired +41.943 ± 1.493%, 24/24 episodes win      |
| served                           |                       0.99887 | 沒靠大量 unserved 換 EE                               |
| parity                           |  **max Δbits = 0、max ΔJ = 0** | 目前所有已完成 search steps 都 exact parity              |
| search budget                    | 240/240 steps hit 3-sweep cap | 所以這不是 optimum；只能稱 **lower bound**                |
| rate-floor variant               |             **+23.914%**, 6/6 | bits ratio 0.981、served 0.99917、p10 98.26 Mbit/s |
| nominal-information variant      |             **+10.958%**, 6/6 | 但 bits ratio **0.483**，吞吐崩太多                     |
| compound variant                 |                 +44.854%, 6/6 | 相對同 6 episodes 的普通 search 只再多 **+0.274%**        |

因此不能再說「ceiling 大概只有幾個百分點」。正確措辭是：

> 目前 budget-limited local central search 已經找到至少 +41.36% 的 one-step EE headroom；而加入嚴格 per-user rate floor 後，6-episode probe 仍有 +23.91%。這是 centralised one-step optimum 的**下界**，不是 ceiling 本身。

尤其 rate-floor 結果很關鍵：它把「+41% 只是把使用者 throughput 壓爛」這個解釋大幅削弱了。

目前還有 4 個 ceiling 補格程序活著，而且我已逐一核對 `cwd + cmdline`，全部正確，不應停止或重啟：

* bits lever 後半段，目前 4/6；
* joules lever 後半段，目前 4/6；
* B1 initialization basin，目前 1/6；
* random initialization basin，目前 1/6。

你最早給的 `3457360 / 3457364 / 3457368 / 3457372` 已退出；這是正常的，24/24 base results 已經落地。現在跑的是後續補格 PID，不是重跑主 search。

### H4：本體與 LP 已完成；oracle-first 正在跑

H4 本體已完成，而且修正了前面的盲審：

**energy head 不是 inert。**

η→0 時，9 個 trained checkpoints 有 **11.0–42.2%** action 會改變，平均約 24.6%。但是 closed-loop EE 變化是 **−8.1% 到 +3.1%**，沒有一致正向符號。

所以最新結論應該是：

> equal-share energy credit 確實能改變 policy，但它沒有把 policy 穩定地推向 pooled-EE improvement。

這比「energy term 完全不起作用」更精確，而且對下一版方法很重要：問題是 **credit alignment**，不只是 network 不理它。

更重要的是 LP probe 已完整完成。最值得保留的是兩個 cell：

| LP-prev cell | Eval EE gain |  served | bits ratio | p10 相對 rule |
| ------------ | -----------: | ------: | ---------: | ----------: |
| `c=2,m=0`    |   **+7.56%** | 0.99850 |      0.887 |       0.959 |
| `c=1,m=0`    |   **+6.66%** | 0.99854 |  **0.954** |   **1.016** |

而 `c=1,m=0` 在 calibration 仍是 **+4.75%**，bits ratio **0.952**、served 0.99813、p10 約 rule 的 0.968。

這是目前整個研究最重要的新證據之一：

**simultaneous、observation-only、per-user decision contract 本身確實拿得到可量測的 EE improvement。**

換句話說，不能再說「這個問題一定需要 coordinator 才有 EE 空間」。

但 LP-seq 的最高 EE cell `c=2,m=0` 雖然 +8.92%，served 只有 0.98796，而且 p10 只剩 rule 的 0.409，所以那個點不能算成功。

Oracle-first 現在也已經真的啟動，而且只是 measurement，不是 training。4 個 shard PID 均已核對為：

`/home/sat/mcrl-v025-h4-probe-ws/scripts/oracle_cells.py`

在我最後一次逐 JSON 核對時，第一優先 cell **A-real / R1 / evaluation 已完成 16/24 episodes**；4 shards 都仍正常運作。完整 worklist 是 150 episode-items，之後才會有 A-real/B-real aggregate、rate-floor replay 與 order-sensitivity。

因此 **現在還不能裁定 B1 vs B2**。

### Q9：只有 Q9a 完成，整體 Q9 還沒完成

Q9a 已經完成且 commit：

`1c2d0ba3`

內容包括：

* pilot 45 個 `P3-*` registry rows；
* 242 個值逐一 cross-check，0 mismatch；
* RESULTS-REGISTRY 新增 episode-set condition trap；
* DOCUMENT-STATUS 新增 pilot / Fable / agy / work-queue entries。

但我重新 grep 過：

**目前 RESULTS-REGISTRY / DOCUMENT-STATUS 還沒有 H4、LP、ceiling、oracle 的正式 rows。**

所以目前狀態是：

**Q9 pilot half = DONE；H4/LP/ceiling/oracle curation = 尚未做。**

---

# 2. 目前方法的最新證據圖

現在已經不是「整條 Multi-Catfish 是死路」那麼簡單。比較準確的證據圖是：

| 問題                                          | 現有證據                                                      | 現在的裁定                                  |
| ------------------------------------------- | --------------------------------------------------------- | -------------------------------------- |
| 現有三個 static Catfish 有沒有各自價值？                | A2 102.03M、A3 random 101.24M；directed 只高 **0.78%**        | **沒有證明**                               |
| offline replay 是否有用？                        | A3 相對 A1 約 +2.6%                                          | 有，但目前比較像 generic replay/regularisation |
| equal-share energy head 是否沒作用？              | η→0 改 11–42% actions                                      | **不是 inert**                           |
| equal-share energy credit 是否對 EE 對齊？        | η→0 closed-loop −8.1～+3.1%，方向不一致                          | **沒有對齊好**                              |
| physics/action space 有沒有 EE headroom？       | central search 至少 +41.36%；rate-floor +23.91%/6ep          | **非常明確地有**                             |
| independent per-user contract 有沒有 headroom？ | LP-prev `c=1,m=0` eval +6.66%、cal +4.75%，bits ratio >0.95 | **有**                                  |
| 是否只有 coordinator 才能進步？                      | LP-prev 已反例                                               | **否**                                  |
| coordinator 是否仍可能拿到更多？                      | +41% vs per-user 約 +5–7%                                  | **是，而且差距很大**                           |
| 三個新 Catfish 是否已能定案？                         | 尚無新 source-value / distinctness / marginal ablation       | **不能**                                 |

所以我現在會把研究方向改寫成：

> **目前 three-static-Catfish implementation 已經不值得救；但 Multi-Catfish research question 反而比幾小時前更有根據。**
>
> 原因不是我們已經證明「三隻都有效」，而是現在第一次同時證明了兩件必要條件：
>
> 1. 系統裡真的存在很大的 EE controllability；
> 2. 其中至少一部分是 simultaneous per-user observable policy 可以取得的，不全是 centralized-only effect。

這是實質進展。

但你的目標「三隻 Catfish 都對 pooled EE 有正 marginal」目前仍然**沒有證據**。按照現在已寫死的 controller rule，Catfish 數量不能預設成 3；可能最後是 1、2、3 或 4。

另外還有一個很值得注意的 engineering finding：目前正在準備的 B1 difference-credit lane 已確認，若直接使用 naive `F(with u)-F(without u)`，**outage user 可能因 0 bits / 0 J 形成 free-ride**。所以 explicit outage charge 不是裝飾，而是必要的 credit semantics。這個 lane目前只做到 code reading / semantics / tests 設計，**沒有 optimizer step、沒有 training**。

---

# 3. Ceiling 三種結果應走哪條方法路線

### Scenario A — constrained headroom ≤ +3.3%

這條原本的路徑是：

停止調 DQN、Catfish、DQfD；直接重做 controllable physics/action space，例如 per-beam power、beam sleep/activation、handover interruption、payload resource control。

但依目前 24/24 base result +41.36%，而且 parity exact，**Scenario A 現在幾乎已經被實際結果排除**。除非最後 audit 發現 instrumentation validity failure，目前沒有這個跡象。

### Scenario B — per-user observable headroom 足夠

方法路線應該是：

**oracle → credit → representation → learner → Catfish source screen**

而不是先訓練 Catfish。

具體來說，先等 A-real/B-real：

* 如果 **A-real 明顯贏 rule，而 B-real 相對 A-real沒有再多 ≥3.3 points**：
  主要問題是 credit，走 **B1 difference reward**；deployment contract 不變。

* 如果 **B-real 比 A-real再高 ≥3.3 points**：
  表示 credit 還不夠，policy 還缺 current-step lighting information，走 **B2 sequential/current-step observation**。

* 如果 realised oracle 很高但 observation-only approximation 拿不到：
  先 redesign observation，不訓練。

這裡目前有一個很重要的細節：

原始 ceiling 的 nominal variant 雖然 +10.96%，**bits ratio 只有 0.483**，所以它自己不符合原 Scenario-B 的 `bits ratio ≥ 0.95` gate。

但是後來 oracle-first amendment 把 A-nom 擴展成 observation-only LP family，而 **LP-prev(1,0)** 已經做到：

* evaluation +6.66%，bits ratio 0.954；
* calibration +4.75%，bits ratio 0.952；
* served >0.998；
* p10 沒有崩。

所以目前不是「Scenario B 已正式過關」，但已經有一個非常像 **B-compatible deployable witness** 的東西。現在缺的是 A-real/B-real 把「credit vs information」拆開。

### Scenario C — 只有 joint decision 拿得到 headroom

如果最後 A-real/B-real 或 deployable nominal screens 都失敗，而 rate-floor central search 仍保持很高，那就應改：

**centralized critic / set-level critic / CTDE / coordinator**。

此時 Catfish 不再是「三個 per-user Q head 的老師」，而應該代表不同的 **joint beam-lighting operating regimes**。

但以現在 LP-prev 已經 +5～7% 這個結果來說，我不會再把「pure C-only」當首選假說。比較像是：

**B 有一塊真實可用的空間；C 還有更大的 residual headroom。**

也就是有可能先做出 defensible 的 per-user B 方法，再把 centralized gap 留作後續工作，而不必一開始就把整篇論文改成 CTDE。

---

# 4. 現在應停止、清理、啟動什麼

**現在不要停止任何正在跑的 ceiling / oracle 程序。** 我已核對它們的 cwd 和 cmdline，都是正確工作；殺掉只會浪費已投入計算。更不能重新啟動舊的 4 個 base PID。

Q5 的 3000-episode、DROP_C1/2/3、DQfD/ACRM 新 arm、任何新 Catfish training 都繼續 **NO-GO**。目前也沒有任何由我啟動的新 long training。

`watch_health.sh` PID 3291897 正常，繼續保留。

`b0/corrected-baseline-20260911` 的 content-equivalence audit 已經完成：2 個 commit byte-identical ported、另外 2 個已被較新的 fixes supersede，且已建立 `archive/b0-corrected-baseline-20260911` tag。因此現在**可以清掉 b0 worktree**，但我建議仍保留 branch + archive tag，不做 `git branch -D`。這只是 housekeeping，不影響研究關鍵路徑。

B1-credit engineering 可以繼續做到 tests、mutants、2-episode no-training diagnostic、cost benchmark，因為它沒有 optimizer，而且目前 LP 結果已使 B 路線值得預備。但**oracle gate 出來以前不能跨進 training**。

我會把接下來的 controller critical path定成：

**ceiling 補格完成 → A-real/B-real oracle → 套用已宣告 gate → 決定 B1 / B2 / C → 才決定第一個短 training。**

Q9 則可以現在就先整理已穩定的 **H4 + LP**，等 ceiling/oracle 完整後再補第二批；然後把 ceiling final report 交給 Fable phase-2b 做最後一次 validity re-check。

最重要的結論是：**現在不再需要懷疑「這個物理問題到底有沒有足夠 EE 空間」；有，而且很多。真正未決的問題已收斂成「多少可以被 simultaneous per-user learner 拿到，以及需要什麼 credit / information」。** 這比繼續嘗試修舊三個 Catfish 更接近一條可辯護的方法路線。
