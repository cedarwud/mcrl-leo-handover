# GPT prompt — continue SMC-ER figures and build the English algorithm deck in parallel

> **DO NOT REUSE UNCHANGED.** This prompt predates the 2026-08-28 diagonal
> routing and EE-positive acceptance contract. Any continuation must first read
> `THREE-CATFISH-EE-POSITIVE-ACCEPTANCE-CONTRACT-V0.1-2026-08-28.md`, replace
> all-head/full-vector gradient arrows with `C1 -> Q_1^M`, `C2 -> Q_2^M`,
> `C3 -> Q_3^M`, replace generic C2 persistence with activation-churn-aware
> persistence, and label all singleton/C123 EE effects as empirical hypotheses.

Copy everything below into the existing figure-authoring GPT session.

---

You are the lead authoring agent for the SMC-ER figure and presentation work.
Continue the existing figure work without pausing it, and immediately start a
parallel English PowerPoint workstream by assigning a dedicated sub-agent.
Do not wait for final figures before building the deck.

## 1. Worker routing and autonomy

Classify both workstreams as **non-heavy**:

- **[non-heavy] Figure work:** read-only scientific inspection plus SVG/native
  diagram/3D figure authoring and visual QA.
- **[non-heavy] Presentation work:** PPTX implementation, rendering, and
  structural/visual QA.

These tasks stay in the current environment; no Ubuntu training server is
needed. Use multiple sub-agents when slots permit. At minimum:

1. keep the current figure author/lead working on the figures;
2. spawn one presentation-author sub-agent now;
3. when a slot becomes free, assign a different sub-agent to presentation QA
   or perform that independent QA yourself.

Do not merely write a plan. Inspect the live files, build the deck, render it,
inspect the rendered slides, revise defects, and leave concrete deliverables.
Do not stop to ask about choices that can be resolved from the authorities
below. Report progress periodically.

## 2. Scientific authority and live-state rule

Before authoring, read the following files completely and use their **current
live bytes**, because they may receive small audit corrections while you work:

1. `/home/u24/papers/mcrl-leo-handover/docs/MULTI-CATFISH-FIGURE-HANDOFF-V1.0-2026-08-27.md`
2. `/home/u24/papers/mcrl-leo-handover/docs/MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md`
3. `/home/u24/papers/mcrl-leo-handover/docs/MULTI-CATFISH-CONCEPT-ALGORITHM-FREEZE-V0.1-2026-08-27.md`
4. `/home/u24/papers/mcrl-leo-handover/docs/MULTI-CATFISH-NONRESULTS-PAPER-AUTHORING-CONTRACT-V0.1-2026-08-27.md`
5. `/home/u24/papers/mcrl-leo-handover/.scratch/catfish-cross-model-audit/SOL-ULTRA-SMC-ER-R3-FIGURE-SPEC-DELTA-2026-08-27.md`
6. `/home/u24/papers/mcrl-leo-handover/.scratch/catfish-cross-model-audit/AGY-PPTX-SYMBOL-AUDIT-2026-08-27.md`
7. `/home/u24/papers/modqn-paper-reproduction/thesis-mc/WRITING-GUIDE.md`
8. the active Chapter 3 symbol table and English Chapter 3/4 sources referenced
   by that writing guide, read-only.

Also inspect the current figure session's asset manifest and existing drafts.
Never infer scientific semantics from an old drawing when it disagrees with
the current three SMC-ER documents.

Important update for the existing figure session:

- The exact method name is **Specialist Multi-Catfish Experience Routing
  (SMC-ER)**.
- The Chapter 2 MODQN science card is now deliberately symbol-free. Do not
  leak Chapter 4 notation into Chapter 2.
- Exact draft captions for Fig. 4-1 through Fig. 4-7 now appear in the
  authoring contract. Treat them as the semantic acceptance criteria even
  though the slide deck itself is English.
- Every specialist-to-Main experience path owns a separate consumer gate.
  A gate is **checked**; only a pass permits routing, while failure remains
  shadow-only. Never draw a single shared all-stream gate.
- C3 is currently shadow-only at its Main-consumer boundary.
- For C3, the one-user identity holds algebraically; the `+2` load condition
  guarantees a strictly positive total-`r3` change under the declared fork.
  Do not say the `+2` condition makes the identity true, and never say it
  guarantees EE.

