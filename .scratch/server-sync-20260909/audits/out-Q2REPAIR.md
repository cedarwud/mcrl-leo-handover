Completed the Q2-v2 schema repair and retest.

- Report: [Q2-SCHEMA-V2-AND-RETEST-2026-09-10.md](/home/sat/mcrl-v025-c1c2suff-ws/Q2-SCHEMA-V2-AND-RETEST-2026-09-10.md)
- Successor: [q2_schema_v2.py](/home/sat/mcrl-v025-c1c2suff-ws/q2_schema_v2.py)
- Schema digest: `506e5fd92846fa2a033d8eba92dfe418bc234bc9df441b640493817fb506eb34`
- Changed original slots: `6, 10, 14, 18`; three offset elevations added
- Effective dimension: `15 → 18`
- Sealed-head LOAO: top-1 `0.2570` vs floor `0.2450`; `R² −34.6314`
- Ordering inversion persists: sealed `0.5531 < 0.6477` linear
- Supported reading: first—Q2 features are not the binding constraint; the target or head is
- Direct exact-adapter audit: 992/992 rows matched exactly
- Tests: 3/3 passed
- Maximum measured peak RSS: `1,740,352 KiB`, below 4 GiB

No sealed artifact, production training, policy, acceptance test, or evaluation-only data was touched. No EE claim is made.
