# FIG4-SPEC — Coordination attribution and the QoS / deadline co-primaries

**Status.** Specification only. No results exist. Every numeric slot is
`⟨結果待填⟩`. Producing this figure before `PHYSICS-GO` is barred (brief §E).

**What it shows.** The two things Figure 3 deliberately leaves out, and which the
admission decision actually turns on: (a) whether the *set-level* layer earns its
place against the exact and unilateral comparators, and (b) whether the QoS
co-primaries, the deadline behaviour and the physics-validity certificates pass.

Figure 3 answers "did informative source training for route $x$ help?".
Figure 4 answers "is the coordinator doing something a cheaper selector could
not, and did it stay inside its constraints while doing it?".

**Authority.** `_work/SUCCESSOR-BRIEF.md` §A.5 (selectors), §A.7 (selection),
§A.8 (guards), §A.12 (admission, load-bearing certificates), §D.2 (deadline);
contract v1 §§C2, C4, D2 with amendments v1.2 §3 and v1.6 §4.

---

## 1. Panel (a) — selector ladder on realised pooled EE

**Estimand.** Realised pooled `ΣB / ΣE` at 48 boundaries, relative to `BASE`
($a^0$, the validated two-head proposal), for each selector:

| Row | Selector | What it is |
|---|---|---|
| 1 | `BASE` ($a^0$) | Reference at 0 % by construction. |
| 2 | `S_UNI` | Iterated exact unilateral improvement to a local optimum, **full legal option set** (not the top-8 shortlist), own compute budget, **termination certificate required**. |
| 3 | `UNI` | Unilateral-only search retaining all three score terms — reported separately because **search value ≠ interaction value**. |
| 4 | `S0` | The set selector with the **exact** $\Psi_A$. |
| 5 | `S3` | The **deployed** learned set head $\hat\Psi_\theta$. |
| 6 | `U1 / J1` ceiling | Exact-F oracle. A **ceiling arm, never a factor arm** — plot in grey, visually separated, labelled as a bound. |

**Axes.** y categorical (the six rows, in the order above, `BASE` at the top).
x continuous, relative pooled-EE gain over `BASE`, **per cent (%) relative**.
Intervals exactly as in FIG3-SPEC §3 — two-way pigeonhole, paired within
resamples, ratio recomputed per draw, central 95 % percentile, decision on the
one-sided 2.5th-percentile lower bound, with both measured coverages printed.

**The two contrasts that are load-bearing** must be drawn as explicit brackets
spanning their rows, not left for the reader to subtract:

1. **`S0` vs `BASE`** — realised gain, decision threshold **≥ +1 %**.
2. **`S0` vs certified `S_UNI`** — must exceed the certified numerical error.

**The certification gate is a visual state, not a footnote.** If `S_UNI` has no
termination certificate it is **budget-limited**, the contrast is **not
load-bearing**, and the row must be hatched and labelled `未取得終止證明`. A
budget-limited `S_UNI` row must never be drawn in the same style as a certified
one.

**The learned-value axis.** `S3` vs matched `S0` is a **separate, predeclared**
axis reported beside — not inside — the ladder, under **equal computation budget
including timeouts**. State the bound explicitly on the figure: over one exactly
evaluated catalogue, **`S3` cannot exceed `S0`'s maximum of the same score**.
The only admissible learned claims are therefore (i) better realised closed-loop
pooled EE under model mismatch, (ii) equal decision quality at materially lower
measured end-to-end computation, or (iii) a measured residual task. **The claim
axis is named before training** and must be printed on the figure.

---

## 2. Panel (b) — decision-relevant nonadditivity

The C3 condition in `ADMIT_FULL` is not "the interaction term is nonzero" — the
requirement `g_I ≠ 0` was **withdrawn**. It is that the coordinator's choice
*differs from the additive/unilateral optimum at a reported non-trivial fraction
of anchors*, including rejected harmful joint moves.

| | |
|---|---|
| x | Fraction of anchors, **per cent (%)**, 0–100. |
| y | Three categories: `選擇異於加性最適` / `選擇異於單邊最適` / `拒絕有害聯合移動`. |
| Marks | Horizontal bars with the same interval treatment; the third category is the one most often forgotten and must be present even when zero. |
| Companion | Tie frequency at the immediate-score maximiser (v1.6 §2), because with a unique immediate maximiser a tie-break-only continuation cannot change the selection, so **`FULL` and `DROP_C2` coincide** — the figure must show the tie frequency that makes that statement checkable. |

Print alongside: `set-level C2 邊際 = ⟨結果待填⟩`. A zero set-level C2 marginal is
**reported as such and never patched**; C2's certificate in the physics matrix is
**forecast validity, not a selection marginal**.

---

## 3. Panel (c) — QoS co-primaries with sealed margins

Three co-primaries, each with its own prospective non-inferiority margin. Bars
show the arm-vs-comparator difference with the same interval construction;
margins are drawn as dashed threshold lines and the pass/fail side is shaded.

