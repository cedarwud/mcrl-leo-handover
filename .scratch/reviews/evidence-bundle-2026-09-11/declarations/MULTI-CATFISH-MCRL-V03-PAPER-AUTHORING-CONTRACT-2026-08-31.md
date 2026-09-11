# Multi-Catfish MCRL V0.3 paper-authoring contract

Date: 2026-08-31  
Status: **C1/C3 authoring authority only; C2 V0.7 prose superseded after R14;
replacement C2 pending**

> **Authoring hold for C2 (2026-09-02).** Do not present the focal-next
> `motion-one` route below as the current or provisionally locked C2. R13 was
> compatible with zero and the later R14 held-out diagnostic failed against
> the strongest null in all three lineages. C1/C3 prose remains usable within
> its stated evidence boundary. Final three-route method prose waits for a new
> C2 headroom and observability pass.

This document is the paper-writing contract for Multi-Catfish MCRL V0.3. It is
subordinate to the current EE-axis contract and the current-authority index,
and is anchored to the canonical implementation in
`src/mcrl/algorithms/ee_axis_pairwise.py`. It is intended to let a paper
author write Chapters 4 and 5 without importing an archived V0.1/V0.2, R6,
R7, or SMC-ER story.

The main-text depth is governed by
`MULTI-CATFISH-MCRL-V03-PRESENTATION-LAYER-2026-08-31.md`. It preserves the
complete scientific method while moving implementation receipts, schema
fields, and audit mechanics to an appendix or artifact documentation.

## 1. Authority and scope

Use these sources in this order:

1. `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md`;
2. `docs/MULTI-CATFISH-EE-AXIS-REDESIGN-CONTRACT-V0.3-2026-08-31.md`;
3. `src/mcrl/algorithms/ee_axis_pairwise.py`;
4. the current Opus co-design and C3 formula-first census receipts.

The name remains **Multi-Catfish MCRL**. `SMC-ER` is not the method name in
V0.3. The endpoint is the unchanged Main-only ratio-of-sums energy efficiency
(EE):

\[
\eta^N=\frac{\mathcal B}{\mathcal E},\qquad
\mathcal B=\sum_t\sum_{u\in\mathcal U}R_u(t)\Delta t,\qquad
\mathcal E=\sum_t P^N(t)\Delta t.
\]

The design does **not** attempt to make three conflicting legacy rewards all
increase. The three routes are training-time views of one physical
counterfactual, and survive only if their combined deployed score improves
held-out Main-only ratio-of-sums EE while respecting the service guard.

## 2. Method in one paragraph

At a sealed predecision anchor, identify eligible users and select one focal
user by the largest signed-motion opportunity, breaking ties by the lowest
user index. Enumerate that user's native 28 legal action slots under the
native mask. Each slot defines a candidate branch \(C\) matched with Main
branch \(M\); C1 and C3 retain their opening views, while C2 records the focal
user's attributable EE surplus at the next slot. Opening rows are stored in
\(D^o\), C2 next-slot rows in \(D^t\), and held-out matched traces in \(D^a\)
are used only for evaluation and the scoped identity check. Three independent
online Q networks learn pairwise action advantages without Bellman bootstrapping
or target networks. At deployment, Q2 contributes only for that motion-selected
focal user, while one native-mask argmax still uses the unweighted `Q1+Q2+Q3`
score. There is no auction, coordinator, joint decoder, voting, pair-matching,
or post-training override.

## 3. Notation contract

Use one-letter primary symbols and one-letter superscripts/subscripts. A
long-form name may appear in prose once, but do not introduce multi-letter
mathematical aliases for the same quantity. Route labels `C1`, `C2`, `C3`
and dataset labels `D^o`, `D^t`, `D^a` are fixed interface labels.

