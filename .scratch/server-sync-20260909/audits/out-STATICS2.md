Completed the clean-path rebuild and wrote [STATIC-BASELINE-FAMILY-CLEANPATH-2026-09-10.md](/home/sat/mcrl-v025-rank2-ws/STATIC-BASELINE-FAMILY-CLEANPATH-2026-09-10.md).

Key results:

- Clean EE: `RANDOM` 11.233999, `ROUND_ROBIN` 3.441227, `RSS_MAX` 41.621560, `NEAREST_ELIGIBLE` 11.027760, `MYOPIC_GREEDY` 31.078504, `FIRST_IMPROVEMENT_FP` 31.028111 Mbit/J.
- Only the two search arms changed.
- Fixed-point moves increased from 699 to 4,210; clean movement occurred at all 12 anchors.
- `RSS_MAX` remains highest, at 1.341× the clean fixed point.
- `RANDOM` still beats `NEAREST_ELIGIBLE`.
- Scalar `evaluate` calls: exactly zero.
- Final run: one process, niceness 15, all numerical threads pinned to 1, peak RSS 2.629 GiB, completed before 17:05Z.

Machine evidence is in [cleanpath-receipt.json](/home/sat/mcrl-v025-rank2-ws/.scratch/cleanpath/cleanpath-receipt.json), with the reproducible driver at [run_cleanpath.py](/home/sat/mcrl-v025-rank2-ws/.scratch/cleanpath/run_cleanpath.py).
