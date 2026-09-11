# Multi-Catfish MCRL — current design state

**2026-09-10. Written so the design can be read as one document instead of ~100 records.
This is not the paper and does not modify it.** Sections marked **STABLE** are safe to write
prose against now; sections marked **OPEN** must not be written down as settled.

Every quantitative figure carries four fields: **reference / information class / estimand /
numerator**. A figure that cannot carry all four is not stated. This rule exists because six
figures reported earlier today were retracted, all for the same reason: the number measured
something other than what it was called.

---

## 1. The problem — STABLE

A LEO constellation serves ground users over Ka-band multi-beam satellites. At a **handover
anchor**, each user must be assigned to a (satellite, beam); transmit power and modulation
follow from that assignment.

Three couplings make the assignment non-separable:

1. **Equal-airtime sharing inside a beam.** A beam's bandwidth is divided equally among the
   users it serves, so a user's achievable rate is an explicit function of **beam occupancy**.
   Adding a user to a beam lowers every other user's share.
2. **Co-channel interference** between beams, within and across satellites, under frequency
   reuse.
3. **Power is provisioned per beam to the worst served link**, so one user's requirement sets
   the beam's power draw for everyone on it.

Together these mean **one user's assignment changes other users' outcomes**. That is why a
per-user greedy choice is not optimal and why a set-level term exists at all.

## 2. Physical constants — STABLE

| quantity | value |
|---|---|
| anchor interval `Delta t` | `30.08 s`, evaluated over **48 boundaries** (47 intervals of `0.640 s`, trapezoidal) |
| per-beam RF cap | `1.65 W` |
| PA share of radiated power | `94.8%`; amplifier law `sqrt(p * p_sat) / 0.35`, `p_sat = 5.2178 W` |
| per-active-chain circuit power | `0.338 W` |
| per-satellite baseband | `0.200 W` |
| contracted user rate | `50 Mbit/s`, i.e. `1.504 Gbit` per user per anchor |
| fading quantile used in scoring | 10th percentile, `q10 = 0.5137` at 30 deg elevation (`0.4292` at 10 deg) |
| rate model | **discrete ACM mode table**, not Shannon |

**Caveat to carry into the prose.** The `sqrt(p * p_sat)` amplifier law **does not appear in
the twelve-paper corpus** this project reviewed. It is a recognised model but it is not what
this literature uses. Earlier characterisation of it as standard practice was an overstatement
and must not be repeated in the paper.

## 3. The objective — STABLE, with one correction

The sealed endpoint is the **Main-only ratio-of-sums energy efficiency**:

```
eta = B / E,    B = sum_t sum_u R_u(t) * Delta t,    E = sum_t P(t) * Delta t
```

*(authoring contract, 2026-08-31, §1)*

**Correction that must be reflected.** The field credits `min(capacity, demand)`: delivered
capacity **above** the contracted rate is not counted. Crediting the surplus is non-standard
and flatters the result — one figure moved from `+113.412%` to `+0.273%` when the cap was
applied. **All reported efficiency in this project now uses the demand-capped numerator**:
integrate each user's delivery over the full `30.08 s` endpoint first, then apply
`min(user delivery, 1.504 Gbit)`, then pool. One user's surplus never satisfies another's
demand.

**Second correction.** Reporting **only** pooled efficiency is against convention. Papers that
care about heterogeneity report the **summed-per-user** form alongside, and criticise pooled
efficiency for hiding per-link allocation. The paper should report both. *(This has not yet
been done in any measurement and is on the repair register.)*

**Service guard.** Any selected configuration must serve at least as many users as the
nearest-eligible baseline. Attainment — how many users reach the contracted rate — is reported
separately from "served" and the two are never substituted for one another.

## 4. Why a learned system exists — STABLE, with one item under verification

A local search over single-user reassignments reaches a good fixed point, but **takes 45–65 s**,
while the decision deadline is **30.08 s**. The learned system exists to approximate, inside
the deadline, what the search reaches outside it.

