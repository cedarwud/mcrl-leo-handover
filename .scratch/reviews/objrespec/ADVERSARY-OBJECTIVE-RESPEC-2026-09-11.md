# **REJECT**

Adversarial review, fresh context, read-only. No training, no server job, no gradient step.
Reviewer instruction was to break the proposal, not to improve it.

**Reviewed proposal.** Drop or replace `r3` because occupancy has no power derivative; stop
pricing handovers as a reward preference term and instead model their cost as lost bits in the
EE numerator via the 3GPP interruption, "so that the trained objective and the declared
pooled-EE endpoint stop disagreeing."

**Verdict in one line.** The proposal's own mechanism, priced at its own cited source, closes
**1.2% of the disagreement it exists to close** — and the other 98.8% is a physics artefact for
which the owner already sealed a successor on 2026-09-08 that reverses *both* of the
proposal's premises.

---

## What I verified vs. what I assert

### Verified by reading source and re-deriving the arithmetic this session

| Claim | Status | Evidence |
|---|---|---|
| Per-beam power is `max` over served users | **TRUE** | `src/mcrl/env/link_budget.py:439-465` `beam_power_w`, `out[beam] = max(out[beam], value)` |
| Lighting a new beam costs >= 6.267 W | **TRUE, reproduces to 3 d.p.** | `p_sat = 1.65*10^0.5 = 5.21776`; `xi(0.825) = 0.35*sqrt(0.825/5.21776) = 0.139169`; `0.825/0.139169 + 0.338 = 6.26606 W` (`link_budget.py:254-273, 468-546`) |
| Adding a user to a lit beam costs <= +2.455 W | **TRUE** | `8.38342 - 5.92806 = 2.45536 W` from the same three constants |
| A handover consumes zero joules | **TRUE** | `system_power_w` (`link_budget.py:549-587`) is `P^f + sum_b z*P^p`; no handover term anywhere in the power chain. `HANDOVER_COST` lives only in `action_contract.py` and the reward path |
| Handover resets the segment to `p0 = 0.825 W` | **TRUE** | `step.py:786-808`: `continuing = segment.continues(association[uid])`; any association change takes the `else` branch and sets `start_gain = transmit_gain[uid]` so `recurrence_power_w` returns exactly `p0` (`link_budget.py:379-408`) |
| Interference is `z`-gated and load-unweighted | **TRUE** | `interference.py:10-14`, explicit |
| 62 ms / 142 ms are real TS 38.133 values | **TRUE** | `docs/R2-PHYS-PROVENANCE-MATRIX-2026-08-26.md:74-82`, Annex A.14.2.1.7.3 and A.14.2.1.9.2-.3, against a SHA-256-pinned ETSI PDF |
| 24 episodes are independent geometry draws | **TRUE** | `ephemeris.py:421-427` `EpisodeStartSampler.draw` — uniform over 373 available file dates x uniform second-of-day. Not one carrier geometry. **The prompt's suspicion here is wrong; concede it.** |
| RNG-stream position is genuinely controlled | **TRUE** | `step.py:1375-1388` draws fading over `order` = the whole tracked satellite set, which `scenario.py:10-13` fixes for the episode. Consumption is action-independent, so both arms see the same 24 epochs. Also `_draw_segment_ages` uses a spawned `_age_rng` |
| The frozen run had a real eval loop | **TRUE** | `artifacts/training-2026-08-25-rerun01/*/status.json` carries `evaluation_seeds` (10) and per-seed greedy panels. The checkpoint is not an unselected last-episode dump |
| `R = (B/U) log2(1+gamma)` makes a beam's total rate independent of `U` | **FALSE** | see Objection 2 |
| "Occupancy has no power derivative" is a stable property | **FALSE going forward** | see Objection 3 |

### Asserted (reasoning, not measurement)

Everything in the three objections below that is arithmetic on the verified numbers. I ran no
new rollout. Where I project a counterfactual pooled EE I say so.

---

## Objection 1 (ranked first) — the replacement term is 68x to 167x too small to do the job the proposal gives it

This is the objection that decides the verdict, and it is settled by arithmetic on numbers the
project itself sourced.

The declared decision clock is `DECISION_STEP_S = 47 * 0.640 = 30.08 s` (`constants.py:73-90`).
The sourced interruption is 62 ms intra-satellite / 142 ms inter-satellite. So one handover
destroys **0.20612%** / **0.47207%** of one user-step's bits. `R2-PHYS-PROVENANCE-MATRIX`
already tabulated exactly this on 2026-08-26 (`:130-135`).

