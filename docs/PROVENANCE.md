# 移植來源與逐位元組證明 — W-01(2026-08-21),W-16 修訂(2026-08-22)

**來源 repo**:`~/papers/modqn-paper-reproduction`,`HEAD 6aa281df`
**依據**:`docs/MCRL-NEW-PROJECT-SDD-01-2026-08-21.md` W-01、W-16

> ## ⚠ 授權已於 W-16 修正
>
> SDD §3.8:「逐位元組」在**已知移植了 L-1…L-4** 之後不再是乾淨的 provenance,
> 而是**帶著已知缺陷出貨**。授權改為 **逐位元組 + 一份宣告的補丁帳本**。
>
> **⇒ 本 repo 的 provenance 敘述為:「來源 `6aa281df` + `docs/PATCH-LEDGER.md` 所列的補丁」。**
> 任何未列於帳本的改動即為 provenance 破損。

## 已移植

| 新路徑 | 來源 | 來源 sha256(前 16) | 現況 |
|---|---|---|---|
| `src/mcrl/algorithms/modqn.py` | `algorithms/modqn.py` | `10600c208cc13c68` | **來源 + P-01…P-04**(見帳本) |
| `src/mcrl/env/step_types.py` | `env/step_types.py` | `c4995ba509bbe2e6` | **來源 −P-16**:`PowerSurfaceConfig`、七個 `HOBS_POWER_SURFACE_*`、三組 `POWER_CODEBOOK_*` 與 `StepResult` 的四個功率欄位已刪除(裁決 C-2) |
| `src/mcrl/runtime/q_network.py` | `runtime/q_network.py` | `d11318d61ad93a77` | 逐位元組相同 |
| `src/mcrl/runtime/replay_buffer.py` | `runtime/replay_buffer.py` | `374a73e1b3a5e9da` | 逐位元組相同 |
| `src/mcrl/runtime/state_encoding.py` | `runtime/state_encoding.py` | `723974bcc6db9d5d` | 逐位元組相同 |
| `src/mcrl/runtime/objective_math.py` | `runtime/objective_math.py` | `e8a55760ee1dc4da` | 逐位元組相同 |
| `src/mcrl/runtime/trainer_spec.py` | `runtime/trainer_spec.py` | `0392e66c3e2f4686` | 逐位元組相同 |

合計 2,507 行(移植當下)。

## 新增檔(無來源,不是補丁)

| 路徑 | 用途 | 工作項 |
|---|---|---|
| `src/mcrl/errors.py` | 型別化 fail-closed 例外 | W-16 |
| `src/mcrl/env/action_contract.py` | `NO_OP_ACTION` 與動作索引契約起點(§4A) | W-16,W-03 續寫 |
| `src/mcrl/runtime/finiteness.py` | P-3 有限性電池(G-11) | W-16 |
| `pyproject.toml`、各 `__init__.py` | 套件化與 pytest 設定 | W-16 |
| `src/mcrl/runtime/collapse_metrics.py` | G-3 四項崩潰指標 | W-12 |
| `src/mcrl/runtime/trainer_config_validation.py` | 乾淨版設定驗證器(**新寫非移植**) | W-09/W-10 |
| `tests/` | W-16 補丁的對應測試 + 移植缺口 shim | W-16 |

## 刻意**不**移植(附理由)

| 檔案 | 行數 | 理由 |
|---|---|---|
| `env/step.py` | 1,446 | **已重寫**(W-17)。新檔 `src/mcrl/env/step.py` 與來源**沒有共用一行**:順序是遞推功率 → 可行性 → 服務 → `z` → 干擾 → SINR → rate → 功率 → 獎勵 |
| `env/channel.py` | 407 | **已重寫**為 `env/interference.py` + `env/link_budget.py`(W-06/W-17) |
| `env/power_surface.py` | 390 | **不重寫,整條刪除**:它就是裁決 C-2 移除的載量式 PA。取代者是 `link_budget.recurrence_power_w`(角度遞推) |
| `env/beam.py` | 284 | 同上(固定網格) |
| `env/orbit.py` | 283 | 同上(合成軌道 → SGP4) |
| `runtime/angle_aware_ee.py` | 1,076 | **需改**(dwell `N`);移植時機為 W-05/W-06,貝索 Miller 路由為 W-15 |
| `runtime/popart_online.py` | 188 | `popart_enabled: False`(§8) |
| `runtime/trainer_config_validation.py` | 1,124 | 內容多為 catfish / anti-collapse 驗證,**正是 §8 禁用的東西**;W-09/W-10 另寫乾淨版 |
| `artifacts/{compat,paths}.py`、`models.py` 的 run-metadata / log-row 型別 | — | 本專案不產生那些 artifact 格式;W-12 只移植 checkpoint 四個名字 |

