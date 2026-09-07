# HANDOFF — 全文文字/公式/篇幅對齊 phase（2026-07-20 晚交接）

> ## ⛔⛔ 2026-07-21 更新：本檔多處已被取代，開工先讀 `GENRE-RULES.md`
>
> **規則權威已移到 `thesis-mc/GENRE-RULES.md`**（生效版體裁準則，含適用範圍與實測依據）；
> 推導過程、跨模型審查紀錄與被推翻的版本在 `WRITING-RULES.md` 2026-07-21 條目。
> 狀態用 `python3 tools/genre_scan.py` 讀，不要用本檔的舊數字。
>
> **本檔已作廢的部分（逐項）**：
> 1. **§1 的基線表**：ch1 的數字已過期（現況＝1937 中文字）。更嚴重的是 **ch3「+87%」／ch4「+43%」不可用**
>    ——那是拿 `thesis.pdf` 的 pdftotext 詞數當參考值，而該文字**含數學符號**（ch3 有 11.1% 的 token 是
>    單字母、ch4 9.5%），我方詞數則已去數學。改用中文對中文量得 ch3 = 3.21×、ch4 = 2.45×，兩把尺差約兩倍。
> 2. **§1 的「ch3 大減／ch4 大減」指示作廢**（USER 2026-07-21）：公式數、演算法數與角度感知功率模型的複雜度
>    是**真實內容差異**，不是冗贅；而且**現況有些公式交代不清楚，方向可能是要補不是刪**。
>    ch3／ch4 的處理原則見 `WRITING-RULES.md` 的「ch3／ch4 不是純刪」條。
> 3. **§1 的 ch6「+4.9×」不可用**：`ris.docx` 的 ch6 中文只翻了 1 段（英文 25 段 vs 中文 1 段），中文尺是壞的。
> 4. **§2 的體裁事實**已被五章 hold-out 取代（見 `GENRE-RULES.md` §1）。其中兩個直覺被推翻：
>    「方法章需要長句」（參考的方法章句子最短，平均 26）、「等人只能用一次」（參考 ch2 用 11 次）。
> 5. **§6 的「摘要 4 段」已還原為單段**（參考亦為單段），並補回結果佔位。
>
> **仍然有效**：§0/§0b 的開工紀律與派工授權、§3 的公式編號欠帳（兩套編號機制、8 條字母後綴式號、
> 重編號需中英逐位元同步＋交叉引用全掃）、§4 的護欄、§5 的建置與 interleave 指令。
>
> **2026-07-21 進度**：摘要與 ch1 已完成並經 codex＋agy 跨模型審查後修訂；體裁準則已發布；
> 已確定規則（三個塑形的術語遷移）已套到 ch3／ch4 的**文字面**。
> **ch2 已完成**（USER 兩項裁決皆＝比照 CDRL：2.1 全面具名、去（一）–（四）編號）：
> 1662 字＝1.05×、平均句長 40、最長句 84、>100 字句 0、每段字數全落回參考帶內；
> EN 已派 haiku 重譯並經 controller 三項獨立驗證；兩份 docx 已重建。
> 診斷與被刪命題清單＝`scratch/ch2-genre-review-2026-07-21/`；決策記錄＝`WRITING-RULES.md` 頂部。
> **ch3／ch4 逐式盤點＝已完成（2026-07-21）**，結論如下（盤點原檔在
> `scratch/ch3-ch4-equation-audit-2026-07-21/`＝gitignored，會隨機器消失；本節是追蹤得到的那份）。
>
> **★ 改寫問題定義（推翻交接檔 §1 的「ch3 大減／ch4 大減」）**：以「每式分到的散文字數」量，
> 參考 ch3＝244 字/式、ch4＝267 字/式；我方 **ch3＝198（0.81×，每式解釋得更少）**、
> **ch4＝452（1.69×；扣掉 1598 字圖說後 367＝1.38×）**。
> ⟹ **ch3 長是因為式子多 4 倍，不是話多 → 方向是補**；**ch4 的餘裕在散文側 → 方向是壓**。兩章處方相反。
>
> **已完成**：式號機制統一到 `\tag`（26 條 matrix 轉換，含 3 組「一個 `$$` 塞兩式」拆分；式號零位移，
> `fd5ff5d8`）｜§3.3 揭露缺口補齊（3.21 需求加權 vs 3.32 均分）｜無編號的 CN 運算子式編為 3.35a（`5d05706f`）。
>
> **ch3 待辦（USER 已同意方向，逐條需 USER 過目）**
> 1. **補定義順序**：式 3.12 的 $I^{intra}/I^{inter}$ 用完**無定義也無指路**（正式定義晚 5 式在 3.13/3.14）＝唯一的真缺陷；
>    式 3.8 的 $f_{c}$ 命名藏在式 3.9 之後；式 3.12a 引入句說「反解式 (3.15)」但 3.15 在 67 行後。
> 2. **補用途句** 4 條（3.1、3.2、3.8、3.17）——CDRL 體裁是每個符號定義都帶「它管什麼」的角色子句。
> 3. **補引入句** 7 條（3.22–3.25、3.33–3.35）＝弱引入句。⚠ §3.1 的 26 條引入句**全部合格**，不必動。
> 4. **式 3.30** 的目標索引 $j$ 沒有在正文寫出 $j=1,2,3$（只在不進 build 的符號表裡）。
> 5. **併番候選** 4 條（3.2、3.10、3.12、3.17）——降低式數以拉高每式解釋密度。
>
> **ch4 待辦**：散文餘裕 **1060 中文字**（重複命題 915／同義反覆 105／冗語 40）。最大兩塊＝
> 「部署時不變／鯰魚移除」ch4 內講 8 次、「容量上限只在環境端」跨 ch1/ch3/ch4 講 5 次。
> **USER 裁決＝收，但要逐條給他看**（附保留哪處／刪哪處／刪的改成什麼＋依 §0.1 造被刪命題清單）。
> ⚠ ch4 另有兩個未定變數：**圖說 1598 字**（圖大部分會換掉，USER 說先擱著）與
> **演算法回插**（現正文零演算法；兩個 pseudocode 停在 `deferred/algorithms-for-final.md`，參考論文只有 1 個）。
>
> **⛔ 兩條對帳紀律**：(a) `WRITING-RULES` 的「已套用」宣稱不可信（它自己記了這條教訓）——一律 grep 檔案內容；
> (b) `notation-table.md` **不進 build**，只在該表定義的符號＝論文裡未定義。實測全書真正未定義 0 條、
> 僅在符號表 1 條（式 3.30 的 $j$），真正的病是**順序**與**用途句缺席**，不是缺定義。
>
> **CDRL 公式體裁規格**＝`scratch/ch3-ch4-equation-audit-2026-07-21/CDRL-EQUATION-TEMPLATE.md`
> （逐頁抽取＋原文引證；核心＝引入句／式／where 補殘餘符號／用途句 的三明治，以及「參考論文沒有符號表」）。
> **未了帳**：ch3／ch4 的長度尺未定；圖檔仍畫兩類階層（圖 4-2／4-3／4-7，在圖檔 session 手上）⟹
> 依 `GENRE-RULES.md` §3.T **不得宣稱術語遷移已完整套用**；`GENRE-RULES.md` §6 的兩個獨立檢查未做。