| Symbol | Meaning | Unit or constraint |
|---|---|---|
| \(t\) | physical time-step index | integer |
| \(k\) | slot index in a matched physical comparison | \(0,1\) |
| \(u\) | focal user index | \(u\in\mathcal U\) |
| \(i\) | generic or non-focal user index | \(i\in\mathcal U\setminus\{u\}\) when non-focal |
| \(b\) | matched branch label | \(b\in\{C,M\}\) |
| \(s\) | satellite index | \(s\in\mathcal S\) |
| \(v\) | physical beam index | \(v\in\mathcal V\) |
| \(s_u(t)\) | deployed state of user \(u\) | versioned vector |
| \(a\) | generic legal action | \(a\in A_u(t)\) |
| \(A_u(t)\) | legal, service-safe action set of user \(u\) | may be empty |
| \(M\) | matched reference action/branch label | fixed at source generation |
| \(C\) | unilateral candidate action/branch label | differs first only at focal action |
| \(R_{u,s,v}(t)\) | physical link throughput | bit/s |
| \(R_u(t)\) | selected-link aggregate throughput of user \(u\) | bit/s |
| \(P^N\) | canonical network power; branch forms are \(P_M^N\), \(P_C^N\) | W |
| \(\mathcal B\) | delivered bits over the evaluation window | bit |
| \(\mathcal E\) | network energy over the evaluation window | J |
| \(\eta^N\) | network-level ratio-of-sums EE | bit/J |
| \(\lambda_0\) | frozen global calibration multiplier | bit/J |
| \(g_k\) | fixed-\(\lambda_0\) system surplus at offset \(k\) | bit |
| \(\zeta_{1,u}\) | C1 focal opening surplus | bit |
| \(\zeta_{2,u}\) | C2 focal next-slot attributable EE surplus | bit |
| \(\zeta_{3,u}\) | C3 non-focal opening rate externality | bit |
| \(p_{b,u}(1)\) | focal marginal network power at successor slot 1 on branch \(b\) | W |
| \(Q_j\) | route-\(j\) action-value surface | normalized surplus |
| \(j\) | route index | \(1,2,3\) |
| \(\Phi_u\) | deployment score for user \(u\) | normalized surplus |
| \(\Delta t\) | interval duration | s |
| \(\kappa\) | shared output scale | bit |
| \(n_0\) | decisions in the TRAIN-only scale-calibration window | positive integer |
| \(\beta\) | reference-action gauge coefficient | nonnegative |
| \(\nu_j\) | frozen route-\(j\) loss-dispersion scale | positive |
| \(w_j\) | route-\(j\) loss weight, \(w_j=1/\nu_j^2\) | positive; optimization only |
| \(\ell_j\) | route-\(j\) pairwise regression loss | nonnegative |
| \(D^o\) | opening source dataset | TRAIN/validation source |
| \(D^t\) | C2 focal next-slot source dataset | TRAIN/validation source |
| \(D^a\) | held-out scoped-identity dataset | held-out evaluation only |

The paper symbol \(\zeta_{j,u}\) maps to implementation receipt fields such
as `z1`, `z2`, and `z3`; those field names are not paper notation. Do not call
\(\zeta_{2,u}\) or \(\zeta_{3,u}\) “r2” or “r3” objectives. Legacy reward names are
historical context only. Do not reuse `θ` for a Catfish target; the antenna
angle remains an independent physical quantity elsewhere in the paper.

After the link-level throughput \(R_{u,s,v}\) is defined in Chapter 3, the
compact user-level rate used below is

\[
R_u(t)=\sum_{s\in\mathcal S}\sum_{v\in\mathcal V}
x_{u,s,v}(t)R_{u,s,v}(t).
\]

## 4. Fixed physical accounting

Before inspecting Catfish outcomes, compute one TRAIN-only calibration value:

\[
\lambda_0=\frac{\mathcal B_0^M}{\mathcal E_0^M}.
\]

The same floating-point value is used for every arm, window, head, and
candidate in a stage. For a matched candidate/reference pair:

\[
g_k=\Delta t\sum_{i\in\mathcal U}[R_i^C(k)-R_i^M(k)]
-\lambda_0\Delta t[P_C^N(k)-P_M^N(k)].
\]

Candidate and reference schedules are sealed before any outcome is read, and
use the same canonical multi-user physics and branch-independent matched
random field. The V0.2 isolated-world evaluator is not part of the target
path because it changed bandwidth, interference, load, beam activation, and
marginal energy conventions.

### C1/Q1: focal opening surplus

At `k=0`, only focal user `u`'s physical action differs. All opening energy
change is charged to the focal route:

\[
\zeta_{1,u}=\Delta t[R_u^C(0)-R_u^M(0)]
-\lambda_0\Delta t[P_C^N(0)-P_M^N(0)].
\]

C1 is the RIS-lineage Catfish route: retain EXP/ACRM experience generation
and private preparation. EXP/ACRM is a mechanism for producing and learning
from C1 experiences; it does not change the canonical EE endpoint and does
not create a second deployment controller.

### C3/Q3: non-focal opening externality