**Under verification:** the provenance of the 45–65 s figure — what implementation, on what
hardware, and whether an engineered search fits inside 30.08 s. If it does, this motivation
weakens. Nothing in the paper should lean on the exact number until this is settled.

## 5. What the selector actually does at deployment — STABLE, verified today

For each anchor, a **legal catalogue** of candidate whole-network configurations is built
(observed size `948–1000` rows on the measured world). Each row is scored:

```
score(row) = sum over users of [ per-user additive terms ]  +  set-level interaction term
```

and the row with the highest score is committed; ties break on lexicographic configuration id.
*(`scripts/run_v025_pilot_c3.py:1542-1563`)*

**There is no incumbent, no move set, and no "first move".** The interaction term is added to
every row that has a coalition context, and the argmax is over the whole catalogue, so the
set-level term can change the committed choice.

*This corrects an earlier description in this project's own records, which said the deployed
selector was a cyclic first-improvement search over single-user moves. That describes the
`S_UNI` comparator arm and the offline search harness, not the learned arms.*
*(`stagec_v025/deployment.py:62`, `:647`; `synthetic.py:372`; `learner.py:28`.)*

The interaction term is only formed for catalogue rows whose changed set has **size two or
more** (`run_v025_pilot_c3.py:1510`), and on the measured catalogue **79.164%** of legal rows
have no such context. So the set-level term can reorder roughly one fifth of a catalogue.

## 6. The three routes — ROLES STABLE, FORMS OPEN

The design decomposes the score into three information sources. **The three roles are stable
across every candidate design currently under consideration:**

| route | role — safe to write | current form — **OPEN** |
|---|---|---|
| **C1** | the focal user's own-link contribution, per user, local | difference surplus versus the declared default action |
| **C2** | temporal / persistence over a short forecast horizon | absorbing persistence over three sealed offsets |
| **C3** | the set-level correction: what the per-user terms miss | the residual `Psi = Delta F(A) - sum_i d_i`, defined by subtraction |

Two independently proposed replacement designs keep the same three roles and change the
forms:

- physical-term split — credited bits under the candidate's occupancy; resource energy under
  the candidate's activation; continuation;
- information-innovation split — local-link, temporal and relational increments of a
  conditional forecast of the same sealed objective.

**Write the roles. Do not write the formulas yet.**

**Known structural facts about the current forms**, which are why they are open:

- `C3` is **identically zero on single-user changes**, because a residual of one term is
  nothing. Ranking configurations by the residual **alone** is therefore ill-posed, and its
  measured value alone is slightly negative.
- `C2`'s set-level oracle marginal is **zero by construction** — declaration v1.9 §5. Its
  certificate is forecast validity, not a selection marginal.
- `C1` and `C2` are **per-user**; `C3` is **set-level**. The three are not symmetric objects,
  and a requirement phrased as "all three behave the same way" is asking three structurally
  different things to behave alike.

## 7. The ablation design — STABLE

Five learned arms, sealed inventory (`stagec_v025/learner.py:28`):

```
FULL  ·  DROP_C1  ·  DROP_C2  ·  DROP_C3  ·  ALL_NEUTRAL_CONTROL
```

`ALL_NEUTRAL_CONTROL` trains every head on a neutral source. **It is the reference that can
separate the arms, and it is never relabelled `BASELINE`.** The nearest-eligible carrier
incumbent is a different object; because the deployment repair step hands every arm the same
exact-surplus seed, a contrast measured against the carrier incumbent **cannot separate the
arms at all** and is not evidence about any route.

**Format limits, round-trip verified:** the sealed checkpoint format admits **five arms,
2,000 completed epochs, checkpoint cadence 100**; resume is bit-exact. Three thousand and nine
thousand epochs, and eight-arm inventories, are rejected by the loader.

## 8. What the survival criterion says — OPEN, and the two readings differ

The authoring contract states the routes *"are training-time views of one physical
counterfactual, and survive only if their **combined** deployed score improves held-out
Main-only ratio-of-sums EE while respecting the service guard."*

