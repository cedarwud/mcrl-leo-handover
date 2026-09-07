# Multi-Catfish MCRL Teaching Deck: Storyboard Plan (V0.23)

- **Target Presentation Template:** `/home/u24/pptx-craft/assets/wmnlab.pptx` (13.333" × 7.5", 16:9 widescreen)
- **Typographic Authority:** Times New Roman throughout. Slide Titles: **28 pt**; Ordinary body text: **24 pt**; Text inside diagrams/cards/boxes: **20 pt**. No 26, 22, 18, 16, or 14 pt text. Ordinary prose and acronyms upright; variables, Greek symbols, and formulas in native OfficeMath italic.
- **Active Method Baseline:** V0.23 Method Core Frozen (`docs/MULTI-CATFISH-MCRL-V023-C3-METHOD-FREEZE-2026-09-05.md`), LC-SRS Observability Gate Contract (`docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md`), Current Multi-Catfish Authority (`docs/CURRENT-MULTI-CATFISH-AUTHORITY.md`).
- **Active Symbol Authority:** `artifacts/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md` (§10.13) and `artifacts/chinese-word-v023-lcsrs-20260905-r2/SYMBOL-COLLISION-AND-SINGLE-LETTER-AUDIT.md`.
- **Method Name Authority:** *Multi-Catfish MCRL* (no unverified acronym expansion).
- **Status Tags Used:** `STABLE`, `PROVISIONAL_C3_GATE`, `RESULTS_PENDING`.

---

## Deck Structure Overview (38 Slides)

| Slide # | Slide Title | Cadence Section | Status Tag | Primary Layout |
|:---|:---|:---|:---|:---|
| 1 | Multi-Catfish MCRL: Teaching Deck Overview | Part I: Motivation & Objective | `STABLE` | Title Hero Layout |
| 2 | LEO Satellite Network Context: Orbital Dynamics & Narrow Beams | Part I: Motivation & Objective | `STABLE` | Split Diagram + Bullets |
| 3 | Coupled Satellite Resources: Beam Power & Ground Interference | Part I: Motivation & Objective | `STABLE` | 2-Card Resource Grid |
| 4 | Limits of Conventional Multi-Objective Handover: The MODQN Dilemma | Part I: Motivation & Objective | `STABLE` | Comparison Side-by-Side |
| 5 | The Canonical Endpoint: Network Ratio-of-Sums Energy Efficiency | Part I: Motivation & Objective | `STABLE` | Formula Spotlight + Metric Card |
| 6 | Linear Surplus Formulation and the Frozen Multiplier | Part I: Motivation & Objective | `STABLE` | Linear Surplus Box |
| 7 | The Causal Attribution Dilemma in Multi-User Handover | Part II: Causal Decomposition | `STABLE` | Three Questions Callout Grid |
| 8 | Architecture Invariant: Three Independent Q Networks | Part II: Causal Decomposition | `STABLE` | 3-Head Independent Topology |
| 9 | Architecture Invariant: Route-Local Zero-Bootstrap Training | Part II: Causal Decomposition | `STABLE` | Loss Flow Diagram |
| 10 | Unilateral Counterfactual Evaluation: The C1 Opening Intervention | Part II: Causal Decomposition | `STABLE` | Branch Comparison Tree |
| 11 | The Coalition Exception: Why C3 Breaks Unilateral Symmetry | Part II: Causal Decomposition | `PROVISIONAL_C3_GATE` | Unilateral vs Coalition Card |
| 12 | Route C1 Role: Focal Opening Net Surplus | Part III: Route C1 | `STABLE` | Role Card & Responsibilities |
| 13 | Route C1 Target Formulation: Assigning Opening Energy | Part III: Route C1 | `STABLE` | Math Derivation Panel |
| 14 | Route C1 Lineage: The RIS EXP/ACRM Provenance | Part III: Route C1 | `STABLE` | Lineage Process Pipeline |
| 15 | Route C1 Historical Evidence: V0.4 Frozen-Policy Margin | Part III: Route C1 | `STABLE` | Historical Evidence Card |
| 16 | Route C2 Role: Evaluating Temporal Persistence | Part IV: Route C2 | `STABLE` | Persistence Timeline Card |
| 17 | Route C2 Evolution: From Temporal-Fork to First-Successor k1 | Part IV: Route C2 | `STABLE` | Chronological Evolution Tree |
| 18 | Route C2 Diagnostic Failures: V0.6 Screen and V0.7 R14 Audit | Part IV: Route C2 | `STABLE` | Forensic Metric Card |
| 19 | Current C2 Status: Present but Unqualified OPS-3 Diagnostic | Part IV: Route C2 | `STABLE` | Boundary Warning Box |
| 20 | The Spatial Externality Problem: Shared Beam Coupling | Part V: Route C3 (LC-SRS) | `PROVISIONAL_C3_GATE` | Spatial Interference Map |
| 21 | The Beam Extinction Blindspot in Unilateral Exploration | Part V: Route C3 (LC-SRS) | `PROVISIONAL_C3_GATE` | 3-Panel Step Diagram |
| 22 | The Two-User Cooperative Game: Four Matched Profiles | Part V: Route C3 (LC-SRS) | `PROVISIONAL_C3_GATE` | 2×2 Profile Matrix |
| 23 | Exact Two-Player LC-SRS Teacher Formulation | Part V: Route C3 (LC-SRS) | `PROVISIONAL_C3_GATE` | Formula-Dense Derivation Panel |
| 24 | Super-Additive Interaction Surplus and the Shapley Target | Part V: Route C3 (LC-SRS) | `PROVISIONAL_C3_GATE` | Interaction Surplus Block |
| 25 | Construction-Level Exact Identity: Surplus Conservation | Part V: Route C3 (LC-SRS) | `PROVISIONAL_C3_GATE` | Conservation Spotlight Panel |
| 26 | The Teacher Anchor Surface: Supported, Reference, and Control | Part V: Route C3 (LC-SRS) | `PROVISIONAL_C3_GATE` | 3-Class Partition Grid |
| 27 | Deployment C3View: Committed vs. Detached Context | Part V: Route C3 (LC-SRS) | `PROVISIONAL_C3_GATE` | Tensor Schema Block |
| 28 | Relational Token Architecture: Shared 67-64-64-1 Scorer | Part V: Route C3 (LC-SRS) | `PROVISIONAL_C3_GATE` | Neural Network Architecture Flow |
| 29 | Reference-Centering: Enforcing the Structural Zero Invariant | Part V: Route C3 (LC-SRS) | `PROVISIONAL_C3_GATE` | Invariant Proof Card |
| 30 | Pairwise Advantage Learning: Zero-Bootstrap Loss | Part VI: Learning & Deployment | `STABLE` | Objective Panel |
| 31 | Class-Balanced Tri-Partite Loss for LC-SRS | Part VI: Learning & Deployment | `PROVISIONAL_C3_GATE` | Tri-Partite Loss Panel |
| 32 | One-Pass Deployment: Native Masked Argmax | Part VI: Learning & Deployment | `STABLE` | Single Decision Seam Diagram |
| 33 | Runtime Invariants: Prohibited Coordination Mechanisms | Part VI: Learning & Deployment | `STABLE` | Red-Line Prohibition Grid |
| 34 | Method Safeguards: Native Masks and Propensity Strata | Part VII: Rigor & Evaluation | `STABLE` | 4-Quadrant Shield Architecture |
| 35 | Active V0.23 Development Gate: Four Evaluation Arms | Part VII: Rigor & Evaluation | `PROVISIONAL_C3_GATE` | 4-Arm Gate Specification Table |
| 36 | Active V0.23 Development Gate: Pre-Registered Passing Criteria | Part VII: Rigor & Evaluation | `PROVISIONAL_C3_GATE` | Pre-Registered Predicates List |
| 37 | Historical vs. Future Evaluation: The Multi-Arm Matrix | Part VII: Rigor & Evaluation | `RESULTS_PENDING` | Historical / Future Table |
| 38 | Scientific Claim Ceiling: Development Gate Boundary | Part VII: Rigor & Evaluation | `STABLE` | Final Boundary Synthesis Card |

