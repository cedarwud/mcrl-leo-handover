# 交接：敘事轉向（解崩敘事作廢）— 2026-07-20

> **給下一個論文撰寫 session。** 本檔是換對話的原因與待辦，不是決策文件。
> **權威**：`analysis/family-b-collapse-diagnosis/COLLAPSE-ROOT-CAUSE-IS-LR-2026-07-20.md`（commit `0082683d`）
> ＋ `CURRENT-STATE.md`。本檔只是把它翻譯成「論文要改哪幾行」。衝突時以權威為準。

---

## 0. 先讀這段，不然會寫錯

專案長期把 family_b 的 MODQN「崩潰」當成 MODQN／shared-Q／per-user-argmax 的性質。
**它是 `lr = 0.01` 的產物。** 只翻學習率一個變數（0.01 → 0.001，兩份 `run_metadata` 的
leaf-diff 只差這一個欄位），argmax EE 235.53 → 472.22、最差使用者覆蓋 0.312 → 0.698。

**⛔ 兩條硬規則（USER-directed，寫進論文前先確認自己沒違反）：**

1. **`lr` 不是貢獻，永遠不准寫成貢獻。** 「我們調學習率把崩潰修好了」是修自己的基準，不是研究成果。
   論文裡不出現這件事——`lr = 1e-3` 就只是 §5.1 的一個訓練參數。
2. **任何「本框架修好／解開了 MODQN 的崩潰」的句子都已死。** 正確調校的基準沒有這個病。

---

## 1. 新敘事（USER 2026-07-20 口述 ＋ 權威記錄）

- **回歸正常**：不再強調解崩。主線＝**能量效率**。
- **容量懲罰＝相對 CDRL 最大的不同**，是本論文新增的策略。這是**設計／新穎性**宣稱，
  不依賴任何實驗數字 ⟹ **現在就可以寫**。
- 基準的真正弱點改述為：**基準從訓練到部署都看不到每顆衛星的波束數上限**，容量只在環境端被強制執行；
  把上限寫進訓練損失，讓學到的價值承擔它，才是本論文的作法。這個說法不依賴崩不崩，比舊敘事更站得住。

### 已 grounded 的數字（6 formal seeds，同一支凍結 argmax scorer，Mbits/J）

| 量 | 值 | 意義 |
|---|---|---|
| `L2 − L1` | **+56.54**（6/6） | 情境正規化相對原始基準的增量 |
| `L6 − L2` | **+124.31**（6/6） | **完整 MCCRL 相對「已正規化的 MODQN」** ← headline |
| `min_cov` | 0.586 → 0.732 → 0.957（L1→L2→L6） | 最差使用者覆蓋 |

Framing（權威指定）：**z-score ＝ substrate（baseline 取 L2）；headline ＝ `L6 − L2`。**
框架的宣稱因此**變強不變弱**——它現在贏的是一個**正確調校**的基準，是更難、更站得住的門檻。

---

## 2. ⚠ 一個必須守住的界線（RED LINE (b)）

USER 說「強調 catfish 提升 EE」。但目前 grounded 的是 **`L6 − L2` ＝ 整個框架**的增益，
**不是 catfish 單獨的貢獻**。把 +124.31 說成 catfish 的功勞，就是 RED LINE (b)
「不得假稱 catfish 驅動勝利」。

- **可以現在寫**：容量懲罰是相對 CDRL 的新增策略（設計事實）；框架整體相對 L2 的增益（已測）。
- **必須等 `abl9k2` 十臂消融**：各機制的**相對貢獻排序**、「哪一個機制在推 EE」。
- 記憶裡的舊帳：catfish-effectiveness 過去**全 NEGATIVE**。這次可能翻案，但**要等數據**，
  不要靠敘事需要就先寫上去。

---

## 3. 要改的位置（已量測：全前四章只有 7 處，其餘不受影響）

「過度集中」在 ch1–4 只出現 **7 次**，而「能量效率」有 **68 次** ⟹ EE 敘事本來就是主體，
**Ch.3／Ch.4 的機制描述幾乎全部存活**。要動的就是這 7 處：

| # | 位置 | 現況 | 要怎麼改 |
|---|---|---|---|
| 1 | `mc-modqn-base.md:38` 中文摘要 | 「兩點不足」其二＝各自取 argmax → 過度集中、超出容量者難取得吞吐量 | 其二改為「基準從訓練到部署都看不到波束數上限」；不用崩潰／過度集中語言 |
| 2 | `:58` §1 動機段末 | 同上 | 同上 |
| 3 | `:64` 貢獻項二 | 「…容易造成過度集中。為此保留…」 | 動機改為容量上限對基準不可見；框架描述本身不用改 |
| 4 | `:68` 貢獻項三 | 「檢視容量上限與過度集中之間的關係」 | 改為容量掃描的中性描述 |
| 5 | `:445` §3.2（六） | **小節標題**「評估指標與過度集中問題」 | retitle（例：「評估指標與容量受限下的行為」） |
| 6 | `ch4-method.md:123` §4.3 策略一 | 以「過度集中的時間步很稀少」動機化能效分層 | 換動機：分層依 **EE 分位**分流，用 EE 分布講，不用過度集中講 |
| 7 | `ch4-method.md:264` §4.6 | 「單靠這一項並不能排除過度集中」 | **這句是防誤讀的保護句，語氣可留**；只需確認上下文不預設基準會崩 |

