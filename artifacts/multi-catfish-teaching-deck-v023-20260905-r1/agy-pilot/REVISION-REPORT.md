# Multi-Catfish MCRL Teaching Deck: V0.23 Planning Revision Report

- **Report ID:** `v023-teaching-deck-revision-20260905-r2`
- **Audit Disposition Addressed:** `REVISE_BEFORE_PPTX`
- **Working Directory:** `/home/u24/papers/mcrl-leo-handover`
- **Ownership Scope:** Strictly confined to `artifacts/multi-catfish-teaching-deck-v023-20260905-r1/agy-pilot/`
- **Non-Execution Invariant:** Zero simulator runs, zero neural network training, zero test split evaluations, zero PPTX assembly.

---

## 1. Executive Summary & Status Transition

A rigorous, systematic revision of all teaching-deck planning artifacts has been completed. All 12 specific audit directives returned in the `REVISE_BEFORE_PPTX` finding have been addressed and validated. The planning package is now fully aligned with:
1. `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md`
2. `docs/MULTI-CATFISH-MCRL-V023-C3-METHOD-FREEZE-2026-09-05.md`
3. `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md`
4. `artifacts/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md` §10.13
5. `artifacts/chinese-word-v023-lcsrs-20260905-r2/SYMBOL-COLLISION-AND-SINGLE-LETTER-AUDIT.md`

### Artifact Inventory
| File | Status | Key Updates Applied |
|:---|:---:|:---|
| `STORYBOARD.md` | **COMPLIANT** | Expanded to 38 slides; strictly 28 pt title, 24 pt body, 20 pt box text; visual plan for every slide. |
| `SCIENCE-CLAIM-MAP.md` | **COMPLIANT** | Separated active vs. historical identities; C2 OPS-3 diagnostic status; V0.23 gate arms; synthetic fixture citation. |
| `MATH-TOKEN-INVENTORY.json` | **COMPLIANT** | 38 slides covered; zero ASCII control characters; zero forbidden multi-letter subscripts; clean `\\arg\\max`. |
| `PILOT-SLIDE-SPEC.md` | **COMPLIANT** | Slide 23 spec; strictly 28 pt title, 24 pt body, 20 pt box text; cited contract §5 and `test_w181` synthetic fixture. |
| `CORE-FLOW-DRAFT.svg` | **COMPLIANT** | Valid XML; font sizes strictly 28px, 24px, 20px; C2 OPS-3 diagnostic badge; LC-SRS exact identity. |
| `REVISION-REPORT.md` | **COMPLIANT** | Comprehensive traceability mapping for all 12 audit items across all files. |

---

## 2. Detailed Traceability Mapping: The 12 Audit Directives

### Directive 1: Removal of V0.3 Three-Route Bookkeeping from Active Method
- **Requirement:** Remove V0.3 retired three-route bookkeeping ($\zeta_1+\zeta_3+\zeta_2=g_0+g_1$, $D^o/D^t/D^a$) as a current method. The only active exact conservation identity is the named two-user current-slot LC-SRS identity $\sum_{i=1}^2 (\ell_i + z_{3,i}) = G(x^c) - G(x^0)$, bounded to that game.
- **Implementations:**
  - `STORYBOARD.md`: Slides 9, 23, 25 explicitly present the two-user LC-SRS conservation identity as the sole active identity. Slide 37 and 38 mark V0.3 additive bookkeeping as strictly historical.
  - `SCIENCE-CLAIM-MAP.md` §1.3: Defines the two-user LC-SRS identity as the only active exact identity. Explicitly notes V0.3 three-route bookkeeping is retired and historical.
  - `MATH-TOKEN-INVENTORY.json`: Removed all active occurrences of $\zeta_1, \zeta_2, \zeta_3$ and $D^o, D^t, D^a$. Active formulas use $\ell_i, e_i, \Psi, z_{3,i}, y_i$.
  - `CORE-FLOW-DRAFT.svg`: Replaced the old non-overlapping bookkeeping banner with the active exact two-user LC-SRS conservation identity banner.
  - `PILOT-SLIDE-SPEC.md` §3: Box 2.2 defines the active exact identity $\sum_{i=1}^2 (\ell_i + z_{3,i}) = G(x^c) - G(x^0)$.