---

## Detailed Slide-by-Slide Storyboard

### Slide 1: Multi-Catfish MCRL: Teaching Deck Overview
- **Teaching Purpose:** Establish the presentation subject, the core architectural concept, author context, and date baseline without unverified acronym expansions.
- **Status Tag:** `STABLE`
- **Authority Citations:**
  - `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md` §Binding authority
  - `docs/MULTI-CATFISH-MCRL-V03-PRESENTATION-LAYER-2026-08-31.md` §1
- **Exact Content:**
  - *Title (28 pt):* Multi-Catfish MCRL: Teaching Deck Overview
  - *Body Text (24 pt):*
    - Core Method Concept: One canonical energy-efficiency objective, three independent Q surfaces, and one native masked argmax.
    - Resolves multi-user beam contention through training-time counterfactual attribution without runtime coordination overhead.
    - Active Baseline: V0.23 method core freeze and pre-outcome observability gate contract.
- **Suggested Visual:** Hero title layout on clean white background with wmnlab deep blue accents (`#003366`). 28 pt bold title, 24 pt subtitle, and metadata box containing author affiliation, date (2026-09-05), and active baseline status. Box text: 20 pt.

---

### Slide 2: LEO Satellite Network Context: Orbital Dynamics & Narrow Beams
- **Teaching Purpose:** Explain the physical environment of dense LEO satellite constellations: fast orbital velocities, narrow steerable spot beams, and frequent handovers.
- **Status Tag:** `STABLE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V03-ALGORITHM-SPEC-2026-08-31.md` §1
  - `artifacts/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md` §2, §4
- **Exact Content:**
  - *Title (28 pt):* LEO Satellite Network Context: Orbital Dynamics & Narrow Beams
  - *Body Text (24 pt):*
    - High Orbit Velocity: Satellites move rapidly relative to ground users $u \in \mathcal{U}$, causing rapid geometry transitions.
    - Geometric Variation: Slant range $d_{u,s,v}(t)$ and beam off-axis angle $\theta_{u,s,v}(t)$ drift continuously over time.
    - Frequent Handovers: Ground users must repeatedly switch serving beams and satellites to maintain communication link connectivity.
- **Suggested Visual:** Split layout: Left diagram box (width: 5.8", height: 5.6") illustrating satellite orbital track, beam footprints, and ground users with 20 pt labels. Right container (width: 5.8", height: 5.6") presenting 24 pt bullet text.

---

### Slide 3: Coupled Satellite Resources: Beam Power & Ground Interference
- **Teaching Purpose:** Detail the electrical and spectral coupling across satellite beams: fixed base power, RF radiated power, and co-channel interference.
- **Status Tag:** `STABLE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V03-ALGORITHM-SPEC-2026-08-31.md` §1
  - `artifacts/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md` §2.1, §4
- **Exact Content:**
  - *Title (28 pt):* Coupled Satellite Resources: Beam Power & Ground Interference
  - *Body Text (24 pt):*
    - Beam Activation Cost: Activating a spot beam incurs substantial DC power for baseband and amplifier circuits.
    - Spectral Coupling: Co-channel beams produce mutual interference, and users sharing a beam divide total bandwidth $B^w / U_{s,v}$.
    - System Trade-off: Optimizing a single link often wakes up idle beams or creates interference, degrading global efficiency.
- **Suggested Visual:** 2-card grid: Left box (width: 5.8", height: 5.6", background `#F8FAFC`, border `#003366`) covering "Electrical Hardware Costs". Right box (width: 5.8", height: 5.6", background `#F8FAFC`, border `#003366`) covering "Radio Interference Coupling". Card text: 20 pt.

---

### Slide 4: Limits of Conventional Multi-Objective Handover: The MODQN Dilemma
- **Teaching Purpose:** Diagnose why conventional Multi-Objective Deep Q-Networks (MODQN) fail to optimize global energy efficiency.
- **Status Tag:** `STABLE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V03-ALGORITHM-SPEC-2026-08-31.md` §1–2
  - `docs/MULTI-CATFISH-EE-AXIS-REDESIGN-CONTRACT-V0.3-2026-08-31.md` §1
- **Exact Content:**
  - *Title (28 pt):* Limits of Conventional Multi-Objective Handover: The MODQN Dilemma
  - *Body Text (24 pt):*
    - Heuristic Scalarization: Conventional methods sum disparate metrics $r = w_1 r_1 + w_2 r_2 + w_3 r_3$ using arbitrary manual weights.
    - Incompatible Units: Bits per second, handover counts, and user ratios cannot physically sum into energy efficiency.
    - System Blindness: Greedy optimization of link quality ignores shared satellite activation costs and non-focal degradation.
- **Suggested Visual:** Comparative 2-panel display: Left card (Red border `#DC2626`) showing "Conventional MODQN: Heuristic Vector Sum". Right card (Green border `#059669`) showing "Multi-Catfish Approach: Canonical Global EE". Text inside cards: 20 pt.

---

### Slide 5: The Canonical Endpoint: Network Ratio-of-Sums Energy Efficiency
- **Teaching Purpose:** Define the rigorous, immutable physical metric that governs the entire work: network ratio-of-sums energy efficiency.
- **Status Tag:** `STABLE`
- **Authority Citations:**
  - `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md` §Binding authority
  - `artifacts/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md` §10.13.1
- **Exact Content:**
  - *Title (28 pt):* The Canonical Endpoint: Network Ratio-of-Sums Energy Efficiency
  - *Body Text (24 pt):*
    - The Immutable Objective: Global network energy efficiency over full rollout episodes:
      $$[\text{omml: } \eta^N = \frac{\mathcal{B}}{\mathcal{E}} = \frac{\sum_t \sum_{u\in\mathcal{U}} R_u(t) \Delta t}{\sum_t P^N(t) \Delta t} \quad [\text{bit/J}]]$$
    - Strict Accounting: Evaluated as total delivered bits divided by total consumed electrical energy.
    - Operational Rule: Never evaluated as an average of per-step or per-link ratios.
