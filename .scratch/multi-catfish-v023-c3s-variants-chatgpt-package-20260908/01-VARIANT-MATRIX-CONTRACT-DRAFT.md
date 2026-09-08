**V023-C3S-VARIANT-MATRIX-KILL-SCREEN-CONTRACT-2026-09-08.md**

狀態：**DRAFT／pre-outcome**。依 Owner 2026-09-08 10:35 UTC 指令，一次宣告七個 variants，於同一 closed-loop panel 平行篩選，存活者才取得後續資格。本次僅於 SERVER E1 checkout 唯讀起草，無編輯、network 或實驗。

**依據與限制。** 繼承 `.scratch/multi-catfish-v023-c3s-screen/V023-C3S-SET-LEVEL-COORDINATOR-KILL-SCREEN-CONTRACT-2026-09-08.md` 及 Addendum A。使用者指定其為 sealed v1；本地副本仍含 DRAFT 字樣、可寫且未見 seal sidecar，freeze 須核驗權威 digest。已讀 S0 diagnostic：S0 +1.81%、S0-U +1.52%、S0-J +1.76%，均為已知 development evidence，不能推論 closed-loop efficacy。

指定的 `ADJUDICATION-OUTSIDE-ROUND3-C3S-CODEX-GPT6-ASTRA-2026-09-08.md` 在本 checkout 未找到。本稿採使用者提供的機制與 reporting list：myopic reconfiguration 可能經 tracking／handover costs、occupancy 改變侵蝕即時收益；這是待檢驗假說。Freeze 須補齊來源核對，不藉此修改以下科學選擇。

**共同規則。** BASE 為 frozen learned `argmax(Q1+Q2)`：E1 lineages `2026092101–03`、各 `rung-003000`，Q2 initialisations `2026108101–03`；float32、unweighted masked sum、最低合法 slot tie，28 slots，空 mask 為 `NOOP=-1`。九臂各自在自身 state 重算 proposal \(b_t\)，不得共用 BASE trajectory 的 proposals。

令 \(F_t(x)=\hat B_t(x)-\eta_{\rm ref}\hat E_t(x)\)，固定
`η_ref = 0x1.d94fb72305d6ap+26 bits/J`。除明列的單一 lever 外，所有 coordinator 使用相同 nominal guard \(\hat C_t(x)\ge\hat C_t(b_t)\)、完整配置 physics、atomic commit。Nominal channels 為 unit Rician gain、zero-dB shadowing；realised execution 保留 v1 E1/G0 physics 與 keyed fading。投影不得讀實際未來 trajectory、fading、RNG／field keys、oracle scores、另一臂狀態或 running endpoints。

**Lite catalog。** 按 Addendum A 精確解讀「top-2」：BASE，加每人最多一個 unilateral edit；依 Q12 排序自 runner-up 掃描，跳過 NOOP／BASE-equivalent，取首個不同 physical action。另列全部 full-origin evacuations：origin membership 取 BASE nominal service resolution，全部 served members 搬至共同合法的單一 destination；包含 singleton origins、empty destinations，不限 top-2，不列子集合或混合 destinations。

保留合法但未成功撤空的配置。相同 vectors 可 memoize，保留 aliases。Tie keys 沿用 BASE `(0)`、unilateral `(1,user,slot)`、evacuation `(2,origin_NORAD,origin_cell,destination_NORAD,destination_cell)`，字典序最小優先。Binary64 physics coefficients 按 exact rational 比較，無 epsilon；BASE 始終可選。Lite 約 260 nominal evaluations／decision，實際 census 不截斷。

**Variant matrix。** 下表成本為相對 lite 的規劃估值；各臂僅改一個 lever。SUPPORT／NO_SUPPORT 均指後述共同 endpoint rule，不能單憑 arm 結果證明機制因果。

