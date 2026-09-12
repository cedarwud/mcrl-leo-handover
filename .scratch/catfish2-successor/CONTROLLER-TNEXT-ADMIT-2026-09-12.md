# Controller adjudication — `T_NEXT` is ADMITTED to the k = 8 portfolio, with its narrative corrected

Date 2026-09-12. Read against Amendment 15 §2A and §5. Every figure re-derived by me from
`results-lane-n/P0-TNEXT.json` and `A-REPR-TNEXT.json` in the Lane-N worktree (`43555442`).

## 1. Both gates pass

| gate | value | line | verdict |
|---|---|---|---|
| distinctness `disagreement(T_NEXT, T0)` | **0.5964** (21,600 decisions, 24 ep, t = 1…9) | ≥ 0.25 | **PASS**, 2.4 × the line |
| `A_repr` (held-out top-1) | **0.5714** | ≥ 0.50 | **PASS**, +0.0714 |

Zero legal violations. No collapse: 28/28 actions used, entropy 1.874 nats, modal share 0.326. Episode-cluster
bootstrap CI95 [0.5228, 0.6231] with **100 % of draws above 0.50** — against `T_DELTA`'s 55.35 %. Fallback is
**exactly** the final step (2,400/24,000 = 10.00 %, `no_legal_action = 0`), as §2A requires.

**`T_NEXT` is ADMITTED to the k = 8 / k = 9 portfolio**, subject to Lane M's MULTI-D3 mechanism being ready. It is the
first candidate in this portfolio to clear both gates.

## 2. The finding that changes the narrative: term 1 is inert in this physics

**Criterion activation is 0 of 21,600.** `legal_actions_below_cell_horizon_at_t_plus_1 = 0` over 502,215 legal-action
evaluations; the minimum `t+1` user elevation is 7.71°, and one 30.08 s step moves elevation by a mean 11.2° — never
across the 0° threshold from a D2-offered high-elevation satellite.

So over this collection the frozen lexicographic rule

    ( same_physical_association_legal_or_visible_at_t+1,  ← constant True
      nominal_next_step_link_gain_for_that_association,
      current_T0_score,
      -current_action_index )

**executes as `argmax(next-step nominal gain, T0 score, −index)`.**

**This is not a deviation and nothing was tuned** — the definition ran exactly as frozen, and §5 leaves no authorised
constant to move. It is a measurement of the physics: **in v023, association persistence over one step is not a
live discriminator.** Re-specifying the source now, having seen that, would be precisely the post-outcome redesign the
freeze exists to prevent.

**What must change is the claim, not the source.** Amendment 15 §2A's narrative was "temporal foresight /
service-persistence Catfish". **The persistence half is dead by measurement and must be dropped.** What survives is
genuine and is still on the declared information axis: the rule reads `t+1` geometry, which T0 cannot see. The
narrative is therefore **one-step-ahead link-gain foresight**, and nothing more. Writing "service-persistence" into
the paper would be claiming a mechanism this project has measured to be inert.

**The closest existing relative, and why this is not it.** `T_NEXT` as executed is `MAX_NOMINAL_GAIN` evaluated at
`t+1` instead of `t`. Stage 0 measured `MAX_NOMINAL_GAIN` (the `c = 0` link endpoint) at disagreement **0.1982**
against T0. Moving the same gain criterion one step into the future takes disagreement to **0.5964** — **three times
higher**, and past a gate the `t` version fails. That is the cleanest available evidence that the temporal axis, not
the gain criterion, is what makes this source distinct.

## 3. Two implementation readings, both ratified

1. **Users are held at `t`; only the ephemeris advances.** A `t+1` user position does not exist without consuming the
   mobility RNG (`RandomWanderingUsers.step(rng)`), which §2A forbids absolutely. Advancing only the satellite through
   the existing side-effect-free `ScenarioDriver.satellite_ecef_at(+1)` (≈ 220 km/step) is the only reading that
   honours the side-effect-free requirement. **Ratified.** It also means the lookahead is *conservative*: it sees
   satellite motion, the dominant term, and not user motion.
2. **"Legal or visible" is evaluated on the visible disjunct** — cell reachability alone, at the project's existing
   0° thresholds, because the mask's other two terms need latched D2/dwell state the lookahead may not advance.
   **Ratified**, no new constant. Note this makes term 1's inertness *more* robust, not less: the disjunct chosen is
   the permissive one, and it still never fired.

