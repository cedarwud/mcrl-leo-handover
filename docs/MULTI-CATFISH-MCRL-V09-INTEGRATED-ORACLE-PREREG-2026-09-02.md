# Multi-Catfish MCRL V0.9 integrated C2/C3 oracle preregistration

Date: 2026-09-02  
Status: **FORMULA FROZEN BEFORE OUTCOME; NO LEARNER OR TEST SPLIT**  
Decision source: independent `gpt-dr.md` review plus `gpt.pdf` adjudication  
Next decision token if this gate is opened: `PASS_ORACLE_GATE` or
`FAIL_ORACLE_GATE`

## 1. Purpose and claim ceiling

This contract tests one narrow development hypothesis: with C1 held exactly
fixed, can an exact projected-persistence C2 and an action-caused non-focal
physical C3 each add a positive marginal to the same three-head policy under
one unweighted decoder?

This is a no-training oracle falsification on one previously unopened TRAIN
world. A pass is permission to design the learners and short-episode protocol;
it is not learned-policy evidence, held-out evidence, or an efficacy result.

The old learned Q2 and the old lagged victim-burden Q3 are forbidden from every
score and action in this gate.

## 2. Invariants

The following are unchanged:

- canonical final metric
  \(\eta^N=\mathcal B/\mathcal E\), evaluated as a ratio of sums;
- exactly three action-value surfaces \(Q_1,Q_2,Q_3\);
- one common Boolean safe mask \(A_u(t)\);
- direct left-to-right sum
  \(\Phi_u(t,a)=Q_1(s_u(t),a)+Q_2(s_u(t),a)+Q_3(s_u(t),a)\);
- one masked `argmax` and one executed Main action;
- frozen \(\lambda_0\), shared \(\kappa\), TLE data, native D2 clock,
  beam/power/interference equations, and Main-reference convention;
- no coordinator, auction, vote, route weight, sign flip, second decoder, or
  post-training correction.

## 3. C1: frozen opening focal-energy view

C1 is not redesigned. Its numerical \(\lambda_0\) is retained bit-for-bit.
The correct provenance is the existing one-episode TRAIN calibration using the
\(r_1\)-greedy Main-network policy with weights \((1,0,0)\); older prose that
attributes it to \((0.5,0.3,0.2)\) is documentation drift, not permission to
recompute it.

For focal user \(u\), candidate branch \(C\), and Main reference branch \(M\),
the public C1 quantity remains

\[
\zeta_{1,u}
=\Delta t\,[R^C_u(0)-R^M_u(0)]
-\lambda_0\Delta t\,[P^N_C(0)-P^N_M(0)].
\]

## 4. C2: exact projected persistence, version 1.1

Let

\[
H_t=\min\{3,T-1-t\}.
\]

For a legal candidate \(a\), opening service is

\[
o_{u,0}(a)
=\mathbf 1\!\left\{
p^0\frac{G^T_{u}(t_0,a)}{G^T_{u}(t,a)}\le p^{m}
\right\},
\]

with null gain and any execution-infeasible opening mapped to zero. Here
\(p^{m}\) denotes the beam RF-power ceiling; the superscript is kept to one
letter under the active notation rule. For future offset \(h\),
\(\rho_{u,h}(a)\) is the unchanged conjunction of exact native D2 eligibility,
physical cell-centre visibility, positive gain, and recurrence power
feasibility. Persistence is now

\[
\chi_{u,h}(a)=o_{u,0}(a)\prod_{r=1}^{h}\rho_{u,r}(a).
\]

The raw future term is

\[
e_{2,u,h}(a)=
\chi_{u,h}(a)\Delta t
\left[\widehat R_{u,h}(a)-\lambda_0\widehat P_{u,h}(a)\right]
-[1-\chi_{u,h}(a)]\kappa .
\]

For \(H_t>0\),

\[
X_{2,u}(a)=\frac{1}{H_t}\sum_{h=1}^{H_t}e_{2,u,h}(a),
\qquad
Q_2^\circ(s_u(t),a)
=\frac{X_{2,u}(a)-X_{2,u}(a_u^M)}{\kappa}.
\]