- **Suggested Visual:** Large spotlight container (width: 12.0", height: 5.6", background `#F0F4F8`, border `#003366`) displaying the ratio-of-sums equation centered, with structured 20 pt annotation callouts defining $\mathcal{B}$, $\mathcal{E}$, and the non-averaging invariant.

---

### Slide 6: Linear Surplus Formulation and the Frozen Multiplier
- **Teaching Purpose:** Explain the linear surplus transformation using the frozen baseline multiplier $\lambda$ to enable additive credit assignment.
- **Status Tag:** `STABLE`
- **Authority Citations:**
  - `artifacts/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md` §10.13.1
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` §2.1, §5
- **Exact Content:**
  - *Title (28 pt):* Linear Surplus Formulation and the Frozen Multiplier
  - *Body Text (24 pt):*
    - Linear Surplus Metric: To permit additive decomposition while preserving gradient direction:
      $$[\text{omml: } G(x) = \sum_{u\in\mathcal{U}} B_u(x) - \lambda E(x) \quad [\text{bit}]]$$
    - Baseline Multiplier: $\lambda$ is fixed before outcomes from the baseline operating ratio $\lambda = \mathcal{B}_0^M / \mathcal{E}_0^M$.
    - Alignment Guarantee: A positive surplus change $\Delta G > 0$ strictly preserves the first-order improvement direction of $\eta^N$.
- **Suggested Visual:** Central equation panel (width: 12.0", height: 5.6", background `#FFFFFF`, border `#CBD5E1`) showing surplus conversion and dimensional consistency verification: Bits minus (Bit/J)*J = Bits. Text inside callouts: 20 pt.

---

### Slide 7: The Causal Attribution Dilemma in Multi-User Handover
- **Teaching Purpose:** Demonstrate why a single scalar reward fails to guide decentralized policies: conflation of focal gain, non-focal externality, and persistence.
- **Status Tag:** `STABLE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V03-ALGORITHM-SPEC-2026-08-31.md` §1, §3
- **Exact Content:**
  - *Title (28 pt):* The Causal Attribution Dilemma in Multi-User Handover
  - *Body Text (24 pt):*
    - Aggregate Conflation: A single reward change $\Delta G$ hides the distinct physical channels affected by a handover decision.
    - Three Fundamental Questions:
      - Did the switching user gain throughput justified by incremental power?
      - Did the switch cause interference or unload a shared beam for other users?
      - Does the chosen beam remain beneficial in subsequent time slots?
    - Attribution Requirement: Effective learning requires decomposing the global outcome into independent causal roles.
- **Suggested Visual:** 3-column callout layout (each box width: 3.8", height: 5.4", background `#F8FAFC`, border `#94A3B8`). Left: "Focal User Impact". Center: "Non-Focal Spatial Externality". Right: "Temporal Persistence". Box text: 20 pt.

---

### Slide 8: Architecture Invariant: Three Independent Q Networks
- **Teaching Purpose:** Present the three-Q architecture invariant: independent parameters, no shared trunk, and route-local value surfaces.
- **Status Tag:** `STABLE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` §0 (Hard invariant 1)
  - `docs/MULTI-CATFISH-MCRL-V03-ALGORITHM-SPEC-2026-08-31.md` §2
- **Exact Content:**
  - *Title (28 pt):* Architecture Invariant: Three Independent Q Networks
  - *Body Text (24 pt):*
    - Dedicated Surfaces: The architecture instantiates exactly three value networks: $Q_1(s_u, a)$, $Q_2(s_u, a)$, and $Q_3(s_u, a)$.
    - Independent Parameters: Each network possesses separate weights and an independent optimizer without a shared trunk.
    - Absence of Interference: Gradient updates to one Q network cannot alter or corrupt the representation of the other two networks.
- **Suggested Visual:** Topology diagram showing three parallel, unconnected neural network blocks: Top Blue ($Q_1$), Middle Amber ($Q_2$), Bottom Green ($Q_3$). Labeled with "Independent Weights & Optimizers". Box text: 20 pt.

---

### Slide 9: Architecture Invariant: Route-Local Zero-Bootstrap Training
- **Teaching Purpose:** Explain the zero-bootstrap pairwise regression training paradigm that eliminates Bellman instability and target networks.
- **Status Tag:** `STABLE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` §3.3
  - `docs/MULTI-CATFISH-MCRL-C1-C3-PAPER-AUTHORING-DELTA-2026-09-01.md` §7
- **Exact Content:**
  - *Title (28 pt):* Architecture Invariant: Route-Local Zero-Bootstrap Training
  - *Body Text (24 pt):*
    - Zero-Bootstrap Regression: Networks are trained directly on sealed counterfactual advantages rather than recursive TD estimates.
    - No Target Networks: Eliminates lagging target networks, polyak averaging, and temporal credit oscillation.
    - Route Isolation: Each training record updates only its designated route network, preventing cross-route gradient leakage.
- **Suggested Visual:** Contrast block diagram: Upper panel showing conventional RL with unstable recursive Bellman loops (marked with red cross). Lower panel showing Multi-Catfish direct pairwise advantage regression (marked with green check). Box text: 20 pt.

---

### Slide 10: Unilateral Counterfactual Evaluation: The C1 Opening Intervention
- **Teaching Purpose:** Explain the unilateral counterfactual methodology used for Route C1, where a single focal user moves while reference actions are frozen.
- **Status Tag:** `STABLE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-C1-C3-PAPER-AUTHORING-DELTA-2026-09-01.md` §3, §4
- **Exact Content:**
  - *Title (28 pt):* Unilateral Counterfactual Evaluation: The C1 Opening Intervention
  - *Body Text (24 pt):*
    - Reference Branch $M$: Ground users execute the frozen reference policy action profile $a^0$.
    - Candidate Branch $C$: Focal user $u$ unilaterally selects candidate action $a_u^C$, while all other users maintain reference actions.
    - Matched Random Field: Both branches share identical keyed fading draws to isolate the causal effect of user $u$'s action.
- **Suggested Visual:** Branching tree diagram: Root node "Anchor State" splits into Branch $M$ (all users at reference) and Branch $C$ (user $u$ intervenes, non-focal users frozen). Labels and annotations: 20 pt.

---

