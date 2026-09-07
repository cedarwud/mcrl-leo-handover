# H-A hold-horizon focal segment-timing surplus — development census

Read-only diagnostic. Nothing was written into `/home/u24/papers/mcrl-leo-handover`.
Machine-readable companion: `census-result.json`; raw arrays: `census-raw.npz`;
rollout metadata: `census-meta.json`.

## 0. Setup actually used

| item | value |
|---|---|
| evaluation seeds (worlds) | 2026090211 … 2026090216 (no collision found under `artifacts/` or `.scratch/`; block used unshifted) |
| initialization lineages | 2026092101, 2026092102, 2026092103 (gate-selected rung-100 hybrids) |
| behaviour policy | `DROP_C2` = argmax(Q1+Q3) under the common legal mask (verified byte-identical to `five_arm.route_actions(..., "DROP_C2")` on 2000/2000 decisions) |
| anchors | 18 episodes x 10 steps x 100 users = **18 000** |
| lambda0 | `84994621.12635651` = `0x1.443a8f481639ap+26` bits/J, from `.scratch/c3-v04/run_v04_c3_source.py:102` (`LAMBDA_BITS_PER_J`) — reused, never recomputed |
| kappa | `10097071012.757404` = `0x1.2cea89d260f2ap+33` bits, from `trainer.v04_config.kappa_bits` |
| dt | 30.08 s (`driver.config.ephemeris.time_step_s`) |
| p0 / p_max | 0.825 W / 1.65 W |
| horizon | k = 1, 2, 3 |
| census wall time | 173.6 s rollout + 8.6 s analysis (plus a one-off 83 s frozen-TLE view build) |

Checkpoint SHA-256 (all six files loaded):

```
hybrid-2026092101-selected-rung-000100.pt  efc460a785194d189d085df794dc47292798b606871587beb36f073f91ea2171
hybrid-2026092102-selected-rung-000100.pt  019e2160ed7c3802c142a92d4b391d63a0d2e3c0b7cfc0478ab6dbfd0b1178fc
hybrid-2026092103-selected-rung-000100.pt  c0da537690a1ce1be1992ed62ea1972cf34cd6f86553bbe4e0065fd40d3fe377
init-2026092101-rung-000010.pt             f26aab2fab6d31d6f3e4acd97782beeb0bba055ec94611dc9f3ed47038a231f0
init-2026092102-rung-000010.pt             6930534d90840807c4dda1eda9c0ecf58793175053a37a43b75e38a7b6d310ba
init-2026092103-rung-000010.pt             507b871f2536097b400b099b9dcb666e8445e9aee921001d61e70ff6042646b2
```

The strict cross-artifact hash authentication of the five-arm evaluator was **skipped**
(`run_v04_c3_source._validate_source_manifest` refuses: the working tree's source
closure has drifted from the sealed V0.4 manifest). `screen.authenticate_gate` was
called with `source_dir=None`, which still authenticates the gate authority, result
seal, and the per-seed checkpoint SHAs.

### Physics identities validated in-line

* `driver.satellite_ecef_at(0)` vs `candidates.window_satellite_ecef_km`: max deviation **1.02e-10 km** over all anchors — the offset indexing is confirmed to be on the decision clock.
* `transmit_gain_linear(theta_a(t))` recomputed from ECEF vs the observation's own `off_axis_deg`: max relative deviation **5.5e-10**.
* `observation.step_index` matched the loop index at every anchor (0 mismatches).
* Forward-geometry guard removed **zero** legal actions (audit: 51 583 mask entries == 51 583 census-legal entries, 0 rows with attrition).

## 1. Coverage

* 18 000 anchors, 468 391 legal (anchor, action) pairs.
* Legal-action count distribution: **28 legal** at 12 913 anchors (71.7 %), **21 legal** at 5 087 anchors (28.3 %). Nothing else occurs — the 7-action deficit is one unoccupied satellite slot.
* Step-0 anchors: 1 800 (10 %).
* Empty-mask anchors: **0**.
* Anchors with an incumbent (a previously served association present in the table): 15 777 (87.7 %); the incumbent was legal in 100 % of those.
* Legal actions with a zero `candidate_sinr` (the inversion flag): **0**.

## 2. Geometry headroom

Percentiles of the gain ratio `G_a(k)/G_a(0)` over all (anchor, legal action):

| offset | p5 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|---|
| k=1 | 0.933 | 1.102 | **1.354** | 2.066 | 6.60 |
| k=2 | 1.021 | 1.218 | **1.734** | 3.545 | 23.10 |
| k=3 | 1.037 | 1.292 | **2.009** | 4.858 | 43.22 |

