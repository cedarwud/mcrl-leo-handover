# 情境特徵化腳本(非 probe)

這些**不是** probe:它們不碰獎勵門檻、不訓練、不消費任何 P1 輸出。
它們是**情境特徵化**,屬於預註冊**之前**的工作,因此不構成 §7.1 的洩漏
(裁決 `CONTROLLER-RULINGS-H-AND-PREREG-2026-08-22.md` §2)。

| 腳本 | 回答什麼 | 報告於 |
|---|---|---|
| `segment_budget.py` | 累積 3.010 dB 增益預算要幾步?segment 為什麼結束? | `W18-REPLY` §2 |
| `dt_sweep2.py` | `Δt ∈ {1,5,10,30,60}` 下三個目標各自退化與否 | `W19-REPLY-DT` §1 |
| `qe_premise.py` | dwell `N` 在幾何上控制得了任何東西嗎?(封閉式) | `W19-REPLY-DT` §3.1 |
| `qe_rekey.py` | 實測 re-key 率,Q-E 新準則的輸入 | `W19-REPLY-DT` §3.1 |
| `signed_drop_dt30.py` | 段末 vs 段內峰值的有號跌幅,以及峰值鏈路功率 | `W19-REPLY-C-COST` §1、`W19-DONE` §0 |
| `two_timescale_check.py` | 驗證兩個時鐘與 TTT 是列舉值;實測 47 子步成本 | `W19-DONE` §1 |
| `outage_frozen.py` | 凍結情境下的 outage / 遮罩衰減 / 鏈路功率 | `W19-DONE` §0 |
| `feasibility_is_fading_free.py` | 可行性判定是否讀衰落(答案:否) | `W22-REPLY` §1 |
| `sensitivity_arm.py` | 三臂並列:主臂 / 敏感度臂(L=6) / 無暖啟動的 outage 與峰值 | `W21-REPLY` §2 |
| `ceiling_and_segments.py` | **權威版**:由 `link_power_w` 算已耗用預算;segment 結束歸因與未設限段長 | `W20-REPLY` §0–1 |

⚠ `signed_drop_dt30.py` 的「峰值跌幅」在暖啟動上線後**失效**(它相對 episode 內的
起點量,而真正的 `τ` 在 episode 之前)。已在檔頭標記 superseded,
權威量請用 `ceiling_and_segments.py`。

全部從 repo 根目錄執行:`.venv/bin/python scripts/<name>.py`。
需要 TLE 語料(`~/demo/tle_data/starlink/tle`)。


⚠ **每個腳本都要用三條獨立的 generator**(`env_rng` 衰落 / `mobility_rng` 使用者 /
策略自己那條),對應 `MODQNTrainer` 實際提供的結構。
用**一條** generator 兼做三件事時,改動其中任何一項都會推進資料流、
連帶重抽另外兩項 —— **那樣量出來的東西不是任何一項的消融**。
2026-08-23 就是這樣讓段齡與衰落耦合、產生了 95 vs 106 的假差異。

## Corrected probe launcher (2026-08-25)

`run_corrected_probes.py` is the only formal corrected P2/P3/P7 entry point.
It reads the frozen artifact and the self-hashed corrective execution addendum,
draws the frozen train-split epoch distribution, executes the full 200/200/100
grid, and refuses an existing output directory.

```bash
.venv/bin/python scripts/run_corrected_probes.py validate
.venv/bin/python scripts/run_corrected_probes.py run \
  --out-dir artifacts/probes-2026-08-25-rerun01
```

`run` is **heavy** (1,400 matched real-TLE episodes; estimated 45–90 minutes on
the Ubuntu server).  Keep it in server `tmux`; local WSL runs only `validate`
and tests.  `scripts/run_probes.py` and `scripts/run_probe_p3.py` remain
historical 8/12-episode diagnostics and cannot unlock P6.

The runner reports P3 separately for all three reference policies.  Only the
frozen `stay-if-possible` policy feeds the predeclared `c1`/`c3` mappings.  Any
mapping change produces complete probe artifacts but a nonzero exit and an
explicit `P6 remains BLOCKED` gate.

每個 P2/P3/P7 arm 都會核對實際 user-decision rows；完整 `src/mcrl`、launcher、
protocol/prereg、依賴版本 fingerprint 在各 arm 前後重驗，live TLE contract 在開始
與結束各驗一次。任何中途漂移或短跑都只能留下 `failed` status，不能解鎖 P6。

## Server training launcher (2026-08-25 R2)

`run_server_training.py` 是 R2 PREREG 的唯一長訓練入口。P6/main 必須先通過
corrected-probe-to-R2 evidence gate；預設 `pipeline`
先驗證 artifact + live environment,依宣告順序跑 P6 三臂,套用凍結的 LR mapping,
再啟動獨立 main run。`main` mode 必須顯式傳 `--learning-rate`,沒有預設值。

```bash
.venv/bin/python scripts/run_server_training.py validate
.venv/bin/python scripts/run_server_training.py pipeline
```

這是 **heavy** 工作,只在 Ubuntu server 的 `tmux` 內執行；本機只跑
`validate`、測試與結果分析。本次三個 P6 arms 加 main 實際耗時
15 h 47 min 23 s；未來重跑仍須依當時硬體重新估時。

launcher 的 `validate` 會先核對 R2 固定 digest/byte SHA、舊 seal、corrected
protocol/manifest/summary/P3 bytes、200,000/198,910 row counts 與 raw p95 exact mapping，
再核對 P6/main/evaluation seeds、frozen reward scales、373-file TLE
hash/split/sampling、sgp4 2.27 accelerated WGS-72 與 train-ready environment。
長跑每 100 回合原子保存完整 trainer/replay/RNG/log
resume state；續跑與既有結果重用都要求 source/dependency/TLE/config fingerprint
一致,不能只憑舊 `status.json` 的 `complete` 字樣。

2026-08-24 17:35 (Asia/Taipei) historical completion receipt: 01:48 啟動的 Ubuntu
server pipeline 已正常退出並寫成 `phase=complete/status=complete`。P6 三臂與
獨立 main 均完成 9,000 episodes；凍結 selector 選出 `α=0.001`。Fresh live
validate 仍通過；結果與完整限制見
`docs/POST-RUN-VALIDATION-2026-08-24.md`。tmux session 不再存在是命令完成後的
正常狀態,不是失敗。
後續 runtime audit 已判定該 run 受 warm-start identity 與 candidate fading
identity defects 影響；它不再是正式 baseline 或 Catfish 判讀 authority。
Server 原始 corpus 已有 375 檔；本 run 保留它不動,以
`/home/sat/mcrl-runtime/tle-frozen-20260820` 的 373-file hard-link view 對齊
frozen file set。只有 host mount path 可正規化,內容與 split/SGP4 gate 不放寬。
