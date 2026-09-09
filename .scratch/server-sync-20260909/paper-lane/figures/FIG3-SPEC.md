# FIG3-SPEC — Primary contrast figure: route marginals on pooled energy efficiency

**Status.** Specification only. No results exist. Every numeric slot in this
document is a placeholder `⟨結果待填⟩`. Producing this figure before
`PHYSICS-GO` and the calibration freeze is barred (brief §E).

**What it shows.** The single primary claim for the primary setting `a-r0`: the
learned neutral-source marginal of each route on realised pooled energy
efficiency, with its decision interval and the sealed practical margin.

**Authority.** `_work/SUCCESSOR-BRIEF.md` §A.9 (endpoint), §A.11 (arms and
experiments), §A.12 (admission), §D (estimator, panel, zero outcomes);
contract v1 §§C3, D1–D5 with amendments v1.1 §§1, 3 and v1.2 §§3, 4.

---

## 1. Panel and estimand

| Item | Value |
|---|---|
| Setting | `a-r0` only. Every other cell is exploratory and must not appear in this figure. |
| Experiment | (i) *learned neutral-source experiment* — the primary for the C1/C2/C3 claims. Not the oracle factor-score removal, not the checkpoint knockout. |
| Arms | `FULL`, `DROP_C1`, `DROP_C2`, `DROP_C3`, `ALL_NEUTRAL_CONTROL`, external `BASELINE` (6). |
| Panel | 6 arms × **16** learner seeds × 2 worlds per date over ≈ 160 claim dates (≈ 320 worlds per arm-seed). |
| Split | TRAIN only. No TEST. |
| Endpoint | Realised pooled EE over all **48 boundaries** with realised fading, 47 trapezoidal sub-intervals per 30.08 s step. |
| Estimand | Pooled `ΣB / ΣE` — a **ratio of sums, never a sum of ratios**, and never a mean of per-step or per-row EE. |

**Contrast plotted.** For each route $x \in \{C1, C2, C3\}$, the relative
marginal of informative-source training:

$$\Delta_x \;=\; \frac{\mathrm{EE}_{\mathrm{FULL}} - \mathrm{EE}_{\mathrm{DROP\_}x}}{\mathrm{EE}_{\mathrm{DROP\_}x}} \times 100\ \%$$

recomputed **inside every bootstrap draw** from the resampled sums, never from
per-draw averages of ratios.

---

## 2. Axes

### Primary panel (a) — route marginals

| | |
|---|---|
| **y (categorical)** | Route contrast, three rows top to bottom: `C1`, `C2`, `C3`. Row labels carry the arm pair, e.g. `C3 : FULL vs DROP_C3`. |
| **x (continuous)** | Relative pooled-EE marginal, **per cent (%)**. Units are *relative*, not percentage points — δ is "+0.5 % relative" (v1.4), and mislabelling this as pp is a known past error (brief §B). |
| x range | Symmetric about 0, chosen after results; must include 0 and the +0.5 % margin line with ≥ 15 % of the axis width beyond the widest interval end. |
| x ticks | Every 1 %, minor every 0.5 %. |
| Zero line | Solid, `#94A3B8`, 1.0 pt, drawn beneath the markers. |
| Margin line | **δ = +0.5 % relative**, dashed `#DC2626`, 1.1 pt, labelled `δ = +0.5 %（實務邊際）`. |

### Secondary panel (b) — seedwise paired effects

Required by contract v1 §D2 ("seedwise paired effects reported"). Same x axis,
shared with panel (a). One row per route; within a row, 16 small markers, one per
learner seed, showing the paired per-seed effect, with the pooled estimate
overplotted. This panel is what prevents a single-seed artefact from reading as a
route effect.

### Panel (c) — a bare count strip