> **任務（USER 指示,binding）**:調整論文全文的文字內容、公式寫法與定義方式、各章篇幅,
> 目標＝與參考論文 `archive/catfish-route/catfish/thesis.pdf`（CDRL,**英文定稿**,本文 68 頁）的
> **文字長度、公式寫法、段落設計一致**;**忠實沿用參考論文自己的體裁,不自創排版與寫法**
> （＝figures 線 RULE 0「忠實優先」的文字版:參考論文是人寫的,照抄體裁不會有 AI 味）。
> **從第一章開始,逐章等 USER 指令**;ch3/ch4 是重災區;**ch5/ch6 本 phase 凍結不動**。
> 圖（架構圖/結果圖）、演算法有效性、實驗數據**全部不在本 phase 範圍**。

## 0. 開工檢查（新 session 第一件事,跑完回報「基線確認完成」後停下等指令）

1. 依 `docs/devkit/succession-brief-opus.md` §0 讀序開工:`CURRENT-STATE.md` 頂部 banner →
   `.agent-memory/MEMORY.md` 前兩節 → AGENTS.md devkit 區;接班簡報本身也要讀（⚠ 其 §2 是
   07-10 快照,與現況衝突處以本檔 §0b 為準）。
2. 讀本檔全文 + `thesis-mc/WRITING-RULES.md` + `thesis-mc/TRANSLATION-GLOSSARY.md`。
3. 跑一次四章 interleave（指令在 §5),確認交接後沒有別的 session 動壞對齊。
4. 不要動任何檔案,等 USER 從 ch1 下指令。

## 0b. Opus 接班附錄（2026-07-21;依 succession-brief-opus v2 + model-behavior-facts 校準本 phase）