| Arm／唯一 lever | 精確規則與目標機制 | 成本／lite | SUPPORT／NO_SUPPORT 的解讀 |
|---|---|---:|---|
| **V-J：catalog** | `BASE ∪ evacuations`；移除 unilateral family。測試共同撤空是否足以保留收益並減少搜尋。 | 約 60 evaluations，0.23× | 撤空限定策略可／未能取得 progression 資格；不證明全部收益源自 evacuation。 |
| **V-U：catalog** | `BASE ∪ top-2 unilateral edits`；無 evacuations。測試大型共同重配置是否帶來後續損失。 | ≤101 evaluations，約0.39× | 單人候選限定策略可／未能存活；不等同 S0-U 的跨 panel replication。 |
| **V-M：acceptance margin** | 先按 lite 選 \(x^*\)，僅當 \(F_t(x^*)-F_t(b_t)\ge m_t\) 才採用，否則 BASE；固定 \(m_t=\hat B_t(b_t)/1000\)。0.1% 為小幅 bits buffer，篩除可能被後續成本抵銷的微小收益，永不調整。BASE bits 為零時 margin 為零。 | 約1× | 此固定 buffer 可／未能通過 screen；不是最適 margin 證據。 |
| **V-C：cadence** | 僅 \(t=0,3,\ldots,27\) 執行 lite，其餘步直接 BASE；不沿用上次 coordinator action。測試降低介入頻率。 | 活躍步1×；全程平均約⅓×，另有 BASE 成本 | 每三步介入可／未能存活；不推論其他 cadence。 |
| **V-H：hysteresis** | coordinator override 若使 user 的 physical action 同時不同於 \(b_t\) 與先前 committed association，鎖定該 user 於 \(t+1,t+2,t+3\)，\(t+4\) 解鎖。鎖定期間只允許候選對該 user 採 \(b_t\)；BASE 可移動它且不重設鎖。含受鎖 user 的違規 evacuation 整個排除，不拆成子集合。測試快速反覆搬移。 | ≤1×，加小量狀態成本 | 三步鎖定策略可／未能存活；不證明所有 churn 有害。 |
| **V-P：objective** | 最大化 \(F_t(x)-\kappa\sum_u[1-\hat\chi_u(x)]\)；χ 定義如下。測試短暫可行配置與 persistence risk。 | 約1×加共享 D2/TLE projection、逐 profile indicator aggregation；暫估1–2× | 固定 persistence pricing 可／未能存活；不代表 C2 efficacy 或獨立第三 learned head。 |
| **V-L2：objective** | 最大化候選當步與一個 projected BASE interval 的 \(F\) 總和；細則如下。測試次步 tracking／occupancy／handover 後果侵蝕收益。 | 約2× nominal interval evaluations，另加逐候選 clone、projection、Q12 inference；總 latency 可更高 | 一步 lookahead 可／未能存活；不推論長期最優。 |

**V-P 的 joint χ。** 固定 \(\kappa=10097071012.757404\) bits，binary64 authority 為 `0x1.2cea89d260f2ap+33`，沿用 C2 尺度。使用 `src/mcrl/runtime/ee_axis_ops3_live.py` 與 `ee_axis_ops3.py` 的 native convention：

對每個 complete profile \(x\)，以純 nominal resolution 建立所有 users 的 \(o_{u0}(x)\)、所選 physical keys 與 segment-start gains；continuation 保留 committed gain，opening warm-start 沿 native 規則。NOOP／unserved 的 opening indicator 為零。

固定 user ECEF、neighborhood 及所選 `(NORAD,cell)`；複製 D2 tracker，僅傳播已 tracked TLE universe，每 0.640 s 更新，47 個 substeps 取一個 endpoint，沿用 OPS-3 endpoint range-rate 重複 convention。\(H=\min(3,29-t)\)。每 offset 的 \(\rho_{uh}\) 要求原 action 合法、D2 eligible、cell visible、gain>0，且 recurrence \(p_0g_{\rm start}/g_h\) 通過 canonical power-feasibility predicate；不得 clamp power 或新增 SINR／demand threshold。