### Slide 11: The Coalition Exception: Why C3 Breaks Unilateral Symmetry
- **Teaching Purpose:** Contrast unilateral evaluation with Route C3: explain why C3 is a deliberate exception that requires a two-user coalition game.
- **Status Tag:** `PROVISIONAL_C3_GATE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V023-C3-METHOD-FREEZE-2026-09-05.md` §1
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` §1, §5
- **Exact Content:**
  - *Title (28 pt):* The Coalition Exception: Why C3 Breaks Unilateral Symmetry
  - *Body Text (24 pt):*
    - Unilateral Limitation: A single user migrating cannot de-energize a shared beam if other users remain on it.
    - The C3 Coalition Model: Route C3 explicitly models a two-user local coalition departing a shared source beam.
    - Scope Restriction: Unilateral counterfactuals apply to Route C1; Route C3 evaluates four matched current-slot profiles ($00, 10, 01, 11$).
- **Suggested Visual:** Two-panel comparison card (width: 12.0", height: 5.6", background `#FFFFFF`, border `#CBD5E1`): Left: "Route C1 (Unilateral Mover)". Right: "Route C3 Exception (Two-User Coalition Game)". Box text: 20 pt.

---

### Slide 12: Route C1 Role: Focal Opening Net Surplus
- **Teaching Purpose:** Define Route C1's conceptual role: capturing the immediate net surplus of the switching user while accounting for full network energy.
- **Status Tag:** `STABLE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-C1-C3-PAPER-AUTHORING-DELTA-2026-09-01.md` §4
  - `artifacts/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md` §10.13.2
- **Exact Content:**
  - *Title (28 pt):* Route C1 Role: Focal Opening Net Surplus
  - *Body Text (24 pt):*
    - Causal Scope: Focuses on the immediate opening time step ($k=0$) for the switching focal user.
    - Full Energy Accountability: Assigns the entire opening-step system power difference to the focal mover.
    - Hardware Cost Guard: Penalizes handovers that achieve minor rate gains by igniting dormant satellite beams.
- **Suggested Visual:** Concept card with focal user link diagram: Graphic showing switching user connecting to candidate beam, with an electrical meter icon assigning entire satellite RF/circuit delta to that user. Text inside boxes: 20 pt.

---

### Slide 13: Route C1 Target Formulation: Assigning Opening Energy
- **Teaching Purpose:** Present the mathematical definition of the C1 target and explain how the energy assignment operates.
- **Status Tag:** `STABLE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-C1-C3-PAPER-AUTHORING-DELTA-2026-09-01.md` §4
- **Exact Content:**
  - *Title (28 pt):* Route C1 Target Formulation: Assigning Opening Energy
  - *Body Text (24 pt):*
    - Target Equation: Defined by focal rate delta and total network energy delta:
      $$[\text{omml: } \zeta_{1,u} = \Delta t [R_u^C(0) - R_u^M(0)] - \lambda \Delta t [P_C^N(0) - P_M^N(0)]]$$
    - Local Term Equivalence: In coalition game contexts, member 1's local surplus $\ell_1$ reflects this identical net-surplus structure.
    - Causal Bookkeeping: Energy is accounted for once at the opening step and is not duplicated in Route C3.
- **Suggested Visual:** Formula breakdown container (width: 12.0", height: 5.6", background `#EFF6FF`, border `#3B82F6`): Equation centered with callout arrows defining "Focal Rate Term" and "Full System Power Penalty". Text inside callouts: 20 pt.

---

### Slide 14: Route C1 Lineage: The RIS EXP/ACRM Lineage
- **Teaching Purpose:** Explain the heritage of C1: EXP experience sampling and ACRM advantage reference modeling, emphasizing unit safety.
- **Status Tag:** `STABLE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-C1-C3-PAPER-AUTHORING-DELTA-2026-09-01.md` §4
- **Exact Content:**
  - *Title (28 pt):* Route C1 Lineage: The RIS EXP/ACRM Lineage
  - *Body Text (24 pt):*
    - EXP Experience Sampling: Stratified sampling of lower-energy frontier anchors from disjoint TRAIN rollouts.
    - ACRM Advantage Modeling: Evaluates candidate actions against the frozen Main reference baseline.
    - Unit Safety: Implemented as pairwise regression advantage, avoiding corrupted Bellman target units from legacy shaped rewards.
- **Suggested Visual:** Process pipeline diagram: "TRAIN Rollout Data" → "EXP Stratified Sampling" → "Candidate vs. Reference Pairing" → "Normalized Target". Text inside boxes: 20 pt.

---

### Slide 15: Route C1 Historical Evidence: V0.4 Frozen-Policy Margin
- **Teaching Purpose:** Report the historical V0.4 frozen-policy marginal ablation result for Route C1 with strict boundary context.
- **Status Tag:** `STABLE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V04-FIVE-ARM-ABLATION-RESULT-2026-09-01.md`
  - `docs/MULTI-CATFISH-MCRL-C1-C3-PAPER-AUTHORING-DELTA-2026-09-01.md` §4
- **Exact Content:**
  - *Title (28 pt):* Route C1 Historical Evidence: V0.4 Frozen-Policy Margin
  - *Body Text (24 pt):*
    - Frozen-Policy Ablation: Measured under the V0.4 frozen-policy evaluation in the presence of the old Q2 context.
    - Marginal Contribution: FULL vs. DROP-C1 yielded a +254.596% pooled EE margin across 30/30 physical worlds and 3/3 lineages.
    - Boundary Qualification: Confirms C1's marginal indispensability within that ensemble; does not claim the full method beats raw Main.
- **Suggested Visual:** Evidence card (width: 12.0", height: 5.6", background `#F0FDF4`, border `#16A34A`): Header "V0.4 Frozen-Policy Ablation Evidence", displaying +254.596% metric and explicit boundary qualification note. Text inside box: 20 pt.

---

### Slide 16: Route C2 Role: Evaluating Temporal Persistence
- **Teaching Purpose:** Explain the conceptual role of Route C2: accounting for the consequences of handover decisions across subsequent time steps ($k \ge 1$).
- **Status Tag:** `STABLE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V06-C2-K1-PAPER-FIGURE-DELTA-2026-09-02.md` §1–3
- **Exact Content:**
  - *Title (28 pt):* Route C2 Role: Evaluating Temporal Persistence
  - *Body Text (24 pt):*
    - Beyond Step Zero: Handover decisions alter user-satellite associations and loads across subsequent intervals.
    - Ping-Pong Suppression: Identifies actions that yield minor immediate gains but force premature subsequent handovers.
    - Temporal Credit Challenge: As time advances, subsequent actions by other users diffuse the causal impact of the initial choice.
- **Suggested Visual:** Timeline schematic over slots $t$ and $t+1$: Illustrating connection continuity vs. forced premature re-handover at slot $t+1$. Text inside boxes: 20 pt.

---

### Slide 17: Route C2 Evolution: From Temporal-Fork to First-Successor k1
- **Teaching Purpose:** Trace C2 iterations (V0.3 Temporal-Fork hold/release to V0.6 first-successor k1) to explain why research focused on tight horizons.
- **Status Tag:** `STABLE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V06-C2-K1-PAPER-FIGURE-DELTA-2026-09-02.md` §3, §6
  - `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md` §Immediate C2 override
