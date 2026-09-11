# Ruling — Q5 NO-GO; the multi-catfish question stays open; the ceiling's three scenarios and their consequences

Date: 2026-09-11, ~13:35 UTC (server clock). **Owner decision**, recorded before any ceiling number is known to the
controller or the owner (the ceiling search, step 7, is running; H4 probe running). Supersedes the *action* attached to
declared branch 1 of the pilot (`DECLARATION-THREE-CATFISH-PILOT` §Declared reading: "proceed to full-length runs and
drop-one ablations"). The declared **reading** itself stands: the pilot is recorded as branch 1 by the pre-declared rule
(`.scratch/cf3-pilot/CF3-PILOT-2026-09-11.md`); what changes is what is done next, and why.

## 1. Owner decisions (verbatim, Traditional Chinese)

| item | decision | owner's reason |
|---|---|---|
| Q5 全長 3000 ep ＋ drop-one | **NO-GO** | 「目前 A2 directed Catfish = 102.03M、A3 random pool = 101.24M，真正 directed source 相對 random 只有 +0.78%；反而 A3 對 A1 有 +2.6%。現在做 drop-one，是在拆解一個還沒證明超過 random replay 的 effect。」「關閉 Q5，但不關閉 Multi-Catfish 研究題目。」 |
| 論文是否直接轉負結果 | **現在不要定案** | 「Fable 的 DEAD-PATH 判斷有相當證據，但現在正在跑的 EE ceiling 正是最後一個能區分『物理根本沒空間』與『目前 learner 拿不到空間』的關鍵實驗。等它回來再決定。」第三條路：「關掉『目前這個 three-Catfish implementation』，但不關掉 multi-Catfish 題目；利用 ceiling 找出真正存在的 EE control surface，再重新定義三隻 Catfish。」 |
| Q8 清理 | **部分立即執行** | sat 上四個舊 watcher（PID 1209666、1332348、1430512、2469243）可殺；`watch_health.sh`（3291897）保留。`b0/corrected-baseline-20260911` **不能直接刪**：四個 commit（832471ca、0acd146c、923d68b0、ccbbb048）不在 HEAD ancestry；「content diff → 確認功能是否已由其他 SHA port 進主線 → 留一個 archive tag / note → 再 remove worktree，不是直接 git branch -D」。 |
| ChatGPT Deep Research | **做，放到新對話** | pre-result package 已備妥；文獻問題不需等 ceiling；fresh context 是優點。 |
| Q7 加速 | **不要做** | Q5 不跑，加速沒有價值。 |
| Q4 energy-credit 重設計 | **等 ceiling** | 「ceiling 如果顯示 per-user observable headroom，Q4 會成為最高優先；若沒有，修 credit 也沒有用。」 |
| Q6 DQfD／faithful catfish／ACRM 等 utilisation arms | **暫停** | 「先解 source-value / controllability，再研究如何注入。」 |

Owner's causal structure of the pilot (pinned, 24 evaluation episodes, final checkpoint, 3 seeds):
A0 84.21 / A1 98.64 / A3 101.24 / A2 102.03 M bit/J — objective/learner change +17.1 %; any offline replay ≈ +2.6 %;
directed vs random +0.78 %. On the calibration episodes: A2 106.2 vs `A m=2dB` 112.2.

## 2. The ceiling's three scenarios — reading declared now, consequences fixed now

Comparison object: the constrained (service-floor) centralised Dinkelbach coordinate-ascent search vs `A m=2dB` on the
same 24 evaluation episodes (paired per-episode sem); reference on that set `A m=2dB` = 107,000,984 bit/J (ceiling
agent's step 5). Thresholds follow the MDE-based rule adopted in `WORK-QUEUE-DECISIONS` (agy check item 14).

| scenario | condition | what it means | what is done next |
|---|---|---|---|
| **A** | constrained ceiling ≤ **+3.3 %** over `A m=2dB` | no learner — per-user or centralised — has room on this physics/action space | stop changing the DQN, the catfish, DQfD. Re-examine the **physics and the action space**: payload power model; per-beam controllable power; beam sleep/activation; handover interruption; which resources are controllable at all. The three catfish otherwise compete for a margin that does not exist. |
| **B** | ceiling high **and** the nominal-information unilateral point ≥ **+4.5 %** over the rule, served ≥ 0.995, bits ratio ≥ 0.95 | a per-user learner has a job; the current credit / objective / representation is what is wrong | next version: difference reward / counterfactual credit (via `evaluate_actions`) + corrected `Q_B`/`Q_E` decomposition + catfish sources; only then are DQfD, ACRM, JSRL and source-specific catfish worth studying. Q4 becomes top priority. |
| **C** | only the joint / compound (beam-emptying) search is high; the nominal-information unilateral point is not | headroom exists but not for an independent per-user argmax | move to centralised training → joint / set-level critic → CTDE or a coordinator; multi-catfish continues, but the catfish teach different **joint operating regimes**, not three independent Q-heads. |
| between A and B/C thresholds | +3.3 % < ceiling, unilateral < +4.5 % | room too small to resolve with affordable seeds | report as unresolved; no training is launched on it. |

The controller reads the ceiling report against this table when it lands, then sends phase 2b to the Fable auditor with
this ruling attached, then writes the phase-boundary handoff.

## 3. What this ruling closes and what it keeps open

- Closed now: Q5, Q7; the current three-catfish implementation as a candidate for full-length training.
- Paused: Q6 (until source value and controllability are shown).
- Conditional: Q4 (scenario B); the redefinition of the three catfish (scenarios B/C).
- Open: the multi-catfish research question; the paper's framing (decided after the ceiling).
- Executed on this ruling: Q8 part 1 (four stale watcher processes on `sat`, exact-PID, after cmdline check);
  Q8 part 2 dispatched as a content-equivalence audit of `b0/corrected-baseline-20260911` (tag + note before any removal;
  branch deletion stays with the owner).
