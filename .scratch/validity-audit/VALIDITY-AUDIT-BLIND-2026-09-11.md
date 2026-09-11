**Verdict: DEAD-PATH as framed — on this physics pooled EE reduces to the mean spectral efficiency per lit beam (power per beam and per-user throughput both cancel), a one-line max-gain rule already nearly maximises that quantity per user, the only lever left above the rules is co-channel interference across the joint lighting pattern (I/N ≈ 6), which a per-user policy can neither observe at decision time nor act on jointly, and the pilot's "ratio learner" is structurally an own-bits DQN (the equal-share energy term flips the argmax in 0/240 probed decisions) whose selfish bandwidth-share objective pushes toward more lit beams, the EE-negative direction — so neither this learner nor static rule-pool replay can be expected to raise EE above the hysteresis rule; only the owner's low gate (beat MODQN's misaligned reward) is reachable, and that claim is about the baseline, not about learning.**

## 給 owner 的摘要（繁體中文，讀這 15 行就夠）

1. **判定：DEAD-PATH（以目前的框架）。** 不是「訓練不夠久」，是箱子本身：在這套物理裡，pooled EE ≈ 每支點亮波束的平均頻譜效率 × 常數。每束功率與策略無關（六個參考臂都是 187–193 J/beam-step ≈ 6.3 W，pinned 24 校準集，[D]），波束數在分子分母同時出現而相消，每人吞吐量根本不在目標裡（B1 把每人速率從 451 砍到 258 Mbit/s，EE 只掉 7%）。
2. 這個量已被一行規則在每個使用者層面近乎最大化：C1 `A m=2dB` 112.20M vs 訓練 9000 集的 MODQN 93.90M（同一 pinned 校準集）；規則前緣從 m=2 到 6 dB 平坦（±1%，unpinned 本地集）。
3. 規則之上唯一剩下的物理槓桿是跨波束同頻干擾（I/N ≈ 5.9，CAPPENALTY 分解＋噪聲功率推算）。這是「聯合決定點亮哪些波束」的協調問題：per-user 觀測只看得到上一步的干擾，per-user argmax 也做不出聯合動作。天花板量測會告訴我們這個槓桿多大，但不會改變「這個 learner 拿不到它」。
4. 新 learner 實際上是純 own-bits DQN：等分能量標籤讓 η·Q_E 在 0/240 個決策改變 argmax（CF3REVIEW 探針）；一個使用者點亮一束只改自己能量標籤的 1.6%。Dinkelbach 的 η 更新是裝飾。而 own-bits 是搶頻寬份額 B/U_b 的自私目標，推向多開波束——正是 EE 為負的方向；它與系統一步目標在 43% 決策上不一致。
5. Catfish 機制（靜態規則池、每批 11.7%、無模仿損失、無預訓練、無 n-step、無 PER）就是 DQfD 論文裡最差的兩個對照臂（RBS／HER）的配置，且整個示範／競爭／課程文獻是為稀疏獎勵探索設計的；這裡是稠密獎勵、10 步、28 個遮罩動作，ε-greedy 就能覆蓋。最強先驗：A2 ≈ A3 ≈ A1，3 seeds 分不出。若 A2 > A1，最可能是 B1 池帶來的狀態覆蓋或雜訊，不是「示範教會了節能」。
6. Owner 的門檻（贏 A0）多半達得到，但原因是 MODQN 的 r2/r3 佔 r1 項幅度的 61% 且與 EE 反向。能存活的說法只有「MODQN 的獎勵在這套物理上與 EE 錯位」，不是「學習提升了 EE」。審稿人會要求把 `A m=2dB` 與集中式天花板放在 A0 旁邊，並拒絕任何低於一行規則的「學習有效」宣稱。
7. 該做的事：等天花板（要加 nominal-information 變體與每人吞吐量回報）；≤ +3% 就關線；≥ +10% 且 per-user 資訊可達，才值得重做 credit（用 env 現成的 `evaluate_actions` 做 difference reward）或改成協調／集中式決策問題。Q5、Q6、Q7 不要跑；Q4 只在上述條件下做。
8. 誠實的論文：「一行遲滯規則在 EE 上勝過 MODQN；MODQN 的 handover／load 獎勵在有幾何的多波束物理裡與 EE 反向」。這是可以發表的負結果加診斷，不必假裝有學習貢獻。

---

# Blind validity audit of the "learned beam assignment for pooled EE" direction

Reviewer: fresh-context auditor (no prior involvement). Date 2026-09-11. Blind to the CF3 pilot result and to the ceiling measurement.

**Blindness log.** No `ssh`, nothing under `/home/sat/`, none of the forbidden files opened (`CF3-PILOT-*.md`, `cf3-pilot/report/`, `PROGRESS.md` beyond line 148, forecast beyond line 57, `gpt4.md`, `readings.jsonl`, `eval/*.json`, `CF3-SUMMARY.json`, `CF3-TABLES.md`, `.scratch/ee-ceiling/` except `PROMPT.md`, `.scratch/reviews/validity-agy/`). Two incidents to disclose: (1) `.scratch/cf3-pilot/PROGRESS.md` lines 116–118 (inside the allowed range) mention ep-100 progress readings of the **aborted** 10:25 launch — not a pilot result; I do not use them. (2) On resuming after an API-limit interruption, the environment's git-status block showed a new commit subject line "agy blind validity audit (DEAD-PATH) + controller check: cross-archive numbers and wrong citations, kept as hypotheses only". I did not open that directory; the other reviewer's verdict word reached me through the commit subject only. Everything below was derived from the artefacts and code before and independently of that sighting; I record it so the controller can weigh it.

**Evidence tags.** [V] verified by reading the code/artefact or running trivial arithmetic on it this session; [D] derived arithmetic on [V] numbers; [I] inferred; [R] relayed from a project report or a search abstract, not re-checked by me.

**Condition groups (never compared across groups).**
- **[P24cal]** MODQN harness, 100 users, 10 steps × 30.08 s; estimand pooled Σbits/ΣJ divided once, full-buffer Shannon numerator, consumed power (PA supply + 0.338 W/beam + 0.200 W/active satellite, per-beam `max`); host `sat`, pinned TLE archive `427e6a91…`; 24 calibration episodes per-episode reseeded (env `9_121_000+i`, mobility `9_122_000+i`); no training; tree `1d8c3caf` (worktree `cf3/pilot-20260911`). Source `.scratch/cf3-pilot/PROGRESS.md:48-62` [V].
- **[L24]** same harness/estimand/accounting; host local, **unpinned** archive `e07f3e1e…`; 24 episodes, seeds 42/1337/7, fresh env per cell (only episode 0 paired across cells); no training. Sources FEASFRONT, CFSCREEN, POWERACCT, registry FF-/SC-/BP- rows [V].
- **[CAP]** CAPPENALTY: host `sat`, pre-pin archive, capped MDP (k=3 per satellite) vs uncapped, OFF weights or 500-ep retrains, 1 training seed, 24 or 96 episodes [R, registry CP-01..CP-05].
- **[B0s]** B0 smoke: `sat`, pinned, stream harness seeds 42/1337/7, 500-episode retrains at training ε = 0.753, 24 episodes [R, registry B0-10..13]. Smoke only.

---

## A. Is the problem well-posed?

### A.1 What the endpoint is on this code

- Per-user rate `R_u = (B_w/U_b)·log2(1+γ_u)`, `B_w = 166.67 MHz`, `U_b` = served users on the beam (`link_budget.py:590-616`, applied at `step.py:964-971`) [V]. Therefore a beam's bits are `B_w·dt·mean_{u∈b} log2(1+γ_u)`: **the number of users on a beam does not change the beam's bits except through their mean spectral efficiency** [D]. (Erratum 25's `R_beam = B·mean SE` is correct.)
- System power `P^N = Σ_b P_DC(max_{u∈b} p_u) + 0.338·N_beams + 0.200·N_active_sats` (`link_budget.py:439-587`, called at `step.py:973-993`) [V]. `P_DC(p) = p/ξ(p) = 6.527·√p` W for `p < p_sat` [D from `:468-519`]; link power runs from `p⁰ = 0.825` W to the ceiling `1.65` W (`:175, :213`), i.e. 5.93–8.38 W per beam [D]. Measured across the six [P24cal] reference arms, joules per beam-step are **187.7–193.0 J (6.24–6.42 W per lit beam)** — the same to within ±1.5 % whatever the policy [D, table in B.1]. **Power is a per-beam constant.**
- Hence on this physics pooled EE ≈ `(B_w / P̄_beam) × (average over lit beams of the per-beam mean spectral efficiency)` [D]. **Beam count cancels; users per beam cancel; per-user throughput cancels.** The one quantity a policy can move is the mean SE of the served links, averaged over lit beams.

### A.2 What this does to the formulation

1. **The service floor is non-binding and does not protect what it is meant to protect.** Outage arises only when the recurrence power exceeds `p_max` (`step.py:812-822`; largest in-segment loss measured 0.718 dB against a 3.010 dB budget, `link_budget.py:737-751` docstring [V-doc]) or when a user has no legal action; a user cannot choose to be unserved (`assert_selected_actions_valid`, `action_contract.py:574-608` [V]). Every non-random arm serves 0.9966–0.9987 of user-steps [P24cal] [V]. The action contract, not C-S, blocks the "drop users" degeneracy. C-S (−0.5 pp vs A1) can only ever bite on a pathological learner.
2. **The unblocked degeneracy is per-user throughput.** `B1_NO_NEW_BEAM` delivers 258 Mbit/s per served user against 451 for `A m=2dB`, at 104.19M vs 112.20M bit/J [P24cal, D] — 43 % less service for 7 % less EE, and a better packing could do the same at zero EE cost [I from A.1]. Nothing in the endpoint (pooled EE, C-S on *served fraction*, handover reported) prices delivered throughput. A referee will ask why an "energy-efficient" policy that halves everyone's rate counts as a win.
3. **Handovers are free in this physics**: joules accumulate per beam with no association term (`step.py:973-993` [V]); no interruption model exists in the MODQN engine (the ruling on the trained objective confirms it [R]). With `p·G^T` invariant inside a segment (`link_budget.py:379-408` [V]), holding a fading link raises `p` (denominator) without raising the wanted signal, while re-anchoring on the best beam resets `p` to `p⁰` — the PA's cheapest operating point — at the best gain. Free handover + this recurrence make "re-anchor at maximum nominal gain" close to the per-user optimum [I; consistent with the anchor-ablation 1.1975 → 1.2222 [L24, R] and with `A m=0…6dB` all within ±1 % [L24]].
4. **Is the objective fixed by the physics up to noise?** No: the [P24cal] arms span 51.87M (random) to 112.20M. But the spread is produced by one lever (mean SE per lit beam), whose per-user part (point at the highest-gain beam) a one-line rule captures. What is left above the rules is (a) co-channel interference across the joint lighting pattern — `I/N ≈ 5.9` at ~58 lit beams with OFF weights, falling to 0.68 under a 3-beam cap [CAP, D: noise per beam `k·T_sys·B_w = 5.575e-13` W [D from `link_budget.py:35-46, 367-372`]; interference 3.294e-12 → 3.790e-13 W [R, CP-05]] — a **joint** property; (b) second-order packing (who shares a beam matters only through the beam's mean SE, near zero-sum) [D]; (c) segment power aging (~2.5 %) [L24, R].
5. **Near-tautology in the gate.** A0's trained objective `0.5·r1 + 0.3·r2 + 0.2·r3` weights handover and load terms whose magnitudes sum to 61 % of the `r1` term (frozen checkpoint last log: `0.5·r1c = +2.37`, `0.3·r2c = −0.74`, `0.2·r3c = −0.71` [D from values relayed in CATFISH-MECHANISM-FACTS §5.1 [R]]); `MAX_NOMINAL_GAIN` is last on that scalar and first on EE [L24]. An arm whose objective drops `r2`/`r3` is expected to beat A0 on EE almost by construction [I]. That is a statement about A0's reward, not about learning.
6. **The energy signal is unlearnable at the per-user level.** `E_u = P_sys·dt/U` is identical for all 100 users (`cf_ratio.py:97-102` [V]); one user lighting one beam moves its own label by `6.27 W × 30.08 s / 100 = 1.88 J = 1.6 % of s_E = 120.6 J` [D], while its bits label moves by ~100 % of its own scale (CF3REVIEW probe: own-bits spread median 1.85 vs own-energy spread 0.0156 in normalised units; the `η·E` term changed the one-step argmax in **0 of 240** decisions [R, `.scratch/cf3-review/CF3-CODE-REVIEW-2026-09-11.md` C1]). `Q_E(s_u, a_u)` therefore learns ≈ `(T−t)·const` — the clock (which is why the remaining-steps feature was needed) — not an energy consequence of the action.
7. **Observation.** The 112-dim state is `[incumbent one-hot, log1p(candidate SINR with previous-step interference), θ (rad), previous-step demand/100]` (`state_encoding.py:70-125`, `step.py:1109-1199`, `interference.py:445-451` [V]). No current-step interference, no other user's current choice, no elevation or time-to-exit. Everything the rules use is in it (CFSCREEN: rules decoded from the observation reproduce 24,000/24,000 actions [R]); everything the coordination lever needs is not.

**Answer A.** Mathematically well-posed and policy-sensitive, but physically almost separable per user, degenerate with respect to delivered throughput, blind to churn, and — for the learner as built — informationally degenerate on the energy side. The endpoint is not "wrong"; it is nearly solved by a rule, and its remaining structure is a coordination problem the chosen action/observation contract cannot express.

## B. Where would EE headroom physically come from?

### B.1 Decomposition of the pinned premeasure [P24cal] (bits = EE × joules; 240 steps; 24,000 user-steps) [D]

| arm | pooled EE (bit/J) | bits | joules | lit beams | J / beam-step | W / beam | bits / beam-step | Mbit/s per served user |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| TRAINED `e6b063ef` (9,000 ep) | 93,902,816.57 | 2.818e14 | 3.0011e6 | 66.63 | 187.7 | 6.24 | 1.762e10 | 390.9 |
| C1 `A m=2dB` | 112,195,917.54 | 3.245e14 | 2.8926e6 | 62.98 | 191.4 | 6.36 | 2.147e10 | 450.6 |
| C2 `A m=12dB` | 100,988,477.81 | 3.301e14 | 3.2685e6 | 71.55 | 190.3 | 6.33 | 1.922e10 | 458.8 |
| C3 `B1_NO_NEW_BEAM` | 104,190,378.68 | 1.862e14 | 1.7867e6 | 38.57 | 193.0 | 6.42 | 2.011e10 | 258.4 |
| `MAX_NOMINAL_GAIN` | 110,507,234.83 | 3.199e14 | 2.8948e6 | 62.98 | 191.5 | 6.37 | 2.116e10 | 443.8 |
| `RANDOM_MASKED` | 51,866,475.49 | 1.798e14 | 3.4673e6 | 76.43 | 189.0 | 6.28 | 0.980e10 | 265.9 |

- **Joules per beam-step are policy-invariant (187.7–193.0).** Every EE difference in this table is a difference in **bits per lit beam**, i.e. mean spectral efficiency per beam. [D]
- **The ~24.4 beams that separate `B1` (38.57) from `A m=2dB` (62.98)** carry Δbits = 1.384e14 for ΔJ = 1.106e6, a **marginal EE of 1.25e8 bit/J — higher than either arm's pooled EE**. Adding gain-following beams is EE-positive at the margin; B1's consolidation forfeits more gain (users pushed off their best beam) than it recovers in interference. [D]
- **The trained learner's extra beams are the cheap kind:** TRAINED − B1 = 28.06 beams at a marginal EE of 7.9e7 bit/J [D]. It lights beams that carry little (1.76e10 bits/beam-step, the lowest of the non-random arms) — the signature of spreading users onto low-gain or crowded-interference beams.
- **Interference is the only large non-per-user lever.** Under [CAP] (OFF weights, 96 episodes, one seed): removing ~60 % of the beams left joules per beam-step flat (×1.007), cut interference per served user ×0.115, raised per-beam SE 3.39 → 4.35 (×1.28) [R, CP-05]. The lever is real. But it was reached by unserving 46 % of user-steps; B1 shows that the naive all-served consolidation loses. The coordinated optimum — light fewer beams **while** keeping each user near a boresight — lies somewhere between 112M and the interference-limited bound, and is unmeasured. [I]
- **Power-side levers are absent by construction**: no power control (p is set by the recurrence, `step.py:770-810` [V]), no sleep decision beyond "no user chose the beam", per-beam `max` aggregation makes an added user cost 0 J in 83 % of cases [L24, R BP-08].

### B.2 What the lever is, and whether a per-user policy can pull it

The lever is **mean spectral efficiency per lit beam** = f(own off-axis gain, co-channel interference from the joint lighting pattern, segment power). A per-user policy on the 112/113-dim observation:
- **can** pull the own-gain part — that is the rule (block 2 is the nominal SINR; the rule is `argmax` over it with an incumbent hold);
- **cannot** see the current-step interference (block 2 uses the previous step's radiating set [V]) nor other users' current choices, and **cannot** execute the joint move that empties a beam (all its users must move together); the lagged demand block is the only tacit-coordination channel, and CFSCREEN's behaviour-cloning probe of B1 reproduced only ~70 % of its consolidation from that channel [R, L24];
- pulls the segment-power part only weakly (≤ ~2.5 % [L24, R]).

So the reachable-by-per-user headroom above `A m=2dB` is, on this analysis, a few percent at most; the coordination headroom may be larger but belongs to a different action space. [I]

## C. The ceiling

- **Transfer from the registry's V0.25 rows (SV-CE-01…05, +0.84 % coordination ceiling)?** No. Those are the V0.25 a-r0 engine (TDM per-beam accounting, capped active set, 50 Mbit/s rate target, 12 anchors × 4 steps), a different physics and estimand (registry §0 trap 4 [V]). Only the qualitative warning transfers: on that panel joint moves bought < 1 % over a unilateral fixed point.
- **Is the parallel brief (`.scratch/ee-ceiling/PROMPT.md`) the right instrument?** Mostly yes for the question "room above the rules at one-step myopia": centralised Dinkelbach coordinate ascent over the joint assignment with the environment's own counterfactual evaluator (`evaluate_actions`, `step.py:643-723`, common random numbers, no state committed [V]), a served-user floor, paired with the pilot's evaluation episodes, references re-run on the same seeds, placebo-first. Its declared limits (one-step myopic, local search, budget hits) are the right ones.
- **What I would change or add**, in priority order:
  1. **Report bits and per-user throughput beside EE, and add a rate-floor variant** (e.g. no served user below 50 % of its `A m=2dB` rate). Without it the search can "win" by packing users onto fewer beams and halving their service (A.2.2). The served-user floor does not close this hole.
  2. **Run the nominal-information variant** (score candidates with block-2 nominal SINR, previous-step interference) and a **unilateral best-response fixed point** (each user picks its best action given the others, iterated) with the realised evaluator. Together they split the gap into *information* (realised vs nominal) and *coordination* (joint vs unilateral). This is the decisive split for the direction: a per-user learner can at best reach the nominal-information unilateral point.
  3. Start the search from three initialisations (`A m=2dB`, `B1`, random) and report basin sensitivity; local search from the rules may sit in their basin.
  4. A cheap two-step look-ahead on ≥ 6 episodes for the segment-power effect (hold vs switch), to bound the "multi-step optimum could be higher" caveat.
- **Outcome that kills the direction:** constrained ceiling ≤ +3 % over `A m=2dB` (paired per-episode sem on the 24 evaluation episodes) → no learner, per-user or centralised, has room; the paper is the rule.
- **Outcome that keeps a (different) direction alive:** ≥ +10 % with all users served, bits ratio ≥ 0.9, **and** the nominal-information unilateral point capturing at least half of it → a per-user learner with a *correct credit* could in principle have a job. If the gain appears only in the realised-information joint search → it is a coordination/observability problem; the deployable object is a coordinated (centralised or CTDE) policy, outside the declared per-user argmax contract — a redesign, not a fix.
- **What no ceiling outcome changes:** the pilot's learner (own-bits per-user argmax, equal-share energy) cannot reach interference headroom whatever its size (A.2.6, D.1).

## D. Can this learner reach the headroom?

**(i) Identifiability / credit.** `Σ_u B_u` equals the system bits exactly and `Σ_u E_u` the system joules exactly (`tests/test_cf_ratio.py:297-321` [V]), so the *sum* of the per-user rewards is the endpoint's numerator and denominator. But the deployed rule is a **per-user argmax of `Q_B − η·Q_E`**, and: (a) `η·Q_E` has no action contrast (A.2.6; 0/240 flips [R]); (b) `Q_B` is own bits `(B_w/U_b)·log2(1+γ_u)·dt` — a **congestion-game payoff**: a user's best response is a lightly loaded, high-gain beam of its own, which pushes toward *more* lit beams (more joules, more interference) — the EE-negative direction — while the system numerator is indifferent to `U_b` at first order (A.1). CF3REVIEW measured the per-user one-step argmax differing from the system one-step argmax in 104/240 = 43 % of decisions [R]. The three heads and the Dinkelbach price do not change this: the learner optimises the Nash equilibrium of own-bits, not the ratio. What `Q_E` can contribute: nothing to the decision; it only adds a clock-like term to the continuation bootstrap (also argmax'd through `Q_B`).

**(ii) Dinkelbach-in-DQN.** The inner form `max Σ(B − η E)` with an outer ratio update is the standard fractional-RL construction (Dinkelbach-guided DRL and fractional Q-learning exist in the literature: e.g. arXiv:2312.10418 "Fractional Deep RL for Age-Minimal MEC", arXiv:2409.16832 [V-search abstracts]). Two departures matter here. First, Dinkelbach needs the inner maximisation solved (near-)exactly before each `η` update; the pilot updates `η` twice (episodes 500, 750) from an under-trained ε-greedy learner's own greedy calibration EE — the outer loop has no convergence argument at 1000 episodes. Second, and decisively, since `η` never changes the argmax (0/240) and the continuation action is also `Q_B`-dominated, **the outer loop is inert**: harmless, and decorative. The finite-horizon "ratio of sums over 24 episodes" vs "per-episode ratio" distinction is ≤ 0.06 % on this harness [L24, R] and is not the problem.

**(iii) Budget and the three explanations of the 9,000-episode gap.** The frozen run (90,000 updates) reached 93.90M against `A m=2dB` 112.20M [P24cal]. The three causes separate as follows:
- *Misalignment* — measured: `MAX_NOMINAL_GAIN` last on the trained scalar, first on EE [L24, R]; `r2 + r3` = 61 % of the `r1` term [D].
- *Under-optimisation* — measured: `A m=12dB` beats the checkpoint on the checkpoint's own calibrated scalar (+1.22 vs +0.90, [L24, R FEASFRONT §5.4]) — the learner is not at its own objective's optimum.
- *Representational limit* — measured and small: the Q-architecture as a classifier fits the argmax rules to 0.81–0.84 top-1 and the hysteresis rules to 0.92–0.94; closed-loop, the `A m=2dB` clone loses 1.3 % EE, `B1`'s clone 4.3 % [L24, R CFSCREEN §1b–1c]. Representation costs 1–4 %, not 17 %.
So the gap is misalignment plus under-optimisation. The pilot has **10,000 updates, one ninth of the frozen run's**, ε decayed over 222 episodes, target sync every 50 episodes (`cf3_common.py:40, 82-92`; `trainer_spec.py` defaults [V]). That is enough to read *direction vs A0 at equal budget* and not enough to place the learner relative to the rules. Checkpoint-to-checkpoint swings of the order of 20 % were seen in 500-episode retrains ([CAP] CP-04 ratios 1.399 → 1.162 across checkpoints, one seed, capped MDP — magnitude indication only) [R]; final-checkpoint-only at 3 seeds will not resolve differences below roughly 5–10 % [I].

**(iv) If the best rule is representable, why would the learner not find it, and what does that say about "learning"?** Because nothing in the training signal asks for the rule: the learner's fixed point is the own-bits equilibrium under ε-greedy interaction among 100 copies of itself, and that equilibrium is not "point at the best beam"; it is "point at the best *lightly loaded* beam", which spreads. A learner that did converge to `A m=2dB` would have rediscovered a deployable one-line rule at a 1.3 % approximation cost — learning would have added negative value. Learning can add value only through information the rules do not use — time-to-exit, foresight on segment power, current interference — and the observation carries none of the first, ~2.5 % of the second, and a lagged version of the third (A.2.7). On this evidence the learner's ceiling is the rule minus approximation error. [I]

## E. Catfish / demonstration mechanisms

**As implemented (Amendment 3, `cf_ratio.py:196-307, 572-599` [V]):** three static offline pools (100 episodes each of `A m=2dB`, `A m=12dB`, `B1`), immutable, 5 rows each in every 128-row batch (15/128 = 11.7 %), raw `(B, E, H)` labels re-normalised at sample time, TD only — no imitation/margin loss, no pre-training, no n-step, no prioritisation, no EE-threshold split, no asymmetric discount, no intervention schedule, no ACRM. NULL3: identical pools from uniform-legal random policies (52M EE). Amendment 1 item 8 concedes it is "not faithful RIS catfish, DQfD or ACRM" [V].

**Search framings used (two independent, plus two checks).**
1. *Off-policy demonstration data in value-based RL* — DQfD (Hester et al. 2018), Replay Buffer Spiking, Human Experience Replay, R2D3, DDPGfD, Nair et al. Q-filter. Verified this session: search abstracts only; the ablation facts (RBS and HER are DQfD's two worst arms; R2D3's optimum demo ratio ≈ 1/256; DDPGfD needs n-step + prioritisation) are [R] from `DQFD-FAMILY-GROUNDING-2026-09-11.md`, which quotes paper locations.
2. *Auxiliary experience / competitive replay / curriculum / self-play* — Competitive Experience Replay (Liu, Trott, Socher, Xiong, ICLR 2019: "supplements a sparse reward by placing learning in the context of an exploration competition between a pair of agents … complements HER by inducing an automatic exploratory curriculum") [V-search abstract]; CuSP and asymmetric self-play (Sukhbaatar 2018) as ACRM's lineage [R, ACRM-PROVENANCE]; JSRL (Uchendu et al., ICML 2023: guide policy supplies a curriculum of starting states; the theory improves sample complexity of non-optimistic exploration from exponential to polynomial in the horizon; gains "particularly in the small-data regime") [V-search abstract].
3. Check: the RIS "catfish" itself is grey literature (MSc thesis, no venue [R ACRM §1.1]); its own ablation ranks ACRM smallest [R].
4. Check: fractional/Dinkelbach RL exists (D.ii) [V-search].

**Does this literature support gains in a dense-reward, 10-step, near-myopic, 28-action problem?** No — every mechanism in both framings is motivated by sparse reward and hard exploration (CER: "sparse reward"; JSRL: exploration complexity in the horizon; DQfD/R2D3: Montezuma-class tasks). Here every user-step is rewarded, the horizon is 10, the action set is 28 masked options, ε-greedy exploration runs 1 → 0.01 over 222 episodes, and 88 % of every batch is on-policy data. The static-pool-without-margin configuration is precisely the RBS/HER regime that DQfD reports as its worst, with the note that naive seeding "can sometimes be detrimental" [R]. The demo share (11.7 %) is ~30× R2D3's swept optimum [R].

**Strongest prior: A2 ≈ A1 ≈ A3** within 3-seed noise. **If A2 − A1 > 0 resolves**, the most plausible reading is *state coverage*: the `B1` pool's states are far from the learner's (novelty ratio 2.19–2.25, `loads` block [L24, R CFSCREEN §3]) and give `Q_B` support on low-beam configurations it never visits — a generalisation/coverage effect on the bits head, not an energy lesson (`Q_E` cannot act) and not evidence for RIS catfish, DQfD or ACRM. **If A2 > A3 > A1**, extra off-policy data helps and directed data helps more than random data — the NULL pools' states (random policy, 52M EE) are less useful than rule states; still a coverage-quality effect. A null for C3 is uninterpretable as "consolidation fails" (dE_sys diagnostic: 59.5 % of C3-vs-incumbent contrasts within ±1 % of the step's joules [V, PROGRESS lines 72–77]).

## F. Baseline fairness and the gate

- **A0 is the published algorithm** (eq. (16) per-head max, `modqn.py:687-700`; weights 0.5/0.3/0.2, γ 0.9, D-2 per-step floor `outage_gate.py`, lr 0.001, same ε schedule and episodes as A1–A3, `cf3_common.py:82-92` [V]) — fair as "MODQN". It is **not the paper's environment**: the paper (Sun, Zhai, Wu, Si, Yu, IEEE Commun. Lett. 28(12), 2024 — existence [V-search]; contents [R]) has no beam geometry ("a beam there is a non-spatial load channel", `action_contract.py:46-59` docstring [V-code]); this project added pointing, a 39-cell grid, real TLEs, a 30.08 s decision clock and a consumed-power model (`constants.py`, `DEVIATION-REGISTER.md` [V]). A0 is "MODQN's reward and learner on a geometry-resolved physics of this project's making".
- **Can the gate be met by the objective change alone?** Yes, almost by construction (A.2.5). What survives is **"MODQN's r2/r3 scalarisation is anti-aligned with pooled EE on a multi-beam physics with geometry"** — a finding about the baseline, useful for a thesis chapter, not a learning contribution. "Our learner beats MODQN" would be true and hollow.
- **What a referee at a good venue demands beside A0:** the best non-learned rule (`A m=2dB`, `MAX_NOMINAL_GAIN`) and a centralised ceiling in the main table; per-user throughput and served fraction beside every EE; handover rate with an interruption-cost sensitivity (0.062/0.142 s per event ≈ ≤ 0.5 % of bits [R erratum 25]); ≥ 5 seeds with paired per-episode CIs; ablation of the objective (A1 vs A0) separated from the mechanism (A2 vs A1 vs A3).
- **What they refuse:** "learning improves EE" while the learner sits below a one-line rule; "energy-aware decisions" given 0/240; "catfish helps" from a 3-seed A2 − A1 without a margin over seed noise and without the null; any EE gain that comes with halved per-user rates.

## G. Claims table

| # | load-bearing claim | status | artefact / basis |
|---|---|---|---|
| 1 | Pooled EE on this harness ≈ mean SE per lit beam × constant; beam count and per-user throughput cancel | **measured/derived** | B.1 table [P24cal, D]; `link_budget.py:590-616, 439-587` [V] |
| 2 | Simple rules reach ~112M and dominate the 9,000-ep learner | **measured** | [P24cal] C1 112.20M vs TRAINED 93.90M; [L24] frontier |
| 3 | EE headroom exists above the rules | **assumed** (unmeasured; ceiling pending) | physics argues only interference/coordination is left (B.2) |
| 4 | That headroom is reachable by a per-user policy on the 113-dim observation | **assumed, physics-contradicted** | A.2.7, B.2 |
| 5 | The ratio learner optimises pooled EE | **refuted for the argmax** | 0/240 flips [R]; own-bits congestion payoff (D.i) |
| 6 | Equal-share `E_u` gives a learnable energy signal | **refuted** | 1.6 % action contrast [D]; CF3REVIEW C1 [R] |
| 7 | Dinkelbach `η` updates steer the policy | **inferred inert** | D.ii |
| 8 | Static rule-pool replay accelerates or improves a dense-reward DQN | **assumed; literature-contrary** | E; DQfD RBS/HER [R] |
| 9 | Three sources are three distinct catfish | **partly measured against** | C1/C2 one rule at two thresholds; C2 states inside C1's [L24, R CFSCREEN §5] |
| 10 | A0 is a fair baseline | **measured (fair as algorithm), assumed (as environment)** | F |
| 11 | Beating A0 shows learning raises EE | **near-tautological** | A.2.5 |
| 12 | 1000 episodes is enough to see direction | **inferred** (vs A0 yes; vs rules no) | D.iii |
| 13 | The service floor prevents degeneracy | **measured non-binding**; throughput degeneracy unblocked | A.2.1–2 |
| 14 | Pinned archive + per-episode reseeding gives comparable, paired numbers | **measured** | placebo bit-identical 52,420,510.0956937; pairing 24/24 [V PROGRESS ≤148] |
| 15 | 3 seeds resolve differences of the expected size | **assumed; doubtful below ~5–10 %** | D.iii; [CAP] checkpoint swings [R] |
| 16 | Handover can be traded for EE (Amendment 2) | **measured: nothing to trade** | frontier flat m=2…6 dB [L24]; 0 J, 0 bits per handover [V] |
| 17 | Sources are representable by the Q-architecture | **measured, partly** | BC 0.84/0.94/0.71 top-1 [L24, R] |
| 18 | The MODQN paper's design (eq. 16, weights, γ) is faithfully reproduced | **relayed** | paper not read this session [R]; environment deviates by design [V] |

## H. Dead-end risks, cheapest settling measurement, kill condition (wall time on the 20-core server)

| risk | cheapest measurement | wall | kills the direction if |
|---|---|---|---|
| H1 No headroom above the rules | the running ceiling (constrained Dinkelbach coordinate ascent, 24 eval episodes, paired) | ~2 h on 4 processes (per its brief) | ≤ +3 % over `A m=2dB` (paired sem) |
| H2 Headroom exists but needs joint moves / realised information | nominal-information variant + unilateral best-response fixed point on the same episodes | +1 h | nominal-unilateral point ≈ rule while joint-realised ≫ rule → per-user learning cannot reach it |
| H3 Headroom is bought with throughput | report bits ratio and per-user rate distribution from the ceiling logs; rate-floor variant | minutes / +1 h | bits ratio < 0.9 or rate floor removes the gain |
| H4 The learner's effective objective is own-bits | on any A1 checkpoint: fraction of evaluation argmaxes that change when `η → 0`; and closed-loop EE of an explicit own-bits greedy rule `argmax (B_w/(load+1))·log2(1+γ)` on the 24 episodes | 10 min | < 1 % flips; own-bits rule EE < `A m=2dB` (this bounds A1's best case) |
| H5 Representation bound | BC probe of `A m=2dB` with a wider net (256,256) and with the 113-dim input | 20 min | top-1 stays ≤ 0.85 → any learner is capped at ~rule − 1–2 % |
| H6 Static pools are inert | the pilot itself (A2 vs A1 vs A3); if resolution is wanted, 5 seeds × {A1, A2, A3} × 1000 ep | ~1.5 h (15 runs, ~35 min each alone, 12-way ≈ 3×) | \|A2 − A1\| within seed SD → mechanism dropped |
| H7 Seeds cannot resolve the sizes at stake | compute the between-seed SD of final EE from the pilot's 3 seeds per arm | minutes | SD > 3 % → nothing under ~10 % is readable at n = 3 |
| H8 Churn realism | re-score the eval logs with a 0.142 s interruption per inter-satellite handover | minutes | never (≤ 0.5 % of bits); a referee item, not a kill |

## I. Verdict and the better-posed problem

**Verdict: DEAD-PATH as framed.** The framing "a per-user Q-learner, seeded by rule-generated replay, raises pooled EE on this physics" fails on three independent grounds: the endpoint is nearly maximised per user by a one-line rule (A, B); the learner's effective objective is own bits, not the ratio, and its energy credit cannot act (D); the replay mechanism belongs to sparse-reward exploration and is in the configuration its own source literature reports as worst (E). The pending ceiling can only tell us whether *some* coordinated policy has room; it cannot rescue this learner. The owner's gate (beat A0) is likely reachable and would establish "MODQN's reward is misaligned with EE here" — worth reporting, not a learning result.

**The honest paper available today:** "A hysteresis rule (hold unless the best beam's nominal gain exceeds the incumbent's by 2–6 dB) beats the published MODQN scalarisation by ~20 % pooled EE on a geometry-resolved multi-beam LEO physics with a consumed-power model, at ~1 inter-satellite handover per user-minute, because MODQN's handover and load terms price events that cost no energy and push users off their highest-gain beams." Plus the diagnostics (frontier, BC representability, power accounting, cap decomposition). Say plainly that this is the result.

**Better-posed problem (if learning is to have a job):**
- *Objective.* Keep pooled EE but add a per-user rate floor (or minimise consumed joules subject to per-user rate ≥ R_min at full service). Because power is a per-beam constant, this becomes "serve everyone at ≥ R_min with the fewest, best-placed lit beams" — a combinatorial coordination problem where greedy rules can provably underperform and where the throughput degeneracy is closed. Alternatively a demand-driven (non-full-buffer) numerator with queues, which gives the horizon real content.
- *Action space.* Add the levers the physics has and the contract hides: beam lighting/sleep decisions (or a per-satellite beam-plan) and per-beam power control (`P_DC ∝ √p` with `ξ_max` at saturation is a genuine EE trade the recurrence currently fixes). Without at least one of these, the action space is "which of 28 beams", and the rule owns it.
- *Credit.* If a per-user learner is kept, replace equal-share energy with a **difference reward** computed by the environment's own counterfactual evaluator: `D_u = F(a) − F(a_{−u}, a_u^{ref})` with `F = bits − η·joules` at the step (`evaluate_actions` with common random numbers is already there, `step.py:643-723`), charged with an explicit outage term. This is the principled version of queue item Q4 and the only credit under which `η` is not decorative.
- *Horizon.* With free handovers the problem is myopic; either model interruption/signalling costs realistically (0.062/0.142 s buys ≤ 0.5 % — too small to matter) or accept that the horizon is 1 and drop the multi-step apparatus.
- *Baselines.* `A m=2dB`, `MAX_NOMINAL_GAIN`, the centralised Dinkelbach search (upper reference), and MODQN — all in the main table with throughput and handover columns.
- *When RL is necessary at all.* Only if the measured gap between the best rule and the coordinated ceiling is ≥ 10 % **and** a deployable coordinated policy (centralised at the gateway, or CTDE with a joint critic) is admissible. Otherwise a rule with two parameters is the method.

## J. The queued work (HANDOFF §6b)

| item | verdict | condition |
|---|---|---|
| Q1 ceiling | **yes** (running) | add throughput reporting, the nominal-information/unilateral split and a rate-floor variant (C) |
| Q4 outage-charged energy credit | **conditional** | only if Q1 shows ≥ +10 % reachable at the nominal-information unilateral point; then implement it as a difference reward via `evaluate_actions` (I), and screen it with a zero-training argmax-flip probe (H4) before any training |
| Q5 full-length runs with drop-one arms | **no** | attributing a mechanism the physics and literature say is inert; even a positive pilot branch (A2 > A1, A2 > A3) is a coverage effect at 3 seeds, and full length cannot create headroom that Q1 does not show |
| Q6 demonstration-utilisation arms (faithful catfish, DQfD margin, bounded ACRM, JSRL) | **no** as EE-raising mechanisms | a margin loss toward `A m=2dB` clones a rule at −1.3 % EE; JSRL/CER address exploration this problem does not have; reconsider only as a sample-efficiency study after a learner with a real job exists (Q1 + Q4 conditions) |
| Q7 engineering speed-ups | **no** unless Q5 runs | mathematically fine (shared target forwards), but there is nothing to speed up |
| Q8 housekeeping | yes | unrelated to validity |

**Sources consulted on the web this session** (abstracts only): [Sun et al. 2024, IEEE Commun. Lett. (via search)](https://arxiv.org/abs/2605.02416v1), [Competitive Experience Replay (Liu et al., ICLR 2019)](https://arxiv.org/abs/1902.00528), [Jump-Start RL (Uchendu et al., ICML 2023)](https://proceedings.mlr.press/v202/uchendu23a/uchendu23a.pdf), [Fractional DRL for Age-Minimal MEC](https://arxiv.org/html/2312.10418), [Asynchronous Fractional Multi-Agent DRL](https://arxiv.org/html/2409.16832v1), [Dynamic Experience Replay](https://arxiv.org/pdf/2003.02372), [Revisiting Fundamentals of Experience Replay (Fedus et al. 2020)](https://proceedings.mlr.press/v119/fedus20a/fedus20a.pdf). DQfD/R2D3/DDPGfD/Nair facts are relayed from `.scratch/dqfd-grounding/DQFD-FAMILY-GROUNDING-2026-09-11.md`.

---
---

# K. Phase 2a — the pilot result (written after unblinding, 2026-09-11 12:55 UTC)

**Verdict unchanged — DEAD-PATH as framed: the pilot confirms the physics reading (joules per beam-step are 189–191 J for all twelve runs; every EE difference is bits per lit beam), every learned arm sits 5–8 % below `A m=2dB` on the same calibration episodes, the directed-vs-random pool contrast is null (A2 − A3 = +0.78 %, t ≈ 0.8, one deciding seed pair won by 0.05 M, time-averaged learning curves identical), and the only resolved effect — A1 beats A0 by +17 % — is the objective change plus a late decline of A0, exactly the near-tautology predicted in A.2.5.**

Unblinded source: `.scratch/cf3-pilot/CF3-PILOT-2026-09-11.md` only (tables generated from JSON; provenance checks reported passed [R]). New condition group **[P24eval]**: as [P24cal] but on the 24 **evaluation** episodes (env `9_111_000+i` / mobility `9_112_000+i`), final checkpoint `policy-ep01000.pt`, tree `f297334e`. The learning-speed readings (episodes 100/250/500/750/1000) are on the **calibration** episodes and are therefore in [P24cal], the same set as the premeasure rules — the only place pilot arms and rules meet on one episode set. Nothing below compares [P24eval] with [P24cal].

### K.1 Does the verdict or any claims-table row change?

The verdict does not change. Rows of table G that move from assumed/inferred to measured:

| row | before | after the pilot |
|---|---|---|
| 1 (EE = bits per lit beam; power per beam constant) | derived | **measured on the learned arms**: J per beam-step 189.4–191.3 for all 12 runs (6.30–6.36 W/beam) [P24eval, D]; bits per beam-step A0 1.48–1.69e10 < A1 1.84–1.92e10 < A3 1.93–1.95e10 ≈ A2 1.92–1.98e10 [D] |
| 2 (rules dominate the learners) | measured on the 9,000-ep checkpoint | **measured on the 1000-ep learners, same episode set**: calibration@1000 A1 102.90 / A2 106.22 / A3 105.35 vs `A m=2dB` 112.20, `MAX_NOMINAL_GAIN` 110.51, `B1` 104.19, TRAINED-9000 93.90 [P24cal] — all learned arms −5.3 … −8.3 % vs the best rule, ≈ B1 |
| 8 (static pools help a dense-reward DQN) | assumed, literature-contrary | **pools of any kind: marginal +2.6…+3.4 % at the final checkpoint** (A2 − A1 +3.39 M, Welch t 2.3, df 4; A3 − A1 +2.61 M, t 2.3) [P24eval, D]; **directed vs random: null** (A2 − A3 +0.78 M, t 0.8) [D]; **AUC/900 identical** (A1 102.89, A2 102.81, A3 103.15 [P24cal]) |
| 11 (gate near-tautological) | inferred | **measured**: A1 > A0 on 3/3 seeds, +17.1 % [P24eval]; A1 above A0 at every reading 100–1000 on calibration (+26 %, +7 %, +10 %, +13 %, +19 %) [P24cal, D] |
| 12 (1000 episodes shows direction vs A0, not vs rules) | inferred | **measured** as stated |
| 13 (service floor non-binding) | measured | re-confirmed: served 0.9969–0.9998 in all 12 runs; A3's C-S CI [−0.143, −0.061] pp is statistically *below* A1 yet passes at −0.5 pp — the floor cannot discriminate anything a learner does |
| 15 (3 seeds resolve the sizes at stake) | assumed | **measured**: between-seed SD A1 1.9 %, A2 1.6 %, A3 0.4 %, A0 6.6 % [P24eval, D]; within-run checkpoint swings 3–5 M (A1) and 4–19 M (A0) across the 250–1000 readings [P24cal, D] — differences under ~3–5 % are unreadable at n = 3, final-checkpoint-only |
| 16 (nothing to trade on handover) | measured on rules | **measured on learners**: A1–A3 re-anchor at 0.47–0.58 inter-satellite/user-step and still sit below the rules (K.5) |
| 5/6/7 (own-bits learner; energy credit inert; η inert) | refuted/inferred | unchanged; `λ* = 0` for all nine seeds; η moved 110.5 → 100.5–107.2 with no observable consequence [R]; the η→0 argmax-flip probe on the final checkpoints (H4) is still the cheapest confirmation |
| 3/4 (headroom above rules; reachable per user) | assumed | unchanged — the ceiling (phase 2b) decides the first; the pilot adds evidence against the second: the learners converge to a worse copy of the max-gain rule (same beams 62–67, same churn, 8–12 % fewer bits per beam) |

### K.2 Branch 1: signal or noise?

Formally the declared rule fires: A2 > A1 on 2/3 same-index pairs (−0.02, +5.15, +5.04 M) and A2 > A3 on 2/3 (−0.62, +2.92, **+0.05** M), C-S non-inferior [P24eval, R]. Substantively it is noise, on four independent readings [D]:
1. **A2 − A3 = +0.78 M (+0.77 %)**, Welch t = 0.8, smaller than every per-episode sem in the table (1.25–1.62 M) and than the between-seed SD of A1/A2 (1.7–1.9 M); one of the two "wins" is 0.05 M.
2. **The time-averaged learning curves are identical**: AUC/900 on calibration A1 102.89, A2 102.81, A3 103.15 [P24cal]. The controller's own forecast said a catfish effect would show first in learning speed; it shows nowhere — at episode 100 A2 (95.5) and A3 (92.0) are *below* A1 (96.5).
3. The final-checkpoint advantage of A2/A3 over A1 (+3 %) appears only at the 750/1000 readings and is the size of one within-run checkpoint swing (A1 seed 0: 107.4 → 102.7 → 104.8 across 500/750/1000).
4. Under the declaration's own reading table, "A2 ≈ A3 > A1" is **branch 2 — extra experience, not the demonstrators** — and under the evaluation contract's rule 2, an effect that survives replacing the specialist with noise "is the perturbation, not the demonstration, and must not be called catfish".

**What A3 > A1 on 3/3 seeds implies for the mechanism.** Random-legal pools (trajectories at 52 M bit/J, 88 % of whose actions the learner would never take once ε = 0.01) raised the final reading by +2.6 % (marginal). The plausible channel is coverage of poor actions: after episode 222 the on-policy replay contains almost no low-value actions, so TD has nothing grounding `Q_B` on them and the argmax can drift to over-estimated unvisited actions; 15 off-policy rows per batch pin those values down. That is a regulariser on the bits head — a known DQN dataset-coverage effect [I] — and it does not depend on the demonstrator's quality (A2 ≈ A3). It is not evidence about energy (`Q_E` cannot act), about consolidation (`B1`'s pool did not move beams: A2 66.4 vs A1 64.1), or about any of the five RIS-catfish mechanisms. If the owner wants this effect at all it is a one-line engineering note ("keep a small random off-policy prefill in replay"), and even that needs ≥ 5 seeds to resolve at the ±3 % level.

### K.3 A1 vs A0: size, and what carries it

- **Size.** Final checkpoint [P24eval]: A1 98.64 vs A0 84.21 M, +17.1 %, 3/3 seeds (pairs +12.0, +12.5, +18.8 M). On calibration [P24cal] the gap is +26 % at episode 100, **+7 % at 250, +10 % at 500**, +13 % at 750, +19 % at 1000.
- **A0's trajectory**: calibration means 76.5 → 95.1 → 95.6 → 91.8 → 86.4 across 100/250/500/750/1000; seed 2 falls 92.6 → 78.5 between 750 and 1000; H_inter drifts up from 0.16 to ~0.20 [R]. A0 peaks at 250–500 and declines as ε reaches its floor (episode 222) — i.e. **as A0 becomes greedy on its own objective, its EE falls**. That is the misalignment acting, not noise: the r2/r3 terms (61 % of the r1 term's magnitude, A.2.5) are being optimised at the expense of EE. The decline is amplified by eq.(16)'s instability (per-head max with three separate networks; between-seed SD 6.6 %, within-run swing up to 19 M).
- **Under-training?** A0 at 1000 episodes (86.4 M, calibration) is 8 % below the 9,000-episode frozen MODQN (93.90 M, same calibration set [P24cal]) — so yes, A0 at 1000 is short of its own asymptote. But A1 at 1000 (102.9 M, same set) is **+9.6 % above the 9,000-episode MODQN**. The cleanest same-episode-set statement the pilot supports is: **A1(1000 ep) 102.9 > MODQN(9,000 ep) 93.9 > A0(1000 ep) 86.4 M bit/J** — the objective change beats even the fully trained baseline, and the 1000-episode baseline adds a late decline.
- **Decomposition.** Misalignment ≈ the +7…+10 % seen at A0's best readings and vs the 9,000-ep run; A0's late decline/instability adds the rest of the +17 % at the final checkpoint. Neither part is a learning contribution.
- **The owner's gate.** Met, robustly in sign (every seed, every reading). The headline +17 % overstates it; the defensible number is +9–10 % (vs A0's best reading, or vs the 9,000-episode MODQN on the same episodes), and the honest label is "MODQN's r2/r3 scalarisation costs ~10 % pooled EE on this physics; removing it recovers it". A referee will ask why A0 was read at a declining final checkpoint and will want A0 at its best reading and at 9,000 episodes beside it.

### K.4 Where the learned arms sit relative to the rules (same calibration episodes, [P24cal]) and the per-beam decomposition

| arm (calibration @1000, seed mean) | pooled EE (M) | vs `A m=2dB` 112.20 | vs `MAX_NOMINAL_GAIN` 110.51 | vs `B1` 104.19 | vs TRAINED-9000 93.90 |
|---|---:|---:|---:|---:|---:|
| A0 | 86.37 | −23.0 % | −21.8 % | −17.1 % | −8.0 % |
| A1 | 102.90 | −8.3 % | −6.9 % | −1.2 % | +9.6 % |
| A2 | 106.22 | −5.3 % | −3.9 % | +2.0 % | +13.1 % |
| A3 | 105.35 | −6.1 % | −4.7 % | +1.1 % | +12.2 % |

Per-beam decomposition on the evaluation episodes [P24eval, D] (240 steps): J per beam-step **189.4–191.3 for all 12 runs**; bits per beam-step A0 1.478–1.689e10, A1 1.842–1.919e10, A2 1.915–1.982e10, A3 1.926–1.946e10; lit beams A0 50.5–70.2 (unstable), A1 62.2–65.6, A2 65.5–67.1, A3 62.9–64.3. For the pattern only (different episode set), the [P24cal] rules were: `A m=2dB` 2.147e10 bits/beam-step at 63.0 beams, `MAX_NOMINAL_GAIN` 2.116e10 at 63.0, `B1` 2.011e10 at 38.6, TRAINED-9000 1.762e10 at 66.6.

**This matches the blind physics reading exactly**: (i) power per lit beam is policy-invariant to ±0.5 %; (ii) the learners light the same number of beams as the max-gain rule (62–67) and churn like it (K.5), i.e. they converge to an imperfect max-gain rule; (iii) their shortfall is entirely bits per lit beam — 8–12 % fewer than `A m=2dB` — of which the representability probe accounts for ~1–2 % and the own-bits/under-optimisation residue for the rest; (iv) the pools did not move the beam count (no consolidation was learned from `B1`'s pool), only the per-beam SE by ~3 %, consistent with a regularisation effect on `Q_B` (K.2); (v) A0's collapse mode is visible in the same decomposition: seed 0 lit only 50.5 beams with 1.69e10 bits/beam (packing users, halving service per user — the throughput degeneracy of A.2.2, invisible to the endpoint), seed 2 lit 68 beams at 1.48e10 (spreading onto poor beams).

### K.5 Handover

A1–A3 run at H_inter 0.47–0.58 per user-step (1.02–1.19 per user-minute), A0 at 0.18–0.20 (0.37–0.42/min) [P24eval, R]. This is exactly A.2.3: with handovers costing 0 J and 0 bits and `p·G^T` invariant inside a segment, the own-bits learner re-anchors whenever a higher-gain beam appears; it lands at the rules' churn (`A m=2dB` 0.55, `MAX_NOMINAL_GAIN` 0.65 on calibration [P24cal]) — and still below their EE. Every A1–A3 seed sits within 0.02–0.13 of the former C-H bound 0.6016 at λ = 0, so `λ* = 0` for all nine and the C2 head could never have acted [R]. Referee implications: the EE gain over MODQN coincides with **2.7× the inter-satellite handover rate** (≈1.1/min, at the top of the published operating points, ≈1.0/min and a 1.2/min budget [R DR-14/16]); the reviewer will demand an interruption/signalling cost model (the 0.142 s per event sensitivity is ≤ 0.5 % of bits [R erratum 25], but signalling energy is unmodelled) and will read "churn is free" as a modelling omission that inflates every EE number in the table by an unknown amount, rules included.

### K.6 Recommendation to the owner（繁體中文，≤ 10 行）

1. **Q5（全長訓練＋drop-one）不要跑。** A2 對 A3 只有 +0.78%（一個 seed pair 以 0.05M 決勝），AUC 三臂完全相同；drop-one 會去拆解一個還沒和「隨機池」分開的機制，而且全長訓練造不出規則之上的空間——三個學習臂在同一組校準集都低於 `A m=2dB` 5–8%。
2. 宣告上的 branch 1 是規則形式上成立，實質是 branch 2（額外經驗，非示範）；報告要照 evaluation contract rule 2 寫成「perturbation 效應，不得稱 catfish」。
3. 這次 pilot 真正解析出的只有一件事：**A1(1000 集) 102.9 > MODQN(9000 集) 93.9 > A0(1000 集) 86.4 M bit/J（同一校準集）**——MODQN 的 r2/r3 獎勵在這套物理上約損失 10% EE；+17% 的頭條有一半是 A0 在 250 集後自己衰退（seed 2 從 92.6 掉到 78.5）。門檻算過了，但那是對 baseline 獎勵的診斷，不是學習貢獻。
4. 每束功率 189–191 J/beam-step 十二個 run 全部相同；學習臂點的波束數、換手率都跟 max-gain 規則一樣，只是每束少 8–12% 的位元——它們學成了一個較差的一行規則。
5. 等天花板（phase 2b），並要求它回報每人吞吐量與 nominal-information/unilateral 拆解；≤ +3% 就收線寫規則論文；≥ +10% 且 per-user 資訊可達，才重做 credit（difference reward）與動作空間，再談訓練。
6. 若要留一個便宜的後續：在現有 A1–A3 final checkpoints 上做 η→0 的 argmax-flip 探針（幾分鐘），把「能量頭不起作用」從推論變成量測；以及只有在 owner 想發表「隨機 off-policy prefill 讓 DQN 多 3%」這條工程附註時，才補 5 seeds 的 A1 vs A3。
7. 論文主體：一行遲滯規則 + 規則前緣 + MODQN 獎勵錯位的診斷 + 換手成本的敏感度；把 `A m=2dB`、MNG、天花板放進主表，A0 同時給最佳讀數與 9000 集版本。
