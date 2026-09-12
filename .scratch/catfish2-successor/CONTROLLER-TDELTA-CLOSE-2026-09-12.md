# Controller adjudication — `T_DELTA` fails the §7d admission and does not join the portfolio

Date 2026-09-12. Read against Amendment 15 §5 and the corrected B0 contract. Every figure re-derived by me from
`results/DENOMINATOR-FROZEN.json` and `results/R-REPR.json` in the B0 worktree.

## 1. The denominators were frozen correctly, and the pre-registered failure branch was not entered

`den_A = 123,394,821.99 − 112,695,866.84 = 10,698,955.15`; `den_B = 121,480,141.60 − 110,451,525.97 = 11,028,615.63`.
Both positive, so both halves are identifiable and the pre-declared non-identifiable branch does not apply. The freeze
ran as a separate one-shot guarded step that aborts if any `CLOSED-*.json` exists, and none did. The corrected contract
was applied before launch: T0-headroom survives only as `T0_RULE_GAP_CONTEXT`, and the bootstrap now resamples clone,
teacher and rule together.

## 2. My pre-registered herding concern was wrong, and that matters

I registered, before J existed, that `T_DELTA` is a *unilateral* best response with 79 % of users moving, and that
applying it simultaneously is the construction the oracle cells measured as throughput-degenerate. **It did not
happen.**

J: pooled EE **122,446,795**, served **1.00000**, bits ratio **1.0261**, joules 0.9350, 59.19 lit beams (rule 63.38,
T0 56.82). J **beats T0** (117,664,216) by **+4.06 %**. Its real costs are the rate tail (p10 0.713 ×) and churn
(`H_inter + H_intra` 0.778 against T0's 0.642) — not herding. On its own trajectory: disagreement 0.78925, QoS-invalid
0.06757, **zero** outage choices.

**`T_DELTA` is a better teacher than T0.** The concern I raised was the right one to raise and the measurement
answered it against me. Recorded as such.

## 3. The admission gate fails, on two independent grounds

### 3a. Non-degeneracy — decisive

| clone | `R_repr` A / B | bits ratio vs rule | lit beams |
|---|---|---|---|
| BC | 0.1297 / 0.1182 | **0.9043** | 56.51 |
| SOFT τ=0.3 | **0.5061 / 0.5905** | **0.8168** | **48.87** |
| *teacher J* | — | *1.0261* | *59.19* |
| *rule `A m=2dB`* | — | *1.0000* | *63.38* |

The inherited non-degeneracy line is **bits ratio ≥ 0.95** — the T_SEQ screen reported 0.951–0.979 as its evidence of
non-degeneracy, and the same 0.95 is the Amendment 4 / 10 floor. **Neither clone meets it, and the only clone that
reaches `R_repr ≥ 0.5` misses it by a wide margin.**

The mechanism matters more than the number. `SOFT τ=0.3` reaches its EE by **not sending 18 % of the bits and not
spending 22 % of the joules**, lighting 48.87 beams against the rule's 63.38. **The teacher does the opposite**: J
sends **2.6 % more** bits than the rule while lighting 59.19 beams. The clone did not learn the teacher's policy; it
found a *different, throughput-shedding* route to a similar EE ratio. `R_repr` is an EE ratio and cannot see this by
construction — the non-degeneracy check exists for exactly this case, and it fired.

### 3b. Even ignoring 3a, the point estimate is not the evidence this gate intends

`DEVVAL-A` clears the line by **0.0061** on **12 episodes**, with a bootstrap interval 0.406–0.626 and only
**55.35 %** of resamples ≥ 0.5. The T0 screen produced **0.930–1.052 with 100 %** of resamples. I warned when
ratifying the half-split that a marginal value on 12 episodes is not the evidence the T0 screen produced; this is that
case.

### 3c. The recorded confound does not explain the failure

The lane recorded, without proposing a fix, that the corpus was collected on the **teacher's own** trajectory and that
J's state distribution differs from T0's. That is a real confound, but it cannot be what fails `T_DELTA`: **the T0
screen used the same protocol** and scored 0.930–1.052. For the same reason the DEVVAL set is not the cause — **T0
itself scores 0.9488 on this very set**.

## 4. Ruling

**`T_DELTA` fails the §7d admission. Under Amendment 15 §5 it joins the k = 8 / k = 9 portfolio if and only if its
frozen B0 closed-loop contract passes; it does not, so it does not join.** No RL training, no `D3-T_DELTA` arm, no
integration work. No retry with a different clone family, temperature, corpus policy or episode split — the protocol
was frozen before the first fit and executed once each, and repairing the instrument after seeing the result is
exactly what the freeze forbids.

## 5. What this is worth, stated plainly

This is the **second privileged teacher** killed by the same screen. `T_SEQ` scored `R_repr` 0.13–0.15; `T_DELTA`
reaches 0.51–0.59 only via a clone that sheds throughput. The publishable finding is sharp and it is not a
disappointment:

> A counterfactual system-externality teacher is genuinely better than the deployed rule and better than T0 as a
> teacher — J beats T0 by 4.06 % at 100 % service — **and a 113-dim deployable student still cannot carry its
> information.** The advantage is counterfactual, not a feature of the observation.

Diagnosed at the cost of one no-training screen, before a single learner episode was spent. That is what §7d is for,
and it has now paid for itself twice.

## 6. Consequences

The portfolio now rests on **`T_NEXT`** and **`T_TAIL`**. `T_H` stays closed, `T_DELTA` closes, and Stage 0 remains
zero. If both remaining candidates fail, Amendment 15 §9 applies without exception: the search stops, nothing is
relaxed or swept, no fourth family is invented, the single-source S1 is **not** launched under a "Multi-Catfish"
framing, and the evidence returns to the owner.

`TDELTA-CANARY-PREP` loses its purpose — `D3-T_DELTA` will never run. Its generic teacher-identity wiring and its
cost-profiling method are handed to Lane M rather than discarded, and the lane then stops. Formal S1 remains PARKED
and untouched.
