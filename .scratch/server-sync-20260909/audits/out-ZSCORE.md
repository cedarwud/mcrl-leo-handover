Completed the design-phase exploration and wrote the full report:

[ZSCORE-VIEW-AND-TRAINING-2026-09-10.md](/home/sat/mcrl-v025-design-ws/ZSCORE-VIEW-AND-TRAINING-2026-09-10.md)

Key results:

- Z view: **29.948640 Mbit/J**, `modal_frac` **0.067240**
- Q1-v2 non-z: **29.176924 Mbit/J**, `modal_frac` **0.055469**
- Q1-v1 non-z: **26.829317 Mbit/J**, `modal_frac` **0.076563**
- Z versus Q1-v2: **+0.771716 Mbit/J**; active beams, satellites, and distinct argmax indices increased, but modal share also increased.
- All results materially exceed the **11.027760 Mbit/J** weak-static floor.

The real corpus reader passed through the in-process successor adapter, all five arms completed 16 seeds × 500 epochs, sealed head literals remained unchanged apart from schema-derived input widths, no physics was regenerated, and no process exceeded **1,787,658,240 bytes peak RSS**. No sealed artifact was modified.
