# Multi-Catfish MCRL V0.3 figure and deck handoff

Main-deck compression authority:
`MULTI-CATFISH-MCRL-V03-PRESENTATION-LAYER-2026-08-31.md`. The F1--F8
inventory below is a complete reusable figure library, not a requirement to
show eight method figures or reproduce every implementation detail in the
main talk.

Date: 2026-08-31  
Status: **C1/C3 drawing authority only; C2 V0.7 panels superseded after R14;
replacement C2 pending; no training authorized**

> **Figure hold for C2 (2026-09-02).** Do not draw the focal-next
> `motion-one` C2 as a current or locked mechanism. R13 was compatible with
> zero and R14 found `0/3` lineages better than the strongest held-out null.
> Existing C2 panels remain provenance only. C1/C3 figures may continue; show
> C2 as `clean-room temporal redesign pending` until a replacement passes its
> formula-first and observability gates.

This handoff is the source-led brief for all system-overview figures,
algorithm-flow diagrams, Chapter 4 illustrations, and the English algorithm
presentation. It is anchored to:

- `docs/MULTI-CATFISH-EE-AXIS-REDESIGN-CONTRACT-V0.3-2026-08-31.md`;
- `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md`;
- `src/mcrl/algorithms/ee_axis_pairwise.py`;
- `docs/MULTI-CATFISH-MCRL-V03-PAPER-AUTHORING-CONTRACT-2026-08-31.md`.

Archived figure drafts, SMC-ER names, old Bellman/6Q topology, and post-training
coordination diagrams are not visual references for this handoff.

## 1. Non-negotiable visual and text rules

The presentation is English and uses Times New Roman throughout:

- slide titles: at most 28 pt;
- ordinary body text: 24 pt where it fits;
- diagram labels and text inside shapes: 20 pt;
- keep equations editable when the authoring tool supports native math;
- use one-letter primary mathematical symbols with one-letter subscripts or
  superscripts; do not create a second notation system in a figure.

Every figure must visibly distinguish **source generation**, **learning**,
**deployment**, and **held-out evaluation**. Use solid arrows for data/score
flow and dashed arrows for audit or lineage only. Do not draw an arrow from
`D^a` to a loss or optimizer.

Every result-looking chart must be marked `TBD — held-out matched evaluation`
until a receipt exists. Do not draw numerical gains, thresholds, quotas, state
dimensions, learning rates, `β`, or confidence intervals as if frozen.

## 2. Method vocabulary for all figures

| Visual label | Exact meaning |
|---|---|
| `C1 / Q1` | focal opening-step EE surplus; RIS-lineage EXP/ACRM experience route |
| `C2 / Q2` | motion-one (provisionally locked post-R13) focal next-slot attributable EE surplus; native-mask candidate/Main comparison |
| `C3 / Q3` | non-focal opening rate externality; lagged-load-informed unilateral enumeration |
| `D^o` | opening source: store paper targets \(\zeta_1\) and \(\zeta_3\) once |
| `D^t` | focal-next source: store paper target \(\zeta_2\) at successor slot 1 |
| `D^a` | held-out scoped identity traces; evaluation only, no gradient |
| `M` | matched reference branch/action |
| `C` | unilateral candidate branch/action |
| `b` | branch index, `b` ∈ {`C`,`M`} |
| `p_{b,u}` | focal marginal network power at successor slot 1 on branch `b` |
| `λ_0` | one frozen TRAIN-only global bit/J multiplier |
| `Q_j` | one of three independent online Q networks |
| `Φ_u` | \(Q_1+Q_2+Q_3\) deployment score for user \(u\) |
| `A_u(t)` | legal, service-safe masked action set |

Do not label `C2` or `C3` as “r2” or “r3 objectives.” Do not label the
combined score as an auction, coordinator, vote, or joint policy.

## 3. Figure inventory

For the main paper/deck, combine this library into four reader-facing scenes:

1. F1 plus the objective: one matched physical intervention;
2. F2: three non-overlapping EE views;
3. F3--F6 compressed into three source cues feeding three route-local Q
   estimators;