The same opening counterfactual also records the immediate rate effect on
everyone except the focal user:

\[
\zeta_{3,u}=\Delta t\sum_{i\in\mathcal U\setminus\{u\}}
[R_i^C(0)-R_i^M(0)].
\]

C3 is informed by lagged, predecision candidate-beam load, active state, and
maximum required link power. It then enumerates unilateral legal opening
actions at sealed anchors. These quantities are observations, not action
coordination. Opening shared activation and power changes remain in C1, so
C3 does not duplicate them and is invariant to `λ_0`.

### C2/Q2: focal next-slot attributable surplus (motion-one, provisional post-R13 amendment)

At each predecision anchor, select one eligible focal user \(u\) by the largest
signed-motion opportunity; ties go to the lowest user index. Enumerate the
native 28 legal action slots under the native mask. Each slot is compared as a
candidate branch \(C\) against matched Main branch \(M\), and the public C2
target keeps only the focal user's attributable effect at successor slot 1.

For \(b\in\{C,M\}\), define the focal marginal network power by

\[
p_{b,u}(1)=P_b^N(1)-P_{b,-u}^N(1),\qquad b\in\{C,M\}.
\]

The C2 target is

\[
\zeta_{2,u}=\Delta t[R_u^C(1)-R_u^M(1)]
-\lambda_0\Delta t[p_{C,u}(1)-p_{M,u}(1)].
\]

Signed, zero, and negative targets are retained, and each native legal slot is
enumerated once. Only \(Q_2\) is updated by these rows. This is a focal
next-slot target, not an all-user temporal aggregate. The motion-one rule is
provisionally locked after R13; the earlier D2 preregistration predates it and
does not validate this amendment.

### Scoped identity

The former full-window identity is retired. The scoped accounting identity is

\[
\zeta_{1,u}+\zeta_{3,u}+\zeta_{2,u}=g_0+g_{1,u}.
\]

Here \(g_{1,u}\) is the focal-attributable part of the successor surplus. Any
non-focal next-slot remainder is diagnostic only and supplies no gradient. This
identity establishes accounting consistency, not learnability or EE
improvement.

## 5. Source datasets and information flow

The source generator performs expensive counterfactual physics outside an
ordinary gradient step.

| Dataset | Contents | Learner use | Forbidden use |
|---|---|---|---|
| \(D^o\) | one opening matched pair per sealed anchor/action, storing \(\zeta_{1,u}\) and \(\zeta_{3,u}\) once plus common lineage | C1 updates \(Q_1\); C3 updates \(Q_3\) | recomputing or duplicating opening energy in C3 |
| \(D^t\) | matched C2 candidate/Main rows at successor slot 1, storing focal rate/power terms and \(\zeta_{2,u}\) under the native mask | C2 updates \(Q_2\) | mixing branch or source versions; dropping zero or negative rows |
| \(D^a\) | held-out matched traces with opening terms and the scoped focal next-slot identity | ratio-of-sums EE, identity, service, and generalization checks | any gradient, target calibration, or outcome-triggered refresh |

Every row binds the reference-policy version, `λ_0`, state schema, native
legal-action grammar, branch labels, physical IDs, and source lineage. C2 also
binds the selected focal user, native mask, successor-slot terms, and matched
candidate/Main identity. Positive, zero, negative, and all-dark outcomes are
retained.

The C2 public state is the predecision signed-motion opportunity together with
the native legal-action mask; implementation state details remain in the
reproducibility record. C3 needs lagged eligible served load, active-
beam/satellite state, and maximum required link power for each candidate beam.
The exact C3 dimension is `TBD` until its state-schema test verifies causality
and action-slot alignment.

## 6. Three independent learners

There are exactly three independent online Q networks:

\[
Q_1(s_u(t),a),\qquad Q_2(s_u(t),a),\qquad Q_3(s_u(t),a).
\]

They have no shared trainable parameters and no target networks. A route-
`j` row updates only `Q_j`; every other Q surface remains unchanged. Normalize all
targets with one shared scale:

\[
\widetilde\zeta_{j,u}=\frac{\zeta_{j,u}}{\kappa},\qquad
\kappa=\frac{\mathcal B_0^M}{n_0}.
\]

The Pilot-1 pairwise zero-bootstrap loss is:

\[
\ell_j=w_j\left(
[Q_j(s_u(t),a_u^C(t))-Q_j(s_u(t),a_u^M(t))
-\widetilde\zeta_{j,u}]^2
+\beta Q_j(s_u(t),a_u^M(t))^2\right).
\]