\[
\chi_{uh}=o_{u0}\prod_{j=1}^{h}\rho_{uj},\qquad
\hat\chi_u=H^{-1}\sum_{h=1}^{H}\chi_{uh}.
\]

失效後不恢復；\(H=0\) 明定 penalty 為零。χ 無單位，penalty 與 \(F\) 均為 bits，不再乘秒或 H。這採 C2 的 offset-average convention，不取最後一個 offset。

Joint profile 必須涵蓋全部 users 的 selected actions 與 opening resolution；不得把對 BASE 的 unilateral surplus 相加。OPS-3 persistence gates 本身是 link-local，允許共用 geometry/D2 surfaces 再依完整 \(x\) 取值；不得誤稱 χ 已衡量 joint interference。當步 bits、energy、load、interference 仍由完整 joint physics 計算。

**V-L2 投影。** 每個候選，包括 BASE，從相同 predecision snapshot 各建 detached clone；nominal commit \(x\)，保留其 association、segments、occupancy、tracking 與 handover ledgers。固定當前 user positions、dwell/neighborhood，不抽未來 mobility／dwell randomness；沿 native clock 推進 TLE/D2、重建合法 candidates，在此 projected state 重算 frozen Q12 BASE，再 nominal 評估一次。

\[
J_t(x)=F_t(x)+F^{\,x}_{t+1}(b^{\,x}_{t+1}).
\]

只 commit 第一個 action。\(t=29\) 時第二項為零；無 discount、第三 interval、future coordinator 或額外 penalty。Service guard 僅檢查當步，避免新增第二 lever。以上 stationary-user shadow、V-H 鎖定邊界及 V-P averaging 均為未充分指定處的固定直讀。

**Panel 與平行執行。** 固定 BASE、C3-S(lite)、七 variants，共九 trajectories／unit。Lite 完全沿用 v1 Addendum A，供跨 run 描述性比對。四 worlds：

| Domain | Seed |
|---|---:|
| `C3S_SCREEN/world/1` | 8464287092499831892 |
| `C3S_SCREEN/world/2` | 7305539127129390835 |
| `C3S_SCREEN/world/3` | 7691130988233444596 |
| `C3S_SCREEN/world/4` | 5887834234954284271 |

沿用 v1 seed derivation、`SeedSequence(world).spawn(4)` 角色及 keyed-field namespace `MCRL_V023_LCSRS_C3_OBSERVABILITY_V1`；field key 不含 arm／lineage。四 worlds ×三 lineages＝12 units；100 users、T=30、t=0–29、interval 使用 native `47×0.640 s`，約30.08 s。共108 episodes、3,240 committed steps，每臂36,000 opportunities。

九臂同初態、各自 closed-loop 推進，不重設至 BASE anchors。所有 variants 在 outcomes 前共同封存、同批排程，不等待某臂結果才設計下一臂。重用 worlds 必須揭露既有 exposure，不宣稱重新 fresh。

**唯一 kill rule 與 progression。** 用 committed `last_outcome`：
\[
B_t=\Delta t\sum_uR_{ut},\quad E_t=\Delta tP_{{system},t},\quad
\eta_A=\frac{\sum B_t}{\sum E_t},\quad s_A=\frac{\sum C_t}{36000}.
\]

完整有效 panel 上，各 coordinator arm：
**SUPPORT iff \(\eta_A>\eta_{\rm BASE}\) 且 \(s_A\ge s_{\rm BASE}-0.001\)**；否则 NO_SUPPORT，列出所有失敗原因。採 exact pooled comparison，不平均 episode EE；service 容許最多減少36 served opportunities。BASE 本 run 重算，不替換為歷史 endpoint。

所有 SUPPORTers 取得後續規劃資格；唯一優先配置為360 decisions 的**平均 total decision latency 最低者**，包含 cadence 的 BASE-only steps及 projection；同值依 `V-J,V-U,V-M,V-C,V-H,V-P,V-L2,lite`。Latency 不是 kill gate。無 SUPPORT 即關閉本矩陣 progression。不得隱藏任何 arm。

