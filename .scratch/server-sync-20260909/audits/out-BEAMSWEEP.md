Completed the design-phase sweep and wrote [BEAM-WIDTH-CEILING-SWEEP-2026-09-10.md](/home/sat/mcrl-v025-beam-ws/BEAM-WIDTH-CEILING-SWEEP-2026-09-10.md).

| Width | Coordination | Acceleration | Physics s/anchor |
|---:|---:|---:|---:|
| 1.66° | +1.944795% | +1.840863% | 21.968829 |
| 2.40° | +3.365834% | +8.866177% | 22.663792 |
| 3.32° | +11.506880% | +38.291632% | 27.289655 |

**Answer: yes.** Wider beams materially increase the ceilings. However, `3.32°` reduces absolute EE, served PHY, and target attainment; `2.40°` is the more plausible sampled design candidate.

The RF-cap effect is non-monotonic: `2.40°` provides partial relief, while `3.32°` does not relieve the regime overall.

All widths completed 12/12 valid anchors with certified traversals. Maximum RSS was 2.524 GiB. The research workflow pinned the adapter to PANELCEIL’s exact construction and preserved its traversal, timing, pooling, and joint-catalogue semantics. No learner was trained and no sealed artefact was changed.