- **⛔ succession-brief §2.6「thesis-mc/ 任何人不得直接編」已被取代**——那是 2026-07-10 route-B 時代
  快照（當時 ch5 有曝險數字、走 prereg re-quote 流程）。07-19 USER green-light（`CURRENT-STATE.md`
  07-19 夜 banner ③⑥:thesis/figures/slides sessions 開工）與本 phase 的 USER brief 之後,**編修
  thesis-mc 正文就是本 phase 的任務**。brief 其餘紀律照用:§0 狀態用查的、§4 措辭紅線、§5 對策、§6 陷阱。
- **數字紅線(比 brief §7 更嚴)**:本 phase **不引用任何實驗數字、不改任何 claim**。ch5/ch6 凍結;
  改寫中若一句話需要動到效果宣稱或數字,那句超出範圍——停下問 USER。
- **派工授權(明確授權,矯正 Opus 文件化的少派工傾向)**:每章中文改完,英文重譯**必須派 haiku
  sub-agent**（USER binding 偏好:EN 重譯交低階模型;契約=`en/TRANSLATION-CONTRACT.md`,含
  「不信自報、用真 interleave 驗、驗 mtime」）——不要自己逐段翻。>200 行/>3 檔的機械掃描（重編號、
  詞彙替換、交叉引用檢查）一律派 sub-agent,不要「覺得直接讀比較快」。
- **effort**:本 phase 的改稿與體裁對齊用 xhigh 即可;max 只留給真正的診斷型矛盾調查。
- **state 主張同回合附驗證**;回報前逐項對照本 session 的 tool 結果,沒驗過的明說沒驗。
- **context 充足**:不要因 session 變長自砍範圍、提前收尾或建議開新對話;里程碑關帳時才建議換場。
- **並行 session 禮儀**:figures/slides session 會動 `thesis-mc/figures/`,不衝突不協調;memory
  單一寫入者,本 session 只在里程碑寫自己的 topic 檔。

## 1. 量測基線（2026-07-20 晚,pdftotext + en/*.en.md,方法＝去註解/去數學/去圖行後數英文詞）

**比對尺＝英文詞數**（參考論文本文純英文;我方英文版忠實度已驗:全六章逐區塊
EN詞/ZH字比值 0 離群,結構逐塊對齊——可放心當尺;USER 明示只比長度、不審英文內容）。

### 逐章

| 章 | 參考(頁) | 參考(EN詞) | 我方(EN詞) | 我方(ZH字) | 差 | 動作 |
|---|---|---|---|---|---|---|
| ch1 Introduction | 5 | 1126 | 1371 | 2491 | +22% | 微減 |
| ch2 Background | 5 | 1097 | 963 | 1757 | −12% | 大致持平 |
| ch3 Preliminaries | 13 | 3043 | 5682 | 8728 | **+87%** | 大減 |
| ch4 方法章 | 16 | 3783 | 5392 | 8613 | **+43%** | 大減 |
| ch5 Experimental | 14 | 2566 | 1588 | — | 骨架 | **凍結** |
| ch6 Conclusion | ~1 | 182 | 885 | — | +4.9× | **凍結**（之後另議） |

### ch3/ch4 逐節（重災區的手術目標）

| 我方節 | 我方 EN 詞 | 參考對應節 | 參考 EN 詞 |
|---|---|---|---|
| 3.1 System Model | 2455 | 3.1 System Model | 1367 |
| 3.2 Problem Formulation | 1933 | 3.2 Problem formulation | **725** |
| 3.3 Implemented Realization | 522 | 3.3 Basic idea | 509 |
| 3.4 Context Normalization | 761 | 3.4 Comparison of Catfish-DRL… | 442 |
| 4.1 Method Overview | 1629 | 4.1 data preparation | 729 |
| 4.2 Input Representation | 680 | 4.2 DRL training | **2622** |
| 4.3 Objective-Wise Catfish Training | 995 | 4.3 optimization | 432 |
| 4.4 Reward Shaping | 649 | — | — |
| 4.5 Penalty Shaping | 1052 | — | — |
| 4.6 Overall Training Procedure | 457 | — | — |

節-對-節只是位置對照,**不是**內容對應;參考 ch4 是 3 節、單節深挖（4.2 佔 2622 詞）,
我方是 6 節攤平——章內結構要不要跟著收斂,由 USER 逐章裁決,不要自作主張重構。

## 2. 參考論文體裁（機械抽取,照抄這套文法）

- **式數紀律**:ch3 **11 條**（我方 44 條,4×）、ch4 **13 條**（我方 19 條）。
  **零字母後綴式號**——我方有 8 條（3.4a、3.7a、3.12a–e、3.30a）須併番或整併。
