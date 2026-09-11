**`MAX_NOMINAL_GAIN` still beats the trained `e6b063ef…` checkpoint under all three accountings — pooled-EE ratio 1.1975 under `MAX`, 1.1916 under `TDM_AIRTIME`, and 1.1629 under `ADDITIVE` (which this time-division PHY does not admit, so it is reported only as a labelled denominator-only stress bound) — so the aggregation operator accounts for 3.0% of the gap under the airtime model and at most 17.5% under the additive one, and by the pre-declared reading the result has external physical credibility rather than being a simulator counterexample.**

Date: 2026-09-11. Job POWERACCT. **Read-only: `update()` is never called, no gradient step, no optimizer step, `src/` never edited and never import-time patched.** The trained arm *loads* the frozen checkpoint read-only. One python process, `nice -n 16`, `OMP/MKL/OPENBLAS_NUM_THREADS=1`, peak RSS 0.63 GB (cap 5 GB). Wall 351.9 s for the panel + 2 short probes.

Scripts (session scratchpad `/tmp/claude-1000/-home-u24-papers-mcrl-leo-handover/e9fba164-.../scratchpad/`): `power_accounting.py` (the panel), `power_accounting_lib.py` (the same file with its driver block stripped, for the two probes — not used to produce any panel number), `fixed_probe.py`, `neg_check.py`. Raw log `poweracct.log`, raw JSON `power_accounting_result.json`.

Evidence class: **[V]** I ran it or opened the file myself, with file:line. **[D]** derived arithmetic from [V] numbers. **[I]** inferred / reasoned, not measured.

---

## Four fields, declared once, standing for every EE number below

| field | value |
|---|---|
| **reference point** | the trained `e6b063ef…` checkpoint evaluated greedy (ε = 0) on the *same* 24 episodes, *same* frozen seeds (train 42 / env 1337 / mobility 7), *same* RNG stream positions 0–23. Not a paper number, not a training-time number. |
| **information level** | deployable. Every arm sees only the per-user observation the MODQN policy sees; no oracle, no realised fading, no future. The trained arm loads frozen weights. |
| **estimator** | pooled EE = **ratio of sums**: `Σ_steps throughput_bps·dt / Σ_steps P^N·dt`, two running totals over all 24 × 10 steps, divided **once**. Never a mean of per-step or per-user ratios. `dt = DECISION_STEP_S = 30.08 s` (`env/constants.py:76`). |
| **numerator** | full-buffer Shannon, **no demand cap and no rate setpoint** — `R = (B^w/U_b)·log₂(1+γ)`, `env/link_budget.py:590-616`, applied at `env/step.py:964-971`. The numerator is **byte-identical across all three accountings by construction**; only the denominator changes. |

---

## 0. What was held fixed, and how that is guaranteed

The three accountings are **not three runs**. Each arm is run **once**, under the canonical physics, through a `StepEnvironment` subclass whose only override calls `StepEnvironment._resolve_physics` unchanged and then *records* the step. All three denominators are recomputed from that one recorded step. Actions, RNG stream, segments, SINRs, rates, served set, beam membership and the interference field are therefore identical across the three columns **by construction, not by matching**. **[V]**

**Parity check 1 — per step.** My `MAX` recomputation against the environment's own `system_power_w`: `max |Δ| ≤ 2.274e-13 W` over every step of every arm. **[V]**

**Parity check 2 — the published figures.** All four arms reproduce the frozen-seed, fresh-env `none` panel **bit-identically**, to the last printed digit:

| arm | published (`CATFISH-ATTACHMENT-SURFACE`, `none` row) | this run, `MAX` column |
|---|---:|---:|
| `RANDOM_MASKED` | 53,060,175.56 | **53,060,175.561473** |
| `GREEDY_R1R2` | 75,763,635.84 | **75,763,635.837306** |
| `TRAINED e6b063ef…` | 93,110,907.97 | **93,110,907.973748** |
| `MAX_NOMINAL_GAIN` | 111,504,571.39 | **111,504,571.388934** |

**[V]** The parity check passes. Nothing below rests on a re-derivation of the baseline.

