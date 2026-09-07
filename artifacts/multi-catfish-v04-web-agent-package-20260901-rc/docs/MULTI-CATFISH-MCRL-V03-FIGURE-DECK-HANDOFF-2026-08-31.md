# Multi-Catfish MCRL V0.3 figure and deck handoff

Main-deck compression authority:
`MULTI-CATFISH-MCRL-V03-PRESENTATION-LAYER-2026-08-31.md`. The F1--F8
inventory below is a complete reusable figure library, not a requirement to
show eight method figures or reproduce every implementation detail in the
main talk.

Date: 2026-08-31  
Status: **current drawing/deck specification; no result claim; no training authorized**

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
| `C2 / Q2` | downstream temporal EE surplus; hold-or-max-lagged-SINR-rival opening, hold while legal, then monotone branch-local Main release |
| `C3 / Q3` | non-focal opening rate externality; lagged-load-informed unilateral enumeration |
| `D^o` | opening source: store paper targets \(\zeta_1\) and \(\zeta_3\) once |
| `D^t` | temporal source: store paper target \(\zeta_2\) over offsets \(1,\ldots,H^c-1\) |
| `D^a` | held-out full identity traces; evaluation only, no gradient |
| `M` | matched reference branch/action |
| `C` | unilateral candidate branch/action |
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
release/provenance annotations are appendix material. Retain their source
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

**Composition:** A horizontal horizon with offsets \(0,1,\ldots,H^c-1\). At offset
\(0\), place two non-overlapping bands: focal net surplus \(\zeta_1\) and non-focal
rate externality \(\zeta_3\). At offsets \(1,\ldots,H^c-1\), place temporal band \(\zeta_2\).
Show the identity:

\[
\zeta_1+\zeta_3+\zeta_2=\sum_{k=0}^{H^c-1}g_k.
\]

Include the note: “accounting identity, not an efficacy proof.” The release
offset must be visibly inside \(\zeta_2\).

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

### F5 — C2/Q2 temporal departure fork

**Purpose:** Make the C2 decision and temporal scope understandable in one
view.

**Composition:** departure anchor with incumbent association → predecision
rule: “hold if legal; otherwise maximum predecision candidate-SINR legal non-Main rival; physical-ID then action-ID tie break” → sealed matched
continuations `M/C` → candidate hold segment → either planned horizon release
or support-triggered monotone release to branch-local Main → offsets
\(1,2,3,\ldots,H^c-1\) → rates and network power → \(\zeta_2\) → \(D^t\) → \(Q_2\).

**Required callouts:** “reactive release reads only candidate-branch
contemporaneous legality”; “no look-ahead; release is latched”; “planned or
support-triggered release offset included”; “canonical-fading keyed
common-random field required.” Mark the old fixed-hold keyed gate
`INDETERMINATE`, the V0.3B release implementation/test gate `complete`,
and the sealed V0.3B physical-headroom gate
`GO_BOUNDED_LEARNABILITY_PILOT_ONLY — not efficacy`.

**Do not show:** a temporal target made from only one reward, or a source row
that is silently mixed across policy versions.

### F6 — Phase-I datasets and three independent learners

**Purpose:** Give the complete source/learning architecture.

**Composition:**

```text
sealed physical source
        ├── D^o: zeta1, zeta3 ──> Q1 / Q3 route-local updates
        ├── D^t: zeta2        ──> Q2 route-local updates
        └── D^a: full held-out identity ──> evaluation only

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
  -> fixed-hold keyed-CRN C2 census: INDETERMINATE
  -> V0.3B implementation/test complete
  -> V0.3B physical-headroom gate: GO_BOUNDED_LEARNABILITY_PILOT_ONLY
  -> versioned state/replay/checkpoint schema
  -> E1 non-EE instrument-validity gate
  -> bounded matched learnability pilot only after E1 GO
  -> short-EP matched ablations
  -> only then longer training / efficacy claim
```

Put `NO-GO: EE training/ablation until E1` at the top of this figure. The first
10EP result is `VOID_UNINTERPRETABLE_INSTRUMENT` and must not appear as route
evidence. Mark all unsealed thresholds, seeds, and efficacy results `TBD`.

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

7. **C2: temporal departure fork**  
   Use F5; show hold-or-max-lagged-SINR-rival, the legal hold segment, and both
   planned and support-triggered monotone release.

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

- Which route is focal now, temporal later, and non-focal now?
- Why are \(\zeta_1\) and \(\zeta_3\) both in \(D^o\), while
  \(\zeta_2\) is in \(D^t\)?
- Why can `D^a` never send a gradient?
- Are there three executed actions or one? (Correct: one.)
- Does an ablation remove a Q head? (Correct: no; it swaps in an equal-budget
  neutral source.)
- Where is the release offset? (Inside C2.)
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

matched horizons other than Pilot-1 \(H^c=4\), state dimension, canonical
fading-field version, `λ_0`, `κ`, `β`,
learning rate, batch/update schedule,
seed count, threshold/quota, checkpoint result, confidence interval, and every
Chapter 5 numerical EE value.

Never substitute an archived value merely to make a diagram look complete.