4. F7: one summed, service-masked Main action.

F8, complete dataset routing, gate ladders, receipt fields, and detailed C2
source/provenance annotations are appendix material. Retain their source
artifacts for auditability; do not force them into the main narrative.

The following eight figures are sufficient to explain the method and its
evaluation boundary. They can be SVG, PNG, editable PowerPoint objects, or a
3-D render when that improves spatial comprehension. The scientific content,
labels, arrows, and claim ceiling are fixed regardless of rendering tool.

### F1 — Physical system and one-mover counterfactual

**Purpose:** Establish the same physical multi-user world before showing
Catfish roles.

**Composition:** LEO satellite/beam layer, users, one focal user \(u\), other
users \(i\ne u\), reference action \(M\), candidate action \(C\), and a clock/interval
marker. Show only the focal action changing at the opening anchor. Show
shared bandwidth, interference, activation, and canonical network power as
common physical consequences.

**Required callout:** “Candidate and reference are sealed before outcomes are
read; matched random field; unilateral focal intervention.”

**Do not show:** a second isolated world, a coordinator, paired user actions,
or an already-selected joint action.

### F2 — EE timeline and non-overlapping target partition

**Purpose:** Explain why three routes can be trained from one EE endpoint.

**Composition:** A two-slot view with opening slot 0 and successor slot 1. At
slot 0, place two non-overlapping bands: focal net surplus \(\zeta_1\) and
non-focal rate externality \(\zeta_3\). At slot 1, place the
motion-selected focal-attributable band \(\zeta_2\), with its marginal-power
comparison shown in F5. Label the scoped identity as “opening terms plus
focal-next term; non-focal successor remainder is diagnostic.” Include the
note: “accounting identity, not an efficacy proof.”

### F3 — C1/Q1 focal opening route

**Purpose:** Show the RIS-lineage route and prevent confusion about what EXP /
ACRM changes.

**Composition:** \(M/C\) opening pair → focal user rate difference and opening
energy difference → \(\zeta_1\) → \(D^o\) → \(Q_1\). Place EXP and ACRM beside source
generation and private preparation, not in the EE endpoint box.

**Formula:**

\[
\zeta_{1,u}=\Delta t[R_u^C(0)-R_u^M(0)]
-\lambda_0\Delta t[P_C^N(0)-P_M^N(0)].
\]

**Caption sentence:** “C1 retains RIS EXP/ACRM as an experience mechanism;
the endpoint remains canonical ratio-of-sums EE.”

### F4 — C3/Q3 non-focal externality route

**Purpose:** Show the genuinely different spatial route without double-counting
opening energy.

**Composition:** lagged candidate-beam load, active-beam/satellite state, and
maximum required link power → sealed anchor → unilateral legal-action
enumeration → same-world \(M/C\) opening pair → non-focal users \(i\ne u\) →
\(\zeta_3\) → \(D^o\) → \(Q_3\).

**Formula:**

\[
\zeta_{3,u}=\Delta t\sum_{i\in\mathcal U\setminus\{u\}}
[R_i^C(0)-R_i^M(0)].
\]

**Required callout:** “lagged observations are broadcast context, not action
coordination; opening shared energy is already charged to C1.”

### F5 — C2/Q2 focal next-slot route

**Purpose:** Make the C2 decision and temporal scope understandable in one
view.

**Composition:** predecision anchor → select one eligible focal user by largest
signed-motion opportunity (lowest user index on a tie) → enumerate the native
28 legal action slots under the native mask → matched candidate/Main branches
`C/M` → successor-slot focal rate and marginal network-power comparison →
\(\zeta_2\) → \(D^t\) → \(Q_2\).

**Required callouts:** “one focal user per anchor”; “all 28 native legal slots
under the native mask”; “matched candidate C versus Main M”; “focal-attributable
next-slot EE surplus”; “C2 rows update Q2 only”; “at deployment Q2 contributes
only to the motion-selected focal user; the final score is unweighted
Q1+Q2+Q3 with one native masked argmax.”

