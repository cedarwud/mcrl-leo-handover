# Read-only probe: C2 `q2_delta` precision on the real R7 source panel (2026-09-07 11:33 UTC)

Script: `probe_q2_delta_precision.py` (this directory), run against `/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1`
from the isolated R7-era checkout copy; numpy only; writes nothing. Tolerance = the frozen verifier's
`max(1e-12, 1024*eps*max(1,|x|))`.

| world | c2 rows | float64 recompute fails | float32 writer-style fails | max |ser−f64| | max |ser−f32| | target-delta fails |
|---|---:|---:|---:|---:|---:|---:|
| 2026121801 | 96 | 9 | 0 | 2.98e-08 | 0.0 | 0 |
| 2026121802 | 83 | 11 | 0 | 2.98e-08 | 0.0 | 0 |
| 2026121803 | 85 | 11 | 0 | 2.98e-08 | 0.0 | 0 |
| 2026121804 | 86 | 11 | 0 | 5.96e-08 | 0.0 | 0 |
| 2026121805 | 82 | 14 | 0 | 4.47e-08 | 0.0 | 0 |
| 2026121806 | 102 | 8 | 0 | 2.98e-08 | 0.0 | 0 |
| 2026121807 | 72 | 9 | 0 | 2.98e-08 | 0.0 | 0 |
| 2026121808 | 82 | 16 | 0 | 2.98e-08 | 0.0 | 0 |
| **total** | **688** | **89** | **0** | 5.96e-08 | **0.0** | 0 |

Every stored `q2_values` array is exactly float32-representable (`q2_is_exact_float32: true` for all
worlds). Conclusion: defect 6 is entirely the float32-vs-float64 subtraction path; recomputing each
member delta in float32 as the writer does reproduces the serialised values bit-for-bit (max diff 0.0),
so R4's third correction (`_install_q2_delta_precision`) is the right and sufficient fix and the frozen
1e-12 tolerance stays untouched. The second scratch inventory ("R4B") did not exercise this correction
because the inventory harness at that time installed only the first two R4 hooks; it is being extended.
