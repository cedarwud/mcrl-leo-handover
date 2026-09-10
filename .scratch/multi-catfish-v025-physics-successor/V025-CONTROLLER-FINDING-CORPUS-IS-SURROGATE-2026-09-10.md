# Controller finding — the training corpus does not carry the declared targets

**2026-09-10 · `DIAGNOSTIC_NOT_CLAIM` · no sealed artefact, constant, threshold, sign, seed,
horizon, price, guard, acceptance rule, manifest or contract was changed by this record.**

**All 176,223 checked-in source rows were built by an unconditional compute stand-in whose
C1 and C2 labels are bounded `kappa*tanh(log ratio)` surrogates, not the declared
`c1_difference_surplus` / `c2_persistence_forecast`. The declared path is unreachable as
sealed. Every statement about C1/C2 learnability on record was measured against the
surrogate.**

---

## 1. Verified by the controller, reading the code directly

These were confirmed line by line in `/home/sat/mcrl-v025-pilot-ws` by the controller, not
taken from a worker report.

| Fact | Citation |
|---|---|
| The fallback flag is a module-level constant, not a data predicate | `scripts/run_v025_pilot_c3.py:89` — `PILOT_PRIMITIVE_SOURCE_FALLBACK = True` |
| It is dispatched as the **first statement** of the only row-building entry point | `_build_anchor_rows` at `:525`, dispatch at `:537` |
| The stand-in it dispatches to | `_build_anchor_rows_primitive` at `:355`, self-described in its docstring as "Schema-complete provider-primitive fallback for **bounded pilot compute**" (`:359`) |
| C1 label written by the stand-in | `c1_label_bits = kappa * tanh(log(max(ratio, 1e-30)))`, computed ~`:409`, written ~`:460` |
| C2 label written by the stand-in | `c2_label_bits = kappa * SUM_offsets tanh(log(future_ratio))`, `-1` per lost offset, computed ~`:414-427`, written ~`:462` |
| The declared C1 target | `src/mcrl/physics_v025/targets.py:154-173` — `core = (cand.bits - def.bits) - eta*(cand.joules - def.joules)`; label `= core/kappa + Phi` |
| `targets.py` contains **no** `tanh` | grep over the whole file: zero hits |
| `c1_difference_surplus` is **never imported** by the pilot script | `run_v025_pilot_c3.py:36` imports only `c2_persistence_forecast` and `matched_anchor_decomposition` |
| `c2_persistence_forecast` is called only at `:601`, i.e. **after** the `:537` dispatch, on the branch that cannot execute | `:601` |

The two objects are not variants of one another:

- the declared target is **unbounded**, is a difference of `B - eta*E` at the whole-network
  level, and carries `Phi` inside the label;
- the stand-in's label is **bounded** by `kappa`, is a monotone squash of a **per-user gain
  ratio**, contains **no energy term at all**, and stores `Phi` in a separate field.

## 2. Reported by workers, attributed, not independently re-measured here

**`TARGET-DESIGN-2026-09-10.md` (selector workspace), §0.1 and Q1/Q1b.**

- 100% of the 176,223 rows carry the surrogate; the 180 *coalition* rows are genuine but
  all `|A| = 2`.
- Learnability, 16-D linear model: surrogate label **R^2 = 0.598**, within-group ordering
  **0.801**. Production target, held out: **R^2 = 0.151**, ordering **0.650**.
- Variance shares of the declared C1 target: `own` 0.187, `ext` 0.375, `energy` 0.418,
  `Phi` 0.021. The pre-decision part carries **2.1%**.
- Between-anchor share of the cross-user externality: **0.0109** — 98.9% of its variance is
  *within* an anchor, so it does not cancel in a ranking and cannot be dropped.
- **Q1b, the structural fact.** With a *perfect* C1 head, median over 24 anchors: 82 of 100
  users have a strictly positive best unilateral surplus; their sum is **200.4**; the best
  single-user move is **8.02** — a **20.5x** ratio. At `|A| = 100` the exact singleton sum
  is **+480.113**, the exact residual **-440.079**, the exact final value **+40.034**. The
  quantity being ranked is the small difference of two large terms.

**`EXACT-ROW-PATH-COST-2026-09-10.md`.** The declared path is executable and costs
**49.03 s/anchor**, **57.79x** the stand-in, and **29.42 serial worker-hours** for the full
panel at 20 anchors x 12 seeds x 9 arm-owned catalogues with no cross-arm reuse. Verdict
`AFFORDABLE`.