At \(H_t=0\), the C2 surface is zero. If \(o_{u,0}(a)=0\), every valid
future offset uses the existing \(-\kappa\) branch; later geometry cannot
resurrect the segment.

No other C2 formula, projection, constant, or support rule may change.

## 5. C3: projected non-focal externality

### 5.1 Physical counterfactual

For each focal user \(u\), freeze one committed non-focal service background
at the live predecision anchor. At offset \(h\), let \(B^{-u}_{t,h}\) be the
same fail-closed background in both branches. It retains each non-focal
association and segment, uses the native TLE/D2 clock, deterministic unit
fading/zero shadowing, recurrence power, max-per-beam RF power, beam load, and
canonical interference equations. A non-focal segment that becomes
infeasible is absorbing and cannot reappear.

Let \(F_{u,h}(a)\) be the focal physical segment. It exists only when C2's
opening/persistence receipt says that candidate \(a\) is active. The sole
branch difference is

\[
B^{-u}_{t,h}
\quad\hbox{versus}\quad
B^{-u}_{t,h}\oplus F_{u,h}(a).
\]

For the non-focal user index \(i\ne u\), define

\[
e_{3,u,h}(a)
=\Delta t\sum_{i\ne u}
\left[
\widehat R^C_{i,h}(a)-\widehat R^M_{i,h}
\right].
\]

Every sign is retained. Normally the insertion effect is non-positive; a less
harmful action becomes relatively preferable only after Main centering. C3
contains no focal rate, energy, handover reward, or second outage term.

### 5.2 Time aggregation and gauge

The direct adjudication's aggregation is frozen:

\[
X_{3,u}(a)=
\begin{cases}
e_{3,u,0}(a)+\dfrac{1}{H_t}\displaystyle\sum_{h=1}^{H_t}e_{3,u,h}(a),
&H_t>0,\\[6pt]
e_{3,u,0}(a),&H_t=0,
\end{cases}
\]

\[
\zeta_{3,u}(a)=X_{3,u}(a)-X_{3,u}(a_u^M),
\qquad
Q_3^\circ(s_u(t),a)=\frac{\zeta_{3,u}(a)}{\kappa}.
\]

The alternative \((H_t+1)^{-1}\sum_{h=0}^{H_t}e_{3,u,h}\) from the deep-
research report is not used in this gate. This is a pre-outcome formula choice,
not an outcome-responsive rescaling.

### 5.3 C3 state/source boundary for a later learner

No learner is trained here. If the oracle gate passes, the C3 learner input
must be action-aligned and decision-time only. It may include candidate
identity, same-beam non-focal count and delivered-bit burden, cochannel victim
and susceptibility summaries, committed beam RF maxima, focal-to-maximum gap,
new-beam/new-satellite indicators, and the exact opening/persistence
descriptors. It may not read a realised current joint action, successor
outcome, another arm's action, future policy action, final EE, or target sign.

Fresh TRAIN Catfish anchors must later be selected by fixed, outcome-blind
physical strata. All legal actions and all target signs are retained.

## 6. Integrated gate design

### 6.1 Fixed world and arms

- split: TRAIN only;
- evaluation seed: `2026104501`;
- initialization lineages: `2026092101`, `2026092102`, `2026092103`;
- episode length: 10 decisions;
- arms per lineage: four;
- total episodes: 12;
- every arm starts from a fresh environment;
- one keyed random field is shared by all arms of the world and excludes arm
  and lineage labels from its key.

The arms are

\[
\begin{aligned}
\Phi^F_u &= Q_{1,u}+Q^\circ_{2,u}+Q^\circ_{3,u},\\
\Phi^2_u &= Q_{1,u}+Q^\circ_{3,u},\\
\Phi^3_u &= Q_{1,u}+Q^\circ_{2,u},\\
\Phi^1_u &= Q^\circ_{2,u}+Q^\circ_{3,u}.
\end{aligned}
\]

