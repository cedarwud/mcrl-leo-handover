# Ruling — the four sibling concepts that survived, and what each is gated on

Date: 2026-09-10 ~18:50Z · Controller
Source: `SIBLING-CONCEPT-TRANSFER-2026-09-10.md` (`/home/sat/mcrl-v025-concepts-ws`) —
**44 concepts enumerated, 4 survive** a filter of nine measured facts about this physics.
Records job; no learner checkpoint read, no physics run.

## Two things it closed for free

**The off-axis defect is NOT shared.** The sibling's 2026-06-04 audit found its base channel
lacked off-axis, which **confounded** its `NO_A4_ADVANTAGE` verdict and its
"collapse is reward-optimal" framing. **V0.25's related sealed-v1 observation defect was
repaired in Q1 v2.** My lead was worth checking and it came back negative. Closed.

**Four objective variants are on record as tried and failed** over there, and the rejection
lines are the durable output: `kappa`-allocated per-user EE (**the ADR derives a reverse
incentive**), angle-aware EE as a reward variant, proportional-fair angle-aware EE, and
handover-aware EE. **Do not re-run these.**

## 1. ADOPT the direction — an additive contribution that closes exactly to pooled EE

Give every per-user term an additive contribution whose **sum is the instantaneous system EE**,
and report ratio-of-sums across time rather than a mean of instantaneous ratios.

**Why this is the top item.** It attacks the defect `BASIN2` measured directly: **the objective
does not track the metric** — first-improvement from `RSS_MAX` descends from `41.621560` to
`31.812902`, and the six-arm `F` order disagrees with the EE order. This project's decision
score is `sum_u delta(u, a(u)) + psi`. **If each `delta` closed to system EE, the sum would be
the metric rather than a proxy for it.**

**Gated on `ETAFIX`** (dispatched 18:40Z), which asks whether any `eta` makes the `F` order
match the EE order. **If some `eta` does, the defect is an exchange rate and this is not needed.
If none does, the defect is structural and this is the repair.** Those are mutually exclusive
and one job settles it.

**Not adopted blind:** the sibling's own status is "demonstrated to work **for algebraic and
runtime closure**; effectiveness was not established", and its ADR-003 is archived. Closure is
not efficacy.

## 2. ADOPT the cheap gate, not the bundle — supervised ranking before DQfD

The proposal is DQfD-style demonstrations from `RSS_MAX` with a large-margin ranking loss.
The demonstrator is project-local and already measured: **41.621560 Mbit/J at full 1200/1200
service, using strictly less information than the learned selector**, differing from `a0` on a
median **92.5/100** users with **every** differing choice at lower nominal gain.

**The report's own sequencing is right and I adopt it**: because the sealed head loses to plain
linear on level calibration in all three routes, **Q1 v3 plus a linear supervised ranking gate
is the cheaper first test**; the replay/pretrain/L2 bundle is justified only if that gate fails.

**Do not treat the sibling's DQfD failure as a veto.** It was measured on an obsolete load-only
contract that its own later record rules out for current-physics claims — ON `440.63` vs OFF
`523.78`, worse in 6/6 seeds, then invalidated. **A caution, not a verdict.**

**Q1 v3 stays regardless.** DQfD does not replace the feature; a demonstration loss cannot teach
a head to rank on a quantity it cannot see.

## 3. HOLD — joint-profile construction, deterministic before learned

Addresses the single-scalar interaction bottleneck and the 10.78% a jointly constructed profile
already beats the best per-user rule by. The sibling's status: **"cheap zero-learning
optimisation closed 64-82% of the gap"** — as an executor, not a learned win.

**Gated on `COORDVALUE`, `CEILING2` and `BEAMCOUNT`.** If coordination has no value at a good
operating point, or the ceiling saturates at `|A| <= 2`, this is answering the wrong question.

**And it changes the deployment boundary**, so it is disallowed outright if pure per-user
argmax is a project requirement. **That is an owner question, not mine**, and it must be
answered before any work starts, not after.

## 4. ADOPT the direction — per-option congestion context, replacing the single scalar

The interaction route currently reaches the decision as **one scalar** added to a sum over ~100
per-user terms. **A scalar added once cannot represent which candidate option caused which
occupancy-dependent consequence.** Option-indexed context can.

**The sibling's `chi` recovered only 0.4% of its coordination gain** — but it was tested there
as a de-collapse device, and this project **does not have that pathology**: `QCOLLINEAR` places
it on the repaired side of the scale, `+0.087`-`+0.208` above a measured `0.2735` independence
floor against the sibling's `+0.843`. **The structural argument transfers; the numerical result
does not.**

**Do not import the sibling's cap-specific "competitor rank" fields.** Derive only what this
project's own physics supports: `required_se = rate_target * occupancy / bandwidth` and the
1.65 W cap. Same boundary as Q1 v3's gain scalar, so the two compose.

## What this ruling does not do

**None of the four is authorised to run yet.** Three are gated on jobs already in flight, and
one is gated on an owner decision about the deployment boundary. Each creates a **successor**
arm; the sealed five-arm inventory is not mutated.

**And a caution the sweep earns**: 40 of 44 concepts were rejected, most because they address a
binding this project does not have. **That rejection ledger is the durable deliverable** — it
exists so this sweep is not run again.