If the three live method documents change after you start, compare hashes and
perform a focused semantic refresh before the final export. Do not discard
valid layout work; update only affected labels, formulas, arrows, and notes.

## 3. Worktree and ownership safety

- Preserve all unrelated dirty work. Do not reset, stash, clean, broadly
  stage, commit, push, or delete anything.
- Treat `/home/u24/papers/modqn-paper-reproduction` as read-only. It has an
  active dirty manuscript worktree and there is no writer handoff for edits.
- Do not edit `chapter4-0826.pptx` or `chapter5-0826.pptx`. They are reference
  material only and contain known notation mismatches documented by the agy
  audit.
- Create a new isolated presentation project. Prefer
  `/home/u24/pptx-craft/projects/smc-er-algorithm-en-20260827/` if that path is
  writable and has no active writer. Otherwise create an equivalently named
  isolated directory under the current writable figure workspace, and record
  the exact path in the handoff.
- Never overwrite an existing deck. Use versioned output filenames.

## 4. PowerPoint template and native package requirements

Use the official WMNLab template as the base:

`/home/u24/pptx-craft/assets/wmnlab.pptx`

Expected SHA-256:

`17faf48ce35c6901ae6c968ca3f6606a9d37001589f7905634e2c57ff4f6ece1`

The identical read-only copy at
`/home/u24/papers/modqn-paper-reproduction/slides/template.pptx` may be used
only after verifying the same hash. Read and follow
`/home/u24/papers/modqn-paper-reproduction/slides/SLIDE-RULES.md`, with the
explicit diagram exception below.

Preserve the native 16:9 slide size, master, layouts, theme, WMNLab/NTPU logos,
background, footer rule, and automatic slide numbers. Do not recreate the
template by eye and do not flatten whole slides into images.

Use the available `pptx` workflow for the deck, `ppt-native` when native
OfficeMath/OMML is needed, and `svg-craft` when a semantic SVG is the most
efficient diagram carrier. The current user instruction explicitly permits
SVG or other figure assets for scientific diagrams; this overrides the older
"no images" rule **for diagrams only**. Text and equations must remain native
and editable. Keep every SVG source beside the deck and never rasterize text or
formulas. A complex 3D scientific scene may use PNG only if no editable vector
carrier is practical; keep its source/project and record that exception.

## 5. Language, typography, and layout

All visible slide content must be **English**.

- Typeface: **Times New Roman everywhere** for authored Latin text and math.
- Slide titles: **28 pt maximum**; use 28 pt unless the native placeholder
  requires 26 pt for clean fit.
- Main body text: target **24 pt** and keep it at 24 pt whenever practical.
- Diagram boxes, flowchart nodes, callouts, and compact text boxes: **20 pt**.
- Equations: normally 22--24 pt, native editable math.
- Bottom IEEE source line: 14 pt is the only routine exception to the 20 pt
  minimum.
- All authored text is black. Use restrained WMNLab indigo/gold/grey only for
  shape fills, outlines, separators, and semantic route accents.
- Keep content inside the safe region `x=0.65..12.85 in`,
  `y=1.05..6.62 in`; do not cover the logo, footer, or page number.
- Prefer one clear teaching sentence followed by the governing formula and a
  compact diagram. Avoid paragraphs, tiny labels, ornamental cards, and dense
  dashboards.
- Variables and mathematical symbols follow the active notation rules:
  italic letters/Greek/function variables with correct native subscript and
  superscript; digits and operators upright.
- Use single-letter mathematical subscripts/superscripts where the active
  notation requires them. Engineering field names such as `source_id`,
  `bundle_id`, `a_C2`, `s_tilde_*`, and arm IDs must not appear on slides.

No cover slide, section-divider slide, or dedicated references slide. Begin
directly with the problem/motivation slide, consistent with the binding MCRL
slide rules.

## 6. Do not wait for finished figures

Build the complete slide narrative immediately. For every slide whose final
figure is not ready:

1. create a scientifically correct editable native-shape diagram, or a
   semantic SVG draft;
2. assign it a stable asset slot such as `FIG4-1`, `FIG4-2`, ...;
3. keep the surrounding layout, title, equation, and explanatory text final;
4. record replacement instructions in `asset-manifest.md`;
5. replace the provisional carrier later only when the final figure passes the
   same semantic contract.

Do not put visible "TODO", empty image boxes, lorem ipsum, or missing-figure
warnings in the audience-facing deck. A provisional diagram must already be
presentation-usable.

