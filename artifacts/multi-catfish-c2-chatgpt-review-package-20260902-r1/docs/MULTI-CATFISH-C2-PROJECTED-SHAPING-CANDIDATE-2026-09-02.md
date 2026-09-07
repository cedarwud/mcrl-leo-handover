# Multi-Catfish C2 projected temporal-EE shaping candidate

Date: 2026-09-02  
Status: `CLEAN_CANDIDATE_DRAFT__FORMULA_PROBE_REQUIRED`  
Claim ceiling: design hypothesis only; no learner, training, or EE-efficacy claim

## Decision question

Can Q2 learn a deterministic, decision-time forecast of the focal action's
future EE consequence and thereby improve final matched ratio-of-sums EE,
without importing downstream actions across counterfactual branches?

This candidate deliberately does **not** preserve the retired claim that C2 is
an exact realized downstream total-effect decomposition. The canonical final EE

\[
\eta=\frac{\mathcal B}{\mathcal E}
\]

remains frozen. C1, C2, and C3 remain in one fixed-\(\lambda_0\), shared-\(\kappa\)
surplus unit so deployment can still use the direct unweighted sum.

## Three complementary views

- C1/Q1: focal user's realized opening-step rate and the complete opening-step
  network-energy change;
- C2/Q2: focal action's deterministic projected consequence over future
  offsets \(k\geq1\);
- C3/Q3: other users' realized opening-step rate externality.

The user/time boundaries remain non-overlapping. The old exact realized-trace
identity is no longer claimed because C2 is an explicit forecast surrogate.
Final value is judged only by matched raw ratio-of-sums ablation.

## Forecast operator

For focal user \(u\), current legal action \(a\), reference action \(a^M\),
and a short fixed horizon \(K\), define the predicted temporal surplus

\[
\widehat z_{2,u}(a)=
\sum_{k=1}^{K}w_k\Delta t
\left(
[\widehat R_{u,k}(a)-\widehat R_{u,k}(a^M)]
-\lambda_0[\widehat P_{u,k}(a)-\widehat P_{u,k}(a^M)]
\right).
\]

Use fixed, predeclared \(w_k\); the first probe uses \(w_k=1\). The reference
row is exactly zero. Negative targets are retained.

Here \(\widehat R_{u,k}(a)\) and \(\widehat P_{u,k}(a)\) are not realized
successor outcomes. They are decision-time predictions under one declared
frozen-background persistence operator:

1. propagate the action's satellite with the frozen TLE to \(t+k\);
2. keep the current user position fixed for the forecast-only operator;
3. keep the action's physical earth-fixed cell while its projected visibility
   and link-power feasibility remain valid;
4. set predicted service and radiated power to zero after projected loss;
5. use expected fading, never a realized future fading draw;
6. use the committed lagged radiating/load state as the frozen background;
7. compute focal marginal network power as the canonical projected system-power
   difference with and without the focal forecast link on that background.

No branch is advanced, no future native action is selected, and no action from
one branch is imported into another branch. Therefore treatment-induced
successor action-support divergence is outside this forecast operator.

## Physical prediction

Let \(g_{u,k}(a)\) be projected transmit gain and let \(g^s_u(a)\) be the
segment-start gain: the committed start gain for a continuing incumbent, and
the current gain for a new association. The projected required link power is

\[
\widehat p_{u,k}(a)=p^0\frac{g^s_u(a)}{g_{u,k}(a)}.
\]

If projected visibility fails, \(g_{u,k}(a)=0\), or
\(\widehat p_{u,k}(a)>p^{\max}\), the forecast link is unserved at that offset.
The projected wanted signal, path loss, candidate interference against the
lagged radiating field, bandwidth sharing, PA supply draw, beam activation, and
satellite fixed power must reuse the canonical physics functions. The probe may
not invent a separate linear power model.

## Q2 state

Q2 receives the existing causal state plus four action-aligned forecast blocks:

1. normalized cumulative predicted focal bits;
2. normalized cumulative predicted focal marginal energy;
3. projected served fraction over \(1{:}K\);
4. terminal-to-current transmit-gain ratio.

All four blocks are available before action selection and are computed for all
28 native current actions. Illegal current actions remain masked. No realized
future reward, action, mask, fading sample, or branch policy output enters the
state.

The training target is \(\widehat z_{2,u}/\kappa\). Q1 and Q3 are unchanged,
and Q2 must use the same frozen hexadecimal \(\lambda_0\) and \(\kappa\).

## C2 Catfish source

The provisional role name is **Projected-Trajectory Catfish**.

Its source selector is based only on predecision forecast-feature dispersion:

\[
d_u=\max_{a\in A_u}\widehat p_{u,1:K}(a)
-\min_{a\in A_u}\widehat p_{u,1:K}(a),
\]

augmented by whether legal actions disagree in projected survival. Select
anchors/users with large \(d_u\), then enumerate every legal current action and
retain every target sign. The selector cannot inspect realized future EE or
discard rows after seeing \(\widehat z_{2,u}\).

The Catfish function is to expose energy-trajectory and service-risk contrasts
that an ordinary Main trajectory may rarely sample. Q2 compresses those
counterfactual forecasts into the deployed network; deployment performs no
forecast rollout or secondary decision.

## Formula-first no-training probe

For each fresh TRAIN-design anchor:

1. compute all legal \(\widehat z_{2,u}(a)\) values;
2. verify exact reference zero, finite values, all-sign retention, and nonzero
   within-anchor spread;
3. form the centered oracle surface
   \(Q_2^*(a)=\widehat z_{2,u}(a)/\kappa\);
4. compare oracle action choices for \(Q_1+Q_3\),
   \(Q_1+Q_2^*+Q_3\), \(Q_1+Q_2^*\), and \(Q_2^*+Q_3\);
5. execute those choices only through the canonical environment on matched
   fresh development worlds and report raw bits, energy, service, and
   ratio-of-sums EE.

Before any Q2 learner, require directional passage of

\[
\eta(Q_1+Q_2^*+Q_3)>\eta(Q_1+Q_3),
\]

\[
\eta(Q_1+Q_2^*+Q_3)>\eta(Q_1+Q_2^*),
\]

and

\[
\eta(Q_1+Q_2^*+Q_3)>\eta(Q_2^*+Q_3),
\]

with the existing service guard. These are C2, C3, and C1 marginal directions.
Pair-versus-singleton comparisons are diagnostic only.

## Hard stops

Reject this candidate before training if:

- projected values require a realized future RNG draw or future policy action;
- any current legal action lacks a forecast value;
- the canonical power/rate functions cannot implement the forecast operator;
- the target has negligible action spread or never changes the deployed argmax;
- the oracle C2 marginal is nonpositive;
- C1 or C3 becomes nonpositive in the oracle full system;
- service inferiority appears;
- a simple model cannot beat zero and action-only nulls on world/anchor-disjoint
  folds.

## Scientific boundary

A positive formula/oracle probe would establish only that deterministic orbital
foresight is a plausible auxiliary training signal. It would not prove that
the forecast equals the realized downstream total effect, that Q2 can learn it,
or that the final algorithm improves EE. Those claims require the later learned
FULL-versus-DROP-C2 matched evaluation.

## Open decisions before implementation

1. choose the smallest useful \(K\) by preoutcome mechanics, not EE outcome;
2. specify the exact projected marginal-system-power calculation;
3. verify all presentation notation against the active single-letter symbol
   table;
4. obtain independent Fable/Sol adjudication against the clean-room candidate;
5. freeze a bounded probe receipt before opening new outcome-bearing results.