The `_age_rng` confound named in the attachment surface is avoided the same way it was there: **every arm builds a fresh environment**, so `_age_rng` (`env/step.py:534-536`) is spawned from the same env-RNG state in every cell.

---

## 1. The three accountings, stated with their sites

The **fixed hardware terms are byte-identical in all three**. Only the user-aggregation operator inside the PA term changes.

| term | symbol | value | site |
|---|---|---:|---|
| per-illuminated-beam circuit power | `P_cir` | **0.338 W** | `env/link_budget.py:270` |
| per-satellite baseband power (once per satellite with ≥1 active beam) | `P_BB` | **0.200 W** | `env/link_budget.py:273` |
| fixed term assembled | `P^f = Σ_s(N^act_s·P_cir) + 1{N^act_s>0}·P_BB` | — | `env/link_budget.py:521-547`, called `env/step.py:992` |
| PA max efficiency | `ξ_max` | **0.35** | `env/link_budget.py:254` |
| PA saturation power | `p_sat = p_max·10^(BO/10)` | **5.217758 W** | `env/link_budget.py:260-263` (`p_max=1.65 W` `:175`, `BO=5 dB` `:257`) |
| per-link RF ceiling | `p_max` | **1.65 W** | `env/link_budget.py:175` |
| segment-start RF power | `p⁰` | **0.825 W** | `env/link_budget.py:213` |

**PA DC conversion, used verbatim from the module and not reimplemented** — `pa_efficiency` (`env/link_budget.py:468-494`): `ξ(p) = min(ξ_max, ξ_max·√(p/p_sat))`; `supply_power_w` (`env/link_budget.py:496-519`): `P_DC(p) = p/ξ(p)`. Since every per-link power obeys `p ≤ p_max = 1.65 W < p_sat`, the `min` never binds at the per-user level and `P_DC(p) = √(p·p_sat)/ξ_max = 6.52697·√p` W — **concave and increasing**. **[V for the code path, D for the closed form.]**

| accounting | per-beam PA draw | site of the operator it replaces |
|---|---|---|
| **`MAX`** (current) | `P_PA,b = P_DC( max_{u∈b, served} p_u )` | `beam_power_w`, `env/link_budget.py:439-465` ("the aggregation is a **max over served users**, never a sum or a mean"), called `env/step.py:886` |
| **`TDM_AIRTIME`** | `P_PA,b = Σ_{u∈b, served} τ_u · P_DC(p_u)`, `τ_u = 1/U_b` | the review's recommended form. Per-user RF → per-user PA DC draw **first**, then integrate over airtime. |
| **`ADDITIVE`** | `P_PA,b = P_DC( Σ_{u∈b, served} p_u )` | Ha et al. GLOBECOM 2022 §II-B eq. 3 form. |

Total in all three: `P^N = P^f + Σ_b P_PA,b`.

**`U_b` is the same divisor the rate uses.** `τ_u = 1/U_b` with `U_b = eligible_load_by_beam` (`env/service.py:251`), which is exactly what `user_beam_load()` (`env/service.py:164-182`) feeds to `shannon_rate_bps` at `env/step.py:964-971`. I opened `resolve_service` and confirmed `eligible[beam]` is incremented **once per served user and only for served users** (`env/service.py:244-251`), so `U_b` equals the served member count exactly and **`Σ_{u∈b} τ_u = 1` exactly** for every radiating beam — the `≤ 1` constraint holds with equality. **[V]**

### Measured fixed-term share (3 episodes, mean over steps) **[V]**

| arm | mean `P^f` | mean `P^N` (`MAX`) | fixed share | PA share |
|---|---:|---:|---:|---:|
| `MAX_NOMINAL_GAIN` | 23.036 W | 407.995 W | 5.65% | **94.35%** |
| `TRAINED e6b063ef…` | 25.033 W | 437.607 W | 5.72% | **94.28%** |

The PA term is ~94% of system power, so the aggregation operator is where essentially all the leverage is. That is the review's premise and it is correct.

---

## 2. `ADDITIVE` is not this simulator's PHY. I report it anyway, labelled, as a stress bound.

The brief asks me to say so rather than fabricate one, so: **this PHY does not admit simultaneous streams within a beam.** Three independent pieces of the source say so. **[V]**

