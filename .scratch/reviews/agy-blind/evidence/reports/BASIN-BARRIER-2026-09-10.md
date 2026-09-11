**The minimum improving simultaneous-change count is k = 1 at every anchor (spread 1–1; distribution 12/12 at k = 1), the six-arm exact-F order disagrees with the pooled-EE order, and clean first-improvement started from RSS_MAX reaches 31.812902 Mbit/J at 1200/1200 service.**

# BASIN2 — barrier from BASE toward RSS_MAX

Status: **design-phase diagnostic, not a claim**. This is learner-free: no learner checkpoint was read. Only the 12 frozen development anchors were used (world 1, steps 0–3, the three declared carriers); no evaluation-only claim date was read.

## Direct answer

There is no multi-user barrier on this path in this panel. Every anchor has at least 48 guarded, strictly F-improving one-user changes from BASE toward RSS_MAX; therefore the measured minimum is k = 1 in all 12 cells. The earlier search had simply not run on a clean comparison surface. No interaction term is needed merely to escape BASE toward RSS_MAX on these anchors.

The other two direct findings are:

- Objective and reported metric disagree. On the common full-48 endpoint, exact F ranks `RSS_MAX > FIRST_IMPROVEMENT_FP > MYOPIC_GREEDY > RANDOM > NEAREST_ELIGIBLE > ROUND_ROBIN`, while pooled EE ranks `RSS_MAX > MYOPIC_GREEDY > FIRST_IMPROVEMENT_FP > RANDOM > NEAREST_ELIGIBLE > ROUND_ROBIN`.
- First-improvement started at RSS_MAX is not fixed at any anchor. It converges to 31.812902363951235 Mbit/J pooled EE, below RSS_MAX's own 41.62155981714534 Mbit/J.

## Verified by running code

### Evaluator path and contamination exclusion

The executable path is [run_basin2.py](/home/sat/mcrl-v025-basin-ws/.scratch/basin2/run_basin2.py). The barrier surface is at lines 234–362 and the assertions/fail-closed hook are at lines 111–150.

For every selection surface at an anchor, the driver:

1. constructs one fresh dense `StepEvaluator` with setting `a-r0` and asserts that dense primitive arrays exist;
2. uses `boundary_indices=(0,)` (realised field for barrier, arm ranking, first-improvement and the RSS catalogue; nominal field only for the nominal MYOPIC definition and the historical C3 estimator);
3. puts BASE and actual candidates into the evaluator's first `evaluate_many` call;
4. reads profiles only from that evaluator's `_evaluated` store; and
5. globally replaces scalar `StepEvaluator.evaluate` with an exception before any tape evaluation.

The completed receipt records **0 scalar-evaluate calls**. A source search finds no call expression to scalar `.evaluate(...)` in the driver. Thus no scalar `evaluate` is reachable on a BASIN2 selection surface. C2's three future-offset projections in the conditional C3 probe use their own fresh dense `evaluate_many` evaluators; they are forecasts, not a cache reused for the current boundary-0 comparison.

At each anchor, all endpoint profiles being compared enter one separate fresh realised dense full-48 evaluator in one `evaluate_many` call ([lines 929–945](/home/sat/mcrl-v025-basin-ws/.scratch/basin2/run_basin2.py:929)).

This thin driver was necessary because the concurrent STATICS2 driver, although dense and scalar-fail-closed, initially warmed BASE alone rather than together with candidates. BASIN2 independently rebuilt both search arms under the stronger rule. All six resulting configuration IDs match STATICS2 at all 12 anchors.

### Part 1 — barrier location

`N`, `S`, and `R` abbreviate nearest-eligible, stay-if-possible, and random-masked. `Prefix k` is the first strict improvement on the prescribed ascending-user walk; it is not used as a substitute for checking every singleton. The witness is the best improving singleton after the full k = 1 layer was evaluated. Every witness preserved the BASE served-count guard.

