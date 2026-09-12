# CF3-PREP — can `T_DELTA` be decomposed into `T_B` and `T_E`? A design-only assessment

> **This is a DESIGN-ONLY note under Amendment 15 §9 of the a2 directive.**
> **It collected NO candidate outcome of any kind** — no P0 collection, no
> disagreement measurement, no `A_repr` fit, no clone, no rollout, no optimizer
> step, no `sat` process. Nothing was executed. **It is NOT authority for a
> fourth source family.** Amendment 15 §1 seals the portfolio to three families
> and this note does not reopen it. If `T0 + T_NEXT` succeeds and the owner
> later authorises a third-Catfish round, this note exists so that work does not
> start from zero. That is its entire purpose.

**Bottom line: the decomposition is technically clean and it is not worth
running. `T_B` and `T_E` are both well-defined with no new constant. They
inherit `T_DELTA`'s arithmetic-identity property exactly, one term each. `T_B`
inherits all of `T_DELTA`'s non-representable content and none of its observable
content, so it is predicted to fail `A_repr` at least as badly as `T_DELTA`'s
clone did (which cleared its own trivial baseline by +0.010 to +0.021). `T_E` as
literally written is decided by an exact-tie set and an action-index ordering,
and with the only no-new-constant repair it becomes structurally `T_TAIL` — "T0
restricted to the minimum-marginal-energy actions" — whose deployable analogue
`B1_NO_NEW_BEAM` the project has already measured at disagreement 0.2567,
dominated by T0, at 0.638 of the condition-5 p10 floor, and already discarded as
the CF3 pilot's C3 source. And this exact bisection — T0 into a pure-bits
endpoint and a pure-energy endpoint — was already prospectively specified,
measured and **rejected** by Stage 0 one information level down (§6.4). The
single most useful thing in this note is §8's prospective test design, which a
future round should copy even if it runs something else.**

Date 2026-09-12. Lane CF3-PREP. Evidence tags: **[R]** = quoted from a committed
report of another lane; **[D]** = plain arithmetic on **[R]** numbers, done here;
**[A]** = an argument from the code, with the code cited. **There is no [V] in
this note, because this lane measured nothing.**

```
PROVENANCE — what this note is made of
- code read (read-only):  worktree /home/u24/papers/mcrl-leo-handover-cf2s-b0,
                          branch catfish2/successor-b0-20260912, base 27f69edf.
                          src/mcrl/algorithms/cf_credit.py is byte-identical to the
                          b1 tip 63b02dc0 (asserted by PHASE-B0 provenance block).
                          No file in any worktree was written by this lane.
- numbers quoted [R]:     PHASE-B0-TDELTA-2026-09-12.md (cf2s-b0 worktree);
                          CONTROLLER-TDELTA-CLOSE / -TTAIL-CLOSE / -TNEXT-ADMIT
                          (main tree, .scratch/catfish2-successor/);
                          LANE-Q-TTAIL-2026-09-12.md (cf2s-tail worktree);
                          STAGE0-2026-09-12.md (main tree, .scratch/catfish2-discovery/);
                          RESULTS-REGISTRY.md rows LP-09, LP-16, EC-01, EC-02.
- constants quoted:       eta_0 = 110,507,234.83444457 bit/J; dt = 30.080000000000002 s;
                          BEAM_POWER_MAX_W 1.65, P_cir 0.338 W/beam, P_BB 0.200 W/sat
                          (link_budget.py:175, 270, 273).  All pre-existing.
- new constants:          NONE.  No threshold, factor, coefficient or gate is
                          proposed, tuned or implied anywhere in this note.
- compute used:           none.  No sat workspace was created, read or written;
                          Lane M's five k = 8 arms were not contended with.
```

---

## 1. The question, and the answer in one paragraph

> Can the already-closed `T_DELTA = ΔB − η₀·ΔE` oracle be cleanly decomposed into
> two physically distinct future candidate sources `T_B` and `T_E`, without
> changing the simulator and without inventing coefficients?

**Technically, yes, and more cleanly than expected**: the shared credit module
never fuses `ΔB` and `ΔE` at all — it returns them as two separate arrays, and
the single line that combines them lives in the B0 *lane script*, not in `src/`
(§2.3). No simulator change and no coefficient is needed; dropping `η₀` is what
the decomposition *is*. **Scientifically, no**: each half inherits `T_DELTA`'s
arithmetic-identity property against its own functional (§5), `T_B` inherits the
whole of `T_DELTA`'s representability failure and none of its mitigation (§6.2),
and `T_E` is either an index-ordering artefact or a re-run of an already-measured
and already-discarded rule (§6.3). §10 states the recommendation.

---

## 2. Audit of the exact counterfactual evaluator

### 2.1 What it computes, at `file:line`

All paths below are in the `cf2s-b0` worktree, which for `src/` is the shared
tree at base `27f69edf`.

| what | where | what it actually does |
|---|---|---|
| `StepEnvironment.evaluate_actions(actions, rng)` | `src/mcrl/env/step.py:643-658` | validates a **full joint** action vector against the step's slot tables, then `_evaluate_selected_actions`. Nothing is committed. |
| `StepEnvironment.evaluate_actions_without_user(actions, rng, focal_user=u)` | `step.py:660-690` | the same, with `u`'s entry replaced by `NO_OP_ACTION` behind the action-contract boundary; every other entry byte-identical. A **removal** counterfactual. Refuses a focal user who is already `NO_OP`. |
| `_evaluate_selected_actions` | `step.py:692-723` | `local_rng = copy.deepcopy(rng)` (`step.py:700`) — **the caller's generator is never advanced**; `segments = self._segments.copy()` (`step.py:701`) snapshots and a `finally` restores the only state `_resolve_physics` writes; rewards and handovers computed with `commit=False`. |
| `_resolve_physics` | `step.py:727-1050` | per-user link-power recurrence (3.11/3.12) at `step.py:770-810`; per-link feasibility against `BEAM_POWER_MAX_W` at `step.py:812-820`; `resolve_service` at `step.py:822`; beam grouping and `beam_power = max over the beam's served users' link powers` at `step.py:864-890`; radiating set, common fading draw, `(U, B)` interference terms, energy. |
| `ServiceResolution` | `src/mcrl/env/service.py:185-260` | resolves `served` / `outage` **per user**: an infeasible link is an outage; there is **no capacity gate and no cross-user admission test**. |
| the returned object | `ActionEvaluation`, `step.py:331` | carries `resolution`, `energy`, `interference`, `radiating`, `link_power_w`, `link_sinr`, `link_rate_bps`, handovers, `system_power_w`, `fixed_power_w`. **It does NOT carry `interference_terms_w`** — that `(U, B)` matrix exists only on `StepOutcome` (`step.py:287`), i.e. only for a *committed* step. This is the mechanical limit B0 §3.1 recorded. |