### Directive 2: Accurate C2 Status (OPS-3 Diagnostic, Present but Unqualified)
- **Requirement:** Old V0.7 learner candidate is retired; current V0.23 context contains the current OPS-3 diagnostic/checkpoint, present in the 3-Q architecture but unqualified, not redesigned or retired. Zero C2 efficacy claim.
- **Implementations:**
  - `STORYBOARD.md`: Slide 8 establishes $Q_2$ is present as an independent head; Slide 18 details V0.6/V0.7 diagnostic screens; Slide 19 explicitly defines C2 as `PRESENT_BUT_UNQUALIFIED_OPS3_DIAGNOSTIC`.
  - `SCIENCE-CLAIM-MAP.md` §1.6, §2.4, §5.2, §6: Formulates C2 status as present in the 3-Q sum as the current OPS-3 diagnostic/checkpoint, but unqualified. Prohibits claiming C2 is solved, confirmed, or has efficacy.
  - `CORE-FLOW-DRAFT.svg`: C2 box and top badge labeled "C2: OPS-3 DIAGNOSTIC (PRESENT BUT UNQUALIFIED, ZERO EFFICACY CLAIMED)".
  - `MATH-TOKEN-INVENTORY.json`: Slide 18 and 19 list formulas for C2 OPS-3 diagnostic and screen outcomes.

### Directive 3: Restriction of C3 to Two-User Coalition Game on 4 Matched Profiles
- **Requirement:** Do not describe active C3 as a general unilateral candidate/reference branch; it is a two-user coalition game on 4 matched profiles ($00, 10, 01, 11$). Restrict unilateral candidate/reference branches to C1.
- **Implementations:**
  - `STORYBOARD.md`: Slide 10 restricts unilateral counterfactuals to C1. Slides 11, 20, 21, 22, 23 explicitly formulate C3 as a two-user coalition game over profiles $00, 10, 01, 11$.
  - `SCIENCE-CLAIM-MAP.md` §1.4: Explicitly declares active Route C3 as strictly a two-user coalition game over 4 matched profiles, restricting unilateral branches to C1.
  - `PILOT-SLIDE-SPEC.md` §1, §3: Describes the 4 physical profiles evaluated offline under matched fading draws.
  - `CORE-FLOW-DRAFT.svg`: Section 1 C3 block explicitly specifies "Four Matched Profiles: 00, 10, 01, 11 (32 Fading Draws)".

### Directive 4: Qualification of Historical V0.4 C1/C3 Empirical Numbers
- **Requirement:** Describe V0.4 numbers strictly as V0.4 frozen-policy, old-Q2 context, marginal contribution only; remove words like "massive gains" or "confirmed efficacy".
- **Implementations:**
  - `STORYBOARD.md`: Slide 15 and Slide 37 explicitly label V0.4 results (+254.6% for C1; +21.2% confirmatory and +22.0% five-arm for C3) as frozen-policy marginal contributions in an old-Q2 context. Words like "massive gains" or "proven policy" were eliminated.
  - `SCIENCE-CLAIM-MAP.md` §2.1, §2.2: Documents C1 and C3 numbers with strict boundaries: marginal contribution only, evaluated in the presence of the old Q2 head. Prohibits merging or averaging C3 confirmatory and five-arm blocks.

### Directive 5: Enforcement of Active V0.23 Development Gate Arms and Separation
- **Requirement:** Active V0.23 gate arms are strictly `INFORMED`, `MATCHED_PLACEBO`, `ZERO_SURFACE`, `TEACHER_ORACLE` with frozen criteria from contract §§11–14; separate from historical/future multi-arm evaluation matrix ($M0, N000, A011, A101, A110, F111$).
- **Implementations:**
  - `STORYBOARD.md`: Slide 35 dedicated to the 4 active V0.23 development gate arms; Slide 36 dedicated to contract §§11–14 criteria; Slide 37 dedicated to separating the gate from the multi-arm matrix ($M0, N000, A011, A101, A110, F111$).
  - `SCIENCE-CLAIM-MAP.md` §3: Details the 4 active gate arms and contract passing criteria (§§11–14). Explicitly separates them from the multi-arm evaluation matrix.
  - `MATH-TOKEN-INVENTORY.json`: Slides 35, 36, 37 separate gate arms from evaluation matrix.

### Directive 6: Repair of MATH-TOKEN-INVENTORY.json
- **Requirement:** Remove BEL (`\x07`) corruption in argmax, remove $N_{\text{pairs}}$ and any multi-letter math subscripts/superscripts, remove retired $\zeta$ and $D^o/D^t/D^a$ tokens. Zero ASCII control characters except whitespace.
- **Implementations:**
  - `MATH-TOKEN-INVENTORY.json`:
    - Replaced all raw command escapes with `\\arg\\max`, completely eliminating BEL (`\x07`) control characters.
    - Replaced $N_{\text{pairs}}$ with atomic notation $N_{\mathrm{p}}$ or $N_p$.
    - Automated validator confirmed zero forbidden multi-letter subscripts across the entire JSON file.
    - Automated validator confirmed zero ASCII control characters (only `\n`, `\t`, `\r` present).
    - Mapped all 38 slides with validated OMML and atomic subscripts.

