Completed the exact factorial run.

Demand-capped headline:

- C1 alone vs `BASELINE`: **+10.80% — positive**
- C2 alone vs `BASELINE`: **+0.45% — positive**
- C3 alone vs `BASELINE`: **−0.06% — negative**

Therefore, **not all three single-route marginals are positive**.

Conditional marginals:

- `FULL − DROP_C1`: **+17.10% — positive**
- `FULL − DROP_C2`: **exactly 0.00% — zero**
- `FULL − DROP_C3`: **+5.62% — positive**

Pair marginals versus baseline:

- `DROP_C1`: **−0.06% — negative**
- `DROP_C2`: **+17.03% — positive**
- `DROP_C3`: **+10.80% — positive**

Interaction differences, conditional minus standalone:

- C1: **+6.30 percentage points**
- C2: **−0.45 percentage points**
- C3: **+5.68 percentage points**

Every number is a ceiling: exact terms, not learned predictions. `BASELINE` remains the committed nearest-eligible incumbent, not `ALL_NEUTRAL_CONTROL`.

The first-anchor peak RSS was **0.432 GiB**; overall peak was **0.936 GiB**, using one serial Python process. FULLSPAN’s existing arms reproduced exactly.

Files:

- [Full report](/home/sat/mcrl-v025-arch-ws/ORACLE-FACTORIAL-2026-09-10.md:1)
- [Machine results](/home/sat/mcrl-v025-arch-ws/.scratch/oracle-factorial/results.json)
- [Reproduction runner](/home/sat/mcrl-v025-arch-ws/scripts/run_oracle_factorial.py:1)

Results SHA-256: `99445de46db39251583b77e9f1aafdcfc288da4701459c4e4058206db6db4209`.
