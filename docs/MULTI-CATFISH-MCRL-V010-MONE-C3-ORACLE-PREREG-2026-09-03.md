# Multi-Catfish MCRL V0.10 MONE-C3 oracle preregistration

Status: **FROZEN BEFORE OUTCOME ACCESS**  
Scope: TRAIN-development, no learner update, no TEST data, no efficacy claim  
Decision answered: whether exact matched-opening non-focal externality is a
useful third head on top of the frozen C1 and corrected OPS3 C2.

## 1. Fixed architecture

The deployment architecture is unchanged: exactly three Q functions, one
common safe mask, the left-to-right unweighted sum `Q1 + Q2 + Q3`, one masked
argmax, and one executed Main action.  This gate contains no coordinator,
auction, second decoder, route weight, sign flip, or post-training override.

The final evaluation quantity is the canonical ratio of sums

\[
\eta=\frac{\sum_{e,t,u}\Delta t\,R_{e,t,u}}
          {\sum_{e,t}\Delta t\,P^N_{e,t}}.
\]

## 2. Frozen heads and gauges

- `Q1` is the existing frozen C1 head for each of the three declared
  lineages.  Its parameters are read-only.
- `O2` is exact OPS3 with the execution-equivalent t=0 warm-start and opening
  service gate (`ee-axis-ops3-live-anchor-v1.2`).
- OPS3 is first centred at the frozen Q1-greedy native action.  This is only
  an action-independent gauge.
- The C3-free behaviour background at each state is

\[
b_u(s)=\min\arg\max_{a\in\mathcal A_u^{\rm safe}(s)}
       \left[Q_1(s_u,a)+O_2(s_u,a)\right].
\]

The same native mask and smallest-index tie break are used throughout.

## 3. MONE C3 target

For focal user `u` and legal action `a`, create `b^(u<-a)` by replacing only
the focal entry of `b`.  Evaluate `b` and `b^(u<-a)` with the same sealed
anchor, canonical `StepEnvironment.evaluate_actions`, and the same keyed
common-random field.  Define

\[
z_{3,u}(s,a\mid b)=\Delta t\sum_{v\ne u}
\left[R_v(s,b^{u\leftarrow a})-R_v(s,b)\right],
\qquad
O_3(s_u,a)=\frac{z_{3,u}(s,a\mid b)}{\kappa}.
\]

The reference entry `O3(s_u,b_u)` is exactly zero.  Illegal entries are zero
behind the common mask.  Negative values are retained.  No clipping,
post-outcome scaling, sign reversal, horizon extension, or threshold tuning
is allowed.

C3 contains only current-slot non-focal delivered bits.  It contains no focal
rate, energy, handover reward, outage term, or future policy consequence.
For the diagnostic matched C1 oracle from the same evaluations,

\[
z_{1,u}=\Delta t\,\Delta R_u-\lambda_0\Delta t\,\Delta P^N,
\]

and the runner must verify, within the declared floating-point tolerance,

\[
z_{1,u}+z_{3,u}
=\Delta t\left(\sum_v\Delta R_v-\lambda_0\Delta P^N\right).
\]

OPS3 C2 owns only projected offsets `h >= 1`; its h=0 quantity is a service
gate.  The three views are therefore separated by user, physical quantity,
and time offset.

## 4. Binding arms

Only the following two arms are binding:

- `FULL = Q1 + O2 + O3`
- `DROP_C3 = Q1 + O2`

At each arm state, `b` is recomputed by the same frozen mapping and the MONE
surface is generated once around that `b`.  It is not recentered around the
FULL action or an arm-specific reduced-head action.

DROP-C1 and DROP-C2 are intentionally absent.  Before Q3 is learned, its
teacher background queries Q1 and O2; using that oracle inside DROP-C1 or
DROP-C2 would leak the supposedly removed head.  The full five-arm ablation
becomes binding only after Q3 is learned and frozen.

## 5. Frozen panel and execution

- split: TRAIN only;
- world seed: `2026104601`;
- seed freshness: a repository-wide text search before this file was created
  returned no occurrence of `2026104601`;
- lineages: `2026092101`, `2026092102`, `2026092103`;
- users: 100;
- steps per episode: 10;
- episodes: one per `(arm, lineage)`, six total;
- keyed field component: `MCRL_V010_MONE_C3_ORACLE_V1` plus the world seed;
- field excludes arm and lineage;
- TLE archive, start instant, mobility, physics, Q1 checkpoints, `lambda0`,
  `kappa`, and `Delta t` are inherited byte-for-byte from the authenticated
  V0.9 runner inputs, except for the corrected OPS3 live adapter;
- compute class: heavy no-training matched oracle; execute on the Ubuntu
  server, with six independent shards.

The V0.9 world `2026104501` must not be reused for acceptance.

## 6. Binding mechanics and decision gate

All of the following are required:

1. exact contract/runtime hashes and one common field per world;
2. no TEST access, learner update, target-network query, or future-policy
   query;
3. every MONE branch changes only the focal native action;
4. every reference row is exactly zero and every illegal row is zero;
5. the opening C1+C3 identity holds within `512 * eps` times the term scale;
6. matched evaluations leave simulator state and RNG byte-identical;
7. corrected OPS3 opening service and required power match execution;
8. MONE has nonzero legal-action spread and changes at least one FULL action;
9. pooled ratio-of-sums EE is strictly `FULL > DROP_C3`;
10. at least two of three lineage EE contrasts are strictly positive;
11. pooled served user-steps for FULL are not below DROP-C3, and at least two
    lineage service contrasts are nonnegative.  A one-user-step shortfall
    fails.

If all conditions pass, the result is `GO_MONE_C3_LEARNER`.  Otherwise it is
`FAIL_MONE_C3_ORACLE`; no learner or episode training is authorized by this
gate.

## 7. Mandatory diagnostics that cannot rescue a failure

At every anchor, record frozen-Q1 versus matched-oracle-C1 pairwise sign
agreement, Spearman rank correlation, top-action agreement, and oracle
regret.  This separates a weak Q1 approximation from a wrong C3 estimand but
cannot replace Q1 in a binding arm.

For every step where FULL differs from `b`, evaluate the realised joint
opening fixed-lambda surplus and compare it with the sum of the selected
unilateral `z1 + z3` terms.  Record the simultaneous interaction residual and
its sign.  A strict majority of exposed steps with direction reversal is a
hard stop even if the episode-level EE margin is positive.

Record per-step action flips, served users, delivered bits, network energy,
hold rate, and active-beam count.  These observations cannot be used to alter
the frozen sign, scale, seed, horizon, threshold, or action set.

## 8. Claim ceiling and next step

A pass is only one-world TRAIN-development evidence that MONE is worth
learning.  It is not learned evidence, held-out evidence, or efficacy.

After a pass, implement and freeze the deployable Q3 state/source/learner,
then run a short-EP five-arm experiment with checkpoints every 100 episodes:
FULL, DROP-C1, DROP-C2, DROP-C3, and the no-Catfish baseline.  Only a frozen
learned Q3 checkpoint may be reused across the retained-Q3 arms.
