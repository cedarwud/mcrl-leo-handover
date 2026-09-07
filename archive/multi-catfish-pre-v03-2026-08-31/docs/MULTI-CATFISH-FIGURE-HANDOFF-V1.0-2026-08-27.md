# SMC-ER figure and English-deck handoff v1.0

> **SUPERSEDED FOR NEW DRAWING (2026-08-28).** The hashes and routing semantics
> below bind the retired all-head carrier. Do not use this file alone to revise
> figures or slides. Apply
> `THREE-CATFISH-EE-POSITIVE-ACCEPTANCE-CONTRACT-V0.1-2026-08-28.md` first:
> draw only `C1 -> Q_1^M`, `C2 -> Q_2^M`, and `C3 -> Q_3^M`; replace generic C2
> persistence with activation-churn-aware temporal persistence; show C2/C3
> useful-bits/EE tests as pre-outcome forecast proxies, not guarantees; and keep
> every EE improvement label empirical/unverified.

Date: 2026-08-27  
Status: historical handoff; structural revision required before further
drawing/deck synchronization; camera-ready insertion and empirical claims
remain closed.

## 1. Authorized scope

The current structural authority is sufficient to proceed in parallel with:

- editable Fig. 2-1 and Fig. 3-1 drafts;
- editable Fig. 4-1--4-7 method drafts;
- an English algorithm-only WMNLab PowerPoint deck;
- provisional native-shape or semantic-SVG carriers wherever a final figure
  is not yet available.

Figure completion is not a prerequisite for slide construction. Slides may be
laid out and visually validated now, then receive reviewed figure assets by a
controlled asset replacement.

## 2. Frozen structural snapshot

| Authority | SHA-256 |
|---|---|
| [Technical method](/home/u24/papers/mcrl-leo-handover/docs/MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md) | `a42a66be367247d96a54091034f7cada89796b34e47660a225400310f26a49fd` |
| [Concept freeze](/home/u24/papers/mcrl-leo-handover/docs/MULTI-CATFISH-CONCEPT-ALGORITHM-FREEZE-V0.1-2026-08-27.md) | `5404bbfb0ea38931269dd4df812170b81675f8646ec20c4dd9fa6fbdaba7ebf0` |
| [Non-result authoring contract](/home/u24/papers/mcrl-leo-handover/docs/MULTI-CATFISH-NONRESULTS-PAPER-AUTHORING-CONTRACT-V0.1-2026-08-27.md) | `6a5dc7e4305f36d90a057293e5059e7d7e5c60130811f47de3f26d56e5ff73e8` |

Review receipts:

- Initial fresh-context review:
  `.scratch/catfish-cross-model-audit/SOL-ULTRA-SMC-ER-R2-FIGURE-GATE-2026-08-27.md`.
- Passing R3 delta review:
  `.scratch/catfish-cross-model-audit/SOL-ULTRA-SMC-ER-R3-FIGURE-SPEC-DELTA-2026-08-27.md`.
- Prior Opus method review:
  `.scratch/catfish-cross-model-audit/OPUS-MAX-SMC-ER-V04-CONCEPT-REVIEW-2026-08-27.md`.
- Existing PPTX symbol mismatch audit:
  `.scratch/catfish-cross-model-audit/AGY-PPTX-SYMBOL-AUDIT-2026-08-27.md`.

If any of the three authority hashes changes, the figure/deck session must
perform a focused semantic diff before calling a later asset synchronized.

## 3. Binding topology and claim boundary

- The exact name is **Specialist Multi-Catfish Experience Routing (SMC-ER)**.
- Training has one Main MODQN and three independent objective specialists.
- Main owns three objective Q functions; each specialist owns only its one
  corresponding Q function. This is four logical learners and six online Q
  functions, plus target copies.
- Every executed specialist branch retains one complete, unmodified joint
  bundle with the full `U x 3` canonical reward matrix.
