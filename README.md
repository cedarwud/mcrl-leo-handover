# mcrl-leo-handover

MCRL(Multi-Catfish Reinforcement Learning)LEO 多波束換手 — 乾淨重建。

**狀態:2026-08-25 corrected probes 已完整跑完，R2 PREREG 已依預先宣告的
Q-F mapping 封存。修正後 `c1 = 2029238.4328742754`、`c3 = 6`；R2 的 evidence
chain、固定 digest/bytes、P6 protocol 與 CLI gates 均由測試鎖定。P6/main 仍須
在 Ubuntu server 通過 live TLE/environment validation 後才可執行。server gates
與完整測試已通過，corrected pipeline 已於 2026-08-25 11:50 Asia/Taipei 進入 P6；
尚未宣稱新的 trained baseline 完成。本機與 server 均為
**819 passed, 1 skipped**。**

**Historical server receipt (2026-08-24 17:35 Asia/Taipei):** Ubuntu server
`/home/sat/mcrl-leo-handover` 的唯一 pipeline 已完成。P6 三個 9,000-episode
arms 全數 finite/complete,凍結 selector 依十個 shared evaluation seeds 的平均
calibrated scalar reward 選出 `α=0.001`;獨立 main 亦完成 9,000/9,000 episodes。
總 elapsed 15 h 47 min 23 s,final checkpoint/log hashes 均與 status 記錄一致。
`α=0.01` 沒有如先前預期發散,但呈現近單波束崩潰且 selector 分數最低。
完整 post-run 判讀見 `docs/POST-RUN-VALIDATION-2026-08-24.md`。後續稽核確認
warm-start age overwrite 與 candidate fading 重抽；因此這是 defective-runtime
completion evidence,不是正式 baseline、Chapter 5 或新機制的 authoring authority。
Server 的 live corpus 已多出 2026-08-21/22 兩天；原 375-file 目錄未刪改，
本 run 以 `/home/sat/mcrl-runtime/tle-frozen-20260820` 的 373-file hard-link view
消費 frozen file set。host-specific `tle_root` 只作 mount 定位，所有內容 hash、日期、
split、sampling 與 SGP4 欄位仍由 live gate 精確比對。

本次 server 實測一個 episode(100 位使用者、10 步、真實 TLE)約 **1.6 秒**:
星曆 → D2 → dwell → 候選表 → 遞推功率 → 可行性 → 服務 → 干擾 (3.12a)(3.12b)
→ SINR (3.13) → rate (3.14) → 功率 (3.15)-(3.16a) → `r1`/`r2`/`r3`。

以凍結常數量測的**暖啟動 OFF 敏感度臂**(12,000 個決策步):
**outage 0.0000**、每步 41 支波束輻射、
`P^N` 258.4 W、SINR p05/p50/p95 = 11.7 / 16.4 / 19.0 dB。
`assert_ready_to_train()` **通過**。這個守衛只回答 Q-D/Q-E/Q-F/Q-G 的選取映射
是否已關閉；Q-C 與 G-5 在現行權威集沒有 active 定義,不虛構成 gate。
它不取代預註冊 digest、P6 協定與完整測試守衛。

**移植來的 `MODQNTrainer` 已能在真實星曆上跑真實 episode**
(`runtime/trainer_env.py`,W-18)。

Q-D(`r3` 尺度)、Q-E(dwell `N = 4`)、Q-F/Q-G(獎勵校準尺度)均已關閉。
凍結之後任何門檻、選取規則或訓練協定的更動都是「看過資料才改」,
正是預註冊要防的洩漏。

**現行時間設定:**`Δt = 30.08 s` 已定案(2026-08-23 裁決),
`H = 10` 與 `β = 0.9` 未動。
   D2 走**雙時間尺度**:量測/觸發 640 ms、決策 30.08 s、TTT **1280 ms**
   (TS 38.331 的列舉值,精確)。segment 於 episode 開始前已暖啟動。
   ⛔ **後果:`outage` 不再是 0,而是 0.0079** —— 功率上限成為作用中的約束。
   見 `docs/W19-DONE-2026-08-23.md` §0。

- 預註冊權威:`artifacts/PREREG-FROZEN-2026-08-25-R2.json`
  (self-digest `3a920671dcce62075b1a21362d392b6c370c99979cba70d72a513da9ae9773f4`;
  byte SHA-256 `8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543`)
- corrected probe execution addendum:
  `artifacts/CORRECTED-PROBE-PROTOCOL-2026-08-25.json`
  (self-digest `0d778ccdbbaf016310e1b541c421d98f95b06c993bc509a637ef37d386824560`);
  這是結果前封存的 post-freeze seed/epoch 補充，不回溯宣稱原 prereg 已包含該 seed