Undefined and zero-outcome draws, per contract v1 §D3: `B = 0` with `E > 0` **is**
`EE = 0` and is a defined draw; a draw is undefined only when a denominator
($E$, or the comparator's EE) is 0. Undefined draws are **recorded and counted,
never substituted**. Panel (c) prints those counts per contrast. If all counts are
zero, the panel collapses to a single line stating so — it is never omitted.

---

## 3. Interval definition and sidedness

This is the part most easily got wrong. State all four properties on the figure.

**Construction.** Primary interval = **two-way pigeonhole bootstrap** over
`dates × learner seeds`, with:
- arms **paired within resamples** (the same resampled dates/seeds for both arms
  of a contrast),
- the **ratio recomputed per draw** from resampled numerator and denominator sums,
- **central 95 % percentile** interval,
- QoS margins formed with **additive numerators and denominators inside draws**.

Supplementary, plotted only as thin secondary whiskers or reported in the caption:
one-way cluster bootstrap and the delta method. They are never the decision
object.

**Sidedness — the decision is one-sided; the drawn interval is two-sided.**
The sealed decision rule uses the **2.5th-percentile lower bound** against
δ = +0.5 % relative. The plotted interval is the central 95 % percentile
interval, whose lower end *is* that 2.5th percentile. Therefore:

- Draw the full two-sided bar, but **emphasise the lower end** (a heavier cap or
  a filled triangle) to show which end carries the decision.
- The caption must say, verbatim in substance: *the decision uses the one-sided
  2.5th-percentile lower bound; the bar shows the central 95 % percentile
  interval, whose lower end is that bound.*
- Never describe the bar as "the 95 % confidence interval" without the
  coverage disclosure below.

**Coverage disclosure — mandatory, no exceptions.** The two-way pigeonhole
percentile interval **under-covers**: measured **0.89–0.92 against 0.95 nominal**
at the sealed seed counts. Contract v1.1 §3 forbids any post-hoc widening. The
figure must therefore print, adjacent to the intervals (not only in the caption):

> 區間覆蓋率實測 ⟨結果待填⟩（名目 0.95）；未做事後加寬。

and, per contract v1.2 §4, the **one-sided coverage of the bound actually used**
— not only the two-sided interval coverage — with its Monte-Carlo uncertainty.

**Multiplicity.** The primary claim is the **conditional intersection–union
conjunction** for `a-r0`. Components are shown with their own intervals but **no
component-wise discovery is claimed**. The figure must not annotate any single
route as "significant" on its own; significance attaches only to the conjunction.

---

## 4. Marks and encoding

| Element | Encoding |
|---|---|
| Point estimate | Filled circle, 5 pt, `#1E3A8A`. |
| Primary interval | Horizontal bar, 2.2 pt, `#2563EB`; lower cap 3.0 pt and 1.5× height (the decision end). |
| Supplementary intervals | Hairline 1.0 pt, `#94A3B8`, offset −6 pt vertically. |
| Seedwise markers (panel b) | Open circles, 2.5 pt, `#7DA9F0`, jittered vertically only, deterministic jitter seeded by seed index. |
| Conjunction verdict | A single badge in the corner: `ADMIT_FULL` / `ADMIT_C1C2` / `NOT_ADMITTED`, coloured `#16A34A` / `#D97706` / `#DC2626`. |
| Arms not in a contrast | `ALL_NEUTRAL_CONTROL` and `BASELINE` appear as reference rows in a separate stub panel, never inside the route contrasts. |

Typography follows the deck invariant: Times New Roman for Latin and maths,
Noto Serif CJK TC for Traditional Chinese, 28/24/20 pt only.

---

## 5. Chinese labels

Only terminology attested in `active-symbol-table-v023-20260905.md` (see
`FIGURE-NOTES.md` for the citation rules and the three successor gaps).

| Slot | String |
|---|---|
| x axis | `合併能量效率相對邊際（%）` |
| Panel (a) title | `(a) 各路徑之來源邊際` |
| Panel (b) title | `(b) 各學習種子之配對效應` |
| EE symbol in caption | `η^N`（bit/J）— **[V]** §10.13.1, "總 delivered bits 除以總 network energy" |
| Margin line | `δ = +0.5 %（實務邊際）` |
| Zero reference | `無效應` |

`η^N` is the correct symbol: the estimand is total delivered bits over total
network energy, which is exactly the table's definition, and explicitly "不是
per-row EE 平均".

---

## 6. Data contract

Render from a single CSV, `figure3-data.csv`, one row per contrast × estimator:

```
contrast,          # C1 | C2 | C3
arm_num,           # FULL
arm_den,           # DROP_C1 | DROP_C2 | DROP_C3
estimator,         # two_way_pigeonhole | one_way_cluster | delta_method
point_pct,         # relative marginal, per cent
lo_pct, hi_pct,    # central 95 % percentile ends; lo_pct is the decision bound
n_draws,           # bootstrap draws actually completed
n_dates, n_seeds,  # 160, 16
n_undefined,       # draws with a zero denominator (recorded, never substituted)
n_zero_bit,        # draws with B = 0, E > 0  (these are EE = 0, defined)
coverage_two_sided, coverage_two_sided_mc,
coverage_one_sided, coverage_one_sided_mc,
endpoint_boundaries,   # must equal 48
physics_digest, provider_digest, code_digest,
attempt_registry_id
```

Plus `figure3-seedwise.csv`: `contrast, seed_index, effect_pct`.

**Render-time assertions** (fail loudly, do not silently plot):
1. `endpoint_boundaries == 48` on every row.
2. `estimator == "two_way_pigeonhole"` exists for all three contrasts.
3. `coverage_two_sided` and `coverage_one_sided` are present and non-null.
4. Every `physics_digest` matches the training digest.
5. `n_seeds == 16` and `n_dates` matches the sealed allocation manifest.
6. No row carries a `PILOT_NOT_CLAIM` label (Track F artefacts must never reach
   this figure).

---

## 7. Receipt fields this figure depends on

Per-step canonical receipts, from which merge re-aggregates every summary and
**refuses on disagreement** (brief §A.10):

- **hex floats** for bits and joules and for each energy component — the figure's
  numerator and denominator must be reconstructible bit-for-bit;
- additive **opportunities** and **served counts** over the **full roster**;
- prior and current **physical identities** `(NORAD, beam-chain)` — never slot
  indices;
- **event type**; **Φ numerator and denominator**;
- **provider / code digests**;
- the **energy-boundary sentence** verbatim in every receipt header (v1.8 §3);
- the **power-solve certificate per profile** and the `CONVERGED_SLOW` share;
- `m_target`, `m_tx` and the realised outcome, separately, per user-step;
- the per-boundary `rate_target_attained` series (QoS reporting only, **no
  decision use**);
- **deadline-miss fraction**;
- an `ATTEMPT-REGISTRY` `STARTED` record predating any outcome-producing call.

---

## 8. Prohibitions specific to this figure

1. No number from Track F, any synthetic fixture, any smoke run, or any cost
   estimate may appear. Track F artefacts carry `PILOT_NOT_CLAIM`.
2. No TEST-split quantity. No episode-count claim.
3. Do not merge or average distinct pre-registered blocks.
4. Do not call any result "coordination"; the sealed wording rule forbids it.
5. Do not describe a lower-bound failure as a negative result — "a lower-bound
   failure alone is inconclusive" (contract v1 §C6).
6. A zero C3 marginal is reported as such and **never patched**; it ends the
   positive C3 claim under this scope and does not license changing features,
   catalogues, sources or regimes.
7. The claim sentence must retain its full qualification: *"informative source
   training for route x improved pooled EE relative to the specified neutral
   source training, with the other routes informative and all heads retained."*

---

## 9. Caption skeleton

> **圖 3.** `a-r0` 設定下各路徑之來源邊際（合併能量效率 `η^N`，bit/J，
> ratio of sums）。點為估計值，粗線為兩向 pigeonhole bootstrap 之中央 95 %
> 百分位區間；**決策使用單側 2.5 百分位下界**對照實務邊際 δ = +0.5 %（相對）。
> 區間覆蓋率實測 ⟨結果待填⟩、單側 ⟨結果待填⟩（名目 0.95），未做事後加寬。
> 面板組合為條件交集–聯集單一主張；各成分不單獨宣稱發現。
> 端點於 48 個邊界以實現衰落計算。僅 TRAIN，無 TEST。
