# Paper lane B v2 (Claude Opus 5, headless): figures on the wmnlab template and a deck built on the existing 38-page storyboard

Sources on the server:
* `/home/sat/mcrl-paper-sources/multi-catfish-teaching-deck-v023-20260905-r1/agy-pilot/STORYBOARD.md` — the 38-page content skeleton (authority for the story arc), plus `PILOT-SLIDE-SPEC.md`, `SCIENCE-CLAIM-MAP.md`, `MATH-TOKEN-INVENTORY.json`, `CORE-FLOW-DRAFT.svg` and the three `wmnlab-template-slide-*.png` style references.
* `/home/sat/mcrl-paper-sources/multi-catfish-teaching-deck-v023-20260905-r1/pilot-build/` — `lc-srs-pilot-native-v4.pptx` (the wmnlab style and **native OMML equation** template), `build_pilot.py` and `native-formulas.json` (the existing build pipeline — reuse it rather than inventing another).
* The symbol authority `/home/sat/mcrl-paper-sources/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md`.
* The sealed successor documents under `/home/sat/mcrl-hub-copy/.scratch/multi-catfish-v025-physics-successor/` and the angle→power→EE note under `…/multi-catfish-v023-controller-handoff-20260907/angle-power-ee-20260908/`.
Output only into `/home/sat/mcrl-hub-copy/.scratch/multi-catfish-v025-paper-lane-20260909/figures/` and `…/slides/`. Never modify anything under `/home/sat/mcrl-paper-sources/` or `docs/`.

1. **`STORYBOARD-DELTA.md`** — go through the 38 pages and mark KEEP / REWRITE / DELETE / NEW against the successor design, one line of reason each; list the pages whose content is invalidated by the physics succession (segment-anchored power, LC-SRS teacher C3, the old service rule) and what replaces them.
2. **Figure 1 (mechanism)** — recompute from the sealed equations (do not copy numbers): required RF power and energy efficiency versus off-axis angle, curves for n_b = 1, 2, 4 under the primary architecture plus the fixed-RF reference, cap and cap-hit angle marked; PDF + SVG + PNG and `figure1-data.csv`; symbols exactly as in the authority table; Chinese axis labels matching the thesis.
3. **Figure 2 (architecture)** — extend `CORE-FLOW-DRAFT.svg`'s visual language: tape → per-user rows → the two heads → per-user proposal → set-level layer over the bounded catalogue → validation → execution → 48-boundary endpoint, with the information boundary and the deadline/fallback path drawn explicitly.
4. **`FIG3-SPEC.md`, `FIG4-SPEC.md`** — exact specifications (axes, units, interval definition and sidedness, receipt fields) for the two result figures, so they can be produced the moment results exist.
5. **Deck** — using `build_pilot.py` and the native-formula pipeline, produce `slides/v025-deck-skeleton.pptx` on the wmnlab template: the storyboard's arc updated per your delta, with native OMML equations for the successor's key formulas, `⟨結果待填⟩` placeholders where results go, and one line of speaker notes per slide. Also write `slides/OUTLINE.md` mirroring it in Markdown.
No result numbers anywhere.