- 歷史 seal:`artifacts/PREREG-FROZEN-2026-08-23.json`、
  `artifacts/PREREG-FROZEN-2026-08-24.json` 與
  `artifacts/PREREG-FROZEN-2026-08-25.json` 均保留原 bytes 與 digest,不得改寫；
  runtime correction 的理由與授權見
  `docs/CONTROLLER-RULINGS-MODQN-RUNTIME-CORRECTION-2026-08-25.md`
- 現行裁決:`docs/CONTROLLER-RULINGS-*.md`
- 參數:`~/papers/modqn-paper-reproduction/docs/NEW-PROJECT-PARAMETER-SPEC-2026-08-21.md`
- 移植證明:`docs/PROVENANCE.md`
- **補丁帳本**:`docs/PATCH-LEDGER.md` ← 任何偏離來源的改動都必須在此有一列
- 星曆層量測:`docs/EPHEMERIS-NOTES.md`(高度、覆蓋率、通過時長皆為量測值)
- G-9 驗收對照:`docs/G9-TEST-MAP.md`(T1–T12 → 測試名)
- D2 量測:`docs/D2-NOTES.md`
- 鏈路預算/天線/dwell 量測:`docs/LINK-BUDGET-NOTES.md`
- `r3` 與執行遮罩:`docs/R3-AND-EXECUTION-MASK-NOTES.md`
- **偏離登記表**:`docs/DEVIATION-REGISTER.md`(`X` 級偏離,每條都須在論文明講)
- **遷移表**:`docs/MIGRATION-TABLE.md`(舊名 ↔ 新名 ↔ 論文符號,W-14)
- 已裁決:`docs/CONTROLLER-RULINGS-2026-08-22.md`(C-1…C-15)、
  `docs/CONTROLLER-RULINGS-W17-2026-08-22.md`(F-1/F-2);
  提問與量測回報見 `docs/CONTROLLER-QUESTIONS-2026-08-22.md`、
  `docs/CONTROLLER-FINDINGS-W17-2026-08-22.md`
- **PREREG 草案(歷史產生來源)**:`docs/PREREG-DRAFT.md`;執行時以凍結 artifact 為準

**B6 現行 cadence:**四個 NORAD slot 身分只在 dwell 邊界重建,段內固定；
D2 eligibility/TTT/margin/range-rate 與幾何每個 decision 刷新。失格列立即 mask、
同一身分可段內重入、新衛星延至下個邊界；四列全失效走既有 no-op。

**corrected probe 入口:**`scripts/run_corrected_probes.py`。舊 8/12-episode
scripts 只保留為歷史 diagnostic；正式 runner 依 frozen grid 跑 P2/P3/P7，且若
served-step `c1` 或 `c3` mapping 改變就保持 P6 關閉。

**重訓入口:**`scripts/run_server_training.py`。corrected probe gate 通過並完成必要
的 corrective refreeze 後，預設 `pipeline` 依序做三臂 P6、
凍結選取規則、獨立 main run；manual `main` 沒有 learning-rate 預設。
每 100 回合原子保存網路/optimizer/replay、三條 NumPy RNG、torch RNG、跨回合
segment-age RNG 與 logs；重跑只在 fingerprint 完全相同時續跑。fingerprint 包含
當前 source bytes、frozen digest、TLE file-set hash、依賴版本、seeds、LR 與實際
TrainerConfig。名義 `complete` 若缺 checkpoint/log/evaluation 證據不得重用。

## 開發

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[train,test]'
.venv/bin/python -m pytest
```

## 禁用清單(SDD §8)

拍賣式解碼、capacity penalty、`v_max`/`k_cap`、
`χ`+z-score 預設開啟、Double-DQN 共用純量化動作、任何形式的 catfish。
保留程式碼是為了日後消融,不是為了現在用(G-6 以 grep 零命中驗收)。

⚠ **執行遮罩 `m^e` 已不存在**(裁決 C-11)。該日稍早曾記為「保留為環境端帳務、
連線恆等式維持三閘」,**那一版已被控方撤回**。定案是**兩閘 `x = a·z`**:
`m` 只作決策時遮罩,不進連線恆等式;選上與被服務之間的閘是**逐鏈路功率可行性**。

另:`PowerSurfaceConfig` 與七個 `HOBS_POWER_SURFACE_*` 模式已由 **P-16 整組刪除**
(裁決 C-2「載量式 PA 整條移除」)。功率模型是**角度遞推**,**沒有模式開關**。
