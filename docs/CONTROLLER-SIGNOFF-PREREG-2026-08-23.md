# PREREG 簽核(2026-08-23)

**簽核通過。** `artifacts/PREREG-FROZEN-2026-08-23.json`,
digest `d35ddaffda580c8c109f758372956d41aa947b9eb3915d742f3f5f9b7aaecf08`。

## 1. 我獨立驗過的

**digest 自己重算過** —— 讀入 JSON、取 `{schema, sections, holdout}`、
`sort_keys=True, ensure_ascii=False` 序列化後 sha256,得到與檔案記錄相同的值。
(檔案原始位元組的 sha256 是 `0deefc44…`,與記錄不同 —— 那是正確的,
自指雜湊必須排除 digest 欄位本身。我先算了位元組雜湊、看到不符,才去讀 `_hashable()`
確認涵蓋範圍。**這一步值得留在紀錄裡:下一個人重算時會遇到同一個「不符」。**)

W-22 §6 的十二項逐一對過,全數符合:

| 項 | 凍結值 |
|---|---|
| 決策步 | `30.080000000000002` s |
| 量測時鐘 / TTT | 640 ms / `ttt_seconds 1.28`、`ttt_steps 2` |
| Q-E dwell `N` | **4** |
| `segment_age_steps` | 6,`L_provenance` 註明「自然結束(換手或 outage)的段長中位數」 |
| 狀態維度 | 112,`contract_block_enabled = False` |
| 學習率 | `CONTROLLED VARIABLE — not a default` |
| 校準 | `calibration_enabled = True` |
| 選取映射 | Q-D / Q-E / Q-F / Q-G 四項齊 |
| `A_zen` | 0.25 dB |
| 遲滯 | 50 km |
| 門檻 | 0.95(`measured 0.9517`)/ 300 km / 1e-3 / 1e-3 |
| 種子 | 20260822 + salted digest |

**追加裁決 A 與 B 也都在:**

- `actions_used`:兩個動作衍生指標由**貪婪 argmax** 計算並明寫「that version answers
  B17 Q1」,執行版另記 `*_executed`;
- `sampled_at`:**first and last decision step**,並寫明只取第一步會系統性漏掉
  回合內發展的集中。

## 2. 你們自己加的兩件我特別認可

- **「缺樣本時拋錯不回報零」** —— 四項全零讀起來像「沒有崩潰」,真正意思是
  「什麼都沒量到」。這個區別在一份 9000 回合的 log 裡沒有人會回頭查。
- **`steps_per_episode = 10` 的限制已進帳本** —— 兩點之間只隔 9 步 ≈ 4.5 分鐘,
  所以 `collapse_drift ≈ 0` 不能讀成「策略不崩潰」,必須並看 `collapse_first` 的絕對水準。
  **這是你們自己對自己新加的指標設下的解讀邊界**,而那通常要等別人誤讀之後才會出現。

## 3. 八個稽核面向,現在全部查過

| # | 面向 | |
|---|---|---|
| 1 | 實作 vs 裁決(C-1…C-15、F-1/F-2、Δt/TTT、Q-D/E/F/G) | ✅ |
| 2 | 範圍 vs SDD §5 工作項 / §8 禁用清單 | ✅ |
| 3 | **驗收閘 G-1…G-12 的判準是否實際達成** | ✅ **本輪補完** |
| 4 | 凍結值 vs 裁決(17 節) | ✅ |
| 5 | probe 義務 vs SDD | ✅ |
| 6 | 論文 ↔ 符號表 ↔ 簡報 | ✅ |
| 7 | 決策紀錄 B1–B17 vs 實作 | ✅(B4 已裁,其餘符合或已被取代) |
| 8 | 結果能否支撐論文主張 | ✅(B17 已標示風險) |

第 3 項本輪查的是**判準而不是程式存在**:G-1 有 `worst_km < G1_POSITION_TOLERANCE_KM`
的實測斷言、G-2 有 `LINK-BUDGET-NOTES.md §6` 的逐項 delta ledger、
G-7 有錨點 + 單調性 + 平台段 + 斜率四種斷言、G-9 有 `G9-TEST-MAP.md` 的 T1–T12 對照、
G-10/11/12 的測試以斷言為主。**不是只有程式在那裡。**

## 4. B4 §3:請做

ch5 的出處敘述我已寫入三語版(`COHERENCE PASS`):

> 在 $V=39$ 下單顆衛星所有波束同時滿載輻射 $39\times1.65=64.3$ W,低於 HOBS Table I
> 的 LEO 最大發射功率 $P_{\max}=50$ dBm $=100$ W,故該上限與所引文獻的每星功率預算
> 相容;本研究不另設每星上限,此處僅作預算相容性檢查。

**你們要做的兩件小事:**

1. `V · p_max ≤ 100 W` 寫成測試 —— 讓它在 `V` 或 `p_max` 任一變動時會亮,
   而不是只活在論文的一句話裡;
2. `BEAM_POWER_MAX_W` 的 docstring 記下這個相容性檢查與它的出處。

⚠ 這兩件**不改任何凍結值**,`p_max` 仍是 1.65 W。

## 5. 下一步

P6 與 9000 回合訓練上 server 另開對話。這一份凍結檔與它的 digest 是那邊唯一需要的
上下文 —— **不要叫新對話讀 SDD**,它仍帶著 125 維、2.05°、以及 `m^e` 的舊裁決。