Two structural facts read from this code matter for everything below, and both
are stated in the credit module's own docstring rather than inferred:

* **Joules are interference-free and SINR-free.** `cf_credit.py:59-63`: "nothing
  in it depends on SINR or interference (the recurrence depends only on the
  off-axis angle, 3.11/3.12). Hence `E_u^D` equals the analytic lighting price
  exactly." Confirmed against `step.py:770-810` (the recurrence is per-user,
  keyed on that user's own segment history and its own chosen slot's off-axis
  angle) and `service.py:185-260` (feasibility is per link). **[A]**
* **Bits are interference-coupled.** `cf_credit.py:50-58`: removing or moving a
  user changes its beam-mates' bandwidth share and changes every co-colour
  victim's interference linearly in the beam's radiated power.

### 2.2 Are `Δbits` and `Δjoules` already separately available?

**Yes, at three separate levels, and the module never fuses them.**

1. **Per evaluation.** `cf_credit.evaluation_bits_joules(ev, dt)`
   (`cf_credit.py:206-209`) returns the pair
   `(system_throughput_bps·dt, system_consumed_power_w·dt)`.
2. **Per candidate action, as two arrays.** `ActionCredits.credit("difference")`
   (`cf_credit.py:397-411`) computes
   ```
   b = self.bits   - self.without_bits      # cf_credit.py:403   -> ΔB per candidate
   e = self.joules - self.without_joules    # cf_credit.py:404   -> ΔE per candidate
   b_out, e_out = outage_charge(b[s], ...)  # cf_credit.py:410
   return np.where(s, b, b_out), np.where(s, e, e_out)   # cf_credit.py:411
   ```
   It returns the **tuple `(B, E)`**. There is no scalarisation inside `src/`.
3. **In the B0 lane's own scorer.** `cf2s_common.StepScorer.candidates`
   (`cf2s_common.py:100-149`) already stores, per user, the arrays
   `row["bits"]` and `row["joules"]` over that user's legal actions
   (`cf2s_common.py:131`), plus `bits_R` / `joules_R` for the reference.

**The one line in the entire project that fuses them is
`cf2s_common.py:211`, `d = b - eta0 * e`, in a lane script — not in `src/`.**
That is the whole of what a decomposition would have to change.

### 2.3 What this means for the bounded question

The decomposition requires **no simulator change, no `src/` change, and no new
coefficient**. It requires deleting a multiplication.

---

## 3. Are `T_B` and `T_E` well-defined? Yes — with two caveats, one of them fatal to `T_E`

Definitions, stated in the project's existing vocabulary and using only the
project's existing quantities:

```
For a current state, R = T0's joint legal action (cf_teacher.t0_scores, masked
argmax, first index on ties).  For focal user u, hold R_{-u} fixed.  For every
legal a of u let (B_u(a), E_u(a)) = ActionCredits.credit("difference"), i.e.
the B1 difference semantics with the already-validated outage charge.

    T_B = argmax_a B_u(a)        (first index on ties)
    T_E = argmin_a E_u(a)        (first index on ties)
```

### 3.1 Both are well-defined over the deployable action set; neither is deployable

The candidate set is exactly `np.flatnonzero(masks[u].mask)` — the deployed 28-slot
legal mask. `NO_OP_ACTION = -1` is **not** in it: it is "the absence of a
decision", not maskable (`action_contract.py`, `NO_OP_ACTION` docstring), so
neither source can select "do not transmit". Both sources, like `T_DELTA`, are
**training-only privileged specialists around T0's joint reference**; deployment
must never need the evaluator, and the only thing that could ever run at
deployment is the 113-dim student.

### 3.2 A finding that simplifies both: the without-`u` baseline does not affect either action

`without_bits` and `without_joules` are **per-user constants**, identical for every
candidate `a`. So on the served candidates the baseline is a pure shift and
cancels in both the argmax and the argmin. It survives only through the outage
charge (`cf_credit.py:410`), and there it is one-sided:

* `b_out = min(0, min over served b) ≤ min over served b`, so **`argmax B` can
  never strictly prefer an outage candidate** when a served one exists;
* `e_out = E_max = (supply(p_max) + P_cir + P_BB)·dt` is, by the module's own
  proof (`cf_credit.py:71-86`), an **upper bound on the E credit of any served
  action**, so **`argmin E` can never strictly prefer an outage candidate**
  either.

**Therefore `T_B = argmax over served candidates of bits(R_{-u}, a)` and
`T_E = argmin over served candidates of joules(R_{-u}, a)`, exactly.** [A]

Two consequences. First, **neither source needs the without-`u` evaluation at
all** — the removal counterfactual, the cheap-exact-baseline parity work, and the
whole `without_user_rates` / `interference_terms_w` restriction of B0 §3.1 are
simply irrelevant to them. That removes 100 evaluations per step (§9) and removes
an entire class of verification work. Second, the outage charge, which cost B0 a
paragraph of explanation, reduces here to a one-line invariant that a screen can
*assert* rather than measure.

**Residual degeneracy, which a screen must count rather than assume away:** if
*every* legal action of `u` is an outage, then all `b` equal `b_out = 0` and all
`e` equal `E_max`, both sources tie across the whole candidate set, and the
first-index rule decides. B0 measured 361 of 4,000 parity decisions with at least
one outage candidate and **0 outage choices in 18,989 deviations** [R], but it
never reported an all-outage-decision count. A screen must report it.

### 3.3 `T_B` is well-defined without qualification