| Co-primary | Unit | Sealed margin | Direction |
|---|---|---|---|
| Complete-service availability | **percentage points (pp)** | above **−0.5 pp** | higher is better |
| Handover rate | **% relative**, per user-step | below **+5 %** | lower is better |
| Φ-priced handover cost | **% relative**, per user-step | below **+5 %** | lower is better |

**Unit discipline.** Availability is in **pp**; the two handover quantities are
**relative %**. Mixing these is a known past defect — label each axis
independently and never share one x axis across all three.

**Denominator rule.** QoS margins are formed with **additive numerators and
denominators inside draws**. A cell whose denominator is zero is
`FAIL_UNDEFINED_DENOMINATOR` — it is recorded and counted, never substituted and
never silently dropped.

---

## 4. Panel (d) — deadline, fallback and physics validity

This panel exists because timeout and fallback outcomes are **counted in $B$ and
$E$**, so they are part of the endpoint, not operational trivia.

| Quantity | Unit | Note |
|---|---|---|
| Deadline-miss fraction | % of anchors | Budget is **10 s** with 4-worker parallelism, inside a 30.08 s decision interval. The 10 s figure governs (contract v1 §F2); the engine prompt's "30.08 s wall" refers to the interval. |
| Fallback commits | % of anchors | Those anchors committed the **pre-validated $a^0$**. `BASE` is computed, validated and repaired *before* the coordinator's clock starts, which is why the fallback is always available. |
| Measured end-to-end selection time | **s** | Distribution, not just a mean; mark the 10 s budget line. Stage 4d measured **24.7 s** — the budget is **not currently met**, and the pre-declared escalation ladder (4-worker parallelism → one boundary per offset → M = 64 → 48) is binding. |
| Power-solve certificates | % of profiles | Stacked bar: `CONVERGED` / `CONVERGED_SLOW` / `INVALID`. A high `CONVERGED_SLOW` share is **a physics finding to discuss, not a reason to change the model**. `INVALID` stops the unit. |
| Catalogue size | rows per anchor | Guard ≤ 1 500; ≈ 1 200 expected. Also plot the stage-3 item-10 diagnostic: how many legal options fell **outside** the top-8 shortlist and the best excluded option's margin. |
| Null-action users | count | A user with zero legal candidates is unserved and excluded from the product; the catalogue never silently collapses to `{BASE}`. |

**No silent caps.** If any bound in this figure truncates what is shown
(top-$M$, shortlist, sampling), the figure must say what was dropped. A
suppressed truncation reads as full coverage.

---

## 5. Verdict strip

A single strip across the bottom binding the panels to the sealed decision.

**Admission trichotomy** (monotone; no branch weakens a condition another branch
imposes on the same factor):

- `ADMIT_FULL` — all load-bearing certificates pass: `S0` realised gain over
  `BASE` ≥ +1 %; `S0` > certified `S_UNI` beyond certified numerical error; C1's
  oracle marginal positive beyond numerical error; C3's interaction term
  decision-relevant; C2's forecast validity established; QoS / validity /
  deadline pass.
- `ADMIT_C1C2` — identical **except** the C3 conditions are not met. Training is
  admitted, **C3 is carried as an evaluated layer**, and the resulting learned C3
  statement is explicitly labelled as **lacking an oracle certificate**.
  `ADMIT_C1C2` is **not** "C3 failed" — the learned `FULL` vs `DROP_C3` test still
  runs, because a learned coordinator and an oracle removal are different
  estimands.
- `NOT_ADMITTED` — C1's oracle marginal or the QoS / validity / deadline
  conditions fail → contingency ladder rung 1.

**Claim ladder**, printed as the interpretation key:

- **Level B (primary)** — the C3 layer raises realised pooled EE over the
  C1 + C2 policy under the same deployable information, catalogue and 10 s
  budget: `FULL(S3 or S0)` vs `DROP_C3`, relative gain lower bound **> +0.5 %**,
  QoS margins met.
- **Level A (secondary, stricter)** — additionally `FULL` > information-matched
  `S_UNI` with decision-relevant nonadditivity.
- **Level C (tertiary)** — learned `S3` matches `S0` at lower compute; reported
  **only if A or B hold for `S0`**.

**Diagnostics may not be promoted.** Cap-hit rate, plateau share, ACM
distribution and lit-beam counts are **diagnostics only** and must be visually
subordinate — different panel, lighter weight, explicitly labelled. `J1 − U_all`
is **informative but not decisive**, because two purely additive good moves can
exceed the best single move.

---

## 6. Chinese labels

