# Fresh-context red-team review — C3-S closed-loop kill screen v1 (Claude Opus 5, 2026-09-08)

Scope: receipts under `runs/c3s-20260908-r1/`, `c3s_policy.py`, `src/mcrl/env/{step,link_budget,service,dwell}.py`.
Read-only; no sealed artifact touched; no TEST split opened. All numbers below are recomputed by me from the
unit receipts unless attributed.

## 0. What is clean (do not spend effort here)

- **Arithmetic reconciles exactly.** Summing the 360 per-step `bits_hex`/`energy_j_hex` rows per arm reproduces
  `pooled_exact` bit-for-bit as exact rationals for all three arms (bits, joules, served). No aggregation slip.
- **Matching is real.** `initial_state_sha256` identical across the three arms in all 12 units.
  corr(BASE step energy, FULL step energy) over the 360 matched slots = **0.9922** — the arms stay in phase,
  so hypothesis (e) (trajectory divergence destroying comparability) is not supported.
- **Not an outlier.** Leave-one-unit-out pooled dEE spans 2.789–2.959 %; leave-one-world-out 2.727–3.036 %.
  90.3 % of the 360 matched step slots are positive. This is not noise and not one world.
- **The project's own historical EE failure mode is excluded.** `energy_efficiency.py` gate G-8 (the old 3.9×
  headline that was a 33.7 % coverage difference) cannot apply: served is identical (§1.1).

The result is real *inside this simulator under this estimand*. Everything below is about what it means.

## 1. Artifact hypotheses, ranked

| # | Hypothesis | P(overturns the claim) |
|---|---|---|
| H1 | Unpriced handover + stale-anchor renewal: the endpoint charges zero joules for churn, and the recurrence freezes each user's received transmit-gain at segment start, so re-anchoring is a free option BASE was trained not to take | **0.45** |
| H2 | No non-learned comparator: C3-S is "use nominal physics to correct the learner", and a nominal-physics optimiser seeded from a trivial baseline may match it | **0.45** |
| H3 | "Set-level coordination" is largely mis-described (singleton-evacuation aliases; LITE ≡ FULL) | 0.05 for the number, **0.85 that the framing must change** |
| H4 | Service guard is vacuous by construction, so the kill rule is a bare one-sided EE inequality with no effect size | 0.15 |
| H5 | Denominator is ≈ 6.5 W × lit-beam count with no bus/payload floor | 0.10 |
| H6 | η_ref mis-pricing (124.08 M vs realised 117.42 M) | 0.08 |
| H7 | Joule-weighted step aggregation × strong dwell-phase heterogeneity × T = 30 | 0.10 |
| H8 | Four world clusters, dependent contrasts | 0.05 |
| H9 | Nominal-model privilege on the bits term | 0.15 |
| H10 | Exact-fraction / aggregation slip | **0.01** (checked, clean) |

### H1 — Unpriced handover and stale-anchor renewal *(the main finding; absent from all eight prior documents)*

**Mechanism.** Two code facts combine.

1. `recurrence_power_w` (`link_budget.py:379`) gives `p(t) = p⁰·G^T(θ(τ))/G^T(θ(t))`, and the wanted signal
   (`step.py:946-957`) is `link_power[u] · transmit_gain[u,col] · path · fade · G^R = p⁰·G^T(θ(τ))·path·fade·G^R`.
   **The transmit-antenna factor of a user's received power is frozen at its segment-start value.** A user cannot
   benefit from geometry improving under it; only a *handover* re-anchors τ ← t.
2. Any association change resets the segment (`step.py:829-861`, `segment.continues(...)` false → `start_gain =
   transmit_gain[uid]`), and `HANDOVER_COST` (Φ₁ = 0.5 intra, Φ₂ = 1.0 inter, `action_contract.py:408-418`) exists
   **only** in the training reward `r2_handover` (`step.py:1101`). It appears nowhere in `system_power_w`. Grep of
   `ee_axis_evaluation.py` / `link_budget.py` for `HANDOVER_COST`: zero hits.