`bits(R_{-u}, a)` is a continuous quantity and exact ties are not expected: B0
measured **0 exact top-1/top-2 ties in 4,000 decisions** on the combined score,
with a minimum *positive* margin of 9.257e5 bits against a score scale of
1.485e10–5.682e10 [R]. The first-index rule is a formality for `T_B`.

### 3.4 `T_E` is well-defined only in a sense that should not satisfy anybody

This is the caveat that matters and I state it plainly.

`ΔE` is *exactly zero* for every candidate that joins an already-lit beam whose
current maximum link power is at least `u`'s own link power on that slot. That is
not an approximation: joules depend on no SINR and no interference
(`cf_credit.py:59-63`), the beam radiates `max` over its served users' link
powers (`step.py:886`), and `u`'s own link power is a per-user angle recurrence
independent of everyone else's action (`step.py:770-810`). Add `P_cir·dt` only if
`u` lights the beam, and `P_BB·dt` only if `u` lights the satellite
(`cf_credit.py:224-252`). Every other candidate contributes exactly 0.

So `T_E`'s score is a **coarse, heavily-tied, largely-integer-valued** function,
and the size of its exact-tie set is the single quantity that decides whether the
source is information or noise. **This lane did not measure that tie set and must
not** — but the arithmetic makes the concern concrete rather than speculative:
the environment lights 56.8 beams under T0 and 63.4 under the rule [R], each user
has 28 candidate slots of which a mean 26.4 are legal [R], and the cheapest
non-zero increment available is `P_cir·dt = 0.338 × 30.08 = 10.167 J`, priced at
`η₀ × 10.167 = 1.124e9 bits` [D].

If the tie set is large — which is what one would expect — then `T_E`'s action is
decided by `np.argmin`'s **first index on ties**, i.e. by the action-index layout
`a = 7·l + j`, satellite slot then beam slot. **Amendment 15 §2A says in terms
that "the current user-relative action-slot number is not a permanent physical
identity and may not be used as one."** A source that resolves most of its
decisions by that number would be earning its distinctness gate from a labelling
convention. Its `A_repr` would then measure whether a 113-dim network can predict
"the lowest-index zero-marginal-cost slot", which it probably can, and which
would mean nothing.

**The only repair available without inventing a constant** is the frozen
lexicographic pattern Amendment 15 §2A and §2B already use for `T_NEXT` and
`T_TAIL`:

```
    T_E' :  ( -marginal_joules,  current_T0_score,  -current_action_index )
```

using the project's existing `cf_teacher.t0_scores`. This is legitimate — it
introduces nothing new — but it changes what the source *is*, and §6.3 shows what
it changes it into.

---

## 4. What privileged information each would carry

The deployed observation is 112 + 1 = 113 dims: four 28-wide per-user blocks —
access one-hot, `log1p(channel_quality)`, per-candidate off-axis angle `theta`,
and `beam_loads` = **global ungated per-beam demand of the previous step**,
divided by `num_users` — plus normalised remaining steps
(`runtime/state_encoding.py::encode_state`, `cf_ratio.py:204-210`). Each user sees
only its own four blocks. **Nowhere in it are: other users' channel qualities, the
current-step lit set, per-beam radiated or maximum link power, the colour map, or
the `(U, B)` interference-term matrix.**

**`T_B` = argmax system bits under `(R_{-u}, a)`.** Decomposes into
(i) `u`'s own realised rate, which is bandwidth-share-divided — own gain is
observable (block 2), the divisor is proxied by the *previous* step's demand
(block 4); (ii) the share dilution `u` imposes on its new beam-mates — the
current-step membership of that beam is **not** observable; (iii) the co-channel
interference `u` adds to every same-colour victim on other beams and satellites,
linear in the beam's radiated power — **not observable at all**, and the largest
genuinely novel part.

**`T_E` = argmin system joules under `(R_{-u}, a)`.** Decomposes into
(i) the supply-power increment on the target beam, non-zero only if `u` becomes
its unique maximum-power user; (ii) `P_cir` if `u` lights the beam; (iii) `P_BB`
if `u` lights the satellite. Needs the current lit set and the per-beam maximum
link powers — not directly observable, but proxied by block 4 (previous-step
demand tells you which beams were populated) and block 3 (`theta` drives `u`'s own
link power through the recurrence). **It contains no interference information
whatsoever, by construction.**

**Are they different from each other?** Yes, and this is the most attractive
property of the decomposition: in this physics `B` and `E` depend on **disjoint
mechanisms** — bits are interference-coupled and joules are not. The split is
physically principled, not an arbitrary bisection of an expression.

**Are they different from T0?** Much less than the framing suggests.
`T0 = LP-prev(c = 1, m = 0)`, `score(a) = log2(1 + max(γ_a, 0)) − 1·[N_a = 0]`
(`cf_teacher.py:60-82`), reading blocks 2 and 4. Its first term is a monotone
transform of the own-rate part of `T_B`; its second term is a 0/1 proxy for the
`P_cir` part of `T_E`. The credit module says so itself: **"The LP(c, m) rule
family is the greedy (one-step, own-bits) version of this credit"**
(`cf_credit.py:34-35`), and Stage 0 verified LP-prev(0) ≡ `MAX_NOMINAL_GAIN` and
LP-prev(c→∞) ≡ `B1_NO_NEW_BEAM` bit-identically [R].

**So T0 is already a crude scalarisation of exactly the pair `(T_B, T_E)`, with
`c = 1` as its mixing coefficient.** The decomposition does not open a new
information axis. It separates the two axes T0 already mixes and adds to each the
cross-user part T0 lacks — which is precisely the part `T_DELTA`'s screen showed
does not survive the 113-dim bottleneck.

Stage 0's own sentence on this is worth quoting against the proposal: *"The
`c = 1` mixture, not either term, is where the value sits."* [R] — and it is not
a stray remark; it is the verdict of a measured decomposition experiment that
tested this exact bisection one information level down. See §6.4.

---

## 5. The tautology question, answered directly

**Q: `T_DELTA` is the argmax of `ΔB − η₀ΔE`, and T0's action is in the candidate
set, so `Δ ≥ 0` was guaranteed. Would `T_B` and `T_E` have the same structural
property against their own scoring functionals?**

