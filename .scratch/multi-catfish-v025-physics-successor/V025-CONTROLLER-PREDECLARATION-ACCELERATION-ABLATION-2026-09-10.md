# Pre-declaration — the three-route ablation on the acceleration axis

**2026-09-10 11:40 UTC. Written before the measurement exists.** No sealed constant,
threshold, sign, seed, horizon, price, guard or acceptance rule is changed. This fixes what
will be measured and how it will be read, while no number exists to tune against.

---

## 1. Why the axis changes, and why that is not outcome selection

The claim under the current framing is that each route raises pooled EE **above the certified
unilateral fixed point**. The size of that prize is measured, on the declared full-buffer
numerator, and it is the ceiling for that claim regardless of how it is partitioned:

| measurement | value | verification |
|---|---|---|
| 8 anchors, STRICT, correctly paired, 1.66° | `+0.899421%` | **controller-verified**, `final-strict-one-sided-1.66.json`, `summary.pairings.correct.pooled_relative_ee_gain` = `0.008994207878970206` |
| 30 TRAIN dates, `MARGIN_Q`, date-paired | mean `+0.717%`, **date SD `0.751%`**, 95% t `[+0.436%, +0.997%]`, **4/30 non-positive** | **controller-verified**, `CEILING30-MARGIN-2026-09-10.md:34` |
| load/rate regime sweep, 11 points | never above `1%` | reported, not re-verified |

**The owner has stated that a ~1% result is not meaningful.** Partitioning ≤1% three ways
cannot produce three substantial contributions. That is arithmetic, and it was established
**before** this pre-declaration and independently of any route's sign.

**The rationale for changing axis is therefore outcome-independent**: the prize on the current
axis is too small for the claim, whichever way it comes out. It is not "the routes failed here
so try elsewhere"; the ceiling was measured, and no partition of it can meet the stated bar.

## 2. The axis, and that the contract already names it

**Contract v1 F2, controller-verified:** *"the coordinator's compute budget is **10 s wall** on
the declared worker count (the rest of the 30.08 s interval reserved for
sensing/transport/validation/commit); BASE (a⁰) is computed, validated and repaired **before**
the coordinator starts; the runner enforces the timer (cancel), not the solver; a miss executes
the validated a⁰."*

**Contract v1 C4, controller-verified:** *"matching S0 at lower compute is an **acceleration
claim, reported separately**."*

**The measured prize on this axis** (`ANYTIME-UNILATERAL-2026-09-10.md`, `SEALED` pooled curve,
controller-verified):

| budget | anytime EE (Mbit/J) | fraction of the first-improvement prize |
|---:|---:|---:|
| 10 s (the contract's coordinator budget) | **15.336646** | **42.91%** |
| 30.08 s (the whole anchor interval) | 25.846321 | 81.74% |
| convergence | **30.786890** | 100% |

**At the contract's own budget the headroom above the anytime incumbent is `+100.7%`**, two
orders of magnitude larger than the coordination band.

**The receipt's own warning, which this pre-declaration adopts:** the comparator is *"the
actual anytime incumbent at the same wall-clock budget, not the legal base configuration or a
convergence certificate time."* Any comparison against `BASE` on this axis is void.

## 3. What is to be measured

For every arm in the sealed inventory — `FULL`, `DROP_C1`, `DROP_C2`, `DROP_C3`,
`ALL_NEUTRAL_CONTROL` — at the contract's 10 s coordinator budget, on the same anchors, same
catalogue construction, same guard, same tie-break, same nominal information class (A2: no
realised fading), reporting on the **declared full-buffer numerator**:

1. **Recovered fraction.** Pooled EE attained, as a fraction of the certified fixed point's
   pooled EE on the same anchors.
2. **The contrasts.** `FULL - ALL_NEUTRAL_CONTROL`, and `FULL - DROP_Ci` for each route, on
   recovered fraction. **`ALL_NEUTRAL_CONTROL` is the reference. `BASE` is not, and is never
   relabelled as one.**
3. **The comparator.** The anytime incumbent's recovered fraction at the same 10 s budget,
   reported beside every arm.
4. **Deadline misses.** Per contract F2 a miss executes the validated `a⁰`; misses are a
   co-reported QoS field and their B and E enter the endpoint. Report the miss rate per arm.
5. **Physics evaluations consumed**, per arm, so "acceleration" has a denominator.

## 4. The reading, fixed now

- **The claim is about recovered fraction under budget, not about EE above the fixed point.**
  No figure from this measurement may be restated as a coordination gain, and no coordination
  figure may be restated as an acceleration gain.
- **`FULL > ALL_NEUTRAL_CONTROL` on recovered fraction is the primary contrast.** If it fails,
  the learned system does not beat neutral-source training on this axis either, and that is
  reported as the result.
- **`FULL > DROP_Ci` for each route is the per-route contrast.** Whatever ordering emerges
  among the three is reported as measured; **no ordering among routes is required**, because
  the relative importance of the routes is an empirical fact and not a design target.
- **A route whose contrast is zero or negative is reported as zero or negative.** One or two
  small contributors is an outcome, not a failure to be repaired by adjustment.
- **If the anytime incumbent at the same budget beats every learned arm, that is the result**,
  and the acceleration claim fails with it.
- **Three routes are not assumed necessary here.** If a single learned proposer recovers as
  much as `FULL`, that is a finding about the decomposition and must be reported, not
  suppressed.

## 5. What this pre-declaration does not do

- It does not authorise training, a panel, contract v2, or a corpus substitution.
- It does not claim the acceleration axis will succeed. **Nothing on this axis has been
  measured for any learned arm.**
- It does not retract the coordination result. `+0.899%` / `+0.717%` stand as measured, with
  their interval and their 4/30 non-positive dates, and remain reportable as a mechanism-level
  finding.
- It does not move any pass mark. The owner's bar — substantial, not ~1% — is unchanged; what
  changes is which quantity it is applied to, and why.
