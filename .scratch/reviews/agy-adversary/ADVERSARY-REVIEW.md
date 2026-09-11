**Verdict: Reject — The proposed narrative is constructed on post-hoc circular outcome-fitting and misrepresents learner-free static diagnostic constructions (a hand-crafted 8-beam minimum set cover and an unlearned RSS heuristic) as learned "routes" on a Pareto frontier, while the project's own empirical evidence demonstrates that the learned routes fail their necessity condition, compete destructively, and optimize a surrogate objective that actively penalizes system energy efficiency.**

---

# ADVERSARY PEER REVIEW: MULTI-ROUTE MCRL FOR LEO SATELLITE HANDOVER & BEAM ASSIGNMENT

**Reviewer:** Hostile but Fair Independent Reviewer  
**Evidence Boundary:** `./evidence/` snapshot (`reports/`, `declarations/`, `code/`)  
**Operational Rule:** Zero additional experiments executed; evaluation strictly based on recorded empirical receipts, sealed contracts, and physics code.

---

## 1. Executive Summary & Overview of the Attack

The manuscript proposes an agentic reinforcement learning architecture ("Multi-Catfish MCRL") for handover and beam assignment in multi-beam Low Earth Orbit (LEO) satellite constellations. The core claim is that global system energy efficiency ($\eta^N = \mathcal{B} / \mathcal{E}$, pooled decoded bits over pooled payload joules) can be decomposed into three distinct learned routes ("Catfish"):
1. A **bits side** route optimizing per-user link quality;
2. An **energy side** route optimizing beam concentration / active beam reduction;
3. A **time side** route optimizing persistence / avoiding handover interruption.

The authors impose an explicit **necessity condition**: each route on its own must improve energy efficiency (EE) under a service guard, or else it is not a meaningful component. Recognizing that these objectives conflict, the authors frame the combination of routes as navigating a fundamental **Pareto trade-off between EE and service quality** (served users and rate-target attainment), offering as proof a purported Pareto pair: a configuration at $46.11\text{ Mbit/J}$ with $2.5\%$ rate-target attainment versus another at $41.62\text{ Mbit/J}$ with $24.75\%$ attainment. Finally, the authors claim that a **ratio-consistent (Dinkelbach-style) combination rule** is required because empirical evidence proves no single linear exchange rate can order configurations by EE.

This review attacks this narrative on every foundational premise. Based strictly on the project's own sealed declarations and empirical evidence, I demonstrate:

1. **Fictitious Pareto Attribution (The Central Deception):** The offered $46.11\text{ Mbit/J}$ vs. $41.62\text{ Mbit/J}$ Pareto pair was **not produced by learned routes**. The $46.11\text{ Mbit/J}$ point is a learner-free, hand-crafted combinatorial minimum set cover from a diagnostic script ([`CROWDCOST`](evidence/reports/CROWDING-COST-2026-09-10.md)); the $41.62\text{ Mbit/J}$ point is the classical, unlearned static heuristic `RSS_MAX` ([`STATIC-BASELINE-FAMILY-CLEANPATH`](evidence/reports/STATIC-BASELINE-FAMILY-CLEANPATH-2026-09-10.md)). Not only are these learner-free heuristics, but the project's own diagnostics prove that the learned networks **structurally cannot even represent** `RSS_MAX` ([`APPROACHING-THE-INSTRUMENTS`](evidence/reports/APPROACHING-THE-INSTRUMENTS-2026-09-10.md)). Passing these off as evidence of learned routes reaching non-dominated frontiers is scientifically unacceptable.
2. **Failure of the Necessity Condition:** The evidence conclusively shows that neither Route 2 nor Route 3 satisfies the necessity condition. In the project's primary five-arm evaluations ([`Z-VIEW-SCORING`](evidence/reports/Z-VIEW-SCORING-2026-09-10.md)), **dropping Route 3 (C3) consistently *increases* system EE across all 16 seeds** (by $+10.04\text{ Mbit/J}$ in Q1 v1, $+1.20\text{ Mbit/J}$ in Q1 v2, and $+2.25\text{ Mbit/J}$ in z-view). Route 3 actively harms system EE. In Q1 v2, dropping Route 2 (C2) also increases system EE across 15 of 16 seeds. In learner-free oracle testing ([`C2-TARGET-VALUE`](evidence/reports/C2-TARGET-VALUE-2026-09-10.md)), a perfect oracle C2 produces a negligible $+0.68\%$ gain that collapses to $0.00\%$ under the sealed tie-break rule. Route 2 and Route 3 do not raise EE; they fail the authors' own gate.
3. **Circularity & Retrospective Outcome-Fitting:** The re-interpretation of the interaction route as an "energy side" route is a post-hoc rationalization. The sealed authoring contract ([`MULTI-CATFISH-MCRL-V03-PAPER-AUTHORING-CONTRACT`](evidence/declarations/MULTI-CATFISH-MCRL-V03-PAPER-AUTHORING-CONTRACT-2026-08-31.md)) defined C1, C2, and C3 as temporal and spatial counterfactual decompositions (focal opening, focal next-slot, non-focal opening externality), expressly forbidding numerical improvement claims. When C3 failed as an interaction coordinator, the proposers seized upon an unrelated diagnostic finding showing that packing users into 8 beams yields high EE, and retroactively rebranded C3 as an "energy-side concentration" route.
4. **The Single-Judge Absurdity:** The paper defines pooled EE ($\eta^N$) as the single primary optimization criterion. When combining routes results in an arm (`FULL`) that is strictly worse in EE than its constituent ablation (`DROP_C3` or `DROP_C2`), this is an optimization failure, not a "trade-off." In Q1 v2, `DROP_C2` strictly dominates `FULL` on EE ($43.41$ vs. $42.26\text{ Mbit/J}$), served users ($31,965$ vs. $31,962$), and target attainment ($27.47\%$ vs. $27.20\%$).
5. **Dinkelbach as a Non-Sequitur:** While [`ETA-EXCHANGE-RATE`](evidence/reports/ETA-EXCHANGE-RATE-2026-09-10.md) proves that no single linear exchange rate orders configurations by EE, Dinkelbach iteration converges in a single step to $\eta^* = 41.62\text{ Mbit/J}$ (`RSS_MAX`). Crucially, at that exact fixed point, first-improvement search **still descends away from `RSS_MAX` and EE still falls at 9 of 12 anchors**. The failure is caused by an insurmountable **selection horizon mismatch** and spatial heterogeneity, which a Dinkelbach combination rule does not fix.
6. **Fatal Baseline Disconnect:** The baseline MODQN uses $r_3 = -U_{b_u}$ (a load-balancing / spreading term). The project's own physics measurements ([`CROWDING-COST`](evidence/reports/CROWDING-COST-2026-09-10.md)) prove that spreading users across beams monotonically and catastrophically destroys EE ($d(\text{EE})/d(\text{active}) = -425,009\text{ bit/J}$ per added beam). Thus, the baseline's load-balancing objective is in direct physical opposition to system EE. Furthermore, [`BASELINE-MODQN-REFERENCE`](evidence/reports/BASELINE-MODQN-REFERENCE-2026-09-10.md) reveals that **no runnable external MODQN baseline exists on the V0.25 physics path**; the project substituted a static heuristic carrier proposal (`carrier_base`) and labelled it `BASELINE`.
7. **Pervasive Methodological Contamination:** $100\%$ of the scoring panel anchors in [`Z-VIEW-SCORING`](evidence/reports/Z-VIEW-SCORING-2026-09-10.md) overlap identically with the training anchors ([`CONVERGED-EXACT-SCORING`](evidence/reports/CONVERGED-EXACT-SCORING-2026-09-11.md)). There is zero out-of-sample evidence supporting the proposed architecture.