1. **Noise is evaluated at the FULL beam bandwidth while rate is divided by `U_b`.** `noise_power_w` returns `σ² = k_B·T_sys·B^w` (`env/link_budget.py:367-372`), and the step physics calls it with the whole `beam_bandwidth_hz`, documented "**per beam, independent of its load**" (`env/step.py:214-217`). The rate then divides by `U_b` (`env/link_budget.py:590-616`). Full-bandwidth noise with a `1/U_b` rate share is the **time-division** reading — one user on air at a time, whole band, `1/U_b` of the interval. Under FDMA the noise would have to be `k_B·T_sys·(B^w/U_b)`; it is not.
2. **The docstring states the mechanism outright**: "*The beam is time-shared, so its bandwidth is divided by the number of users it serves*" (`env/link_budget.py:600-602`).
3. **There is no precoder and no per-user beam.** A radiating beam is one `(norad_id, cell_id)` pair carrying **one** power and **one** boresight, the cell centre (`build_radiating_beams`, `env/interference.py:119-152`; `_boresight`, `env/step.py:1517-1538`). Users on the same beam differ only by their off-axis angle into that single pattern. A multiuser precoder — the object whose per-user powers Ha et al. sum — has no representation here.

So `ADDITIVE` is **not a description of this simulator's physics**. I report its column as a **labelled upper-bound stress test**: the most aggressive standard aggregation operator, applied to the denominator only, to answer "could *any* mainstream aggregation flip this?". It should not be read as a corrected physics.

**One term `ADDITIVE` needs and does not get here, disclosed:** under a genuinely additive PHY the per-beam radiated power fed to `build_radiating_beams` (`env/step.py:886-897`) would also be the sum rather than the max, raising co-channel interference and therefore **lowering bits** for everyone. I deliberately did not apply that, because the brief's clean decomposition holds the actions *and* the channel fixed and prices only the joules. Its net direction across arms is **not established** — `MAX_NOMINAL_GAIN` runs fewer but more heavily loaded beams, i.e. fewer interferers each radiating more — and I did not measure it. **[I, sign undetermined.]**

---

## 3. Full panel — 4 arms × 24 episodes, frozen seeds (42/1337/7) **[V]**

Bits, served, handover rate and mean active beams are **identical across the three accountings by construction** (same run), so they are listed once.

| arm | pooled bits | served | handover rate | mean active beams | users/beam |
|---|---:|---:|---:|---:|---:|
| `RANDOM_MASKED` (harness check) | 1.842866e+14 | 0.9360 | 0.8680 | 76.642 | 1.221 |
| `GREEDY_R1R2` | 2.617496e+14 | 0.9955 | 0.1418 | 76.300 | 1.305 |
| **`TRAINED e6b063ef…`** (greedy) | 2.848622e+14 | 0.9988 | 0.2799 | 67.904 | 1.471 |
| **`MAX_NOMINAL_GAIN`** | 3.266731e+14 | 0.9981 | 0.7120 | **63.717** | **1.566** |

`MAX_NOMINAL_GAIN` is indeed the **most consolidated** arm — fewest radiating beams, highest occupancy — which is exactly the arm the review predicted the `max` operator would flatter. **[V]**

### Pooled joules and pooled EE, per accounting

