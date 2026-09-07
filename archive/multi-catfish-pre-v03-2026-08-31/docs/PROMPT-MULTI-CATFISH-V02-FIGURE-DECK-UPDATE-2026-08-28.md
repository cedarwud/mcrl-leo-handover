# GPT prompt — update figures and English deck to Multi-Catfish MCRL V0.2

```text
[non-heavy | current environment | figure/deck authoring and QA only]

Goal

Update the existing Multi-Catfish figures and English algorithm deck now. Do
not wait for the 1500/3000EP trend experiments. Produce a new versioned review
package that accurately depicts the frozen V0.2 mechanism while keeping all
unmeasured performance claims explicitly provisional.

Authority

Read these files before editing, in this order:

1. /home/u24/papers/mcrl-leo-handover/docs/CATFISH-V0.2-OBSERVABLE-SUPPORT-SPEC-2026-08-28.md
2. /home/u24/papers/mcrl-leo-handover/docs/CATFISH-V0.2-OBSERVABLE-SUPPORT-FREEZE-2026-08-28.json
3. /home/u24/papers/mcrl-leo-handover/artifacts/multi-catfish-v02-support-census-20260829-r8.json
4. /home/u24/papers/mcrl-leo-handover/artifacts/multi-catfish-v02-zero-dose-parity-20260829-r6/zero-dose-parity.json
5. /home/u24/papers/mcrl-leo-handover/docs/THREE-CATFISH-EE-POSITIVE-ACCEPTANCE-CONTRACT-V0.1-2026-08-28.md

Treat older SMC-ER prompts, future-rollout certificates, V3 four-offset power
screens, and all-head donor diagrams as historical material, not authority.
Inspect the current editable sources, review package, and deck, including:

- /home/u24/papers/mcrl-leo-handover/artifacts/multi-catfish-figure-drafts/
- /home/u24/papers/mcrl-leo-handover/artifacts/smc-er-algorithm-en-20260827/
- /home/u24/papers/mcrl-figures/new/SMC-ER-review-2026-08-28/, if readable
- /home/u24/papers/mcrl-leo-handover/docs/PROMPT-MULTI-CATFISH-MCRL-DIAGONAL-FIGURE-DECK-UPDATE-2026-08-28.md only as an obsolete-delta checklist; current V0.2 authority wins on every conflict

Frozen mechanism facts

- Public method name: “Multi-Catfish MCRL”. “SMC-ER” may remain only in legacy filenames or provenance notes.
- There are three independent specialist Q-networks, one per Main objective:
  C1 uses Q_1^F and may inject only into Q_1^M;
  C2 uses Q_2^F and may inject only into Q_2^M;
  C3 uses Q_3^F and may inject only into Q_3^M.
- Main canonical replay updates all three Main heads. Each specialist transition is stored as a complete atomic U x 3 canonical reward bundle, but the donor gradient is strictly diagonal. For C2/C3, only the authorised focal row contributes to the donor loss; nonfocal rows are audit-only/no-gradient. C1 uses all admissible joint rows.
- The Main donor rule is the matching-head loss blend
  (1-beta)L_j^Main + beta L_j^Cj, with no dose borrowing. beta=0.25 is a frozen pilot parameter, not a proved optimum.
- At evaluation/deployment all Catfish doses are zero. Main alone scalarizes Q_1^M, Q_2^M, Q_3^M and chooses the final action. There is no voting, auction, coordinator, action fusion, reward fusion, parameter fusion, or post-training coordination.

Required role depictions

C1 — direct EE Catfish

- Preserve the RIS-lineage EXP/ACRM concept: an informed Q_1^F source, a masked-uniform neutral control, private EXP prefill in D_1^F, private ACRM comparison against detached Main, unchanged canonical r_1 entering Main, and conditional routing only to Q_1^M.
- Do not depict the LEO source as a literal RIS DFT/WMMSE solver.

C2 — activation-onset continuity Catfish

- Trigger from current observable state only when detached frozen Main leaves a valid incumbent for a destination whose lagged demand is zero.
- The focal support is the incumbent plus other valid warm actions whose lagged demand is at least one; it must contain at least two actions. The incumbent itself is not required to be warm.
- Q_2^F selects inside that support and binds the selected physical (NORAD, cell) identity for a fixed H=3 behavior option with remapping and explicit termination.
- C2 learns unchanged canonical r_2=-Psi_u and routes only the focal-row donor loss to Q_2^M.
- Do not draw future rollout, useful-bit forecast, EE-surplus admission, or realised-outcome filtering as online eligibility.

C3 — same-satellite load-relocation Catfish

- Trigger from current observable state only when detached frozen Main stays on the incumbent source.
- Candidate destinations are different valid beams on the same satellite, already warm, with source lagged demand at least destination lagged demand plus two.
- The support contains explicit defer-to-Main/source plus qualifying destinations. A selected relocation binds the physical identity for H=3.
- C3 learns unchanged canonical r_3=-U_b and routes only the focal-row donor loss to Q_3^M.
- Realised service failure may terminate the behavior option, but it never filters the already executed transition from replay.
- Do not depict the old V3 four-offset power certificate, useful-bit nonloss test, strict EE-surplus test, or post-outcome acceptance as current runtime logic.

Evidence and claim boundary

- The support census establishes only that C2/C3 observable choices occur. It does not establish useful rewards or EE improvement.
- The 1EP/2EP runs establish plumbing, isolation, persistence, and parity only. They are not efficacy results.
- Fable Max issued GO_SHORT_PILOT, not GO_9000 and not a superiority verdict.
- Label the mechanism “proposed”, “conditional”, “falsifiable”, or “awaiting matched Main-only EE evidence” where appropriate.
- Do not claim validated EE improvement, novelty, superiority, statistical significance, or that the full C123 arm is already best.
- Do not add invented Chapter 5 curves, values, confidence intervals, or performance arrows. Leave results panels as clearly marked placeholders for held-out Main-only ratio-of-sums EE.
- Reserve two clearly provisional result slots: (a) Main-only EE versus users
  for the final checkpoint and (b) Main-only EE versus training episode from
  mandatory 100EP checkpoints.  Do not populate either slot until measured
  server artifacts exist.

Work

1. Audit every existing figure, caption, legend, deck slide, manifest entry, and explanatory note against the authority above.
2. Update Fig. 4-1 through Fig. 4-7 and any other affected overview/operator/routing/deployment figures. Preserve editable sources and formulas.
3. Update the English deck, especially slides 1 and 3–17 where affected. Use the existing wmnlab.pptx visual template. Use Times New Roman; title size no larger than 28 pt, body preferably 24 pt, and dense diagram text boxes 20 pt.
4. Use any suitable mix of editable PowerPoint objects, SVG, Figma MCP, svg-craft, 2D/3D rendering, or raster assets. Choose by clarity; do not block deck work while waiting for bespoke figures. Temporary native PowerPoint blocks are acceptable if labelled and replaceable.
5. Preserve the prior package as history. Write a new versioned output directory and do not overwrite accepted or review artifacts in place.
6. Update figure/deck manifests, authority hashes, changelog, and QA report. State exactly which files and slides changed.

Visual semantics

- Distinguish environment trajectories, replay storage, no-gradient audit paths, and gradient paths by line style and legend; do not rely on color alone.
- Make focal-user scope visible for C2/C3 and joint-row scope visible for C1.
- Show physical-ID option continuation separately from eligibility/admission.
- Keep all formulas editable. Follow the thesis symbol table and its single-letter/subscript convention; list any unavoidable new symbol before using it.
- Prefer one coherent system overview plus role-specific detail figures over repeating the full architecture on every slide.

Success and QA

- Render every revised SVG/PNG/PPTX/PDF and inspect the actual pixels at normal presentation size.
- Check clipping, overflow, font substitution, unreadable text, connector ambiguity, wrong arrow direction, and color-only distinctions.
- Run available figure/deck structural validators and include their receipts, but do not equate validator success with scientific acceptance.
- Deliver editable sources, rendered PNG/PDF previews, contact sheets, manifest, changelog, and a concise QA report.
- End with a table mapping each frozen V0.2 fact to the exact figure(s) and slide(s) that communicate it, plus a separate list of items intentionally deferred until 1500/3000EP evidence exists.

Autonomy and stop rule

Proceed without asking about ordinary layout choices. Stop only if a controlling authority file is missing/unreadable or two controlling files materially conflict. Do not run training, modify Chapter 5 result data, or promote any empirical claim.
```