- Each source owns an independent Main-consumer gate. Only gate-pass bundles
  route to Main; gate-fail bundles remain shadow-only.
- `F_3` is currently shadow-only. `F_1` and `F_2` also remain conditional until
  their own gates pass.
- Experience is routed. Actions, Q values, parameters, votes, or intents are
  never fused.
- All specialists are removed for evaluation and deployment; Main alone
  selects the action.

The figures and slides may say **proposed**, **objective-aligned**,
**conditional**, **training-only**, and **falsifiable**. They may not say the
method is effective, novel, empirically superior, complementary in observed
support, or guaranteed to improve EE.

## 4. Figure status and deck mapping

| Figure | Structural status | Primary deck job |
|---|---|---|
| Fig. 2-1 | open; source-bound science card accepted | baseline MODQN carrier, with no Chapter 4 symbols |
| Fig. 3-1 | open; source-bound science card accepted | physical multi-beam LEO system only |
| Fig. 4-1 | open | complete SMC-ER overview and Main-only deployment |
| Fig. 4-2 | open | four-learner/six-Q topology |
| Fig. 4-3 | open | C1 source, C1-only EXP prefill, private ACRM, conditional routing |
| Fig. 4-4 | open | C2 physical-association persistence option and indirect EE path |
| Fig. 4-5 | open | C3 one-user load move, exact `r3` delta, separate safeguards, shadow status |
| Fig. 4-6 | open | atomic full-bundle routing with one independent gate per source |
| Fig. 4-7 | open | Phase I/II/III training-to-deployment sequence |

All nine rows are structural-authoring permissions, not camera-ready
acceptance. Final captions remain those in the live authoring contract.

## 5. English deck contract

Use [the parallel-authoring GPT prompt](/home/u24/papers/mcrl-leo-handover/docs/PROMPT-SMC-ER-FIGURES-AND-ENGLISH-DECK-2026-08-27.md).
Its presentation worker is **non-heavy** and should remain in the current
environment.

The deck must use the native WMNLab template at
`/home/u24/pptx-craft/assets/wmnlab.pptx`, whose expected SHA-256 is
`17faf48ce35c6901ae6c968ca3f6606a9d37001589f7905634e2c57ff4f6ece1`.
All visible text is English and Times New Roman. Titles are at most 28 pt,
normal body text targets 24 pt, and diagram/flowchart text boxes use 20 pt.
Equations and text remain editable. Final figures are not required to begin:
native shapes or semantic SVGs may occupy stable figure slots until reviewed
assets replace them.

The old `chapter4-0826.pptx` and `chapter5-0826.pptx` are read-only references,
not sources of notation. Their known mismatches must not propagate into the new
deck.

## 6. Closed gates

### Camera-ready and manuscript insertion

Still blocked by both:

1. an explicit writer handoff for the dirty external thesis worktree; and
2. writer-authorized synchronization of the old external one-Catfish symbol
   rows with `F_j`, `Q_j^F`, `D_j^F`, and `tau_{j,t}^F` before Chapter 4 or
   final figures are inserted.

This block does not prevent standalone editable figures or the standalone
algorithm deck from being built and reviewed.

### Empirical claims

Still blocked by source/role gates, consumer-representation gates, matched
pilots, and later preregistered experiments. The structural review is not
evidence of effectiveness, specialist survival, combined benefit, or novelty.

## 7. Handoff completion test

A drawing or slide asset is synchronized to v1.0 only when:

1. it records the three frozen authority hashes above;
2. its labels and formulas satisfy the corresponding science card and exact
   caption;
3. it preserves independent source gates and current C3 shadow status;
4. it contains no result badge or unsupported effectiveness claim; and
5. it has a visual-QA receipt at the intended manuscript or slide size.

Desktop Microsoft PowerPoint inspection remains the final human acceptance
gate for the deck. Browser, SVG, package, or LibreOffice validation is
engineering evidence only.
