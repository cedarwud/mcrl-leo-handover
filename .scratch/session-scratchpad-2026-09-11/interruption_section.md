
## Under the declared handover interruption

**Outcome: the declared interruption treatment cannot be expressed on this panel through the
mandated evaluator path, so no interruption-scored EE is reported for any arm.** The verification
that establishes this is a finding in its own right and is given first.

### 1. What selects the interruption — a treatment code, not a free constant

**Verified by reading primary source and by running code.** The interruption is not a value the
scorer chooses; it is a term of the sealed matrix treatment.

- `PhysicsSetting` carries an `interruption: InterruptionCode` field constrained to `{"off","on"}`
  ([matrix.py:24](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/matrix.py:24),
  [matrix.py:34-35](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/matrix.py:35)).
- The treatment letter fixes it
  ([matrix.py:79-90](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/matrix.py:90)):
  `"0" → ("0","0","off","ACM")`, `"T" → ("T","0","off","ACM")`, `"S" → ("0","f","off","ACM")`,
  **`"H" → ("0","0","on","ACM")`**, **`"SH" → ("0","f","on","ACM")`**.
- Exactly one place consumes the flag
  ([adapter.py:269-273](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/adapter.py:273)):
  `integrate_47_subintervals(..., interruption_enabled=setting.interruption == "on")`.

**Verified by running code** — enumerating the 31 declared settings: **10 carry
`interruption == "on"`** (`a-rH`, `a-rSH`, `a-γH`, `a-γSH`, `a′-rH`, `a′-rSH`, `a′-γH`, `a′-γSH`,
`bH`, `bSH`) and 21 carry `"off"`.

### 2. The condition that selects 0.062 s versus 0.142 s

**Verified by reading primary source**, quoted rather than paraphrased
([integration.py:78-89](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/integration.py:89)):

```python
for event in logged:
    if event.kind in {"initial_entry", "reentry"}:
        continue
    duration = (
        SAME_SATELLITE_INTERRUPTION_S
        if event.kind == "same_satellite_beam_change"
        else SATELLITE_CHANGE_INTERRUPTION_S
    )
```

So: initial entry and re-entry open no blackout at all; `same_satellite_beam_change` opens
**0.062 s**; **everything else that survives the skip** — in practice `satellite_change` — opens
**0.142 s**. The `event.kind` fed in is produced by `_interruption_events`
([run_v025_matrix_probe.py:743-758](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:758)),
which maps the physical ledger `beam_change → same_satellite_beam_change`,
`satellite_change → satellite_change`, and — worth recording — **`cell_rekey →
same_satellite_beam_change`**: a cell re-key is priced **0** by `Φ` but would open a 0.062 s
blackout. On this panel there are no re-keys, so that asymmetry is inert here.

Both constants are marked `VERIFY_SOURCE` at
[constants_v025.py:68-69](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/constants_v025.py:69)
("round-3 §2.16 conditional ADR-004 electronic handover proxy"). **I did not verify them against
3GPP TS 38.133 §6.1C.1.3.2** — that source is not reachable from this host — and no figure in this
report depends on them.

### 3. Which anchors on this panel carry the treatment: none, and the question is mis-shaped

**Verified by running code.** The treatment is a property of the **matrix cell**, not of the
anchor, so it does not vary across a panel. All 12 anchors here are scored in the single cell
**`a-r0`**, whose treatment letter is `"0"` and whose interruption code is therefore **`"off"`**.
There is no anchor on this panel that carries an interruption-on treatment, and none that could.

The same holds for the surrounding evidence base: BEAMCOUNT, CLEANPATH, CEILING2, COORDVALUE and
every figure in this report are `a-r0`. **The entire V0.25 development-panel record is
interruption-off**, which is a larger fact than this one job.

### 4. Can the mandated dense evaluator express it? No — by construction, not by omission

**Verified by running code.**

- `batch.evaluate_ar_tdm_catalogue` **has no interruption parameter**. Its full signature, read by
  `inspect.signature`, is `(arrays, selected_rows, *, field, chunk_size, rate_target_bps,
  circuit_power_per_active_chain_w, boundary_indices)`. It never receives an event ledger, so it
  cannot know which users handed over, let alone for how long.
- The profile built from its result hard-wires useful time to decoding time —
  `dict(decoding)` at
  [run_v025_matrix_probe.py:852](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:852)
  — so the one reported field that interruption is defined to move is set equal to the
  interruption-free field before any arm is scored.
- `StepEvaluator.evaluate_many` gates the dense path on the label being exactly `a-r0`:
  `if not missing or step.arrays is None or self.setting.label != "a-r0":` then
  `self.evaluate(config)`
  ([run_v025_matrix_probe.py:798-800](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:800)).
  Every interruption-on setting is a different label, so selecting one does not enable
  interruption on the dense path — it **leaves the dense path entirely**.

**Therefore, in this engine, "dense batch" and "interruption on" are mutually exclusive: there is
no code path that is both.**

### 5. It is runnable off the mandated path, and that still does not permit the comparison

**Verified by running code and by reading primary source.** `run_setting_for("a-rH")` returns a
sealed run setting, and `geometry_for` does materialise configurations on the frozen exact arrays
panel ([tapes.py:869-879](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/tapes.py:879)), so
`a-rH` would run here — through scalar `StepEvaluator.evaluate`. Two independent things block
using it for the requested comparison:

1. **The mandatory evaluator rule for this job forbids it.** Scalar `StepEvaluator.evaluate` is
   replaced by a raising stub with the counter asserted zero, in this job and in every job that
   produced the parity targets being compared against. Lifting that is an owner decision, not
   mine.
2. **It would not be a one-factor contrast.** The scalar path additionally merges
   `discontinuities_from_event_ledger` into the integration tape
   ([run_v025_matrix_probe.py:193-213](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:213),
   consumed at [adapter.py:269-271](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/adapter.py:271)),
   which the dense path never does. An `a-rH` scalar number would therefore differ from the
   `a-r0` dense numbers in this report by **two** changes at once — interruption on, and
   dense→scalar-with-discontinuities — and "with and without interruption side by side" would
   confound them. There is no scalar `a-r0` figure anywhere in this evidence base to difference
   that away against.

### 6. Stop

**No interruption-scored EE is reported for any arm.** No constant was substituted, no treatment
was approximated, no arm was re-scored under alternative scoring, and no winner was re-selected.
The question the coordinator posed — whether charging the physical cost of churn dissolves the
62.502712 → 17.257910 trade-off — **cannot be answered on this panel through the mandated
evaluator path.** None of the three pre-declared readings is reached, because the measurement that
would discriminate between them does not exist here.

Everything already reported above stands unchanged: it was all produced at `a-r0`, interruption
off, and nothing in this section alters a single figure in it.

### 7. One shape constraint that the declared code does fix, and one scale note that is not a measurement

**Verified by reading primary source — the effect would be numerator-only.** In
`integrate_trapezoidal`, joules accumulate outside the per-user loop as
`joules += 0.5 * (left.power_w + right.power_w) * duration`
([integration.py:129](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/integration.py:129))
and **no blackout term is ever subtracted from them**; only `bits` and `useful` carry
`- removed_bits` / `- removed_time`
([integration.py:151-152](/home/sat/mcrl-v025-c1c2suff-ws/src/mcrl/physics_v025/integration.py:152)).
Whatever the treatment would do, it cannot move the denominator. This is consistent with the
companion audit's finding that a handover consumes zero joules, and it means interruption is
indeed the only channel by which churn could cost anything here.

> **Derived, conditional, and explicitly not a measurement of the treatment.** The table below is
> arithmetic on the declared constants and the event mix already measured above. It reports how
> many seconds of blackout the declared `_blackouts` condition would open, as a fraction of the
> integration tape. It is **not** an interruption-scored EE and must not be quoted as one.
> Each arm has exactly one event per user per decision instant (`_physical_events` yields one
> event per user), so the interval-merging branch of `_blackouts` never fires and the seconds are
> additive.
>
> | Arm | beam changes | satellite changes | blackout (s) | of the 36,096 user-seconds of tape | measured EE, interruption off |
> |---|---:|---:|---:|---:|---:|
> | declared incumbent, held | 0 | 0 | 0.000 | 0.0000 % | 10.325892 |
> | search winner, budgeted vs base | 65 | 321 | 49.612 | 0.1374 % | 17.257910 |
> | declared rule, budgeted vs base | 80 | 314 | 49.548 | 0.1373 % | 17.200058 |
> | geometric base (`BASE`) | 60 | 329 | 50.438 | 0.1397 % | 11.027760 |
> | `RSS_MAX` | 475 | 714 | 130.838 | 0.3625 % | 41.621560 |
> | `CAP_050` search winner | 326 | 844 | 140.060 | 0.3880 % | 62.502712 |
> | strongest declared rule (S2\|A2) | 313 | 862 | 141.810 | 0.3929 % | 52.042303 |
>
> The declared windows are 0.062 s and 0.142 s against a `DECISION_INTERVAL_S` of 30.08 s, i.e.
> **0.2061 %** and **0.4721 %** of one decision interval. The widest spread in blackout fraction
> across the arms above is **0.2506 pp** (churniest arm minus the budgeted arm).
>
> **The assumption this note does not verify**, and the reason it is not a bound: bits removed are
> `∫ rate` over the blackout window, so the fraction of a user's bits removed equals the fraction
> of its time removed **only if the user's rate over the first 0.142 s equals its mean over the
> 30.08 s**. I did not inspect the rate profile over the first subinterval. A front-loaded rate
> profile would make the loss larger than the time fraction, and nothing here bounds how much
> larger. **The measurement is what would settle it; this note is not a substitute for it**, and
> in particular it does not license claiming that the ranking is unchanged.

### 8. What would have to be built to make this measurable

Either would make it a clean one-factor contrast; both are owner decisions, and I have costed
neither.

- **(a) Widen the dense path.** Give `evaluate_ar_tdm_catalogue` a per-user blackout argument,
  subtract the declared `_linear_integral` term over the blackout window, expose a dense
  `useful_time_s` distinct from `decoding_time_s`, and widen the `label != "a-r0"` gate at
  `run_v025_matrix_probe.py:798` to admit `a-rH`. Keeps the mandatory evaluator rule intact and
  keeps every existing parity target comparable. Changes engine code, so it needs a versioned
  successor.
- **(b) Run scalar `a-r0` and scalar `a-rH` over the same 12 anchors and the same seven
  configurations**, and report the interruption effect as the **within-scalar** difference, which
  differences the discontinuity mechanism away. Changes no engine code and is exact, but requires
  an explicit exemption from the mandatory evaluator rule for that pass, and the non-batch path
  is far more expensive per configuration.

Option (b) is the smaller change and the one I would propose first, precisely because it needs no
physics edit; but it cannot be started without the owner lifting the evaluator rule for it.