Apply it to the panel, most favourably to the proposal (every handover charged the full
inter-satellite 142 ms):

```
MAX_NOMINAL_GAIN  numerator x (1 - 0.7117 * 0.0047207) = x 0.9966402
TRAINED           numerator x (1 - 0.2796 * 0.0047207) = x 0.9986801
ratio 1.19771 -> 1.19771 * 0.9979572 = 1.19526
```

**+19.77% becomes +19.53%.** The re-specification closes **0.24 percentage points of a 19.77
point gap — 1.2% of it.** Using the full `D_handover = 152 ms` instead of `T_interrupt` gives
+19.51%, closing 0.26 pp. The rule still beats the learner; the two objectives still disagree;
the arms do not reorder. **The proposal fails on its own stated success criterion.**

Inverting for the interruption that *would* close it:

```
(1 - 0.7117 f) / (1 - 0.2796 f) = 1/1.19771  ->  f = 0.34516  ->  10.38 s per handover
```

That is **68x** the sourced 152 ms, **73x** the 142 ms, **167x** the 62 ms. And the same
provenance document that supplies the 142 ms forbids exactly this move in writing
(`:206-209`): *"No coefficient may be enlarged merely to make the R2 effect visible. If a
sourced event-local or multi-step model still has negligible EE effect, R2 must remain a
continuity/QoS specialist rather than being advertised as an EE-improving Catfish."*