| Anchor | BASE↔RSS Hamming | Improving singletons | Minimum k | Prefix k | Witness user | Exact witness ΔF |
|---|---:|---:|---:|---:|---:|---|
| s0/N | 100 | 75 | 1 | 1 | 24 | `224802907420021164045752417160577/26016682618076460000000` |
| s0/S | 100 | 75 | 1 | 1 | 24 | `224802907420021164045752417160577/26016682618076460000000` |
| s0/R | 99 | 71 | 1 | 2 | 44 | `11928187897291676564751235218017/1084028442419852500000` |
| s1/N | 100 | 60 | 1 | 25 | 24 | `46937884983906666234427575227351/8672227539358820000000` |
| s1/S | 100 | 52 | 1 | 38 | 1 | `4209169496332009610291562821709/542014221209926250000` |
| s1/R | 98 | 72 | 1 | 6 | 41 | `165820596214546895140062328505581/13008341309038230000000` |
| s2/N | 99 | 48 | 1 | 1 | 74 | `3777052973032604181236322135361/542014221209926250000` |
| s2/S | 100 | 50 | 1 | 1 | 24 | `19958397704952577910103753671363/2168056884839705000000` |
| s2/R | 98 | 53 | 1 | 1 | 8 | `3316560505944549432955816002359/406510665907444687500` |
| s3/N | 99 | 48 | 1 | 1 | 57 | `12868303976343185292448367999899/1626042663629778750000` |
| s3/S | 100 | 49 | 1 | 1 | 40 | `4793063135977434501535263534269/650417065451911500000` |
| s3/R | 96 | 60 | 1 | 2 | 22 | `36783729276515512890820938082739/3252085327259557500000` |

Distribution: `{1: 12}`; range 1–1. Because an improving singleton exists in every cell, no k ≥ 2 layer is needed to establish the minimum.
The condition “no one-user move toward RSS_MAX improves F” is false at all 12 anchors.

The complete prescribed trajectories are recorded without float substitution in the canonical [receipt](/home/sat/mcrl-v025-basin-ws/.scratch/basin2/basin2-receipt.json):

- `anchors[i].barrier.differing_users_ascending` is the walk order;
- `anchors[i].barrier.trajectory[k].f.rational` is exact F after the first k users are changed;
- `anchors[i].barrier.trajectory[k].delta_f.rational` is its exact difference from BASE; and
- each trajectory has `Hamming + 1` entries, covering k = 0 through RSS_MAX exactly.

The first prefix improvement is sometimes much later than the true minimum (notably 25 at s1/N and 38 at s1/S). This is why the exhaustive singleton layer matters.

### eta_ref

The exact value is

`eta_ref = 14235186615308645000000 / 1300834130903823 = 10943122.01465532 bits/J`.

It is stored in `/home/sat/mcrl-v025-c1c2suff-ws/artifacts/v025-pilot-c3-20260909-PILOT_NOT_CLAIM/PILOT_NOT_CLAIM-calibration.json`, named as `CALIBRATION_PATH` at PANELCEIL lines 30–34 and loaded as an exact `Fraction` at lines 133–145. Its origin is `_pilot_calibration` at `scripts/run_v025_pilot_c3.py` lines 274–296: realised full-grid BASE at development step 0, with `eta_ref = bits_ref / joules_ref`. That historical calibration routine uses scalar evaluation for the single calibration profile; it was not called by BASIN2, and it is not a selection comparison.

### Part 2 — objective or search?

The exact F below is the sum of the 12 exact `B - eta_ref E` values from the separate realised full-48 endpoint evaluators. The EE column pools bits and joules over the same endpoints.

| Arm | Exact full-48 F total | F rank | Pooled EE (Mbit/J) | EE rank | Served |
|---|---:|---:|---:|---:|---:|
| RSS_MAX | `7927579133825909518148442019073129/6504170654519115000000` | 1 | 41.62155981714534 | 1 | 1200/1200 |
| FIRST_IMPROVEMENT_FP | `182284015385783081025503748778277/173444550787176400000` | 2 | 31.028111070819413 | 3 | 1200/1200 |
| MYOPIC_GREEDY | `4378769067684380626595931910550149/4336113769679410000000` | 3 | 31.078503908389287 | 2 | 1200/1200 |
| RANDOM | `43402789145486438242259312296636831/1300834130903823000000000` | 4 | 11.233999490189383 | 4 | 1102/1200 |
| NEAREST_ELIGIBLE | `37316468596396753509435869902185817/4336113769679410000000000` | 5 | 11.027760227532434 | 5 | 960/1200 |
| ROUND_ROBIN | `-213751235692980220161939564068765693/130083413090382300000000` | 6 | 3.441227180663568 | 6 | 798/1200 |

