# 給 server 端訓練對話的接手提示(2026-08-24 corrected freeze)

> **Historical only (2026-08-25).** 本檔記錄的是已確認含 warm-start age
> overwrite 與 candidate fading 重抽的舊 pipeline。不得照本檔重用
> 2026-08-24 output 或 checkpoint；corrected rerun 必須使用新的 2026-08-25
> freeze、fresh output directory 與 source fingerprint。

**工作類型:重計算。** 本輪已在 Ubuntu server 完成；三個 P6 arms 加獨立
main 實際耗時 15 h 47 min 23 s。任何完整重跑仍只在 server 執行,不要在本機
(WSL2)跑。

**Completion receipt (2026-08-24 17:35 Asia/Taipei):** 01:48 在
`/home/sat/mcrl-leo-handover` / tmux `mcrl-p6-main-20260824` 啟動的唯一
pipeline 已正常完成並退出。server full suite 為
`792 passed, 1 skipped in 191.50 s`;fresh live validate 仍通過 digest
`01b0d85c...c022` 與 TLE file-set hash `427e6a91...38fe9`。P6 三臂均為
finite/complete,selector 選出 `α=0.001`,獨立 main 完成 9,000/9,000 episodes。
Post-run controller evidence、B17 限定判讀與完整 hashes 見
`POST-RUN-VALIDATION-2026-08-24.md`。這是 empirical completion,但仍不自動成為
Chapter 5 或新機制的 authoring authority。

Server 原始 TLE 目錄目前有 375 檔(較 freeze 多 2026-08-21/22)。兩份新檔與原
corpus 均未刪改；本 run 的預期路徑指向
`/home/sat/mcrl-runtime/tle-frozen-20260820` 這個 373-file hard-link view。
`tle_root` 是 host mount path,source-digest comparison 只正規化這一欄；live gate
仍精確核對每檔 hash/date、file-set hash、split/sampling 與 SGP4,不得以此放寬 corpus。

---

## 0. 你唯一需要的上下文

```
~/papers/mcrl-leo-handover/artifacts/PREREG-FROZEN-2026-08-24.json
digest  01b0d85cedbd67f80a24c2adf7ff4181c728070111d06334e8dc55f07f52c022
```

**這份凍結檔就是契約。** 18 個區段,涵蓋星曆、切分、抽樣、D2、天線與鏈路預算、dwell、
獎勵、動作與狀態、訓練、probe grid、門檻、停止規則、參考策略、指向格、資料完整性、
選取映射、段落暖啟動與 corrected-refreeze provenance。

2026-08-23 原 seal 保留在同一目錄,不可修改或刪除。它的 self-digest 是
`d35ddaff…`,但有 stale N=3 敘事且只命名、未操作化 P6。2026-08-24 corrected seal
明列 supersession 與授權,才是這次 run 的 current contract。

⛔ **不要讀 `docs/MCRL-NEW-PROJECT-SDD-01-*.md`。** 它是設計階段的文件,已被
二十餘輪裁決取代,目前仍帶著三個錯的東西:狀態維度寫 **125**(現行是 112)、
`θ^R_min` 寫 **2.05°**(現行 2.498°)、以及 `m^e` 一條**已被撤回**的保留裁決。
凍結檔與程式是對的,SDD 不是。

⚠ **digest 的重算方式**:它**不是**檔案位元組的 sha256
(新檔 byte SHA 是 `8c5603c94ecdebf65d5c5aee72fcd0c0feb0cfb94eeea6f0cfe6a0f11a3478b3`)。
自指雜湊必須排除 `digest` 欄位本身,要取 `{schema, sections, holdout}`、
`json.dumps(sort_keys=True, ensure_ascii=False)` 之後 sha256。
`PreregRecord.verify()` 已經做這件事,直接用它。

---

## 1. 動手之前先做的五件事

1. `PreregRecord.verify()` 通過 —— 確認凍結檔沒被改過;
2. launcher 的 P6 protocol guard 通過 —— 三臂、P6/main/evaluation seeds 與
   frozen reward scales 完全一致;