- **Exact Content:**
  - *Title (28 pt):* Route C2 Evolution: From Temporal-Fork to First-Successor k1
  - *Body Text (24 pt):*
    - V0.3 Temporal-Fork (Retired): Multi-step horizon ($H^c=3$) with hold/release mechanisms suffered from divergence and credit leakage.
    - V0.6 First-Successor k1 (Evaluated): Strictly restricted temporal accounting to the first successor offset ($k=1$):
      $$[\text{omml: } \zeta_{2,u} = \Delta t \sum_{i\in\mathcal{U}} [R_i^C(1) - R_i^M(1)] - \lambda \Delta t [P_C^N(1) - P_M^N(1)]]$$
    - Tight Horizon Lesson: Long decentralized multi-step rollouts introduce severe noise; tight 1-step accounting isolates direct causality.
- **Suggested Visual:** Timeline evolution graphic showing V0.3 multi-step hold/release (marked retired) leading to V0.6 1-step offset accounting. Box text: 20 pt.

---

### Slide 18: Route C2 Diagnostic Failures: V0.6 Screen and V0.7 R14 Audit
- **Teaching Purpose:** Present the empirical negative results of V0.6 and V0.7 C2 learner candidates with complete scientific transparency.
- **Status Tag:** `STABLE`
- **Authority Citations:**
  - `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md` §Post-R14 C2 supersession notice, §Immediate C2 override
- **Exact Content:**
  - *Title (28 pt):* Route C2 Diagnostic Failures: V0.6 Screen and V0.7 R14 Audit
  - *Body Text (24 pt):*
    - V0.6 Learner Screen: FULL vs. DROP-C2 produced -28.575% pooled EE with 0/3 positive lineages and a 76.07% action-flip rate.
    - V0.7 R14 Leave-One-Anchor-Out Audit: All three Q2 lineages exhibited higher held-out MSE than the state-independent null predictor.
    - Forensic Cause: Sparse within-state action support caused the network to hallucinate large advantages on out-of-distribution actions.
- **Suggested Visual:** Diagnostic failure summary container (width: 12.0", height: 5.6", background `#FEF2F2`, border `#DC2626`): Displaying -28.575% result, 0/3 pass rate, and action-flip rate metric. Text inside box: 20 pt.

---

### Slide 19: Current C2 Status: Present but Unqualified OPS-3 Diagnostic
- **Teaching Purpose:** State the exact binding authority status of C2 in V0.23: present in the 3-Q architecture as an unqualified diagnostic head, requiring clean-room redesign.
- **Status Tag:** `STABLE`
- **Authority Citations:**
  - `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md` §Post-R14 C2 supersession notice
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` §0 (Hard invariant 5)
  - `artifacts/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md` §10.13.2
- **Exact Content:**
  - *Title (28 pt):* Current C2 Status: Present but Unqualified OPS-3 Diagnostic
  - *Body Text (24 pt):*
    - Structural Presence: In V0.23, $Q_2$ remains present in the deployed three-head sum $Q_1 + Q_2 + Q_3$ as an OPS-3 diagnostic checkpoint.
    - Empirically Unqualified: C2 is currently an unqualified diagnostic head; it is not an active, validated learner candidate.
    - Clean-Room Requirement: Any future C2 learner candidate requires a complete clean-room redesign and pre-registered gate before training.
- **Suggested Visual:** Regulatory status box (width: 12.0", height: 5.6", background `#FFFBEB`, border `#D97706`): Yellow caution banner with lock icon: "Present in Architecture [YES]", "Validated Efficacy [NONE]", "Future Candidate [Clean-Room Redesign Required]". Box text: 20 pt.

---

### Slide 20: The Spatial Externality Problem: Shared Beam Coupling
- **Teaching Purpose:** Explain the spatial externality problem in satellite networks where multiple users share beam bandwidth and interference channels.
- **Status Tag:** `PROVISIONAL_C3_GATE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V023-C3-METHOD-FREEZE-2026-09-05.md` §1
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` §1
- **Exact Content:**
  - *Title (28 pt):* The Spatial Externality Problem: Shared Beam Coupling
  - *Body Text (24 pt):*
    - Resource Contention: Users mapped to the same satellite beam share time-frequency resources, reducing individual rates.
    - Mutual Interference: Adjacent co-channel beams generate cross-tier interference depending on user off-axis angles.
    - Coordinated Migration Benefit: When users migrate off a shared beam, non-focal users experience reduced contention and higher throughput.
- **Suggested Visual:** Multi-user beam coverage diagram showing two users in a shared beam footprint, with interference vectors to neighboring cells. Labels and annotations: 20 pt.

---

### Slide 21: The Beam Extinction Blindspot in Unilateral Exploration
- **Teaching Purpose:** Detail the core motivation for LC-SRS: why single-agent unilateral exploration cannot identify beam de-allocation savings.
- **Status Tag:** `PROVISIONAL_C3_GATE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V023-C3-METHOD-FREEZE-2026-09-05.md` §1
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` §1, §5
- **Exact Content:**
  - *Title (28 pt):* The Beam Extinction Blindspot in Unilateral Exploration
  - *Body Text (24 pt):*
    - Beam Extinction Potential: Completely emptying a satellite beam enables powering down its RF chain, saving substantial base power.
    - Unilateral Exploration Failure: If user 1 explores alone, the beam remains active for user 2; neither user alone sees energy savings.
    - Cooperative Requirement: A two-user cooperative coalition model is required to observe and internalize joint beam de-allocation.
- **Suggested Visual:** 3-step comparison card: Box 1: "Shared Beam Active (Both on beam)". Box 2: "User 1 Moves Alone (Beam remains ON for User 2 -> Zero power saved)". Box 3: "Joint Coalition Move (Both depart -> Beam shuts DOWN -> Power saved!)". Text inside boxes: 20 pt.

---

### Slide 22: The Two-User Cooperative Game: Four Matched Profiles
- **Teaching Purpose:** Detail the four matched current-slot physical profiles ($00, 10, 01, 11$) forming the LC-SRS cooperative game.
- **Status Tag:** `PROVISIONAL_C3_GATE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V023-C3-METHOD-FREEZE-2026-09-05.md` §1
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` §5, §6
  - `artifacts/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md` §10.13.1
- **Exact Content:**
  - *Title (28 pt):* The Two-User Cooperative Game: Four Matched Profiles
  - *Body Text (24 pt):*
    - Four Evaluated Profiles: Evaluated under identical keyed fading across 32 matched draws:
      - $x^0 = 00$: Both members retain reference actions $a_1^0, a_2^0$ on the source beam.
      - $x^1 = 10$: Member 1 moves to designated destination; member 2 stays.
      - $x^2 = 01$: Member 2 moves to designated destination; member 1 stays.
      - $x^c = 11$: Both members migrate simultaneously to designated destinations.
    - Offline Evaluation: Profile evaluation occurs exclusively in the offline training teacher.
- **Suggested Visual:** 2×2 Matrix (width: 12.0", height: 5.6", background `#F8FAFC`, border `#CBD5E1`): Quadrants for 00 (Reference), 10 (Member 1 Move), 01 (Member 2 Move), 11 (Joint Departure with Beam Shut-Off). Text inside quadrants: 20 pt.