Label this as the **motion-one, provisionally locked post-R13 C2 amendment**.
The earlier D2 preregistration predates motion-one and does not validate this
amendment.

**Required formulas:**

\[
p_{b,u}(1)=P_b^N(1)-P_{b,-u}^N(1),\qquad b\in\{C,M\}.
\]

\[
\zeta_{2,u}=\Delta t[R_u^C(1)-R_u^M(1)]
-\lambda_0\Delta t[p_{C,u}(1)-p_{M,u}(1)].
\]

**Do not show:** an all-user temporal aggregate, multiple focal users,
or a source row that is silently mixed across policy versions.

### F6 — Phase-I datasets and three independent learners

**Purpose:** Give the complete source/learning architecture.

**Composition:**

```text
sealed physical source
        ├── D^o: zeta1, zeta3 ──> Q1 / Q3 route-local updates
        ├── D^t: focal-next zeta2 ──> Q2 route-local updates
        └── D^a: scoped held-out identity ──> evaluation only

Q1       Q2       Q3
 |        |        |
 independent online networks; no shared parameters; no target networks
```

Show `κ` as one shared normalization and the pairwise zero-bootstrap loss
beside each route. Draw an arrow from a route row only to its matching `Q_j`.
Do not draw cross-route gradient arrows.

**Required formula:**

\[
\ell_j=w_j\left(
[Q_j(s_u(t),a_u^C(t))-Q_j(s_u(t),a_u^M(t))
-\zeta_{j,u}/\kappa]^2
+\beta Q_j(s_u(t),a_u^M(t))^2\right).
\]

### F7 — Deployment score and masked action

**Purpose:** Resolve the most likely reader misunderstanding: three Q outputs
do not imply three executed actions.

**Composition:** current Main state \(s_u(t)\) → three Q surfaces → elementwise sum
\(\Phi_u\) → legal/service-safe mask \(A_u(t)\) → one `argmax` → one executed Main
action. Include a crossed-out annotation “no auction / no coordinator / no
vote / no post-training override.”

**Formula:**

\[
\Phi_u(t,a)=Q_1(s_u(t),a)+Q_2(s_u(t),a)+Q_3(s_u(t),a),\qquad
a_u^\star(t)=\arg\max_{a\in A_u(t)}\Phi_u(t,a).
\]

### F8 — Ablation and gate ladder

**Purpose:** Separate the mechanism test from claims that are not yet allowed.

**Ablation panel:** show `M0` as a separate original-MODQN reference. Show the
other five V0.3 rows with an identical action mask and three-head outline:

| Arm | Route sources |
|---|---|
| `M0` | independent original MODQN reference |
| `N000` | neutral / neutral / neutral |
| `F111` | active C1 / active C2 / active C3 |
| `A011` | neutral C1 / active C2 / active C3 |
| `A101` | active C1 / neutral C2 / active C3 |
| `A110` | active C1 / active C2 / neutral C3 |

Draw every V0.3 arm (`N000`, `F111`, `A011`, `A101`, `A110`) with `Q1`, `Q2`,
`Q3` still present. Do not draw those three heads inside `M0`. A neutral route
is an equal-budget neutral source; it is not a removed head and does not
trigger score renormalization.

**Gate ladder:**

```text
P1-P4 formula checks
  -> C3 unilateral census
  -> C2 native-mask focal-next source check
  -> balanced R13 development screen: provisional core lock passed
  -> longer trend and held-out validation
  -> only then formal matched efficacy gate
```

Put `DEVELOPMENT ONLY — NOT FORMAL EFFICACY` at the top of this figure. Cite
[`MULTI-CATFISH-MCRL-V07-C2-BALANCED-DEVELOPMENT-GATE-RESULT-2026-09-02.md`](MULTI-CATFISH-MCRL-V07-C2-BALANCED-DEVELOPMENT-GATE-RESULT-2026-09-02.md)
for the balanced R13 screen and state that the b-lineage variability and
a-lineage small service loss require longer trend and held-out validation. Mark all
unsealed thresholds and formal efficacy results `TBD`.

