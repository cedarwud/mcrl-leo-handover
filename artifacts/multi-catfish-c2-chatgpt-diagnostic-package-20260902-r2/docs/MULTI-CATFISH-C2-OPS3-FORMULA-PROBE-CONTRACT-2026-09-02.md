# Multi-Catfish C2 OPS-3 formula-probe contract

Date: 2026-09-02  
Status: `FROZEN_FOR_BOUNDED_FORMULA_PROBE__NO_LEARNER_NO_TRAINING`  
Claim ceiling: fresh TRAIN-design directional evidence only

## Decision and invariant

OPS-3 Projected-Persistence Catfish is the sole candidate authorized for the
next formula implementation and oracle screen. It is not an accepted C2.

The deployed architecture remains exactly three independent heads, one common
safe mask, direct unweighted `Q1 + Q2 + Q3`, one argmax, and one executed Main
action. Final efficacy remains canonical pooled ratio-of-sums EE. The fixed
surplus multiplier and unit are

\[
\lambda_0=\texttt{0x1.443a8f481639ap+26}\;\text{bit/J},
\qquad
\kappa=\texttt{0x1.2cea89d260f2ap+33}\;\text{bit}.
\]

The decision interval is
\(\Delta t=\texttt{0x1.e147ae147ae14p+4}\) seconds.

## Exact projection operator

At current predecision time \(t\), let

\[
H_t=\min\{3,T-1-t\}.
\]

For \(H_t=0\), every legal action receives \(Z_{2,u,t}(a)=0\). Otherwise,
for focal user \(u\) and each **current native legal** physical action
\(a=(s,c)\):

1. Hold the focal user at its current ECEF position.
2. Keep the action's physical satellite \(s\) and earth-fixed cell \(c\)
   fixed for all projected offsets; there is no future action or argmax.
3. Propagate the tracked TLE satellite set to every native 640 ms D2
   measurement between the current decision and offsets \(h=1,2,3\).
4. Deep-copy the live predecision `D2Tracker` and advance only that copy with
   the frozen user coordinates. The live environment, driver, tracker, RNG,
   candidate order, and networks may not change.
5. Evaluate cell visibility at the future satellite and the physical **cell
   centre**, never at the focal user.
6. Use unit Rician power gain and zero-dB shadow loss. OPS-3 draws no RNG and
   this convention is called a deterministic median/no-fading channel shadow.

Let \(g^s_{u,a}\) equal the committed segment-start transmit gain only when
the action continues the focal user's currently served physical link;
otherwise it equals the current transmit gain of \(a\). At offset \(h\),

\[
\widehat p_{u,a,h}=p^0\frac{g^s_{u,a}}{g_{u,a,h}}
\]

when \(g_{u,a,h}>0\). Define the instantaneous projected feasibility

\[
\rho_{u,a,h}=
\mathbf 1\{\text{projected D2 eligible}\}
\mathbf 1\{\text{cell visible}\}
\mathbf 1\{g_{u,a,h}>0\}
\mathbf 1\{\widehat p_{u,a,h}\le p^{\max}\}.
\]

OPS-3 is a persistence forecast, not a hidden re-association policy. Service
loss is therefore absorbing:

\[
\chi_{u,a,h}=\prod_{r=1}^{h}\rho_{u,a,r}.
\]

Once \(\chi=0\), later offsets cannot silently restart a new segment.

## Frozen non-focal background

For each focal user, construct \(\mathcal L_t^{-u}\) only from the last
committed **served** associations and link powers of users \(v\ne u\):

- beam load is the count of those served associations;
- beam RF power is their maximum link power;
- beam/satellite activation follows from that set;
- `_previous_demand` is forbidden because it is ungated demand;
- the physical beam cells and RF powers stay frozen over the projection;
- their satellites move according to the same TLE projection for interference.

Using the canonical max-per-beam RF rule, nonlinear PA efficiency, per-beam
circuit power, and once-per-active-satellite baseband power, define

\[
\widehat{\Delta P}^{N}_{u,a,h}=
P^N\!\left(\mathcal L_t^{-u}\oplus[(s,c),\widehat p_{u,a,h}]\right)
-P^N(\mathcal L_t^{-u}).
\]

If \((s,c)\) already exists, the focal link changes its beam power only
through `max(background power, p_hat)`. A new beam adds its canonical circuit
cost, and a previously inactive satellite adds its canonical baseband cost.

Let \(\widehat R_{u,a,h}\) be focal Shannon rate under projected geometry,
the deterministic median channel, canonical same-satellite receive-gain
override, frozen co-channel interference, and beam load
\(1+n^{-u}_{s,c}\). No non-focal future rate enters C2.

## Frozen score and oracle surface