---

### Slide 23: Exact Two-Player LC-SRS Teacher Formulation
- **Teaching Purpose:** Present the exact mathematical definitions of the LC-SRS component terms and interaction surplus in the privileged teacher.
- **Status Tag:** `PROVISIONAL_C3_GATE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V023-C3-METHOD-FREEZE-2026-09-05.md` §1
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` §5
  - `artifacts/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md` §10.13.3
- **Exact Content:**
  - *Title (28 pt):* Exact Two-Player LC-SRS Teacher Formulation
  - *Body Text (24 pt):*
    - Component Terms ($i \in \{1, 2\}$):
      $$[\text{omml: } \ell_i = B_i(x^i) - B_i(x^0) - \lambda [E(x^i) - E(x^0)]]$$
      $$[\text{omml: } e_i = \sum_{u\ne i} [B_u(x^i) - B_u(x^0)]]$$
    - Joint Interaction Surplus:
      $$[\text{omml: } \Psi = \Psi_B - \lambda \Psi_E]$$
      where $\Psi_B$ and $\Psi_E$ measure joint-minus-unilateral bit and energy interactions.
- **Suggested Visual:** Structured derivation panel (width: 12.0", height: 5.6", background `#FFFFFF`, border `#003366`) displaying formulas for $\ell_i$, $e_i$, and $\Psi$ with 20 pt annotation callouts explaining physical roles.

---

### Slide 24: Super-Additive Interaction Surplus and the Shapley Target
- **Teaching Purpose:** Explain the Shapley value attribution dividing interaction surplus equally between the two coalition members.
- **Status Tag:** `PROVISIONAL_C3_GATE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V023-C3-METHOD-FREEZE-2026-09-05.md` §1
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` §5
  - `artifacts/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md` §10.13.3
- **Exact Content:**
  - *Title (28 pt):* Super-Additive Interaction Surplus and the Shapley Target
  - *Body Text (24 pt):*
    - Target Formula: User $i$'s C3 target receives its unilateral externality plus half of coalition interaction:
      $$[\text{omml: } z_{3,i} = e_i + \frac{\Psi}{2}]$$
    - Normalized Training Label: Scaled by the common output factor:
      $$[\text{omml: } y_i = \frac{z_{3,i}}{\kappa}]$$
    - Fair Attribution: Shapley sharing guarantees that both members are incentivized to execute the joint departure.
- **Suggested Visual:** Conceptual balance diagram: Bar showing $z_{3,i}$ decomposed into Unilateral Externality ($e_i$) plus Equal Interaction Share ($\Psi / 2$). Text inside graphic: 20 pt.

---

### Slide 25: Construction-Level Exact Identity: Surplus Conservation
- **Teaching Purpose:** Present the construction-level exact identity proving surplus conservation in the two-user game, citing synthetic unit test verification.
- **Status Tag:** `PROVISIONAL_C3_GATE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V023-C3-METHOD-FREEZE-2026-09-05.md` §1
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` §5
  - `tests/test_w181_ee_axis_coalition_residual_c3.py`
- **Exact Content:**
  - *Title (28 pt):* Construction-Level Exact Identity: Surplus Conservation
  - *Body Text (24 pt):*
    - Exact Identity: For the named two-user current-slot game across profiles $00, 10, 01, 11$:
      $$[\text{omml: } \sum_{i=1}^2 (\ell_i + z_{3,i}) = G(x^c) - G(x^0)]$$
    - Construction-Level Proof: Algebraically exact by definition of $\ell_i$, $e_i$, and $\Psi$.
    - Implementation Verification: Bounded synthetic unit-test fixtures (`test_w181`) verify zero numerical residual without overstating raw simulator proof.
- **Suggested Visual:** Green spotlight container (width: 12.0", height: 5.6", background `#F0FDF4`, border `#16A34A`): Highlighting the summation equation in large OfficeMath format with verification stamp and test citation. Text inside box: 20 pt.

---

### Slide 26: The Teacher Anchor Surface: Supported, Reference, and Control
- **Teaching Purpose:** Detail the tri-class anchor surface partition ($S_h, R_h, C_h$) that prevents label contamination.
- **Status Tag:** `PROVISIONAL_C3_GATE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` §3.3, §5
  - `artifacts/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md` §10.13.3
- **Exact Content:**
  - *Title (28 pt):* The Teacher Anchor Surface: Supported, Reference, and Control
  - *Body Text (24 pt):*
    - Supported Cells ($S_h$): Validated two-member designated moves; assigned mean 32-draw label $\bar{y}_r$.
    - Reference Cells ($R_h$): Detached reference action $a_i^0$ of each user; ground truth is identically zero.
    - Control Cells ($C_h$): Legal non-supported actions; ground truth is identically zero.
- **Suggested Visual:** User × Action matrix grid layout (width: 12.0", height: 5.6", background `#FFFFFF`, border `#CBD5E1`): Color-coded cells showing Supported (Green), Reference Zeros (Blue), and Control Zeros (Gray). Text inside matrix: 20 pt.

---

### Slide 27: Deployment C3View: Committed vs. Detached Context
- **Teaching Purpose:** Describe the predecision C3View observation consumed by Q3, separating committed context from detached reference context.
- **Status Tag:** `PROVISIONAL_C3_GATE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` §3.1
  - `artifacts/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md` §10.13.4
- **Exact Content:**
  - *Title (28 pt):* Deployment C3View: Committed vs. Detached Context
  - *Body Text (24 pt):*
    - Committed Context: Physical environment parameters already committed at previous step (load, power, active satellites).
    - Detached Reference Context: Reference action profile $a^0 = \arg\max(Q_1 + Q_2)$ evaluated in inference mode.
    - Zero Privilege Leakage: Contains zero teacher fading realizations, profile outcomes, or future state information.
- **Suggested Visual:** Dual-namespace tensor block diagram: Left box "Committed Context (Physical Past)". Right box "Detached Context (Combinatorial Baseline)". Causal boundary shield icon between them. Text inside boxes: 20 pt.

---

### Slide 28: Relational Token Architecture: Shared 67-64-64-1 Scorer
- **Teaching Purpose:** Detail the neural network architecture of Q3: concatenation of action-context with relational tokens and processing through an MLP.
- **Status Tag:** `PROVISIONAL_C3_GATE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` §3.3
  - `artifacts/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md` §10.13.4
- **Exact Content:**
  - *Title (28 pt):* Relational Token Architecture: Shared 67-64-64-1 Scorer
  - *Body Text (24 pt):*
    - Input Representation: Action context $c_{ia} \in \mathbb{R}^{29}$ concatenated with token $t_{iar} \in \mathbb{R}^{38}$ to form a 67-dim input.
    - Shared Token Scorer: Multi-layer perceptron $f_\theta: \mathbb{R}^{67} \to 64_{\text{ReLU}} \to 64_{\text{ReLU}} \to 1$.
    - Masked Accumulation: Aggregates token scores under mask $F_i(a) = \sum_{r: m_{iar}=1} f_\theta(c_{ia}, t_{iar})$.
