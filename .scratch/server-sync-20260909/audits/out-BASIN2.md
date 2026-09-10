Completed [BASIN-BARRIER-2026-09-10.md](/home/sat/mcrl-v025-basin-ws/BASIN-BARRIER-2026-09-10.md).

Key results:

- Minimum barrier: `k = 1` at 12/12 anchors.
- Exact-F and pooled-EE rankings disagree.
- First-improvement from RSS_MAX: `31.812902363951235 Mbit/J`, 1200/1200 served.
- RSS_MAX is not a unilateral fixed point at any anchor.
- Scalar evaluator calls: `0`.
- Peak RSS: `2.736 GiB`.
- Canonical [receipt](/home/sat/mcrl-v025-basin-ws/.scratch/basin2/basin2-receipt.json) validated successfully.

The research workflow’s evaluator audit led to using a thin fail-closed driver because STATICS2’s warmup did not satisfy the stronger “BASE together with candidates” rule.