---

## 2. Forensic Deconstruction of the Offered Pareto Pair ($46.11$ vs. $41.62\text{ Mbit/J}$)

The proposers offer the following concrete evidence for their multi-route Pareto trade-off:
> *"an energy-side configuration at 46.11 Mbit/J with 2.5% rate-target attainment versus a link-side configuration at 41.62 Mbit/J with 24.75% attainment, both serving all users — a non-dominated pair."*

This claim is the central pillar of the narrative. It collapses completely under forensic examination of the evidence bundle.

### 2.1 The True Provenance of the Numbers

* **The $46.11\text{ Mbit/J}$ point:**
  - **Evidence:** [`CROWDING-COST-2026-09-10.md`](evidence/reports/CROWDING-COST-2026-09-10.md:7) and [`BEAM-CAPACITY-REALISM-2026-09-10.md`](evidence/reports/BEAM-CAPACITY-REALISM-2026-09-10.md:14,108-122).
  - **Classification:** `[ESTABLISHED: LEARNER-FREE DIAGNOSTIC]`.
  - **Reality:** This configuration was generated by `run_crowding_cost.py` using an **unlearned combinatorial construction**: it computed an exact minimum legal-beam set cover (exactly 8 beams at every anchor) and packed all 100 users into those 8 beams (mean occupancy $12.5\text{ users/beam}$). As verified in [`BEAM-CAPACITY-REALISM`](evidence/reports/BEAM-CAPACITY-REALISM-2026-09-10.md:118), its rate-target attainment is exactly $30 / 1,200 = 2.500\%$, and its EE is $46.110374\text{ Mbit/J}$.
  - **Connection to Learned Routes:** **Zero.** No neural network, no Q-learning head, and no Catfish route produced this assignment.

* **The $41.62\text{ Mbit/J}$ point:**
  - **Evidence:** [`STATIC-BASELINE-FAMILY-CLEANPATH-2026-09-10.md`](evidence/reports/STATIC-BASELINE-FAMILY-CLEANPATH-2026-09-10.md:42).
  - **Classification:** `[ESTABLISHED: LEARNER-FREE HEURISTIC]`.
  - **Reality:** This configuration is `RSS_MAX`, a classical, unlearned greedy heuristic where each user independently connects to the beam with maximum received signal strength / SNR. Its pooled EE is $41.621560\text{ Mbit/J}$, serving $1,200 / 1,200$ users, with rate-target attainment of exactly $297 / 1,200 = 24.750\%$.
  - **Connection to Learned Routes:** **Zero.** `RSS_MAX` is an unlearned heuristic baseline that never touches a training loop or a policy network.

### 2.2 The Structural Inability of the Learned Model to Represent Either Point

Even if the proposers argue that these static endpoints represent "what the routes are trying to learn," the evidence refutes the possibility that the learned architecture can represent them:

1. **The Learned Policy Cannot Represent `RSS_MAX`:**
   - In [`APPROACHING-THE-INSTRUMENTS-2026-09-10.md`](evidence/reports/APPROACHING-THE-INSTRUMENTS-2026-09-10.md:1,28-37), schema inspection of Q1 v2 (`66ed4a3f...`) and Q2 v2 (`a891dd98...`) confirms:
     > *"Neither Q1 v2 nor Q2 v2 contains per-option `nominal_gain` (or sufficient primitives), so the learned system structurally cannot represent the rule that reaches 41.622, regardless of training, schedule or corpus; median `a0→RSS_MAX` Hamming distance is 92.5/100..."*
   - Across 16 frozen checkpoints, when the learned $a^0$ policy disagrees with `RSS_MAX`, it chooses an option with lower nominal gain in **$100.00\%$ of cases** (median loss $-1.626\text{ dB}$).