**A: Yes. Exactly, identically, and with the same three escapes.** For `T_B`: `R_u`
is legal, so it is in the candidate array, and `bits` at that index equals
`bits_R` exactly (the alternative vector *is* `R`); the argmax over served
candidates therefore satisfies `ΔB(T_B) ≥ 0` whenever `R_u` is itself served.
For `T_E`: symmetrically, `ΔE(T_E) ≤ 0`. The only ways the sign can fail are the
three B0 already enumerated — the outage charge refusing a system-improving
outage move, an exact tie, and `R_u` itself being in outage — which is why
`T_DELTA`'s candidate-better fraction was 0.99958 rather than 1 [R].

So the controller's `T_DELTA` finding transfers verbatim, one term each:

> **A "candidate-better fraction" or a `CR` computed on `ΔB` for `T_B`, or on
> `ΔE` for `T_E`, is a near-arithmetic identity of that source's construction,
> carries no information about it, and may not be cited as evidence — in a lane
> report, in the registry, or in the paper.** The predicted values are ≈ 1 and
> ≈ ∞ respectively, and a lane that reported them as a result would be
> reproducing the defect that closed `T_DELTA`.

There is a second, softer near-tautology that a screen must also refuse to bank:
**the distinctness gate is nearly free for any exact-evaluator best response.**
`T_DELTA` scored 0.79121 against a 0.25 line [R] and `T_TAIL` 0.41176 [R],
because a system-functional best response and T0's local per-user rule are simply
different functionals over the same 26.4-candidate set. Distinctness passing is
therefore weak evidence, and for `T_E` it could be earned outright by the
first-index tie-break (§3.4).

### 5.1 How a screen would have to be designed so its gates are not tautological

1. **Use Amendment 15 §5's gates, not Stage 0's.** §5 replaced `CR` /
   candidate-better with **distinctness + `A_repr`** for new candidates. Neither
   is scored on the candidate's own functional, so neither is an arithmetic
   identity. `T_DELTA`'s defect was in the *inherited Stage-0 value gate*, which
   §5 does not use. The defect recurs only if a lane volunteers the old numbers.
2. **Cross-score, never self-score.** Report `T_B` against `Δ = ΔB − η₀ΔE` (the
   functional it does *not* maximise — `T_B` trades energy for bits, so the sign
   is genuinely free) and `T_E` against `ΔB`. These are the only Δ-type numbers a
   screen may report, and both must be pre-declared as diagnostics, not gates.
3. **Add a closed-source pre-gate, before anything else runs.** Measure
   `disagreement(T_B, T_DELTA)` and `disagreement(T_E, T_DELTA)` on the same
   collection. **If either is small, that source is a closed source under a new
   name, and running it is reopening `T_DELTA`** — barred by Amendment 15. Also
   measure `disagreement(T_B, T_E)`: if it is small, the "two distinct sources"
   claim is empty and the round collapses to one candidate.
4. **Pre-declare the degeneracy counters**, so a distinctness pass cannot be
   earned by arbitrariness: the exact-tie mass of the leading criterion per
   decision, the fraction of decisions the leading criterion decides *uniquely*
   (the diagnostic that explained `T_TAIL`), and the all-outage-decision count.
5. **Every `A_repr` figure is reported beside the candidate's own
   pure-T0-imitation baseline** — now mandatory, per the `T_TAIL` closure §3.
   Design in §8.3.

---

## 6. The representability question, answered honestly

### 6.1 What `T_DELTA`'s screen actually established, re-read against the `T_TAIL` standard

The `T_TAIL` closure ruled that "`A_repr ≥ 0.50` should be read alongside the
candidate's own pure-T0-imitation baseline", the baseline being the source's own
agreement rate with T0. Applying that standard retrospectively to `T_DELTA`, from
B0's committed numbers:

| quantity | value | source |
|---|---:|---|
| `disagreement(T_DELTA, T0)` on the clone's own corpus **C** | 0.79046 | [R] B0 §4.2 |
| ⇒ trivial baseline (a perfect T0 clone's top-1 against `T_DELTA`) | **0.20954** | [D] `1 − 0.79046` |
| clone **BC** TEST top-1 | 0.2305 | [R] B0 §5.2 |
| clone **SOFT τ = 0.3** (the selected one) TEST top-1 | 0.2198 | [R] B0 §5.2 |
| **BC margin over its own trivial baseline** | **+0.0210** | [D] |
| **SOFT τ = 0.3 margin over its own trivial baseline** | **+0.0103** | [D] |
| for comparison: `T_NEXT` +0.168, `T_TAIL` −0.125 | | [R] TTAIL close §3 |

*(The trivial baseline is computed from the whole-corpus disagreement rather than
from the TEST split specifically, because the TEST-split value was never
reported; the corpus that would give it exactly lives on `sat` and this lane is
barred from `sat`. Labelled as an estimate accordingly.)*

**So `T_DELTA`'s clone recovered about two percentage points of a
seventy-nine-point distinctive band — on the order of 2–3 % of the source's
distinctive information.** And B0's own §5.5 records the mechanism directly:
clone agreement with T0's action on their own closed loops was **0.3909** (BC) and
**0.5051** (SOFT τ = 0.3), against the teacher's 0.20954 — **the clones agree with
T0 roughly twice as often as the teacher does.** That is exactly the
*collapse toward T0* that the `T_TAIL` closure identified as the decisive failure
mechanism, and it was already present in `T_DELTA`'s numbers before that
vocabulary existed.

This reframing is worth recording independently of the decomposition question:
**`T_DELTA` did not fail `R_repr` narrowly and then fail non-degeneracy; it also
failed the `T_TAIL` standard, badly, and the two closures agree on the
mechanism.**

### 6.2 Would `T_B` inherit it? Yes, and worse

`T_DELTA`'s score is `ΔB − η₀ΔE`. Of those two terms, `ΔE` is the one with an
observable proxy: it is interference-free, driven by the target beam's lit state
and `u`'s own link power, and block 4 (`beam_loads`) plus block 3 (`theta`) speak
to both. `ΔB` is the one that is not: its distinctive content is the co-channel
interference externality and the current-step share dilution, neither of which
appears anywhere in the 113 dims (§4).

**`T_B` is `T_DELTA` with the more-observable term deleted.** Every part of
`T_DELTA` that a 113-dim student could in principle latch onto is removed, and
the part that defeated it is kept whole. The prediction follows directly and
should be stated as a prediction, not a measurement: **`T_B`'s `A_repr` would be
no better than `T_DELTA`'s clone top-1 of 0.2198–0.2305, against a trivial
baseline of roughly the same 0.21, i.e. a fail against the 0.50 line by about
0.28 and a margin over trivial of approximately zero.** [A]

The one honest counter-consideration: `A_repr` uses BC top-1 on the deployed
observation with episode-disjoint splits (Amendment 15 §5), which is not
bit-identical to B0's clone protocol (which selected a soft temperature on VAL
and read a closed-loop EE ratio). The instruments differ. But the two protocols
already agree on `T_DELTA` — B0's BC arm *is* a top-1 imitation clone, and it
scored 0.2305 — so there is no reason to expect the change of instrument to
rescue a strictly harder label set.

