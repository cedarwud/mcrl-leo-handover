Completed the design-phase measurement and wrote the report:

[CROWDING-COST-2026-09-10.md](/home/sat/mcrl-v025-crowd-ws/CROWDING-COST-2026-09-10.md:1)

Key result: pooled `d(EE)/d(active) = −425,009.885 bit/J/beam`; EE falls 83.19% from 8.00 to 98.25 mean active beams, with no panel-level sign flip. Therefore crowding is cheap and the sibling project’s collapse diagnosis does not generally transfer.

The controlled exception is N=2: spreading 1→2 beams raises EE 60.80% and saves 32.62 J. The sign flips between N=2 and N=4; sharing wins at N=4 and N=8.

The audit also found that the recorded max-per-beam model is legacy behavior. Current `a-r0` uses full-band TDM, nonlinear slot-integrated PA energy, and frequently reaches the explicit 1.65 W cap.

Supporting artifacts:

- [Measurement receipt](/home/sat/mcrl-v025-crowd-ws/.scratch/crowding-cost/crowding-cost-receipt.json)
- [Execution log](/home/sat/mcrl-v025-crowd-ws/.scratch/crowding-cost/run.log)
- [Reproduction harness](/home/sat/mcrl-v025-crowd-ws/.scratch/crowding-cost/run_crowding_cost.py:1)

Run used one Python process at `nice=15`, all BLAS threads pinned to one, and peaked at 1.649 GiB RSS. The diagnosis workflow kept code facts, runtime measurements, derivations, and conclusions explicitly separated.