\(w_j=1/\nu_j^2\) may normalize optimization noise but does not change output
units. \(\kappa\), \(\nu_j\), and \(\beta\) are frozen on TRAIN-only calibration; the
initial proposed \(\beta\) is \(0.1\) and remains `TBD` until preregistration. Do not
add a redundant sum loss or mix this estimator with legacy Bellman maxima.
Old checkpoints are incompatible and cannot be resumed.

## 7. Deployment

At each Main decision, mask illegal or service-unsafe actions and perform one
combined argmax:

\[
\Phi_u(t,a)=Q_1(s_u(t),a)+Q_2(s_u(t),a)+Q_3(s_u(t),a),\qquad
a_u^\star(t)=\arg\max_{a\in A_u(t)}\Phi_u(t,a).
\]

Only this masked Main action executes. There is no sequential route vote, no
auction, no coordinator, no joint decoder, no pair matching at deployment,
and no post-training coordination or override. The scientific weights in the
deployed sum are exactly `(1,1,1)` because all heads share the same normalized
surplus unit.

## 8. Initial ablation contract

The first ablation set is fixed as follows. `M0` is the original MODQN and is
an independent reference, not a V0.3 head-equivalent control. The remaining
arms use the V0.3 three-Q topology and equal-budget source accounting.

| Arm | C1 source | C2 source | C3 source | Meaning |
|---|---|---|---|---|
| `M0` | legacy MODQN | legacy MODQN | legacy MODQN | independent historical reference |
| `N000` | neutral | neutral | neutral | three-head neutral-source control |
| `F111` | active `D^o` | active `D^t` | active `D^o` | full Multi-Catfish V0.3 |
| `A011` | neutral | active `D^t` | active `D^o` | C1 ablation |
| `A101` | active `D^o` | neutral | active `D^o` | C2 ablation |
| `A110` | active `D^o` | active `D^t` | neutral | C3 ablation |

In `N000` and every `A` arm, an ablated route still has its own `Q_j`,
optimizer, action surface, and deployment summand. Its source is replaced by
an equal-budget neutral source; the head is not removed and the score is not
renormalized. This isolates the value of the route without changing capacity,
update count, or the one-argmax deployment rule. Exact neutral-source
construction and threshold/quota/seed values are `TBD` until the pilot is
sealed.

## 9. Chapter 4 authoring plan

Use a compact reader-facing arc in the main chapter: one EE objective and
matched intervention; three non-overlapping contribution views; one concise
source-mechanism paragraph; route-local pairwise learning; and one masked
deployment action. Sections 4.1--4.6 below are the complete author checklist,
not a requirement that every item receive a separate main-text section or
slide. Gate ledgers, provenance fields, exact state additions, and
neutral-sampler mechanics belong in the reproducibility appendix.

Write Chapter 4 in the following order. Each paragraph should state both the
mechanism and its limitation.

### 4.1 Objective and causal counterfactual

Introduce unchanged ratio-of-sums EE, the fixed TRAIN-only `λ_0`, same-world
matched candidate/reference branches, and the reason the old isolated-world
split is excluded. State that legacy `r2`/`r3` are not current objectives.

### 4.2 Multi-Catfish axis decomposition

Define C1 as focal opening surplus, C3 as non-focal opening rate externality,
and C2 as the motion-selected focal user's next-slot attributable surplus.
Give the C2 marginal-power and focal-surplus equations and the scoped identity.
Explain that the roles are complementary accounting views, not three claims
that their raw targets must all increase.

### 4.3 Role-specific source generation

Describe `D^o`, `D^t`, and `D^a`. Explain C1 EXP/ACRM, C2's one-user signed-
motion selection and native 28-slot candidate/Main enumeration, and C3
lagged-load-informed unilateral enumeration. State that `D^a` is held out and
never contributes gradients.

### 4.4 Pairwise learner and independent Q surfaces

Give the shared-`κ` normalization, pairwise zero-bootstrap loss, gauge penalty,
route-diagonal update rule, no-target-network condition, and checkpoint
incompatibility with MODQN.

### 4.5 Single masked deployment

Give the summed score and one masked argmax. Explicitly state what is absent:
auction, coordination, joint decoder, voting, pair matching, and post-training
override.

### 4.6 Gates and reproducibility