## 7. Required scientific invariants

The deck must make the following unambiguous:

- One unchanged Main MODQN plus three independent training-only specialists
  `F_1`, `F_2`, and `F_3`.
- Main owns `Q_1^M,Q_2^M,Q_3^M`; each `F_j` owns only the corresponding
  `Q_j^F`. This is four logical learners and six online Q functions, plus
  target copies—not three extra full MODQNs.
- The environment reward vector remains canonical:
  `r_1` is energy efficiency, `r_2=-Psi` is association-change cost, and
  `r_3=-U` is load balancing.
- Each specialist learns its own objective, but every actually executed source
  bundle retains the complete unmodified `U x 3` reward matrix and joint
  action.
- Experience is routed; actions, Q values, parameters, votes, or intents are
  not fused.
- Main applies only its unchanged baseline reward calibration after admission.
  Specialist-private shaping, option state, certificates, and diagnostics
  never enter Main reward.
- Each source has an independent Main-consumer gate. Pass routes the complete
  bundle; fail remains shadow-only. Adverse outcomes are retained.
- A bundle carries total sample weight one and is routed to Main at most once.
- Specialists exist only in training. Evaluation and deployment execute Main
  alone. There is no auction, coordinator, post-training negotiation, voting,
  or action override.
- The method is proposed and falsifiable. It is not yet an effectiveness or
  novelty result.

Role-specific boundaries:

- **C1 / Energy-Frontier Catfish:** unchanged canonical `r_1`; LEO-native
  Phase-I source/control; EXP prefill enters only `D_1^F`; ACRM shaping is C1
  private; only later executed C1 bundles may conditionally reach Main.
- **C2 / Temporal-Continuity Catfish:** unchanged canonical
  `r_2=-Psi`; a short physical-association persistence option with explicit
  continuation, termination, and release; any EE effect is indirect and
  empirical.
- **C3 / Spatial Load-Balancing Catfish:** unchanged canonical
  `r_3=-U`; a same-satellite one-user move from a more loaded source to an
  already-active lower-load destination. With the declared inclusion
  convention, strict total-`r3` improvement occurs iff
  `U_source >= U_destination + 2`. The separate system-power quantity
  `Delta P^N(h)` is a certificate/diagnostic, never a reward. C3 may conflict
  with C2 by paying one initial intra-satellite change and is currently
  shadow-only at the Main-consumer gate.

## 8. Required slide narrative

Build an algorithm-only deck of approximately 15--17 content slides. Use the
following narrative unless live content requires a small split/merge for
readability:

1. **Why Multi-Catfish?** Multi-objective interference and the need for
   objective-specialized experience.
2. **Baseline MODQN Carrier.** Three objective value functions produce one
   feasible Main action through the unchanged scalarization/exploration path.
3. **Design Invariants.** Reward alignment, complete bundles, no action fusion,
   training-only specialists, Main-only deployment.
4. **SMC-ER Overview.** Use the current Fig. 4-1 carrier or an editable draft.
5. **Four Learners, Six Q Functions.** Use Fig. 4-2; distinguish logical
   learners, objective heads, replays, and target copies.
6. **Canonical Rewards and Atomic Experience.** Show the three rewards and the
   complete `U x 3` bundle without inventing new reward symbols.
7. **C1: Energy-Frontier Experience.** Phase-I source/control gate, C1-only EXP
   prefill, online C1, and private ACRM; use Fig. 4-3.
8. **C2: Temporal-Continuity Option.** Trigger, physical-ID hold, terminate,
   release, direct `r_2`, and dashed empirical EE interaction; use Fig. 4-4.
9. **C3: Spatial Load-Balancing Move.** Source/destination eligible loads,
   already-active destination, one-user relocation; begin Fig. 4-5.
10. **Why the `+2` Condition Works.** Show the exact total-`r3` delta derivation
    and state that the identity is unconditional while `+2` gives strict
    positivity under the declared fork.
11. **C3 Safeguards and Current Shadow Boundary.** Separate load, power, and
    service certificates; `Delta P^N(h)` is diagnostic; explain the current
    observation mismatch and shadow-only status.
12. **How the Objectives Can Affect EE.** Solid arrows for direct objective
    endpoints, dashed arrows for empirical interactions; C2/C3 do not receive
    guaranteed EE claims.
13. **Atomic Conditional Routing.** One gate per source, full-bundle admission,
    fixed quotas, unchanged Main calibration, and objective-wise Main update;
    use Fig. 4-6.