### 6.3 Would `T_E` inherit it? It is caught in a squeeze instead

`T_E` is the one half with a plausible route to a high `A_repr`, because `ΔE` is
interference-free and partly proxied by block 4. But a high `A_repr` for `T_E`
would be a pass for information T0 already has, and the two branches of §3.4 both
end badly:

**Branch A — take `T_E` literally (`argmin ΔE`, first index on ties).** Its
distinctness is then substantially manufactured by the action-index ordering
(§3.4), which Amendment 15 §2A forbids treating as a physical identity, and its
`A_repr` measures the predictability of an index convention. This branch is not
scientifically admissible whatever number it produces.

**Branch B — repair it with the frozen lexicographic tie-break
`(−ΔE, T0 score, −index)`.** The source becomes **"T0 restricted to the
minimum-marginal-energy actions"** — structurally identical to what the `T_TAIL`
closure §4 called the honest description of `T_TAIL`: *"T0 restricted to the
actions surviving a service-tail filter"*. `T_TAIL`'s diagnosis was that its
leading criteria *filtered* heavily while *uniquely deciding* almost never, so the
T0 tie-break decided 99.32 % of the time, the clone collapsed toward T0, and
`A_repr` landed 0.125 **below** its own trivial baseline [R]. A large `ΔE = 0` tie
set is exactly the condition that reproduces this. And if instead the tie set is
small — so the energy filter *does* decide — then `T_E` becomes an
always-consolidate rule, which the project has already measured:

| the nearest already-measured relative | value | source |
|---|---:|---|
| `B1_NO_NEW_BEAM` ≡ LP-prev(c→∞), the activation endpoint: disagreement with T0, shared states | **0.2567** — barely over the 0.25 line | [R] Stage 0 §2 |
| its EE / T0 | 0.8877 | [R] |
| its p10 / T0 | 0.3200 | [R] |
| its condition-5 p10 / floor | **0.638 ✗** (the only arm besides RANDOM to fail it) | [R] |
| its Pareto status | **dominated by T0** | [R] |
| its bits ratio vs `A m=2dB` | 0.586 (evaluation) / 0.574 (calibration) — throughput-degenerate | [R] LP-09 / LP-16 |
| its history in this project | it **was** the CF3 pilot's C3 catfish source, on the `Q_E` head | [R] DOCUMENT-STATUS |

`T_E` is not identical to `B1_NO_NEW_BEAM` — it uses the *current-step* lit set
where the rule uses previous-step loads, and it lacks the rule's `argmax γ_a`
tie-break — but it is the same policy character, at the same endpoint of the same
family, whose *exact* endpoint the project has measured as dominated and
throughput-degenerate and has already tried as a catfish source.

Amendment 15 §7 is correctly permissive here (`Ti-only` need not beat
`T0-only`, and a bad standalone rollout is not disqualifying). That is why the
argument above is *not* "`T_E` would be a bad controller". It is: **`T_E`'s
distinctive information is either an index artefact, or the same information the
project has already extracted from this corner of the physics and already
discarded.**

### 6.4 The precedent this note nearly missed: Stage 0 already ran this decomposition

Found while checking the nearest relatives, and it is the single most relevant
piece of prior evidence in the project. **Stage 0 prospectively specified,
measured and rejected exactly this decomposition — at the deployable-rule
information level.** Its "T0 decomposition diagnostic" split
`T0 = LP-prev(c = 1, m = 0)` into its two endpoints:

* the **link endpoint** `MAX_NOMINAL_GAIN` ≡ LP-prev(`c = 0`) — the pure-bits
  term, verified bit-identical;
* the **activation endpoint** `B1_NO_NEW_BEAM` ≡ LP-prev(`c → ∞`) — the
  pure-energy term, verified bit-identical.

That is the same bisection `T_B` / `T_E` proposes, one information level down.
Stage 0's verdict, quoted [R]:

> "Neither endpoint separately satisfies conditions 1–5 against the fused T0, so
> by brief §3 the decomposition is **rejected as a multi-catfish interpretation,
> and T0 remains one candidate source.** … Neither endpoint owns a state subset
> where it beats fused T0 in aggregate — both have `Σ Δ < 0` and `CR < 0.5` on
> exactly the states where they disagree. The `c = 1` mixture, not either term,
> is where the value sits."

Measured endpoint figures [R]: link endpoint disagreement **0.1982** (fails the
0.25 line), `CR` 0.3253, `Σ Δ` −2.04e13, EE/T0 0.9352; activation endpoint
disagreement 0.2567, `CR` 0.3920, `Σ Δ` −1.85e13, EE/T0 0.8877, p10 at 0.638 of
the condition-5 floor, dominated by T0.

**Does the cause of that rejection exist at the counterfactual information
level?** The project's standing rule is that an old failure transfers only when
its cause does, so this must be asked rather than assumed. The cause was a
property of the *criterion*, not of the information level: each endpoint pursues
one term to the exclusion of the other, and in this physics EE is a ratio in which
both terms move together, so a single-term argmax leaves value on the table
wherever it departs from the mixture. That mechanism is untouched by upgrading
from a local rule to an exact counterfactual — `T_B` is still a pure-bits argmax
and `T_E` still a pure-joules argmin.

