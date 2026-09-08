1. **Domain truth：負載均衡改善 EE 是條件命題。**
   文獻支持在需求、功率上限與干擾約束下聯合配置資源；不支持「用戶數越平均，bits/J 必然越高」。例如 [Efrem與Panagopoulos（2019）§II](https://arxiv.org/html/1912.00920v1)權衡未滿足需求與 RF 功率，並未證明均衡負載可降低非線性 PA 能耗。
   舊模型是 full-buffer、無限 Shannon rate、等時分享、beam RF＝用戶功率的 max，且沒有最低速率要求；因此缺少「負載增加→維持速率所需功率增加」這條機制。但 beam activation、power leadership 與干擾仍提供改善機會，不能說完全沒有能量槓桿。[16-A](sandbox:/workspace/scratch/520bc6398efc/review_input/16-ASTRA-FRESH-C3-CORE-ADJUDICATION.md)
   舊系統也不是單純 noise-limited：18 的配對檢查量得約 7.7–11.2 dB 干擾損失；沒有 rate-target congestion，不代表沒有 interference coupling。[18〈Focused physics checks〉](sandbox:/workspace/scratch/520bc6398efc/review_input/18-DIFFERENTIAL-PHYSICS-AUDIT.md)
   最新主模型以 **20 的 sealed amendment** 為準：50 Mbit/s 名目速率目標、memoryless TDM power control、ACM inversion；補上 occupancy→required-power，移除 entry-anchor。[20 §1–4](sandbox:/workspace/scratch/520bc6398efc/review_input/20-SEALED-PRIORITY-AMENDMENT-v1.1.md)
   但實際關係是 **ACM 階梯加 cap**，不是光滑指數；TDM 的 \(W/n\) 是等效 airtime bandwidth，接收雜訊仍用全頻寬 \(N_0W\)。再加上凹的 PA 曲線與開束成本，均衡和合併仍須逐配置比較。[19 A–D](sandbox:/workspace/scratch/520bc6398efc/review_input/19-ASTRA-ROUND4-RATE-TARGET.md)

2. **Root-cause ranking：納入 16–18 後，排序如下。**
   **① Counterfactual／執行介面錯配。** MONE 單邊預測全正、聯合執行卻反轉 28/60 次；分配 coalition credit 不保證完整採納。但 R7 teacher composition 曾 +0.335%，所以不是所有 additive policy 都不可能成功。[01 §1](sandbox:/workspace/scratch/520bc6398efc/review_input/01-CHRONOLOGY.md)
   **② 物理 regime 與研究假說錯配。** 缺少 occupancy→rate-target power 機制，並存在 anchor／wanted-versus-radiated power 的模型問題。[11 H01–H03](sandbox:/workspace/scratch/520bc6398efc/review_input/11-ASTRA-PHYSICS-ROUND3.md)
   **③ 執行目標／probe plumbing 錯配，上調優先級。** 03 的 C3 不是 LC-SRS；λ 分支缺陷已確認，不能再把那些數字當成宣告機制的完整 oracle 判決。[18〈Executed versus declared C3 oracle〉](sandbox:/workspace/scratch/520bc6398efc/review_input/18-DIFFERENTIAL-PHYSICS-AUDIT.md)
   **④ 可部署資訊缺口。** ZR 依賴他人同時動作與 realised fading，是部分家族的獨立瓶頸。[01 §1，列7–15](sandbox:/workspace/scratch/520bc6398efc/review_input/01-CHRONOLOGY.md)
   **⑤ Balancing／consolidation 誤框架。** 是②的設計後果；「永遠合併」同樣錯誤，不能照抄17的必要充分論斷。[16 A–B](sandbox:/workspace/scratch/520bc6398efc/review_input/16-ASTRA-FRESH-C3-CORE-ADJUDICATION.md)
   **⑥ Training-stack 語義問題。** Bootstrap、時間聚合主要涉及 legacy MODQN；目前監督式 Q1/Q2 不經該 TD 路徑，仍須核對尺度、參照與時間範圍。[12 E4/E5/E7](sandbox:/workspace/scratch/520bc6398efc/review_input/12-REGISTER-E-REWARD-TRAINING.md)
   **⑦ 候選集合／短視野限制；⑧ 評估推論不足。** 會限制可見機會與可推廣程度；pooled ratio 本身正確，零門檻反而可接受極小正值，並非天然「不敏感」。[14 F1–F7](sandbox:/workspace/scratch/520bc6398efc/review_input/14-REGISTER-F-EVALUATION.md)
   **⑨ BASE 吸收全部收益。** 證據弱：E1 U₁ +1.992%、J₁ +2.222% 已反駁「完全耗盡」。[05](sandbox:/workspace/scratch/520bc6398efc/review_input/05-E1-RESULT.md)
   **⑩ 大型純物理算術 bug，下調至末位。** 18 明顯降低其可信度；不能以它解释整段歷史。
   **充分解釋必須處理①–③及 ZR 的④；目前沒有任何組合被證明在因果上必要且充分。** Anchor 對 +2.9% 的實際貢獻仍未識別，不能將整個收益或整段失敗都歸給它。[16-E](sandbox:/workspace/scratch/520bc6398efc/review_input/16-ASTRA-FRESH-C3-CORE-ADJUDICATION.md)

3. **Concept-right-code-wrong：下一個差分重點應是 target→decision→endpoint。**
   先修正題目前提：18 並非全部誤差小於 \(10^{-6}\)；Bessel 缺陷使最大 bits 相對誤差達 \(2.93\times10^{-6}\)。其270步支持舊宣告模型的局部算術一致性，沒有驗證 successor；完整重跑材料亦未附於本包。[18〈Verdict／Limitations〉](sandbox:/workspace/scratch/520bc6398efc/review_input/18-DIFFERENTIAL-PHYSICS-AUDIT.md)
   **最具診斷力：`DeclaredTarget×Decoder_EndToEnd_Parity`。** 同一組00/10/01/11原始狀態，交叉比較「production／獨立宣告公式」與「additive／atomic decoder」，一路核對實際動作及終端 bits、joules、service。
   必含不變 bits、能量(10,10,10,8)、λ＝1的 fixture：單邊 C3＝0，但 \(\Psi=2\)、LC-SRS shares＝(1,1)；再對 authenticated 真實 witnesses 重做。[16 C5](sandbox:/workspace/scratch/520bc6398efc/review_input/16-ASTRA-FRESH-C3-CORE-ADJUDICATION.md)
   Production／reference 不同定位 plumbing；兩者一致但 additive／atomic 不同定位 composition；atomic 也無收益，只能限制該模型、狀態與候選集合。
   另需非約束 demand-cap 不變性、所有 producer 顯式 λ/κ、每個 demand regime 重新最佳化 J；**不可直接改用 `t3_energy`，因 C1 已含單邊全網能量，會重複計價。**[15，`target_triplet`／`_unit_worker`](sandbox:/workspace/scratch/520bc6398efc/review_input/15-ORACLE-MARGINALS-CODE/oracle_marginals.py)
   補做真實 coordinator 路徑 NULL≡BASE、ACM邊界／cap／solver residual，以及共同動作 bootstrap fixture。18 的 bootstrap PASS 只排除 head-index 誤用，沒有排除各頭選不同最大動作；instantaneous additivity PASS 也未消除跨時間聚合差異。[12 E4/E5](sandbox:/workspace/scratch/520bc6398efc/review_input/12-REGISTER-E-REWARD-TRAINING.md)、[18](sandbox:/workspace/scratch/520bc6398efc/review_input/18-DIFFERENTIAL-PHYSICS-AUDIT.md)

4. **Best C3 prior：以 QoS 約束的 joint association／activation coordinator。**
   配置須包含 transfers、swaps、evacuations；把 interference 放入聯合功率求解，把 QoS 當約束，而非把 occupancy variance 當獎勵。這比預設「均衡」或「關束」方向更合理；聯合功率／beam scheduling 亦有節能先例，但不是本系統成功保證。[20 §4](sandbox:/workspace/scratch/520bc6398efc/review_input/20-SEALED-PRIORITY-AMENDMENT-v1.1.md)、[Chen等，2024](https://scholar.xjtu.edu.cn/en/publications/joint-power-allocation-and-beam-scheduling-in-beam-hopping-satell/)
   選擇目標用完整配置的 \(\widehat F=\widehat B-\eta_{\rm ref}\widehat E\)，保留 BASE、平手選 BASE、atomic execution；E 必須是 slot-integrated **DC＋circuit＋已宣告 standby**，不是未加權的 \(\sum_u p_u^{RF}\)。[11 §2、19 A–B](sandbox:/workspace/scratch/520bc6398efc/review_input/19-ASTRA-ROUND4-RATE-TARGET.md)
   最新模型計算 full-buffer achieved ACM bits，因此不能假定所有配置 bits 恆定而只最小化功率；只有等交付量比較才可如此簡化。[20 §2](sandbox:/workspace/scratch/520bc6398efc/review_input/20-SEALED-PRIORITY-AMENDMENT-v1.1.md)
   固定 \(\eta_{\rm ref}\) 是 surrogate：只有等於相關 comparator 的 pooled EE，\(\Delta B-\eta_{\rm ref}\Delta E>0\) 才與提升該 ratio 等價；最終仍須直接評估 pooled EE及rate attainment。[16-A/C](sandbox:/workspace/scratch/520bc6398efc/review_input/16-ASTRA-FRESH-C3-CORE-ADJUDICATION.md)
   比較器至少包含重新訓練的 successor Q1+Q2、同資訊／同候選／同算力的 S0、greedy-seeded nominal optimizer，以及完整單人搜尋；用真正多人 witness 證明超出 unilateral correction。[11 §4](sandbox:/workspace/scratch/520bc6398efc/review_input/11-ASTRA-PHYSICS-ROUND3.md)
   **C1 已升級 whole-network surplus，C3 必須處理剩餘聯合交互。** Learned C3 可提供可預測的模型誤差修正、未來負載價值，或期限內更好的搜尋；單純模仿 S0只證明加速，不證明額外 EE，也不能預測獨立不可觀測 fading。[20 §4](sandbox:/workspace/scratch/520bc6398efc/review_input/20-SEALED-PRIORITY-AMENDMENT-v1.1.md)、[16-D](sandbox:/workspace/scratch/520bc6398efc/review_input/16-ASTRA-FRESH-C3-CORE-ADJUDICATION.md)

5. **Still unexamined：以下三項未見完成驗證，不能斷言從未有人想到。**
   **① Successor 的實際可用能量區間。** 真實 occupancy／channel 組合究竟跨越可節能 ACM 階梯、停在 plateau，還是普遍撞 cap？須連同跨束 TDM 同時排程、coupled solver residual及時槽 DC 能耗驗證；宣告 rate target 不等於創造可用 C3 marginal。[19 A/D；20 §1–2](sandbox:/workspace/scratch/520bc6398efc/review_input/20-SEALED-PRIORITY-AMENDMENT-v1.1.md)
   **② 有利配置是否在進入 oracle 前就被排除。** Coarse satellite shortlist 的 superset 保證尚未建立；within-mask 完整枚舉無法發現漏掉的合法衛星，多步／多束重排也可能不在 evacuation catalog。這可把「候選漏失」誤判成「物理無空間」。[11 H40；16 B8](sandbox:/workspace/scratch/520bc6398efc/review_input/11-ASTRA-PHYSICS-ROUND3.md)
   **③ 新 C1/C2 之後，是否仍有可學的獨立聯合收益。** 全網 C1可能吸收舊 C3作用；剩餘收益可能需要不可部署資訊，也可能被更完整的 nominal decoder取得。包內沒有 successor retraining＋matched S0＋FULL/DROP結果能回答；這會直接改變第三個 learned component 的必要性。[20 §4–6](sandbox:/workspace/scratch/520bc6398efc/review_input/20-SEALED-PRIORITY-AMENDMENT-v1.1.md)

6. **Process：把順序固定為「語義→已知答案→完整路徑→獨立驗證→研究裁決」。**
   **① Assumption register 先行：** 每條假設連到物理機制、實際 consumer、適用模型版本與可推翻它的證據；已知未決事項必須帶入每次新設計，不能只留在歷史 memo。[09 B4；11 §1](sandbox:/workspace/scratch/520bc6398efc/review_input/09-OPUS-ANCHORED-POWER-AUDIT.md)
   **② Known-answer suites：** 優先守住 radiation／airtime／energy 一致性、宣告 target parity、λ傳遞、共同動作 bootstrap與不等能量 pooling；測試須能抓到刻意注入的錯誤。[11 §3](sandbox:/workspace/scratch/520bc6398efc/review_input/11-ASTRA-PHYSICS-ROUND3.md)
   **③ 每臂真實一步＋placebo：** 強制 NULL≡BASE；random-feasible／renewal 用於歸因，不能預設它必須輸 BASE。此步也能提早抓到21所記的 deepcopy失敗。[08 §6–7](sandbox:/workspace/scratch/520bc6398efc/review_input/08-OPUS-HARNESS-AUDIT.md)、[21 #12](sandbox:/workspace/scratch/520bc6398efc/review_input/21-POST-ROUND3-ADDENDA.md)
   **④ Independent recomputation：** 保存 as-run code、原始幾何／fading／schedule及逐項收支；從 primitive inputs 重算，再驗證 receipt，避免兩個 verifier只共享同一錯誤。[18〈Limitations〉](sandbox:/workspace/scratch/520bc6398efc/review_input/18-DIFFERENTIAL-PHYSICS-AUDIT.md)
   **⑤ Reviewer rotation：** 在更換 target family或再次保留同一失敗介面前，讓新 reviewer 檢查「到底換了哪個假說」；先獨立閱讀證據，再讀既有裁決。INVALID不能算負結果，模型優先序不能隨勝負改動。[01 §3–4](sandbox:/workspace/scratch/520bc6398efc/review_input/01-CHRONOLOGY.md)、[20 §5](sandbox:/workspace/scratch/520bc6398efc/review_input/20-SEALED-PRIORITY-AMENDMENT-v1.1.md)

LOAD_BALANCE_EE=REGIME_CONDITIONAL | CORE=model_regime_mismatch,target_decoder_mismatch,target_pipeline_defects,deployable_information_gap | MOST_DIAGNOSTIC_TEST=DeclaredTarget_x_Decoder_EndToEnd_Parity | BEST_C3_PRIOR=QoS_Constrained_Joint_Association_Activation_Coordinator
