# Differential-audit completion criterion

The audit is complete only when one deterministic command:

1. independently recomputes the documented physics for three
   `DIFF_AUDIT/world/{1..3}` worlds, 100 users, 30 steps, and each of the
   stay-if-possible, nearest-eligible, and random-masked carriers;
2. records every environment/reference discrepancy above `1e-6`, including
   a first-divergence witness and source location;
3. replays 200 stored C1 and 200 stored C2 labels and the three named
   2026-08-31 regressions;
4. compares the executed and declared C3 oracles on one synthetic world; and
5. emits `DIFFERENTIAL-AUDIT-REPORT-2026-09-08.md` (at most 250 lines) plus
   machine-readable evidence without modifying `src/` or any sealed file.

The command must have been run at least twice with identical evidence hashes.