**The one thing that could make it not transfer**, stated so it is not glossed
over: the rule endpoints are *local* — they read only `u`'s own gain and the
previous step's loads — whereas `T_B` and `T_E` internalise the cross-user
externality. A single-term criterion that *knows what it costs everyone else*
could in principle own a state subset that its local analogue does not. That is a
real possibility and it is the only argument for running the round. But it is also
exactly the content that `T_DELTA`'s screen showed does not reach a 113-dim
student (§6.1–§6.2), so even if the possibility is real, the pipeline cannot
deliver it.

So: the decomposition has been rejected once on measured evidence at the rule
level, and the mechanism that rejected it is criterion-level rather than
information-level. That does not by itself close the counterfactual version — the
project does not transfer verdicts that way — but it raises the bar for running it
well above "it has not been tried".

---

## 7. Code reuse — what exists verbatim, what would have to be written

### 7.1 Reusable verbatim, no change

| artefact | where | why it is exactly right |
|---|---|---|
| the credit itself | `src/mcrl/algorithms/cf_credit.py` (`ActionCredits.credit("difference")`, `outage_charge`, `PowerModel`) | already returns `(ΔB, ΔE)` **as two arrays** (`cf_credit.py:403-404, 411`) |
| the exact evaluator | `src/mcrl/env/step.py:643-723` | unchanged; the rng-deep-copy and segment snapshot/restore contract is the same for any argmax over the same candidate set |
| T0's reference and scores | `src/mcrl/algorithms/cf_teacher.py:60-102` | the reference `R`, the tie-break convention, and the tie-break score for a repaired `T_E` |
| the per-step candidate scorer | `.scratch/catfish2-successor/scripts/cf2s_common.py::StepScorer.candidates` (b0 worktree) | already produces per-user `bits`/`joules` arrays over the legal set (`cf2s_common.py:131`) — **this is the entire measurement machinery** |
| the collection / sharding / rollout driver | `cf2s_tdelta.py` (b0) | DEV/DEVVAL seed guards, `cf_dev.dev_rollout`-mirrored accumulation, episode sharding, parity assertion |
| the `A_repr` protocol | `.scratch/catfish2-successor/lane-q/scripts/ttail_clone.py` (cf2s-tail worktree) | Amendment 15 §5's frozen family, episode-disjoint splits, BC top-1 only, and **it already computes `t0_imitation_floor`** (`ttail_clone.py:147, 172, 304`) — the control the `T_TAIL` closure made mandatory |
| the lexicographic tie-break helper | `.scratch/catfish2-successor/lane-q/scripts/ttail_common.py::lex_argmax` (cf2s-tail) | exactly the `(criterion, T0 score, −index)` shape a repaired `T_E` needs |
| the P0 seed namespace | Amendment 15 §3: env `9_202_500 + i`, mob `9_203_500 + i` | already audited clean by the controller before launch |

### 7.2 What would have to be written

Very little, and none of it in `src/`.

1. **Two argmax lines**, replacing `cf2s_common.py:211`'s `d = b - eta0 * e`:
   `j_B = argmax over served of row["bits"]`, `j_E = argmin over served of
   row["joules"]` (or `lex_argmax` for a repaired `T_E`). Both sources come out of
   **one** pass over the candidate arrays already in memory.
2. **Drop the without-`u` branch** (`cf2s_common.py:138-145`) — §3.2 shows it is
   not needed. This is a deletion, not new code.
3. **The degeneracy counters** of §5.1(4): tie mass, unique-decision fraction,
   all-outage decisions. Perhaps thirty lines.
4. **The pairwise disagreement matrix** `{T0, T_DELTA, T_B, T_E}` on the same
   collection — the closed-source pre-gate. `T_DELTA`'s action comes free from the
   same arrays (one extra scalarisation, zero extra evaluations).
5. **A mutant suite**, in the shape Lane Q used (11 named mutants each
   individually red). At minimum: `argmax`↔`argmin` swapped; `bits`↔`joules`
   swapped; `η₀` reintroduced anywhere; the outage substitution removed; the
   tie-break changed; the reference changed from `R` to something else.
6. **A parity test for a cheap exact `ΔE` path**, if §9's optimisation is wanted.

### 7.3 A cost optimisation that exists only for `T_E`, and its verification debt

Because joules depend on no SINR and no interference (§2.1), and because `u`'s
link power and feasibility are per-user (`step.py:770-820`, `service.py:185-260`),
`joules(R_{-u}, a)` should be computable **analytically** from one evaluation of
`R_{-u}` plus `u`'s own per-slot link power — with no per-candidate system
evaluation at all. That would collapse `T_E`'s cost from ~2,638 evaluations per
step to order 100.

**This is a plausible design finding, not a verified one.** It is *not* the cheap
path B0 examined: B0's `without_user_rates` is a **removal** counterfactual for
*bits*, restricted to committed steps by `interference_terms_w`; this is a
**replacement** claim for *joules*, and the reason it could work is precisely the
reason the bits version could not. Before it were used it would need B0 Task 1's
own treatment: exact argmin identity on a declared parity sample, maximum absolute
and relative score deviation, and the minimum positive top-1/top-2 margin to
compare them against. **This lane did not run it and states it as an open item.**

---

## 8. The prospective test design (only if a round is ever authorised)

Stated as a design. **Nothing here is authorised, and running it would require an
owner decision under Amendment 15 §1.**

### 8.1 Order of operations, frozen before the first number

1. Freeze the source definitions, the collection seeds, the splits, the
   degeneracy counters and the reporting contract in a PROGRESS file **before any
   counted computation**, in B0's manner.