- **Suggested Visual:** Neural architecture flow: `[Context (29)]` + `[Token (38)]` → Concatenator (67) → Linear(64) → ReLU → Linear(64) → ReLU → Linear(1) → Masked Sum $\Sigma \to F_i(a)$. Text inside boxes: 20 pt.

---

### Slide 29: Reference-Centering: Enforcing the Structural Zero Invariant
- **Teaching Purpose:** Present the reference-centering operator $Q_{3,i}(a) = F_i(a) - F_i(a_i^0)$ that mathematically pins reference action output to zero.
- **Status Tag:** `PROVISIONAL_C3_GATE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` §3.3
  - `artifacts/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md` §10.13.4
- **Exact Content:**
  - *Title (28 pt):* Reference-Centering: Enforcing the Structural Zero Invariant
  - *Body Text (24 pt):*
    - Reference Centering Operator: Defined as:
      $$[\text{omml: } Q_{3,i}(a) = F_i(a) - F_i(a_i^0)]$$
    - Invariant Guarantee: Ensures $Q_{3,i}(a_i^0) \equiv 0$ identically for any parameter weights $\theta$, eliminating network baseline drift.
    - Scalar Deployment Surface: Outputs a standard scalar surface $(U, 28)$ with zero structural offset.
- **Suggested Visual:** Graphic illustrating raw uncentered score $F_i(a)$ subtracting reference baseline $F_i(a_i^0)$, pinning reference output exactly to 0 on the vertical axis. Text inside graphic: 20 pt.

---

### Slide 30: Pairwise Advantage Learning: Zero-Bootstrap Loss
- **Teaching Purpose:** Explain the loss function used for pairwise advantage regression on Routes C1 and C2 with numerical gauge regularizer.
- **Status Tag:** `STABLE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-C1-C3-PAPER-AUTHORING-DELTA-2026-09-01.md` §7
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` §3.3
- **Exact Content:**
  - *Title (28 pt):* Pairwise Advantage Learning: Zero-Bootstrap Loss
  - *Body Text (24 pt):*
    - Pairwise Objective (Routes $C_1, C_2$): Trained on normalized advantage differences:
      $$[\text{omml: } \ell_j = w_j \left( \left[ Q_j(s_{j,u}, a_u^C) - Q_j(s_{j,u}, a_u^M) - \frac{\zeta_{j,u}}{\kappa} \right]^2 + \beta Q_j(s_{j,u}, a_u^M)^2 \right)]$$
    - Gauge Regularizer: Numerical gauge $\beta = 0.1$ anchors reference predictions without altering preference ordering.
    - Loss Normalization: Weights $w_j$ normalize loss scale during training; deployment weights remain strictly unity.
- **Suggested Visual:** Mathematical panel container (width: 12.0", height: 5.6", background `#FFFFFF`, border `#CBD5E1`): Displaying pairwise equation with callout boxes highlighting "Advantage Error" and "Gauge Penalty". Text inside callouts: 20 pt.

---

### Slide 31: Class-Balanced Tri-Partite Loss for LC-SRS
- **Teaching Purpose:** Present the class-balanced loss function for Route C3 that prevents majority-class collapse across S, R, and C classes.
- **Status Tag:** `PROVISIONAL_C3_GATE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` §3.3
- **Exact Content:**
  - *Title (28 pt):* Class-Balanced Tri-Partite Loss for LC-SRS
  - *Body Text (24 pt):*
    - Tri-Partite Loss Formulation: Balanced over Supported, Reference, and Control classes:
      $$[\text{omml: } L_3 = \operatorname{mean}_h \left\{ \operatorname{mean}_{r\in S_h} [Q_3(r) - \bar{y}_r]^2 + \operatorname{mean}_{r\in R_h} Q_3(r)^2 + \operatorname{mean}_{r\in C_h} Q_3(r)^2 \right\}]$$
    - Balanced Batch Sampling: Optimizer draws anchors and classes uniformly with replacement, scaling sampled errors by 3.
    - Collapse Prevention: Equal class weighting prevents sparse Supported cells from being overwhelmed by Control zeros.
- **Suggested Visual:** 3-pillar diagram representing Supported ($S_h$), Reference ($R_h$), and Control ($C_h$) classes with equal 1/3 weighting arrows feeding into total loss $L_3$. Text inside boxes: 20 pt.

---

### Slide 32: One-Pass Deployment: Native Masked Argmax
- **Teaching Purpose:** Describe the single-pass decentralized deployment seam: unweighted sum of the three Q heads under the native safe mask.
- **Status Tag:** `STABLE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` §0 (Hard invariant 3)
  - `docs/MULTI-CATFISH-MCRL-C1-C3-PAPER-AUTHORING-DELTA-2026-09-01.md` §7
  - `artifacts/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md` §10.13.1
- **Exact Content:**
  - *Title (28 pt):* One-Pass Deployment: Native Masked Argmax
  - *Body Text (24 pt):*
    - Additive Deployment Score: Direct unweighted sum across the three independent Q surfaces:
      $$[\text{omml: } \Phi_u(t, a) = Q_1(s_u(t), a) + Q_2(s_u(t), a) + Q_3(s_u(t), a)]$$
    - Action Execution: Single argmax filtered by native service-safe mask $\mathcal{A}_u^+(t)$:
      $$[\text{omml: } a_u^\star(t) = \arg\max_{a\in\mathcal{A}_u^+(t)} \Phi_u(t, a)]$$
    - Single Executed Decision: Exactly one Main action executes per ground user without coordination rounds.
- **Suggested Visual:** Clean execution pipeline: Three parallel Q heads feed an unweighted summer $\Sigma \to \Phi_u(t, a)$, through filter gate $\mathcal{A}_u^+(t)$, to an $\arg\max$ operator emitting $a_u^\star(t)$. Text inside boxes: 20 pt.

---

### Slide 33: Runtime Invariants: Prohibited Coordination Mechanisms
- **Teaching Purpose:** Explicitly detail prohibited runtime mechanisms to dispel any misconception that Multi-Catfish MCRL uses multi-agent coordination.
- **Status Tag:** `STABLE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` §0 (Hard invariant 4)
  - `docs/MULTI-CATFISH-MCRL-V03-ALGORITHM-SPEC-2026-08-31.md` §2, §7
- **Exact Content:**
  - *Title (28 pt):* Runtime Invariants: Prohibited Coordination Mechanisms
  - *Body Text (24 pt):*
    - Strictly Prohibited at Deployment:
      - NO runtime coordinator, auction, bidding, or tokens.
      - NO voting, consensus rounds, or joint action decoders.
      - NO multi-agent communication or iterative negotiation.
      - NO post-selection repair, fallback rules, or heuristic overrides.
    - Offline Complexity, Online Simplicity: Multi-causal reasoning occurs in offline training; runtime inference remains purely local and decentralized.
