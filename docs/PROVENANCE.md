# 移植來源與逐位元組證明 — W-01(2026-08-21)

**來源 repo**:`~/papers/modqn-paper-reproduction`,`HEAD 6aa281df`
**依據**:`docs/MCRL-NEW-PROJECT-SDD-01-2026-08-21.md` W-01

## 已移植(逐位元組相同,sha256 已驗)

| 新路徑 | 來源 | sha256(前 16) |
|---|---|---|
| `src/mcrl/algorithms/modqn.py` | `algorithms/modqn.py` | `10600c208cc13c68` |
| `src/mcrl/env/step_types.py` | `env/step_types.py` | `c4995ba509bbe2e6` |
| `src/mcrl/runtime/q_network.py` | `runtime/q_network.py` | `d11318d61ad93a77` |
| `src/mcrl/runtime/replay_buffer.py` | `runtime/replay_buffer.py` | `374a73e1b3a5e9da` |
| `src/mcrl/runtime/state_encoding.py` | `runtime/state_encoding.py` | `723974bcc6db9d5d` |
| `src/mcrl/runtime/objective_math.py` | `runtime/objective_math.py` | `e8a55760ee1dc4da` |
| `src/mcrl/runtime/trainer_spec.py` | `runtime/trainer_spec.py` | `0392e66c3e2f4686` |

合計 2,507 行。

## 刻意**不**移植(附理由)

| 檔案 | 行數 | 理由 |
|---|---|---|
| `env/step.py` | 1,446 | **要重寫**(W-02/W-03:TLE+SGP4、D2、dwell) |
| `env/channel.py` | 407 | 同上 |
| `env/power_surface.py` | 390 | 同上 |
| `env/beam.py` | 284 | 同上(固定網格) |
| `env/orbit.py` | 283 | 同上(合成軌道 → SGP4) |
| `runtime/angle_aware_ee.py` | 1,076 | **需改**(dwell `N`);移植時機為 W-05/W-06 |
| `runtime/popart_online.py` | 188 | `popart_enabled: False`,未使用 |

## ⚠ W-01 的規模在 SDD 中被低估(本次執行時發現)

SDD r3 的 W-01 寫「移植 `algorithms/modqn.py`(vanilla,逐位元組),規模:**小**」。

**實測**:`algorithms/modqn.py` 的相依閉包為 **15 檔、6,626 行**,
且包含 `env/{step,channel,power_surface,beam,orbit}.py` 共 **2,810 行——正是要被取代的部分**。
直接逐位元組移植會把舊環境整組拖進新 repo,**與開新專案的目的相反**。

**解法(已採用,且有先例)**:在**介面處切斷**。
`env/step_types.py` 只依賴 stdlib + numpy,是完整的容器型別契約;
`paper_baseline/paper_simple_env.py`(700 行)證明**只 import 它就能建出完整環境**,
且讓 `algorithms/modqn.py` 保持 byte-unchanged 運行。

**⇒ 新環境寫在 `step_types.py` 的契約之上,舊 `env/*` 一律不進來。**
**⇒ SDD 的 W-01 敘述須更新:不是「小」,而是「小,但必須在 `step_types` 介面處切斷」。**

## 尚未處理

- `state_encoding.py` 目前 `from ..env.step import UserState`,**需改指 `step_types`**
  (`UserState` 的正典定義在 `step_types.py`);此為 W-10 的一部分,本次未動,
  故移植後的樹**尚不可 import**。這是刻意的:W-01 只負責凍結來源與證明逐位元組同一。
- 未建 venv、未跑測試。