- **公式引入句**:「… can be expressed as:」「can be defined as:」「as follows,」;
  接續句:「where NRF ≤ Nt …」「Here, sk denotes …」。一式一段,長段落約 33 個/章（ch3）。
- **圖表標題**:`Figure 3.1: caption`（章**點**序＋冒號;我方現為 `Figure 4-2:` 章**折線**序——是否改由 USER 裁）。
- **段首標籤**:`Label: 內文…`（冒號、無粗體）——我方 2026-07-20 已全面改成此體例,維持。
- **內文零粗體**（僅封面/標題/表頭）;參考文獻標題＝純英文 `References`——已照辦,維持。
- 密度:參考 ch1≈225 EN 詞/頁。

## 3. 已知的公式正規化欠帳（「公式寫法」子任務,動 ch3/ch4 時一併處理）

1. **兩套編號機制並存**:ch3 與 ch4 前 6 式用 Word 轉檔遺留的 `\begin{matrix} … \text{(3.x)}`,
   ch4 其餘用 `\tag{4.x}`——參考論文是單一右緣編號體例,應統一（統一到哪一種由 USER 定;
   ⚠ `tools/ris_preprocess.py` 的 B1 只處理 `\tag`,改機制前先看該檔）。
2. 字母後綴式號清除（§2）。
3. 式數縮減:合併瑣碎中間式（參考論文一頁至多 1–2 式）。
4. 重編號時記得:**中英兩檔逐位元同步**（interleave 逐位元比對數學）+ 正文交叉引用全掃
   （本 session 曾因重編號雙重位移出過「4.4/4.4」錯,修法＝機械掃描不靠人記）。

## 4. 護欄（全部沿用,本 phase 不改任何 claim）

- 權威:`WRITING-RULES.md`（含 3 RED LINES）+ `TRANSLATION-GLOSSARY.md`＋
  `CURRENT-STATE.md` 頂部 banner（MCRL 改名除外清單、消融敘事、⛔ 三不可寫）。
- 速記:MCCRL/容量感知/介入退火/消融/Double-DQN＝已刪詞,不得回流;lr 修正不是貢獻;
  懲罰塑形不寫成競爭者施壓;分類不歸給 CDRL;無「修好崩潰」句;ch5 的〔暫定〕標記＝
  誠實護欄**保留**;HTML 註解＝還原記帳**保留**（不印出）。
- G1/EUV 凍結面照舊;`thesis/`＝死 route-C 不碰;figures pipeline 不在本 phase。
- 中文改完該章 → 依 `en/TRANSLATION-CONTRACT.md` 派 haiku 重譯該章英文 → interleave 驗 →
  兩份 docx 重建 → 對 §1 基線回報新長度。**英文永遠是中文的影子,不獨立編輯。**

## 5. 建置與驗證指令

```bash
cd thesis-mc
bash tools/build_ris.sh              # 中文版 docx（scratch/conversion-test/mc-thesis-ris.docx）
bash tools/build_bilingual.sh        # 中英對照版（…/mc-thesis-ris-bilingual.docx）
# interleave 驗證（四章）:
env MPLCONFIGDIR=/tmp/modqn-mplconfig python3 - <<'EOF'
import sys, pathlib; sys.path.insert(0, "tools"); import build_bilingual as bb
for z, e in [("mc-modqn-base.md","en/mc-modqn-base.en.md"),("ch4-method.md","en/ch4-method.en.md"),
             ("ch5-experimental-result.md","en/ch5-experimental-result.en.md"),
             ("ch6-conclusion.md","en/ch6-conclusion.en.md")]:
    bb.interleave(pathlib.Path(z).read_text(), pathlib.Path(e).read_text(), label=z)
print("四章 interleave 全過")
EOF
```

docx 驗收慣例（本 session 建立,沿用）:引用 [1]–[23] 連續零孤兒、禁用詞掃描全 0、
圖 15 張不重複、表 2 個 EN-only、清單項全 Compact、`(i)`–`(vi)` 不被 pandoc 誤判為清單
（英文段首括號列舉必須寫成 `\(i\)`）。

## 6. 交接時點的既知狀態（2026-07-20 20:5x）

- 四章中/英全對齊、兩份 docx 與來源同步（含新版圖 4-2）、
  參考文獻第二次重編完成（[14] Kirkpatrick 移出,紀錄在 `REFERENCES.md`「已移出」節含復原條件）。
- 並行 session 注意:slides/figures session 會更新 `thesis-mc/figures/*.png`;
  重建 docx 前不需理會,建置自動嵌最新檔。伺服器 ep2k 訓練與本 phase 無關。
- 摘要已改 4 段中英交錯、943→715 字;正文粗體已全清、段首標籤冒號體例。