## 4. English deck outline

The **main deck is six slides** and follows the presentation-layer contract:

1. one EE objective and one matched intervention;
2. three non-overlapping EE views;
3. three Catfish source roles;
4. route-local pairwise learning;
5. one summed and masked Main action;
6. current evidence boundary.

The detailed outline below is an appendix/source-slide inventory. A deck
author may draw from it when a defense question requires more depth, but must
not treat all entries as mandatory main slides.

The deck may use temporary native PowerPoint rectangles while final figures
are being rendered. A temporary box must carry the same labels and formulas as
the corresponding figure specification above.

1. **Title — Multi-Catfish MCRL V0.3**  
   One-line thesis: “Three causal EE-surplus views, one masked Main action.”

2. **Why the redesign**  
   Ratio-of-sums EE is the unchanged endpoint; legacy `r2/r3` are not current
   objectives; isolated-world residuals are removed.

3. **One physical world, one focal intervention**  
   Use F1 and state the branch-sealing/common-random contract.

4. **The EE-axis decomposition**  
   Use F2, including the exact identity and its non-efficacy limitation.

5. **Three Catfish roles**  
   Three columns for C1, C2, C3 using the role labels and one-sentence
   mechanisms; no claim that raw route targets all increase.

6. **C1: focal opening surplus**  
   Use F3; explain EXP/ACRM as experience generation.

7. **C2: focal next-slot route**  
   Use F5; show one motion-selected focal user, all 28 native legal action
   slots under the mask, matched candidate/Main comparisons, and focal-
   attributable successor-slot surplus.

8. **C3: non-focal externality**  
   Use F4; show lagged load/activation/power and unilateral enumeration.

9. **Phase-I source datasets**  
   Show F6's `D^o`, `D^t`, `D^a` split and the no-gradient held-out boundary.

10. **Three independent Q networks**  
    Show route-local updates, pairwise loss, shared `κ`, no target nets.

11. **One deployment action**  
    Use F7 and explicitly contrast three estimators with one executed action.

12. **Ablation design**  
    Use F8's `M0`, `N000`, `F111`, `A011`, `A101`, `A110` table and neutral
    equal-budget rule.

13. **Evidence gates**  
    Show formula-first → census → pilot → ablation ladder. State what each
    gate can and cannot establish.

14. **Results placeholder**  
    Use empty or clearly labelled `TBD` axes for held-out ratio-of-sums EE.
    Do not fabricate trends or numerical values.

15. **Conclusion and claim ceiling**  
    “V0.3 defines a coherent, testable three-route mechanism. EE improvement
    remains an empirical question.”

## 5. Required annotations for figure/deck QA

Before release, a fresh reader must answer from the visuals alone:

- Which route is focal now, motion-selected focal next, and non-focal now?
- Why are \(\zeta_1\) and \(\zeta_3\) both in \(D^o\), while the focal-next
  \(\zeta_2\) is in \(D^t\)?
- Why can `D^a` never send a gradient?
- Are there three executed actions or one? (Correct: one.)
- Does an ablation remove a Q head? (Correct: no; it swaps in an equal-budget
  neutral source.)
- Which user receives the C2 contribution at deployment? (Only the
  motion-selected focal user.)
- Is C3 a coordinated action? (Correct: no; unilateral enumeration with
  lagged observations.)
- Is the method already proven to improve EE? (Correct: no.)

If any answer cannot be obtained without oral explanation, revise the visual
labels or add a short callout. A polished render is not scientific acceptance:
the current training boundary remains **NO-GO**, and all efficacy statements
wait for held-out matched ratio-of-sums EE receipts.

## 6. Open `TBD` fields

Keep these visibly unresolved in diagrams and slides until preregistration or
sealed receipts provide them:

state dimension, canonical fading-field version, `λ_0`, `κ`, `β`,
learning rate, batch/update schedule,
seed count, threshold/quota, checkpoint result, confidence interval, and every
Chapter 5 numerical EE value.

Never substitute an archived value merely to make a diagram look complete.