**The orders disagree:** FIRST_IMPROVEMENT_FP and MYOPIC_GREEDY swap positions. This is an objective/aggregation disagreement, not a search limitation. The boundary-0 selection-F totals disagree still more: `FIRST_IMPROVEMENT_FP > RSS_MAX > MYOPIC_GREEDY > RANDOM > NEAREST_ELIGIBLE > ROUND_ROBIN`.

RSS_MAX's dominance over the clean fixed point survives in the pooled full-48 endpoint:

- bits: 1,653,612,586,626.6667 versus 1,623,572,418,389.6296 (RSS_MAX +30,040,168,237.0371);
- joules: 39,729.71205047167 versus 52,325.85427723728 (RSS_MAX −12,596.14222676561); and
- exact F difference at eta_ref: `2183857113718087959384102879775483/13008341309038230000000` > 0.

Therefore pooled `F(RSS_MAX) > F(clean fixed point)` for every `eta >= 0`, derived directly from strictly more pooled bits and strictly less pooled energy. Anchorwise at the full-48 endpoint the F sign is positive in 9 cells and negative in the three s3 cells; the dominance statement is about the pooled panel totals, matching the pooled premise.

Clean-path parity against STATICS2:

| Arm | Published EE | STATICS2 clean EE | BASIN2 clean EE | BASIN2 − published |
|---|---:|---:|---:|---:|
| RANDOM | 11.233999 | 11.233999490189385 | 11.233999490189383 | +0.000000490189 |
| ROUND_ROBIN | 3.441227 | 3.441227180663569 | 3.441227180663568 | +0.000000180664 |
| RSS_MAX | 41.621560 | 41.62155981714534 | 41.62155981714534 | −0.000000182855 |
| NEAREST_ELIGIBLE | 11.027760 | 11.027760227532434 | 11.027760227532434 | +0.000000227532 |
| MYOPIC_GREEDY | 28.668530 | 31.078503908389287 | 31.078503908389287 | **+2.409973908389** |
| FIRST_IMPROVEMENT_FP | 13.430253 | 31.028111070819413 | 31.028111070819413 | **+17.597858070819** |

The tiny direct-arm differences are only the six-decimal published rounding. BASIN2 and STATICS2 match exactly for the two rebuilt search arms and to floating summation noise (≤1.8e-15 Mbit/J) for the other four.

### Part 3 — what RSS_MAX makes reachable

Neither requested start is a fixed point in any cell.
Both runs preserve the declared algorithm: realised boundary zero, guard equal to the initial start's served count, ascending user ID, each user's declared legal-option order, the first strict F improvement, and a final complete zero-move certificate. Thus “same guard” is the same initial-start guard rule, applied to RSS_MAX or MYOPIC_GREEDY respectively.

| Anchors | From RSS_MAX moves / passes | From MYOPIC moves / passes |
|---|---|---|
| s0/N, s0/S, s0/R | 313/11, 313/11, 313/11 | 323/11, 323/11, 322/12 |
| s1/N, s1/S, s1/R | 279/10, 279/10, 279/10 | 295/9, 324/12, 267/8 |
| s2/N, s2/S, s2/R | 291/10, 291/10, 291/10 | 269/10, 261/10, 324/11 |
| s3/N, s3/S, s3/R | 255/9, 255/9, 255/9 | 307/14, 284/10, 320/11 |

The pass count includes the final zero-move certificate. Pooled realised full-48 outcomes are:

| Profile | Bits | Joules | EE (Mbit/J) | Served |
|---|---:|---:|---:|---:|
| RSS_MAX start | 1,653,612,586,626.6667 | 39,729.71205047167 | 41.62155981714534 | 1200/1200 |
| First-improvement from RSS_MAX | 1,623,313,012,293.3333 | 51,026.875628071866 | **31.812902363951235** | 1200/1200 |
| MYOPIC start | 1,558,660,774,521.4814 | 50,152.37474480677 | 31.078503908389287 | 1200/1200 |
| First-improvement from MYOPIC | 1,617,689,519,702.963 | 52,966.93469229799 | 30.541497806143457 | 1200/1200 |

