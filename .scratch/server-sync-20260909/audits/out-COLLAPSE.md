Report written: [BASE-COLLAPSE-DIAGNOSIS-2026-09-10.md](/home/sat/mcrl-v025-probe-ws/BASE-COLLAPSE-DIAGNOSIS-2026-09-10.md).

Key result: learned q1-v2 `a0` averages `modal_frac=0.05236`, 49.07 active beams across 5.79 satellites, and `argmax_distinct=0.49070`. These values are far from the supplied sibling one-beam regime and overlap its spread proxy in mean active satellites, without assigning a categorical threshold.

The report separates run-verified, paper-derived, and inferred findings. It also documents:

- Full occupancy histograms and null-action anomalies.
- All epoch-500 seeds/checkpoints used.
- Myopic, geometric, carrier-BASE, and v1 sensitivity controls.
- Fixed `eta_ref` and realised pooled-ratio context.
- Code-level occupancy/reward/objective findings.
- The unresolved S_UNI comparator: exact anchor 0 returned `DEADLINE_FALLBACK_BASE` after a 600-second low-memory attempt, so no fallback was misreported as certified.
