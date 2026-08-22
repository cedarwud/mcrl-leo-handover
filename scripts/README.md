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

全部從 repo 根目錄執行:`.venv/bin/python scripts/<name>.py`。
需要 TLE 語料(`~/demo/tle_data/starlink/tle`)。
