# Current MCRL r3 parameter diagnostics

These six figures use the current five-arm MCRL ablation labels: MODQN,
MCRL w/o experience shaping, MCRL w/o reward shaping, MCRL w/o penalty
shaping, and MCRL. MODQN is the unnormalized reference; every MCRL-family arm
uses the Z-score substrate.

The plotted `r3` anchors are the completed per-seed trajectories at episode
1700. The scenario response is transferred from the completed KC1 raw-r3
shape. Thus, it is a derived r3 parameter diagnostic, not a newly evaluated
sweep.

Each CSV includes exactly the five plotted means at every point, so it can be
imported into OriginLab without creating extra curves. PNGs show no confidence
bands, error bars, or smoothing.
