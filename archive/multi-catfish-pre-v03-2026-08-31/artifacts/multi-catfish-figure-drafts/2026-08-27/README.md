# SMC-ER Editable Figure Drafts — 2026-08-27

This package contains nine new non-results figure drafts for Specialist Multi-Catfish Experience Routing (SMC-ER). They are editable review artifacts for the current algorithm, not adaptations of the retired one-Catfish MCRL architecture.

## Review entry points

- Static nine-up comparison: `gallery/contact-sheet.png`
- Browser gallery: `gallery/index.html`
- Figure ownership and authority: `FIGURE-MANIFEST.md`
- Visual semantics: `VISUAL-SYSTEM.md`
- Per-figure QA and open gates: `QA-REPORT.md`
- Frozen captions: `CAPTIONS.md`
- Editable figures: `svg/`
- Browser-rendered evidence: `png/`

## Rebuild and inspect

Six figures are generated from the shared semantic-SVG builder:

```bash
python3 source/build_main_figures.py
```

Fig. 4-3, Fig. 4-4, and Fig. 4-5 are directly editable semantic SVG sources. To review all nine in a browser from this package root:

```bash
python3 -m http.server 8765 --bind 127.0.0.1
```

Then open `http://127.0.0.1:8765/gallery/index.html`.

## Carrier decision for Fig. 3-1

The maintained React/R3F scene at `http://127.0.0.1:8732/` and the source workspace `/home/u24/papers/mcrl-figures` were inspected as possible visual carriers. The final draft uses a source-bound 2.5D semantic SVG because the figure's reader task is association/load/angle causality, and the editable vector carrier makes the selected and candidate links, occupied and empty beams, and physical chain easier to audit at once. The maintained 3D route remains useful for future physical-scene exploration, but it is not treated as scientific authority.

## Acceptance boundary

- Structural drawing gate: open and exercised.
- Live v0.4-R3 / v0.1-R3 authority refresh: fully reread and recorded in `QA-REPORT.md`.
- SVG validation and browser rendering: passed as engineering evidence.
- Human scientific review: pending.
- Manuscript-scale PDF/desktop font review: pending.
- Camera-ready/final-figure handoff: not open.
- Chapter 5 and all result values: untouched.