### Directive 7: Correction of Pilot Citation for Conservation Identity
- **Requirement:** `test_w184` does not prove identity. `test_w181` tests it on a synthetic fixture, not raw simulator traces. Describe identity as construction-level exact by definition and cite contract §5 and `test_w181`.
- **Implementations:**
  - `STORYBOARD.md`: Slide 25 states the identity is construction-level exact by mathematical definition and cites contract §5 and synthetic fixture `test_w181`.
  - `SCIENCE-CLAIM-MAP.md` §1.3: Cites contract §5 and unit test `test_w181` on a synthetic fixture (residual $< 10^{-6}$ bit), not on raw simulator traces.
  - `PILOT-SLIDE-SPEC.md` §3 (Box 2.2): Authority citation explicitly corrected from `test_w184` to contract §5 and synthetic fixture `test_w181`.
  - `CORE-FLOW-DRAFT.svg`: Section 1 identity box cites synthetic fixture `test_w181`.

### Directive 8: Strict Typographic Invariants (28 pt Title, 24 pt Body, 20 pt Box Text)
- **Requirement:** Enforce user typography exactly: Times New Roman throughout; slide titles 28 pt; ordinary body text 24 pt; text inside diagrams/cards/boxes 20 pt. Strictly NO 26, 22, 18, 16, 14 pt text.
- **Implementations:**
  - `STORYBOARD.md`: Every slide explicitly annotates: `Title (28 pt Bold)`, `Body Text (24 pt)`, `Box / Card Text (20 pt)`. Zero prohibited sizes.
  - `PILOT-SLIDE-SPEC.md`: Header and coordinates specify 28 pt title, 24 pt body, 20 pt box/badge text. Removed all 26, 22, 18, 16, 14 pt references.
  - `CORE-FLOW-DRAFT.svg`: CSS font-size classes updated to strictly 28px (`.font-title`), 24px (`.font-section`), and 20px (`.font-box-title`, `.font-box-body`, `.font-box-sub`, `.font-badge`). Regex scan verified zero other font sizes.
  - `MATH-TOKEN-INVENTORY.json`: Metadata documents the typographic invariant.

### Directive 9: Removal of Unsupported Empirical Claims
- **Requirement:** Remove sub-millisecond runtime, less-than-10-degree elevation, and prove-causal-learning claims.
- **Implementations:**
  - `CORE-FLOW-DRAFT.svg`: Removed "Computes in sub-millisecond time"; replaced with "One forward pass per candidate action".
  - `STORYBOARD.md` & `SCIENCE-CLAIM-MAP.md` §5: Sub-millisecond runtime, $<10^\circ$ elevation, and proving causal learning are explicitly cataloged as Prohibited Claims (Items 9, 10, 11).

### Directive 10: Launch Authority Boundaries (Development Gate Only)
- **Requirement:** Launch authority authorizes only V0.23 development gate; no episode training (100–9000), no TEST split, no efficacy.
- **Implementations:**
  - `STORYBOARD.md`: Slides 35, 36, 38 bound the work to the offline development gate on 8 fresh TRAIN worlds.
  - `SCIENCE-CLAIM-MAP.md` §5, §6: Formally lists claims of TEST split evaluation or episode training (100–9000 episodes) as forbidden until formal authorization.

### Directive 11: Strict Method Naming Convention
- **Requirement:** Method name is strictly *Multi-Catfish MCRL*; do NOT expand MCRL as "Multi-Causal Reinforcement Learning".
- **Implementations:**
  - `STORYBOARD.md`: Slide 1 title and text updated to *Multi-Catfish MCRL: Teaching Deck Overview*. Acronym expansion removed everywhere.
  - `SCIENCE-CLAIM-MAP.md`: Core principle explicitly states the method name is strictly *Multi-Catfish MCRL*; expansion forbidden in §5.12.
  - `MATH-TOKEN-INVENTORY.json`: Slide 1 title and metadata updated to *Multi-Catfish MCRL*.
  - `CORE-FLOW-DRAFT.svg`: Uses strictly *Multi-Catfish MCRL*.

