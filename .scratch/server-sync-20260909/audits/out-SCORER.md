Implemented and smoke-tested the dual-axis scorer.

- Scorer: [score_stagec_checkpoints.py](/home/sat/mcrl-v025-selector-ws/scripts/score_stagec_checkpoints.py:1)
- Required handoff: [DUAL-AXIS-SCORER-2026-09-10.md](/home/sat/mcrl-v025-selector-ws/DUAL-AXIS-SCORER-2026-09-10.md:1)
- Tests: [test_dual_axis_scorer.py](/home/sat/mcrl-v025-selector-ws/tests/stagec_v025/test_dual_axis_scorer.py:1)
- Smoke result: [dual-axis-scores.json](/home/sat/mcrl-v025-selector-ws/.scratch/dual-axis-scorer-smoke-20260910/dual-axis-scores.json)

Smoke results:

- Checkpoint SHA-256 matched `bcf99d…10428`.
- F6: 9 rows.
- F7: 5 rows.
- F8: 5 rows.
- Knockout check ran on 3/3 anchors.
- One Python process, niceness 15, BLAS threads pinned to 1.
- Peak RSS: `71,094,272` bytes.
- Scorer tests: `3 passed`.

The training runner still hashes to `4885570b…7d66` and was not modified. It records neither per-arm physics evaluations nor wall-clock-to-decision, so those fields are explicitly unavailable and never estimated.

A broader pre-existing Stage-C test remains failing in `build_coalition_row` due to a capped-decomposition mismatch. It is unrelated to the scorer and was left unchanged.
