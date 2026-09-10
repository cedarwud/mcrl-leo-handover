Report complete: [INTERACTION-SCALE-2026-09-10.md](/home/sat/mcrl-v025-scale-ws/INTERACTION-SCALE-2026-09-10.md).

The hypothesis is refuted on this development panel:

- Median interaction-range/additive-gap ratio: **0.338757**
- Learned interaction changed **36/480 decisions**, spanning **9/20 anchors**
- Exact `psi` changed **100/480 decisions**, spanning **11/20 anchors**
- `DROP_C3` differed from FULL on **39/480 decisions**, so they are not bit-identical here
- Other arm differences: DROP_C1 **45/480**, DROP_C2 **110/480**, ALL_NEUTRAL_CONTROL **341/480**

Thus the scalar interaction route can materially move the argmax; there is no structural scale impossibility on this panel. No scale fix is presently justified as necessary. If closing the learned-versus-exact activation gap becomes a declared objective, common frozen C3 output calibration is the smallest honest design change.

The run used 24 frozen checkpoints, one Python process at nice 17, all BLAS threads pinned to one, and peaked at **1,449.703 MiB RSS**. It computed no EE and accessed no evaluation-only claim dates.

Supporting artifacts:

- [Receipt](/home/sat/mcrl-v025-scale-ws/interaction-scale-receipt.json)
- [Diagnostic source](/home/sat/mcrl-v025-scale-ws/interaction_scale_diagnostic.py)