So the EE endpoint and the reward the heads were trained against **disagree about the price of a handover**, and
C3-S optimises the endpoint directly. BASE is not merely a weak argmax — it is optimising a different objective.

**Receipt evidence (the fingerprint).** `DwellConfig.steps = 4` is frozen (`dwell.py:41-90`). Pooling by
within-dwell phase `t mod 4`:

| phase | BASE joules share | BASE mean P (W) | implied lit beams | FULL dEE % | dBits % | dJ % | ΔP (W) | Δbeams |
|---|---|---|---|---|---|---|---|---|
| 0 (boundary) | 38.7 % | 377.8 | 56–60 | **+1.348** | +0.936 | −0.406 | −1.53 | −0.23 |
| 1 | 27.6 % | 270.1 | 40–43 | +1.748 | +0.928 | −0.806 | −2.18 | −0.33 |
| 2 | 18.4 % | 205.4 | 30–33 | +3.921 | +2.607 | −1.265 | −2.60 | −0.40 |
| 3 (oldest) | 15.3 % | 170.8 | 25–27 | **+9.262** | +4.791 | −4.092 | −6.99 | **−1.06** |

The advantage is **monotone in how long BASE has held its associations**, in both the bits and the joules term —
exactly what "renewal is free and BASE is penalised for it" predicts, and *not* what a load-balancing or
congestion story predicts. (Per-beam cost is tightly bounded: `link_budget.py:735-753` records the largest
in-segment loss as **0.718 dB** of the 3.010 dB budget, so p ∈ [0.825, 0.973] W and per-beam total ∈
[6.27, 6.78] W. Hence "ΔP → Δbeams" above is safe to ±4 %.)

**Confirm/refute.** Refuted if a re-run shows FULL/LITE make no more physical handovers than BASE, or if the
gain survives after charging handovers in the denominator. Confirmed if handover count per step is materially
above BASE and the excess tracks the phase profile above.

**Cheap test (T1, ≈1.6 worker-h).** Re-run BASE + LITE on a 4-unit sub-panel (1 world × 3 lineages + 1) with
per-step logging of: `HandoverClass` counts, active beam count, mean segment age, mean `p_{s,v}`, and the number
of users whose committed action differs from the step's BASE proposal. Everything needed is already computed in
`_resolve_physics`; this is a logging change, not new physics. **None of it is in the current receipts** — the
receipts cannot answer "how many users moved" or "how many handovers happened", which is the single largest
instrumentation gap in the run.

### H2 — There is no non-learned comparator; "C3" may be "the simulator correcting the learner"

The coordinator deviated at **360/360** decisions in both arms. Because BASE wins lexicographic ties, that means
a strictly better nominal candidate existed at every single step, out of ~3 218 (FULL) / ~917 (LITE). The learned
heads contribute only the seed `b_t` and, for LITE, a top-2 slot ranking — LITE's unilateral catalogue is exactly
**100.0 candidates per decision** (one per user, `profile_counts`), i.e. one runner-up each. The claim
"a third Catfish improves EE" is not separable from "a one-step nominal-physics optimiser beats a learned
argmax", which is a much weaker and much less novel claim.

Astra's global view already concedes that C1 "已把 unilateral 的全部 network-energy delta 納入", yet S0-U
(unilateral only, no evacuation) captured +1.523 % of S0's +1.813 %. Both cannot be right.

**Cheap test (T3, ≈2 worker-h).** Same panel, four arms: {greedy non-learned association (e.g. max current G^T /
nearest legal cell), greedy + C3-S(lite), Q12 BASE, Q12 + C3-S(lite)}. Report the 2×2. If greedy + C3-S ≈ Q12 +
C3-S, the coordinator's gain is not a *third* contribution on top of C1/C2 — it substitutes for them, and the
"three positive contributions" story collapses at the same time it appears to be completed.

