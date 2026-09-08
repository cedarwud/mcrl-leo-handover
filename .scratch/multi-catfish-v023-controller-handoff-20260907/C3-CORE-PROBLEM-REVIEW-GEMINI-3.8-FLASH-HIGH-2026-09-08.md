### 1. Domain Truth
"Load balancing improves EE" is strictly **REGIME_CONDITIONAL**, never an unconditional domain truth ([DOC 02:§1]). It improves pooled EE ($\sum \text{bits}/\sum \text{joules}$) only when: (1) PA power scales super-linearly with load; (2) co-channel interference heavily dominates; or (3) rate-target power inversion steeply penalizes bandwidth congestion ($P \propto 2^{R/B}-1$) ([DOC 02:§3, DOC 11:H10]). In multi-beam LEO payloads with high static overhead ($P_{\text{cir}}=0.338\text{ W/beam}, P_{\text{BB}}=0.200\text{ W/sat}$), sub-linear PA efficiency ($\propto \sqrt{p}$), and beam-max RF power ($p_{s,v}=\max_u p_{u,s,v}$) ([DOC 02:§2]), dispersing load ignites new beams, causing **beam activation expansion** (+0.338 W each) with zero RF savings ([DOC 01:Row 4, DOC 02:§2]). In this regime, **beam consolidation** (packing users to extinguish beams) dominates balancing ([DOC 01:Row 6, DOC 02:§3]). The old simulator had fixed RF caps and segment-anchored power ([DOC 11:H01, H02]), penalizing load dispersion. The successor replaces this with memoryless angle-aware rate-target power control and TDM bandwidth slicing, where required power grows convexly as user bandwidth shrinks, restoring a physical load-to-power lever ([DOC 00, DOC 11:H01]).

### 2. Root-Cause Ranking
**Ranked Hypotheses:**
1. *No load $\to$ energy lever in old physics* ([DOC 02:§2]): Beam-max power and $\sqrt{p}$ PA curves meant rebalancing never saved transmitter energy.
2. *Balancing vs. consolidation mis-framing* ([DOC 01:Row 6, DOC 02:§3]): True satellite EE requires extinguishing beams; dispersing load activated extra beams (+0.338 W).
3. *Additive per-user heads cannot represent all-or-nothing beam savings* ([DOC 01:§3.2, DOC 02:§5, DOC 11:H19]): Coordinated beam extinction is non-additive; independent argmax causes destructive herding (60/60 unilateral positive, 28 joint reversed).
4. *Deployable information barrier (Missed)*: Oracle ZR worked (+0.985%) only via unobservable realized fading; deployable EXPECTED_ZR failed ([DOC 01:Rows 14–15]).
5. *Executed C3 targets $\neq$ declared targets* ([DOC 01:§3.1, §3.3]): Evaluated as single-user counterfactuals but composed via unweighted $\kappa$-normalized sums.
6. *Strong BASE absorbs gains* ([DOC 02:§7]): Q1/Q2 captures first-order link budget and service risk, leaving razor-thin margins easily erased by coordination noise.
7. *Training-stack & physics defects* ([DOC 11:H01, H10, H13]): Disconnected bootstrap (H13), Shannon ACM fantasy (H10), and anchor renewal artifacts (H01).
8. *Evaluation insensitivity* ([DOC 11:H22]): Ratio-of-sums pooled metrics masking individual world reversals.
**Necessary parts**: Hypotheses 1, 2, and 3 are jointly **necessary and sufficient**: even perfect exact oracles produced negative C3 marginals across all demand regimes ([DOC 03:G0–G3]).

### 3. Concept-Right-Code-Wrong
To definitively isolate conceptual viability from implementation bugs, four differential tests are required:
1. *Clean-Physics Oracle Replay*: Evaluate oracle marginals on a memoryless physics simulator to eliminate segment-anchored renewal artifacts (H01) and max-vs-wanted power inconsistencies (H02) ([DOC 11:H01, H02]).
2. *Combinatorial Joint vs. Additive Argmax Oracle (E1 Existence Diagnostic)*: Compare optimal set-level beam evacuation ($J_1$) against additive per-user argmax $\arg\max_u [Q_1+Q_2+z_3/\kappa]$ using identical ground-truth utilities ([DOC 02:§8–9, DOC 11:H19]).
3. *Direct Joint Value Replay*: Execute joint decisions picked directly by true system surplus $G(c) - G(b)$ without decomposing into per-user $z_{3,u}$ shares or applying $\kappa$-scaling ([DOC 01:§3, DOC 11:H11, H12]).
4. *Target & Bootstrap Unit Tests*: Verify TD target consistency between joint policy rollout and bootstrap evaluation (H13) ([DOC 11:H13]).
**Single most diagnostic test**: *The Joint-vs-Additive Combinatorial Oracle Gap Test* ($J_1$ search vs. additive argmax, [DOC 02:§9, DOC 11:H19]). If combinatorial set search finds positive pooled EE headroom while additive argmax fails on identical states, it proves the coordination concept is sound but the additive per-user interface/code is fatally flawed.

