# Controller GO checklist for the a-r0 matrix — written before the seal package exists
Recorded 2026-09-09, server clock 06:12 UTC. Written now so that the seal package's arrival adds no deliberation latency, and so that the criteria cannot be shaped by what the package happens to contain.

Writing `/home/sat/mcrl-records/AR0-SEAL-GO`, containing the seal package's sha256, is the only act that authorises the matrix. I write it only when every line below is satisfied. A line that cannot be satisfied is reported to the owner as a blocker; it is never waived by me.

## A. Physics version
1. Every executing workspace for the matrix carries the **corrected** ACM: `physics_v025/acm.py` = `aa58aeeb83c5…`, `resolution.py` = `e0b1cc50532a…`, `batch.py` = `3677d530f348…`, or their successors from a later sealed stage. Verified by hash, not by claim.
2. `m_target`, `m_tx` and `realised_outcome` are separately present in a sampled receipt. The credited mode is never read from realised post-fading SINR.
3. No file under `src/mcrl/env/` differs from the sealed baseline.

## B. Calibration
4. `eta_ref`, `lambda` and `kappa` for every setting in the package were computed **under the corrected physics**. Any value carried over from a pre-fix computation is a blocker.
5. The calibration reference policy is `nominal-greedy` as declared, and the package states the step count.
6. The package records calibration values per setting, not one global value.

## C. Sealed-contract conformance
7. The cell list and its order match the sealed priority order byte for byte: `a-r0 > a'-r0 > a-γ0 > b0 > a'-γ0`, then S, H, SH, T in the same architecture order, with U diagnostic-only.
8. Per-arm ranking keys are as amended in v1.9 §4: FULL = `C1+C3` then C2; DROP_C1 = `C3` then C2; DROP_C2 = `C1+C3` then configuration ID; DROP_C3 = `C1` then C2.
9. The margin rule is v1.9, not v1.6: the fading quantile touches only the wanted link's predicted reception, it does not re-solve power, and the product includes the Rician term.
10. The admission trichotomy `ADMIT_FULL` / `ADMIT_C1C2` / `NOT_ADMITTED` is monotone and its truth-table KAT passes.
11. Interaction labels are uncapped; only exact per-user Shapley reporting is capped at |A| <= 4.
12. There is **no TEST split** anywhere in the package.

## D. Statistics
13. The primary uncertainty statement is the two-way pigeonhole bootstrap over TLE dates by learner seeds, recomputing pooled sums per resample.
14. `delta = +0.5 %` is applied as a **relative** margin, per the v1.4 erratum.
15. The package states the learner-seed count as **16**, per contract v1.1 and the stage-C spec erratum.
16. Measured coverage is reported alongside the nominal 95 %, and the package does not present the nominal figure alone.

## E. Cost and operations
17. The projected core-hours fit the window, with the assumption behind the projection stated. A projection with no stated assumption is a blocker.
18. Checkpoints every 100 episodes are configured.
19. The launch commands are detached, cap concurrency as declared, and write logs to a dated directory.
20. Nothing in the package writes into `/home/sat/mcrl-hub`, `/home/sat/mcrl-leo-handover`, or that clone's venv.

## F. Things that are explicitly NOT gates
Loss values, oracle direction, and any pre-fix probe or pilot number carry **no** weight here. They are not evidence about energy efficiency and they do not authorise or block the matrix. A 9000-episode continuation is a separate decision that requires notifying the owner first, and this checklist does not authorise it.
