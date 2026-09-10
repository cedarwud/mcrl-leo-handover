Completed [LR-CONVERGENCE-SWEEP-2026-09-10.md](/home/sat/mcrl-v025-c1c2-ws/LR-CONVERGENCE-SWEEP-2026-09-10.md).

Key result: no tested learning rate was admissible for C1, C2, or C3 by epoch 500; all remained finite, but none satisfied the predeclared stabilization criteria. Thus none of the current literals is admissible and the 500-epoch horizon is inadequate.

Validation passed for all 21 cells and 105 requested checkpoints. Peak RSS was `113,016 KiB`; one nice’d Python process was used. `learner.py` and all inputs remained unchanged. Machine results are in [results.json](/home/sat/mcrl-v025-c1c2-ws/.scratch/lr-convergence-sweep/results.json).
