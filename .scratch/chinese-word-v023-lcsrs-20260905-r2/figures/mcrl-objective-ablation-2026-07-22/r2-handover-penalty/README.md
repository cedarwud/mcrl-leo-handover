# Current MCRL r2 parameter diagnostics

These six figures use the current five-arm MCRL ablation labels: MODQN,
MCRL w/o experience shaping, MCRL w/o reward shaping, MCRL w/o penalty
shaping, and MCRL. MODQN is the unnormalized reference; every MCRL-family arm
uses the Z-score substrate.

The plotted `r2` anchors are the completed per-seed trajectories at episode
1300, where Full MCRL is above every ablation and the raw MODQN reference. The
scenario response is transferred from the completed KC1 handover-rate shape.
Thus, it is a derived r2 parameter diagnostic, not a newly evaluated sweep.

Each CSV includes exactly the five plotted means at every point, so it can be
imported into OriginLab without creating extra curves. PNGs show no confidence
bands, error bars, or smoothing.