2. Write the mutant suite and turn each mutant red **before** the collection.
3. Run **one** P0 collection on T0's own trajectory (the shared-state
   construction), 24 DEV episodes, `t = 1…9` as the headline read with `t = 0`
   reported separately (Lane Q's convention). Score `T_B`, `T_E` **and**
   `T_DELTA` from the same candidate arrays.
4. Read the **pre-gates** (§8.2) before anything else. A pre-gate failure closes
   the round there.
5. Only then read distinctness, then fit the clones, then read `A_repr` beside its
   trivial baseline.

### 8.2 Pre-gates — these come first and can end the round

| pre-gate | why | reading |
|---|---|---|
| `disagreement(T_B, T_DELTA)`, `disagreement(T_E, T_DELTA)` | a decomposition that reproduces a closed source **is** that closed source | small ⇒ that half is `T_DELTA` renamed; closing, not admitting |
| `disagreement(T_B, T_E)` | the whole claim is that they are two distinct sources | small ⇒ the round has one candidate, not two |
| exact-tie mass of the leading criterion, per decision | §3.4 | large for `T_E` ⇒ Branch A is dead and only the lexicographic repair may proceed |
| fraction of decisions the leading criterion decides **uniquely** | the diagnostic that explained `T_TAIL` | near zero ⇒ predicted collapse toward T0 |
| all-outage decisions | §3.2 | reported, not gated |

### 8.3 Distinctness, `A_repr`, and the mandatory companion baseline

**Distinctness** is Amendment 15 §5's `disagreement(T_i, T0) ≥ 0.25` on the frozen
P0 collection. Recorded as a distinctness gate only, never a value claim, and —
given §5's second paragraph — explicitly annotated as *weak* for an
exact-evaluator best response.

**`A_repr`** is §5's frozen protocol, unchanged and not re-tuned: `113 → 100 → 50
→ 50 → 28`, tanh, Adam 1e-3, batch 256, ≤ 400 epochs, the deployed 113-dim
observation only, episode-disjoint TRAIN/VAL/TEST fixed before fitting, **BC /
top-1 imitation only**, admission `A_repr ≥ 0.50`. Call it `A_repr`, never
`R_repr`.

**The candidate's own pure-T0-imitation baseline is a required companion**, per the
`T_TAIL` closure §3. Two forms, and a round should report both:

* **analytic (free, and the conservative one):** the fraction of TEST-split
  decisions where T0's action equals the source's action — the score a *perfect*
  T0 clone would achieve. This is Lane Q's `t0_imitation_floor`
  (`ttail_clone.py:147`), costs nothing, and is a strict upper bound on any
  realisable T0-only clone.
* **fitted (one extra fit, ~18 s):** the same frozen family on the same corpus and
  the same splits, with labels replaced by `R_u`, evaluated for top-1 agreement
  with `T_i` on the same TEST episodes.

**The headline figure is `A_repr − trivial baseline`, reported next to
`T_NEXT`'s +0.168 and `T_TAIL`'s −0.125.** A source clearing 0.50 while sitting
below its own baseline has learned nothing, and a source below 0.50 but far above
its baseline is a different kind of failure; the fixed floor alone cannot tell
them apart.

**Also required, because `T_DELTA` needed it and did not have it:** the clone's
top-1 **conditional on the source disagreeing with T0** versus **conditional on
agreeing** (Lane N and Lane Q both reported this; B0 did not), and the clone's own
agreement rate with T0 on its closed loop, which is what exposes collapse.

### 8.4 One diagnostic that is *not* authorised under the current text

The natural way to localise a representability failure is an **information
ablation**: fit the same clone on the 113 dims, and again on 113 dims plus the
specific missing quantity (the current lit set / per-beam maximum link powers),
and see whether the gap closes. If it does, the bottleneck is provably the
observation and not the fit — which would be a genuinely publishable sharpening
of "the advantage is counterfactual, not a feature of the observation".

**Amendment 15 §5 forbids it as written**: `A_repr` is defined "on the deployed
113-dim observation only", with no observation variants. It would need an owner
decision, and it must be run — if ever — strictly *outside* the gate, as a
diagnostic that cannot rescue a failed candidate. Recorded here so the idea is not
lost and so nobody smuggles it in as part of the screen.

### 8.5 What must never be reported as evidence

`CR` or candidate-better on `ΔB` for `T_B`, or on `ΔE` for `T_E` (§5). "`T_B`
raises system throughput on `X` % of deviations" and "`T_E` reduces system energy
on `X` % of deviations" are the same forbidden statement in prose.

---

## 9. Compute cost, from the existing measured figures only

No new measurement. All inputs are [R]; the products are [D].

**Measured inputs.** `T_DELTA` needs `1 + Σ_u (1 + |legal_u|)` evaluations per
step — the 2,801 / 2,901 bounds assume `|legal| = 27 / 28`, and the realised
collections averaged 26.371 legal actions, i.e. **2,738 evaluations per step**
[D] (657,145 over 240 steps [R]). Per-evaluation wall on `sat`, `nice -n 16`, one
BLAS thread: **0.008698 s** was Lane Q's pre-launch smoke figure and the basis of
its projection; **realised** was 0.007846 s (Lane Q) and ≈ 0.00781 s (B0's S
collection, 657,145 evaluations in 5,133 s summed shard wall [D]), with B0's
parity arm at 9.47 ms. The tables below use the conservative **8.698 ms**, which
overstates the realised cost by ~11 %. Local WSL2 was measured at 0.025849 s,
**2.97× `sat`**.

**`T_B` and `T_E` are cheaper than `T_DELTA` and free relative to each other.**
They need no without-`u` evaluation (§3.2), so their object is
`1 + Σ_u |legal_u|` — identical to `T_TAIL`'s, which realised **2,624.9
evaluations per step** at mean 26.239 legal actions [R]; at `T_DELTA`'s mean of
26.371 the same object is **2,638 per step** [D], a 3.7 % saving on `T_DELTA`'s
2,738. And because both are argmax/argmin over the *same* candidate arrays,
**scoring both costs one pass, not two**; `T_DELTA` can be scored from the same
arrays as well, at zero extra evaluations, which is what makes the §8.2
closed-source pre-gate free.

| item | evaluations | single-threaded CPU @ 8.698 ms | elapsed, 4 `sat` shards |
|---|---:|---:|---:|
| one 24-episode / 240-step P0 collection, **`T_B` + `T_E` + `T_DELTA` together** | ≈ 630,000 | **≈ 1.52 h** | **≈ 23 min** |
| clone fits: 2 candidates × BC, + 1 fitted T0-imitation control (analytic control is free) | — | ≈ 1 min | ≈ 1 min |
| **minimum complete round under Amendment 15 §5** | **≈ 630,000** | **≈ 1.5 h** | **≈ 25 min** |
| optional standalone joint-rollout diagnostics, one per candidate (**not** required by §5) | ≈ 1,260,000 | ≈ 3.0 h | ≈ 46 min |
| **round with both diagnostics** | ≈ 1,890,000 | **≈ 4.6 h** | **≈ 70 min** |

Same figures on this local WSL2 box, at the measured 2.97×: **≈ 4.5 h** minimum,
**≈ 13.6 h** with diagnostics. If §7.3's analytic `ΔE` path verified, `T_E` alone
would drop to order 100 evaluations per step — but `T_B` would still carry the
full 2,625, so a joint pass saves nothing and only a `T_E`-only round would
benefit.

**Cost is not the reason to decline this round.** One and a half CPU-hours is
less than a single Lane-M arm. The reasons are in §6 and §10.

---

## 10. Assessment and recommendation

**Recommendation: do not run this decomposition as a third-Catfish round.** Stated
as an assessment, not a proposal, and with the specific reasons the a2 directive
asked for.

**`T_B`** — well-defined, cheap, physically meaningful, and the wrong half. It is
`T_DELTA` with the observable term deleted and the non-representable term kept
whole (§6.2). `T_DELTA`'s clone already cleared its own trivial baseline by
+0.010 to +0.021 and agreed with T0 roughly twice as often as its teacher did
(§6.1). There is no mechanism by which removing the energy term improves that.
It would inherit the arithmetic-identity property exactly (§5) and the
representability failure with interest.

**`T_E`** — well-defined only in a sense that should not satisfy anybody. Taken
literally it is decided by an exact-tie set and the action-slot index ordering,
which Amendment 15 §2A explicitly refuses as a physical identity (§3.4). Repaired
with the only no-new-constant tie-break available, it becomes "T0 restricted to
the minimum-marginal-energy actions" — the exact structural shape whose clone
collapsed toward T0 and landed 0.125 *below* its own trivial baseline in
`T_TAIL`'s closure — and its already-measured deployable analogue
`B1_NO_NEW_BEAM` sits at disagreement 0.2567, EE/T0 0.8877, p10/T0 0.3200, 0.638
of the condition-5 floor, dominated by T0, and has already served as the CF3
pilot's discarded C3 source (§6.3).

**The decomposition as a whole** does not escape what killed `T_DELTA`, because
what killed `T_DELTA` was not the mixing coefficient. T0 is itself a crude
scalarisation of exactly `(T_B, T_E)` with `c = 1` (§4). The genuinely novel
content of each half is the cross-user externality, and that content is absent
from all 113 dimensions of the deployed observation by construction — which is
precisely the sentence the `T_DELTA` closure already published as its finding.

**And this bisection has already been rejected once on measured evidence.**
Stage 0 prospectively specified, measured and rejected the same split of T0 into
a pure-bits endpoint and a pure-energy endpoint, ruling that "the `c = 1`
mixture, not either term, is where the value sits" (§6.4). The cause of that
rejection is criterion-level, not information-level, so it plausibly transfers to
the counterfactual version. The one way it might not — that a single-term
criterion which internalises the externality could own a state subset its local
analogue does not — depends entirely on information that `T_DELTA`'s screen
measured as not reaching the student. Both halves of the case therefore point the
same way.

**What is worth keeping from this note if the round is never run:**

* the retrospective `T_TAIL`-standard reading of `T_DELTA` (§6.1), which shows the
  two closures agree on one mechanism — collapse toward T0 — and strengthens the
  paper's negative finding rather than adding to it;
* the observation that the credit module never fuses `ΔB` and `ΔE`, so the
  decomposition costs one deleted multiplication (§2.3) — useful to any future
  reader who assumes it would be a re-implementation;
* the baseline-cancellation result (§3.2), which retires the without-`u`
  evaluation and the whole cheap-baseline question for any future argmax-over-one-
  term source;
* the tautology-avoidance design (§5.1) and the `A_repr`-with-trivial-baseline
  protocol (§8.3), which apply to **any** future source screen, not just this one.

**If the owner authorises a round anyway**, §8 is the design, §9 is the budget
(≈ 1.5 CPU-hours minimum), and §8.2's pre-gates should be read first, because two
of them can end it in the first twenty minutes for a fraction of the cost of
discovering the same thing at `A_repr`.

---

## 11. Boundary — what this lane did not do

* **No candidate outcome of any kind was collected.** No P0 collection, no
  disagreement measurement, no `A_repr` fit, no clone, no rollout, no scoring of
  any candidate. No script in any worktree was executed. No environment was
  constructed and no episode was rolled.
* **No learner training and no optimizer step**, of any kind, including
  measurement-instrument clones.
* **No new threshold, constant, coefficient, factor or gate** was invented,
  proposed, tuned or implied. Every quantity named here is pre-existing: `η₀`, the
  0.25 distinctness line, the 0.50 `A_repr` floor, the served ≥ 0.995 / bits ≥ 0.95
  / p10 ≥ 0.5× non-degeneracy checks, the `E_max` outage charge, and the
  first-index tie rule.
* **No source was admitted, closed or ranked.** `T_DELTA`, `T_H` and `T_TAIL`
  remain closed; `T_NEXT` remains the admitted sole survivor; the portfolio
  remains sealed to three families under Amendment 15 §1.
* **Amendment 11 is not touched.** Neither `T_B` nor `T_E` introduces an absolute
  rate threshold, a target-SINR inversion, an ACM table, an `R_min`, a demand cap
  or any demand model; both are argmax/argmin of quantities the environment
  already computes. C-2 / PATCH P-22 stays closed.
* **No `sat` compute.** No `sat` workspace was created, read or written; no `sat`
  process was started; Lane M's five concurrent k = 8 arms were not contended
  with. Work was local and read-only.
* **No write outside the main tree.** `/home/u24/papers/mcrl-leo-handover-cf2s-multi`
  and every `-cf2s*`, `-dev`, `-b1`, `-cf3` worktree were **read only**. This lane
  wrote exactly two files, both in the main tree:
  `.scratch/catfish2-successor/CF3-PREP-DESIGN-NOTE-2026-09-12.md` and
  `.scratch/catfish2-successor/PROGRESS-CF3-PREP.md`.
* **Formal S1 was not touched**: no formal, calibration or CONFIRM seed namespace
  was named, constructed or consumed, and no formal outcome was inspected.