The owner's stated requirement is that **each** of the three individually raises EE, both
alone and in combination.

**These are different claims and the paper's wording depends on which is adopted.** This is a
decision, not a measurement.

## 9. Open, and must not be written as settled

1. **Which decomposition** — incumbent, physical-term split, or information-innovation split.
2. **Whether each route's declared target is learnable at all.** For C1 the first measurement
   found held-out top-1 accuracy `0.1711` against a constant-predictor floor of `0.1716`, and
   a high-capacity model on the same inputs did no better — but that was measured on a feature
   schema with two dead slots, rank 14 of 16, effective dimension 12, and **no elevation
   feature**. A repaired schema (effective dimension 14, elevation added, off-axis angle
   computed rather than hard-coded to zero) now exists and the test is being re-run. C2 and C3
   have never been tested this way at all.
3. **Whether any route raises EE relative to neutral-source training.** The only measurement
   in existence is `-0.01745` *(ref: `ALL_NEUTRAL_CONTROL` · info: as-run panel smoke ·
   estimand: relative pooled-EE marginal · numerator: pooled EE)*, measured on a corpus whose
   labels are surrogates and on the defective feature schema. **It is negative, and it is the
   only reading of the actual question that exists.**
4. **All results.** Every efficiency figure produced earlier today was retracted.

## 10. What is closed, and should stop consuming effort

**The mechanism-paper framing.** A 2024 VTC paper that this project itself cites for the beam
pattern already contains, in Ka-band multi-beam LEO: joint handover and beam switching,
per-beam transmit power as a decision variable, bandwidth shared equally among a beam's users
so rate is an explicit function of occupancy, an occupancy-coupled power loop, a per-user rate
floor, intra- and inter-satellite interference, and pooled energy efficiency as the reported
objective. The remaining genuinely distinct modelling element — a discrete ACM mode table
inside an EE and handover loop — is judged standard industrial practice rather than a research
contribution.

**The learned route is not closed by that finding.** The corpus reviewed does not address a
learned multi-component coordinator evaluated under a decision-time budget. But the room there
has to be found, not assumed: a 2026 paper does joint handover and power under deep
reinforcement learning with a split discrete-continuous action.

---

# UPDATE — 2026-09-10 ~15:40Z. Read this before acting on anything above.

**Two findings since this document was written change what §8, §9 and §10 mean. Neither
changes §1–§7, which describe structure rather than results.**

## U1. The comparison family exists for the first time, and it inverts the reference frame

Nothing above mentions a non-learned comparison family, because **none had ever been run on
this panel.** One now has (`STATIC-BASELINE-FAMILY-2026-09-10.md`, 12-anchor development
panel, full-buffer numerator, both parity gates reproducing the sealed `PANELCEIL` receipt
exactly — 12/12 configuration IDs):

| arm | pooled EE (Mbit/J) | served | active beams |
|---|---:|---:|---:|
| `RSS_MAX` — demand-blind greedy on link gain | **41.621560** | **1200/1200** | 47.8 |
| `MYOPIC_GREEDY` — one-step greedy on `F` | 28.668530 | 1186/1200 | 89.4 |
| `FIRST_IMPROVEMENT_FP` — the certified fixed point | 13.430253 | 1036/1200 | 64.2 |
| `RANDOM` | 11.233999 | 1102/1200 | 81.8 |
| `NEAREST_ELIGIBLE` — geometric base | 11.027760 | 960/1200 | 57.3 |
| `ROUND_ROBIN` | 3.441227 | 798/1200 | 100.0 |

**`RSS_MAX` uses less information than the learned selector** — no demand, occupancy,
interference, energy or fading — and delivers **31.7% more bits on 57.5% less energy at full
service**. Because bits are strictly higher and energy strictly lower, **`F(RSS_MAX) > F(FP)`
for every `eta >= 0`**: the certified fixed point is not a good point of its own objective. It
is a local optimum of a **single-user move class**.

**Consequences for the sections above.**

