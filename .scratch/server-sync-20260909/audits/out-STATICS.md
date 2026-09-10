Completed [STATIC-BASELINE-FAMILY-2026-09-10.md](/home/sat/mcrl-v025-rank-ws/STATIC-BASELINE-FAMILY-2026-09-10.md).

Key results:

- `RANDOM`: 11.233999 Mbit/J
- `ROUND_ROBIN`: 3.441227
- `RSS_MAX`: 41.621560
- `MYOPIC_GREEDY`: 28.668530
- `NEAREST_ELIGIBLE`: 11.027760 — parity passed
- `FIRST_IMPROVEMENT_FP`: 13.430253 — parity passed

Notably, `ROUND_ROBIN` is 69.37% below random despite minimal concentration; it fails through over-dispersion and high energy use, not crowding. Conversely, `RSS_MAX` serves 1200/1200 and substantially exceeds the designated strong-search comparator.

Machine evidence is in [statics-receipt.json](/home/sat/mcrl-v025-rank-ws/.scratch/statics/statics-receipt.json) and [run_statics.py](/home/sat/mcrl-v025-rank-ws/.scratch/statics/run_statics.py). Peak RSS was 2.517 GiB using one nice-15, single-threaded Python process.
