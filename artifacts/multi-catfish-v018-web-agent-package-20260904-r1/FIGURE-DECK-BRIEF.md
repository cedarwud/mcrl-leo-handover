# V0.18 figure and English teaching-deck brief

> **PROVISIONAL_V0.18_NO_LEARNED_OR_EFFICACY_CLAIM**

This brief is an execution-ready visual specification. Method diagrams and
teaching slides may be produced now. Result plots are reserved placeholders
until the learned-Q3 gate and physical five-arm screen are complete.

## Visual grammar

Use one consistent three-route palette, for example:

| Route | Label | Suggested accent | Meaning |
|---|---|---|---|
| C1 / Q1 | Energy-Frontier | amber | focal immediate opening view |
| C2 / Q2 | Projected-Persistence | blue | deterministic projected persistence |
| C3 / Q3 | Relational Zero-Marginal | teal | current non-focal relational externality |
| Main | one safe action | dark navy | only executed action |
| evidence boundary | pending / receipt | slate or gray | no efficacy claim |

Use solid arrows for data flow, dashed arrows for labels/receipts, and a
double-outline box for “training-time only; never a deployed controller.”
Every result placeholder must contain a visible `PENDING — NO V0.18 LEARNED OR
PHYSICAL RESULT YET` label.

## Figure inventory

### F1 — One objective, three views, one action

Show the simulator state entering three parallel route boxes (`C1/Q1`,
`C2/Q2`, `C3/Q3`), then the three surfaces entering one unweighted sum and one
native safe argmax. A single Main action exits to the environment. Put “no
auction / no coordinator / no post-training override” under the decoder.

### F2 — Matched physical comparison

Show one sealed anchor, focal user \(u\), detached reference branch \(M\),
candidate branch \(C\) with exactly one focal-action difference, and a shared
keyed exogenous-randomness field. Split the observed surplus into the route
views without suggesting that three branches are executed.

### F3 — C1 Energy-Frontier

Show RIS-lineage EXP/ACRM selecting informative opening comparisons, then the
focal immediate rate and complete opening network-energy term forming
\(\zeta_{1,u}\), followed by Q1-only training. Retain negative examples.

### F4 — C2 Projected-Persistence

Show current geometry/TLE entering a cloned projection, offsets
\(h=1,2,3\), frozen non-focal background, service indicator, projected focal
rate, marginal network power, and the \(-\kappa\) outage term. Show the
reference-centred Q2 surface. Explicitly mark “forecast / no future action / no
future RNG.”

### F5 — C3 Relational Zero-Marginal

Show one focal action connected to multiple non-focal victim tokens. A shared
victim scorer produces signed contributions, with negative contributions always
kept and positive contributions gated by predecision compatibility. Aggregate,
centre at the reference, and produce Q3. Make clear that `z3_bits` is a
post-capture label only.

### F6 — Source chronology and provenance

Use a six-stage timeline: detach Q1/Q2 and mask → encode predecision tensors →
persist Q1+Q2 background → open exact matched target → state/RNG immutability
check → execute only the source/reference action. Put complete-world split and
SHA/provenance receipts at the bottom.

### F7 — Learner and deployment

Show three independent learners, each updating only its own Q head. For C3,
show structured tensors `(U,A,7)` and `(U,A,U,6)` into one shared scorer. Then
show \(Q_1+Q_2+Q_3\), common mask, one argmax, one action. Do not draw six Q
networks or an extra Catfish agent.

### F8 — Five-arm ablation design and claim ceiling

Show the five planned arms in a table or small decision tree. Highlight that
the physical screen is pending and that raw ratio-of-sums EE plus service is
the endpoint. Use gray placeholder bars rather than fabricated values.

### Optional F9 — Evidence status panel

It is acceptable to show the verified analytic status as a small diagnostic
card: `PASS_ANALYTIC_DIAGNOSTIC`, BASE `118.424M` bit/J, EXACT `119.645M`,
NOMINAL `119.730M`, with the subtitle “TRAIN oracle/nominal diagnostic only;
not learned-Q3 efficacy.” Do not make it a final performance chart.

## Suggested English teaching-deck arc

1. Title and claim boundary.
2. Why one EE objective needs complementary action views.
3. The matched physical intervention.
4. C1 Energy-Frontier.
5. C2 Projected-Persistence.
6. C3 Relational Zero-Marginal.
7. How the source data become three Q heads.
8. One safe Main action at deployment.
9. Planned five-arm ablation (all result values pending).
10. What is verified now and what remains to be tested.

## PowerPoint constraints

Use `~/pptx-craft/wmnlab.pptx` as the template. The teaching deck is English.
Use Times New Roman throughout: title approximately 28 pt, body approximately
24 pt, and text inside diagram boxes approximately 20 pt. Use native editable
PowerPoint shapes for ordinary boxes/arrows and native OfficeMath/OMML for
every displayed formula. Mathematical symbols and variables are italic;
ordinary prose and route names are upright. Keep public symbols to one-letter
names with one-letter or numeric indices (for example \(Q_j\),
\(\zeta_{j,u}\), \(a_u^*\)); do not introduce aliases such as `EE_1`,
`Reward_2`, or multiword mathematical subscripts.

Method figures may be editable SVG plus PNG exports, but a deck formula must
remain native editable math. If a 3-D simulator screenshot helps explain
geometry, label it as an illustration and never as a measured result.