## ⚠ W-01 的規模在 SDD 中被低估(移植時發現)

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

## ⚠ 移植缺口:本樹尚不可 import(W-16 覆核後擴充)

W-01 只記了一項(`state_encoding` 的 import)。**實際有五項**,
其中 `trainer_config_validation` 讓 `TrainerConfig()` **連建構都會失敗**:

| 未解析的相依 | 出現在 | 擁有者 | 現況 |
|---|---|---|---|
| ~~`..env.step`~~ | ~~`modqn.py`、`state_encoding.py`~~ | W-10 | ✅ **已解決**(P-09):三個容器型別重指 `step_types`,`StepEnvironment` 改為 `TYPE_CHECKING` 專用 |
| ~~`..runtime.popart_online`~~ | ~~`modqn.py`~~ | W-09 | ✅ **已解決**(P-05):整條路徑刪除 |
| ~~`..runtime.angle_aware_ee.per_ue_energy_efficiency`~~ | ~~`modqn.py`~~ | W-06 | ✅ **已解決**(P-12):移植進 `runtime/energy_efficiency.py`,與系統級閉包共用 P-7 政策 |
| ~~`.trainer_config_validation.validate_trainer_config`~~ | ~~`trainer_spec.py`~~ | — | ✅ **已解決**:新寫乾淨版(來源 1,124 行多為 §8 禁用項驗證,不可移植) |
| ~~`..artifacts`(4 個名字)~~ | ~~`modqn.py`~~ | W-12 | ✅ **已解決**:移植精簡版(來源 863 行 5 模組 → 本 repo 2 模組) |

## ✅ 五項缺口全部關閉,**測試 shim 已整個刪除**

`tests/_port_shim.py` 不存在了。**這棵樹現在真的可以 import,不靠任何 stand-in。**

⚠ **關閉過程中發現的一件事,值得記下**:`trainer_config_validation` 的 stand-in 是個
**寬容的 no-op**。我寫完真的驗證器之後測試照樣全過 —— 因為 stand-in **遮蔽了它**。
「shim 活得比它的擁有者久就是 bug」在這裡不只是過時,而是**主動掩蓋新程式碼**。
`tests/test_no_shim_remains.py` 現在守住這件事:conftest 必須**一行可執行語句都沒有**
(以 AST 檢查,因為文字搜尋會被 docstring 絆倒)。

**W-16 的處置**:不預先做別的工作項,改以**測試專用**的 stand-in
(`tests/_port_shim.py`)在 import 前掛進 `sys.modules`。
每個 stand-in 要嘛**轉出 `step_types` 的正典型別**,要嘛**直接拋錯**——絕不虛構行為。
**擁有的工作項一落地,對應的 stand-in 必須刪除**;shim 活得比它的擁有者久就是 bug。

## 尚未處理

- **訓練器與新環境之間還沒有接頭。** `MODQNTrainer` 消費的是 `StepResult`
  (`rewards` / `done` / `user_states` / `action_masks` 四個欄位),
  W-17 產出的是 `StepOutcome` / `StepObservation`。兩者未接,
  `tests/_fake_env.py` 仍以 `StepResult` 驅動訓練器測試。
- 訓練未跑;訓練屬重計算,另開 brief 並在 Ubuntu server 執行。
  ⛔ 而且 `assert_ready_to_train()` 目前會擋住 —— 見 F-1。

## W-17 新寫的檔(非移植,無來源)

| 檔案 | 行數 | 內容 |
|---|---|---|
| `src/mcrl/env/interference.py` | ~470 | (3.12a)(3.12b) 的兩個和、`RadiatingBeams`、候選表視角 |
| `src/mcrl/env/step.py` | ~700 | `StepEnvironment`、`PhysicsConfig`、`Segment` |

`runtime/bessel.py` 另加 `bessel_j_array`(向量化)。
**純量 `bessel_j` 一個字沒動** —— G-10 的錨點仍量在它身上,
向量版逐元素比對最大絕對誤差 2.9e-16。

## 已解決(先前列於此)

- ~~`state_encoding.py` 的 import 指向舊路徑~~ → W-10 / P-09。
- ~~`epsilon_decay_episodes` 預設 7000 已過時~~ → W-09 / P-06 改為 **2000**
  (已核對:`common_trainer.py:296` 為 2000,來源 9 份 resolved config 中 8 份為 2000)。