- **§9 item 4 is now understated.** The retractions were about arithmetic and attribution.
  This is about the reference: every headroom, ceiling and route-contrast figure produced
  before today was measured around a profile that a one-line rule beats **3.099x**.
- **§8's disagreement is unaffected but reframed.** Whichever survival reading is adopted,
  it is stated relative to a base. Which base is now an open question, not a given.
- **§9 item 3's `-0.01745`** was measured against `ALL_NEUTRAL_CONTROL` at that base. It
  remains the only reading of the actual question that exists, and it remains negative.
- **`RANDOM` beats the geometric base by +1.87%.** The sub-random check the owner asked for is
  failed by the geometric base.

## U2. The optimisation is under-run, so tonight's contrasts cannot settle route deadness

`LR-CONVERGENCE-SWEEP-2026-09-10.md`, under a rule fixed before it ran and computing no EE:
**21 of 21 route x learning-rate cells fail at 500 epochs**; none of the three current literals
is admissible; the runner takes **one full-batch Adam update per epoch**, so "500 epochs" is
**500 gradient steps**, with C3 loss still moving 6.89–8.96% per 100 steps at step 500.

**Tonight's two 16-seed runs remain a valid paired comparison at equal budget. They cannot
establish that a route is dead.** `HORIZON` is measuring whether more steps or minibatching is
the lever; the horizon becomes a stopping rule against the already-declared stability criterion
rather than a chosen number.

## U3. What this does and does not do to the killed routes

**Does not revive anything.** No kill has been overturned. What has changed is that the
**condition** under which several of them were taken is now known to have been broken.

`KILLTRIAGE` is classifying every recorded kill as died-on-mechanism (reference-independent) or
died-on-magnitude-against-BASE (at risk). `BASIN` is measuring the minimum number of
**simultaneous** user changes needed for the first F-improving move from base toward `RSS_MAX`
— because escaping a basin where no unilateral move helps but a joint move does **is** the
interaction route, and the probe that ruled C3 dead computed its marginals around the base.

## U4. What is now safe to write, and what is not

**Safe.** §1–§7 as written. The non-learned comparison family's definitions and numbers above:
they are on a parity-checked receipt and do not move when the algorithm changes. These belong
in the experimental chapter's comparison section and can be drafted now.

**Not safe.** Any ceiling or headroom percentage. Any statement that a route is dead. The
method chapter's core equation `F = B - eta_ref*E - Phi`, until `BASIN` reports whether the
failure is search-limited or objective-limited — that distinction decides whether `eta_ref`
stays frozen, and a frozen linear scalarisation is exactly the object Calvo-Fullana Prop. 1
addresses.

## U5. The hypothesis that prompted the measurement is not supported in its stated form

The comparison family was commissioned partly to test whether this project's base is in the
sibling project's shared-Q + argmax collapsed regime, where spreading users fixed it. On this
panel the opposite holds: **`ROUND_ROBIN` at 100 active beams — maximally spread — is the worst
arm by 12.1x**, paying 5.5x the energy for less than half the bits; the **most concentrated**
arm with the **lowest** action diversity is the best. This is consistent with the recorded
physics: per-beam power is a max over served users, so opening a beam pays a near-full PA.

**The conclusion the hypothesis pointed at — that judgements were made against a broken
reference — is confirmed. The mechanism it proposed is not.** `CROWDCOST` is running the
controlled version.

---

# CORRECTION — 2026-09-11 ~01:05Z (found by an independent reviewer)

Two statements in this document are false and must not be used:

1. **Any statement that EE uses a demand-capped numerator is wrong.** Declaration v1.8 item 5 fixes a
   **full-buffer** numerator; every measurement report uses full-buffer with no demand cap.
2. **"Per-beam power is the max over served users" is wrong for the V0.25 a-r0 path.** That is the
   legacy environment. The a-r0 path is **TDM**: one active member per beam per slot (CROWDCOST,
   Part 1).

Also superseded: the three-sides narrative discussed on 2026-09-10/11 was rejected by six
independent reviews; see `.scratch/reviews/REVIEW-SYNTHESIS-2026-09-11.md`.