The median candidate beam's transmit gain **rises** over the horizon (the satellite is
still closing on the cell), so holding usually gets *cheaper*, not more expensive.

Fraction of legal actions whose hold becomes infeasible:

| by k=1 | by k<=2 | by k<=3 |
|---|---|---|
| **1.956 %** | 1.977 % | 1.977 % |

Hold-horizon distribution over legal actions: h=3 in 98.02 %, h=1 in 0.02 %, h=2 in
0.00 %, h=0 in 1.96 %. Infeasibility is effectively **binary and immediate**: an action
that survives k=1 survives k=3.

Incumbent (continue) action: infeasible at k=1 in **0.038 %** of anchors with an
incumbent (6 of 15 777). The already-compensated segment is essentially never the one
that dies.

## 3. Within-anchor action-specific headroom

| quantity (kappa units) | median | IQR |
|---|---|---|
| std of ZETA2/kappa over legal actions | **1.719** | [1.506, 1.933] |
| range of ZETA2/kappa | **6.009** | [5.428, 6.688] |
| std of Q1+Q3 | **0.245** | [0.202, 0.292] |
| range of Q1+Q3 | 0.955 | [0.790, 1.098] |

* Median ratio `std(ZETA2/kappa) / std(Q1+Q3)` = **6.92**.
* Fraction of anchors with a strictly nonzero within-anchor ZETA2 range: **100 %**.
* Within-anchor Pearson correlation between ZETA2/kappa and Q1+Q3: median **0.545**, IQR [0.325, 0.738].
* argmax(ZETA2) == argmax(Q1+Q3) at **37.6 %** of anchors.

The target has real, action-specific structure at every single anchor — the failure mode
of the five previous realized-residual C2 designs (no decision-time discriminability) does
not appear here. But its natural scale is ~7x the trained Q1+Q3 spread, so a naive
unit-weight route sum would be dominated by Q2.

## 4. Positive alternatives

* Some legal `a != a_taken` has a strictly larger ZETA2 at **62.4 %** of anchors.
* Median of `max_a ZETA2_a - ZETA2_{a_taken}` = **0.517 kappa** (IQR [0, 1.997], mean 1.123, p95 3.91).

## 5. Oracle flip rate (argmax(Q1+Q3+ZETA2/kappa) vs argmax(Q1+Q3))

| scaling | 2026092101 | 2026092102 | 2026092103 | pooled |
|---|---|---|---|---|
| x0.5 | 0.559 | 0.476 | 0.514 | 0.516 |
| **x1.0** | **0.608** | **0.532** | **0.571** | **0.570** |
| x2.0 | 0.635 | 0.559 | 0.594 | 0.596 |
| scale-matched (x0.1446, extra) | 0.364 | 0.302 | 0.329 | 0.332 |

