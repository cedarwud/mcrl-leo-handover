# Multi-Catfish C2 OPS-3 fresh-context design review

Date: 2026-09-02  
Status: `INDEPENDENT_REVIEW_COMPLETE__FORMULA_PROBE_NOT_IMPLEMENTED`  
Claim ceiling: reviewer design; no implementation, learner, training, or efficacy claim

## Verdict

A decision-time orbital-persistence C2 is conceptually valid as an auxiliary
shaping/distillation mechanism. It avoids the V0.5/V0.6 failure class by
advancing no counterfactual branch, importing no successor action, and making
no realized downstream total-effect claim.

The earlier projected-shaping draft is not freezeable as written. It needs an
explicit service-loss term, exact deterministic fading/shadow convention,
terminal handling, canonical marginal-network-power construction, horizon
normalization, and action-aligned primitive state rather than cumulative target
components.

## Recommended candidate: OPS-3

The provisional role name is **Projected-Persistence Catfish**. For current
time `t`, use

\[
H_t=\min(3,T-1-t).
\]

If \(H_t=0\), set the C2 value to zero. For focal user \(u\), current legal
physical action \(a\), and offset \(h\in\{1,\ldots,H_t\}\), propagate the
satellite from the frozen TLE while holding the user at the current ECEF
position. Freeze the last committed non-focal associations, link powers, beam
loads, beam cells, and activation state. Use unit Rician power gain and zero-dB
shadow loss; call this a deterministic median-channel shadow, not expected
shadow fading.

Let \(g^s_{u,a}\) be the committed segment-start gain when \(a\) continues the
current physical link and the current transmit gain otherwise. Let
\(g_{u,a,h}\) be projected transmit gain. Then

\[
\widehat p_{u,a,h}=p^0\frac{g^s_{u,a}}{g_{u,a,h}}.
\]

Define the projected service indicator

\[
\chi_{u,a,h}=
\mathbf 1\{\text{D2 eligible}\}
\mathbf 1\{\text{cell visible}\}
\mathbf 1\{g_{u,a,h}>0\}
\mathbf 1\{\widehat p_{u,a,h}\le p^{\max}\}.
\]

Let \(\mathcal L_t^{-u}\) be the frozen non-focal physical background. Using
the canonical max-per-beam RF power, nonlinear PA efficiency, beam circuit
power, and satellite baseband power, define

\[
\widehat{\Delta P}^{N}_{u,a,h}=
P^N\left(\mathcal L_t^{-u}\oplus[(a,\widehat p_{u,a,h})]\right)
-P^N(\mathcal L_t^{-u}).
\]

Let \(\widehat R_{u,a,h}\) be focal Shannon rate under the same frozen
background, projected geometry, deterministic median channel, co-channel
interference, and load `1 + non-focal load`. No non-focal rate enters C2.

The proposed native-bit trajectory score is

\[
Z_{2,u,t}(a)=\frac{1}{H_t}\sum_{h=1}^{H_t}
\left[
\chi_{u,a,h}\Delta t
\left(\widehat R_{u,a,h}-\lambda_0
\widehat{\Delta P}^{N}_{u,a,h}\right)
-(1-\chi_{u,a,h})\kappa
\right].
\]

The `-kappa` service-risk term prevents projected outage from appearing useful
merely because it saves energy. Uniform averaging keeps a three-offset route at
a representative one-decision scale rather than tripling Q2's influence.

For current frozen-Main reference \(a^M\), define the direct-sum oracle surface

\[
Q_2^*(s_t,a)=\frac{Z_{2,u,t}(a)-Z_{2,u,t}(a^M)}{\kappa}.
\]

The learned pair target is the same difference. This preserves the existing
fixed \(\lambda_0\), shared \(\kappa\), and reference-zero gauge. Final efficacy
is still decided by raw matched ratio-of-sums, not the fixed multiplier.

## Minimal action-aligned Q2 state

Use one action-shared scorer. For each current action include four frozen
background quantities:

- non-focal beam load;
- non-focal maximum RF power;
- beam-active bit;
- satellite-active bit.

For each of three projected offsets include:

- valid-horizon bit;
- projected service indicator \(\chi\);
- normalized required link power;
- `log(1 + projected SINR)`.

This gives 16 physical values per action plus the current legal mask. It avoids
feeding cumulative predicted bits/energy directly to Q2 and remains
cell-specific; V0.7 instead repeated one satellite range-rate feature across
seven cell actions.

## Projected-Persistence Catfish source

Mine recurrence and availability cliffs using only decision-time forecast
primitives. For each user-state compute required-power dispersion across legal
actions/offsets and whether projected service indicators disagree. Within
dwell-phase and incumbent/new-link strata, take fixed quotas from both cliff
and non-cliff states, rank by power dispersion, enumerate every current legal
action, and retain all positive, zero, and negative labels.

Projected physical loss sets \(\chi=0\). It never deletes a row, imports a
future action, or invokes a fallback.

## Smallest no-training interaction probe

Use one fresh TRAIN-design world, three frozen Q1/Q3 lineages, and the four
native policies

\[
P_{123}=Q_1+Q_2^*+Q_3,\quad P_{13}=Q_1+Q_3,
\]

\[
P_{12}=Q_1+Q_2^*,\quad P_{23}=Q_2^*+Q_3.
\]

This is 12 ten-step episodes. Each arm computes its own current state, mask,
OPS-3 surface, and single argmax. No action crosses arms. Require directional
passage of

\[
\eta(P_{123})>\eta(P_{13}),\quad
\eta(P_{123})>\eta(P_{12}),\quad
\eta(P_{123})>\eta(P_{23}),
\]

with the existing service guard. These recheck C2, C3, and C1 respectively.
If directions are mixed, use a predeclared three-world 36-episode escalation;
mixed results do not authorize a learner.

Estimated runtime is 1--3 minutes for the one-world screen and 3--8 minutes
for the three-world escalation if projection is vectorized. These are
non-heavy local diagnostics.

## Hard stops

Stop before any learner if:

- the formula needs a future RNG draw, future policy action, or imported mask;
- any current legal action lacks a finite score;
- projected loss deletes or clips a row instead of setting \(\chi=0\);
- an offset-zero term or non-focal future rate enters C2;
- the surface has no action spread or never changes a Q1+Q3 argmax;
- cell-distinct projected geometry still produces satellite-slot-identical
  scores;
- C1, C2, or C3 has a nonpositive marginal in all three lineages;
- the service guard fails.

## Claim boundary

OPS-3 is a learned approximation of a deterministic orbital-persistence,
recurrence-power, and service-risk prior under a frozen-user, frozen-background,
median-channel shadow. It is not an exact future-EE decomposition, a causal
total effect, policy-invariant potential shaping, or a prediction of realized
mobility/fading/downstream switching.

Because OPS-3 is analytically computable, Q2 is supervised distillation of a
known model-based score. That is compatible with the user's one-head training
requirement but must be disclosed in the paper.

## Current authorization

- formula implementation and unit tests: pending adjudication;
- bounded no-training oracle probe: pending a frozen implementation contract;
- Q2 learner and episode training: not authorized.
