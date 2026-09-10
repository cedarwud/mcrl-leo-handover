Completed [MODQN-COLLAPSE-2026-09-10.md](/home/sat/mcrl-v025-mqcollapse-ws/MODQN-COLLAPSE-2026-09-10.md).

MODQN is **not physically collapsed**:

- MODQN: `modal_frac=0.04170`, `active=68.70` beams / `7.47` satellites, `argmax_distinct=0.07470`
- Myopic: `0.05010`, `63.32 / 6.47`, `0.13920`
- 10 TRAIN scenarios × 10 steps × 100 users
- Exact training environment recovered with no detected source, TLE, or dependency drift
- Checkpoint SHA-256 matched before and after
- Peak RSS: 805,003,264 bytes; one Python process; nice 16; all BLAS threads pinned to 1
- No EE extracted, aggregated, or compared

The reusable runner is [measure_modqn_collapse.py](/home/sat/mcrl-v025-mqcollapse-ws/scripts/measure_modqn_collapse.py), with research-driven environment provenance recorded in [environment-provenance.md](/home/sat/mcrl-v025-mqcollapse-ws/.scratch/modqn-collapse/environment-provenance.md).