2. **The Learned Policy Cannot Represent the Crowded Endpoint:**
   - Reaching the $46.11\text{ Mbit/J}$ endpoint requires a massive global coordination move: moving a median of 93 users onto 8 beams.
   - However, C3's candidate catalogue (`bounded-union-v2`) is overwhelmingly restricted to local edits: $78.72\%$ singletons ($|A|=1$), $19.31\%$ pairs ($|A|=2$), totaling $98.13\%$ at $|A| \le 2$ ([`APPROACHING-THE-INSTRUMENTS`](evidence/reports/APPROACHING-THE-INSTRUMENTS-2026-09-10.md:143)). The candidate set contains **$0$ of the $5,814$ improving multiuser moves** needed to reach crowded configurations ([`COORDINATION-VALUE`](evidence/reports/COORDINATION-VALUE-2026-09-10.md:165)).
   - In [`APPROACHING-THE-INSTRUMENTS`](evidence/reports/APPROACHING-THE-INSTRUMENTS-2026-09-10.md:120-138), when the learned model disagrees with `CROWDCOST`, $99.13\%$ of differing choices land on a **less-occupied beam** (median $-12$ users). The learned policy suffers from an active **load-spreading bias**.

### 2.3 Adversary Deduction on the Pareto Claim

`[INFERENCE]` The proposers observed two numbers generated by external diagnostic scripts during exploratory runs ($46.11\text{ Mbit/J}$ from a combinatorial packing script, and $41.62\text{ Mbit/J}$ from a classical SNR baseline). Because one had higher EE and lower attainment, and the other had lower EE and higher attainment, the proposers appropriated them as "an energy-side configuration" and "a link-side configuration" to manufacture an artificial narrative of learned Pareto trade-offs. 

In reality:
- **Neither point is an output of the proposed method.**
- **The proposed method cannot reach either point.**
- **The proposed method does not arbitrate between them.**

Presenting this pair as evidence for the proposed architecture is a fatal breach of scientific reporting standards.

---

## 3. Failure of the Necessity Condition & Empirical Failure of Routes

The proposed narrative explicitly sets its own survival rule:
> *"Necessity condition: each route on its own must raise EE (under a service guard); a route that cannot is not a meaningful component."*

Let us test each of the three routes against the evidence.

### 3.1 Route 3 (C3 / The Interaction Route): A Uniform Destroyer of Energy Efficiency

Does Route 3 raise EE? The project ran extensive 16-seed evaluations comparing the full model (`FULL`) against an ablated model where Route 3 is replaced by a neutral-source control (`DROP_C3`).

* **Empirical Receipts ([`Z-VIEW-SCORING-2026-09-10.md`](evidence/reports/Z-VIEW-SCORING-2026-09-10.md:100-115)):**
  - **Q1 v1 Run:**
    $$\text{FULL} - \text{DROP\_C3} = -10.042006\text{ Mbit/J}\quad (-23.35\%)$$
    Seed sign distribution: **$0$ positive / $16$ negative / $0$ zero**. At all 16 seeds, retaining C3 destroys EE. Dropping C3 raises EE from $32.96$ to $43.00\text{ Mbit/J}$.
  - **Q1 v2 Run:**
    $$\text{FULL} - \text{DROP\_C3} = -1.200528\text{ Mbit/J}\quad (-2.76\%)$$
    Seed sign distribution: **$2$ positive / $14$ negative / $0$ zero**. Dropping C3 raises EE from $42.26$ to $43.46\text{ Mbit/J}$.
  - **z-view Run:**
    $$\text{FULL} - \text{DROP\_C3} = -2.251681\text{ Mbit/J}\quad (-5.26\%)$$
    Seed sign distribution: **$1$ positive / $15$ negative / $0$ zero**. Dropping C3 raises EE from $40.56$ to $42.81\text{ Mbit/J}$.

* **Learner-Free Ceiling Evidence ([`CEILING-CLEAN-AND-LEVERS-2026-09-10.md`](evidence/reports/CEILING-CLEAN-AND-LEVERS-2026-09-10.md:1,45-76)):**
  - Even under perfect oracle coordination, the clean coordination ceiling at the sealed $1.66^\circ$ beam width is a meager **$+0.844\%$** over a simple unilateral fixed point.
  - In a nested coalition support diagnostic ($|A| \le 1$ up to $|A| \le 6$), the coordination ceiling completely **saturates at $|A| \le 1$ at $+0.338\%$** and stays completely flat through $|A| \le 6$, despite expanding the catalogue from $8,888$ to $320,936$ rows and increasing selector time by $21.5\times$.
  - In [`COORDINATION-VALUE-2026-09-10.md`](evidence/reports/COORDINATION-VALUE-2026-09-10.md:1,9), exhaustive search shows that **$k=1$ (unilateral) moves improve EE at $12/12$ anchors**. There is no local coordination barrier requiring multi-user joint action.

`[ESTABLISHED]` Across all architectures, seeds, and budgets, **Route 3 fails the necessity condition**. It does not raise EE; it reliably degrades it. By the authors' own stated condition, Route 3 is not a meaningful component and must be eliminated.

### 3.2 Route 2 (C2 / Persistence & Time Side): Negligible Physics, Destructive Competition

Does Route 2 raise EE?

* **In Q1 v2, Route 2 Fails ([`Z-VIEW-SCORING`](evidence/reports/Z-VIEW-SCORING-2026-09-10.md:108)):**
  - When Q1 is improved from v1 to v2 (allowing the link route to see better features), the Route 2 marginal flips sign:
    $$\text{FULL} - \text{DROP\_C2} = -1.148719\text{ Mbit/J}\quad (-2.65\%)$$
    Seed sign distribution: **$1$ positive / $15$ negative / $0$ zero**. Dropping C2 raises EE from $42.26$ to $43.41\text{ Mbit/J}$!
  - This demonstrates destructive inter-route competition: C2 appeared positive in v1 ($+6.13\text{ Mbit/J}$) only because Q1 v1 was crippled. The moment Q1 improved, C2 became a drag on the system.
