# Multi-Catfish MCRL V0.3 presentation layer

Date: 2026-08-31  
Status: **current paper-main-text and main-deck compression contract**  
Scope: authoring only; this document does not delete or relax implementation,
causal-matching, reproducibility, test, or training requirements.

## 1. One-sentence method

> One matched physical intervention is partitioned into focal-now,
> non-focal-now, and everyone-later EE-surplus views; three route-local Q
> estimators learn those views, and their sum selects one service-safe Main
> action.

This is the complete reader-facing story. C1, C2, and C3 are complementary
views of one EE objective, not three objectives whose raw values must all
increase.

## 2. Main-text scientific core

The paper main text keeps six equation blocks.

### 2.1 One final objective

\[
\eta^N=\frac{\mathcal B}{\mathcal E}.
\]

### 2.2 One matched physical comparison

\[
g_k=\Delta t\sum_{i\in\mathcal U}[R_i^C(k)-R_i^M(k)]
-\lambda_0\Delta t[P_C^N(k)-P_M^N(k)].
\]

### 2.3 Three non-overlapping views

\[
\begin{aligned}
\zeta_{1,u}
&=\Delta t[R_u^C(0)-R_u^M(0)]
-\lambda_0\Delta t[P_C^N(0)-P_M^N(0)],\\
\zeta_{3,u}
&=\Delta t\sum_{i\in\mathcal U\setminus\{u\}}
[R_i^C(0)-R_i^M(0)],\\
\zeta_{2,u}
&=\sum_{k=1}^{H^c-1}g_k.
\end{aligned}
\]

Reader labels are fixed:

- C1/Q1: **focal now**;
- C3/Q3: **non-focal now**;
- C2/Q2: **everyone later**.

### 2.4 Exact non-overlap

\[
\zeta_{1,u}+\zeta_{3,u}+\zeta_{2,u}
=\sum_{k=0}^{H^c-1}g_k.
\]

This proves bookkeeping identity only, not learnability or EE efficacy.

### 2.5 Route-local pairwise learning

The paper may show the full registered loss:

\[
\ell_j=w_j\!\left(
[Q_j(s_u,a_u^C)-Q_j(s_u,a_u^M)-\zeta_{j,u}/\kappa]^2
+\beta Q_j(s_u,a_u^M)^2\right).
\]

The main deck uses only the semantic relation

\[
Q_j(s_u,a_u^C)-Q_j(s_u,a_u^M)\approx\zeta_{j,u}/\kappa.
\]

### 2.6 One deployed action

\[
\Phi_u(t,a)=\sum_{j=1}^{3}Q_j(s_u(t),a),\qquad
a_u^\star(t)=\arg\max_{a\in A_u(t)}\Phi_u(t,a).
\]

Only this Main action is executed. There is no auction, coordinator, vote,
joint decoder, or post-training override.

## 3. Three Catfish descriptions for paper and slides

- **C1 — Energy-Frontier:** RIS-lineage EXP/ACRM generates informative
  candidate-versus-Main opening comparisons for the focal user's immediate
  EE surplus.
- **C2 — Temporal-Fork:** at an eligible departure anchor, temporarily retain
  the legal incumbent, observe the matched downstream system EE surplus, and
  release once to branch-local Main when the incumbent becomes infeasible.
- **C3 — Spatial-Externality:** lagged load and activation context identifies
  spatially interactive anchors; unilateral opening comparisons estimate the
  focal action's immediate rate effect on non-focal users.

Negative route targets are retained. A negative \(\zeta_{j,u}\) can teach a Q
surface that a candidate is worse than Main; route value is judged by
held-out EE ablation, not by requiring positive target labels.

## 4. Authoring-depth boundary

| Layer | Must show | May omit from that layer |
|---|---|---|
| Paper main text | one objective; matched M/C intervention; three views and identity; one pairwise learner; one deployed action; one sentence per source mechanism | hashes, schema fields, key construction, physical-ID encoding, tie-break sequence, checkpoint format, exact state field list, neutral sampler internals |
| Main deck | the six-slide flow in Section 6; compact pairwise relation; summed masked action | full loss weights/gauge, dataset row schema, gate ladder, source digests, release receipts, replay/checkpoint details |
| Appendix/supplement | causal matching and common-randomness protocol; full loss/calibration; source/control construction; reproducibility and claim gates | none of the facts needed to reproduce or audit the experiment |
| Implementation/tests | all canonical checks and complete provenance | nothing is removed merely because it is absent from the paper or slides |

The paper may summarize keyed common randomness as one sentence: candidate
and reference branches use identical exogenous randomness. Key composition,
hashes, match counts, and serialization belong in the reproducibility
appendix or artifact documentation.

## 5. C2 fallback disclosure

The main story uses the only currently exercised C2 path: legal incumbent
hold followed by monotone release to branch-local Main. The unexercised
max-lagged-SINR rival fallback is not an implementation detail because it can
change the source population and targets. Therefore:

- while it remains active in the canonical source rule, disclose it once in
  the detailed method or appendix, but do not give it a main slide or depict
  it as validated;
- if the canonical experiment is frozen as hold-only, anchors without a legal
  incumbent are ineligible and the fallback is omitted entirely from the
  paper and deck.

Presentation compression must not silently change the algorithm.

## 6. Six-slide main-deck arc

1. **One EE objective and one intervention** — \(\eta^N\), matched M/C world,
   one focal action difference.
2. **Three non-overlapping EE views** — focal now, non-focal now, everyone
   later, plus the identity.
3. **Three Catfish source roles** — one short sentence and one visual cue per
   route; no implementation receipts.
4. **Route-local learning** — opening/temporal comparisons feed \(Q_1,Q_3\)
   and \(Q_2\); use the compact pairwise relation.
5. **One deployed action** — \(Q_1+Q_2+Q_3\), safety mask, one Main argmax.
6. **Evidence boundary** — formula correctness is not efficacy; show only
   sealed ablation evidence and mark unresolved gates plainly.

Detailed route figures, dataset routing, control construction, and gate
ladders are appendix slides, not required stops in the main narrative.

## 7. Public notation subset

The main text and main deck introduce only the subset required by their
displayed formulas:

\[
\eta^N,\;\mathcal B,\;\mathcal E,\;M,\;C,\;\lambda_0,\;g_k,\;
\zeta_{1,u},\;\zeta_{2,u},\;\zeta_{3,u},\;Q_j,\;\Phi_u,\;
A_u,\;R_u,\;P^N,\;\Delta t,\;k,\;H^c.
\]

The following are appendix-level unless needed at first use in the full loss
or dataset discussion:

\[
\kappa,\;n_0,\;\widetilde\zeta_{j,u},\;\nu_j,\;w_j,\;\beta,\;
\ell_j,\;D^o,\;D^t,\;D^a,\;s_u,\;a_u^M,\;a_u^C.
\]

Do not add aliases such as \(EE_1\), \(EE_2\), \(EE_3\), \(r_2\), \(r_3\),
\(\delta_j\), or \(\rho_j\). Primary mathematical symbols remain
single-letter with single-letter or numeric indices according to the active
symbol contract.

## 8. Claim ceiling

This compression authorizes explanation and figure/deck production. It does
not authorize a claim that any Catfish or the full method improves EE. Such a
claim requires held-out matched ratio-of-sums ablation with the service guard.
Current short-pilot evidence remains directional, and the present C1 result
is coverage/control-confounded until the cluster-matched adjudication closes.