The PANELCEIL bounded catalogue rebuilt around RSS_MAX contains strict F improvements at **12/12** anchors. Catalogue size is 1,029–1,137 unique profiles; 474–655 profiles per anchor strictly improve guarded boundary-0 F. The selected best profile changes four users in every cell. Its pooled full-48 EE is **41.69324093641454 Mbit/J** at 1200/1200, improving RSS_MAX by 0.07168111926920 Mbit/J.

### Part 4 — conditional C3 re-anchoring probe

Budget permitted the first four of 12 anchors. This is the historical exact oracle-head estimator, not the V0.25 set-decomposition interaction: O12 chooses per-user actions using exact C1+C2; O123 adds exact C3; C1 is focal bits minus lambda times network energy, C3 is nonfocal bits, C2 is the same exact three-offset persistence forecast, and C1/C3 are each divided once by kappa. The reported marginal is the same full-48 endpoint `EE(O123) - EE(O12)`.

| Cell | Around BASE: O12→O123 ΔEE | Sign | O12/O123 Hamming | Around RSS_MAX: O12→O123 ΔEE | Sign | Hamming |
|---|---:|---|---:|---:|---|---:|
| s0/N | −0.434917574370 | negative | 11 | 0 | zero | 0 |
| s0/S | +1.600683260550 | positive | 2 | 0 | zero | 0 |
| s0/R | −3.357195956583 | negative | 18 | 0 | zero | 0 |
| s1/N | +0.726712297246 | positive | 12 | +0.046381988036 | positive | 2 |

Pooled over these four cells, the BASE-referenced marginal is −0.527376591023 Mbit/J (56.266823987985 → 55.739447396961); the RSS_MAX-referenced marginal is −0.001385873160 Mbit/J (50.516633979005 → 50.515248105845).

**The sign of the exact interaction marginal depends on the reference profile; that is a statement about the earlier probe's scope, not a revival.** The two pooled marginals are both negative, and this diagnostic does not conclude that C3 is alive.

## Derived on paper

- Since every anchor has at least one guarded singleton with exact ΔF > 0, the minimum possible cardinality is attained: k = 1. No assumption about larger coalitions enters that conclusion.
- Strictly greater pooled bits and strictly lower pooled energy imply `B_RSS - eta E_RSS > B_FP - eta E_FP` for every `eta >= 0`; this is stronger than checking only eta_ref.
- Different orders on identical full-48 profiles establish an objective/aggregation disagreement between additive F and the pooled EE ratio. Additional search cannot make those two rankings mathematically identical.

## Inferred, not established beyond this panel

- A learned interaction term is not needed to escape BASE along the BASE→RSS_MAX direction on these 12 anchors. This does not say interactions are useless for selecting the best endpoint or on evaluation-only dates.
- Hundreds of clean first-improvement moves from RSS_MAX, coupled with lower full-48 EE after convergence, indicate that the boundary-0 additive-F search can move away from a stronger pooled-EE profile. This is consistent with the measured objective/horizon mismatch; it is not evidence from learner loss.

## Reproducibility and resource record

- Canonical receipt: [basin2-receipt.json](/home/sat/mcrl-v025-basin-ws/.scratch/basin2/basin2-receipt.json), 12/12 anchors, status `COMPLETE`.
- Receipt digest: `dee10d03e6752135527ab85e1ff6c3dbb6600ed5fdaf7b38335cc117ffacaa66` (independently recomputed and matched).
- Driver digest: `0135d54c4c3a9a0731c653f58eac6e77e469a510aa0089a53c4d3f0a959c43d0`.
- STATICS2 receipt digest: `d5f298df3e863ee77b37bffa56e5f8675a06dfd905ef84585cb0eefdd3d77530`.
- Interpreter: `/home/sat/mcrl-leo-handover/.venv/bin/python`; one BASIN2 Python process; `nice -n 15`; OpenBLAS, OMP, MKL, NumExpr, VECLIB and BLIS thread counts all 1.
- Peak RSS: **2,938,171,392 bytes = 2.736 GiB**, below 5 GB.
- Wall time: 2,726.176 s. The run printed `anchor k/12` at every completed anchor and printed peak RSS before the tape, after the tape, at every anchor, and at completion.