| accounting | arm | pooled joules | **pooled EE (bit/J)** | sem | vs `MAX` column |
|---|---|---:|---:|---:|---:|
| `MAX` | `RANDOM_MASKED` | 3.473162e+06 | 53,060,175.56 | 394,444 | — |
| `MAX` | `GREEDY_R1R2` | 3.454818e+06 | 75,763,635.84 | 633,759 | — |
| `MAX` | **`TRAINED`** | 3.059385e+06 | **93,110,907.97** | 902,313 | — |
| `MAX` | **`MAX_NOMINAL_GAIN`** | 2.929683e+06 | **111,504,571.39** | 1,095,687 | — |
| `TDM_AIRTIME` | `RANDOM_MASKED` | 3.466698e+06 | 53,159,114.24 | 395,232 | +0.19% |
| `TDM_AIRTIME` | `GREEDY_R1R2` | 3.428135e+06 | 76,353,338.78 | 644,789 | +0.78% |
| `TDM_AIRTIME` | **`TRAINED`** | 3.026859e+06 | **94,111,458.32** | 895,972 | +1.07% |
| `TDM_AIRTIME` | **`MAX_NOMINAL_GAIN`** | 2.913089e+06 | **112,139,763.26** | 1,122,381 | +0.57% |
| `ADDITIVE` | `RANDOM_MASKED` | 3.755301e+06 | 49,073,720.12 | 400,748 | −7.51% |
| `ADDITIVE` | `GREEDY_R1R2` | 3.811517e+06 | 68,673,335.40 | 665,446 | −9.36% |
| `ADDITIVE` | **`TRAINED`** | 3.540181e+06 | **80,465,428.82** | 888,512 | −13.59% |
| `ADDITIVE` | **`MAX_NOMINAL_GAIN`** | 3.491118e+06 | **93,572,620.07** | 960,658 | −16.08% |

**The full ranking is unchanged in all three accountings**, all four arms, no exceptions: `MAX_NOMINAL_GAIN` > `TRAINED` > `GREEDY_R1R2` > `RANDOM_MASKED`. **[V]**

---

## 4. The table that decides it

| accounting | `MAX_NOMINAL_GAIN` EE | trained EE | **ratio** | gap | resolvability |
|---|---:|---:|---:|---:|---:|
| **`MAX`** (current, parity) | 111,504,571.39 | 93,110,907.97 | **1.1975** | +19.76% | 13.0 sem |
| **`TDM_AIRTIME`** (review's recommended form) | 112,139,763.26 | 94,111,458.32 | **1.1916** | +19.16% | 12.6 sem |
| **`ADDITIVE`** (stress bound, not this PHY) | 93,572,620.07 | 80,465,428.82 | **1.1629** | +16.29% | 10.0 sem |

**Answer to the question asked, restated plainly: yes under both. 1.1916 under `TDM_AIRTIME`, 1.1629 under `ADDITIVE`.** All three gaps are resolvable at 24 episodes by ≥10 sem (unpaired; the arms share episodes and seeds, so a paired test would be tighter and I did not add one). **[V for the EE and sems, D for the ratios and sems-of-difference.]**

### Declared reading, applied as written

> **The ranking survives all three → the 19.8-22.2% result has external physical credibility, and the `max` operator was not carrying it.**

That is the measured branch and I apply it exactly as written. I am **not** looking for a rescue because none is needed, and I am not widening the search.

### How much of the gap the operator accounts for — and the ceiling on how much it ever could

| | gap over the trained checkpoint | accounted for by the operator |
|---|---:|---:|
| `MAX` → `TDM_AIRTIME` | 19.755 pp → 19.156 pp | **0.598 pp = 3.0% of the gap** |
| `MAX` → `ADDITIVE` | 19.755 pp → 16.289 pp | **3.465 pp = 17.5% of the gap** |

**And there is a hard ceiling, because the operator only touches the denominator.** Decomposing the pooled-EE ratio into its two halves — a decomposition that is exact, since bits are identical across columns: **[D from [V] totals]**

| accounting | bits ratio MAX/TRAINED | joules ratio MAX/TRAINED | EE ratio |
|---|---:|---:|---:|
| `MAX` | **1.14678** | 0.95761 | 1.19755 |
| `TDM_AIRTIME` | **1.14678** | 0.96241 | 1.19156 |
| `ADDITIVE` | **1.14678** | 0.98614 | 1.16289 |

`MAX_NOMINAL_GAIN` delivers **14.68% more bits** than the trained checkpoint, and no aggregation operator can move that — it is a property of which beam the rule points at. So:

- The **entire** denominator-side advantage is worth at most `19.755 − 14.678 = 5.08 pp`, i.e. **25.7% of the gap**. Even a hypothetical accounting that exactly equalised the two arms' joules would leave **+14.68%**.
- `ADDITIVE` already extracts **3.465 pp of that 5.08 pp — 68% of everything the operator could ever be worth** — and drives the joules ratio to 0.9861, i.e. it very nearly neutralises `MAX_NOMINAL_GAIN`'s denominator advantage outright. The residual +16.29% is essentially the bits advantage.

**This is the substantive finding and it is stronger than the ratio table alone.** The review's mechanism is real: `ADDITIVE` does penalise the consolidated arm harder (its joules rise **+19.16%** against the trained arm's **+15.72%**) — but the result was never a denominator effect, so re-pricing the denominator cannot reach it.