14. **Training-to-Deployment Sequence.** Phase I source preparation, Phase II
    independent collection/update/gated routing, Phase III Main-only
    deployment; use Fig. 4-7.
15. **Algorithm Walkthrough.** Present concise pseudocode with exclusive
    branches: Main-origin direct admission; only the actual source specialist
    updates; its bundle routes only on its own gate pass; failure is shadow.
16. **Ablations and Falsifiers.** C1 source/EXP/ACRM factors, C2 option controls,
    C3 load/power/joint support and shadow gate, plus zero-dose/Main-only
    comparisons. No observed result numbers.
17. **What the Proposed Method Contributes.** Three distinct reward-aligned
    experience generators, atomic conditional routing, and Main-only
    deployment—phrased as a proposed design and evaluation plan.

Do not force 17 slides if two adjacent topics remain legible at the specified
font sizes. Do not solve overcrowding by shrinking body text below the stated
hierarchy.

## 9. Figure-to-slide synchronization

Maintain `asset-manifest.md` with one row per Fig. 4-1--4-7 containing:

- figure ID and exact live source path;
- source format and whether it is editable;
- semantic-contract version/hash checked;
- slide number(s) using it;
- status: native provisional / SVG provisional / figure-reviewed / inserted;
- replacement crop/size instructions;
- last visual-QA receipt.

Figure authors may use Figma MCP, `svg-craft`, the maintained browser/3D route
at `http://127.0.0.1:8732/`, direct native PPTX drawing, or another appropriate
carrier. Choose per figure; do not force every figure into the same format.
Scientific semantics and legibility at presentation scale matter more than the
tool choice.

## 10. Required deliverables

Create at least:

- `deck-outline.md` — final English slide titles, slide purposes, formulas,
  figure slots, and claim ceiling;
- `asset-manifest.md` — live figure/deck synchronization table;
- a reproducible deck build source (`build_deck.py`, TypeScript, or the route
  selected by the installed PPTX skill);
- `exports/smc-er-algorithm-en-v0.1.pptx` or the next non-overwriting version;
- `renders/` containing every rendered slide plus a contact sheet;
- `qa-report.md` recording structural, font, overflow, package, and visual
  checks;
- `HANDOFF.md` with exact paths, hashes, remaining provisional assets, and the
  scientific claim boundary.

Keep all build assets and receipts inside the isolated project. Do not stage or
commit them unless explicitly asked.

## 11. Mandatory QA before handoff

1. Verify the template hash before building.
2. Verify the output package opens and passes ZIP/package integrity checks.
3. Confirm the output retains the template's slide size, master, layouts,
   theme, logos, footer rule, and slide-number fields.
4. Audit every authored Latin text run for Times New Roman.
5. Audit titles `<=28 pt`, normal body near `24 pt`, diagram/text-box labels
   `20 pt`, and only the documented reference exception at `14 pt`.
6. Audit for overflow, overlap, clipping, off-canvas objects, and footer/logo
   collisions.
7. Confirm equations and prose remain editable; no text/formula is embedded as
   a raster image.
8. Render all slides to full-resolution images and inspect the contact sheet,
   then inspect every dense or equation-heavy slide individually. Revise any
   visual defect you can see.
9. Read the deck back structurally and check that the narrative order, symbols,
   and formulas match the live method documents.
10. Search visible text for forbidden engineering identifiers, old reward
    definitions, old P3 wording, `phi_1/phi_2`, action-fusion language,
    post-training coordination, guaranteed C2/C3 EE gains, or claims that C3
    already routes to Main.
11. Treat LibreOffice/render QA as engineering evidence only. State that final
    desktop MS PowerPoint viewing remains the human acceptance gate.

## 12. Completion condition

Do not declare completion merely because a `.pptx` file exists. The first
handoff is complete only when the full algorithm narrative is present in an
editable WMNLab deck, every unfinished figure has a scientifically correct
provisional carrier, all mandatory QA above is documented, and the deck can be
updated later by asset replacement rather than structural reconstruction.

At the end, report:

- exact deck path and SHA-256;
- slide count;
- which Fig. 4-1--4-7 assets are provisional versus reviewed;
- QA commands and results;
- any issue that still requires MS PowerPoint or scientific-author acceptance;
- confirmation that figure work continued in parallel and was not blocked by
  deck authoring.

---