3. 373-file TLE manifest、file-set hash、split/sampling、sgp4 `2.27` accelerated
   WGS-72 與 corrected freeze 完全一致;
4. `assert_ready_to_train()` 通過 —— 四個選取映射(Q-D/E/F/G)都已關閉;
5. 全套測試綠(本機基準是 **792 passed, 1 skipped**,但 server 必須重跑,
   不可沿用本機聲明)。

**任何一項不過就停下來回報,不要繞過。** 這些守衛存在的理由是:
凍結之後真正的風險不是有人改那份 JSON,是有人改它所描述的程式。

---

## 2. 要跑什麼

### P6(唯一需要短訓練的 probe)

`α ∈ {0.01, 0.003, 0.001}` 依此順序各跑 9000 回合,三臂共用凍結的
training/environment/mobility seed triplet,回報 G-3 的崩潰四項
(`active_beam_count`、`argmax_agreement`、`q_margin`、`q_entropy`)。
`q_margin` 須正規化。Run 前的預期是 `α = 0.01` 會發散；實際上它保持 finite
並完成 9,000 episodes。G-11 的規則仍是非有限值即拋錯中止、不得靜默續訓；
只是這次沒有觸發。不得為了符合舊預期而改設定重跑。

每個 finite arm 只評估 **final-episode policy**,不用 observed-best checkpoint。
三臂共用十個 train-split evaluation seeds,holdout 不進 P6。唯一主選取量是十個 seeds 的
**平均校準 scalar reward**;不完整/非有限臂排除,完全同分照宣告 sweep 順序。
random-near-tie、Q perturbation 與 cross-seed ranking 全是診斷,不得改選 LR。
若沒有任何 finite complete arm,整條 pipeline 停止,不得啟動 main。

near-tie 以每個 user/decision 的 valid scalarized-Q range 正規化,門檻 1%;flat row
讓所有 valid actions 入組,專用 RNG 均勻抽樣且 environment/mobility streams 與 greedy
配對。perturbation 是 `σ = 0.01 Q_range` 的 iid Gaussian,每列 32 replicates,回報
greedy retention 與 non-tied pairs Kendall tau；cross-seed 回報 modal-order fraction
與 Kendall W。兩者沒有 pass threshold。

### 主訓練

9000 回合 × 10 步,`β = 0.9`,`Ω = (0.5, 0.3, 0.2)`,批次 128,
`ε` 由 1 線性降至 0.01 共 2000 回合,每 50 回合同步目標網路。
學習率是**受控變因**,主結果採用哪一個值由 P6 決定 —— 不要挑一個預設值跑。

唯一入口:

```bash
.venv/bin/python scripts/run_server_training.py validate
.venv/bin/python scripts/run_server_training.py pipeline
```

`pipeline` 會在 P6 summary 寫出 selected LR 後才把 phase 切成 `main`。
manual `main` 必須顯式傳 P6 選出的 `--learning-rate`;CLI 不提供預設。

每 100 回合寫一個 atomic resume checkpoint,包含 online/target networks、optimizer、
replay、train/environment/mobility RNG、torch CPU RNG、跨 episode 的 segment-age RNG
與 contiguous logs。重新執行同一命令會在相同 fingerprint 下從下一個 absolute
episode 繼續；epsilon 與 target-sync cadence 不重置。fingerprint 包含 source bytes、
corrected prereg digest、TLE file-set hash、依賴版本、所有 frozen seeds、LR、reward
scales 與實際 TrainerConfig。只看 `status = complete` 不算可重用:final checkpoint、
9000 筆有限連續 logs、hashes 與(對 P6)十個完整 matched evaluations 必須全在。

完成後核對而不改狀態:

```bash
sed -n '1,160p' artifacts/training-2026-08-24/pipeline-status.json
sed -n '1,200p' artifacts/training-2026-08-24/p6-summary.json
sed -n '1,200p' artifacts/training-2026-08-24/main/status.json
```

