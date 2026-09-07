# Multi-Catfish MCRL V0.3 paper-authoring contract

Date: 2026-08-31  
Status: **current authoring contract; formula-first candidate; no training or efficacy claim**

This document is the paper-writing contract for Multi-Catfish MCRL V0.3. It is
subordinate to the current EE-axis contract and the current-authority index,
and is anchored to the canonical implementation in
`src/mcrl/algorithms/ee_axis_pairwise.py`. It is intended to let a paper
author write Chapters 4 and 5 without importing an archived V0.1/V0.2, R6,
R7, or SMC-ER story.

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

At a sealed anchor, make one focal physical action differ between a candidate
branch and a matched reference branch in the same multi-user world. A frozen
TRAIN-only multiplier converts energy changes to bit-equivalent surplus. The
opening interval is split into a focal net-surplus route (C1/Q1) and a
non-focal immediate-rate-externality route (C3/Q3); all later intervals are a
temporal continuation route (C2/Q2). Opening data are generated once and
stored in \(D^o\), temporal data in \(D^t\), and held-out full traces in \(D^a\) are
used only for evaluation and identity checks. Three independent online Q
networks learn pairwise action advantages without Bellman bootstrapping or
target networks. At deployment, one service-masked argmax selects the action
from `Q1+Q2+Q3`. There is no auction, coordinator, joint decoder, voting,
pair-matching, or post-training override.

## 3. Notation contract

Use one-letter primary symbols and one-letter superscripts/subscripts. A
long-form name may appear in prose once, but do not introduce multi-letter
mathematical aliases for the same quantity. Route labels `C1`, `C2`, `C3`
and dataset labels `D^o`, `D^t`, `D^a` are fixed interface labels.

| Symbol | Meaning | Unit or constraint |
|---|---|---|
| \(t\) | physical time-step index | integer |
| \(k\) | offset within a matched horizon | \(0,\ldots,H^c-1\) |
| \(u\) | focal user index | \(u\in\mathcal U\) |
| \(i\) | generic or non-focal user index | \(i\in\mathcal U\setminus\{u\}\) when non-focal |
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
| \(\zeta_{2,u}\) | C2 downstream temporal surplus | bit |
| \(\zeta_{3,u}\) | C3 non-focal opening rate externality | bit |
| \(Q_j\) | route-\(j\) action-value surface | normalized surplus |
| \(j\) | route index | \(1,2,3\) |
| \(\Phi_u\) | deployment score for user \(u\) | normalized surplus |
| \(H^c\) | matched counterfactual horizon length | positive integer; Pilot 1 uses \(H^c=4\) |
| \(\Delta t\) | interval duration | s |
| \(\kappa\) | shared output scale | bit |
| \(n_0\) | decisions in the TRAIN-only scale-calibration window | positive integer |
| \(\beta\) | reference-action gauge coefficient | nonnegative |
| \(\nu_j\) | frozen route-\(j\) loss-dispersion scale | positive |
| \(w_j\) | route-\(j\) loss weight, \(w_j=1/\nu_j^2\) | positive; optimization only |
| \(\ell_j\) | route-\(j\) pairwise regression loss | nonnegative |
| \(D^o\) | opening source dataset | TRAIN/validation source |
| \(D^t\) | temporal source dataset | TRAIN/validation source |
| \(D^a\) | held-out full-identity dataset | held-out evaluation only |

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

### C2/Q2: downstream temporal surplus

C2 uses a departure temporal fork. At the predecision point, the rule first
uses the incumbent hold action when it is legal; otherwise it uses the legal
non-Main rival with maximum predecision `candidate_sinr`, evaluated against
the previous-step radiating set. Ties use physical ID then action ID. The branch is
sealed before outcomes are evaluated. The continuation policy is branch-local
and frozen for the matched horizon. The candidate holds while its opening key
remains uniquely legal in its own contemporaneous predecision table. At the
first support-expiry offset it releases monotonically to complete branch-local
Main, without reading future offsets, the reference branch, or any outcome.
For \(k=1,\ldots,H^c-1\):

\[
\zeta_{2,u}=\sum_{k=1}^{H^c-1}\left\{
\Delta t\sum_{i\in\mathcal U}[R_i^C(k)-R_i^M(k)]
-\lambda_0\Delta t[P_C^N(k)-P_M^N(k)]\right\}.
\]

The four-offset fork therefore includes offsets `1`, `2`, and `3`; omitting
the planned or support-triggered release offset is incorrect. C2 captures hold, switch, release,
recurrence power, interruption, and future availability. Under canonical
fading, the branch-independent keyed common-random field is mandatory. The
sealed fixed-hold gate is `INDETERMINATE`; its 5/5 positive-seed headroom
signal is not a learnability or efficacy claim. The reactive-release amendment
is implemented in the isolated V0.3B path with 256/256 targeted tests passing;
its fresh-seed physical-headroom gate remains unsealed.

### Non-overlap identity

The decomposition is exact bookkeeping for one matched physical world:

\[
\zeta_{1,u}+\zeta_{3,u}+\zeta_{2,u}=\sum_{k=0}^{H^c-1}g_k.
\]

This identity establishes accounting correctness only. It does not establish
learnability or EE improvement.

## 5. Source datasets and information flow

The source generator performs expensive counterfactual physics outside an
ordinary gradient step.

