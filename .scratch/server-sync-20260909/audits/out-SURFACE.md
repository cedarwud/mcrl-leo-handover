Both mandatory parity gates failed under the required fresh-dense evaluator rule, so the cube and correlation analysis were correctly stopped.

- Nominal / best / one: expected `28.668530`, observed `31.078504`
- Realised / first / converged: expected `13.430253`, observed `31.028111`
- Peak RSS: 2.620 GiB; one Python process; niceness 15; all threads pinned to 1
- Code inspection confirms the deployed selector uses nominal dense boundary 0, not realised boundary 0.

Report: [SELECTION-SURFACE-2026-09-10.md](/home/sat/mcrl-v025-surface-ws/SELECTION-SURFACE-2026-09-10.md)

Machine evidence: [parity.json](/home/sat/mcrl-v025-surface-ws/.scratch/surface/parity.json) and [run_parity.py](/home/sat/mcrl-v025-surface-ws/.scratch/surface/run_parity.py).