- **Suggested Visual:** 4-box red-bordered warning layout (each box width: 5.8", height: 2.6", background `#FEF2F2`, border `#DC2626`) showing prohibited mechanisms with red prohibition icons. Text inside boxes: 20 pt.

---

### Slide 34: Method Safeguards: Native Masks and Propensity Strata
- **Teaching Purpose:** Detail the experimental and runtime safeguards: native feasibility masks, service non-inferiority guards, and matched-placebo strata.
- **Status Tag:** `STABLE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` §2.1, §7
- **Exact Content:**
  - *Title (28 pt):* Method Safeguards: Native Masks and Propensity Strata
  - *Body Text (24 pt):*
    - Native Safe Mask $\mathcal{A}_u^+(t)$: Prunes geometrically infeasible beams and power over-allocation before scoring.
    - Service Non-Inferiority Guard: Rejects policies that degrade served fraction or minimum user rate relative to Main.
    - Matched-Placebo Strata: Permutes targets within propensity strata to verify true action-specific learning over baseline propensity.
- **Suggested Visual:** 3-card horizontal grid (each card width: 3.8", height: 5.6", background `#F8FAFC`, border `#94A3B8`). Left: "Native Safe Mask". Center: "Service Non-Inferiority". Right: "Matched Placebo Control". Text inside cards: 20 pt.

---

### Slide 35: Active V0.23 Development Gate: Four Evaluation Arms
- **Teaching Purpose:** Present the four evaluation arms of the active V0.23 development gate from contract sections 11–14.
- **Status Tag:** `PROVISIONAL_C3_GATE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` §11–14
- **Exact Content:**
  - *Title (28 pt):* Active V0.23 Development Gate: Four Evaluation Arms
  - *Body Text (24 pt):*
    - Gate Protocol Arms (8 TRAIN worlds, 3 student seeds, 48 fits):
      - `INFORMED`: Student trained on genuine LC-SRS targets with class-balanced loss.
      - `MATCHED_PLACEBO`: Student trained on within-stratum permuted targets.
      - `ZERO_SURFACE`: Reference baseline where $Q_3 \equiv 0$ everywhere.
      - `TEACHER_ORACLE`: Privileged sparse teacher surface for literal one-pass composition benchmark.
    - Scope Clarification: This is an offline observability gate, NOT episode training or policy efficacy evaluation.
- **Suggested Visual:** 4-column arm specification table (width: 12.0", height: 5.6", background `#FFFFFF`, border `#003366`) detailing data source, loss function, and evaluation role for each of the four gate arms. Text inside table: 20 pt.

---

### Slide 36: Active V0.23 Development Gate: Pre-Registered Passing Criteria
- **Teaching Purpose:** Detail the comprehensive pre-registered passing criteria from Section 12 of the V0.23 gate contract.
- **Status Tag:** `PROVISIONAL_C3_GATE`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` §12
- **Exact Content:**
  - *Title (28 pt):* Active V0.23 Development Gate: Pre-Registered Passing Criteria
  - *Body Text (24 pt):*
    - Core Passing Predicates:
      - Coverage: $\ge 24$ closure-eligible pairs across 8 worlds, $\ge 1$ per world.
      - Learner Generalization: Informed Spearman $\ge 0.20$, sign accuracy $\ge 0.60$, informed strictly exceeds placebo in $\ge 6/8$ worlds.
      - Composition & Service: Literal 11 adoption $\ge 25\%$, topology consistency $\ge 80\%$, service non-inferiority passed in all worlds.
    - Discrete Precedence: Emits exact token `GO_FIXED_LEARNER_SCREEN_CONTRACT` only if all predicates pass.
- **Suggested Visual:** Checklist container (width: 12.0", height: 5.6", background `#F8FAFC`, border `#003366`) with organized sections for "Pair Coverage", "Learner Metrics", and "Composition Predicates". Text inside boxes: 20 pt.

---

### Slide 37: Historical vs. Future Evaluation: The Multi-Arm Matrix
- **Teaching Purpose:** Clearly separate the historical V0.4 and future full-policy multi-arm matrix (M0, N000, A011, A101, A110, F111) from the active V0.23 gate.
- **Status Tag:** `RESULTS_PENDING`
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V03-ALGORITHM-SPEC-2026-08-31.md` §8
  - `docs/MULTI-CATFISH-MCRL-V04-FIVE-ARM-ABLATION-RESULT-2026-09-01.md`
- **Exact Content:**
  - *Title (28 pt):* Historical vs. Future Evaluation: The Multi-Arm Matrix
  - *Body Text (24 pt):*
    - Multi-Arm Evaluation Protocol: Designed for full episode-level policy evaluation:
      - `M0`: Frozen Main baseline; `N000`: Neutral control.
      - `A011` (DROP-C1), `A101` (DROP-C2), `A110` (DROP-C3): Leave-one-out marginal tests.
      - `F111`: Full Multi-Catfish ensemble.
    - Strict Distinction: This multi-arm matrix is NOT the active V0.23 gate; it belongs to historical V0.4 and future episode training.
- **Suggested Visual:** 6-row comparison matrix table (width: 12.0", height: 5.6", background `#FFFFFF`, border `#CBD5E1`) listing arms, source configurations, and roles, with prominent banner: "Framework for Future Full-Policy Evaluation". Text inside table: 20 pt.

---

### Slide 38: Scientific Claim Ceiling: Development Gate Boundary
- **Teaching Purpose:** Conclude with an unambiguous scientific claim ceiling, explicitly listing verified method facts, development boundaries, and prohibited claims.
- **Status Tag:** `STABLE`
- **Authority Citations:**
  - `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md` §Post-R14 C2 supersession notice
  - `docs/MULTI-CATFISH-MCRL-V023-C3-METHOD-FREEZE-2026-09-05.md` §Claim ceiling
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-LAUNCH-DECISION-2026-09-05.md`
- **Exact Content:**
  - *Title (28 pt):* Scientific Claim Ceiling: Development Gate Boundary
  - *Body Text (24 pt):*
    - Frozen Method Facts: Canonical ratio-of-sums EE, exact two-player LC-SRS identity, 3-Q architecture, and one-pass masked argmax.
    - Scope of Current Authority: The active launch decision authorizes ONLY the V0.23 offline development gate on the Ubuntu server.
    - Enforced Claim Ceilings: Does NOT authorize C2 redesign, episode training, 100 to 9000 episode runs, TEST split, or policy efficacy claims.
- **Suggested Visual:** Dual-card synthesis panel (width: 12.0", height: 5.6"): Left card (Green border `#16A34A`) "Established Method Core". Right card (Amber border `#D97706`) "Enforced Claim Ceilings & Future Milestones". Text inside cards: 20 pt.