**Cheap test (T2, ≈0.3 worker-h, decisive and nearly free).** A `RANDOM-RENEW` arm: each step pick a uniformly
random legal non-BASE unilateral edit, *no nominal scoring at all*. It costs BASE-arm compute (~1.9 s/decision).
If churn alone captures a large fraction of +2.9 %, H1 is confirmed and the optimiser is decoration. This is the
highest information-per-CPU-second test available and I recommend it first.

### H3 — "Set-level coordinator" is mostly mis-described

At step 0 all three arms share an identical state, FULL's catalogue (4 329–4 581) is a strict superset of LITE's
(1 729–1 981), and FULL scans ~2 400 unilateral candidates against LITE's 100. **In all 12/12 units the nominal
objective F = B̂ − η_ref·Ê of the two selected candidates is exactly equal (difference 0.0 in binary64)** — including
the 7 units where the reported IDs differ in *kind* (`U:56:7` vs `J:62267:65->45564:65`). Exact rational equality
across 12 independent units is only possible if the action vectors are identical: these are **singleton-evacuation
aliases**, which `_evacuation_skeletons` (`c3s_policy.py:308`) admits by design with no minimum-origin-size filter.

Consequences the paper must absorb:

- FULL's extra ~2 400 unilateral candidates per decision buy **zero** realised EE. LITE (917 candidates,
  ~3.5× cheaper) is marginally *better*: +2.9218 % vs +2.8832 %.
- The reported catalogue split (FULL 194 U / 166 J; LITE 55 U / 305 J) is a **tie-break labelling artefact**, not a
  measurement of coordination. In FULL the unilateral alias always outranks a singleton evacuation, so FULL's
  166 "J" selections are genuine ≥2-user moves; in LITE many "J" are singletons. The two arms' 51.9 % ID agreement
  understates their physical agreement badly (12/12 identical actions at step 0).
- The one honest set-level number available — FULL's 166/360 genuinely multi-user selections — is not reported
  anywhere, and cannot be recovered from LITE at all.

This does not move the +2.9 %. It does mean the sentence "model-based **set-level** coordinator" is not supported
by the receipt in the strength it implies. Test: T1's "users changed per decision" counter settles it exactly.

### H4 — The service guard is vacuous by construction

**All 29 unserved user-steps in every arm occur at step index 0.** From step 1 to step 29, service is 100/100 in
every unit in all three arms. Served is identical at every level: pooled 35 971, per world 8 982 / 8 998 / 8 991 /
9 000, per lineage 11 989 / 11 990 / 11 992, and per *step* (0 mismatches in 360). Nominal served − realised served
= 0 in 720/720 decisions.

This is structural, not lucky. A fresh segment has p = p⁰ = 0.825 W < p_max = 1.65 W, so **any association change
is always feasible** — the coordinator's only tool is one that guarantees service. `link_budget.py:748` records
outage 0 of 12 000 decision steps. So `s_arm ≥ s_BASE − 0.001` can never bind against a coordinator that moves
users, the "36 fewer served user-steps" allowance is unreachable, and the kill rule reduces to a bare one-sided
`η_arm > η_BASE` with no minimum effect size. Gemini's fresh-root review reached the served-count half of this;
the *reason* (p⁰ feasibility) and the "all 29 at step 0" localisation are new. Service is invariant, not protected.

### H5 — The denominator is a lit-beam counter

`system_power_w = Σ_beams [6.5264·√p + 0.338] + 0.200·N_active_sat`, with no bus/payload constant and a
zero-user beam costing exactly nothing. Mean BASE power is 260.5 W ≈ 40 lit beams; mean FULL 257.3 W. **The entire
pooled energy advantage is 0.50 fewer lit beams per step out of ~40.** I tested sensitivity to an unmodelled
constant payload directly on the receipts:

| P_bus per sat (×4) | 0 W | 10 W | 25 W | 50 W | 100 W | 200 W | 400 W |
|---|---|---|---|---|---|---|---|
| FULL dEE % | 2.883 | 2.712 | 2.527 | 2.326 | 2.108 | 1.919 | 1.786 |

Bounded, because 56.2 % of the gain is on the bits side (log decomposition: bits 56.2 %, energy 43.8 %). Report the
number, do not treat it as fatal. Cost: zero, already done.