| Dataset | Contents | Learner use | Forbidden use |
|---|---|---|---|
| \(D^o\) | one opening matched pair per sealed anchor/action, storing \(\zeta_{1,u}\) and \(\zeta_{3,u}\) once plus common lineage | C1 updates \(Q_1\); C3 updates \(Q_3\) | recomputing or duplicating opening energy in C3 |
| \(D^t\) | sealed departure temporal fork, hold-or-max-lagged-SINR-rival predecision, hold-while-legal release policy, matched offsets \(1,\ldots,H^c-1\), storing \(\zeta_{2,u}\), release offset/reason, and held-key match counts | C2 updates \(Q_2\) | mixing policy-version rows silently; dropping expiry or negative traces |
| \(D^a\) | held-out full-identity matched traces with all offsets and raw physical totals | ratio-of-sums EE, identity, service, and generalization checks | any gradient, target calibration, or outcome-triggered refresh |

Every row binds the reference-policy digest, `λ_0`, state schema, legal-action
grammar, horizon, random-field version, and physical IDs. C2 additionally
binds its release offset/reason and per-offset held-key match count. Positive,
zero, negative, all-dark, and genuinely right-censored outcomes are retained.
Downstream held-key expiry triggers the V0.3B monotone release and is
not silently dropped, imputed, or censored.

The minimum causal state additions are versioned together with replay and
checkpoints. C2 needs previous recurrence power, current-to-segment-start
gain ratio, segment age, and a no-previous-association/incumbent-outside-table
bit. C3 needs lagged eligible served load, active-beam/satellite state, and
maximum required link power for each candidate beam. The exact dimension is
`TBD` until the state-schema test verifies causality and action-slot alignment.

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

Write Chapter 4 in the following order. Each paragraph should state both the
mechanism and its limitation.

### 4.1 Objective and causal counterfactual

Introduce unchanged ratio-of-sums EE, the fixed TRAIN-only `λ_0`, same-world
matched candidate/reference branches, and the reason the old isolated-world
split is excluded. State that legacy `r2`/`r3` are not current objectives.

### 4.2 Multi-Catfish axis decomposition

Define C1 as focal opening surplus, C3 as non-focal opening rate externality,
and C2 as every downstream temporal surplus. Give the three equations and
the exact identity. Explain that the roles are complementary accounting axes,
not three claims that their raw rewards must all increase.

### 4.3 Role-specific source generation

Describe `D^o`, `D^t`, and `D^a`. Explain C1 EXP/ACRM, C2 hold-or-max-lagged-SINR-rival
opening followed by hold-while-legal monotone release, and C3
lagged-load-informed unilateral enumeration. State that
`D^a` is held out and never contributes gradients.

### 4.4 Pairwise learner and independent Q surfaces

Give the shared-`κ` normalization, pairwise zero-bootstrap loss, gauge penalty,
route-diagonal update rule, no-target-network condition, and checkpoint
incompatibility with MODQN.

### 4.5 Single masked deployment

Give the summed score and one masked argmax. Explicitly state what is absent:
auction, coordination, joint decoder, voting, pair matching, and post-training
override.

### 4.6 Gates and reproducibility

Present P1-P4 and G-C3/G-C2/G-D/G-O as formula-first gates. State that the
fixed-hold keyed C2 gate is sealed `INDETERMINATE`, the reactive-release
implementation/test gate is complete but its fresh physical-headroom gate is
pending, thresholds and seeds are sealed before gate runs, and source rows
bind all lineage fields.

## 10. Claims that may and may not be written

### Permitted now

- “We propose Multi-Catfish MCRL V0.3, a three-route fixed-horizon EE-surplus
  learner.”
- “The three targets form an exact non-overlapping accounting partition under
  one frozen multiplier and one matched physical world.”
- “C1, C2, and C3 represent focal-now, everyone-later, and non-focal-now
  effects, respectively.”
- “C3 has formula-first unilateral physical opportunity in the current
  single-seed census; this is not a learned efficacy result.”
- “The deployment policy is one masked argmax of three independent online Q
  surfaces.”

### Forbidden until held-out matched ablations pass

- “The method improves EE,” “C2/C3 increase EE,” or any numerical improvement
  claim.
- “All three rewards improve,” “the objectives are jointly optimized,” or
  “r2/r3 are preserved objectives.”
- “C2 passed viability” before the reactive-release source grammar
  passes its own fresh-seed gate.
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
   downstream temporal surplus, and C3/Q3 non-focal opening rate externality.
2. **What does each Catfish do?** C1 uses RIS EXP/ACRM experience generation;
   C2 evaluates a hold-or-max-lagged-SINR-rival opening and releases
   monotonically to branch-local Main when support expires; C3 uses
   lagged load/activation/power observations and unilateral legal-action
   enumeration.
3. **How are data split?** \(D^o\) stores opening \(\zeta_{1,u}\) and
   \(\zeta_{3,u}\) once, \(D^t\) stores \(\zeta_{2,u}\), and held-out \(D^a\)
   stores full identity traces without
   gradients.
4. **How is deployment done?** Three independent online Q networks feed one
   service-masked argmax of `Q1+Q2+Q3`.
5. **What do the ablations mean?** `M0` is independent legacy MODQN;
   `N000/F111/A011/A101/A110` retain all three heads and replace selected
   route sources with equal-budget neutral sources.
6. **What is the claim ceiling?** Formula-first accounting and physical
   opportunity are not EE efficacy; only held-out matched ratio-of-sums EE
   ablations can establish improvement.

If any answer is ambiguous, revise the paper text or figure handoff before
calling the method camera-ready.
