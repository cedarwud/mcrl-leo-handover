# Multi-Catfish MCRL V0.18 — web / figure / teaching-deck handoff

> **PROVISIONAL_V0.18_NO_LEARNED_OR_EFFICACY_CLAIM**

Date: 2026-09-04 (Asia/Taipei)  
Package status: `METHOD_FIGURES_AND_TEACHING_DECK_ALLOWED__RESULTS_HELD`

This package is a clean authoring handoff for the current V0.18 method. It is
ready for a web agent or figure/deck agent to begin method diagrams and an
English teaching presentation now. It deliberately does not freeze a learned
Q3 checkpoint, a physical five-arm result, a paper claim, or a final notation
authority.

## What is settled enough to draw

The method has one final objective, one physical action at deployment, and
three independent Catfish/Q-head views:

```text
predecision state
    ├── C1 Energy-Frontier        → Q1
    ├── C2 Projected-Persistence  → Q2 (learned OPS-3 surface)
    └── C3 Relational Zero-Marginal → Q3 (V0.18 learner pending)

safe score(a) = Q1(s,a) + Q2(s,a) + Q3(s,a)
executed action = one native-safe masked argmax_a safe score(a)
```

The three routes are not three agents, not three deployment controllers, and
not a post-training coordination layer. Each route creates a training-time
comparison/source view and updates only its own Q head. The final action is
one Main action selected with the common native safety mask.

## What is not settled

- The analytic ZR diagnostic has passed, but it is an oracle/parameter-free
  TRAIN diagnostic; it is not learned-Q3 efficacy.
- The V0.18 structured Q3 source/learner gate has not yet produced a learned
  result. Its pre-outcome contract is still a draft until the final freeze.
- The physical five-arm screen has not yet run. Its result figures must remain
  placeholders.
- A long 500/1500/3000/9000-episode claim is not authorized by this package.
  Any 9000-episode launch requires a separate notice and authority.

## Read in this order

1. [`CLAIM-STATUS.md`](CLAIM-STATUS.md) — verified facts, inferences,
   proposals, and forbidden claims.
2. [`METHOD-BRIEF.md`](METHOD-BRIEF.md) — the reader-facing algorithm and
   compact equations.
3. [`FIGURE-DECK-BRIEF.md`](FIGURE-DECK-BRIEF.md) — figure inventory, slide
   arc, visual semantics, and result-placeholder rules.
4. [`SUPERSESSION-MAP.md`](SUPERSESSION-MAP.md) — which historical documents
   are provenance only and must not be drawn as current V0.18.
5. [`WEB-AGENT-PROMPT.md`](WEB-AGENT-PROMPT.md) — copy/paste work order for a
   fresh web or authoring agent.
6. `source-map/` and `evidence/` — exact source paths and byte-preserved
   evidence copies.

## Authoring rule

Draw and explain the method now. Keep result plots, ranking arrows, and any
sentence of the form “C1/C2/C3 improves EE” visibly marked `PENDING` until
the learned-Q3 gate and the separately sealed five-arm physical screen pass.
The analytic values in the evidence folder may be shown only as a boxed
“TRAIN analytic diagnostic — not learned efficacy” status item.

The package is intentionally additive. It does not edit shared authority,
notation tables, source code, training outputs, or older packages.