| Slot | String |
|---|---|
| (a) title | `(a) 選擇器階梯：相對 BASE 之實現合併能量效率` |
| (a) x | `相對 BASE 之增益（%）` |
| (b) title | `(b) 具決策相關性的非加性` |
| (b) x | `錨點比例（%）` |
| (c) title | `(c) QoS 共同主要指標與邊際` |
| (c) x, availability | `完整服務可用度差（百分點）` |
| (c) x, handover | `換手率相對差（%）` |
| (c) x, Φ cost | `Φ 計價換手成本相對差（%）` |
| (d) title | `(d) 期限、回退與物理有效性` |
| (d) x, time | `端到端選擇時間（s）` |
| Budget line | `預算 10 s` |
| Uncertified row | `未取得終止證明` |

Note `η^N` remains the EE symbol; `S3 / S0 / S_UNI / BASE / UNI / U1 / J1` are
document identifiers and stay in Latin, upright, per the symbol table's rule that
program identifiers and gate tokens are not paper symbols.

---

## 7. Data contract

`figure4-selectors.csv`:

```
selector,              # BASE | S_UNI | UNI | S0 | S3 | CEILING
is_ceiling,            # 1 for U1/J1 — never a factor arm
gain_vs_base_pct, lo_pct, hi_pct,
termination_certificate,   # PRESENT | ABSENT  (S_UNI only; ABSENT => not load-bearing)
compute_budget_s, measured_selection_time_s,
estimator, n_draws, n_dates, n_seeds,
coverage_two_sided, coverage_one_sided,
endpoint_boundaries    # must equal 48
```

`figure4-nonadditivity.csv`: `category, fraction_pct, lo_pct, hi_pct, n_anchors`
plus `tie_frequency_pct`, `set_level_c2_marginal_pct`.

`figure4-qos.csv`: `co_primary, unit, diff, lo, hi, margin, direction,
n_undefined_denominator`.

`figure4-ops.csv`: `deadline_miss_pct, fallback_commit_pct,
selection_time_quantiles, converged_pct, converged_slow_pct, invalid_pct,
catalogue_rows, excluded_legal_options, best_excluded_margin_db,
null_action_users`.

**Render-time assertions:**
1. `endpoint_boundaries == 48` everywhere.
2. If `selector == "S_UNI"` and `termination_certificate == "ABSENT"`, the row is
   hatched and excluded from the load-bearing bracket — assert the renderer did
   both.
3. `is_ceiling` rows are excluded from every contrast bracket.
4. `unit` for availability is `pp`; for handover rate and Φ cost is `pct_rel`.
   Assert no two of the three share an axis object.
5. `invalid_pct == 0`, otherwise refuse to render (an `INVALID` certificate stops
   the unit).
6. Compute budgets equal across `S3` and `S0` rows when the learned-value axis is
   drawn.

---

## 8. Receipt fields

All of FIG3-SPEC §7, plus specifically for this figure:

- **power-solve certificate per profile** and the `CONVERGED_SLOW` share;
- **deadline-miss fraction** as a co-reported QoS field;
- `S_UNI` **iteration count and termination certificate**, per anchor;
- the stage-3 item-10 **shortlist diagnostic** (count of legal options outside
  the top-8 shortlist; best excluded option's margin);
- **null-action user counter**;
- served counts over the **full roster** and additive opportunities, for the
  availability co-primary;
- Φ numerator and denominator, for the Φ-priced cost;
- catalogue row count per anchor;
- `ATTEMPT-REGISTRY` `STARTED` record predating any outcome-producing call.

---

## 9. Prohibitions

Everything in FIG3-SPEC §8, and additionally:

1. Never label the mechanism "coordination" in a claim sentence.
2. Never draw a budget-limited `S_UNI` as though certified.
3. Never let a ceiling arm (`U1`/`J1`) enter a factor contrast.
4. Never promote a diagnostic (cap-hit, plateau, ACM mix, lit beams) into a
   claim.
5. Never present `ADMIT_C1C2` as a C3 failure.
6. Never show the 24.7 s measurement as a *result*; it is a pre-outcome
   engineering measurement on the development path and must be labelled as such.
7. Do not report a marginal measured on nominal scores — **marginals are measured
   on the realised pooled endpoint `ΣB/ΣE`, never on nominal scores**.

---

## 10. Caption skeleton

> **圖 4.** `a-r0` 設定下的協調歸因與共同主要指標。(a) 各選擇器相對 `BASE`
> 之實現合併能量效率；載重對比為 `S0` vs `BASE`（門檻 +1 %）與 `S0` vs
> 已認證 `S_UNI`。(b) 具決策相關性的非加性；`g_I ≠ 0` 之要求已撤回。
> (c) QoS 共同主要指標與其前瞻性邊際（可用度以百分點，換手率與 Φ 計價成本以
> 相對百分比）。(d) 期限、回退與功率求解證書。區間同圖 3；決策使用單側
> 2.5 百分位下界，覆蓋率實測 ⟨結果待填⟩（名目 0.95），未做事後加寬。
> 天花板臂 `U1`/`J1` 僅為上界，不參與任何因子對比。僅 TRAIN，無 TEST。