### An asymmetry worth naming, because it runs *against* the review's expectation

`TDM_AIRTIME` **lowers** every arm's joules relative to `MAX`, and lowers the **trained** arm's more (−1.06%) than `MAX_NOMINAL_GAIN`'s (−0.57%). That is not arbitrary: `P_DC(·)` is concave and increasing, so an airtime-weighted **mean** of per-user draws is always **≤** the draw of the **max** user (Jensen), with the discount growing in within-beam power dispersion. The trained policy holds segments and lets its link powers inflate — 4–5% of its links sit at `p⁰` against `MAX_NOMINAL_GAIN`'s 70–76% (positive control, attachment surface) — so it has more dispersion and collects the bigger discount. **`TDM_AIRTIME` therefore helps the learner, not the churner**, and narrows the ratio by 0.6 pp. **[V for the joules, D for the Jensen argument.]**

---

## 5. The mechanism: marginal joules of adding one user to an already-radiating beam

Measured as a **leave-one-out** on the actual configurations: for every radiating beam with `U_b ≥ 2`, for every member `u`, `Δ = P_PA,b(members) − P_PA,b(members\{u})`, with the eligible load stepping `U_b → U_b − 1` in the without-`u` state (only the airtime accounting sees that divisor). Joules are `Δ·dt`, `dt = 30.08 s`. **[V]**

| accounting | arm | n | mean ΔP | **mean ΔE** | median ΔP | exactly 0 | genuinely negative |
|---|---|---:|---:|---:|---:|---:|---:|
| **`MAX`** | `MAX_NOMINAL_GAIN` | 14,225 | +0.055058 W | **+1.656 J** | **+0.000000 W** | **83.3%** | 0% |
| **`MAX`** | `TRAINED` | 13,219 | +0.127561 W | **+3.837 J** | **+0.000000 W** | **68.3%** | 0% |
| **`TDM_AIRTIME`** | `MAX_NOMINAL_GAIN` | 14,225 | **+0.000000 W (exact)** | **0.000 J (exact)** | +0.000000 W | 46.9% | **22.0%** |
| **`TDM_AIRTIME`** | `TRAINED` | 13,219 | **+0.000000 W (exact)** | **0.000 J (exact)** | +0.000000 W | 25.4% | **36.3%** |
| **`ADDITIVE`** | `MAX_NOMINAL_GAIN` | 14,225 | +2.116591 W | **+63.667 J** | +2.263490 W | 0% | 0% |
| **`ADDITIVE`** | `TRAINED` | 13,219 | +2.145875 W | **+64.548 J** | +2.288288 W | 0% | 0% |

**Canonical single instance, reproducible by hand** — a beam already serving 2 users at `p⁰ = 0.825 W` gains a third, also at `p⁰`: **[V]**

| accounting | before | after | **Δ** |
|---|---:|---:|---:|
| `MAX` | 5.927900 W | 5.927900 W | **+0.000000 W = +0.000 J** |
| `TDM_AIRTIME` | 5.927900 W | 5.927900 W | **+0.000000 W = +0.000 J** |
| `ADDITIVE` | 8.383317 W | 10.267425 W | **+1.884108 W = +56.674 J** |

**The review's claim about `MAX` is confirmed and then some.** Under `MAX` the marginal is **exactly 0 W for 83.3% of added users** on `MAX_NOMINAL_GAIN`'s beams (79.07% bit-exact zeros plus 4.22% at −8.9e-16 W, which a dedicated check confirmed is float noise, not a real negative — `neg_check.py`, largest magnitude 8.882e-16 W). The mean is non-zero only because removing the *one* member who holds the beam maximum does cost something.

**But `TDM_AIRTIME` does not repair that defect — it makes it exact.** With `Σ_u τ_u = 1`, the airtime accounting is the **arithmetic mean** of per-user DC draws, so the marginal has the closed form