tmux session 與 worker PID 在 pipeline 完成後不再存在是正常狀態。

---

## 3. 這次訓練的真正用途:它是論文貢獻框架的 go/no-go

不要把它當成「產出一個 baseline 數字」。B17 把第一個里程碑定義成回答四個問題,
其中第一題只有訓練跑得出來:

> **shared-Q + argmax 在新環境還會不會崩潰?**

而 B17 自己接著寫:

> ⚠ 必須預備兩套敘事:拿掉 `v_max` 後碰撞只稀釋頻寬、不拒絕服務,崩潰可能大幅減輕。
> **若新 baseline 不崩潰:「協調是 EE 大槓桿」不會重現、catfish 要打破的同質化可能
> 不存在,整條貢獻線須重想。**

⇒ **「不崩潰」是一個要照實回報的結果,不是一個要調參數去避免的失敗。**
若跑出來不崩潰,回報,不要改設定重跑。

### 讀崩潰指標時的三個陷阱(都已凍進 PREREG)

1. **用貪婪版,不是執行版。** 兩個動作衍生指標各有兩種:
   `active_beam_count` / `argmax_agreement` 由**貪婪 argmax** 計算,回答 B17 Q1;
   `*_executed` 是 epsilon-greedy 實際執行的,它是「實際點亮了幾支波束」。
   `ε` 要 2000 回合才降到 0.01 而訓練跑 9000 ⇒ **執行版在前五分之一量到的主要是隨機策略。**
2. **兩點取樣,看差值也看絕對值。** 每回合取第一步與最後一步,`collapse_drift` 是兩者之差。
   ⚠ `steps_per_episode = 10`,兩點只隔 9 步 ≈ 4.5 分鐘,回合內能發展多少集中受此上限 ——
   **`collapse_drift ≈ 0` 不能讀成「策略不崩潰」**,必須並看 `collapse_first` 的絕對水準。
3. **四項全零是「什麼都沒量到」,不是「沒有崩潰」。** 缺樣本時程式會拋錯而不回報零,
   若你看到零,那是真的零。

### 獎勵記錄

逐目標均值**校準前與校準後都有記**。B17 第二題(三個目標的平衡)要的是校準後的,
因為有效取捨是 `ω_j / c_j`。⚠ 已知參考策略下的有效占比是
**43.5% / 14.3% / 42.2%**,而名目權重是 50 / 30 / 20 —— `r2` 稀疏所以只拿到名目的一半。
**訓練後這個比例會變**(換手變多),那個變化本身就是要回報的東西。

---

## 4. 已知的兩個開放結論(不要試圖「修好」)

- **三項幾何遮罩與功率閘在參考策略下不 binding**(`|A_u| = 28`,outage 0.94%)。
  這是量測結果,已寫進 ch5。訓練後的策略可能不同 —— 照實回報差異。
- **`r1` 與 `r3` 在候選層同向**(`argmax(r1) ∈ best(r3)` 恆為真),真正的張力是
  `{r1, r3}` 對抗 `r2`。這已答了 B17 第四題(keying 本來就對,後續該加強探索)。

---

## 5. 回報格式

跑完回報給 controller(本機),內容:

1. `PreregRecord.verify()` 與 `assert_ready_to_train()` 的結果;
2. P6 三臂的崩潰四項,以及 `α = 0.01` 是否如預期中止(本輪答案:否,finite complete);
3. 主訓練的崩潰四項(貪婪版與執行版並列)、`collapse_first` 與 `collapse_drift`;
4. 三個目標的校準後貢獻占比,與參考策略下的 43.5 / 14.3 / 42.2 對照;
5. **B17 第一題的答案:崩潰了沒有。** 這一題的答案決定後面整條路怎麼走。

⛔ 過程中若需要改任何凍結值,停下來回報,不要自行修改後續跑。
凍結檔改了,這一輪的結果就不再是預註冊的。
