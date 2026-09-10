Completed the diagnostic report:

[APPROACHING-THE-INSTRUMENTS-2026-09-10.md](/home/sat/mcrl-v025-approach-ws/APPROACHING-THE-INSTRUMENTS-2026-09-10.md)

Key findings:

- `nominal_gain` is not expressible from Q1-v2/Q2-v2 inputs. Minimal repair: one per-option log nominal-gain field.
- Median `a0→RSS_MAX` Hamming distance: **92.5/100**.
- Against RSS, every differing learned choice has lower gain.
- Against CROWDCOST, **99.13%** of differing learned choices use a less-occupied beam.
- RSS is catalogue-unreachable in **161/192** checkpoint-anchor cases. The 31 exceptions use the special 100-user S0 profile.
- Proposed binding changes: **C1 feature, C2 target, C3 candidate**; optimisation remains secondary.

Machine evidence: [results.json](/home/sat/mcrl-v025-approach-ws/.scratch/approaching-instruments/results.json)

All acceptance checks passed. The run used one Python process, niceness 15, single-threaded BLAS, and peak RSS **1.712 GiB**. The research workflow’s independent schema audit also caught and documented that the frozen checkpoints use the older v1 schemas, not Q1-v2.