Present the formula/source gates and the balanced R13 development result as
development evidence only. The provisional C2 core lock passed because the
aggregate mean and median and two of three lineage means were positive; the
result is recorded in
[`MULTI-CATFISH-MCRL-V07-C2-BALANCED-DEVELOPMENT-GATE-RESULT-2026-09-02.md`](MULTI-CATFISH-MCRL-V07-C2-BALANCED-DEVELOPMENT-GATE-RESULT-2026-09-02.md).
State that the b-lineage variability and a-lineage service loss require longer
trend and held-out validation. No development result is a formal efficacy
claim.
Thresholds and source rows remain sealed before any claim-bearing evaluation.

## 10. Claims that may and may not be written

### Permitted now

- “We propose Multi-Catfish MCRL V0.3, a three-route fixed-horizon EE-surplus
  learner.”
- “The C1/C3 opening views and focal-next C2 view use one matched physical
  intervention; their scoped identity is accounting evidence only.”
- “C1, C2, and C3 represent focal-now, motion-selected focal-next, and
  non-focal-now effects, respectively.”
- “C3 has formula-first unilateral physical opportunity in the current
  single-seed census; this is not a learned efficacy result.”
- “The balanced R13 C2 screen is development evidence for a provisional core
  lock, not Q2 learnability, formal efficacy, or EE improvement.”
- “The deployment policy is one masked argmax of three independent online Q
  surfaces.”

### Forbidden until held-out matched ablations pass

- “The method improves EE,” “C2/C3 increase EE,” or any numerical improvement
  claim.
- “All three rewards improve,” “the objectives are jointly optimized,” or
  “r2/r3 are preserved objectives.”
- Any C1-negative or C2/C3-positive interpretation of the void 10EP
  directional flags.
- “The oracle census proves the learned Q3/Q2 works.”
- Any post-training auction, coordinator, joint action, voting, or override
  claim.
- Any result, threshold, quota, state dimension, learning rate, or `β` value
  not present in a sealed receipt.

## 11. Chapter 5 placeholder

Do not invent numbers. Replace the following placeholders only with sealed
receipts from matched Main-only evaluation:

| Placeholder | Required content |
|---|---|
| `TBD-5.1` | dataset split, physical IDs, horizon, random-field version |
| `TBD-5.2` | state dimension and schema digest |
| `TBD-5.3` | `λ_0`, `κ`, learning rate, `β`, batch/update schedule |
| `TBD-5.4` | training seeds and checkpoint cadence (every 100 episodes) |
| `TBD-5.5` | EE curves for `M0`, `N000`, `F111`, `A011`, `A101`, `A110` |
| `TBD-5.6` | ratio-of-sums EE, service/outage guard, confidence intervals |
| `TBD-5.7` | head pivotality, target distributions, censored incidence |
| `TBD-5.8` | failure analysis and gate outcomes |

The current authority is training **NO-GO**. No 1500/3000/9000-episode result
may be described as available from this contract. Before any 9000-episode run,
the user must be notified; every eventual run checkpoints every 100 episodes.

## 12. Fresh-reader acceptance test

A reader who has not seen the archived documents must be able to answer:

1. **What are the three Q routes?** C1/Q1 focal opening surplus, C2/Q2
   motion-selected focal next-slot attributable surplus, and C3/Q3 non-focal
   opening rate externality.
2. **What does each Catfish do?** C1 uses RIS EXP/ACRM experience generation;
   C2 selects one focal user by predecision signed-motion opportunity, ties to
   the lowest user index, and enumerates that user's native 28 legal slots
   against Main; C3 uses lagged load/activation/power observations and
   unilateral legal-action enumeration.
3. **How are data split?** \(D^o\) stores opening \(\zeta_{1,u}\) and
   \(\zeta_{3,u}\) once, \(D^t\) stores C2 focal next-slot rows, and held-out
   \(D^a\) stores the scoped identity without gradients.
4. **How is deployment done?** Select at most one focal user per predecision
   state; Q2 affects only that user, whose action uses the unweighted
   service-masked argmax of `Q1+Q2+Q3`.
5. **What do the ablations mean?** `M0` is independent legacy MODQN;
   `N000/F111/A011/A101/A110` retain all three heads and replace selected
   route sources with equal-budget neutral sources.
6. **What is the claim ceiling?** Formula-first accounting and physical
   opportunity are not EE efficacy; only held-out matched ratio-of-sums EE
   ablations can establish improvement.

If any answer is ambiguous, revise the paper text or figure handoff before
calling the method camera-ready.