* **Oracle C2 Has No Measurable Value ([`C2-TARGET-VALUE-2026-09-10.md`](evidence/reports/C2-TARGET-VALUE-2026-09-10.md:1,7-10,113-138)):**
  - Testing a perfect, unlearned oracle C2 across 93 development anchors:
    $$\text{EE}(\text{C1}+\text{C2}) - \text{EE}(\text{C1}) = +0.2387\text{ Mbit/J}\quad (+0.68\%)$$
    The $95\%$ cluster bootstrap interval spans **$[-3.60\%, +5.73\%]$**, which cannot be distinguished from zero.
  - On the 22-anchor subset, the marginal is negative: **$-2.10\%$**.
  - Across the 30 anchors where C2 changes the decision, it **worsens the choice at 20 anchors** and improves it at only 10.
  - Under the project's sealed tie-break reading ([`V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.9`](evidence/declarations/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.9-AMENDMENT-2026-09-09.md:9)), the exact-C1 maximizer is unique at $93 / 93$ anchors; thus, C2 changes exactly **$0$ of $93$ decisions**, yielding a marginal of **identically zero**.
* **Physical Invalidity of Handover Energy ([`R2-PHYS-PROVENANCE-MATRIX-2026-08-26.md`](evidence/declarations/R2-PHYS-PROVENANCE-MATRIX-2026-08-26.md:8,126-177)):**
  - Verification status is formally sealed as `R2_PHYS_NOT_CLOSED`.
  - Incremental handover access energy $E_{HO}$ has **no physical source closure**; it is set to zero or arbitrary dimensionless weights.
  - 3GPP TS 38.133 standards interruption times are $62\text{ ms}$ (intra-satellite) and $142\text{ ms}$ (inter-satellite). On the project's $30.08\text{ s}$ decision step, $62\text{ ms}$ represents **$0.206\%$ of a decision step** (a 47-fold dilution).
  - The provenance matrix explicitly rules:
    > *"If a sourced event-local or multi-step model still has negligible EE effect, R2 must remain a continuity/QoS specialist rather than being advertised as an EE-improving Catfish."*

`[ESTABLISHED]` Route 2 fails the necessity condition as an EE-raising component. Its physical time cost is negligible on the operational clock, its energy cost is ungrounded, and in trained evaluations it is either redundant or actively harmful.

### 3.3 Route 1 (C1 / Link Quality): The Only Functioning Component

In [`Z-VIEW-SCORING`](evidence/reports/Z-VIEW-SCORING-2026-09-10.md:107), when Q1 is given effective features (v2), the C1 marginal is:
$$\text{FULL} - \text{DROP\_C1} = +12.691200\text{ Mbit/J}\quad (+42.92\%)$$
with **$16 / 16$ seeds positive**.

`[INFERENCE]` The entire system's positive performance is driven by Route 1 (per-user link quality). Routes 2 and 3 do not form a symbiotic multi-objective triad; they are non-functional appendages that degrade the performance of Route 1.

---

## 4. Circularity, Outcome-Fitting, and Retrospective Re-Labelling

The proposed narrative candidly admits:
> *"the narrative was developed in an extended conversation, turn by turn, and may have been shaped by that process; the decomposition in (1) was proposed partly because it maps onto measurements already in hand."*

In peer review, this is not an innocent confession; it is an admission of **post-hoc hypothesis generation (HARKing)** and **outcome-fitting**.

### 4.1 The Shifting Identity of Route 3

How was the decomposition originally formulated, and how did it mutate?
1. **The Contractual Definition:** In [`MULTI-CATFISH-MCRL-V03-PAPER-AUTHORING-CONTRACT-2026-08-31.md`](evidence/declarations/MULTI-CATFISH-MCRL-V03-PAPER-AUTHORING-CONTRACT-2026-08-31.md:149-179), the decomposition was strictly mathematical:
   - C1 = focal opening surplus $\zeta_{1,u} = \Delta t [R_u^C(0) - R_u^M(0)] - \lambda_0 \Delta t [P_C^N(0) - P_M^N(0)]$.
   - C3 = non-focal opening rate externality $\zeta_{3,u} = \Delta t \sum_{i \ne u} [R_i^C(0) - R_i^M(0)]$.
   - C2 = focal next-slot attributable surplus $\zeta_{2,u}$.
   It was an exact accounting identity ($g_0 + g_{1,u} = \zeta_1 + \zeta_2 + \zeta_3$), representing immediate focal, immediate non-focal, and future focal effects.