### H6 — η_ref pricing

η_ref = 124 075 740.547 is **+5.67 % above this panel's realised η_BASE (117 419 389.19)** and +2.71 % above the
achieved η_FULL. Under Dinkelbach the pooled-EE-correct shadow price is the *achieved* ratio, so the frozen price
is **energy-averse** relative to optimal — the direction is conservative, which is why I rate this low. But it is
an unvalidated scalar imported from a panel whose BASE *was* 124.08 M, and the arithmetic of the mismatch appears
in none of the eight prior documents. The adjudication granted only a cached-candidate choice-stability rescoring
at 4/5, 1, 6/5 and explicitly declined closed-loop sensitivity; I would not reopen that ruling for the sealed
screen, but a development-side closed-loop check on a 2-unit sub-panel (~2.4 worker-h) is worth having before the
FULL2 plan fixes the constant again.

### H7 — Joule-weighted aggregation over a strongly heterogeneous cycle

Ratio-of-sums weights each step by its joules, and joules vary 2.2× across the dwell phase (§H1 table). The
declared estimand is fine, but the number is a mixture with 38.7 % of the weight on the +1.35 % phase and 15.3 %
on the +9.26 % phase. Sensitivity: declared 2.883 %; equal-weight mean of per-step dEE 3.952 % (median 2.114 %);
T = 10 → 2.425 %; T = 20 → 3.019 %; T = 28 (whole cycles) → 3.071 %; first half 2.568 %, second half 3.188 %.
No prior document notes the *within-episode* joule weighting. Report the phase breakdown; do not re-weight.

### H8 / H9 — Clusters and model privilege

Four world clusters, not 36 000 observations — already ruled on by astra and dr3; jackknife is stable so I add
nothing. On privilege: **nominal energy equals realised energy exactly in 720/720 decisions.** Energy is a
deterministic function of the association vector, so the coordinator has a *perfect* energy oracle and only the
bits term is uncertain — and that error is 98 % common-mode across arms (corr 0.975 between FULL's and LITE's
nominal-bits error at matched steps; per-arm sd 2.05 %, sd of the difference 0.46 %). This *strengthens* the
result against an optimiser's-curse reading (the nominal ranker is good, consistent with S0's Spearman 0.910),
but it means "nominal model-based" understates the privilege: half the objective is not modelled, it is known.
Deployment degradation would hit only B̂ — and F is a small difference of two comparable terms (at step 0,
B ≈ 1.98e12 vs η_ref·E ≈ 1.90e12, F ≈ 8e10), so a few-percent channel-model error is order-of-F.

## 2. Estimand critique

**"FULL2 + C3-S vs FULL2, pooled EE, service ≥ BASE − 0.001" is the right *shape* and the wrong *content*.**

1. **The service condition is not a condition.** §H4 shows it cannot bind. Reporting "service was preserved"
   overstates a tautology. The endpoint needs a constraint that can actually bite: delivered bits per served user,
   a demand-satisfaction fraction, or a worst-user rate floor. With unbounded Shannon rates and no demand cap,
   "energy efficiency" here has no notion of *enough*, so the guard's only job — preventing throughput sacrifice
   for joules — is unperformed. (Net throughput rose +1.6 %, so no sacrifice occurred; but that is luck, not the
   design.) Note the per-step evidence that the sacrifice mode is live: at steps 28–29, FULL delivers −1.2 % /
   −2.0 % bits and −2.0 % / −3.9 % joules, and still scores a positive dEE.
2. **The comparator is the weak point a hostile reviewer will attack first, and the attack is cheap.** Demand:
   (a) a non-learned nominal-physics one-step optimiser seeded from a greedy association — does C3-S beat *that*?
   (b) a churn-matched null (random legal renewal) — does the *optimisation* beat mere churn? (c) a
   handover-rate-matched BASE. Without (a)–(c), "third Catfish" is indistinguishable from "we let the controller
   use the simulator at test time", which no reviewer will accept as a learned contribution.
