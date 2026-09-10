# Corrections to the plan, before execution

**2026-09-10 13:50 UTC. Every correction below is to a document I wrote today, and none of the
affected measurements has run.** Cost of fixing now: a paragraph each. Cost of fixing after the
run: the run.

Source: `PIPEAUDIT-ASTRA-2026-09-10.md`, an audit of the pipeline design — the one thing about
this project that had never been audited.

---

## C1 — two different denominators were being called the same thing

**Verified by reading both definitions.**

| formula | name | value at 10 s, SEALED |
|---|---|---|
| `(EE_t - EE_base) / (EE_fixed - EE_base)` | **incremental prize** — the anytime receipt's definition | **42.9081%** |
| `EE_t / EE_fixed` | **absolute fraction of fixed-point EE** — my acceleration pre-declaration and the scorer | **49.8155%** |

**I have been quoting `42.91%` as "the fraction recovered" while my own axis is defined as the
absolute fraction.** Those are different quantities and they differ by seven percentage points
here.

The `+100.7%` headroom is unaffected: it is `EE_fixed / EE_10 - 1` and is neither of the above.

**Correction.** F1 and F8 state which formula they use, in the axis label. `42.91%` may never
appear on an axis labelled absolute fraction. The scorer already computes the absolute form;
the figure plan and the acceleration pre-declaration are amended to say so explicitly.

## C2 — the two axes, as specified, are one axis

**Derived from the scorer's own arithmetic.** Both axes reuse the same arm pools, and axis B
divides by one fixed positive `EE_fixed`, so

```
fraction_FULL - fraction_DROP = (EE_FULL - EE_DROP) / EE_fixed
```

**Signs and ties must therefore match. No learned action is recomputed under a budget.**

So "one run, two axes" — my amendment 1 — does not produce two measurements. It produces one
measurement and a rescaling of it. **Reporting them as independent evidence would be double
counting.**

**Correction.** Until timed execution exists, the two are reported as **an offline EE contrast
and its normalised display**, in one table, never as two axes. A genuine acceleration result
requires arms to execute under the budget, with real cancellation and real fallback — which
`SELECTOR-LATENCY-2026-09-10.md` shows the current path cannot do (median `12.014 s`, 65% miss
rate, `_catalogue_with_census` at `8.299 s` median). **The acceleration axis is therefore not
available from the first run and is not claimed from it.**

## C3 — the continuation rule mishandles a non-monotone trajectory

My rule equates monotone movement with non-convergence. A relative-contrast sequence
`0, +2, -1, +3, -2%` is neither monotone nor flat; `0, 0, 0, +1, +1%` is a stepwise plateau;
and strictly monotone changes of vanishing size are already practically flat.

**Correction.** 500 remains the default stop under the existing "only if" rule. A moving but
non-monotone trajectory is labelled **"unresolved at the planned horizon"** — neither converged
nor unusable. Before any number exists, the following are fixed: strict versus non-strict
monotonicity, a practical tolerance on the EE scale, the seed aggregate, the extension length
and an absolute cap. **The rule remains blind to sign.**

## C4 — "flat zero" says less than I claimed

I wrote that a flat-zero contrast means the heads learned nothing usable. **It does not.**
`FULL` and neutral can both improve identically (`10, 12, 14, 16, 18` for each) leaving the
contrast at zero throughout; continuous score changes may never cross the catalogue's argmax
boundary; opposing per-anchor effects may cancel in pooled `B/E`; or every arm may execute
`a0` on a deadline miss.

**Correction.** The reading becomes: **"no observed incremental pooled EE advantage on this
fixed panel at the sampled checkpoints."** Before concluding anything about learning, report
absolute per-arm trajectories, assignment turnover, per-anchor `B/E`, and executed fallbacks.
**No inference from loss is permitted in either direction.**

## C5 — EE and service can move in opposite directions, and I gave no joint reading

Derived example: neutral delivers `100` bit at `10` J (`10` bit/J); `FULL` delivers `90` bit at
`6` J (`15` bit/J). **EE rises 50% while delivered bits fall 10%.** Both statements are true.

**Correction.** The signed EE contrast is retained and is called an **efficiency/service
trade-off**, not an unconditional improvement. A breach of the existing service guard is an
invalid deployment; a deterioration within the guard is a co-metric cost. **If no operational
acceptance rule is stated before the outcome, overall preference is left explicitly
unresolved** rather than decided afterwards.

## C6 — the knockout requirement was stated too strongly

Amendment 2 required decision-level separation between `ALL_NEUTRAL_CONTROL` and knockout
before the primary number may be reported. **Separation is necessary for that label, not
sufficient as causal validation** — and a well-fitted zero-target head becoming
decision-identical to knockout is a plausible success of its own objective, not a defect.

**Correction.** Keep the knockout label where equality holds. **Do not discard the trained
contrast, and do not seek a deliberately worse neutral fit in order to manufacture
separation.** Attribute the contrast to **informed-target versus exact-zero-target training,
finite horizon included**, and report the deployed knockout separately.

---

## What is now blocked that I had thought was not

The first training run can still produce **axis A** — an offline EE contrast against
`ALL_NEUTRAL_CONTROL` on the declared full-buffer numerator. That stands.

**It cannot produce an acceleration result.** That needs timed execution under the 10 s budget,
and the deployed path currently misses it on 65% of anchors with catalogue construction
dominating. **The acceleration claim's prerequisite is an engineering task with a measured
target — the catalogue stage must fit the `3.648–6.738 s` residual — not a scoring choice.**

## The rule I am imposing on myself

**No new specification document until the corrected ones have been checked against each
other.** I wrote the pipeline contract, the figure plan, three amendments and the acceleration
pre-declaration within about two hours, and an audit found two structural errors in them. I was
generating specification faster than it could be verified. That is a rate problem and it is
mine.