The flip rate is remarkably insensitive to a 4x swing in the multiplier (0.52 -> 0.60),
which says the flips are driven by the *ordering* the target imposes, not by a knife-edge
weight. The scale-matched row (multiplier chosen so ZETA2's typical within-anchor spread
equals Q1+Q3's) is the decision-relevant figure: even then a third of decisions move.

## 6. Component decomposition

Within-anchor variance shares (covariance decomposition, `Var(Z) = Cov(Z,R) - Cov(Z,E)`):

| | median over anchors | pooled (sum of covariances / sum of variances) |
|---|---|---|
| rate term | **0.494** | 0.574 |
| energy term | **0.506** | 0.426 |

Both halves carry roughly equal weight — the target is not a disguised energy term and
not a disguised rate term.

Censoring: it binds (some legal action with h < 3) at **17.4 %** of anchors. Where it
binds its median variance share is ~0.0002 but the distribution is very heavy-tailed
(p95 = 3.45), i.e. a small set of anchors where censoring is the whole story. The pooled
censoring share is not reportable as a single number (Var of the uncensored variant is
dominated by a handful of infeasible actions whose hold power exceeds p_max).

Ranking agreement with the energy term alone: the full within-anchor ranking coincides at
**0 %** of anchors; the argmax coincides at **12.0 %**.

Incumbent positioning under the target (extra): ZETA2(incumbent) minus the anchor mean is
**+1.133 kappa** (median), the incumbent's percentile rank by ZETA2 is **0.714** (median),
and the incumbent is the ZETA2 argmax at 11.1 % of anchors. The target does prefer holding,
but not overwhelmingly.

## 7. Hold realism (Q1+Q3 behaviour policy)

* Overall: the incumbent was chosen at **35.1 %** of all decisions, **40.1 %** of decisions where an incumbent existed.

| step | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| continue rate (of those with an incumbent) | n/a | 0.467 | 0.524 | 0.481 | **0.083** | 0.530 | 0.517 | 0.396 | **0.077** | 0.509 |

Steps 4 and 8 collapse to <9 %: those are the **dwell re-anchor boundaries** (cells
re-anchor every 4 steps). The incumbent is still present in the candidate table at
~93 % of those anchors, so this is a policy effect at the boundary, not a masking effect.
Step 0 has no incumbent by construction.

| lineage | 2026092101 | 2026092102 | 2026092103 |
|---|---|---|---|
| continue rate (with incumbent) | 0.284 | 0.487 | 0.431 |

The premise of a hold-horizon target — that the policy actually holds — is satisfied for
roughly 2 of every 5 decisions, and about 1 in 2 away from dwell boundaries.

## 8. PREDICTION CHECK (validity of the deterministic forecast)

For every user served at t who is still served on the **same (norad, cell)** at t+1,
comparing the realized `link_power_w(t+1)` with the decision-time prediction
`p0 * start / G(theta_a(t+1))`:

| population | n | median rel. err | p95 | p99 | max | within 1 % | within 5 % |
|---|---|---|---|---|---|---|---|
| continue, t >= 1 | 5 485 | **0.335 %** | **1.45 %** | 2.21 % | 3.54 % | 86.5 % | 100 % |
| continue, t = 0 (warm-start affected) | 837 | 12.05 % | 35.9 % | 42.2 % | 48.7 % | 13.7 % | 29.7 % |
| switch, t >= 1 (prediction = p0 exactly) | 8 910 | 0.0 | 1.3e-16 | — | 1.3e-16 | 100 % | 100 % |
| switch, t = 0 (prediction = p0 exactly) | 954 | 0.0 | 1.3e-16 | — | 1.3e-16 | 100 % | 100 % |

**The forecast is essentially exact.** The residual on continuing links is entirely the
frozen-user-position approximation: a 250 m step at ~483 km subtends ~0.03 deg, and the
observed error band (median 0.3 %, max 3.5 %) is exactly that order. Switchers are exact
to floating point, confirming that a new segment's first step is p0 by construction.

The step-0 row is the documented exception and **not** a defect of H-A: the simulator
applies a `uniform-episode-length` segment warm start at t=0
(`PhysicsConfig.segment_warm_start`), so the committed start gain is `G(theta(tau))` for
a pre-episode tau, whereas the census — which by contract sees only decision-time state
and has no previous outcome at t=0 — uses `G_a(0)`. In deployment every anchor with
t >= 1 has the true segment in `_segments`, so the top row is the operative number.

## 9. Runtime and approximations

Runtime: 173.6 s rollout (18 episodes, ~9.6 s each) + 8.6 s analysis; one-off 83 s to
build the frozen TLE view under the scratchpad. Well inside the 30-minute budget; the
full 6-world x 3-lineage design was run (no reduction needed).

Approximations, all deliberate and all reported:

1. **Frozen user position.** Future off-axis angles use `driver.user_ecef_km()` at t for every offset k. Quantified by the prediction check: median 0.34 %, max 3.5 % on link power.
2. **Expected-value fading.** `link_power_factor(..., shadow_fading_db=0)` and Rician fade = 1 at every offset *and* in the decision-time inversion of `candidate_sinr`. Because both sides use the same convention, the SINR forecast reduces exactly to `SINR_a(t+k) = gamma_a(t) * (start / G_a(0)) * (path_a(t+k) / path_a(t))`, i.e. the decision-time fading/shadow draw is carried through multiplicatively rather than dropped.
3. **Frozen interference.** `I_a + N` is held at its decision-time value for all k.
4. **Frozen non-focal context.** `n_a`, `m_a`, `sat_active_a` come from the previous `StepOutcome` — the same one-step lag the deployed state uses. `m_a` and `n_a` exclude the focal user's own contribution when the focal user was served on that beam.
5. **Step-0 convention.** No previous outcome at t=0: every beam is empty/inactive (`n_a=0`, `m_a=0`, `sat_active=False`, so every action pays the full 0.338 W circuit + 0.200 W baseband activation) and every action starts a new segment with `start = G_a(0)`. The simulator's warm start makes this an approximation at t=0 only; 1 800 of 18 000 anchors.
6. **Authentication skipped.** As above; every loaded checkpoint is SHA-256 recorded.
