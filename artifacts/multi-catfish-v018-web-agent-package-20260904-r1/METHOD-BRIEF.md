# Multi-Catfish MCRL V0.18 method brief

> **PROVISIONAL_V0.18_NO_LEARNED_OR_EFFICACY_CLAIM**

This is the compact method description for a paper/teaching-deck author. It
intentionally separates the conceptual algorithm from implementation receipts.
The exact source and code maps are in `source-map/`.

## 1. The single objective

The final objective is canonical Main-only ratio-of-sums energy efficiency:

\[
\eta=\frac{\mathcal B}{\mathcal E}.
\]

Here \(\mathcal B\) is the total delivered bits and \(\mathcal E\) is the
total network energy over the declared episode/evaluation block. The three
Catfish routes are not three competing final objectives. They are three
training-time views of how one physical action can affect this same objective.

## 2. One physical comparison

At a sealed predecision anchor, choose a focal user \(u\). Let \(M\) be the
detached Main/reference branch and \(C\) be a matched candidate branch that
differs in only the focal user's physical action. Candidate and reference use
the same keyed exogenous randomness. The opening physical surplus is

\[
g_k=\Delta t\sum_{v\in\mathcal U}
    [R_v^C(k)-R_v^M(k)]
    -\lambda_0\Delta t[P_C^N(k)-P_M^N(k)].
\]

The exact target/measurement is attached only after the predecision inputs and
background reference have been captured. No target or realised branch outcome
is allowed into the deployable state.

## 3. The three Catfish roles

### C1 — Energy-Frontier / Q1

C1 preserves the RIS lineage's EXP/ACRM source idea. EXP/ACRM supplies
informative, reference-anchored candidate-versus-Main opening comparisons. Its
reader-facing view is the focal user's immediate rate change together with the
complete opening network-energy difference:

\[
\zeta_{1,u}=\Delta t[R_u^C(0)-R_u^M(0)]
 -\lambda_0\Delta t[P_C^N(0)-P_M^N(0)].
\]

C1 rows train only \(Q_1\). A negative \(\zeta_{1,u}\) is retained as a
counterexample (“this candidate is worse than Main”), not discarded.

### C2 — Projected-Persistence / Q2

C2 is the OPS-3 projected-persistence family. It looks ahead over the next
available offsets while holding the focal user and non-focal physical
background fixed. It does not execute a future action, run a future policy, or
claim to reproduce future fading/switching.

For \(H_t=\min\{3,T-1-t\}\), legal action \(a\), and offset
\(h\in\{1,2,3\}\), the projected service indicator is \(\chi_{u,a,h}\). The
projected focal rate is \(\widehat R_{u,a,h}\), and the canonical marginal
network-power change is \(\widehat{\Delta P}^{N}_{u,a,h}\). The projected
surplus is summarized as

\[
Z_{2,u,t}(a)=\frac{1}{H_t}\sum_{h=1}^{H_t}
\left[\chi_{u,a,h}\Delta t
 (\widehat R_{u,a,h}-\lambda_0\widehat{\Delta P}^{N}_{u,a,h})
 -(1-\chi_{u,a,h})\kappa\right].
\]

When \(H_t=0\), the surface is zero. Service loss is absorbing, and the
\(-\kappa\) term prevents outage from looking beneficial merely because it
saves energy. The Q2 surface is centred at the detached Main/reference action
\(a^M\):

\[
Q_2^*(s_t,a)=\frac{Z_{2,u,t}(a)-Z_{2,u,t}(a^M)}{\kappa}.
\]

The deployed \(Q_2\) is the learned OPS-3 approximation of this source family.
All legal signs are retained.

### C3 — Relational Zero-Marginal / Q3

C3 addresses the immediate non-focal externality that is hard to encode with a
flat action vector. It uses only current predecision relational information:
the candidate/reference action context, native mask, physical beam identity,
non-focal load/power context, nominal interference geometry, and an observed
SINR proxy. The exact realised counterfactual is a label only.

For each focal action \(a\), a shared victim scorer predicts a contribution
\(d_{u,a,v}\) for each non-focal victim \(v\). Negative predicted victim
effects always count. Positive effects count only when the exact predecision
compatibility bit \(c_{u,a}=1\) says the unilateral change preserves the
zero-marginal network-energy support. The aggregated relational value is

\[
F_{u,a}=\sum_v\left[
 \min(d_{u,a,v},0)+c_{u,a}\max(d_{u,a,v},0)\right].
\]

After aggregation, centre at the detached reference action:

\[
Q_3(s,a)=\frac{F_{u,a}-F_{u,a^M}}{\kappa}.
\]

Thus the reference entry is exactly zero, illegal entries remain outside the
native mask, and the shared scorer is permutation-safe over victims. C3 learns
the unchanged exact native-bit `z3_bits` surface; that surface never enters
the forward input.

## 4. Structured C3 representation

For \(U\) users and \(A=28\) native actions, the predecision representation
has:

```text
action context:  (U, A, 7)
victim tokens:   (U, A, U, 6)
action mask:     (U, A)       Boolean native safe-action mask
victim mask:     (U, A, U)    non-focal relational support
compatibility:   (U, A)       Boolean positive-credit support side-channel
reference:       (U,)         detached Q1+Q2 reference action
```

The public seven-value action context describes service headroom, physical
beam relation, non-focal load, and non-focal power headroom. The six-value
victim token describes observed reference-action SINR and nominal relational
load/interference quantities. Physical identity is `(norad_id, cell_id)`, not
flat action-index equality.

## 5. Source capture and learning

The source order is:

1. compute and detach \(Q_1\), learned \(Q_2\), the native mask, and the
   reference action;
2. encode and authenticate the predecision relational tensors;
3. persist the evaluation-only \(Q_1+Q_2\) background surface;
4. open the matched exact ZR measurement and attach `z3_bits` as a label;
5. verify that the measurement did not mutate live state or RNG;
6. execute only the frozen source/reference action once.

The learner is one `RelationalZRC3QNetwork` with one shared victim scorer and
one independent optimizer. It uses a zero-bootstrap pairwise surface loss on
the `bits / kappa` scale. It never updates \(Q_1\) or \(Q_2\), has no target
network, and has no Bellman or coordination component. The current gate fixes
exactly 100 updates per initialization and uses fresh complete-world
TRAIN/VALIDATION splits.

## 6. Deployment

At decision time, all three learned surfaces are evaluated on the same state
and native safe-action mask:

\[
\Phi_u(s,a)=Q_1(s,a)+Q_2(s,a)+Q_3(s,a),
\qquad
a_u^*=\arg\max_{a\in\mathcal A_u^{\rm safe}(s)}\Phi_u(s,a).
\]

The decoder executes exactly this one Main action. There is no auction,
coordinator, vote, veto, joint decoder, matching stage, route weight, or
post-training override. A dropped head in an ablation is omitted from the
literal sum; the remaining heads are not renormalized.

## 7. Planned physical ablation

After the learned-Q3 gate, a separate TRAIN-development physical screen is
planned with exactly:

```text
FULL     = Q1 + Q2 + Q3
DROP_C1  = Q2 + Q3
DROP_C2  = Q1 + Q3
DROP_C3  = Q1 + Q2
MAIN     = frozen legacy baseline
```

Every arm uses the same native safe mask and one masked argmax. The endpoint is
raw pooled ratio-of-sums \(\eta=\sum\mathcal B/\sum\mathcal E\), with service
reported separately. This package contains no result for those arms.