Both were flagged by the lane rather than silently taken. The bit-identity proof over environment state and every
generator is the receipt that the side-effect-free requirement holds.

## 4. What `A_repr = 0.5714` does and does not establish

Recorded honestly, because the lane volunteered both numbers:

- The clone is **more concentrated than the teacher**: entropy 1.354 vs 1.871, modal share 0.524 vs 0.390, 26 of 28
  actions. It has not collapsed, but it is not a faithful copy.
- **Clone top-1 is 0.5054 on states where `T_NEXT` differs from T0, against 0.6804 where they agree.** So roughly
  **half the source's distinctive information survives the 113-dim bottleneck** — the half that matters for a
  catfish, since the agreeing half is information T0 already supplies.
- Only **4 test episode clusters**. The interval is indicative, not the T0 screen's evidence.
- Per-step top-1 decays late in the episode: 0.61 at t = 1 down to 0.41 / 0.46 at t = 8 / 9.

Set against the two teachers this screen has already killed, the contrast is real: `T_SEQ` 0.13–0.15, `T_DELTA` a
degenerate 0.51 reached by shedding 18 % of the bits, `T_NEXT` +0.0714 above the line with 100 % of draws above it and
no throughput-shedding mechanism. But `A_repr` is an *admission* gate, not evidence of learner value. **Nothing here
predicts the k = 8 outcome, and the drop-one criterion may not be replaced by it** (Amendment 15 §7).

## 5. Context, explicitly not a value claim

`T_NEXT` standalone: served 0.99538, pooled EE 1.0311e8 = **0.876 × T0**. Amendment 15 §7 states that `Ti-only` is
**not required to beat `T0-only`**; a source may be a useful specialist without being the best standalone controller.
This is exactly that case and it is recorded so it cannot later be mistaken for a failure — or for a promise.

## 6. Disposition

`T_NEXT` advances to the k = 8 five-arm pairwise matrix once Lane M's generic MULTI-D3 mechanism and its matched
two-proposal null pass their twelve required tests. `delta_DEV` stays **+1.0 %**, frozen before any k = 8 result
exists. Lane Q's `T_TAIL` P0 is running on `sat`; Lane N used **zero** `sat` workers, so all capacity is Lane Q's.
Formal S1 remains PARKED.

---

## 7. Denominator reconciliation (added 2026-09-12, after the lane's follow-up)

§2 above cites **502,215** legal-action evaluations; the lane's report §4c cites **569,415** for a same-named
quantity. **Both are correct and the difference is exact**, not a rounding artefact:

- `source_diagnostics.persist_true` accumulates over every step that runs a lookahead, `t = 0…8` (`t = 9` is the T0
  fallback and runs none) → **569,415**;
- `criterion_activation` accumulates only over the scored `t ≥ 1` steps → **502,215**;
- the difference is precisely the `t = 0` block: **569,415 − 67,200 = 502,215**, and `67,200 = 24 episodes × 100
  users × 28 actions` exactly — the initial state, where the full action set is legal. Verified by me.

**`persists = False` is 0 on both denominators**, so the inertness finding of §2 is unchanged on either accounting.
The lane committed the denominator alongside each figure (`25448632`) rather than leaving two committed documents
appearing to disagree. No measurement, number or finding changed.

## 8. Sharpening of the `MAX_NOMINAL_GAIN` comparison (from the lane, verified as reasoning)

§2 argues that moving the same gain criterion from `t` to `t+1` raises disagreement with T0 from 0.1982 to 0.5964.
The lane adds a point that strengthens it: Stage 0's 0.1982 arm is `argmax_a γ_a` over **block 2**, which carries
stochastic fading and previous-step interference, whereas the `t+1` quantity is the deterministic link budget
`G_T(θ)·H` with **both stochastic terms absent**.

So the three-fold jump is **not** an artefact of a noisier signal producing more disagreement — the `t+1` quantity is
the *cleaner* of the two and still triples the disagreement. That closes the most obvious alternative explanation for
§2's claim that the temporal axis, rather than the gain criterion, is what makes `T_NEXT` distinct.
