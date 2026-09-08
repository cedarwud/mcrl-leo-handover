已依序讀完審查包。以下【檔號／節】對應 ZIP 內檔案；包內引用的原始程式與 receipts 未另附，因此數值重現仍屬各審查紀錄的證據。

1. **主模型：我選 b；a-r 是有條件成立的可調功率酬載模型。**
   固定波束 RF、由幾何與通道變化驅動 ACM，是有明確依據的前向鏈路參考；但不是所有 LEO 系統的強制架構。[ETSI TR 102 376-1 §§4.4.0–4.4.1](https://www.etsi.org/deliver/etsi_tr/102300_102399/10237601/01.02.01_60/tr_10237601v010201p.pdf)
   b 的角度影響 SINR、bits、EE，**不直接改變同一啟用波束的 RF watts**；若後者不可放寬，應明確採用可調功率架構，不能靠設計意圖證明其普遍性。【05 §5；05c「Owner’s requirements」】
   a 必須交代可獨立控制的使用者載波／時槽、酬載致動能力、CSI 與回授延遲、更新速度及功放限制；ESA 的可調波束功率技術不能直接證明逐使用者瞬時控制。[ESA 技術說明](https://www.esa.int/Enabling_Support/Space_Engineering_Technology/Multi-Beam_Satellite_Communications_Payload_with_Flexible_Power_Allocation)
   a-γ 可選明示 MODCOD 目標，例如本包 8PSK 2/3 對應 7.528 dB；a-r 應反查實際 ACM 表，50 Mbit/s 只能稱合成目標，不能稱實測需求。【04 C.4；05b B–C】
   必須區分使用者／波束／衛星 cap、硬體飽和與操作 back-off；達不到目標時降 MODCOD、計入實際部分傳輸及耗能，另報目標未達，禁止換手重設優惠。【05d §1–2】

2. **聚合：兩者都可一致，但「equal bandwidth sharing」必須說清楚。**
   TDM：使用者以 \(f_u=1/n_b\) 輪流占完整 \(W\)，槽內噪聲為 \(N_0W\)；平均 RF 為 \(\sum f_up_u\)，PA 平均供電為 **\(\sum f_uP_{\rm DC}(p_u)\)**，不能先平均 RF 再套非線性效率。【04 C.2–5、D.1】
   FDM：同時各占 \(W/n_b\)，噪聲為 \(N_0W/n_b\)，波束 RF 為 \(\sum p_u\)，干擾依頻譜重疊計算；共用 PA 須使用多載波 back-off／失真模型。[Ramírez 等，§II](https://arxiv.org/html/2109.09385v3)
   因此 \(W/n_b\) 的速率係數本身不能判定 TDM/FDM；本包原先的全頻寬噪聲較符合 TDM 解讀。【03 B14】
   我要求**同一份時間—頻率發射配置**生成 wanted signal、interference、PA supply；取消 private wanted／beam-max 混搭。
   耦合功率須共同求解；收斂不等於目標可達，解碼失敗的已發射訊號仍計干擾與能量。【05 §2.11；05d §2】

3. **SERVICE=replace：保留 PHY 可解碼判定，替換 bits 公式及「服務」名稱。**
   對已配置傳輸，可用 `served_PHY ⇔ SINR ≥ SINR_min`；它不是最低速率或 QoS 保證，另報 rate-target attainment、使用者速率尾端與中斷時間。【05 §2.10–11】
   使用 \(B_u=\int_{\text{獲配且可用時間}}W\,SE_{m(\gamma_u(t))}\,dt\)（TDM）；低於最低模式為零，不以截頂 Shannon 冒充 ACM。
   可採 **DVB-S2 EN 302 307-1 V1.4.1，Table 13 全部 28 模式**、normal frame、無 pilots、roll-off 0.20；這是明示的 modem profile，不能稱 DVB-S2X 的普遍上限。[標準 §6、Table 13、Annex A](https://www.etsi.org/deliver/etsi_en/302300_302399/30230701/01.04.01_60/en_30230701v010401p.pdf)
   表中 QPSK 1/4 為 \((-2.35\text{ dB},0.490243\text{ bit/symbol})\)，32APSK 9/10 為 \((16.05,4.453027)\)。
   若 \(W\) 是占用頻寬，則 \(SE_{\max}=4.453027/1.2=3.710856\) bit/s/Hz；以 \(M=1.7\) dB 得 \(\gamma_{\min}=-2.35+1.7-10\log_{10}1.2=-1.4418\) dB。【05 §2.8–10】
   1.7 dB 可保留為共同接收器損失假設；其來源是特定 32APSK 測試，並非完整 LEO 非線性／追蹤損失預算。須另聲明等效高斯干擾、同步與額外開銷。[ITU-R BO.1784-1，Annex 1 附件 §1](https://www.itu.int/dms_pubrec/itu-r/rec/bo/R-REC-BO.1784-1-201612-I!!PDF-E.pdf)

4. **能量邊界可保留；必須修正硬體對應及開關語義。**
   PA supply＋啟用波束 circuit＋啟用衛星 baseband 可作「部分酬載 EE」，bus、地面站與終端可排除；不得稱整顆衛星／端到端 EE。【05 §2.12–16】
   0.338 W 與 0.200 W 不能直接驗證 Ka-band 飛行硬體；原來源另計 LO、phase shifters，且 RF-chain 數目取決於架構。我要求列出硬體清單、共用關係與可關閉部分。[You 等，§II-C、Tables I–II](https://arxiv.org/pdf/2201.06281)
   standby=0 可作理想完全關機情境，但須搭配非零敏感度及切換時間假設；本包 \(35/420=1/12\) 是**地面整機 mute/active 比值**，不是已驗證的星載 PA 待機比例。[CPI MKT-497，p.2](https://www.cpii.com/docs/datasheets/826/MKT-497%20SA49KOA_SB49KOA%2080%20W%20SSPA_SSPB.pdf)
   換手 event joules 可明示排除，不能宣稱物理上為零或已證實可忽略；中斷應扣 useful time，已維持的 RF／電路耗能仍保留。
   我不接受把每次 beam change 自動套成同一 RRC handover：62/142 ms 必須有程序映射，否則僅作條件式敏感度。【04 B.4、D.4；05 §2.15–16】

5. **獎勵方向合理，但不是能保證三個元件有效的「標準配方」。**
   接受 \(R=B-\eta_{\rm ref}E\)，且 B、E、時間範圍與 endpoint 一致；折扣回報不能無說明地取代未折扣 pooled EE。【05 §2.21–25】
   若 \(\eta_{\rm ref}=B_{\rm ref}/E_{\rm ref}\)，則 \(B-\eta_{\rm ref}E=E(\eta-\eta_{\rm ref})\)：對**同一參考**的改善符號精確，但任意候選排序與全域最適化不等價。[Dinkelbach](https://pubsonline.informs.org/doi/10.1287/mnsc.13.7.492)
   Difference reward 應重算全網 bits／energy，反事實基準不依賴該使用者所選動作；它改善單方信用指派，不能保證多使用者同步 argmax 正確。[Wolpert、Tumer、Frank §2](https://proceedings.neurips.cc/paper/1998/file/5129a5ddcd0dcd755232baa04c231698-Paper.pdf)
   Φ 可作 QoS 約束／偏好，搭配換手率共同主要報告；既已扣中斷 bits，額外 Φ 須說明仍代表何種成本，避免重複懲罰。
   C2 重建幾何、MODCOD／rate、負載、cap 與可見時間預測；使用部署可得資訊，重新生成兩個 head 的相關特徵、targets、λ／κ，明定當期與未來項不重複計價。【12-E 詳細 §12；05 §2.24–30】
   C3-S 應稱 model-based coordinator；須有 greedy＋相同 coordinator、單方搜尋及模型誤差控制，才能分辨學習、聯合協調與精確模型資訊的貢獻。【06 H2；05 H19】

6. **最低設計須先把聲明限定為「另外兩者存在時，各元件均有正貢獻」。**
   同一 successor、horizon、未開啟面板測 \(111,011,101,110\)；加 retrained \(000\) 與外部 baseline。C1/C2 用等預算 neutral-source 替換，C3-off 執行原 proposal。【19 §4.1–2】
   此設計識別條件式 FULL−DROP 與 joint−null；若要平均主效應或交互作用，需完整 \(2^3=8\) 格，不能只補 000 就宣稱完成 factorial。
   **以至少 5 組獨立完整訓練種子起步**，組內配對；最終數量由預設精度／效應決定，5 seeds、600 worlds 都不是充分保證。[Agarwal 等](https://arxiv.org/abs/2108.13264)
   日期／相鄰時間區塊與 training seed 的交叉變異一起處理；paired bootstrap 每次重算 \(\sum B/\sum E\)，不能用平均 log-EE 的 CI 代替 pooled EE 的 CI。【19 §4.4–5】
   各相對 EE 對比預設 \(\delta_i\)；沿用 0.5% 時須明稱最低實用效應的研究設定，要求同時 95% 下界超過它，並通過 **FULL 對各 DROP** 的 QoS 非劣性。
   排除已開啟前 100 worlds，固定終點與選模規則；3000 通過後延伸至 9000 不是獨立複現。日期也不是由重複抽樣自動證明的獨立單位。【12-F F3–F5；19 F9、§6】

7. **MATRIX=sound，作為有界 regime map；不能替代確認性驗證。**
   合理設定全部揭露、主模型依物理適用性事先固定，符合 multiverse 分析的透明度精神；沒有任何規則能把「要求三者必須正」變成科學事實。[Steegen 等](https://sites.stat.columbia.edu/gelman/research/published/multiverse_published.pdf)
   必要聲明：「**本矩陣是在已知舊模型結果後、取得 successor 結果前指定；主模型、參數與排除規則已固定，所有完成、失敗及未完成格均揭露，次要情境的正結果不替代主模型，確認使用另行未開啟的時間區塊。**」【05c「Rules」；05d §3–5】
   現有 20 格只新增 a-r0／a′-r0，不能把 a-γ 的 standby／interruption 敏感度當成 a-r 的穩健性；若保留 a-r primary，應補其關鍵對照。【05 §4；05d §3】
   U 同時取消 cap 與 margin，不能分辨兩者效果；snapshot 是數值近似，須與固定決策時刻下的收斂積分比較。
   每格重訓估計 regime-specific efficacy，固定舊政策則估計 transfer；失敗格不算零效果，修 bug 也不能成為換 primary 的藉口。

8. **有，部分審查把正確疑點升格成了錯誤定論。**
   **06 H1、08 D、09 A1–A3：**只有 \(pG^T\) 固定；功率可下降、bits 可變，dwell phase≠segment age，現有資料未識別 +2.9% 有多少來自 renewal。【03 A、B01；05 §1】
   **06／08／10 correction 的 Φ 解釋：**實際 repriced Q1/Q2 未使用 legacy Φ，不能說該 BASE「被 Φ 訓練得避免換手」。【12-E 詳細 §11】
   **01 §2–3、15 §3：**consolidation 不必提高 EE；共同能耗底值也可翻轉排序，例如 \(9/8>10/10\)，但 \(9/28<10/30\)。【04 A】
   **13 §4：**解碼失敗不要求事後刪除發射者直到達到 admission fixed point；那會改寫已發生的干擾與耗能。【05 §2.11】
   **17 §3–5：**共同 \(\Delta t\) 抵消不能消除積分偏差；平均 RF 誤差也不能直接換算成非線性 PA 能量誤差。
   **18 §3：**不同面板的中位數不能相減作精確因果分解；無衰落 ceiling 亦不能直接證明隨機通道歷史中位數不可能。【20「Focused physics checks」「Ambiguities」】
   **20「Three defect tests」／21 最後附錄：**「每個 head 使用自己的 target network」與「各 head 獨立取 max 造成不可共同實現的 target」是不同測試，兩份結論未必矛盾。
   **20 並非全數誤差 <\(10^{-6}\)**：bits 最大 \(2.93\times10^{-6}\)；此量級不足以解釋 2.9%，而公式重現也不等於物理模型成立。

PRIMARY=b | SERVICE=replace | EVAL_MIN=五組以上獨立訓練、共同未開啟面板、條件式因子對照與跨種子／時間區塊不確定性 | MATRIX=sound