3. **The kill rule admits an arbitrarily small positive.** Correctly ruled as an operational progression, but
   it means the screen's output carries no magnitude and no uncertainty. Fine for a screen; the FULL2 plan must
   not inherit it.
4. **The contrast is internally inconsistent with the negative section.** The oracle marginal that closed the
   additive route (C3 ≤ 0 in G0–G3) and the +2.9 % here are *different objects* priced under the same name.
   The paper cannot report "C3 fails additively" and "C3 succeeds" as two results about one mechanism.

## 3. Upstream framing check — the mis-definition to fix before writing

**"C3 = coordination / load balance" was the wrong axis, and the set-level success does not vindicate it — it
disguises a different lever.**

The physics forbids the load-balancing story outright: per-beam power is a **max**, not a sum; there is no PA
saturation region (p ≤ 1.65 W ≪ 5.218 W); there is no occupancy ceiling; bandwidth is split equally; a beam with
no users costs nothing. So spreading users is monotonically bad and consolidating is monotonically good — a
single monotone axis with no interior optimum, hence no coordination surplus for an additive head to learn.
Two weeks of ≤ 0 oracle marginals is the correct answer to a mis-posed question, and Gemini's global view said so.

What C3-S actually found is **temporal, not spatial**: the recurrence freezes each user's transmit-gain anchor at
segment start, and the endpoint charges nothing to renew it. The monotone dwell-phase profile (+1.35 → +9.26 %
as segments age) is the signature. Concretely, before writing:

- **Rename the mechanism.** It is *endpoint-aware deployment-time reconfiguration* — re-anchoring stale
  associations and extinguishing marginal beams — not set-level coordination. §H3 shows the receipt cannot even
  support the multi-user claim as stated.
- **Reconcile the two prices of a handover.** Either add the switching cost to the EE denominator (or a
  handover-rate constraint to the endpoint), or state explicitly and prominently that the endpoint prices
  handovers at zero while the training reward prices them at Φ₁/Φ₂, and that the third contribution is measured
  in the gap. In a *handover* paper this cannot be a footnote.
- **Decide what C1/C2 are for.** If a nominal-physics optimiser at deployment time recovers this much, the
  reviewer's question is why the heads are learned at all. T3 answers it in ~2 worker-hours and the answer is
  load-bearing for the whole three-contribution structure — including the possibility that it *helps*, by
  showing greedy + C3-S ≪ Q12 + C3-S.

## 4. Top 3 actions

1. **T2 + T1 together: instrumented churn-null replay.** ≈2 worker-h. On a 4-unit sub-panel run BASE, LITE, and a
   `RANDOM-RENEW` arm (uniform random legal non-BASE unilateral edit, no scoring), logging per step: handover
   counts by class, active beam count, users-changed-vs-BASE, mean segment age, mean beam power.
   *Decides:* whether +2.9 % is optimisation or unpriced churn (H1, H2), and how much of it is genuinely
   multi-user (H3). Nothing else in the FULL2 plan should be fixed before this returns.
2. **T3: non-learned-seed 2×2.** ≈2 worker-h. {greedy, greedy+C3-S(lite), Q12, Q12+C3-S(lite)} on the same panel.
   *Decides:* whether C3-S is a third contribution or a substitute for the first two — i.e. whether the
   `FULL2+C3-S vs FULL2` contrast is even the right confirmatory question.
3. **Endpoint amendment before the FULL2 plan is sealed.** ≈0 compute, drafting only. Add (a) a binding
   service/throughput condition that is not action-invariant, (b) an explicit statement of the handover-pricing
   gap, and (c) mandatory reporting of handover rate, active beam count and the dwell-phase EE breakdown
   alongside any EE number. *Decides:* whether the confirmatory run can produce a claim a reviewer will accept.
   Report H5's bus-power table and H6's η_ref arithmetic as disclosures; neither needs a re-run.

**Do not** re-run the sealed screen, retune η_ref, or open TEST for any of this. Every test above is a
development-side diagnostic on fresh sub-panels and leaves the sealed result intact.
