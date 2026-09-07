# CDRL-style thesis figure batch — 2026-07-22

This directory is the reviewable, builder-driven redraw batch for Chapters 3
and 4.  The governing rule is reference fidelity first:

1. reproduce the relevant CDRL composition;
2. repair only the source's local ambiguity or routing defect;
3. adapt the repaired composition to the implemented MCRL semantics;
4. invent a new composition only when CDRL has no corresponding mechanism,
   while retaining its sparse serif type, light grouped plates, physical
   glyphs, and neutral-main / warm-training ownership grammar.

The untracked CDRL reference PNGs under
`archive/catfish-route/fig-ref/` are local source material and are not part of
this batch or its commit.

## 1. Full CDRL reference audit

All 15 available source images were considered.  The primary reusable figures
are CDRL Figs. 3.5 and 4.4–4.10.  Figs. 1.1 and 3.1 provide overview/system
composition; Figs. 2.1(b), 3.2–3.4, and 4.2 provide only hardware, grouping, or
card-stack vocabulary because their RIS/actor-critic/teacher-student semantics
do not belong to MCRL.

| CDRL image | What is retained | What is not transferred |
|---|---|---|
| `fig1.png` | environment/model two-column grouping | RIS hardware and offline data preparation |
| `fig2b.png` | flat physical components and subsystem grouping | BS/RIS/RF-chain semantics |
| `fig3-1.png` | wide physical topology | terrestrial BS–RIS–UE entities |
| `fig3-2.png` | symmetric grouped subsystems only | alternating optimizers |
| `fig3-3.png` | agent/network container grammar only | actor–critic roles |
| `fig3-4.png` | asymmetric paired-panel grammar only | teacher advice |
| `fig3-5.png` | neutral Main / warm Catfish paired architecture | single-objective and direct-weight interpretations |
| `fig4-2.png` | repeated-sample card stacks and Calculate-EE destination | offline random dataset generation |
| `fig4-4.png` | replay → state → network → action → environment loop | RIS action components |
| `fig4-5.png` | training swimlanes and ownership | scalar-only actor–critic training |
| `fig4-6.png` | two replay memories, mixed batch, random-period diamond | fixed 70/30 text and full duplicate agent diagrams |
| `fig4-7.png` | two vertical decisions and three replay/discard routes | fixed absolute EE thresholds |
| `fig4-8.png` | mirrored discount-horizon comparison | discount symbol gamma |
| `fig4-9.png` | bar-level competitive-reward geometry | unpaired performance comparison |
| `fig4-10.png` | compact trained-model lane | deployed Catfish/replay/update path |

## 2. Required 13-figure set

The batch records the candidate figures used to explain the method narrative.
The existing LEO system model is retained; the entries below include work
completed before the 2026-07-22 batch pass.

| Chapter slot | Final artifact | CDRL source grammar | Status and claim boundary |
|---|---|---|---|
| 3-1 system model | `../fig2.png` | Fig. 3.1 / 2.1(b) | **KEEP** existing physical LEO geometry; system description only |
| ~~3-2 power-to-EE~~ | — | — | **REMOVED (USER, 2026-07-22):** formulas sufficiently express the relation; all associated figure assets and builders deleted |
| ~~3-3 context normalization~~ | — | — | **REMOVED (USER, 2026-07-22):** equations define the operation more clearly; figure assets and builder deleted |
| ~~4-1 MODQN baseline~~ | — | Fig. 4.4 | **REMOVED (USER, 2026-07-22):** the baseline loop is fully defined by the §4.1 prose and equations and duplicates the MCRL architecture; all associated assets and builders deleted |
| 4-1 MCRL architecture | `fig-mcrl-architecture.png` | Figs. 3.5 and 4.5 | **ADAPT** three parallel shaping strategies; Catfish is training-only |
| 4-3 CDRL → MCRL lineage | `fig-cdrl-mcrl-lineage.png` | Figs. 3.5, 4.5, and 4.10 | **ADAPT** aligned components, not two false sequential flows |
| 4-4 congestion context | `fig-congestion-context.png` | Fig. 4.4 state-component grammar | **NEW** action-before features only; no outcome leakage or effectiveness claim |
| 4-5 EE stratification | `fig-stratification.png` | Fig. 4.7 | **DIRECT ADAPT** rolling quantiles plus warm-up route |
| 4-6 asymmetric discount | `fig-asymmetric-discount.png` | Fig. 4.8 | **DIRECT ADAPT** agent-to-agent beta asymmetry, schematic bars |
| 4-7 periodic intervention | `fig-periodic-intervention.png` | Fig. 4.6 | **DIRECT ADAPT** fixed mix ratio, random interval, extra main update |
| 4-8 competitive reward | `fig-competitive-reward.png` | Fig. 4.9 | **DIRECT ADAPT** paired first-objective reward; Catfish update only |
| 4-9 capacity penalty | `fig-capacity-penalty.png` | CDRL bar/rank vocabulary | **NEW** preference tail beyond `v_max`; not actual user count or guaranteed spreading |
| ~~4-10 training/deployment~~ | — | — | **REMOVED (USER, 2026-07-22):** redundant with the MCRL architecture; all associated assets and builder deleted |

## 3. Supersession boundary

The corresponding equation-card/prose-card figures in `thesis-mc/figures/`
are superseded by this batch but are not deleted here.  In particular:

- `fig-stratification.png` and `fig-congestion-context.png` in the parent
  directory are not the review targets;
- the parent `fig-intervention-annealing.png` and this directory's earlier
  `fig-intervention-annealing.*` outputs are superseded by
  `fig-periodic-intervention.*` because the implemented mechanism does not
  anneal;
- the parent `fig-capacity-penalty.png` is superseded by this directory's
  ranked-tail version;
- legacy coordination/collapse figures remain retired and are not reused.

Chapter Markdown and figure numbering are intentionally untouched in this
batch: `thesis-mc/ch4-method.md` contains concurrent user work.  Promotion and
renumbering can therefore be performed as one later, narrow integration change
without overwriting that work.

## 4. Rebuild and validation contract

Every final artifact has a sibling `build_*.py` (except the retained system
model), editable SVG, rendered PNG, and `.viz.json`.  The accepted pipeline is:

```text
builder
  -> check_layout --preset academic
  -> check figure
  -> validate svg
  -> svg2png
  -> eye-pack (colour + grayscale)
  -> fill_eye
  -> check_eye
```

The 40 px type scale is the user-set scale for this redraw batch.  Its profile
warnings against the older 24/22 px manifest are expected; all geometry and
print-scale checks must still have zero violations.