> `Δ = ( P_DC(p_new) − P̄_DC,b ) / (U_b + 1)`

and is **exactly zero** for a user drawing the beam's own mean, **negative** for any user below it. The measured mean over all LOO pairs is `0.000000 W` to machine precision — that is an algebraic identity, not a coincidence: within one beam the LOO marginals sum to exactly zero. Genuinely negative marginals reach **−1.122 W** (verified in `neg_check.py`, 2 episodes of `MAX_NOMINAL_GAIN` only; the panel's p10 is −0.0972 W for `MAX_NOMINAL_GAIN` and −0.2198 W for `TRAINED`). **[V for the measurement, D for the closed form.]**

So on the specific mechanism the review names — *"a new user below the beam's existing maximum has exactly zero marginal RF cost, which makes consolidation artificially attractive"* — **the airtime model the review recommends has the same property, in a stronger form.** Only `ADDITIVE` prices an added user, at **~+64 J per user per 30.08 s step**, roughly **38× the `MAX` mean**. And `ADDITIVE` is the one accounting that this PHY does not support (§2).

---

## 6. Would any policy's own decisions change under a different accounting?

Noted as instructed; the fixed-action comparison above is the clean decomposition and stands first. **[V for the first three, I for the fourth.]**

- **`MAX_NOMINAL_GAIN`** — argmax over `channel_quality` only. Reads **no** power quantity. Decisions are **invariant** to the accounting.
- **`GREEDY_R1R2`** — scores `0.5·κ·r̂1 + 0.3·r̂2` with `r̂1 = (B/(load+1))·log₂(1+SINR)`, a **rate** proxy with no power term. Decisions are **invariant**.
- **`RANDOM_MASKED`** — invariant by definition.
- **`TRAINED e6b063ef…`** — frozen weights, so its decisions here are invariant too. But its *training signal* `r1` carries `P^N` in the denominator, so a checkpoint **retrained** under `TDM_AIRTIME` or `ADDITIVE` could differ. That is a retraining question, explicitly out of scope (the brief's instruction is verbatim: do not retrain). **Not established, and not claimed either way.**

---

## 7. Evidence classification

**[V] Verified by running code this session, read-only, no gradient step:** the 4-arm × 24-episode panel with all three denominators (`poweracct.log`, `power_accounting_result.json`); the per-step parity `|MAX_recomputed − env P^N| ≤ 2.274e-13 W`; the bit-identical reproduction of all four published `none` figures; the LOO marginal distributions; the float-noise check on `MAX`'s apparent negatives; the fixed-power share probe; the canonical 2→3 instance.

**[V] Verified by reading local source, with file:line:** `env/link_budget.py:175, 213, 254, 260-263, 270, 273, 367-372, 439-465, 468-494, 496-519, 521-547, 549-588, 590-616`; `env/step.py:214-217, 534-536, 886-897, 964-971, 979-993, 1517-1538`; `env/service.py:164-182, 244-251`; `env/interference.py:119-152`; `env/constants.py:76`.

**[D] Derived:** the three ratios, the gap percentage points, the bits/joules decomposition, the 5.08 pp ceiling and the 25.7% figure, the `6.52697·√p` closed form, the airtime marginal's closed form, the users-per-beam column, the sem-of-difference figures.

**[I] Inferred, not measured:** the direction of the unmodelled `ADDITIVE` interference term (§2) — **sign undetermined**; the behaviour of a checkpoint retrained under a different accounting (§6).

**Limits, stated rather than papered over:**
- `ADDITIVE` is a **denominator-only** re-pricing of a PHY that does not admit it. It is a bound on what the aggregation operator can do, not a corrected simulator.
- One seed triple (42/1337/7), 24 episodes, 100 users, stream positions 0–23. Nothing here speaks to other seeds, user counts, or constellations.
- I did **not** sweep the PA model, add arms, re-select, or tune anything. The three accountings were fixed before the run and all three are reported.
- I was not surprised by the outcome — the declared first branch held at ≥10 sem in every column — so I did **not** re-run at larger n.

**Not established:** anything about arms, accountings, seeds or physics settings not run here.