**`PREFLIGHTDATA` (interim, 2026-09-10, coverage workspace).** Independently reproduced the
surrogate finding from the shipped bytes — each path stamps a distinct
`forecast_method_sha256`, and 176,223 of 176,223 rows carry the fallback digest — and added:

- `missing_incumbent` is **also** constant 0.0 on every row: a **second** dead slot, not
  previously on the list, alongside the known `off_axis_angle`;
- the 16-column design matrix has **rank 14**, smallest singular value exactly 0;
- slots 4 and 12 are **exact indicator functions** of slots 3 and 11 — effective input
  dimension is **12**, and any per-slot ablation over those pairs is arbitrary;
- slot 1 (`nominal_required_power_over_cap`) carries a **1e6 sentinel on 10.21%** of rows
  (the null-action rows), giving that slot SD 302,837 against O(1) elsewhere;
- `outage` agrees with `null_action` on all 176,223 rows in both directions — it never
  encodes a real PHY service failure;
- the selected coalition is chosen by **lexicographic `configuration_id`**, not by the
  `-(C1+C3)` factor score, over an **unfiltered** candidate set;
- measured cost on one 992-row anchor: stand-in **4.79 s**, declared path **632.83 s**
  (**132x**).

**The two cost measurements disagree (57.79x vs 132x) and are left unreconciled here.**
They were taken at different row densities and anchors and neither has been re-run.

## 3. Detectability — the part that matters for planning

Of the thirteen defects PREFLIGHTDATA enumerated, **one** (the 1e6 sentinel) could have
announced itself in a training curve, and then only as unexplained instability rather than
as a diagnosis. **Twelve are silent.** Three of them push the wrong way: a bounded,
saturating surrogate of a single ratio is **strictly easier to fit** than the declared
unbounded surplus, and ~31% of the C2 surrogate sits on one constant floor. A healthy C1/C2
training curve on this corpus is therefore **not weak evidence** that the routes learned the
declared quantities; it is **no evidence**.

## 4. Accountability

`TARGET-DESIGN-2026-09-10.md` recorded §0.1 — the same finding, with the same citations —
**earlier the same day**, and its own text says it "should be fixed regardless of the
verdict, and is not sealed". The controller read that report, recorded the `TARGET_REFORMULATE`
verdict, and **did not act on §0.1**. It surfaced again only because an unrelated pre-flight
census re-derived it from the shipped bytes.

The failure mode is not "the finding was missing". It is **a finding that was present,
correct, and filed** while the controller went on planning a panel that would have consumed
those rows. This is the same shape as the `MARGIN_Q` case, where the rule that would have
caught it had already been written down on 2026-09-08 and was not applied.

## 5. Owed repairs register — nothing here is authorised by this record

1. `PILOT_PRIMITIVE_SOURCE_FALLBACK` is `True` unconditionally; the declared path at
   `run_v025_pilot_c3.py:544+` never runs. Changing it is a **declared change**, recorded as
   such, with a rationale independent of what it does to any route's sign — not a bug fix.
2. `off_axis_angle` hard-coded 0.0 at both row paths; **no elevation feature exists** in the
   16-slot schema.
3. `missing_incumbent` constant 0.0.
4. Slots 4/12 duplicate slots 3/11 exactly; design matrix rank 14 of 16.
5. Slot 1 sentinel 1e6 on 10.21% of rows.
6. `outage` is an alias of `null_action`.
7. Coalition selection by lexicographic id over an unfiltered candidate set.
8. `Phi` computed without `cell_rekeyed_users` on the stand-in path — latent on this corpus,
   activates on tapes built from boundary candidates.
9. `StepEvaluator.evaluate` vs `evaluate_many` disagree on the same `Configuration`
   (-29.45 to +54.08 kappa-units of network bits), and the stand-in takes its **reference**
   through `evaluate` (`:396`) while the catalogue goes through `evaluate_many`. Under
   investigation as `EVALPATH`; **no conclusion yet**.

## 6. What this does and does not say

It says: no claim about C1 or C2 learnability currently rests on the declared estimand.
It says: the declared path exists, executes, and has a measured price.

It does **not** say the declared targets are unlearnable — `R^2 = 0.151` held out is a
measurement on 24 anchors with one linear model, not a ceiling.
It does **not** say the stand-in was illegitimate when it was written; it says the flag that
made it unconditional was never revisited.
It does **not** authorise flipping that flag, rebuilding the corpus, or funding the panel.