\[
Z_{2,u,t}(a)=\frac{1}{H_t}\sum_{h=1}^{H_t}
\left[
\chi_{u,a,h}\Delta t
\left(\widehat R_{u,a,h}-\lambda_0
\widehat{\Delta P}^{N}_{u,a,h}\right)
-(1-\chi_{u,a,h})\kappa
\right].
\]

The `-kappa` term prevents an outage from receiving an energy-saving credit.
The mean, rather than a three-offset sum, preserves the representative
one-decision output scale. Every sign is retained.

For the current frozen-Main reference action \(a^M\),

\[
Q_2^*(s_t,a)=\frac{Z_{2,u,t}(a)-Z_{2,u,t}(a^M)}{\kappa}.
\]

The reference row must be bit-exact zero. Final EE signs are determined only
from raw bits and energy, never from \(\lambda_0\).

## Formula-state receipt

The formula implementation emits 16 finite physical values per action:

- other-user beam load divided by user count;
- other-user beam maximum RF power divided by \(p^{\max}\);
- beam-active bit;
- satellite-active bit;
- for each \(h=1,2,3\): valid-horizon bit, \(\chi\), required-power ratio,
  and `log1p(projected SINR)`.

For offsets outside \(H_t\), all four values are zero. For a zero/null gain,
the required-power feature is zero and \(\chi=0\); for a finite but
over-ceiling requirement, the uncapped ratio greater than one is retained.
Rate, SINR, and marginal power are zero after absorbing loss. These feature
rules do not clip or change the target.

## Required mechanics tests before opening outcomes

The formula gate must prove:

1. terminal \(H_t=0\) gives an all-zero legal Q2 surface;
2. candidate equals reference gives exact zero;
3. changing the gauge action changes only a constant offset;
4. \(\chi=0\) contributes exactly `-kappa`, not an energy credit;
5. service loss is absorbing;
6. shared-beam max and new-beam/satellite activation use canonical power;
7. deterministic median-channel evaluation consumes no RNG;
8. cloned D2 projection and formula evaluation leave all live state unchanged;
9. every current legal action has one finite score, illegal actions are never
   selected, distinct cells use distinct projected geometry, and negative
   scores are retained;
10. no \(h=0\), non-focal future rate, future action, future mask, fallback,
    or post-outcome row deletion enters the module.

Failure makes the probe `INVALID_NO_OUTCOME_OPENING`.

## Predeclared TRAIN-design worlds and arms

The unopened TRAIN-design seed panel is fixed before execution:

- smoke world: `2026104501`;
- mandatory expansion before any learner: `2026104501`, `2026104502`,
  `2026104503`.

For each of three frozen Q1/Q3 lineages, run four native ten-step policies:

\[
P_{123}=Q_1+Q_2^*+Q_3,\quad P_{13}=Q_1+Q_3,
\]

\[
P_{12}=Q_1+Q_2^*,\quad P_{23}=Q_2^*+Q_3.
\]

Each arm owns its contemporaneous state, mask, OPS-3 surface, and one argmax.
Only keyed exogenous randomness is shared. No action crosses arms. The smoke
budget is exactly 12 episodes; the three-world budget is exactly 36 episodes.

## Decision rules

At the 12-episode smoke stage, stop and return to formula design if any one of
the following is nonpositive in all three lineages:

\[
\eta(P_{123})-\eta(P_{13})\quad(C2),
\]

\[
\eta(P_{123})-\eta(P_{12})\quad(C3),
\]

\[
\eta(P_{123})-\eta(P_{23})\quad(C1).
\]

Also stop on pooled service inferiority for any FULL/drop comparison. Otherwise
run the predeclared three-world panel. The three-world directional gate requires
for **each** of C1/C2/C3:

1. positive pooled raw ratio-of-sums EE difference;
2. positive initialization-specific difference in at least two of three
   lineages;
3. positive median physical-world difference;
4. pooled FULL served fraction non-inferior;
5. nonnegative served-fraction difference in at least two of three lineages.

No bootstrap confidence claim is made from three worlds. Passage authorizes
only Q2 source/state dataset work and a bounded learner preregistration. Failure
does not authorize coefficient, sign, horizon, seed, or penalty tuning on the
opened worlds.

## Claim boundary

OPS-3 is a deterministic orbital-persistence, recurrence-power, and
service-risk prior under a frozen-user, frozen-background, median-channel
shadow. It is not an exact realized future-EE decomposition, a causal total
effect, a policy-invariant potential, or a prediction of realized mobility,
fading, or downstream switching. Q2 would be supervised distillation of this
known score; that disclosure is mandatory if it survives.

No 500/1500/3000/9000-episode training is authorized by this contract.