### 4. Design of a C3 Under Successor Physics
**Best Prior Component**: A *Two-Stage Set-Level Beam-Activation & Clustering Coordinator* ([DOC 02:§8, DOC 11:H19]). Under rate-target power control ($P \sim 2^{R/(B/n)}-1$) and switchable beams, joint power is highly non-convex. The coordinator acts at the topology level, selecting active beam subsets and assigning user clusters to prevent bandwidth starvation while extinguishing unnecessary RF chains.
**Objective**: Maximize pooled EE: $\sum_u R_u / \sum_b (P_{\text{RF},b} + P_{\text{cir}}\mathbb{I}_{b \in \mathcal{B}_{\text{on}}} + P_{\text{BB}}\mathbb{I}_{s \in \mathcal{S}_{\text{on}}})$ subject to user rate requirements ($R_u \ge R_{\text{req}}$) and service non-inferiority ([DOC 02:§1, DOC 11:H17]).
**Comparator**: A deployable, model-based nominal-physics greedy decoder / Dinkelbach heuristic operating on identical CSI ([DOC 02:§8, DOC 11:H19]).
**What Learned C3 Adds Beyond Nominal Decoder**:
1. *Search Pruning under Real-Time Deadlines*: Learns policy priors/GNN scores to prune the $O(2^B \cdot S^U)$ combinatorial joint search down to millisecond inference, solving the execution deadline bottleneck ([DOC 11:H25]).
2. *Multi-Step Trajectory Value*: Learns lookahead value for orbital drift and handover churn over the 30.08 s interval ([DOC 11:H04, H23]), which memoryless instantaneous physics decoders cannot price.

### 5. What is Still Unexamined
Three critical unexamined elements in the files that could overturn conclusions:
1. *Discrete ACM Threshold Cliffs vs. Continuous Shannon SE (H10)* ([DOC 11:H10]): Simulations used unbounded continuous Shannon rates. Real DVB-S2X uses discrete MODCOD thresholds and SE caps. Load balancing that slightly degrades SINR may drop users below a decoding cliff (zero bits) or produce zero gain if already capped at maximum MODCOD, fundamentally altering EE trade-offs.
2. *Non-Radiation of Failed Links Hiding Failure Energy (H03)* ([DOC 11:H03]): Under `service.py:185` and `step.py:822`, dropped links disappeared before transmission without consuming scheduled radiation energy. In real payloads, failed attempts radiate power. This artificial energy subsidy directly skews candidate evaluations and masks true failure costs.
3. *Dwell / Residence Latch Leakage (H05)* ([DOC 11:H05]): $N=4$ dwell (120.32 s) was specified to freeze cell anchors, but code permitted switching every step due to an obsolete 1 s check. It is unknown whether BASE achieved high EE via rapid, physically inadmissible ping-pong handovers, or whether C3 was unfairly penalized by boundary rekeying.

### 6. Process Improvements
To eliminate the pattern of "known early, found late", institutionalize these five standing checks in chronological order:
1. *Known-Answer Physical Benchmark Suites*: Unit tests on minimal analytic topologies (e.g., 2-user 2-beam consolidation) verifying exact energy formulas before any RL runs ([DOC 11:H01, H02, H24]).
2. *Assumption Register Sign-off Gate*: Formal sign-off on domain simplifications (H01–H25); any unphysical shortcut (e.g., segment-anchored power) blocks training authorization ([DOC 11:Section 1]).
3. *Factorial & Placebo Null Arms*: Mandatory random-head and zero-weight placebos alongside candidate heads to catch uninformative representations early ([DOC 01:Row 17, DOC 11:H21]).
4. *Independent Recomputation Pipelines*: Decouple evaluation verifiers from experiment runner trees, preventing verification bugs from suppressing diagnostic data for 22+ hours ([DOC 01:Row 17, DOC 11:H24]).
5. *Reviewer Rotation & Red-Team Cadence*: Formal red-team escalation triggered automatically whenever $N \ge 3$ consecutive iterations of a target family fail, challenging framing before weeks are burned ([DOC 01:Table 1]).

LOAD_BALANCE_EE=REGIME_CONDITIONAL | CORE=no_load_to_energy_lever,balancing_vs_consolidation_misframing,additive_per_user_heads | MOST_DIAGNOSTIC_TEST=Joint_vs_Additive_Combinatorial_Oracle_Gap | BEST_C3_PRIOR=Two_Stage_Set_Level_Beam_Activation_Planner