Here superscripts \(F,1,2,3\) are single-character arm labels: full,
drop-C1, drop-C2, and drop-C3 are named in prose. Summation order is exactly
the written left-to-right order. Every surface uses one common safe mask.

### 6.2 Binding outcome rule

For each drop index \(j\in\{1,2,3\}\), define the canonical ratio-of-sums
contrast between the full arm and the arm that omits head \(j\).

The gate passes only if all conditions hold:

1. pooled \(\eta^N_F>\eta^N_j\) for every \(j\);
2. each contrast is positive in at least two of three lineages;
3. pooled full-arm served user-steps are not lower than each comparator;
4. service is noninferior in at least two of three lineage contrasts.

One pooled user-step shortfall is a failure. No confidence interval, surrogate
surplus, or diagnostic can rescue a failed binding rule.

### 6.3 Hard stops

Stop without expanding seeds if any of the following occurs:

- contract, source, schema, world, keyed-field, mask, or reference mismatch;
- a nonfinite surface or a nonzero Main-reference row after centering;
- a stale/inconsistent committed background or hidden live-state mutation;
- any TEST access, learner/optimizer update, old-Q2/old-Q3 query, future-policy
  query, or action crossing;
- any binding EE or service rule fails;
- C3 has zero legal-action spread throughout the world;
- adding C3 never changes an action relative to its drop-C3 comparator;
- the C2 and C3 opening-service gates disagree.

No sign, scale, seed, horizon, threshold, outage term, \(\lambda_0\),
\(\kappa\), source stratum, or acceptance rule may be changed after an outcome
is opened.

## 7. Required receipts and nonbinding diagnostics

Persist raw per-episode and per-step delivered bits, energy, served counts,
actions, EE, world identity, random-field identity, Q1 checkpoint hash, C2/C3
anchor/projection/surface hashes, mask hashes, action-flip counts, and
lineage/pooled margins.

Two diagnostics are mandatory but cannot rescue acceptance:

1. At (t\in\{1,4,7\}), compare the C3 opening shadow's action ordering
   with a true matched one-step non-focal externality under the current arm's
   fixed non-focal actions. At each scheduled step use, in increasing user-ID
   order, up to the first four users having at least four legal actions. For
   each user compare the selected arm action with the three smallest-index
   other legal actions. Persist pairwise agreement, Spearman rank agreement,
   and top-action agreement. This measurement is nonbinding, but the merged
   gate must expose at least one comparable sample.
2. At the same scheduled steps, give each user its highest-(Q_3^\circ)
   legal action other than the arm-selected action, breaking ties by the
   smallest native action index. Group those proposals by physical beam and
   select the lexicographically first beam having exactly two or three users.
   In the current arm's selected-action background, remove that group and
   then reinsert its members unilaterally and jointly. Record

   \[
   I=\Delta B^J-\sum_u\Delta B^U_u,
   \]

   where \(J\) is the joint realised non-focal-bit change and \(U\) denotes
   unilateral shadows. The merged gate must expose at least one evaluable
   sample. A single reversal is recorded but is not fatal; a strict majority
   (more than 50%) of evaluable scheduled samples reversing direction is the
   pre-outcome definition of systematic reversal and blocks the learner.

Unscheduled steps are recorded as such and are not failures. Missing
scheduled samples do not individually fail when another scheduled sample is
evaluable, but zero merged exposure for either diagnostic fails closed.

## 8. Execution order

1. formula and adapter unit tests;
2. runner/static receipt tests;
3. seal this contract plus all source/schema hashes;
4. run the 12-episode oracle gate on the Ubuntu server;
5. write an immutable result and mechanical verdict;
6. only after `PASS_ORACLE_GATE`, update the active method/notation/paper and
   prepare a 100-episode checkpointed learner smoke;
7. only after learner-mechanics gates, run short EP ablations at every
   100-episode checkpoint.

Because the all-victim action surface is action-by-user-by-offset work, step 4
is classified **heavy** and must not be run in the browser-coupled local WSL
environment.