2. **The Collapse of Coordination:** When C3 was evaluated as a multi-user coordination term across 38 distinct negative rulings ([`KILL-TRIAGE-2026-09-10.md`](evidence/reports/KILL-TRIAGE-2026-09-10.md)), it failed at every stage: negative oracle marginals ([#15](evidence/reports/KILL-TRIAGE-2026-09-10.md:51)), negative learnability screens ([#21](evidence/reports/KILL-TRIAGE-2026-09-10.md:57)), and a negligible coordination ceiling of $<0.84\%$ ([`CEILING-CLEAN-AND-LEVERS`](evidence/reports/CEILING-CLEAN-AND-LEVERS-2026-09-10.md:45)).
3. **The Opportunistic Rebranding:** Later, a separate physical study investigated beam concentration ([`CROWDING-COST`](evidence/reports/CROWDING-COST-2026-09-10.md)) and found that an artificial 8-beam minimum cover yielded $46.11\text{ Mbit/J}$. Suddenly, the proposers abandoned the "rate externality / coordination" definition of C3 and rebranded it as an "energy side (beam concentration)" route!

### 4.2 Why This Rebranding is Fraudulent

- **The C3 network never learned beam concentration:** C3 was trained on $\zeta_3$ (non-focal bits) or coalition residuals $\Psi_A$ in `bounded-union-v2`. It was never trained with a global beam-packing loss.
- **The learned policy actively spreads load:** As measured in [`APPROACHING-THE-INSTRUMENTS`](evidence/reports/APPROACHING-THE-INSTRUMENTS-2026-09-10.md:124), the learned policy exhibits a $99.13\%$ bias towards *less-occupied* beams, directly opposing concentration.
- **Violation of Sealed Priority Declarations:** The project's sealed priority declaration ([`V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-2026-09-08.md`](evidence/declarations/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-2026-09-08.md:16-19)) explicitly bound the rules to prevent this exact behavior:
  > *"Rules that make 'whichever helps C3' honest: ... A positive C3 under (b) with a non-positive C3 under (a) is a reported finding, not grounds to swap the primary after the fact... If C3's set-level oracle marginal is $\le 0$ in every completed, physically defensible cell, C3 training/screens/confirmation close and a bounded negative is reported."*

Redefining a failed coordination route into an "energy side / concentration" route after observing high EE in a separate, unlearned crowding script is circular outcome-fitting.

---

## 5. The Single-Judge Problem vs. Faux Pareto Optimization

The proposed narrative attempts to evade the failure of the necessity condition by claiming:
> *"Because objectives conflict, combining routes involves trade-offs, and the trade-off is between EE and service quality (served users, rate-target attainment), not EE against EE; the method's value is reaching Pareto points no single route reaches."*

This defense is mathematically and conceptually bankrupt.

### 5.1 When is a Combination Worse than its Best Constituent a Legitimate Trade-Off?

In multi-objective optimization, combining mechanisms $A$ and $B$ to form $C$ where $\text{Metric}_1(C) < \text{Metric}_1(A)$ is a legitimate Pareto trade-off **if and only if**:
1. $\text{Metric}_2(C) > \text{Metric}_2(A)$; AND
2. The problem was formulated with $\text{Metric}_1$ and $\text{Metric}_2$ as formal co-equal objectives; AND
3. Neither $A$ nor $B$ alone can achieve $C$'s balance.

None of these conditions hold here.

### 5.2 Strict Pareto Domination by Ablations

Let us examine the actual arm-level data from [`Z-VIEW-SCORING-2026-09-10.md`](evidence/reports/Z-VIEW-SCORING-2026-09-10.md:73-82) for Q1 v2:

| Arm | Pooled EE (Mbit/J) | Served Users | Rate-Target Attainment | Handover Rate |
|---|---:|---:|---:|---:|
| **`DROP_C2`** | **43.410508** | **31,965 (99.89%)** | **27.47%** | 0.9901 |
| **`DROP_C3`** | **43.462317** | 31,828 (99.46%) | **27.46%** | 0.9467 |
| **`FULL`** | **42.261789** | 31,962 (99.88%) | **27.20%** | 0.9922 |

Notice the devastating comparison between `FULL` and `DROP_C2`:
* `DROP_C2` achieves higher EE ($43.41$ vs. $42.26\text{ Mbit/J}$).
* `DROP_C2` serves **more** users ($31,965$ vs. $31,962$).
* `DROP_C2` achieves **higher** rate-target attainment ($27.47\%$ vs. $27.20\%$).

**`FULL` is strictly Pareto-dominated by `DROP_C2` across all primary performance metrics.** Adding Route 2 to `DROP_C2` does not buy a trade-off. It degrades energy efficiency, drops served users, and lowers rate-target attainment simultaneously. Calling this a "Pareto trade-off" is an attempt to dress up multi-agent interference and optimization degradation as an intended design feature.

### 5.3 Synthetic Operating Setpoint vs. True SLA Demand

The narrative treats "rate-target attainment" ($2.5\%$ vs. $24.75\%$) as an SLA service quality metric.
However, [`V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.1-AMENDMENT`](evidence/declarations/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.1-AMENDMENT-2026-09-08.md:3,6) and [`BEAM-CAPACITY-REALISM`](evidence/reports/BEAM-CAPACITY-REALISM-2026-09-10.md:122) explicitly record:
- $r^* = 50\text{ Mbit/s}$ was sealed as a **"synthetic operating point"** and **"explicitly not calibrated demand or an SLA."**
- In the crowded endpoint ($46.11\text{ Mbit/J}$), all $1,200/1,200$ users are PHY-served (decodable), delivering an average broadband rate of $29.72\text{ Mbit/s}$ per user!
- The system definition of service is decodability ($\text{SINR} \ge -1.44\text{ dB}$), which both configurations satisfy at $100.0\%$.

The authors construct a pseudo-trade-off against a synthetic power-control parameter to distract from the fact that their combined model underperforms simple ablations on system EE.

---

## 6. The Broken Objective and the Dinkelbach Non-Sequitur

The narrative argues:
> *"The combination rule must be ratio-consistent (Dinkelbach-style), not a fixed linear weighting, because a measured result shows no single linear price orders configurations by EE."*

This argument misinterprets the empirical findings of [`ETA-EXCHANGE-RATE-2026-09-10.md`](evidence/reports/ETA-EXCHANGE-RATE-2026-09-10.md) and proposes a mathematical cure that fails to treat the actual pathology.

### 6.1 What the Evidence Actually Shows About Linear Pricing

In [`ETA-EXCHANGE-RATE-2026-09-10.md`](evidence/reports/ETA-EXCHANGE-RATE-2026-09-10.md:1,7-19):
1. **Empty Admissible Interval:** It is mathematically verified that no single constant $\eta \ge 0$ can order the six clean static arms in agreement with their pooled EE order. The pair `MYOPIC_GREEDY` > `FIRST_IMPROVEMENT_FP` requires $\eta > 29.87\text{ Mbit/J}$, while `RANDOM` > `NEAREST_ELIGIBLE` requires $\eta < 12.84\text{ Mbit/J}$. These constraints are mutually exclusive.
2. **Dinkelbach Convergence:** Applying Dinkelbach iteration to the six-arm set converges in **one single iteration** to $\eta^* = 41.621560\text{ Mbit/J}$ (`RSS_MAX`), because `RSS_MAX` strictly dominates all other arms in both bits and joules ($B \uparrow, E \downarrow$).
3. **The Descent Persists at the Dinkelbach Fixed Point:**
   - Crucially, when strict first-improvement search is executed at this exact Dinkelbach fixed point $\eta^*$, **the search STILL descends away from `RSS_MAX`!**
   - Under $F = B - \eta^* E$, pooled EE falls from $41.62\text{ Mbit/J}$ to **$40.86\text{ Mbit/J}$**.
   - EE **falls at 9 of the 12 anchors** under both $F = B - \eta^* E$ and the deployed $F = B - \eta^* E - \Phi$.

### 6.2 Why Dinkelbach Fails to Fix the Objective-Metric Mismatch

Why does optimizing $F(\eta^*)$ degrade EE at $75\%$ of anchors even at the exact Dinkelbach fixed point?
[`ETA-EXCHANGE-RATE`](evidence/reports/ETA-EXCHANGE-RATE-2026-09-10.md:146) derives the exact mechanism:
- **Spatial / Anchor Heterogeneity:** The local EE of `RSS_MAX` varies dramatically across steps, from $19.8\text{ Mbit/J}$ (step 3) to $71.8\text{ Mbit/J}$ (step 0). A single pooled price $\eta^* = 41.62\text{ Mbit/J}$ is simultaneously **too low** for steps 0–2 (causing the search to over-spend energy for marginal bits) and **too high** for step 3.
- **Selection Horizon Mismatch:** The decision objective $F$ is evaluated on a myopic **boundary-0 snapshot** (instantaneous channel), whereas the reported metric $\eta^N$ integrates over the **full 48 boundaries** of the 30.08 s interval. In [`COORDINATION-VALUE`](evidence/reports/COORDINATION-VALUE-2026-09-10.md:124-142), boundary-0 $F$ rejects $3,671$ service-guarded EE improvements (including one worth $+7.85\text{ Mbit/J}$) and accepts $24,278$ EE decreases!

### 6.3 Adversary Deduction on Dinkelbach

`[INFERENCE]` Invoking a "Dinkelbach-style combination rule" is an academic hand-wave. Dinkelbach's algorithm solves fractional programming problems $\max B(x)/E(x)$ over a fixed set via parametric linear programs $\max B(x) - \lambda E(x)$ where $\lambda$ is updated globally at each outer iteration. 
In a decentralized multi-agent reinforcement learning environment:
- An adaptive $\lambda_t$ creates an intensely **non-stationary reward function**, destroying the convergence guarantees of independent Q-learners.
- More damningly, the empirical evidence proves that even if $\lambda$ is set to the exact optimal ratio $\eta^*$, the policy **still moves in the wrong direction at 9 of 12 anchors** due to the horizon and spatial mismatch.

Citing the linear order failure to justify Dinkelbach without solving the horizon and spatial dispatch problem is theoretical posturing unsupported by the data.

*(Literature note: Calvo-Fullana et al. 2023 [Prop. 1] is cited in the tasking for linear scalarization standing, but as noted in [`ETA-EXCHANGE-RATE`](evidence/reports/ETA-EXCHANGE-RATE-2026-09-10.md:197), standing in literature does not substitute for empirical validity in this physics.)*

---

## 7. Relation to the Baseline (MODQN)

The proposed narrative contrasts itself with a multi-objective DQN baseline with three rewards:
- $r_1 = \text{EE}$ (per-link additive contribution to system EE, $R_u / P^N$);
- $r_2 = -\Psi$ (handover interruption penalty);
- $r_3 = -U_{b_u}$ (negative beam occupancy / load balance).

This comparison exposes fatal structural contradictions.

### 7.1 The Baseline Objective Actively Destroys System EE

Consider the physical role of $r_3 = -U_{b_u}$:
- $r_3$ penalizes beam occupancy, incentivizing the policy to **spread users evenly across all available beams**.
- Now examine the physical reality of the satellite payload, proven in [`CROWDING-COST-2026-09-10.md`](evidence/reports/CROWDING-COST-2026-09-10.md:1,66-93):
  - Activating a beam chain incurs a continuous hardware overhead of $0.338\text{ W}$ ($10.17\text{ J}$ per step), plus $0.200\text{ W}$ ($6.02\text{ J}$) for the first active beam on a satellite ([`batch.py`](evidence/code/energy_efficiency.py)).
  - Because of these fixed opening costs, system EE decreases monotonically with every active beam added:
    $$\frac{d(\text{EE})}{d(\text{active})} = -425,009.885\text{ bit/J per added mean-active beam}$$
  - Spreading assignments across beams reduces system EE from $46.11\text{ Mbit/J}$ (8 active beams) down to $7.75\text{ Mbit/J}$ (98 active beams) — an **$83.19\%$ destruction of energy efficiency**!

`[ESTABLISHED]` In this satellite physics, **load balancing is diametrically opposed to energy efficiency**. By rewarding load spreading, MODQN's $r_3$ drives the satellite to open unnecessary RF chains, burning power and collapsing system EE. As [`CROWDING-COST`](evidence/reports/CROWDING-COST-2026-09-10.md:134) states:
> *"On this panel an explicit load-balancing term would be actively harmful to EE because it would reward movement in the direction whose measured EE slope is negative."*

### 7.2 Is the Proposed Method Distinguishable from the Baseline?

The proposed method claims three routes: link quality, concentration, and handover avoidance.
- But if Route 3 in the baseline was spreading users, and the proposed method's Route 3 is also exhibiting a load-spreading bias (as proven in [`APPROACHING-THE-INSTRUMENTS`](evidence/reports/APPROACHING-THE-INSTRUMENTS-2026-09-10.md:124)), then the proposed method has simply inherited the flawed dynamics of the baseline.
- If the proposers instead claim their Route 3 encourages *concentration*, they have no mechanism or loss function that enforces it, and the empirical selections refute it.

### 7.3 The Non-Existent External Baseline

Most damningly, can the authors even demonstrate that their method beats the baseline?
In [`BASELINE-MODQN-REFERENCE-2026-09-10.md`](evidence/reports/BASELINE-MODQN-REFERENCE-2026-09-10.md:1,11-13,71-76):
- **No runnable V0.25 external BASELINE exists.**
- The legacy MODQN checkpoint (from V0.23) cannot run on the V0.25 environment because no input adapter, action mapping, or joint repair rule was ever implemented.
- In the project's actual execution scripts, the object evaluated under the label `BASELINE` is **`carrier_base`**, a trivial, static geometric rule (`nearest-eligible`).
- The project has **never measured the true MODQN baseline on the current physics**. Any claim of outperforming MODQN is completely unsupported by code or data.

### 7.4 MODQN Was Never Collapsed

The proposers justified the overhaul by importing a diagnosis from a sibling project that MODQN suffers from "geometric collapse" (all users piling onto one beam).
[`MODQN-COLLAPSE-2026-09-10.md`](evidence/reports/MODQN-COLLAPSE-2026-09-10.md:1,7-11) definitively refutes this:
- On 100 native evaluation profiles, authenticated MODQN opened an average of **$68.70$ physical beams** and $7.47$ satellites, with a mean largest-beam occupancy of only $4.17$ users out of 100 (maximum observed: 7).
- MODQN was never collapsed; it was broadly spread. The motivating premise for the entire Catfish redesign was an imported myth that does not hold in this environment.

---

## 8. Methodological Audit & Evidence Breakdown

To maintain strict scientific standards, I classify the evidence into explicit categories:

| Finding | Classification | Underlying Document & Verification |
|---|---|---|
| 46.11 vs. 41.62 Mbit/J are unlearned static/diagnostic configurations | **[ESTABLISHED: LEARNER-FREE]** | [`CROWDCOST:7`](evidence/reports/CROWDING-COST-2026-09-10.md:7), [`STATIC-FAMILY:42`](evidence/reports/STATIC-BASELINE-FAMILY-CLEANPATH-2026-09-10.md:42), [`BEAMCAP:118`](evidence/reports/BEAM-CAPACITY-REALISM-2026-09-10.md:118) |
| Q1/Q2 structurally cannot represent `RSS_MAX` (missing `nominal_gain`) | **[ESTABLISHED: CODE AUDIT]** | [`APPROACHING:1,28`](evidence/reports/APPROACHING-THE-INSTRUMENTS-2026-09-10.md:1,28), [`q1_schema_v2.py`](evidence/reports/APPROACHING-THE-INSTRUMENTS-2026-09-10.md:40) |
| Dropping Route 3 improves EE across all 16 seeds | **[ESTABLISHED: TRAINED MODEL, IN-SAMPLE]** | [`Z-VIEW-SCORING:100-115`](evidence/reports/Z-VIEW-SCORING-2026-09-10.md:100-115) |
| Dropping Route 2 in Q1 v2 improves EE across 15/16 seeds | **[ESTABLISHED: TRAINED MODEL, IN-SAMPLE]** | [`Z-VIEW-SCORING:108`](evidence/reports/Z-VIEW-SCORING-2026-09-10.md:108) |
| Oracle C2 value is within noise (+0.68%, CI covers zero) or 0.00% under tie-break | **[ESTABLISHED: ORACLE / LEARNER-FREE]** | [`C2TARGET:1,113-138`](evidence/reports/C2-TARGET-VALUE-2026-09-10.md:1,113-138) |
| Handover energy $E_{HO}$ is unsourced; time dilution is $47\times$ | **[ESTABLISHED: PROVENANCE SEAL]** | [`R2-PHYS:8,126-177`](evidence/declarations/R2-PHYS-PROVENANCE-MATRIX-2026-08-26.md:8,126-177) |
| Linear price ordering fails; descent persists at Dinkelbach $\eta^*$ at 9/12 anchors | **[ESTABLISHED: LEARNER-FREE SEARCH]** | [`ETAFIX:1,11-19,118`](evidence/reports/ETA-EXCHANGE-RATE-2026-09-10.md:1,11-19,118) |
| Spreading beams destroys EE ($d(\text{EE})/d(\text{active}) = -425\text{ kbit/J}$) | **[ESTABLISHED: PHYSICAL SIMULATION]** | [`CROWDCOST:1,89-93`](evidence/reports/CROWDING-COST-2026-09-10.md:1,89-93) |
| No runnable external MODQN baseline exists on V0.25 | **[ESTABLISHED: CODE INSPECTION]** | [`BASELINE-REF:1,11-13`](evidence/reports/BASELINE-MODQN-REFERENCE-2026-09-10.md:1,11-13) |
| 100% of panel anchors in Z-VIEW-SCORING are training anchors | **[ESTABLISHED: DATA AUDIT]** | [`CONVSCORE:1,68-98`](evidence/reports/CONVERGED-EXACT-SCORING-2026-09-11.md:1,68-98) |
| Unilateral moves ($k=1$) improve EE at 12/12 anchors (no coordination barrier) | **[ESTABLISHED: EXHAUSTIVE ENUMERATION]** | [`COORDVALUE:1,9,41-52`](evidence/reports/COORDINATION-VALUE-2026-09-10.md:1,9,41-52) |
| F8 certified fixed-point reference axes were contaminated | **[ESTABLISHED: CACHE DEFECT AUDIT]** | [`Z-VIEW-SCORING:254-264`](evidence/reports/Z-VIEW-SCORING-2026-09-10.md:254-264), [`CLEANPATH:24`](evidence/reports/STATIC-BASELINE-FAMILY-CLEANPATH-2026-09-10.md:24) |

### 8.1 Total In-Sample Contamination

[`CONVERGED-EXACT-SCORING-2026-09-11.md`](evidence/reports/CONVERGED-EXACT-SCORING-2026-09-11.md:1,97-101) exposes an irrecoverable methodological flaw in the reported trained-model numbers:
> *"Train/score anchor overlap is total: every one of the 20 panel anchors (`V025_PROBE/world/1`, steps 0–6, global 000–019) is a training anchor of every run checked... Any score on these panels is therefore IN-SAMPLE, the Z-VIEW-SCORING numbers included... no number on these panels measures generalisation to unseen anchors..."*

`[ESTABLISHED]` Every single marginal, seed count, and percentage reported in [`Z-VIEW-SCORING`](evidence/reports/Z-VIEW-SCORING-2026-09-10.md) is **$100\%$ in-sample**. Even with the severe unfair advantage of in-sample memorization, Route 3 and Route 2 failed to beat their ablated counterparts. There is **zero out-of-sample evidence** in this entire snapshot.

---

## 9. Reviewer Demands & Prohibited Claims

Before any version of this work could be considered for publication, a peer review panel must impose uncompromising demands and strictly police forbidden claims.

### 9.1 What the Paper Must NOT Claim

The authors must be barred from making the following assertions:
1. **NO Claim of Multi-Route Synergy:** The authors must not claim that the three routes jointly improve EE, that they form an effective decomposition of system EE, or that Route 2 and Route 3 are validated, necessary components.
2. **NO Claim of Learned Pareto Frontiers:** The authors must not claim that the method reaches non-dominated Pareto operating points between EE and service quality, and must explicitly withdraw the $46.11$ vs. $41.62\text{ Mbit/J}$ example as a comparison of learned policies.
3. **NO Claim of Dinkelbach Resolution:** The authors must not claim that a Dinkelbach combination rule resolves the linear scalarization failure in policy deployment without presenting a fully implemented, converged, and evaluated closed-loop algorithm.
4. **NO Claim of Beating MODQN:** The authors must not claim superiority over the baseline MODQN on the V0.25 physics until an authentic, runnable MODQN baseline is implemented and evaluated under identical conditions.
5. **NO Claim of Handover Energy Optimization:** The authors must not claim that Route 2 optimizes handover energy, given that handover energy is unclosed ($E_{HO}=0$) and interruption time is diluted to $0.2\%$ of the decision step.
6. **NO Claim of Generalization:** The authors must not report any numbers from the 20-anchor development panels as evidence of policy generalization.

### 9.2 What a Reviewer Would Demand

1. **Strict Held-Out Evaluation:** Complete execution of the Stage 8 evaluation protocol ([`V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md`](evidence/declarations/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md)) on the 48 frozen, evaluation-only claim dates, evaluated with the pre-registered two-way cluster bootstrap across 12 learner seeds.
2. **Authentic MODQN Bridge:** Construction of a verified, byte-authenticated V0.25 bridge for the baseline MODQN policy, reporting true baseline EE, active beams, and handover rates on the identical test panel.
3. **Multi-Step Continuation Evaluation for C2:** Execution of the proposed T1/T2 time-indexed endpoint attribution test ([`C2-TARGET-VALUE`](evidence/reports/C2-TARGET-VALUE-2026-09-10.md:239-254)) to determine whether C2 carries genuine horizon value at steps $t+1 \dots t+3$ or is merely fitting step-$t$ residuals of C1.
4. **Honest Baseline Calibration:** Reporting the performance of simple classical heuristics (e.g. `RSS_MAX` with simple admission gating) alongside any learned models, with honest disclosure that `RSS_MAX` outperforms all learned models on clean evaluators ($41.62\text{ Mbit/J}$).

---

## 10. What Survives the Attack? (The Honest Paper)

If the grandiose three-route Catfish Pareto narrative is discarded, does any valid scientific contribution survive this critique?

**Yes — but it is a fundamentally different, humbler paper.**

### The Honest Paper That Could Be Accepted:

1. **A Rigorous Negative Result on Multi-User LEO Coordination:**
   - The paper can document the exhaustive search showing that $k=1$ unilateral moves improve EE at $12/12$ anchors, that the coordination ceiling is saturated below $0.84\%$, and that attempting to train a multi-user coordination route (C3) systematically degrades reinforcement learning performance.
   - This is an important, high-value negative result: it warns the satellite communications community that complex multi-agent coordination architectures are largely unnecessary and counterproductive for downlink beam assignment in this operational regime.
2. **Analysis of the Physical Flaw in Classical Load Balancing:**
   - The paper can provide a deep physical and mathematical analysis of why the standard multi-objective reward formulation ($r_3 = -U_{b_u}$) inherited from terrestrial networks backfires in LEO constellations.
   - In terrestrial cellular networks, base stations are already powered on and interference is local; in LEO satellite payloads, radiating beam chains incur massive fixed DC power overheads. Spreading load opens RF chains and monotonically destroys system energy efficiency ($d(\text{EE})/d(\text{active}) = -425\text{ kbit/J}$). Exposing this physical mechanism is a valuable contribution.
3. **A Hardened Single-Route (C1) Link Quality Architecture:**
   - Route 1 (focal link quality) demonstrably works. When provided with proper geometric gain features, C1 delivers robust, sign-consistent EE gains ($+12.69\text{ Mbit/J}$, $16/16$ seeds positive).
   - A stripped-down, single-agent RL policy optimizing angle-aware path loss and link margin, coupled with a simple heuristic beam shut-off mechanism, represents a sound, reproducible engineering contribution.

### Conclusion

The proposers tried to weave an intricate narrative of three complementary Catfish routes navigating a subtle Pareto frontier via Dinkelbach optimization. That narrative is thoroughly contradicted by their own experimental data. The data reveals a story of an effective link optimizer (C1) dragged down by two non-functional, outcome-fitted routes (C2 and C3), evaluated against phantom baselines and justified using unlearned heuristic data points. 

Until the authors abandon this fictional narrative and report their results with scientific fidelity, the manuscript must be **Rejected**.
