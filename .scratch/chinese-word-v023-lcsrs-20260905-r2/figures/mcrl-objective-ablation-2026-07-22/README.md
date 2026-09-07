# Current MCRL objective-ablation line figures

This directory holds the current five-arm MCRL ablation figures, separated by
their objective / y-axis:

- `r1-energy-efficiency/`: energy efficiency `r1`.
- `r2-handover-penalty/`: handover reward `r2`.
- `r3-load-balance/`: load-balance reward `r3`.

Both use the thesis-wide labels `MODQN`, `MCRL w/o experience shaping`,
`MCRL w/o reward shaping`, `MCRL w/o penalty shaping`, and `MCRL`. The raw
MODQN reference does not use Z-score; all MCRL-family arms do.

The figures are derived parameter diagnostics assembled from completed
trajectories and completed scenario sweeps. Their manifests state the selected
anchor checkpoint and every source file; they are not newly run matched sweeps.
