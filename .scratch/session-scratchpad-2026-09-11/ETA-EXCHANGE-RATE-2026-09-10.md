**The in-force V0.25 `eta_ref` is `14235186615308645000000/1300834130903823` = 10.943122 Mbit/J; no `eta >= 0` makes the exact-`F` order of the six clean arms match their pooled-EE order, with or without `Phi`; Dinkelbach converges in one step to 41.621560 Mbit/J; and at that corrected `eta` the pooled descent from `RSS_MAX` persists under BASIN2's `F = B − eta E` (41.621560 → 40.855271 Mbit/J, versus 31.812902 at `eta_ref`) but becomes a +0.064394 Mbit/J ascent under the deployed `F = B − eta E − Phi` (→ 41.685954), while EE still falls at 9 of 12 anchors under both.**

# ETAFIX — does correcting the exchange rate fix the objective–metric mismatch?

Status: `DESIGN_PHASE_DIAGNOSTIC_NOT_A_CLAIM`. The run is learner-free: it read no checkpoint, no learner output and no loss. It used only the 12 frozen development anchors (`V025_PROBE/world/1`, steps 0–3, carriers nearest-eligible / stay-if-possible / random-masked) and read none of the 48 evaluation-only claim dates. It changed no sealed artefact and no deployed objective. Every re-priced objective here exists only in memory as a probe `PilotCalibration`. This job measures and prices. It does not recommend.

## Direct answer

**The exchange rate is not the cause of the objective–metric mismatch.** It is the dominant cause of the descent's pooled size. Under the deployed `Phi`-inclusive score, correcting it is enough to flip the pooled sign of the descent. It does not remove the order mismatch or the per-anchor descent.