### Directive 12: Expansion to 38 Slides with Unrestricted Page Count
- **Requirement:** Page count unrestricted. Split crowded slides with 24 pt body text into 38 slides. Every slide needs a visual plan.
- **Implementations:**
  - `STORYBOARD.md`: Fully developed across 38 distinct slides. Every slide contains:
    1. Title & Cadence
    2. Status Tag (`STABLE`, `PROVISIONAL_C3_GATE`, `RESULTS_PENDING`)
    3. Content Structure (28 pt Title, 24 pt Body, 20 pt Box Text)
    4. Exact Math & Symbol Callouts (Atomic indices)
    5. Visual Plan (Geometry, card containers, color palettes, visual hierarchy)
  - `MATH-TOKEN-INVENTORY.json`: Contains 38 corresponding entries matching `STORYBOARD.md`.

---

## 3. Comprehensive 38-Slide Master Structure

| # | Slide Title | Status Tag | Visual Layout Archetype |
|:---:|:---|:---:|:---|
| 1 | Multi-Catfish MCRL: Teaching Deck Overview | `STABLE` | Header banner + 3 architecture pillar cards |
| 2 | LEO Satellite Network Context: Orbital Dynamics & Narrow Beams | `STABLE` | Side-by-side: orbital geometry schematic vs. beam characteristics |
| 3 | Coupled Satellite Resources: Beam Power & Ground Interference | `STABLE` | Split card: DC base power equation vs. SINR interference coupling |
| 4 | Limits of Conventional Multi-Objective Handover: The MODQN Dilemma | `STABLE` | Comparative 2-column: scalarized weighting failure vs. physical trade-off |
| 5 | The Canonical Endpoint: Network Ratio-of-Sums Energy Efficiency | `STABLE` | Hero spotlight box (canonical $\eta^N$) vs. counter-example card |
| 6 | Linear Surplus Formulation and the Frozen Multiplier | `STABLE` | Equation container ($\lambda, G(x)$) + first-order equivalence card |
| 7 | The Causal Attribution Dilemma in Multi-User Handover | `STABLE` | Multi-user temporal trace diagram with conflicting credit highlights |
| 8 | Architecture Invariant: Three Independent Q Networks | `STABLE` | 3-column architecture diagram: independent parameter backbones |
| 9 | Architecture Invariant: Route-Local Zero-Bootstrap Training | `STABLE` | Side-by-side: supervised target flow vs. zero-bootstrap stability card |
| 10 | Unilateral Counterfactual Evaluation: The C1 Opening Intervention | `STABLE` | Intervention timeline: focal user candidate vs. reference profile |
| 11 | The Coalition Exception: Why C3 Breaks Unilateral Symmetry | `STABLE` | 2x2 profile grid showing zero unilateral saving vs. joint beam shut-off |
| 12 | Route C1 Role: Focal Opening Net Surplus | `STABLE` | Card flow: focal rate gain minus network step-0 power penalty |
| 13 | Route C1 Target Formulation: Assigning Opening Energy | `STABLE` | Formula card ($y_{1,u}$) with component breakdown annotations |
| 14 | Route C1 Lineage: The RIS EXP/ACRM Lineage | `STABLE` | Lineage progression flow: from initial heuristic to principled counterfactual |
| 15 | Route C1 Historical Evidence: V0.4 Frozen-Policy Margin | `STABLE` | Empirical evidence table (+254.6% EE) with strict marginal-only boundary |
| 16 | Route C2 Role: Evaluating Temporal Persistence | `STABLE` | Temporal branch schematic: evaluation at successor offset $k=1$ |
| 17 | Route C2 Evolution: From Temporal-Fork to First-Successor k1 | `STABLE` | Evolutionary step diagram: simplifying multi-step rollout to $k=1$ |
| 18 | Route C2 Diagnostic Failures: V0.6 Screen and V0.7 R14 Audit | `STABLE` | Diagnostic failure card: -28.6% screen and 0/3 LOAO generalization failure |
| 19 | Current C2 Status: Present but Unqualified OPS-3 Diagnostic | `STABLE` | Amber warning callout: present in 3-Q architecture but unqualified |
| 20 | The Spatial Externality Problem: Shared Beam Coupling | `STABLE` | Satellite footprint diagram: two ground users under single shared spot beam |
| 21 | The Beam Extinction Blindspot in Unilateral Exploration | `STABLE` | 4-quadrant state diagram: profiles 00, 10, 01 keep beam on; 11 extinguishes |
| 22 | The Two-User Cooperative Game: Four Matched Profiles | `PROVISIONAL_C3_GATE` | 2x2 combinatorial matrix card ($x^0, x^1, x^2, x^c$) with 32 fading draws |
| 23 | Exact Two-Player LC-SRS Teacher Formulation | `PROVISIONAL_C3_GATE` | Dual-panel layout: local terms & $\Psi$ on left; Shapley target on right |
| 24 | Super-Additive Interaction Surplus and the Shapley Target | `PROVISIONAL_C3_GATE` | Cooperative game theory diagram: Shapley value decomposition |
| 25 | Construction-Level Exact Identity: Surplus Conservation | `PROVISIONAL_C3_GATE` | Hero spotlight box: $\sum(\ell_i + z_{3,i}) = \Delta G$; residual $< 10^{-6}$ bit |
| 26 | The Teacher Anchor Surface: Supported, Reference, and Control | `PROVISIONAL_C3_GATE` | 3-tier strata cards: Supported ($S$), Reference ($R$), Control ($C$) |
| 27 | Deployment C3View: Committed vs. Detached Context | `PROVISIONAL_C3_GATE` | Two-phase flow: detached spatial anchor $a^0$ feeding deployable C3View |
| 28 | Relational Token Architecture: Shared 67-64-64-1 Scorer | `PROVISIONAL_C3_GATE` | Neural network block diagram: 29-dim context + 38-dim tokens to MLP |
| 29 | Reference-Centering: Enforcing the Structural Zero Invariant | `PROVISIONAL_C3_GATE` | Invariant proof card: $Q_3(a) = F(a) - F(a^0) \implies Q_3(a^0) \equiv 0$ |
| 30 | Pairwise Advantage Learning: Zero-Bootstrap Loss | `PROVISIONAL_C3_GATE` | Supervised regression diagram: offline batch targets with $\gamma_b=0$ |
| 31 | Class-Balanced Tri-Partite Loss for LC-SRS | `PROVISIONAL_C3_GATE` | Loss weighting diagram: $1/3 \mathcal{L}_S + 1/3 \mathcal{L}_R + 1/3 \mathcal{L}_C$ |
| 32 | One-Pass Deployment: Native Masked Argmax | `STABLE` | Deployment pipeline: direct 3-Q sum $\to$ native mask $\to$ single argmax |
| 33 | Runtime Invariants: Prohibited Coordination Mechanisms | `STABLE` | Red-line barrier diagram: strict prohibitions on brokers, tokens, voting |
| 34 | Method Safeguards: Native Masks and Propensity Strata | `STABLE` | Double barrier card: physical feasibility mask + propensity weighting |
| 35 | Active V0.23 Development Gate: Four Evaluation Arms | `PROVISIONAL_C3_GATE` | 4-column experimental protocol: `INFORMED`, `PLACEBO`, `ZERO`, `ORACLE` |
| 36 | Active V0.23 Development Gate: Pre-Registered Passing Criteria | `PROVISIONAL_C3_GATE` | Checklist card: $\ge 24$ pairs, zero reference MSE, positive skill |
| 37 | Historical vs. Future Evaluation: The Multi-Arm Matrix | `RESULTS_PENDING` | Matrix table separating active gate from full evaluation arms ($M0 \dots F111$) |
| 38 | Scientific Claim Ceiling: Development Gate Boundary | `RESULTS_PENDING` | Dual status summary: Development Gate Passed vs. Policy Efficacy Pending |