Provenance、資訊隔離、physics、matching、非有限值或 coverage 矛盾為 **INVALID_RUN**；中斷、資源不足、缺集為 **INCOMPLETE**。任一者成立，整個 matrix 不作正式 SUPPORT／NO_SUPPORT 或 progression；保留已得資料。

**完整報告與成本。** 九臂全部公布 pooled B/E/EE/service、差值及失敗原因；逐 world cluster、lineage、unit 報告，不把12 units 當12個獨立 worlds。公布：

- Q inference、enumeration、evaluation、projection／clone、total latency 的 mean／median／p95／max、超過30.08 s 比例、candidate census、peak RSS。
- 每步與累積 bits、joules、EE、service 及相對 BASE 差值曲線。
- override／fallback／guard rejection、evacuation 成功率、handover classes、tracking／segment resets、occupancy、active beams／satellites、PA／system power。
- 相鄰及三步內 physical association reversals，區分 BASE 與 coordinator 造成；nominal gain 對 realised outcome 及 curve sign reversals。不可將 reward handover penalty 另加為 joules。

規劃 envelope 為約 **9×lite**，含 projection、clone、驗證 overhead，預留約 **v1 full arm 的1.3–2×**；12 workers 約 **1.5–2 h**。純 evaluation 數的9×lite 並不算術等於上述 full 比例，兩者為粗略算力與 wall-time 預算，須分別驗證；不得以時間壓力改 catalog、timeout-to-BASE 或提前裁決。

**Multiplicity、禁止事項與 freeze。** 九臂包含共同 BASE，實際為八個 coordinator-versus-BASE contrasts，只有四個 world clusters；這是 development screen，沒有 confirmatory multiplicity control。Survivor 仍須新 worlds、另封規約的 FULL2 confirmatory `100→500→1500→3000` ladder，主比較 `FULL2+survivor vs FULL2`。本稿不授權執行該 ladder，不成立三項正貢獻，也不重開已關閉的 additive C3 路線。

禁止 outcome 後改 lever values、混合 levers、換 seeds／horizon／regime、挑選重跑、刪除失敗臂、learner updates、TEST 或 realised-information selection。有效結果不重跑；僅修復有證據的 infrastructure defect，保留全部原 receipts 與 repair provenance。

Freeze checklist：

- 核驗 v1＋Addendum A seal、補齊 round-3 source、記錄全部已知 exposure；封存本文及 evidence manifest。
- 綁定 checkpoints、parameter hashes、TLE archive、physics、dependencies、code、launch arguments、12-worker scheduling。
- 驗證九臂 coverage、matching、lite equivalence、catalog/ties、margin、cadence、lock 邊界、joint χ、terminal/lookahead、state/RNG purity、accounting 與 progression。
- 封存 `<<BIND_AT_FREEZE:CONTRACT_SHA256>>`、`<<BIND_AT_FREEZE:EVIDENCE_MANIFEST_PATH>>`、`<<BIND_AT_FREEZE:EVIDENCE_MANIFEST_SHA256>>`、`<<BIND_AT_FREEZE:EXECUTION_MANIFEST_PATH>>`、`<<BIND_AT_FREEZE:EXECUTION_MANIFEST_SHA256>>`、`<<BIND_AT_FREEZE:OUTPUT_ROOT_PATH>>`。
- 記錄 freeze timestamp／reviewer；write-once receipts、atomic publication、0444、重開驗 hash；resume 僅接受 authenticated complete units。所有科學值已固定，placeholder 僅供 paths／digests。

Claim ceiling：`TRAIN_DEVELOPMENT_C3S_VARIANT_MATRIX_KILL_SCREEN_NO_LEARNER_NO_EFFICACY_NO_TEST`

ASTRA_C3S_VARIANTS=DRAFTED