1. **Order: `eta` is not the cause.** No single `eta` orders the six arms as pooled EE does. Without `Phi` the admissible set is empty because two pairs demand incompatible prices. With `Phi` (COORDVALUE's deployed score) the `RANDOM`/`NEAREST_ELIGIBLE` pair is inverted at every `eta >= 0`. The minimum number of discordant pairs over all `eta` is 1 in both cases, never 0.
2. **Descent: the pooled answer depends on whether `Phi` is in `F`; the per-anchor answer does not.** At the Dinkelbach fixed point `eta* = 41.621560` Mbit/J:
   - Under BASIN2's `F = B − eta E`, first-improvement from `RSS_MAX` still ends below its start, at 40.855271. Re-pricing removes 92.19% of the pooled loss (9.808657 → 0.766289 Mbit/J) but not its sign.
   - Under the deployed `F = B − eta E − Phi` it ends above its start, at 41.685954 (+0.064394 Mbit/J, +0.155%, 1200/1200). By the tasking's rule ("ascends or stays ⇒ the exchange rate was the cause"), `eta` was the cause of the **pooled** descent under that score.
   - Under both scores EE still **falls at 9 of 12 anchors** (every step-0 to step-2 anchor) and rises only at the 3 step-3 anchors. The pooled +0.064394 is the net of those opposing effects, and its sign flips with whether `Phi` is included.
   - It is also smaller than the +0.071681 Mbit/J gain BASIN2's bounded PANELCEIL catalogue already found around `RSS_MAX`.
3. **Horizon.** At `eta_ref` the descent endpoint has fewer full-48 bits (−3.0300×10¹⁰) and more full-48 energy (+11,297.16 J) than `RSS_MAX`. It is dominated in both coordinates, so `F` evaluated on the metric's own horizon would reject it at every `eta >= 0`. The search accepted it because it optimises boundary-0 `F`. Re-pricing COORDVALUE's own rows shows the same split: at the best single `eta` on the deployed boundary-0 horizon, 6,548 of 76,671 guarded rows (8.540%) still disagree in sign with ΔEE. On the full-48 horizon the minimum is 2,002 (2.611%).

The only pricing that removes every sign disagreement is `eta` = the start's own full-48 EE, on the full-48 horizon, without `Phi`. That result is **tautological**: then `F(x) − F(s) = E(x)·(EE(x) − EE(s))`, so it just ranks by EE. It is a redefinition of `F` into the ratio, not a corrected exchange rate.

## Four fields for every figure in this report

| Figure family | Reference | Information class | Estimand | Numerator |
|---|---|---|---|---|
| `eta_ref` | one profile: the step-0 nearest-eligible `BASE` of `V025_PROBE/world/1` (development) | realised full-48 physics of that single configuration, scalar `evaluate` path inside `_pilot_calibration` | `B/E` of that one profile | full-buffer successfully decoded forward-downlink information bits, no demand cap |
| Arm pooled EE, arm `F` | 12 frozen development anchors, clean `STATICS2` configurations | realised dense full-48 endpoint, one fresh evaluator and one `evaluate_many` per anchor | pooled EE = `ΣB/ΣE`; pooled `F(eta) = ΣB − eta·ΣE [− ΣPhi_cost]` | same bits |
| Descent endpoints | same 12 anchors, start `RSS_MAX`, guard = start served count | selection on realised boundary-0 `F` (current-boundary fading, no future boundary); scoring on realised dense full-48 | pooled EE `ΣB/ΣE` of the terminal configurations | same bits |
| COORDVALUE re-pricing | COORDVALUE's 76,671 guarded candidate-anchor rows (k = 1 exhaustive, k > 1 sampled 128 per cell) | COORDVALUE's own verified rows, re-priced arithmetically; nothing re-evaluated | count of rows with sign(ΔF) ≠ sign(ΔEE) | same bits |

## 1. The exchange rate actually in force (verified by reading and running code)

- **Value.** `eta_ref = 14235186615308645000000 / 1300834130903823 = 10,943,122.01465532 bit/J = 10.943122 Mbit/J`, with `lambda_bits_per_j` identical by contract (`assert_same_energy_price`, `endpoint.py:127-140`). `kappa = 8541111969185187/10000000 = 854,111,196.9185187` bits/user-step = `bits_ref / 100 users`.
- **Where it is loaded.** From `/home/sat/mcrl-v025-c1c2suff-ws/artifacts/v025-pilot-c3-20260909-PILOT_NOT_CLAIM/PILOT_NOT_CLAIM-calibration.json`, named at `run_panelceil.py:30-34` and loaded as an exact `Fraction` at `run_panelceil.py:133-145`. The same file feeds the exact-row generators (`.scratch/c2-declared/generate_exact_rows.py:25-28`, `.scratch/q2-schema-v2/verify_exact_adapter_v2.py:25`, and others). The C2 corpus metadata line records it with calibration digest `6fd3af80…`.
- **What it was calibrated to.** `_pilot_calibration` (`scripts/run_v025_pilot_c3.py:274-296`) sets `eta_ref = bits/joules` of `ENGINE._base_configuration(tape, 0, "nearest-eligible")`. The evaluator there uses the default `boundary_indices = tuple(range(48))` (`run_v025_matrix_probe.py:777`), so the value is the realised full-48 EE of the step-0 nearest-eligible `BASE`. It is an injected constant, never re-derived from outcomes. This run's independent dense recomputation of that configuration gives 10,943,122.014655314 bit/J. That agrees to 15 significant figures but is **not bit-identical**, because the sealed routine used scalar `evaluate` and this run used the dense path.
- **V0.25 has one declared value, and it is not the V0.23 one.** All six `v025-pilot-*-PILOT_NOT_CLAIM` calibration files carry the identical pair. The V0.23 fraction `4163290999041717/33554432` (124.075741 Mbit/J) occurs nowhere in the V0.25 workspaces. It is 11.338× the V0.25 value.
- **The objective has two in-use definitions.** `network_objective` (`targets.py:130-143`) returns `outcome.bits − eta·outcome.joules` ("Phi stays separate"). BASIN2, CLEANPATH, PANELCEIL and CEILING2 search on that, via `runner._objective`. COORDVALUE scores the deployed objective as `B − eta_ref·E − Phi_cost` with `Phi_cost = −kappa·_phi_for(incumbent, config)`. This report tests both. `phi_qos` (`targets.py:72-80`) penalises only `satellite_change` (1.0) and `beam_change` (0.5). It has no load, occupancy, balancing or fairness term, which independently confirms CROWDING-COST Part 4.
- **Correction to the tasking's energy-signature premise.** The "93,512 J, 2.35×" figure comes from the **superseded contaminated** `mcrl-v025-rank-ws/.scratch/statics/statics-receipt.json` (`FIRST_IMPROVEMENT_FP` 93,511.945 J, 13.430253 Mbit/J, 1036/1200 served). On the clean path the same arm uses 52,325.854 J at 31.028111 Mbit/J, 1200/1200 served: **1.3170×** `RSS_MAX`'s 39,729.712 J, not 2.35×. The direction survives (`RSS_MAX` has strictly more bits and strictly less energy), but the magnitude is about half.

## 2. Parity gate and evaluator rule (verified by running code)

The gate ran before any sweep or search, in both processes:

| Arm | Required | Phase A/B process | Phase C process |
|---|---:|---:|---:|
| `RSS_MAX` | 41.621560 | 41.62155981714534 | 41.62155981714534 |
| `FIRST_IMPROVEMENT_FP` | 31.028111 | 31.028111070819413 | 31.028111070819413 |

All six arms reproduce the sealed clean receipt to the last printed digit. All 72 configuration IDs match it. Phase C's 72 endpoints are bit-identical to phase A's.

- Each selection surface was one fresh dense `StepEvaluator(boundary_indices=(0,))` whose first `evaluate_many` contained `BASE`, the start and the first user's candidates. It was asserted in code and profiles were read only from `_evaluated`.
- Each endpoint comparison was one separate fresh realised dense full-48 evaluator with one `evaluate_many` containing every compared profile, including `BASE`.
- `StepEvaluator.evaluate` was replaced class-wide by a counting, raising stub before any work. **Final assertion: zero scalar calls in phase A/B and zero in phase C.**
- The two `RSS_MAX` endpoints in different batches differ in joules in the last ulp at 3 anchors (7.6×10⁻¹⁷ relative). No sign below depends on that.

## 3. The order test swept over `eta` (verified by running code; algebra derived on paper)

### 3.1 The six clean arms

| Arm | Pooled bits | Pooled joules | Pooled EE (Mbit/J) | Served | `Phi_cost` (bits) | `Phi_cost / B` |
|---|---:|---:|---:|---:|---:|---:|
| `RSS_MAX` | 1.6536125866×10¹² | 39,729.712050 | 41.621560 | 1200/1200 | 8.1269×10¹¹ | 0.4915 |
| `MYOPIC_GREEDY` | 1.5586607745×10¹² | 50,152.374745 | 31.078504 | 1200/1200 | 8.6436×10¹¹ | 0.5546 |
| `FIRST_IMPROVEMENT_FP` | 1.6235724184×10¹² | 52,325.854277 | 31.028111 | 1200/1200 | 8.5838×10¹¹ | 0.5287 |
| `RANDOM` | 1.2886056260×10¹² | 114,705.864740 | 11.233999 | 1102/1200 | 8.8102×10¹¹ | 0.6837 |
| `NEAREST_ELIGIBLE` | 1.1212971016×10¹² | 101,679.495970 | 11.027760 | 960/1200 | 3.0663×10¹¹ | 0.2735 |
| `ROUND_ROBIN` | 7.5375305200×10¹¹ | 219,036.120671 | 3.441227 | 798/1200 | 7.4607×10¹¹ | 0.9898 |

The `Phi` cost is a first-order term, between 27% and 99% of pooled bits. `NEAREST_ELIGIBLE` is the carrier `BASE`, so it changes few users relative to the prior-step incumbent (0 at step 0) and pays the least.

### 3.2 The algebra

`F_i(eta) − F_j(eta) = ΔB − eta·ΔE` (minus `ΔPhi_cost` when `Phi` is included) is affine in `eta`. Let `m_ij = (ΔB − ΔPhi_cost)/ΔE`. If `EE_i > EE_j`, the orders agree on that pair iff `eta < m_ij` when `i` spends more energy, or `eta > m_ij` when `i` spends less. Without `Phi`, `m_ij − EE_i = E_j(EE_i − EE_j)/(E_i − E_j)`. So a spend-more/better-EE pair sets an **upper** bound above both of its ratios, and a spend-less/better-EE pair sets a **lower** bound below both. The admissible `eta` set is the intersection of 15 half-lines.

### 3.3 Result

| Pair (higher EE first) | Energy | Bound, no `Phi` (Mbit/J) | Bound, with `Phi` (Mbit/J) |
|---|---|---:|---:|
| `MYOPIC_GREEDY` > `FIRST_IMPROVEMENT_FP` | spends less | `eta > 29.865312` | `eta > 32.616098` |
| `RANDOM` > `NEAREST_ELIGIBLE` | spends more | `eta < 12.843834` | `eta < −31.250555` (never, for `eta >= 0`) |
| `MYOPIC_GREEDY` > `NEAREST_ELIGIBLE` | spends less | `eta > −8.488` (always) | `eta > 2.336070` |
| `FIRST_IMPROVEMENT_FP` > `NEAREST_ELIGIBLE` | spends less | `eta > −10.177` (always) | `eta > 1.002571` |
| the other 11 pairs | — | satisfied for all `eta >= 0` | satisfied for all `eta >= 0` |

**No `eta` makes the `F` order equal the EE order.** Without `Phi`, the binding pair needs `eta > 29.865311773` while `RANDOM`/`NEAREST_ELIGIBLE` needs `eta < 12.843834483`. With `Phi`, the second constraint cannot be met at any nonnegative price.

| `eta` band, no `Phi` (Mbit/J) | Exact-`F` order | Discordant pairs |
|---|---|---:|
| `0 <= eta < 12.843834` (contains `eta_ref` = 10.943122) | RSS > FP > MYOPIC > RANDOM > NE > RR | 1 (`MYOPIC`/`FP`) |
| `12.843834 < eta < 29.865312` | RSS > FP > MYOPIC > NE > RANDOM > RR | 2 |
| `eta > 29.865312` (contains `eta*` = 41.621560 and V0.23's 124.075741) | RSS > MYOPIC > FP > NE > RANDOM > RR | 1 (`RANDOM`/`NE`) |

With `Phi`: 4 discordant pairs for `eta < 1.002571`, 3 up to 2.336070, 2 up to 32.616098, and 1 (`RANDOM`/`NE`) above that. Raising `eta` from `eta_ref` to `eta*` swaps **which** pair is wrong. It does not reduce the count below 1. The sealed `eta_ref` reproduces BASIN2's reported order exactly.

**Why no single price can work (derived).** The two conflicting pairs sit at EE levels about an order of magnitude apart (about 11 and about 31 Mbit/J). A spend-more pair near 11 Mbit/J caps `eta` just above 11. A spend-less pair near 31 Mbit/J floors it just below 31. A linear scalarisation orders points by one direction `(1, −eta)`; a ratio orders them by angle from the origin. These agree on every pair only if every pair's incremental rate falls on the correct side of one number, and here they do not.

## 4. Dinkelbach iteration (verified by running code)

Feasible set: the six arms' pooled full-48 endpoints. The rule is `eta ← ΣB/ΣE` of the arm maximising `F` at the current `eta`, with a cap of 20 iterations.

| Iteration | `eta` (Mbit/J) | `argmax F` | `F` at argmax (bits) | Next `eta` |
|---:|---:|---|---:|---:|
| 0 | 10.943122015 (`eta_ref`) | `RSS_MAX` | +1.218846×10¹² | 41.621559817 |
| 1 | 41.621559817 | `RSS_MAX` | 0 (exact) | 41.621559817 — **fixed point** |

`eta* = 5512041955422222500000000/132432373501572239 = 41.62155981714534` Mbit/J, reached after one update. With `Phi` the sequence is identical (argmax `RSS_MAX` both times). `F_Phi` at the fixed point is −8.1269×10¹¹, `RSS_MAX`'s `Phi` cost, because the Dinkelbach identity no longer holds once `Phi` is in `F`.

- `RSS_MAX` has strictly more bits and strictly less energy than every other arm, so it is `argmax F` at **every** `eta >= 0`. `eta_ref` already selects the EE-best arm. On this set there is no argmax error for Dinkelbach to correct. Every disagreement is among non-argmax arms, and Dinkelbach says nothing about those.
- This is a fixed point of the **six-arm** set only. BASIN2's PANELCEIL catalogue around `RSS_MAX` already reaches 41.693241 Mbit/J at 1200/1200, so the fixed point over the full action space is at least that.

## 5. The descent test at the corrected `eta` (verified by running code)

This is the same driver and the same declared algorithm as BASIN2: realised boundary 0, guard = start served count, ascending user ID, declared legal-option order, first strict improvement, terminal zero-move certificate. It ran once at `eta_ref` as parity and once at `eta*`. Only the calibration object differs.

| Start / search | Pooled bits | Pooled joules | Pooled EE (Mbit/J) | ΔEE vs start | Moves (anchors moved) | Served |
|---|---:|---:|---:|---:|---:|---:|
| `RSS_MAX` start | 1,653,612,586,626.67 | 39,729.712 | 41.621560 | — | — | 1200/1200 |
| first-improvement at `eta_ref`, `F = B − eta E` | 1,623,313,012,293.33 | 51,026.876 | **31.812902** | −9.808657 | 3,414 (12/12) | 1200/1200 |
| first-improvement at `eta*`, `F = B − eta E` | 1,689,615,661,077.78 | 41,356.124 | **40.855271** | −0.766289 | 2,547 (12/12) | 1200/1200 |
| first-improvement at `eta_ref`, deployed `F = B − eta E − Phi` | 1,627,684,391,279.79 | 52,350.954 | **31.091781** | −10.529779 | 3,290 (12/12) | 1200/1200 |
| first-improvement at `eta*`, deployed `F = B − eta E − Phi` | 1,705,672,333,017.04 | 40,917.195 | **41.685954** | **+0.064394** | 2,571 (12/12) | 1200/1200 |

The `Phi`-inclusive rows come from the phase-C process: same search algorithm and evaluator rule, objective `runner._objective(profile, cal) − Phi_cost`, `Phi` against the prior-step carrier incumbent exactly as COORDVALUE `total_f`. Their `Phi` term depends on the carrier, so the three carriers at a step no longer coincide.

The `eta_ref` row reproduces BASIN2's 31.812902363951235 exactly, with per-anchor move counts 313/279/291/255 by step, identical to BASIN2. **At `eta*` the descent persists.** `RSS_MAX` is not a fixed point at any anchor.

Per step (full-48, identical across the three carriers at each step):

| Step | Start EE | EE after `eta_ref` search | EE after `eta*` search | Full-48 ΔF of `eta*` endpoint at `eta*` | Incremental rate ΔB/ΔE of `eta*` endpoint (Mbit/J) |
|---:|---:|---:|---:|---:|---:|
| 0 | 71.838507 | 39.069966 | 43.638876 | −5.4710×10¹⁰ | 0.508 |
| 1 | 65.792380 | 34.404628 | 42.776666 | −4.8613×10¹⁰ | 2.644 |
| 2 | 49.718426 | 31.174170 | 38.229163 | −3.4465×10¹⁰ | ΔB < 0, ΔE > 0 |
| 3 | 19.836770 | 24.600789 | 38.934956 | +1.2722×10¹¹ | ΔB > 0, ΔE < 0 |

With `Phi` at `eta*`, per anchor (full-48 EE; start `RSS_MAX`):

| Step | Start EE | nearest-eligible | stay-if-possible | random-masked | Sign |
|---:|---:|---:|---:|---:|---|
| 0 | 71.838507 | 47.394 | 47.394 | 45.150 | falls 3/3 |
| 1 | 65.792380 | 42.745 | 42.745 | 46.146 | falls 3/3 |
| 2 | 49.718426 | 39.498 | 38.265 | 38.321 | falls 3/3 |
| 3 | 19.836770 | 38.702 | 38.754 | 37.176 | rises 3/3 |

Pooled, the `Phi`-inclusive `eta*` endpoint buys +5.2060×10¹⁰ bits for +1,187.48 J (incremental 43.84 Mbit/J, just above `eta*`) and lowers `Phi` cost by 7.17×10¹⁰ bits. The `Phi`-free `eta*` endpoint buys +3.6003×10¹⁰ bits for +1,626.41 J (22.14 Mbit/J, below `eta*`). The handover term pulls the search toward the incumbent. On this panel that is enough to tip the pooled balance positive. It does not change the per-anchor pattern.

**Mechanism (derived from these verified figures).** One pooled `eta*` is too low for the step-0 to step-2 anchors, whose own EE is 49.7–71.8, and too high for step 3, whose own EE is 19.8. So the search descends where the start is locally efficient and ascends where it is not. The same single-scalar obstruction appears in §3. Pooled, the `eta*` endpoint buys 3.6003×10¹⁰ bits for 1,626.41 J, an incremental 22.14 Mbit/J, below `eta*`. Its full-48 `F` at `eta*` therefore falls by 3.169×10¹⁰, while its boundary-0 `F` rose at every anchor by construction of strict first-improvement. Because `F(RSS_MAX; eta*) = 0` pooled (to 1.2×10⁻⁴ bits), the pooled sign of full-48 ΔF at `eta*` equals the sign of ΔEE exactly. The remaining `Phi`-free descent, and the 9/12-anchor descent under both scores, is therefore a **selection-horizon and single-scalar** effect (boundary-0 `F` versus the full-48 metric, with one price for anchors whose own EE spans 19.8–71.8), not a mispriced constant. The energy signature the tasking predicted is present, but it is a horizon signature. The `eta_ref` endpoints spend 1.2844× (no `Phi`) and 1.3177× (with `Phi`) `RSS_MAX`'s energy while delivering fewer bits. The `eta*` endpoints spend 1.0409× and 1.0299×.

## 6. What COORDVALUE's own rows say about price, `Phi` and horizon (re-priced from its verified rows; nothing re-evaluated)

COORDVALUE Part 2 reported 3,671 guarded EE improvements rejected by `F` and 24,278 guarded EE decreases accepted, at `eta_ref`, on its boundary-0 selection score with `Phi`. Re-pricing its 76,671 guarded rows (log SHA-256 `79546806…`) reproduces both counts exactly. Its ΔF reconstructs to 1.8×10⁻¹¹ relative error. The disagreement then splits as follows:

| Score | ΔEE > 0 but ΔF < 0 | ΔF > 0 but ΔEE < 0 | Total | Share of guarded rows |
|---|---:|---:|---:|---:|
| Deployed: boundary 0, `Phi`, `eta_ref` (COORDVALUE) | 3,671 | 24,278 | 27,949 | 36.453% |
| boundary 0, no `Phi`, `eta_ref` | 3,708 | 23,649 | 27,357 | 35.681% |
| boundary 0, `Phi`, `eta*` | 3,617 | 11,996 | 15,613 | 20.364% |
| boundary 0, no `Phi`, `eta*` | 3,615 | 11,796 | 15,411 | 20.100% |
| boundary 0, no `Phi`, `eta` = start's own boundary-0 EE | 3,807 | 8,817 | 12,624 | 16.465% |
| **boundary 0, `Phi`, best single `eta` (223.08–223.43 Mbit/J)** | — | — | **6,548** | **8.540%** |
| boundary 0, no `Phi`, best single `eta` (225.22–225.58) | — | — | 6,489 | 8.463% |
| full-48, `Phi`, `eta_ref` | 982 | 28,210 | 29,192 | 38.074% |
| full-48, no `Phi`, `eta*` | 372 | 1,719 | 2,091 | 2.727% |
| **full-48, `Phi`, best single `eta` (52.644–52.647)** | — | — | **2,002** | **2.611%** |
| full-48, no `Phi`, best single `eta` (51.402–51.436) | — | — | 1,089 | 1.420% |
| full-48, no `Phi`, `eta` = start's own full-48 EE | 0 | 0 | 0 | 0% — tautological (ranks by EE itself) |

Read strictly:

- **Price matters most for the count on the deployed horizon.** `eta_ref` → `eta*` removes 44% of the deployed disagreements (27,949 → 15,613), and the best single price removes 77% (to 6,548).
- **Price cannot finish the job on any horizon.** The best single price on the deployed boundary-0 horizon is about 223 Mbit/J, more than 5× any pooled EE on this panel, and still leaves 6,548 disagreements. Even on the metric's own horizon, no single price leaves fewer than 1,089, because start EE differs by anchor.
- **`Phi` is a secondary term for COORDVALUE's local sign counts.** At any fixed price it moves them by 202–998 rows (at most 1.3% of guarded rows). It is first-order for the six-arm order (§3), where it makes one inversion permanent.
- The largest-rejected-gain figure (+7.852367 Mbit/J) and COORDVALUE's catalogue-support finding are COORDVALUE's own and are not re-derived here. The rejected-gain figure is `eta`-dependent (§7). The support finding is not.

## 7. Pricing the change (not a recommendation)

**Which of today's figures used the current `eta`.** Classified by mechanism. Named items were read in this job. A keyword triage over today's reports is a pointer, not an audit.

1. **Unchanged by any `eta`.** These are configurations chosen without the objective, and their pooled EE: `RSS_MAX` 41.621560, `RANDOM` 11.233999, `NEAREST_ELIGIBLE` 11.027760, `ROUND_ROBIN` 3.441227 (CLEANPATH verified these four never touch the selection evaluator). Also any EE of a fixed configuration, COORDVALUE's ΔEE columns and its k = 1 EE-barrier counts, and CEILING2's width-driven changes to fixed-rule endpoints.
2. **The configuration itself is chosen by `F`, so it changes with `eta` and must be re-run.** This covers `MYOPIC_GREEDY` 31.078504 and `FIRST_IMPROVEMENT_FP` 31.028111; every PANELCEIL/CEILING2 search object (`U_FIRST`, `U_BEST`, `J_PANEL_BOUNDED`, the nested-support winners, and so the +0.844250% coordination, +0.090744% traversal and the acceleration ratios); BASIN2's barrier k (defined on `F`), witnesses, ΔF values, `F` ranks, first-from-`RSS_MAX`/`MYOPIC` endpoints and catalogue best 41.693241; and COORDVALUE's Part 2 sign counts and "best EE gain `F` rejects". Measured here, `eta*` moves the first-from-`RSS_MAX` endpoint from 31.812902 to 40.855271 Mbit/J, so these objects are far from `eta`-invariant.
3. **Labels, states and rewards priced with `eta`.** The C1 difference surplus, C2 persistence forecast and C3 interaction / set / matched-anchor decompositions (`targets.py:154-665`); the exact-row corpus built from `PILOT_NOT_CLAIM-calibration.json`; every encoded state (`encode_c2_state` binds `lambda = eta` and `kappa`, `state_v025.py:130-145`); and `reward_core = B − eta·E` (`endpoint.py:112-125`). Anything trained or scored on these inherits `eta`, and `kappa`, which is tied to the same `bits_ref`.

**What a corrected `eta` would and would not change (measured).** Categories 2 and 3 would all need re-measurement. At `eta*` it would:

- not make the six-arm order correct under either `F`;
- turn the pooled descent from `RSS_MAX` into a +0.064394 Mbit/J ascent under `F` with `Phi`, but leave a −0.766289 Mbit/J descent without `Phi`;
- leave EE falling at 9/12 anchors under both;
- on COORDVALUE's rows, leave at least 6,548 sign disagreements on the deployed horizon, or 1,089 on the metric horizon, even at the best single price.

**What kind of change each option is.**

| Option | Mechanical footprint | Contract status | Class |
|---|---|---|---|
| Replace the constant with `eta*` (or another number) | swap one calibration file; regenerate every category 2–3 artefact | `CalibrationValues` requires `eta_ref == bits_ref/joules_ref` (`calibration.py:138-139`), with the reference drawn from exactly the two disjoint `V025_CAL` worlds (`calibration.py:144-146`, `freeze_setting_calibration` at `:235-266`). `eta*` is the pooled EE of a policy on **development** anchors, not a calibration-world reference, so it cannot be expressed under the sealed contract. | **Versioned successor** at minimum: new calibration source definition and schema, with every downstream artefact re-derived |
| Adaptive multiplier (Dinkelbach outer loop, per-anchor or per-step update, or primal–dual) | `F` becomes policy-dependent; the reward is non-stationary; state encodings bind a moving `eta`; `kappa` loses its fixed reference | changes what `F` is: the selection estimand moves from a fixed linear score to a sequence of scores converging on the ratio | **Scientific redefinition** of the objective. The limit case, per-start own-EE pricing on the metric horizon, is identical to ranking by EE (0 disagreements, tautological). |
| Keep `eta`, change the selection horizon | selection evaluator boundaries, not the price | touches the deployed selection information class | out of scope here. It is named only because §5–§6 locate the residual there. |

Context supplied by the tasking, not re-read in this job: a frozen linear scalarisation is the object addressed by Calvo-Fullana et al. 2023, Prop. 1, which gives an adaptive multiplier literature standing. That is standing, not evidence. On this panel, at the multiplier that iteration converges to on the six-arm set, the order defect and the per-anchor descent persist. Only the pooled descent under the `Phi`-inclusive score changes sign.

## Verified, derived, inferred

**Verified by running code.** In-force `eta_ref` and its loader, origin and file identity. Parity (both processes). Zero scalar calls (both processes). All six arm endpoints and 72 configuration IDs. Exact pairwise crossings and the empty admissible interval, with and without `Phi`. The `eta` grid orders. Dinkelbach sequences. Descent endpoints at `eta_ref` (BASIN2 reproduced exactly) and at `eta*`, under both `F` definitions, with per-anchor signs. Per-step full-48 ΔF. Reproduction of COORDVALUE's two counts and all re-priced counts in §6.

**Derived on paper from verified figures.** The pairwise-bound algebra and the "upper above, lower below" lemma. `RSS_MAX` is argmax `F` for every `eta >= 0`. The Dinkelbach identity `F(x; EE(s)) − F(s; EE(s)) = E(x)(EE(x) − EE(s))` and hence the tautology of own-EE pricing. The pooled sign equivalence at `eta*`. The 92.19% share of the loss removed by re-pricing. Energy ratios 1.3170 / 1.2844 / 1.0409.

**Inferred.** The residual descent and residual sign disagreement are selection-horizon effects: boundary-0 `F` against the full-48 pooled metric. This is supported by the dominance of the `eta_ref` endpoint in full-48 bits and energy, and by the per-step pattern, but no run here changed the selection horizon. Also inferred: the cross-step EE spread (19.8–71.8 Mbit/J for `RSS_MAX`) is why a single pooled price is simultaneously too low and too high. All of this is limited to these 12 development anchors.

## Reproducibility and resource record

- Drivers: `.scratch/etafix/run_etafix.py` (SHA-256 `0fcd90e5ce0447641549011e8df0ca41b119da04360026d8a68cd923f6b4d73e`, phases A–B) and `.scratch/etafix/run_etafix_phi.py` (`b82571c314c69bb77014f623e11e0362eec7792d550f9a1f2631f4486b650520`, phase C, imports phase A–B helpers unchanged and digest-checked). `.scratch/etafix/decompose_coordvalue.py` (`654e7e0a545030b619175f87df99686152775dbacff84acbe52e78144c10ce33`, read-only re-pricing).
- Receipts: `.scratch/etafix/etafix-receipt.json` (status COMPLETE, canonical digest `73fa71a5a77979bfa36af7bc7f296da8b408931d1ed8f935e3567998c541e9a3`, recomputed and matched), `.scratch/etafix/etafix-phi-receipt.json` (status COMPLETE, canonical digest `b28eed6653f1194e0d819c898aaa418a42a118d09aee6055ea45e77baf23af37`, recomputed and matched), `.scratch/etafix/coordvalue-repricing.json`.
- Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`; niceness 15; `OMP`/`OPENBLAS`/`MKL`/`NUMEXPR`/`VECLIB`/`BLIS` threads all 1; at most 2 concurrent Python processes. Peak RSS **2.563 GiB (2,752,073,728 B)** for phases A–B, **2.596 GiB (2,787,340,288 B)** for phase C, 0.051 GiB for the re-pricing. All are below 5 GB. `anchor k/12` and peak RSS were printed at every anchor of every phase.
- Wall time: phases A–B 1,777.2 s; phase C 1,951.9 s. Phases A–B completed at 19:18Z. The controlling session was interrupted afterwards, and phase C and the re-pricing ran on resumption (~23:45Z onward). No result was lost or recomputed across the interruption.
