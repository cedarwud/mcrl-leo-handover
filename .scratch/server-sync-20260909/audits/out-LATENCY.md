Completed [SELECTOR-LATENCY-2026-09-10.md](/home/sat/mcrl-v025-harness-ws/SELECTOR-LATENCY-2026-09-10.md).

Key result: median **12.014 s**, worst **24.079 s**, with **13/20 misses (65%)**. Catalogue construction dominates at 8.299 s median and 19.184 s worst; it alone exceeded 10 s on 9 anchors.

Also recorded:

- Same-panel 10 s anytime exact comparator: **15.336646 Mbit/J**, reused without recomputation.
- Peak RSS: **1,490.422 MiB**.
- One process, `nice -n 15`, all BLAS/OpenMP threads pinned to one.
- Substantial concurrent machine load disclosed.
- Epoch-2000 Q1/Q2 checkpoints used; synthetic correctly shaped C3 heads used because archived C3 inputs are 117-wide while the deployed context is 240-wide.
- Verified, paper-derived, and inferred findings are separated.

Supporting artifacts: [benchmark](/home/sat/mcrl-v025-harness-ws/harness/selector_latency.py) and [receipt](/home/sat/mcrl-v025-harness-ws/receipts/selector-latency-full20.json).