**Answering the prompt's "is r2 self-defeating — cosmetic, or a real change?" — neither. It is
a near-total deletion of the handover price wearing a physics costume.** Price both terms in
the run's own authenticated units (`status.json`: `objective_reward_mean_calibrated =
[4.3757, -2.255, -2.9433]`, `r1_raw = 8.879e6`, `c1 = 2,029,238.43`):

- **Today**, one extra inter-satellite handover costs `0.3` scalar. To break even it must buy
  `0.6 * c1 = 1.2175e6` of raw `r1`, i.e. a **+13.71%** rise in that episode's `r1`.
- **Under the proposal**, it must buy **+0.047%** of that episode's bits.
- **The proposal reduces the price of a handover by a factor of ~290.**

So the proposed optimal handover rate is the corner: hand over at every opportunity. The panel
already shows why — going from 0.2796 to 0.7117 buys +14.62% bits and −4.30% joules, about
**33.8% of bits per unit handover rate** against an interruption cost of **0.47% per unit
handover rate**, a 72:1 margin. (That is an average, not a marginal; the marginal is smaller,
but not by 72x.)

**Evidence that would settle it:** re-score the existing five-arm pooled-EE panel with the
numerator multiplied by `(1 - rate * 0.0047207)` per arm. No rollout needed — it is a
spreadsheet on the numbers already in `CATFISH-ATTACHMENT-SURFACE-2026-09-11.md:539-545`. If
the ranking flips, I am wrong. My arithmetic says it does not move at all.

---

## Objection 2 — the `r3` argument contains an algebra error, and the true occupancy-EE channel runs through the numerator, where the proposal is not looking

The proposal's second premise is: *"`R = (B/U) log2(1+gamma)` makes a beam's total rate
independent of `U`."*

That is true only when every user on the beam has the same SINR. In general:

```
R_beam = sum_{u in b} (B/U_b) log2(1+gamma_u) = B * mean_{u in b} log2(1+gamma_u)
```

A beam's total rate is `B` times the **mean spectral efficiency of its served set**. The
marginal effect of adding user `u` to beam `b` is

```
d(R_beam) = B * (SE_u - mean_SE_b) / (U_b + 1)
```

which is **negative whenever the added user is below the beam's mean** — precisely the crowding
case `r3` is aimed at. Against a power derivative that is `0` (or at most `+2.455 W`), that
numerator term is the *dominant* marginal EE effect of occupancy, and the proposal's analysis
omits it entirely.

The repo's own demonstration of the cancellation is where the error is visible:
`service.py:334-351` `old_r3_is_load_blind` takes `spectral_efficiency: float = 1.0` — **a
scalar**. The cancellation is proved under homogeneous SINR and then generalised. It does not
generalise.

There is a second omitted channel, and it runs the *opposite* way to `r3`.
`interference.py:10-14` states that interference is gated by `z` and **weighted by nothing**:
*"A beam serving eight users interferes exactly as hard as a beam serving one."* So lighting a
beam costs every co-channel victim SINR regardless of its load. At the system level,
`throughput ~ B * sum_{active b} mean_SE(b)` while `power ~ sum_b (P_cir + sqrt(p_b p_sat)/xi_max)`:
both scale roughly linearly in active-beam count, so the first-order EE effect of spreading
**cancels**, and what survives is second-order — of which interference is the largest and is
**negative for spreading**.

So the correct diagnosis is not "`r3`'s premise fails." It is:

> `r3`'s premise is right at the beam level and wrong at the system level, and its *instrument*
> is wrong at both: a head count is blind to spectral efficiency, which is the quantity the
> physics actually charges for.

The proposal's stated ground for dropping `r3` would not survive a referee doing the algebra —
and it reaches the right action for a reason a reviewer can falsify in one line.

**Regimes where the cancellation fails, answering the prompt directly:** (i) **high load** —
`c3 = 6` is the p95 of `|r3|`, so a tail of beams carries 6-8 users where a weak user's
`(SE_u - mean_SE_b)/(U_b+1)` term is largest; (ii) **cell edge** — a user near a null has
`SE_u << mean_SE_b`, so its admission is nearly pure numerator loss at zero power cost;
(iii) **beam saturation** — `classify_link_power_feasibility` at `p_max = 1.65 W` throws users
into `outage_infeasible`, and the audit trail records ~30% of served links below the lowest
MODCOD under a `SINR_min` rule, so outage is load-coupled in a way `r3` does not see and the
proposal does not consider.

**Evidence that would settle it:** on the existing panel, regress per-beam `EE_b = B *
mean_SE(b) / (P_cir + sqrt(p_b p_sat)/xi_max)` against `U_b`, and separately against
`mean_SE(b)`. If `U_b` carries no partial correlation once `mean_SE` is conditioned on, the
proposal's conclusion stands and my mechanism is the same conclusion by a better route. If it
does, the head should be **respecified on SE, not dropped**.

---

## Objection 3 — finding 3 is a known physics artefact with an owner-sealed remedy already in place, and both of the proposal's premises are reversed by that remedy

I could not break finding 3 statistically. **I tried and failed on all four fronts the prompt
named, and I concede them:**

- **Episodes are not one geometry.** `ephemeris.py:421` draws an independent date from 373 file
  dates and an independent second-of-day per episode. `sem` over 24 such draws is the right
  dispersion for the frozen scenario distribution. CV is 4.7% against a 19.8% effect.
- **RNG-stream position is genuinely controlled**, not merely argued: fading is drawn over the
  episode-fixed tracked satellite set (`step.py:1375-1388`, `scenario.py:10-13`), so
  consumption does not depend on the actions and both arms land on the same 24 epochs.
- **The estimand defect is real and small** (<=0.06% at episode level; 19.8% is not 0.06%).
- **Greedy evaluation of an exploration-trained checkpoint is the correct comparison** — greedy
  is the deployment policy, and the frozen run carries a genuine 10-seed eval loop
  (`status.json: evaluation_seeds`), so this is not an unselected final-episode dump.

**But finding 3 is fully explained by the entry anchor, and I can name the line.** Received
power inside a segment is `p(t) * G(theta(t)) = p0 * G(tau)/G(t) * G(t) = p0 * G(tau)` — pinned
at the **segment-start** gain. A handover starts a new segment at the current angle
(`step.py:786-808`), so `MAX_NOMINAL_GAIN` re-anchors every step at the best available `G`, and
gets, simultaneously and by construction:

- **more bits** — the anchor `G(tau)` is maximal every step (observed: 1.146x);
- **fewer joules** — `p` resets to `p0 = 0.825 W` instead of ageing toward `1.65 W` (observed:
  0.957x).

`+14.6%` bits and `-4.3%` joules is the renewal premium, not an objective-specification
finding. This is not new. The project already recorded it on 2026-09-08 as the
segment-anchored-power finding, already ablated the anchor (diag2: *"with the anchor ablated,
forced renewal is bit-identical to BASE — the +0.49% premium was purely the `p0` reset"*), and
the owner already ordered a one-pass audit of the whole power/EE formula.

**And this is the part that should stop the proposal outright.** The sealed successor
declaration (`V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.1+`, primary
`V025-ANGLE-RATE-TPC-TDM-ACM`) does two things, quoted from the review package
(`.scratch/multi-catfish-v023-c3-core-problem-chatgpt-package-20260908/OUTSIDE-ROUND6-CHATGPT-QA-2026-09-08.md:5`):

> "補上 occupancy->required-power，移除 entry-anchor" — **add** the occupancy-to-required-power
> mechanism, **remove** the entry anchor.

Which means:

1. **Removing the entry anchor removes the mechanism that produced finding 3.** The
   disagreement the proposal exists to fix may not survive the successor at all.
2. **Adding occupancy -> required-power makes `r3`'s premise true.** Under a per-user rate
   target `r*` with `B/n_b` bandwidth, required SINR is `2^(r* n_b / B) - 1` — **exponential in
   occupancy**. The proposal would delete a head three days before the sealed physics gives it
   the strongest possible power derivative.

The proposal therefore overturns a sealed decision without citing it, in the direction that
sealed decision explicitly rejects. The project's own standing rule
(`adversarial-review-before-overturning`, recorded as an error committed twice) requires
reading every revision before doing this.

**Evidence that would settle it:** the ablation harness already exists. Re-run the two-arm
pooled-EE panel with the segment anchor ablated. **This is also the answer to "what would make
the whole thing moot."**

---

## What would make the whole thing moot — the single measurement

> **Re-run `MAX_NOMINAL_GAIN` vs `TRAINED e6b063ef` on pooled EE with the segment entry anchor
> ablated, on the same 24 epochs.**

If the +19.8% collapses, the objective never disagreed with the endpoint — the *simulator* paid
a bonus for churn, the proposal is answering an artefact, and re-pricing `r2` and deleting `r3`
would be permanent changes made to fix a bug that is already scheduled for removal. Given diag2
already found the renewal premium was "purely the `p0` reset" in the sibling context, this is
the likely outcome.

A cheaper partial moot: the Objection-1 spreadsheet. If applying the sourced interruption to
the existing panel leaves the ranking unchanged — and it does, at 19.53% — the proposal is
already known not to achieve its stated purpose before anything is run.

---

## The strongest case for keeping `r2` and `r3` exactly as they are

Made properly, because the proposal does not make it.

**1. A handover rate of 0.7117 is a control-plane catastrophe that neither engine models.**
71 of 100 users re-associating every 30.08 s is 142 handovers per user per hour. Per event, TS
38.133 requires measurement reporting (A3/D2), RRC reconfiguration, PRACH, key refresh, UE
context transfer over ISL or feeder, PDCP re-ordering, and a measurement gap. At `D_handover =
152 ms`, 100 users at 0.7117 per 30.08 s is **0.36 s of handover procedure per second,
aggregate** — the control plane is saturated, and RLF risk, ping-pong, and user-perceived stalls
follow. **None of this is bits and none of it is joules.** It appears in neither the numerator
nor the denominator of pooled EE, and it never will, because pooled EE is a physical-layer
ratio. The proposal's move — "model the cost where it physically lands" — silently assumes the
only real cost is the one the physical layer can express. That is the fallacy.

**2. A reward preference term is the standard instrument for exactly this.** The RL handover
literature routinely carries an explicit handover / ping-pong penalty term precisely because the
cost is not expressible in the throughput model
([Jang et al., ETRI Journal 2025](https://onlinelibrary.wiley.com/doi/full/10.4218/etrij.2025-0240);
[Trends in LEO Satellite Handover Algorithms](https://arxiv.org/pdf/2107.08619);
[Handover Protocol Learning for LEO Satellite Networks](https://arxiv.org/pdf/2310.20215);
[Dueling DDQN adaptive multi-objective handover](https://arxiv.org/pdf/2605.02416)). Dropping
`r2` because *this simulator* has no handover joule is confusing **not modelled** with **not
real** — a category error a referee will name.

**3. Deleting a head reverse-engineers the objective from the metric.** `r3`'s stated purpose is
load balancing: `service.py:264-277` proves `sum_u U_{b_u} = sum_b U_b^2`, minimised by an even
spread, and the docstring calls this a legitimate objective in its own right. `Omega = (0.5,
0.3, 0.2)` *is* the paper's multi-objective claim. A two-head MODQN with weights (0.5, 0.2)
renormalised is a different paper.

**4. And the finding, taken seriously, threatens the paper rather than the reward spec.** If
pooled EE is the sole declared endpoint and a one-line rule beats the trained learner by 19.8%
on it, then re-specifying the reward so the learner chases pooled EE puts the learner into
direct competition with a rule that already beats it — and the same document records that on the
objective the learner *is* trained on, **no expressible scripted arm reaches it** (best
`+0.8750 +/- 0.0236` vs `+0.8859 +/- 0.0190`,
`CATFISH-ATTACHMENT-SURFACE-2026-09-11.md:421`). **The three-term objective is currently the
only endpoint on which the learned policy has a defensible claim.** The proposal's success
condition is the paper's failure condition.

---

## What the MORL literature actually licenses

There is no published precedent I could find for *deleting* a reward head on the grounds that
its premise is unphysical in the simulator. The literature-sanctioned moves are two, and neither
is deletion:

- **Keep it as a preference term** with the weight as the declared trade-off. This is the
  dominant practice in RL handover management (sources above) and is what the paper already
  does.
- **Move it to a constraint** — constrained MORL / CMDP, e.g.
  [Huang et al., PMLR v164 (2022)](https://proceedings.mlr.press/v164/huang22a/huang22a.pdf).
  This is also what this project's own outside review already recommended:
  *"把 QoS 當約束，而非把 occupancy variance 當獎勵"* — treat QoS as a constraint rather than
  occupancy variance as a reward
  (`OUTSIDE-ROUND6-CHATGPT-QA-2026-09-08.md:29`). Note that this recommendation supports the
  proposal's instinct about `r3`'s *form* while flatly contradicting its *action*.

Scalarisation is also known to be brittle to exactly the kind of change proposed: small changes
in weighting dramatically alter the reward landscape
([Journal of Cheminformatics, 2026](https://link.springer.com/article/10.1186/s13321-026-01273-8)).
Deleting one of three heads and renormalising is not a small change, and every sealed result
trained under `Omega = (0.5, 0.3, 0.2)` becomes incomparable.

---

## What to do instead

1. **Run the anchor-ablated two-arm pooled-EE panel.** One measurement, existing harness. It
   determines whether there is a problem at all. Nothing else should move first.
2. **Do not touch the MODQN reward before the sealed V025 successor lands.** The successor
   removes the entry anchor (killing finding 3's mechanism) and adds occupancy -> required-power
   (making `r3`'s premise true). Re-specifying the reward against physics that is scheduled for
   replacement is work done against a moving target, in the wrong direction.
3. **If the gap survives anchor ablation, the defect is in the endpoint declaration, not the
   reward.** Pooled EE alone is under-specified: it contains no continuity term and cannot.
   Declare the endpoint as *pooled EE subject to a handover-rate and service-rate constraint*,
   which is what the paper's contribution actually claims, and which the CMORL literature
   supports. That is a one-paragraph pre-registration change, not a reward respec, and unlike
   the proposal it actually resolves the disagreement.
4. **If `r3` is to change, respecify it on spectral efficiency, not delete it** — the physics
   charges for `mean_SE(b)`, not for `U_b`, and the successor will charge for `U_b` too.
5. **Correct the record on the `B/U` claim** before it is cited again. `B/U` does not cancel;
   the beam's total rate is `B * mean_SE`.

---

## Ranked objections, restated

| # | Objection | Settled by |
|---|---|---|
| **1** | The replacement term closes 1.2% of the gap it exists to close; it needs 10.38 s of interruption per handover (68-167x sourced) to work, and it cuts the effective handover price by ~290x | Re-score the existing panel numerator by `(1 - rate * 0.0047207)`. Spreadsheet, no rollout |
| **2** | `B/U` does not cancel — `R_beam = B * mean_SE` — so occupancy has a large numerator derivative the proposal never examines, and interference gives it a second channel with the opposite sign to `r3` | Partial correlation of `EE_b` with `U_b` conditioned on `mean_SE(b)`, on the existing panel |
| **3** | Finding 3 is the entry-anchor renewal premium, already diagnosed 2026-09-08; the sealed V025 successor removes the anchor and adds occupancy -> required-power, reversing both premises | Re-run the two-arm pooled-EE panel with the segment anchor ablated |

## Where I think the proposal is right

Two things, said plainly:

- **`r3 = -U_{b_u}` is the wrong instrument.** I reached that independently and by a different
  route. The panel's own paired result agrees (`GREEDY_R1R2 - GREEDY_SCALARIZED = +0.0091,
  ~2.7 sem` — removing `r3` improves the arm). But the fix is respecification on spectral
  efficiency, timed after the successor lands, not deletion now.
- **The trained objective and the declared endpoint do disagree.** That is real and it matters.
  The proposal's error is the diagnosis (objective mis-specification) rather than the
  observation, and therefore the treatment.

**What would still have to be true for me to change to PROCEED WITH CHANGES:** the anchor-ablated
panel would have to show the +19.8% surviving *and* someone would have to produce a sourced
per-handover cost two orders of magnitude larger than TS 38.133's, from a boundary the paper is
willing to declare (UE energy, control-plane load, RLF-induced retransmission). Absent that
second item, `r2` is a QoS/continuity term — which is exactly what
`R2-PHYS-PROVENANCE-MATRIX-2026-08-26.md` ruled sixteen days ago, and nothing since has moved
it.