---

## 4. Verification & Consistency Audit

```bash
# Verification checklist run against artifacts/multi-catfish-teaching-deck-v023-20260905-r1/agy-pilot/:
- STORYBOARD.md slide count: 38 slides [VERIFIED]
- MATH-TOKEN-INVENTORY.json slide count: 38 slides [VERIFIED]
- ASCII control characters in JSON: 0 (clean) [VERIFIED]
- Multi-letter math subscripts in JSON: 0 (all atomic single-letter/digit) [VERIFIED]
- Core Flow SVG valid XML: True [VERIFIED]
- Core Flow SVG font sizes: strictly 28px, 24px, 20px (0 unauthorized sizes) [VERIFIED]
- Pilot Slide Spec typography: strictly 28 pt, 24 pt, 20 pt (0 unauthorized sizes) [VERIFIED]
- Citation authority: test_w181 synthetic fixture + contract §5 [VERIFIED]
- Acronym expansion "Multi-Causal Reinforcement Learning": 0 occurrences [VERIFIED]
- External repo files touched: 0 [VERIFIED]
- PPTX files generated: 0 [VERIFIED]
```

## 5. Conclusion

The planning artifacts in `artifacts/multi-catfish-teaching-deck-v023-20260905-r1/agy-pilot/` have been completely updated, validated, and reconciled. Every item of the `REVISE_BEFORE_PPTX` audit has been resolved with complete fidelity to the authoritative governance documents.
