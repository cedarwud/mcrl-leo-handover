# V025 synthetic mechanism map — controller pre-declaration (2026-09-08, server clock ≈ 17:00 UTC; before any synthetic or real successor outcome)

**Role.** Engineering and mechanism evidence only, run in parallel with the real-world (TLE) matrix pipeline while the real-world provider is being built. Synthetic results support no claim, admit no training, and may not change any sealed constant, order, margin or rule of the real-world plan. Their permitted effects: (a) engine bug fixes (each logged with a KAT), (b) a written expectation, filed before the real matrix opens, of which regimes should show joint headroom — so that the real map can be read against a prior instead of post hoc.

**Grid (pre-declared).** Parametric synthetic worlds from the stage-2 synthetic path, 30 steps × 48 boundaries, geometry drifting like a LEO pass (elevation sweep 10°→60°→10° per satellite over the horizon window):
- users per visible beam: 1.5 / 4 / 8 (LOW / MID / HIGH occupancy);
- visible satellites per user: 2 / 4 (SPARSE / DENSE);
- co-colour interference coupling: weak (cross-gain −25 dB relative to direct) / strong (−12 dB);
- 3 world seeds per cell → 36 synthetic worlds.
Settings: the five architecture baselines only (`a-r0, a′-r0, a-γ0, b0, a′-γ0`); arms: the 12 stage-2 arms (incl. NULL ≡ BASE, random-feasible, nominal-greedy). Compute ≤ 10 core-hours, ≤ 4 concurrent.

**Reported per (world, setting), no thresholds:** U1 and J1 certificates, J1 − U1 (joint headroom), S0 deployable gain, the three FULL − DROP marginals, ALL_NEUTRAL, availability, handover rate, usable-energy-range diagnostic (ACM mode distribution, SE-plateau share, cap-hit share), fixed-point convergence statistics.

**Pre-registered expectations (to be scored, not tuned):** (E1) under rate-target control, joint headroom J1 − U1 grows with occupancy and with coupling; (E2) at LOW occupancy consolidation dominates and C3's marginal is ≈ 0; (E3) the fixed-RF reference `b0` shows no occupancy→energy coupling (headroom flat across occupancy); (E4) FDM `a′-r0` shows weaker occupancy coupling than TDM `a-r0` because per-user noise bandwidth shrinks with n. A wrong expectation is recorded as such.

Label on every receipt: `SYNTHETIC_MECHANISM_MAP`. Output root `.scratch/multi-catfish-v025-physics-successor/synthetic-map/`.
