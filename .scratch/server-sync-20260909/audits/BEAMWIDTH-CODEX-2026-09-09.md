# Beam half-power-angle source reading and network sweep

`DIAGNOSTIC_NOT_CLAIM`

## Source finding

**The cited HOBS source defines `theta_3dB = 0.058 rad` as the one-sided angle from boresight to the half-power point, not as the full angular span.** Its equation puts the stated parameter itself at half power. Therefore the source-implied full HPBW is `0.116 rad = 6.6463104235 deg`. The current V0.25 engine instead registers `3.32 deg` as a full span and puts its half-power edge at `1.66 deg`; the source-implied beam is consequently almost exactly twice as wide in a one-dimensional cut.

The primary source is Sz-Han Chen, Li-Hsiang Shen, Kai-Ten Feng, Lie-Liang Yang, and Jen-Ming Wu, “Energy-Efficient Joint Handover and Beam Switching Scheme for Multi-LEO Networks,” *2024 IEEE 99th Vehicular Technology Conference (VTC2024-Spring)*, DOI [10.1109/VTC2024-Spring62846.2024.10683088](https://doi.org/10.1109/VTC2024-Spring62846.2024.10683088). The [official conference PDF](https://ieeevtc.org/vtc2024spring/DATA/PID2024002205.pdf) is retrievable. The [audited local PDF](</home/sat/mcrl-v025-beam-ws/.scratch/chinese-word-r1-symbols-20260905-r1/input/thesis-mc/references-pdf/[04]_Energy_Efficient_Joint_Handover_and_Beam_Switching_S.pdf>) has 7 PDF pages and SHA-256 `1b2a8eda4647c4f7b68f8ffb08347aaa9cde18ae32b7d6af84d68f827a0f3089`, matching the repository custody record.

Equation (3), PDF page 2, faithful mathematical transcription (PDF typography normalized to LaTeX; mathematical content and punctuation retained):

> \(G(\theta)=G_0\left[\frac{J_1(\mu(\theta))}{2\mu(\theta)}+36\frac{J_3(\mu(\theta))}{\mu(\theta)^3}\right]^2,\tag{3}\)

The definition immediately following it, with typography normalized:

> \(\mu(\theta)=2.07123\cdot\sin(\theta)/\sin(\theta_{3dB}),\)

Table I, PDF page 6, verbatim row:

> `3dB beamwidth θ3dB    0.058 rad`

The surrounding source text identifies `theta` as the boresight angle and `theta_3dB` as the antenna's 3 dB half-power beamwidth angle. Substitution, rather than terminology, settles the convention:

```text
theta = theta_3dB  =>  mu = 2.07123
G(theta_3dB) / G0 = 0.5000004083327867
10 log10(G/G0)     = -3.0102964099 dB

source one-sided half-power angle = 0.058 rad = 3.3231552118 deg
source-implied full HPBW           = 0.116 rad = 6.6463104235 deg
```

At boresight the bracket's limit is one, and the pattern is symmetric about boresight. Thus `theta_3dB` is the radial/off-axis location of either half-power boundary; the full cut spans from `-theta_3dB` to `+theta_3dB`. The source does not itself print `0.116 rad`; that number is the consequence of equation (3).

## Five-point network sweep

Every input below is first stated as a **one-sided off-boresight half-power angle**. The next column gives the equivalent **full HPBW span**. The `3.32 deg` one-sided point is the requested rounded source value; the source's exact table value is `3.323155... deg`. The `6.65 deg` point is the requested twice-source design point.

Pooled EE is `sum(bits) / sum(joules)` across eight matched real anchors, not an average of anchor ratios. Coordination headroom is `pooled EE(ORACLE_SET) / pooled EE(UNILATERAL) - 1`. Served counts are the engine's `served_PHY` totals (positive decoding time over the committed endpoint), out of 800 user-steps (100 users at each of eight anchors).

| One-sided half-power angle (deg) | Full HPBW span (deg) | Point meaning | BASELINE EE (Mbit/J) | UNILATERAL EE (Mbit/J) | ORACLE_SET EE (Mbit/J) | Oracle over unilateral | BASELINE served / 800 | UNILATERAL served / 800 | ORACLE_SET served / 800 |
|---:|---:|:---|---:|---:|---:|---:|---:|---:|---:|
| 1.66 | 3.32 | current model | 3.861 | 26.762 | 28.502 | 6.50% | 313 | 779 | 790 |
| 2.40 | 4.80 | design sweep | 3.698 | 25.520 | 28.174 | 10.40% | 334 | 761 | 774 |
| 3.32 | 6.64 | rounded source value | 1.387 | 28.956 | 32.304 | 11.56% | 203 | 701 | 729 |
| 4.50 | 9.00 | design sweep | 0.315 | 19.449 | 22.297 | 14.64% | 56 | 528 | 607 |
| 6.65 | 13.30 | requested ~2x-source point | 0.149 | 3.146 | 4.466 | 41.95% | 19 | 158 | 220 |

### Interference structure

An infeasible user-step is classified as interference-limited only if the same assignment is infeasible under physical cross-gain and becomes feasible at every one of the 48 boundaries when cross-gain alone is zeroed. Parentheses show `interference-limited / infeasible`. Top-1 share is the TDM-slot- and trapezoidal-boundary-weighted strongest-aggressor interference divided by weighted total interference over failing transmissions belonging to those interference-limited user-steps.

| One-sided / full span (deg) | BASELINE interference-limited share | UNILATERAL interference-limited share | ORACLE_SET interference-limited share | BASELINE top-1 share | UNILATERAL top-1 share | ORACLE_SET top-1 share |
|:---:|---:|---:|---:|---:|---:|---:|
| 1.66 / 3.32 | 76.34% (355/465) | 91.18% (279/306) | 91.37% (254/278) | 66.66% | 71.83% | 75.31% |
| 2.40 / 4.80 | 100.00% (577/577) | 81.15% (340/419) | 74.53% (278/373) | 49.78% | 65.22% | 62.57% |
| 3.32 / 6.64 | 100.00% (692/692) | 63.81% (298/467) | 55.09% (238/432) | 39.85% | 56.70% | 59.91% |
| 4.50 / 9.00 | 100.00% (742/742) | 58.46% (311/532) | 53.20% (283/532) | 31.34% | 31.93% | 30.85% |
| 6.65 / 13.30 | 100.00% (772/772) | 92.87% (651/701) | 92.47% (614/664) | 22.73% | 26.51% | 26.88% |

The weighted total-interference statistic increased monotonically across all five widths for all three selectors. From the narrowest to widest point it increased by `29.55x` for BASELINE, `110.85x` for UNILATERAL, and `128.48x` for ORACLE_SET. The conditional interference-limited *share*, however, is not monotone for the optimized selectors: it falls through the middle of the range and rises sharply at `6.65 deg`. The top-1 aggressor share falls steadily with width. Interference therefore becomes much larger but less concentrated in one aggressor; a wider beam creates a more diffuse multi-aggressor problem.

## What the curve says

On this matched panel, bounded set-level coordination has positive pooled EE headroom at every sampled antenna design. The headroom rises monotonically from `6.50%` to `41.95%`, with the largest change occurring between the last two sampled points. No claim is made about unsampled angles.

The expectation is therefore only partly captured by the requested summary shares:

- **Less width, less coordination value:** yes on this panel; pooled headroom increases at every sampled width.
- **More width, worse service:** yes for both optimized selectors, whose served totals fall monotonically from `779 -> 158` and `790 -> 220`. BASELINE has a small initial increase (`313 -> 334`) before falling to `19`, so its service curve is not strictly monotone over all five points.
- **More width, more interference:** yes for the weighted total-interference magnitude, but not monotonically for the conditional interference-limited share. The top-1 share decreases, showing that dominance shifts away from a single aggressor as more aggressors matter.

For the original two readings specifically, moving from the current modeled `1.66 deg` one-sided edge to the rounded source `3.32 deg` one-sided edge is associated with these network consequences: BASELINE EE changes by `-64.07%`, UNILATERAL EE by `+8.20%`, ORACLE_SET EE by `+13.34%`, and coordination headroom rises by `5.06 percentage points` (`6.50% -> 11.56%`). Served totals fall by `110`, `78`, and `61`, respectively. These are consequences of the controlled width sweep, never a justification for choosing either width. In particular, the isolated-fixture `+42.5%` wanted-link result is not the network answer for any of the three selectors.

The widest point similarly produces much larger headroom while serving far fewer users. That is a scientific finding about when coordination has value, not a reason to prefer the widest antenna.

## Measurement design and limits

- **Coverage:** eight real anchors per point: steps `0..3` from each of two fixed domains, `V025_PROBE_R2/world/1` and `V025_PROBE_R2/world/2`. Their TLE dates are `2026-05-30` and `2025-07-28`; their deterministic training seeds are `3525272352645343090` and `3445540383109071487`. Domain, date, seed, step, and 100-user population match across every width.
- **BASELINE:** the nearest-eligible physical assignment.
- **UNILATERAL:** deterministic cyclic exact best response under `F = B - eta_ref E`, with `eta_ref = 19,720,681.00172232 bit/J`, continued until a complete pass has no strictly improving legal single-user move. The selection-time served count may not fall below that point's BASELINE count. Every reported anchor has a terminal certificate.
- **ORACLE_SET:** the best exact-`F` selection from a bounded mechanism catalogue built around the unilateral solution: same-beam occupant subsets of sizes 2--4 (1,024-generation cap), victim plus top-2/top-3 physical interference contributors, and complete-beam evacuations, with a global 4,096-configuration cap. UNILATERAL is included as the reference. This is a bounded set-selector oracle, not an unconstrained global combinatorial oracle.
- **Selection/commit separation:** selectors use realised boundary 0 held for `30.08 s`; the three committed configurations are then independently scored through the corrected causal ACM endpoint over all 48 realised boundaries. Consequently an oracle-positive selection move can have a negative or undefined anchor-local committed EE difference; those anchors were retained.
- **Claim ceiling:** TRAIN-only diagnostic, no learner, test split unopened, and the deployment ten-second deadline deliberately ignored for the ceiling computation. It is descriptive evidence over eight anchors, with no uncertainty interval or population-level claim.
- **Controlled axis:** only the transmit-pattern half-power angle changes. `TX_G0_LINEAR = 2000` and every other constant, candidate geometry, and rule stay fixed. This isolates beam-pattern width; it is not an aperture/gain/cell lattice co-design.
- **Execution:** `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 12`, single-threaded numerical libraries, and at most three experiment processes (controller plus two workers). The five receipts report an aggregate sequential wall time of `7,239.04 s` (`120.65 min`), 39 seconds over the nominal two-hour budget, while retaining all five required points and the minimum eight anchors per point.
- **Regression check:** the two existing V0.25/legacy antenna test files pass all 29 tests after the diagnostic, and direct engine evaluation reproduces normalized gain `0.5000004083` at `1.66 deg` and `0.0423687169` at `3.32 deg` under the unchanged current constant.
- **Independent source check:** a separate primary-source review agreed with the equation/table interpretation and the propagation findings. Its note is `.scratch/beamwidth/independent-source-check.md`.

The reproducible sweep command was:

```bash
for hp in 1.66 2.40 3.32 4.50 6.65; do
  nice -n 12 env PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
    /home/sat/mcrl-leo-handover/.venv/bin/python \
    .scratch/beamwidth/run_beamwidth_network.py \
    --worlds 2 --anchors-per-world 4 --one-sided-hp-deg "$hp" \
    --output ".scratch/beamwidth/sweep-one-sided-${hp}.json"
done
```

All five internal receipt digests recomputed successfully. The receipt files are `.scratch/beamwidth/sweep-one-sided-{1.66,2.40,3.32,4.50,6.65}.json`.

## Propagation audit and required comment correction

The false provenance statement occurs in `src/mcrl/physics_v025/constants_v025.py`: `TX_FULL_HPBW_DEG = 3.32` is commented as retaining the HOBS full-HPBW convention, and the provenance map repeats that assertion. `src/mcrl/physics_v025/channel.py` divides this value by two before placing it in the denominator of HOBS equation (3), so the live half-power edge is `1.66 deg`. At the engine's `theta = 3.32 deg`, normalized gain is about `0.04237` (`-13.73 dB`), not one half.

The comment is false and **must be replaced in a separate authorized change** with a declaration that the value is a chosen system-design parameter, plus an explicit convention (the present API stores a full span and the pattern uses its one-sided half). The provenance-map entry and corresponding full-HPBW docstrings should be made consistent at the same time. No sealed or engine file was edited in this task.

The same-source/convention propagation audit found:

- `_BESSEL_MU_COEFFICIENT = 2.07123` is copied from HOBS equation (3), but is convention-invariant; the extra halving of the angular denominator is the issue.
- Legacy `src/mcrl/env/antenna.py` also says HOBS fixes the numerical boresight cutoff `_MU_LIMIT_EPSILON = 1e-10`. Full-text inspection of the audited PDF finds no such cutoff. This is a separate unsupported provenance comment, not an angle-convention propagation.
- `TX_G0_LINEAR = 2000` is not HOBS Table I's `40 dBi` (`10000` linear). Legacy engine documentation says `2000` was re-derived through `D = 1.0275 lambda / theta_3dB` under the narrower full-span convention. It is therefore convention-coupled in provenance: changing the physical aperture/beamwidth design would require re-auditing gain. This sweep holds it fixed deliberately and makes no source-faithful co-design claim.
- The legacy `src/mcrl/env/antenna.py` and `src/mcrl/env/cells.py` each duplicate `THETA_3DB_DEG = 3.32` as a full span and halve it. The latter propagates the convention into cell radius and lattice pitch. The V0.25 sweep did not alter that geometry; in `src/mcrl/physics_v025`, the width constant is consumed only by the transmit pattern.
- `HOBS_REFERENCE_MAX_RF_W = 100` comes from Table I's `50 dBm`, but is an independent, non-live reference and has no angle-convention propagation. `REFERENCE_BEAMS_PER_SATELLITE = 39` is not HOBS Table I's `37` and is not an arithmetic derivative of beamwidth.

The pre/post SHA-256 values of the two sealed files inspected were unchanged:

```text
7863e136423bfac77a0c710d95f9e8b3fe36b928c0dc1ef1bb3b2f69a0ab1112  src/mcrl/physics_v025/constants_v025.py
9f29bb063e8e2ce6898ede1a567b638bb0a14e02e1f97616bf3d87ef422d396e  src/mcrl/physics_v025/channel.py
```

## Disposition

The provenance question is settled: HOBS's `0.058 rad` is a one-sided half-power off-axis angle. The design question is intentionally not settled: the owner has declared half-power angle to be a system design parameter, and this report neither recommends nor ranks a choice. The curve shows where the bounded set coordinator has value and what service/interference consequences accompany that value.