**其餘不用動**：Ch.3 全部公式與模型、Ch.4 §4.1–4.2、§4.4–4.5、§4.7–4.8、所有圖與圖說。

---

## 4. 前四章目前狀態（承接自本 session，不要重做）

- **Ch.3 / Ch.4**：完成。式號 3.1–3.36、4.1–4.21，零 dangling；圖 12 張（ch1=0／ch2=0／ch3=3／ch4=9）。
- **摘要（中）／§1／§2.2**：2026-07-20 已把**方法描述**改寫為現行框架，結果宣稱改成可見佔位
  `**〔待補：…〕**`（三處：摘要、貢獻項三、§2.2 末）。**本次敘事轉向要再動的就是上表那幾行。**
- **圖 1-1 已自論文移除**（USER 決定；畫的是已移除的協調式波束分配）⟹ **第一章現在沒有圖**，刻意。
- **未結案**：§4.4 `［草稿／provisional］`（等快測閘）；Ch.5 全部數字；EN 各版（整體待自定稿 ZH 重譯，
  brief 明訂不翻譯，中英現在已知不一致）。
- **Ch.6 整章仍是協調式波束分配敘事**，未動，在第五章之後的清單上。

---

## 5. 工具（會省下重踩的時間）

```bash
cd thesis-mc
python3 figures/check_figure_sync.py          # 圖↔正文漂移；有漂移 exit 1
python3 figures/check_figure_sync.py --update  # 確認正文已同步後才重設基準
python3 figures/render_png.py <svg> [out.png]  # 唯一正確的 SVG→PNG 渲染法
```

- **`check_figure_sync.py`**：記每張已嵌入圖的內容雜湊（不是 mtime——`git checkout` 不保留 mtime）。
  同時追 builder 與 editable SVG：**曾發生 builder 修好、deliverable 重繪、但論文嵌入的 PNG 沒重繪**，
  只比對 PNG 抓不到。⚠ `--update` 會把「圖說是否還相符」一起蓋掉，**先確認再重設**。
- **`render_png.py`**：直接 `chrome --headless --screenshot` 開 SVG 會壞兩種，**而且兩種的 PNG 尺寸
  都正確、byte 數也合理**（只驗尺寸會全放行）：(a) 內容只填約 46%、其餘空白；(b) 裁掉底部約 64 CSS px。
  正解＝HTML wrapper(margin:0) ＋ width/height 換 viewBox 像素 ＋ 視窗開高 200px 再裁回。
  等價性已驗（重繪 git 中已知正確的 PNG，sha256 位元相同）。

## 6. ⚠ 並行 session 危害（今天發生兩次）

另有 session 同時在 `thesis-mc/` 工作（圖檔線）。**git index 是共用的**：

1. 我整檔讀-改-寫 `ch4-method.md` 時，他們正在改同一個檔的圖說——**沒被蓋掉是時序運氣**，
   我的 assertion 只保護我要替換的字串。
2. 我 `git add` 之後、commit 之前，他們先 commit，**我整批摘要／§1／§2.2 的改寫被掃進他們的
   `db47c745`**。內容完整，但訊息沒描述它 ⟹ 已用空 commit `2ca5aee3` 補記歸屬。

**下一個 session 的作法**：暫存後立刻提交，或用 `git commit -- <paths>` 只提交指定路徑；
動 `*.md` 前先 `git log --oneline -3` 看有沒有新 commit。**分工尚未釘死＝USER 未裁。**

## 7. 驗證配方（改完跑一次）

```bash
cd thesis-mc && python3 - <<'PY'
import re
files={f:open(f,encoding='utf-8').read() for f in ['mc-modqn-base.md','ch4-method.md']}
nc={f:'\n'.join(l for l in t.splitlines() if not l.strip().startswith('<!--')) for f,t in files.items()}
print("協調式:", sum(nc[f].count('協調式') for f in nc))          # 應 0（英摘用 coordinated 不計）
print("解崩語言:", [w for w in ['崩潰','de-collapse','解崩','collapse'] if any(w in nc[f] for f in nc)])
print("結果宣稱:", [w for w in ['優於基準','大幅改善','實驗顯示','顯示此框架'] if any(w in nc[f] for f in nc)])
print("lr 出現在正文（必須 0）:", [w for w in ['學習率','learning rate','lr='] if any(w in nc[f] for f in nc)])
PY
```

外加：孤兒圖／圖序／斷鏈式號檢查（本 session 用過的腳本邏輯，見 `WRITING-RULES.md`
2026-07-20 各條）。

---

## 8. 為什麼建議換對話（不是因為 context 滿）

換對話時 context 才用 30%（304k/1m），**空間不是問題**。理由是 `AGENTS.md` G0 的**錨定**：
本對話有 ~243k tokens 的訊息全建立在舊敘事上，而我剛在舊框架下改寫完摘要與第一章。
留在原對話改新敘事，會傾向把舊句子「修一修」而不是重寫——G0 明文說 frame 變了就重置對話。
